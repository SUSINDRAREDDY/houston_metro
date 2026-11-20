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


def test_direct_trip_keeps_date_and_preferences():
    from datetime import datetime

    now = datetime(2026, 11, 19, 16, 0, tzinfo=intent.TZ)
    result = intent.parse_direct('UH South to Central Station tomorrow at noon by rail, no transfers', now)
    assert result == {
        'intent': {
            'origin': 'UH South', 'destination': 'Central Station',
            'date': '2026-11-20', 'time': '12:00', 'mode': 'rail',
            'max_transfers': 0, 'prefer': 'fastest', 'avoid_alerts': False,
            'clarification': None,
        },
        'leave_now': False,
        'model': 'metroai-direct',
    }
    preset = intent.parse_direct('UH to Downtown, leave now, fewer transfers', now)
    assert preset['leave_now'] is True
    assert preset['intent']['prefer'] == 'fewer_transfers'


def test_direct_trip_leaves_complex_and_ambiguous_requests_to_ai():
    from datetime import datetime

    now = datetime(2026, 11, 19, 16, 0, tzinfo=intent.TZ)
    for prompt in ('UH to Downtown at 5', 'UH to Downtown arrive by 5 PM',
                   'UH to Downtown without walking', 'UH to Downtown, tomorrow, leave now'):
        assert intent.parse_direct(prompt, now) is None


def test_interpret_uses_direct_parser_for_known_stops(monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace
    from backend import main

    monkeypatch.setattr(main.demo_trace, 'enabled', lambda: False)
    monkeypatch.setattr(main.routing, 'connect', lambda: nullcontext(object()))
    monkeypatch.setattr(main.routing, 'stop_search', lambda db, q: [object()] if q in ('UH', 'Downtown') else [])
    monkeypatch.setattr(main, 'rate', main.defaultdict(main.deque))
    calls = []

    async def provider(text):
        calls.append(text)
        return {'model': 'test-provider'}

    monkeypatch.setattr(intent, 'parse', provider)
    request = SimpleNamespace(client=SimpleNamespace(host='test'))
    known = asyncio.run(main.interpret(main.ParseRequest(text='UH to Downtown tomorrow at noon'), request))
    assert known['model'] == 'metroai-direct'
    assert not calls
    unknown = asyncio.run(main.interpret(main.ParseRequest(text='UH to unknown station'), request))
    assert unknown['model'] == 'test-provider'
    assert calls == ['UH to unknown station']


def test_misspelled_fannin_trip_uses_real_stop_lookup_without_ai(monkeypatch):
    import sqlite3
    from contextlib import nullcontext
    from types import SimpleNamespace
    from backend import main

    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE stops(stop_id TEXT,stop_code TEXT,stop_name TEXT,stop_lat REAL,stop_lon REAL,location_type TEXT)')
    for i,name in enumerate(['Uh South University Oaks NB','Fannin South Stn NB',
                             'Fannin South Stn SB','Fannin St @ Southmore Blvd']):
        db.execute('INSERT INTO stops VALUES (?,?,?,?,?,?)',(str(i),str(i),name,29.7,-95.4,'0'))
    monkeypatch.setattr(main.demo_trace,'enabled',lambda:False)
    monkeypatch.setattr(main.routing,'connect',lambda:nullcontext(db))
    monkeypatch.setattr(main,'rate',main.defaultdict(main.deque))
    async def unavailable_provider(text):
        raise AssertionError('A recognized station trip must not call the AI provider')
    monkeypatch.setattr(intent,'parse',unavailable_provider)
    request=SimpleNamespace(client=SimpleNamespace(host='test'))
    result=asyncio.run(main.interpret(main.ParseRequest(text='uh to fanin south'),request))
    assert result['model']=='metroai-direct'
    assert result['intent']['origin']=='uh'
    assert result['intent']['destination']=='fanin south'
    assert result['leave_now'] is True
    assert len(main.routing.stop_search(db,result['intent']['destination']))==2
    db.close()
