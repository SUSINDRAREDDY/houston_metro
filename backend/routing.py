"""Timetable routing: at most two boardings, no LLM-generated transit facts."""
import bisect
import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .config import DB
from . import demo_trace, database

TZ=ZoneInfo('America/Chicago')

def connect():
    if database.managed():
        return database.connect()
    if not DB.exists(): raise ValueError('Schedules are not loaded yet. Run the GTFS import.')
    db=sqlite3.connect(f'file:{DB}?mode=ro',uri=True, factory=demo_trace.Connection if demo_trace.enabled() else sqlite3.Connection)
    db.row_factory=sqlite3.Row
    demo_trace.event('DB_OPEN', path=str(DB.resolve()), mode='read-only', persistent_writes=False)
    return db

def active_services(db, day):
    stamp=day.strftime('%Y%m%d');weekday=day.strftime('%A').lower()
    active={r[0] for r in db.execute(f"SELECT service_id FROM calendar WHERE {weekday}='1' AND start_date<=? AND end_date>=?",(stamp,stamp))}
    for sid,kind in db.execute('SELECT service_id,exception_type FROM calendar_dates WHERE date=?',(stamp,)):
        if kind==1: active.add(sid)
        elif kind==2: active.discard(sid)
    return active

def stop_search(db,q,limit=12):
    q=q.strip()
    if not q:return []
    # Aliases resolve to actual named GTFS stops, not invented coordinates.
    aliases={'uh':'uh south university oaks','university of houston':'uh south university oaks','uh central':'uh south university oaks','downtown':'central station','downtown houston':'central station','medical center':'dryden/tmc','nrg':'stadium park','airport':'iah'}
    if q.lower() in ('downtown','downtown houston'):
        return [dict(r) for r in db.execute("SELECT stop_id,stop_code,stop_name,stop_lat,stop_lon FROM stops WHERE stop_name LIKE 'Central Station %' OR stop_name LIKE 'Central Stn Main %' ORDER BY stop_name LIMIT ?",(limit,))]
    term=aliases.get(q.lower(),q)
    tokens=term.replace('%','').replace('_','').split()
    where=' AND '.join('stop_name LIKE ?' for _ in tokens)
    rows=db.execute(f'''SELECT stop_id,stop_code,stop_name,stop_lat,stop_lon FROM stops
        WHERE (location_type='' OR location_type='0') AND (({where}) OR stop_id=? OR stop_code=?)
        ORDER BY CASE WHEN stop_id=? OR stop_code=? THEN 0 ELSE 1 END,stop_name LIMIT ?''',
        [f'%{x}%' for x in tokens]+[q,q,q,q,limit]).fetchall()
    return [dict(r) for r in rows]

def distance(a,b):
    lat1,lon1,lat2,lon2=map(math.radians,[a['stop_lat'],a['stop_lon'],b['stop_lat'],b['stop_lon']])
    return 6371000*2*math.asin(min(1,math.sqrt(math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2)))

