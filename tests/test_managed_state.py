"""Run against a migrated PostgreSQL test database with DATABASE_URL set."""
import os
import uuid
from datetime import datetime
import pytest
from backend import database, routing

pytestmark = pytest.mark.skipif(not os.getenv('DATABASE_URL'), reason='Requires a migrated PostgreSQL integration database')


@pytest.fixture(autouse=True)
def managed(monkeypatch):
    monkeypatch.setenv('DB_BACKEND','postgres')


def test_routing_and_case_insensitive_bound_search():
    with routing.connect() as db:
        assert routing.stop_search(db,'UH')
        assert not routing.stop_search(db,"' OR 1=1 --")
        assert db.execute('SELECT route_id FROM routes WHERE route_long_name LIKE ?',('%purple%',)).fetchone()
        rows=routing.plan(db,['25080'],['25054'],datetime.fromisoformat('2026-10-17T17:00:00-05:00'),mode='rail',max_transfers=0)
        assert rows and all(j['transfers']==0 for j in rows)


def test_request_temp_tables_do_not_leak_through_pool():
    with database.connect() as db:
        db.execute('CREATE TEMP TABLE request_only(value TEXT)')
        db.execute('INSERT INTO request_only VALUES (?)',('private request value',))
    with database.connect() as db:
        assert db.execute("SELECT to_regclass('pg_temp.request_only')").fetchone()[0] is None


def test_persistent_state_survives_new_connection():
    identifier='test-'+str(uuid.uuid4())
    database.state_put(identifier,{'notice':'persists outside the process'})
    assert database.state_get(identifier)=={'notice':'persists outside the process'}
    with database.connect() as db:
        db.execute('DELETE FROM application_state WHERE key=?',(identifier,))
        db.commit()


def test_upload_validation_does_not_write_cloud_state(monkeypatch):
    from fastapi.testclient import TestClient
    from backend import alerts
    from backend.main import app
    monkeypatch.setattr(alerts,'ensure_current',lambda:None)
    with TestClient(app) as client:
        before=client.get('/api/uploads').json()
        assert client.post('/api/uploads',content=b'hello').status_code==422
        assert client.post('/api/uploads',headers={'X-Filename':'empty.txt'},content=b'').status_code==422
        assert client.post('/api/uploads',headers={'X-Filename':'large.txt'},content=b'x'*(5242880+1)).status_code==413
        assert client.get('/api/uploads').json()==before
