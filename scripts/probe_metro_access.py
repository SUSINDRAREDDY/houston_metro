"""Bounded official-endpoint checks. Never serialize keys or keyed request URLs."""
import json,sys,time
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import httpx
from dotenv import dotenv_values
from google.transit import gtfs_realtime_pb2
ROOT=Path(__file__).resolve().parent.parent
key=dotenv_values(ROOT/'.env').get('METRO_API_KEY')
if not key:raise SystemExit('METRO_API_KEY missing in local .env')
checks=[]
with httpx.Client(timeout=35) as c:
 for path,auth in [('/GtfsRealtime/TripUpdates','none'),('/GtfsRealtime/TripUpdates','header'),('/data/Vehicles','header'),('/data/Vehicles','query'),('/data/Routes','header'),('/v2alerts/alerts','header')]:
  stamp=datetime.now(timezone.utc).isoformat()
  try:
   r=c.get('https://api.ridemetro.org'+path,headers={'Ocp-Apim-Subscription-Key':key} if auth=='header' else {},params={'subscription-key':key} if auth=='query' else {})
   entry={'at':stamp,'path':path,'auth':auth,'status':r.status_code,'bytes':len(r.content)}
   if path.endswith('TripUpdates') and r.status_code==200:
    f=gtfs_realtime_pb2.FeedMessage();f.ParseFromString(r.content)
    entry.update(entities=len(f.entity),trip_updates=sum(e.HasField('trip_update') for e in f.entity),vehicle_positions=sum(e.HasField('vehicle') for e in f.entity),feed_timestamp=f.header.timestamp,feed_age_seconds=round(time.time()-f.header.timestamp),routes=dict(Counter(e.trip_update.trip.route_id for e in f.entity if e.HasField('trip_update'))))
   elif r.status_code!=200:
    try:entry['message']=r.json().get('message','')
    except ValueError:pass
   checks.append(entry)
  except httpx.HTTPError as e:checks.append({'at':stamp,'path':path,'auth':auth,'error_type':type(e).__name__})
 q='{routes{gtfsId patterns{vehiclePositions{vehicleId lat lon lastUpdated}}}}'
 r=c.post('https://houston-otp-server.ibi-transit.com/otp/gtfs/v1',json={'query':q});data=r.json();routes=data.get('data',{}).get('routes',[])
 checks.append({'at':datetime.now(timezone.utc).isoformat(),'path':'public planner GraphQL routes','status':r.status_code,'routes':len(routes),'positions':sum(len(p.get('vehiclePositions') or []) for x in routes for p in x['patterns'])})
p=ROOT/'data'/'metro-access-probe.json';p.write_text(json.dumps(checks,indent=2));print(json.dumps([{k:v for k,v in x.items() if k!='routes' or isinstance(v,int)} for x in checks],indent=2))