def plan(db,origin_ids,destination_ids,departure,mode='any',max_transfers=1,prefer='fastest',excluded_routes=()):
    start_dt=departure.astimezone(TZ)
    day=start_dt.date()
    coverage=db.execute('SELECT feed_start_date,feed_end_date FROM feed_info LIMIT 1').fetchone()
    stamp=day.strftime('%Y%m%d')
    if coverage and ((coverage[0] and stamp<coverage[0]) or (coverage[1] and stamp>coverage[1])):
        raise ValueError(f'Date is outside published feed coverage ({coverage[0]}–{coverage[1]}).')
    start=start_dt.hour*3600+start_dt.minute*60+start_dt.second
    end=start+4*3600
    all_stops={r['stop_id']:dict(r) for r in db.execute('SELECT * FROM stops')}
    if not origin_ids or not destination_ids or any(x not in all_stops for x in origin_ids+destination_ids):
        raise ValueError('Choose an origin and destination from stop search.')
    if set(origin_ids)&set(destination_ids):raise ValueError('Origin and destination must be different stops.')
    db.execute('CREATE TEMP TABLE active(service_id TEXT, shift INTEGER, service_date TEXT)')
    for offset in [-1,0,1]:
        date=day+timedelta(days=offset)
        db.executemany('INSERT INTO active VALUES (?,?,?)',[(s,offset*86400,date.isoformat()) for s in active_services(db,date)])
    if not db.execute('SELECT 1 FROM active WHERE shift=0 LIMIT 1').fetchone():
        raise ValueError('No scheduled service for this date in the loaded feed. Choose a date within its coverage.')
    db.execute('CREATE INDEX active_service ON active(service_id)')
    db.execute('CREATE TEMP TABLE origins(id TEXT PRIMARY KEY)');db.executemany('INSERT INTO origins VALUES (?)',[(s,) for s in origin_ids])
    db.execute('CREATE TEMP TABLE destinations(id TEXT PRIMARY KEY)');db.executemany('INSERT INTO destinations VALUES (?)',[(s,) for s in destination_ids])
    modes={'any':(0,1,2,3),'bus':(3,),'rail':(0,1,2)}[mode]
    route_filter='r.route_type IN ('+','.join(str(m) for m in modes)+')'
    if excluded_routes:
        db.execute('CREATE TEMP TABLE excluded(id TEXT PRIMARY KEY)')
        db.executemany('INSERT INTO excluded VALUES (?)',[(r,) for r in set(excluded_routes)])
        route_filter+=' AND r.route_id NOT IN (SELECT id FROM excluded)'
    base=f'''SELECT t.trip_id,t.trip_headsign,t.shape_id,a.service_date,r.route_id,r.route_short_name,r.route_long_name,r.route_type,r.route_color,
        s.stop_id from_id,d.stop_id to_id,s.stop_sequence from_seq,d.stop_sequence to_seq,
        s.departure_secs+a.shift dep,d.arrival_secs+a.shift arr
        FROM trips t JOIN active a USING(service_id) JOIN routes r USING(route_id)
        JOIN stop_times s ON s.trip_id=t.trip_id JOIN stop_times d ON d.trip_id=t.trip_id AND d.stop_sequence>s.stop_sequence
        WHERE {route_filter} AND s.pickup_type=0 AND d.drop_off_type=0
        AND s.departure_secs+a.shift>=? AND d.arrival_secs+a.shift<=?'''
    first=[dict(r) for r in db.execute(base+' AND s.stop_id IN (SELECT id FROM origins)',(start,end))]
    results=[([r],0,0) for r in first if r['to_id'] in destination_ids]
    if max_transfers:
        second=defaultdict(list)
        for r in db.execute(base+' AND d.stop_id IN (SELECT id FROM destinations)',(start,end)):
            second[r['from_id']].append(dict(r))
        for rows in second.values():rows.sort(key=lambda r:r['dep'])
        times={s:[r['dep'] for r in rows] for s,rows in second.items()}
        # Transfers are at the same stop or explicitly declared by GTFS. No invented street crossings.
        links=defaultdict(dict)
        for s in second:links[s][s]=180
        for r in db.execute('SELECT * FROM transfers'):
            if r['transfer_type']==3:links[r['from_stop_id']].pop(r['to_stop_id'],None)
            else:links[r['from_stop_id']][r['to_stop_id']]=max(180,r['min_transfer_time'] or 0)
        for f in first:
            if f['to_id'] in destination_ids:continue
            for transfer_stop,buffer in links.get(f['to_id'],{}).items():
                if transfer_stop not in second:continue
                lo=bisect.bisect_left(times[transfer_stop],f['arr']+buffer)
                hi=bisect.bisect_right(times[transfer_stop],f['arr']+3600)
                for s in second[transfer_stop][lo:hi]:
                    if s['trip_id']==f['trip_id'] or s['route_id']==f['route_id']:continue
                    results.append(([f,s],s['dep']-f['arr'],buffer))
    results.sort(key=lambda x:(len(x[0]) if prefer=='fewer_transfers' else 0,x[0][-1]['arr'],len(x[0]),-x[0][0]['dep']))
    unique=[];seen=set()
    for legs,wait,buffer in results:
        signature=tuple((r['route_id'],r['from_id'],r['to_id']) for r in legs)
        if signature in seen:continue
        seen.add(signature)
        unique.append({'legs':[leg(db,r,all_stops,day) for r in legs],
            'departure':iso(day,legs[0]['dep']),'arrival':iso(day,legs[-1]['arr']),
            'duration_minutes':round((legs[-1]['arr']-legs[0]['dep'])/60),
            'transfers':len(legs)-1,'transfer_wait_minutes':round(wait/60),'minimum_transfer_minutes':buffer//60,
            'timing':'scheduled'})
        if len(unique)==6:break
    return unique

def iso(day,secs):
    return (datetime.combine(day,datetime.min.time(),TZ)+timedelta(seconds=secs)).isoformat()

def leg(db,r,stops,day):
    board=stops[r['from_id']];alight=stops[r['to_id']]
    between=[dict(s) for s in db.execute('''SELECT p.stop_id,p.stop_name,p.stop_lat,p.stop_lon FROM stop_times s JOIN stops p USING(stop_id)
        WHERE trip_id=? AND stop_sequence BETWEEN ? AND ? ORDER BY stop_sequence''',(r['trip_id'],r['from_seq'],r['to_seq']))]
    return {'trip_id':r['trip_id'],'service_date':r['service_date'],'route_id':r['route_id'],
        'route':r['route_short_name'],'name':r['route_long_name'],'color':r['route_color'],
        'mode':'bus' if r['route_type']==3 else 'rail','headsign':r['trip_headsign'],
        'from':board,'to':alight,'departure':iso(day,r['dep']),'arrival':iso(day,r['arr']),
        'stop_count':len(between)-1,'stops':between,
        'geometry':[[s['stop_lon'],s['stop_lat']] for s in between]}
