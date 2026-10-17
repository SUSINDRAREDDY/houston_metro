"""METRO Transit Data GPS, with the public planner as a keyless fallback."""
import asyncio,time
import httpx
URL='https://houston-otp-server.ibi-transit.com/otp/gtfs/v1'
_cache={}
_lock=asyncio.Lock()
async def positions(route_id):
    async with _lock:
        now=time.time()
        if route_id in _cache and now-_cache[route_id][0]<20:return _cache[route_id][1]
        query='query($id:String!){route(id:$id){patterns{vehiclePositions{vehicleId label lat lon lastUpdated}}}}'
        try:
            async with httpx.AsyncClient(timeout=12) as c:
                r=await c.post(URL,json={'query':query,'variables':{'id':'Houston:'+route_id}})
                r.raise_for_status();raw=r.json()
            if raw.get('errors') or not raw.get('data',{}).get('route'):raise ValueError('Route unavailable')
            vehicles={};stale=0
            for p in raw['data']['route']['patterns']:
                for v in p.get('vehiclePositions') or []:
                    stamp=float(v.get('lastUpdated') or 0)
                    if stamp>1e12:stamp/=1000
                    if not -95.99<float(v['lon'])<-94 or not 29<float(v['lat'])<31:continue
                    if now-stamp>120 or stamp>now+30:stale+=1;continue
                    vehicles[str(v['vehicleId'])]={'id':str(v['vehicleId']),'label':v.get('label') or str(v['vehicleId']),'lat':v['lat'],'lon':v['lon'],'updated_at':stamp}
            result={'status':'live' if vehicles else 'no_positions','vehicles':list(vehicles.values()),'stale_hidden':stale,'checked_at':now,'route_id':route_id}
        except (httpx.HTTPError,ValueError,KeyError,TypeError):
            result={'status':'unavailable','vehicles':[],'checked_at':now,'route_id':route_id}
        _cache[route_id]=(now,result)
        return result

# The OData product has a separate subscription from GTFS Realtime.
import os
from datetime import datetime
from . import config as _config

TRANSIT_URL='https://api.ridemetro.org/data/Vehicles'
_public_positions=positions
_fleet_cache=None
_fleet_lock=asyncio.Lock()

def timestamp(value):
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None:raise ValueError('Missing timestamp timezone')
    return parsed.timestamp()

def parse_fleet(rows, now):
    """Use reported GPS only; exclude stale, unmonitored and future-trip rows."""
    found={}
    for row in rows:
        try:
            if row.get('IsMonitored') is not True:continue
            stamp=timestamp(row['VehicleReportTime'])
            lat,lon=float(row['Latitude']),float(row['Longitude'])
            if not -95.99<lon<-94 or not 29<lat<31:continue
            if not -30<=now-stamp<=120:continue
            start=timestamp(row['TripStartTimeUTC'])
            end=timestamp(row['TripEndTimeUTC'])
            delay=float(row.get('Delayseconds') or 0)
            if not start<=now<=end+max(0,delay):continue
            vid=str(row['VehicleId'])
            if not vid:continue
            route=str(row['RouteName']).strip()
            if not route.isdigit():continue
            item={'id':vid,'label':vid,'lat':lat,'lon':lon,'updated_at':stamp,
                  'route_id':route,'direction':row.get('DirectionName',''),
                  'destination':row.get('DestinationName',''),'trip_id':row.get('TripId',''),
                  '_start':start}
            if vid not in found or (stamp,start)>(found[vid]['updated_at'],found[vid]['_start']):
                found[vid]=item
        except (ValueError,KeyError,TypeError,OverflowError):continue
    return [{k:v for k,v in item.items() if k!='_start'} for item in found.values()]

async def positions(route_id):
    global _fleet_cache
    from .secrets import get
    key=get('METRO_TRANSIT_DATA_API_KEY')
    if not key:return await _public_positions(route_id)
    async with _fleet_lock:
        now=time.time()
        if _fleet_cache is None or now-_fleet_cache['checked_at']>=20:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    response=await client.get(TRANSIT_URL,headers={'Ocp-Apim-Subscription-Key':key,'Accept':'application/json'})
                    response.raise_for_status()
                    raw=response.json()
                if not isinstance(raw.get('value'),list):raise ValueError('Invalid fleet schema')
                # Do not silently treat a partial paginated feed as fleet-wide coverage.
                if raw.get('@odata.nextLink'):raise ValueError('Unexpected paginated fleet response')
                _fleet_cache={'checked_at':time.time(),'status':'ok','rows':raw['value']}
            except httpx.HTTPStatusError as exc:
                _fleet_cache={'checked_at':time.time(),'status':'unauthorized' if exc.response.status_code in (401,403) else 'unavailable','rows':[]}
            except (httpx.HTTPError,ValueError,TypeError,AttributeError):
                _fleet_cache={'checked_at':time.time(),'status':'unavailable','rows':[]}
        now=time.time()
        fleet=parse_fleet(_fleet_cache['rows'],now)
        matches=[v for v in fleet if v['route_id'].lstrip('0')==route_id.lstrip('0')]
        status=_fleet_cache['status']
        return {'route_id':route_id,'status':('live' if matches else 'no_positions') if status=='ok' else status,
                'vehicles':matches,'checked_at':_fleet_cache['checked_at'],'source':'metro_transit_data',
                'scope':'Current vehicles on this route, not a prediction of the selected future journey'}
