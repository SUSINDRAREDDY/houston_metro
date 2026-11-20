import asyncio,json
from datetime import datetime,timedelta
from types import SimpleNamespace
import httpx,pytest
from backend import intent
ASYNC_CLIENT=httpx.AsyncClient
from test_stations import catalog

NOW=datetime(2026,11,20,10,0,tzinfo=intent.TZ)

def extracted(**changes):
    return {'origin':'UH','destination':'Fannin South','date':None,'time':None,'date_text':None,'time_text':None,
            'mode':'any','max_transfers':1,'prefer':'fastest','avoid_alerts':False,'allow_walking':True,'issue':None,**changes}

def fake_provider(monkeypatch,responses):
    monkeypatch.delenv('SECRET_PROJECT_ID',raising=False)
    monkeypatch.setenv('OPENROUTER_API_KEY','test')
    monkeypatch.setenv('OPENROUTER_MODEL','openrouter/free')
    monkeypatch.setattr(intent,'datetime',type('Clock',(datetime,),{'now':classmethod(lambda cls,tz=None:NOW)}))
    calls=[];original=ASYNC_CLIENT
    def handle(request):
        body=json.loads(request.content);calls.append(body)
        assert body['model']=='openrouter/free'
        assert body['provider']['max_price']=={'prompt':0,'completion':0}
        assert body['provider']['require_parameters'] is True
        response=responses[min(len(calls)-1,len(responses)-1)]
        if isinstance(response,int):return httpx.Response(response)
        assert 'response_format' not in body
        assert body['tool_choice']['function']['name']=='submit_trip_request'
        return httpx.Response(200,json={'model':'example:free','choices':[{'message':{'tool_calls':[{'type':'function','function':{'name':'submit_trip_request','arguments':json.dumps(response)}}]}}]})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    return calls

def test_transient_failure_retries_free_only(monkeypatch):
    monkeypatch.setenv('OPENROUTER_REASONING_EFFORT','none')
    calls=fake_provider(monkeypatch,[503,extracted(time='17:00',time_text='5 PM')])
    result=asyncio.run(intent.parse('UH to Fannin South after 5 PM',station_names=['Fannin South Stn NB']))
    assert result['intent']['time']=='17:00' and len(calls)==2
    assert calls[0]['reasoning']=={'effort':'none'}
    assert 'Fannin South Stn NB' in calls[0]['messages'][0]['content']

def test_dropped_preference_gets_one_correction_attempt(monkeypatch):
    calls=fake_provider(monkeypatch,[extracted(mode='any'),extracted(mode='rail')])
    result=asyncio.run(intent.parse('UH to Fannin South by train'))
    assert result['intent']['mode']=='rail' and len(calls)==2
    assert 'dropped the rail requirement' in calls[1]['messages'][-1]['content']

def test_relative_time_is_corrected_if_model_calls_it_ambiguous(monkeypatch):
    calls=fake_provider(monkeypatch,[extracted(issue='ambiguous_time'),extracted(time='10:20',time_text='in 20 minutes')])
    result=asyncio.run(intent.parse('UH to Fannin South in 20 minutes'))
    assert result['intent']['time']=='10:20' and len(calls)==2

def test_paid_model_rejected_before_secret_lookup(monkeypatch):
    monkeypatch.setenv('OPENROUTER_MODEL','paid/model')
    with pytest.raises(intent.InputError,match='Only OpenRouter free'):asyncio.run(intent.parse('UH to downtown'))

@pytest.mark.parametrize('prompt',['UH to Downtown','Can you get me from UH over to Downtown?','Take me to Fannin South from University of Houston'])
def test_every_wording_uses_ai_first(monkeypatch,prompt):
    calls=fake_provider(monkeypatch,[extracted(time='17:00',date='2020-01-01')])
    result=asyncio.run(intent.parse(prompt))
    assert len(calls)==1
    assert result['model']=='example:free'
    assert result['leave_now'] is True
    assert result['intent']['date']=='2026-11-20'
    assert result['intent']['time']=='10:00'

@pytest.mark.parametrize('text,fields,day,clock',[
 ('UH to Fannin South tomorrow at noon',dict(date='2026-11-21',time='12:00',date_text='tomorrow',time_text='noon'),'2026-11-21','12:00'),
 ('UH to Fannin South in 20 minutes',dict(date='2026-11-20',time='10:20',time_text='in 20 minutes'),'2026-11-20','10:20'),
 ('UH to Fannin South after 5 PM by rail, no transfers',dict(time='17:00',time_text='5 PM',mode='rail',max_transfers=0),'2026-11-20','17:00'),
 ('UH to Fannin South without walking',dict(allow_walking=False),'2026-11-20','10:00'),
] )
def test_time_and_constraints_preserved(monkeypatch,text,fields,day,clock):
    fake_provider(monkeypatch,[extracted(**fields)])
    result=asyncio.run(intent.parse(text))
    assert result['intent']['date']==day
    assert result['intent']['time']==clock
    for key in ('mode','max_transfers','allow_walking'):
        if key in fields:assert result['intent'][key]==fields[key]

@pytest.mark.parametrize('text,fields',[
 ('UH to Fannin South by rail',dict(mode='bus')),
 ('UH to Fannin South without walking',dict(allow_walking=True)),
 ('UH to Fannin South, no transfers',dict(max_transfers=1)),
 ('UH to Fannin South tomorrow',{}),
 ('UH to Fannin South at 5 PM',{}),
])
def test_dropped_constraints_never_reach_routing(monkeypatch,text,fields):
    calls=fake_provider(monkeypatch,[extracted(**fields)])
    with pytest.raises(intent.InputError):asyncio.run(intent.parse(text))
    assert len(calls)==2
    assert 'dropped' in calls[1]['messages'][-1]['content'] or 'omitted' in calls[1]['messages'][-1]['content']

