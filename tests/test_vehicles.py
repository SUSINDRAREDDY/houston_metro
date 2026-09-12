import asyncio,time,httpx
from backend import vehicles

def test_only_fresh_positions(monkeypatch):
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
