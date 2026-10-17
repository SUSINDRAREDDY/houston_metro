import asyncio,json
import httpx
from backend import intent

def test_transient_failure_retries_free_only(monkeypatch):
    monkeypatch.setenv('OPENROUTER_REASONING_EFFORT','none')
    monkeypatch.setenv('OPENROUTER_API_KEY','test')
    monkeypatch.setenv('OPENROUTER_MODEL','openrouter/free')
    calls=[]
    original=httpx.AsyncClient
    def handle(request):
        body=json.loads(request.content);calls.append(body)
        assert body['model']=='openrouter/free'
        assert body['reasoning']=={'effort':'none'}
        assert body['provider']['max_price']=={'prompt':0,'completion':0}
        if len(calls)==1:return httpx.Response(503)
        return httpx.Response(200,json={'model':'example:free','choices':[{'message':{'content':json.dumps({'origin':'UH','destination':'Downtown','date':'2026-09-12','time':'17:00','mode':'any','max_transfers':1,'prefer':'fastest','avoid_alerts':False,'clarification':None})}}]})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    result=asyncio.run(intent.parse('UH to Downtown after 5 PM'))
    assert result['intent']['time']=='17:00' and len(calls)==2

def test_paid_model_rejected(monkeypatch):
    monkeypatch.setenv('OPENROUTER_MODEL','paid/model')
    import pytest
    with pytest.raises(ValueError,match='Only OpenRouter free'):
        asyncio.run(intent.parse('UH to downtown'))

def test_unspecified_time_cannot_copy_five_pm(monkeypatch):
    from datetime import datetime
    monkeypatch.setenv('OPENROUTER_API_KEY','test')
    monkeypatch.setenv('OPENROUTER_MODEL','openrouter/free')
    original=httpx.AsyncClient
    def handle(request):
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'origin':'UH','destination':'Downtown','date':'2026-01-01','time':'17:00','mode':'any','max_transfers':1,'prefer':'fastest','avoid_alerts':False,'clarification':None})}}]})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    before=datetime.now(intent.TZ)
    result=asyncio.run(intent.parse('uh to downtown'))
    assert result['leave_now'] is True
    assert result['intent']['date']==before.date().isoformat()
    assert result['intent']['time']==before.strftime('%H:%M')
