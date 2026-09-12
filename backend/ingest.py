"""Validated GTFS snapshot import. Publish with atomic rename; retain last good feed."""
import csv
import hashlib
import io
import json
import os
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import httpx
from .config import DATA, DB, GTFS_URL

TABLES = {
    'agency': ['agency_id','agency_name','agency_timezone'],
    'stops': ['stop_id','stop_code','stop_name','stop_lat','stop_lon','location_type','parent_station'],
    'routes': ['route_id','route_short_name','route_long_name','route_type','route_color'],
    'trips': ['route_id','service_id','trip_id','trip_headsign','direction_id','shape_id'],
    'stop_times': ['trip_id','arrival_time','departure_time','stop_id','stop_sequence','pickup_type','drop_off_type','shape_dist_traveled'],
    'calendar': ['service_id','monday','tuesday','wednesday','thursday','friday','saturday','sunday','start_date','end_date'],
    'calendar_dates': ['service_id','date','exception_type'],
    'shapes': ['shape_id','shape_pt_lat','shape_pt_lon','shape_pt_sequence','shape_dist_traveled'],
    'transfers': ['from_stop_id','to_stop_id','transfer_type','min_transfer_time'],
    'feed_info': ['feed_publisher_name','feed_start_date','feed_end_date','feed_version'],
}
INTEGER = {'stop_sequence','shape_pt_sequence','pickup_type','drop_off_type','route_type','transfer_type','min_transfer_time','exception_type'}
REAL = {'stop_lat','stop_lon','shape_pt_lat','shape_pt_lon','shape_dist_traveled'}

def seconds(value):
    h,m,s = map(int, value.split(':'))
    if h < 0 or not 0 <= m < 60 or not 0 <= s < 60:
        raise ValueError('Invalid GTFS time')
    return h*3600 + m*60 + s

def import_gtfs(path: Path, target: Path = DB):
    stage = target.with_suffix('.building.sqlite3')
    stage.unlink(missing_ok=True)
    counts = {}
    try:
        with zipfile.ZipFile(path) as z, sqlite3.connect(stage) as db:
            names = {Path(n).name:n for n in z.namelist()}
            for required in ['stops','routes','trips','stop_times','agency']:
                if required+'.txt' not in names: raise ValueError(f'Missing {required}.txt')
            if sum(i.file_size for i in z.infolist()) > 2_000_000_000:
                raise ValueError('GTFS exceeds import size limit')
            if 'frequencies.txt' in names and len(z.read(names['frequencies.txt']).splitlines()) > 1:
                raise ValueError('Frequency-based trips require expansion; refusing incomplete import')
            for table,cols in TABLES.items():
                defs = [f'{c} '+('INTEGER' if c in INTEGER else 'REAL' if c in REAL else 'TEXT') for c in cols]
                if table == 'stop_times': defs += ['arrival_secs INTEGER','departure_secs INTEGER']
                db.execute(f'CREATE TABLE {table} ({",".join(defs)})')
                count=0
                if table+'.txt' in names:
                    with z.open(names[table+'.txt']) as f:
                        reader=csv.DictReader(io.TextIOWrapper(f,encoding='utf-8-sig'))
                        batch=[]
                        for row in reader:
                            vals=[row.get(c,'') or (0 if c in INTEGER else None if c in REAL else '') for c in cols]
                            if table=='stop_times':
                                if not row.get('arrival_time') or not row.get('departure_time'):
                                    raise ValueError('Untimed stops require interpolation; refusing incomplete import')
                                vals += [seconds(row['arrival_time']),seconds(row['departure_time'])]
                            batch.append(vals); count+=1
                            if len(batch)==10000:
                                db.executemany(f'INSERT INTO {table} VALUES ({",".join("?" for _ in vals)})',batch);batch=[]
                        if batch: db.executemany(f'INSERT INTO {table} VALUES ({",".join("?" for _ in batch[0])})',batch)
                counts[table]=count
            for table,key in [('stops','stop_id'),('routes','route_id'),('trips','trip_id')]:
                if not counts[table]: raise ValueError(f'Empty {table}')
                db.execute(f'CREATE UNIQUE INDEX {table}_id ON {table}({key})')
            db.executescript('''
                CREATE UNIQUE INDEX times_trip_sequence ON stop_times(trip_id,stop_sequence);
                CREATE INDEX times_stop_departure ON stop_times(stop_id,departure_secs);
                CREATE INDEX trips_service ON trips(service_id);
                CREATE INDEX shapes_sequence ON shapes(shape_id,shape_pt_sequence);
                CREATE INDEX dates_date ON calendar_dates(date);
                CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);
            ''')
            checks=[
                'SELECT 1 FROM stop_times s LEFT JOIN stops p USING(stop_id) WHERE p.stop_id IS NULL LIMIT 1',
                'SELECT 1 FROM stop_times s LEFT JOIN trips t USING(trip_id) WHERE t.trip_id IS NULL LIMIT 1',
                'SELECT 1 FROM trips t LEFT JOIN routes r USING(route_id) WHERE r.route_id IS NULL LIMIT 1',
                'SELECT 1 FROM stop_times WHERE arrival_secs>departure_secs LIMIT 1',
                '''SELECT 1 FROM (SELECT arrival_secs,lag(departure_secs) OVER(PARTITION BY trip_id ORDER BY stop_sequence) prev FROM stop_times) WHERE arrival_secs<prev LIMIT 1''',
            ]
            if any(db.execute(q).fetchone() for q in checks): raise ValueError('GTFS integrity check failed')
            if not counts['calendar'] and not counts['calendar_dates']: raise ValueError('No service calendar')
            zones={r[0] for r in db.execute('SELECT agency_timezone FROM agency')}
            if zones != {'America/Chicago'}: raise ValueError(f'Unexpected timezone: {zones}')
            meta={'imported_at':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source':GTFS_URL,'counts':counts}
            db.executemany('INSERT INTO metadata VALUES (?,?)',[(k,json.dumps(v)) for k,v in meta.items()])
            db.execute('ANALYZE');db.commit()
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('SQLite integrity failure')
        os.replace(stage,target)
        return meta
    except BaseException:
        stage.unlink(missing_ok=True)
        raise

def download():
    path=DATA/'gtfs.download.zip'
    with httpx.stream('GET',GTFS_URL,follow_redirects=True,timeout=180) as r:
        r.raise_for_status()
        with path.open('wb') as f:
            size=0
            for chunk in r.iter_bytes():
                size+=len(chunk)
                if size>200_000_000: raise ValueError('GTFS download exceeds limit')
                f.write(chunk)
    if not zipfile.is_zipfile(path): raise ValueError('GTFS source did not return a ZIP; previous data preserved')
    result=import_gtfs(path)
    os.replace(path,DATA/'gtfs.zip')
    return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--file',type=Path);args=p.parse_args()
    print(json.dumps(import_gtfs(args.file) if args.file else download(),indent=2))
