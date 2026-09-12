"""Private GCS snapshots; only the refresh job writes the shared database."""
import logging
import os
import sqlite3
import threading
import time
from pathlib import Path
from .config import DB

_lock = threading.Lock()
_checked = 0.0
_generation = None

def enabled():
    return bool(os.getenv('GTFS_DB_GCS_URI'))

def blob():
    from google.cloud import storage
    uri = os.environ['GTFS_DB_GCS_URI']
    if not uri.startswith('gs://') or '/' not in uri[5:]:
        raise ValueError('GTFS_DB_GCS_URI must be gs://bucket/object')
    bucket, name = uri[5:].split('/', 1)
    return storage.Client().bucket(bucket).blob(name)

def validate(path):
    with sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode=ro', uri=True) as db:
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('Invalid SQLite snapshot')
        for table in ('stops', 'routes', 'trips', 'stop_times', 'metadata', 'feed_info'):
            if not db.execute(f'SELECT 1 FROM {table} LIMIT 1').fetchone():
                raise ValueError(f'Empty snapshot table: {table}')
        if {r[0] for r in db.execute('SELECT agency_timezone FROM agency')} != {'America/Chicago'}:
            raise ValueError('Wrong transit timezone')

def sync(force=False):
    global _checked, _generation
    if not enabled():
        return
    with _lock:
        if not force and time.monotonic() - _checked < 900:
            return
        # Also throttle failures so an outage does not produce a request stampede.
        _checked = time.monotonic()
        stage = DB.with_suffix('.download.sqlite3')
        try:
            source = blob()
            source.reload(timeout=30)
            if _generation == source.generation and DB.exists():
                return
            if source.size is None or source.size > 400_000_000:
                raise ValueError('Snapshot exceeds 400 MB limit')
            source.download_to_filename(str(stage), if_generation_match=source.generation, timeout=60)
            validate(stage)
            os.replace(stage, DB)
            _generation = source.generation
            logging.info('Loaded transit snapshot generation %s', _generation)
        except Exception:
            if not DB.exists():
                raise
            logging.exception('Snapshot refresh failed; retaining last validated database')
        finally:
            stage.unlink(missing_ok=True)

def publish():
    """Run in a Cloud Run Job: import first, publish only a validated snapshot."""
    from google.api_core.exceptions import NotFound
    from . import ingest
    target = blob()
    try:
        target.reload(timeout=30)
        previous = target.generation
    except NotFound:
        previous = 0
    ingest.download()
    validate(DB)
    # Refuse to overwrite a newer snapshot if another job finished first.
    target.upload_from_filename(str(DB), content_type='application/vnd.sqlite3',
                                if_generation_match=previous, timeout=120)
    logging.info('Published validated transit snapshot')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    publish()
