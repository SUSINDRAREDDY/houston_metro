"""Connected walking/transit itineraries from METRO's own journey planner."""
from datetime import datetime,timedelta
import httpx
from .routing import TZ
URL='https://houston-otp-server.ibi-transit.com/otp/gtfs/v1'
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

async def plan(origin,dest,departure,mode,max_transfers,prefer,excluded=(),avoid=False):
    at=departure.astimezone(TZ)
    if at.microsecond:at=at.replace(microsecond=0)+timedelta(seconds=1)
    modes=[{'mode':'WALK'}]+([{'mode':'TRANSIT'}] if mode=='any' else [{'mode':'BUS'}] if mode=='bus' else [{'mode':'TRAM'},{'mode':'RAIL'},{'mode':'SUBWAY'}])
    variables={'from':f"{origin['stop_lat']},{origin['stop_lon']}",'to':f"{dest['stop_lat']},{dest['stop_lon']}",'date':at.strftime('%Y-%m-%d'),'time':at.strftime('%H:%M:%S'),'modes':modes}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response=await client.post(URL,json={'query':QUERY,'variables':variables});response.raise_for_status();data=response.json()
        if data.get('errors'):raise ValueError('Planner rejected the request')
        itineraries=data['data']['plan']['itineraries']
        result=[j for it in itineraries if (j:=convert(it,departure,max_transfers,mode,excluded,avoid))]
    except (httpx.HTTPError,ValueError,KeyError,TypeError,IndexError):
        raise ValueError('Connected journey planner is unavailable. Try again or turn off walking to search local schedules.') from None
    for journey in result:
        journey['legs'][0]['from']['stop_name']=origin['stop_name']
        journey['legs'][-1]['to']['stop_name']=dest['stop_name']
    result.sort(key=lambda j:(j['transfers'] if prefer=='fewer_transfers' else 0,j['arrival'],j['walking_meters']))
    return result[:6]
