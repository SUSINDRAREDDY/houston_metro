from datetime import datetime,timedelta
import asyncio
import pytest
from fastapi import HTTPException
from backend import connected,routing

def itinerary(now):
    def leg(mode,a,b):
        return {'mode':mode,'startTime':(now.timestamp()+a)*1000,'endTime':(now.timestamp()+b)*1000,
                'distance':100,'from':{'name':'A','lat':29.7,'lon':-95.3},'to':{'name':'B','lat':29.71,'lon':-95.31},
                'route':None if mode=='WALK' else {'gtfsId':'Houston:002' if mode=='BUS' else 'Houston:700','shortName':'2','longName':'Test'},
                'legGeometry':{'points':''},'steps':[]}
    return {'startTime':now.timestamp()*1000,'endTime':(now.timestamp()+1600)*1000,'duration':1600,
            'legs':[leg('WALK',0,100),leg('BUS',200,800),leg('WALK',800,950),leg('TRAM',1100,1500),leg('WALK',1500,1600)]}

def test_walk_bus_rail_transfer_count_and_constraints():
    now=datetime.now(routing.TZ);it=itinerary(now)
    j=connected.convert(it,now,1,'any',[],False)
    assert j['transfers']==1 and j['walking_meters']==300
    assert [l['mode'] for l in j['legs']]==['walk','bus','walk','rail','walk']
    assert connected.convert(it,now,0,'any',[],False) is None
    assert connected.convert(it,now,2,'bus',[],False) is None
    assert connected.convert(it,now,2,'any',['700'],False) is None
    assert connected.convert(it,now+timedelta(minutes=1),2,'any',[],False) is None

def test_past_departure_rejected_before_planning():
    from backend.main import JourneyRequest,journeys
    body=JourneyRequest(origin_ids=['25080'],destination_ids=['25054'],departure=datetime.now(routing.TZ)-timedelta(hours=5))
    with pytest.raises(HTTPException) as error:asyncio.run(journeys(body))
    assert error.value.status_code==422 and 'passed' in error.value.detail

def test_polyline():
    assert connected.geometry('_p~iF~ps|U_ulLnnqC_mqNvxq`@')==[[-120.2,38.5],[-120.95,40.7],[-126.453,43.252]]

def test_three_vehicle_changes_and_walking_limit():
    now=datetime.now(routing.TZ);it=itinerary(now)
    # Four boardings = three changes, irrespective of intervening walks.
    for _ in range(2):
        leg=dict(it['legs'][1]);leg['startTime']=it['endTime'];leg['endTime']=it['endTime']+600000
        it['legs'].append(leg);it['endTime']=leg['endTime'];it['duration']+=600
    assert connected.convert(it,now,3,'any',[],False)['transfers']==3
    assert connected.convert(it,now,2,'any',[],False) is None
    it['legs'][0]['distance']=1300
    assert connected.convert(it,now,3,'any',[],False) is None

def test_no_options_and_upstream_error_are_distinct(monkeypatch):
    import httpx
    original=httpx.AsyncClient
    point={'stop_lat':29.7,'stop_lon':-95.3}
    def run():return asyncio.run(connected.plan(point,point,datetime.now(routing.TZ),'any',1,'fastest'))
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'data':{'plan':{'itineraries':[]}}})),**kw))
    assert run()==[]
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(lambda r:httpx.Response(503)),**kw))
    with pytest.raises(ValueError,match='unavailable'):run()
