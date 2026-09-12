import sqlite3
import pytest
from backend import cloud_data

@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.setenv('GTFS_DB_GCS_URI', 'gs://test/metro.sqlite3')
    monkeypatch.setattr(cloud_data, 'DB', tmp_path/'metro.sqlite3')
    monkeypatch.setattr(cloud_data, '_checked', 0)
    monkeypatch.setattr(cloud_data, '_generation', None)
    return cloud_data.DB

def database(path):
    with sqlite3.connect(path) as db:
        for table in ('stops','routes','trips','stop_times','metadata','feed_info'):
            db.execute(f'CREATE TABLE {table}(value TEXT)')
            db.execute(f'INSERT INTO {table} VALUES ("sample")')
        db.execute('CREATE TABLE agency(agency_timezone TEXT)')
        db.execute('INSERT INTO agency VALUES ("America/Chicago")')

class Blob:
    generation = 42
    size = 1000
    def reload(self, **kwargs):pass
    def download_to_filename(self, path, **kwargs):
        assert kwargs['if_generation_match'] == 42
        database(path)

def test_cold_start_and_unchanged_snapshot(setup, monkeypatch):
    source=Blob()
    monkeypatch.setattr(cloud_data, 'blob', lambda:source)
    cloud_data.sync(True)
    cloud_data.validate(setup)
    assert cloud_data._generation == 42
    monkeypatch.setattr(source, 'download_to_filename', lambda *a,**k:pytest.fail('Repeated download'))
    cloud_data.sync(True)

def test_bad_download_retains_old_database(setup, monkeypatch):
    database(setup)
    previous=setup.read_bytes()
    source=Blob()
    monkeypatch.setattr(source, 'download_to_filename', lambda path,**k:__import__('pathlib').Path(path).write_bytes(b'corrupt'))
    monkeypatch.setattr(cloud_data, 'blob', lambda:source)
    cloud_data.sync(True)
    assert setup.read_bytes()==previous
    assert cloud_data._generation is None
    assert not setup.with_suffix('.download.sqlite3').exists()

def test_empty_cold_start_fails_when_storage_unavailable(setup, monkeypatch):
    def fail():raise RuntimeError('storage unavailable')
    monkeypatch.setattr(cloud_data, 'blob', fail)
    with pytest.raises(RuntimeError):cloud_data.sync(True)
    assert not setup.exists()
