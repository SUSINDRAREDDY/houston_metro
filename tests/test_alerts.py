from datetime import datetime,timezone,timedelta
import json
from backend import alerts

def test_route_numbers_normalized():
    a={'id':'1','routes':['82'],'route_kind':'short_name'}
    assert alerts.for_route([a],{'route_id':'082','route_short_name':'082'})==[a]
    assert alerts.for_route([a],{'route_id':'002','route_short_name':'002'})==[]

def test_stale_snapshot_labeled(monkeypatch,tmp_path):
    p=tmp_path/'alerts.json';monkeypatch.setattr(alerts,'CACHE',p)
    p.write_text(json.dumps({'fetched_at':(datetime.now(timezone.utc)-timedelta(minutes=16)).isoformat(),'source':'test','alerts':[]}))
    assert alerts.snapshot()['status']=='stale'

def test_bad_feed_preserves_database(tmp_path):
    import pytest
    from backend.ingest import import_gtfs
    db=tmp_path/'old.sqlite3';db.write_bytes(b'previous validated snapshot')
    bad=tmp_path/'bad.zip';bad.write_bytes(b'not a zip')
    with pytest.raises(Exception):import_gtfs(bad,db)
    assert db.read_bytes()==b'previous validated snapshot'
