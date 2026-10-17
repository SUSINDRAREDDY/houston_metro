import hashlib
from datetime import datetime

from backend import demo_trace, routing


def test_demo_disabled_in_cloud(monkeypatch):
    monkeypatch.setenv('METRO_DEMO_LOG', '1')
    monkeypatch.setenv('K_SERVICE', 'metro')
    assert not demo_trace.enabled()


def test_real_database_trace_matches_results_without_writes(monkeypatch):
    monkeypatch.setenv('METRO_DEMO_LOG', '1')
    monkeypatch.delenv('K_SERVICE', raising=False)
    events = []
    monkeypatch.setattr(demo_trace, 'event', lambda stage, **fields: events.append((stage, fields)))
    before = hashlib.sha256(routing.DB.read_bytes()).hexdigest()
    with routing.connect() as db:
        origins = routing.stop_search(db, 'UH')
        destinations = routing.stop_search(db, 'Downtown')
        result = routing.plan(db, [s['stop_id'] for s in origins], [s['stop_id'] for s in destinations],
                              datetime.fromisoformat('2026-09-12T17:00:00-05:00'))
    assert result
    assert hashlib.sha256(routing.DB.read_bytes()).hexdigest() == before
    assert any(stage == 'SQL' and 'JOIN stop_times' in fields['statement'] for stage, fields in events)
    assert any(stage == 'DB_ROWS' and fields['complete'] and fields['rows_consumed'] == len(origins)
               and fields['sample'][0]['stop_id'] == origins[0]['stop_id'] for stage, fields in events)
    assert any(stage == 'DB_ROWS' and fields['rows_consumed'] > 100 for stage, fields in events)


def test_request_trace_and_error_context(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.main import app
    monkeypatch.setenv('METRO_DEMO_LOG', '1')
    monkeypatch.delenv('K_SERVICE', raising=False)
    monkeypatch.delenv('GTFS_DB_GCS_URI', raising=False)
    events = []
    monkeypatch.setattr(demo_trace, 'event', lambda stage, **fields: events.append((demo_trace.request_id.get(), stage, fields)))
    # No lifespan here: avoid external alert refreshes in this focused HTTP test.
    client = TestClient(app)
    response = client.get('/api/stops?q=UH')
    assert response.status_code == 200
    rid = response.headers['X-Demo-Request-ID']
    assert any(r == rid and stage == 'SQL' for r, stage, _ in events)
    assert any(r == rid and stage == 'DB_ROWS' for r, stage, _ in events)
    invalid = client.post('/api/journeys', json={})
    assert invalid.status_code == 422
    assert invalid.headers['X-Demo-Request-ID'] != rid
    assert demo_trace.request_id.get() == 'startup'
