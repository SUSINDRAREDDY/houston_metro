"""Connected walking/transit itineraries from METRO's own journey planner."""
import asyncio
from datetime import datetime,timedelta
import httpx
from .routing import TZ
from . import demo_trace
URL='https://houston-otp-server.ibi-transit.com/otp/gtfs/v1'
class PlannerUnavailable(ValueError):
    pass
QUERY='''query($from:String!,$to:String!,$date:String!,$time:String!,$modes:[TransportMode]) {
plan(fromPlace:$from,toPlace:$to,date:$date,time:$time,transportModes:$modes,numItineraries:12){
itineraries{duration startTime endTime legs{mode startTime endTime distance realTime
from{name lat lon} to{name lat lon} route{gtfsId shortName longName}
legGeometry{points} steps{distance relativeDirection streetName}
alerts{alertHeaderText alertDescriptionText}}}}}'''

def geometry(encoded):
    result=[];i=0;lat=lon=0
    while i<len(encoded):
        vals=[]
        for _ in range(2):
            value=shift=0
            while True:
                b=ord(encoded[i])-63;i+=1;value|=(b&31)<<shift;shift+=5
                if b<32:break
                if shift>35:raise ValueError('Invalid route geometry')
            vals.append(~(value>>1) if value&1 else value>>1)
        lat+=vals[0];lon+=vals[1];result.append([lon/1e5,lat/1e5])
    return result

def convert(it, departure, max_transfers, mode, excluded, avoid):
    legs=[];alerts=[]
    for index,l in enumerate(it['legs']):
        walk=l['mode']=='WALK'
        if not walk and l['mode'] not in ('BUS','TRAM','RAIL','SUBWAY'):return None
        actual='walk' if walk else 'bus' if l['mode']=='BUS' else 'rail'
        if not walk and mode!='any' and mode!=actual:return None
        r=l.get('route') or {};rid=(r.get('gtfsId') or '').split(':')[-1]
        if rid in excluded:return None
        for a in l.get('alerts') or []:
            alerts.append({'id':f'planner-{index}-{len(alerts)}','header':a.get('alertHeaderText') or 'Service alert','description':a.get('alertDescriptionText') or '','routes':[rid],'effect':'Service alert'})
        def point(p):return {'stop_id':'','stop_code':'','stop_name':p['name'],'stop_lat':p['lat'],'stop_lon':p['lon']}
        iso=lambda ms:datetime.fromtimestamp(ms/1000,TZ).isoformat()
        legs.append({'route_id':rid,'route':r.get('shortName') or '', 'name':r.get('longName') or '',
            'mode':actual,'headsign':l['to']['name'],'from':point(l['from']),'to':point(l['to']),
            'departure':iso(l['startTime']),'arrival':iso(l['endTime']),'stop_count':None,'stops':[],
            'geometry':geometry(l['legGeometry']['points']),'distance_meters':round(l['distance']),
            'steps':l.get('steps') or [],'realtime':bool(l.get('realTime'))})
    rides=[l for l in legs if l['mode']!='walk']
    if not rides or len(rides)-1>max_transfers or (avoid and alerts):return None
    if it['startTime']/1000<departure.timestamp() or it['endTime']/1000>departure.timestamp()+4*3600:return None
    walking=sum(l['distance_meters'] for l in legs if l['mode']=='walk')
    if walking>1200:return None
    return {'legs':legs,'departure':legs[0]['departure'],'arrival':legs[-1]['arrival'],
            'duration_minutes':round(it['duration']/60),'transfers':len(rides)-1,
            'transfer_wait_minutes':0,'walking_meters':walking,'timing':'live_updates' if any(l['realtime'] for l in rides) else 'scheduled',
            'source':'METRO trip planner','alerts':alerts}

def travel_modes(journey):
    modes={leg['mode'] for leg in journey['legs'] if leg['mode']!='walk'}
    return 'Bus + rail' if modes=={'bus','rail'} else 'Bus' if modes=={'bus'} else 'Rail'


def route_signature(journey):
    # Keep different lines and boarding/alighting places, not repeated departures.
    def point(stop):
        return (round(float(stop['stop_lat']),4),round(float(stop['stop_lon']),4))
    return tuple((leg['mode'],leg['route_id'],point(leg['from']),point(leg['to']))
                 for leg in journey['legs'] if leg['mode']!='walk')