@pytest.mark.parametrize('issue',['missing_places','ambiguous_time','unsupported_request'])
def test_no_followup_questions(monkeypatch,issue):
    calls=fake_provider(monkeypatch,[extracted(issue=issue)])
    with pytest.raises(intent.InputError) as error:asyncio.run(intent.parse('A trip request'))
    assert '?' not in str(error.value)
    assert len(calls)==1

def test_impossible_date_and_untrusted_time_evidence_rejected(monkeypatch):
    fake_provider(monkeypatch,[extracted(date='2026-02-31',date_text='2026-02-31')])
    with pytest.raises(intent.InputError):asyncio.run(intent.parse('UH to Downtown on 2026-02-31'))
    fake_provider(monkeypatch,[extracted(time='17:00',time_text='5 PM')])
    with pytest.raises(intent.InputError):asyncio.run(intent.parse('UH to Downtown'))

def test_manual_future_defaults_are_kept(monkeypatch):
    fake_provider(monkeypatch,[extracted()])
    result=asyncio.run(intent.parse('UH to Fannin South',defaults={'departure':'2026-11-21T14:00:00-06:00','leave_now':False}))
    assert result['intent']['date']=='2026-11-21'
    assert result['intent']['time']=='14:00'
    assert result['leave_now'] is False

def test_unsupported_requirements_not_dropped(monkeypatch):
    fake_provider(monkeypatch,[extracted()])
    with pytest.raises(intent.InputError,match='unsupported'):asyncio.run(intent.parse('UH to Downtown arrive by noon'))

@pytest.mark.parametrize('status',[401,402,429])
def test_quota_errors_are_bounded_and_actionable(monkeypatch,status):
    calls=fake_provider(monkeypatch,[status])
    with pytest.raises(intent.InputError,match='quota'):asyncio.run(intent.parse('UH to Downtown'))
    assert len(calls)==1

def test_backend_resolves_ai_station_names_even_for_simple_prompt(monkeypatch,catalog):
    from backend import main
    calls=fake_provider(monkeypatch,[extracted(destination='fanin south')])
    monkeypatch.setattr(main.stations,'load',lambda:catalog)
    monkeypatch.setattr(main,'rate',main.defaultdict(main.deque))
    request=SimpleNamespace(client=SimpleNamespace(host='test'))
    result=asyncio.run(main.interpret(main.ParseRequest(text='uh to fanin south'),request))
    assert len(calls)==1 and result['validated'] is True
    assert result['model']=='example:free'
    assert {s['stop_id'] for s in result['origin']['stops']}=={'u1','u2'}
    assert {s['stop_id'] for s in result['destination']['stops']}=={'f1','f2'}

def test_unknown_place_returns_inline_error_without_followup(monkeypatch,catalog):
    from backend import main
    from fastapi import HTTPException
    fake_provider(monkeypatch,[extracted(destination='Neverland')])
    monkeypatch.setattr(main.stations,'load',lambda:catalog)
    monkeypatch.setattr(main,'rate',main.defaultdict(main.deque))
    with pytest.raises(HTTPException) as error:
        asyncio.run(main.interpret(main.ParseRequest(text='UH to Neverland'),SimpleNamespace(client=SimpleNamespace(host='test'))))
    assert error.value.status_code==422
    assert 'destination' in error.value.detail and '?' not in error.value.detail

def test_model_cannot_supply_arbitrary_ids_or_extra_instructions(monkeypatch):
    fake_provider(monkeypatch,[extracted(origin_ids=['invented-stop'])])
    with pytest.raises(intent.InputError):asyncio.run(intent.parse('UH to Downtown'))

def test_identical_station_rejected(monkeypatch,catalog):
    from backend import main
    from fastapi import HTTPException
    fake_provider(monkeypatch,[extracted(origin='UH',destination='University of Houston')])
    monkeypatch.setattr(main.stations,'load',lambda:catalog)
    monkeypatch.setattr(main,'rate',main.defaultdict(main.deque))
    with pytest.raises(HTTPException) as error:
        asyncio.run(main.interpret(main.ParseRequest(text='UH to University of Houston'),SimpleNamespace(client=SimpleNamespace(host='test'))))
    assert error.value.status_code==422 and 'same station' in error.value.detail

def test_ambiguous_hour_rejected_even_if_model_guesses(monkeypatch):
    fake_provider(monkeypatch,[extracted(time='17:00',time_text='at 5')])
    with pytest.raises(intent.InputError,match='AM or PM'):
        asyncio.run(intent.parse('UH to Fannin South at 5'))

def test_string_boolean_rejected_by_strict_schema(monkeypatch):
    fake_provider(monkeypatch,[extracted(allow_walking='false')])
    with pytest.raises(intent.InputError):asyncio.run(intent.parse('UH to Fannin South'))

def test_naive_control_time_rejected():
    from backend.main import ParseDefaults,JourneyRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):ParseDefaults(departure='2026-11-21T14:00:00',leave_now=False)
    with pytest.raises(ValidationError):JourneyRequest(origin_ids=['1'],destination_ids=['2'],departure='2026-11-21T14:00:00')
