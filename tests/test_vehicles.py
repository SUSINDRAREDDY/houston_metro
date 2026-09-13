import asyncio,time,httpx
from backend import vehicles

def test_only_fresh_positions(monkeypatch):
    monkeypatch.delenv("METRO_TRANSIT_DATA_API_KEY",raising=False)
    original=httpx.AsyncClient
    now=time.time()
    def handle(req):
        return httpx.Response(200,json={'data':{'route':{'patterns':[{'vehiclePositions':[
          {'vehicleId':'fresh','label':'Bus','lat':29.75,'lon':-95.36,'lastUpdated':now},
          {'vehicleId':'old','label':'Bus','lat':29.75,'lon':-95.36,'lastUpdated':now-600}]}]}}})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    vehicles._cache.clear()
    r=asyncio.run(vehicles.positions('900'))
    assert r['status']=='live' and len(r['vehicles'])==1 and r['stale_hidden']==1
    vehicles._cache.clear()

from datetime import datetime,timezone

def record(now, **updates):
    iso=lambda v:datetime.fromtimestamp(v,timezone.utc).isoformat()
    row={'VehicleId':'42','RouteName':'082','IsMonitored':True,'Latitude':29.75,'Longitude':-95.36,
         'VehicleReportTime':iso(now-10),'TripStartTimeUTC':iso(now-600),'TripEndTimeUTC':iso(now+600)}
    row.update(updates)
    return row

def test_monitored_current_deduplicated():
    now=time.time()
    future=record(now,TripStartTimeUTC=datetime.fromtimestamp(now+500,timezone.utc).isoformat(),RouteName='002')
    rows=[record(now),record(now),future,record(now,VehicleId='old',VehicleReportTime='2020-01-01T00:00:00Z'),record(now,VehicleId='scheduled',IsMonitored=False),record(now,VehicleId='bad',Latitude=0)]
    out=vehicles.parse_fleet(rows,now)
    assert len(out)==1 and out[0]['route_id']=='082'

def test_fleet_shared_across_routes(monkeypatch):
    monkeypatch.setenv('METRO_TRANSIT_DATA_API_KEY','test')
    monkeypatch.setattr(vehicles,'_fleet_cache',None)
    original=httpx.AsyncClient;calls=[]
    def handle(req):
        calls.append(req)
        return httpx.Response(200,json={'value':[record(time.time())]})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    async def check():
        a=await vehicles.positions('082');b=await vehicles.positions('002')
        assert a['status']=='live' and b['status']=='no_positions'
    asyncio.run(check())
    assert len(calls)==1

def test_unauthorized_distinct_from_empty(monkeypatch):
    monkeypatch.setenv('METRO_TRANSIT_DATA_API_KEY','test')
    monkeypatch.setattr(vehicles,'_fleet_cache',None)
    original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(lambda req:httpx.Response(401)),**kw))
    assert asyncio.run(vehicles.positions('082'))['status']=='unauthorized'
