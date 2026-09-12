"""Reported positions from the same public endpoint used by METRO's trip planner."""
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
