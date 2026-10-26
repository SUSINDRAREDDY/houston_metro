from fastapi.testclient import TestClient
from backend import main


def test_liveness_does_not_access_database(monkeypatch):
    monkeypatch.setenv('DB_BACKEND', 'postgres')
    def unavailable():
        raise RuntimeError('private database error')
    monkeypatch.setattr(main.database, 'ready', unavailable)
    client = TestClient(main.app)
    assert client.get('/api/health/live').status_code == 200
    response = client.get('/api/health/ready')
    assert response.status_code == 503
    assert 'private database error' not in response.text


def test_readiness_requires_transit_data(monkeypatch):
    monkeypatch.setenv('DB_BACKEND', 'postgres')
    client = TestClient(main.app)
    monkeypatch.setattr(main.database, 'ready', lambda: False)
    assert client.get('/api/health/ready').status_code == 503
    monkeypatch.setattr(main.database, 'ready', lambda: True)
    assert client.get('/api/health/ready').json() == {'status': 'ready'}