def choose_alternatives(journeys,prefer,limit=6):
    if not journeys:return []
    arrival=lambda j:datetime.fromisoformat(j['arrival']).timestamp()
    walk=lambda j:j.get('walking_meters',0)
    rank=lambda j:(j['transfers'] if prefer=='fewer_transfers' else 0,arrival(j),walk(j))
    unique={}
    for journey in sorted(journeys,key=rank):unique.setdefault(route_signature(journey),journey)
    candidates=sorted(unique.values(),key=rank)
    fastest=min(candidates,key=lambda j:(arrival(j),walk(j)))
    fewest=min(candidates,key=lambda j:(j['transfers'],arrival(j),walk(j)))
    least_walk=min(candidates,key=lambda j:(walk(j),arrival(j)))
    selected=[];seen=set()
    def add(journey):
        key=route_signature(journey)
        if key not in seen and len(selected)<limit:selected.append(journey);seen.add(key)
    add(candidates[0])
    for journey in (fastest,fewest,least_walk):add(journey)
    for kind in ('Bus','Rail','Bus + rail'):
        match=next((j for j in candidates if travel_modes(j)==kind),None)
        if match is not None:add(match)
    for journey in candidates:add(journey)
    varied_transfers=len({j['transfers'] for j in candidates})>1
    varied_walk=len({walk(j) for j in candidates})>1
    result=[]
    for journey in sorted(selected,key=rank):
        highlights=[]
        if arrival(journey)==arrival(fastest):highlights.append('Fastest arrival')
        if varied_transfers and journey['transfers']==fewest['transfers']:highlights.append('Fewest transfers')
        if varied_walk and walk(journey)==walk(least_walk):highlights.append('Least walking')
        result.append({**journey,'travel_modes':travel_modes(journey),'highlights':highlights})
    return result


async def plan(origin,dest,departure,mode,max_transfers,prefer,excluded=(),avoid=False):
    at=departure.astimezone(TZ)
    if at.microsecond:at=at.replace(microsecond=0)+timedelta(seconds=1)
    profiles={'any':[{'mode':'TRANSIT'}],'bus':[{'mode':'BUS'}],'rail':[{'mode':'TRAM'},{'mode':'RAIL'},{'mode':'SUBWAY'}]}
    async with httpx.AsyncClient(timeout=httpx.Timeout(15,connect=4)) as client:
        async def search(profile):
            variables={'from':f"{origin['stop_lat']},{origin['stop_lon']}",'to':f"{dest['stop_lat']},{dest['stop_lon']}",'date':at.strftime('%Y-%m-%d'),'time':at.strftime('%H:%M:%S'),'modes':[{'mode':'WALK'}]+profiles[profile]}
            demo_trace.event('EXTERNAL_REQUEST',provider='METRO planner',profile=profile,coordinates_and_time=variables)
            response=await client.post(URL,json={'query':QUERY,'variables':variables});response.raise_for_status();data=response.json()
            if data.get('errors'):raise ValueError('Planner rejected the request')
            itineraries=data['data']['plan']['itineraries']
            # Validate against the requested sub-search as well as rider constraints.
            result=[j for it in itineraries if (j:=convert(it,departure,max_transfers,profile,excluded,avoid))]
            demo_trace.event('EXTERNAL_RESULT',provider='METRO planner',profile=profile,itineraries_received=len(itineraries),itineraries_matching_filters=len(result))
            return result
        batches=await asyncio.gather(*(search(profile) for profile in (('any','bus','rail') if mode=='any' else (mode,))),return_exceptions=True)
    incomplete=any(isinstance(batch,BaseException) for batch in batches)
    result=[journey for batch in batches if isinstance(batch,list) for journey in batch]
    if incomplete and not result:
        raise PlannerUnavailable('Connected journey planner is unavailable. Try again or turn off walking to search local schedules.') from None
    for journey in result:
        journey['legs'][0]['from']['stop_name']=origin['stop_name']
        journey['legs'][-1]['to']['stop_name']=dest['stop_name']
        journey['alternatives_incomplete']=incomplete
    return choose_alternatives(result,prefer)
