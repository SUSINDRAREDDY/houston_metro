"""Bounded, repeatable investigation of METRO public realtime availability."""
import json,sys
from pathlib import Path
from datetime import datetime,timezone
import httpx
ROOT=Path(__file__).resolve().parent.parent
URL='https://houston-otp-server.ibi-transit.com/otp/gtfs/v1'
ROUTES=['002','025','082','102','008','054','065','269','433','700','800','900']
with httpx.Client(timeout=35) as c:
    def query(q):
        r=c.post(URL,json={'query':q});r.raise_for_status();d=r.json()
        if d.get('errors'):raise ValueError(d['errors'])
        return d['data']
    allroutes=query('{routes{gtfsId shortName longName mode patterns{vehiclePositions{vehicleId lat lon lastUpdated}}}}')['routes']
    detail=[]
    for route in ROUTES:
        data=query('{route(id:'+json.dumps('Houston:'+route)+'){patterns{stops{gtfsId name}}}}')['route']
        if not data:continue
        stops={}
        for p in data['patterns'][:2]:
            ss=p['stops']
            if ss:stops[ss[len(ss)//2]['gtfsId']]=ss[len(ss)//2]['name']
        for sid,name in stops.items():
            d=query('{stop(id:'+json.dumps(sid)+'){stoptimesForPatterns(numberOfDepartures:10){pattern{route{shortName}}stoptimes{scheduledDeparture realtimeDeparture realtime realtimeState serviceDay headsign}}}}')['stop']
            times=[t for p in d['stoptimesForPatterns'] if p['pattern']['route']['shortName']==route for t in p['stoptimes']]
            detail.append({'route':route,'stop_id':sid,'stop_name':name,'departures':len(times),'realtime':sum(bool(t['realtime']) for t in times),'states':sorted({t['realtimeState'] for t in times}),'times':times})
    api=c.get('https://api.ridemetro.org/GtfsRealtime/TripUpdates')
    result={'checked_at':datetime.now(timezone.utc).isoformat(),'endpoint':URL,'routes':allroutes,'stop_checks':detail,'subscription_tripupdates_status':api.status_code}
    path=ROOT/'data'/'realtime-investigation.json';path.write_text(json.dumps(result,indent=2))
    print('routes',len(allroutes),'patterns',sum(len(r['patterns']) for r in allroutes),'positions',sum(len(p['vehiclePositions']) for r in allroutes for p in r['patterns']))
    for d in detail:print({k:v for k,v in d.items() if k!='times'})
    print('subscription trip updates',api.status_code,'evidence',path)
