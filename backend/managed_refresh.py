"""Build an expendable feed snapshot and atomically refresh PostgreSQL tables."""
import os
import tempfile
from pathlib import Path
from . import ingest, database


def refresh():
    import httpx
    import sqlite3
    from scripts.migrate_state import copy_table
    with tempfile.TemporaryDirectory(prefix='metro-refresh-') as folder:
        path = Path(folder)/'gtfs.zip'
        with httpx.stream('GET', ingest.GTFS_URL, follow_redirects=True, timeout=180) as response:
            response.raise_for_status()
            size = 0
            with path.open('wb') as output:
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > 200_000_000:
                        raise ValueError('GTFS exceeds size limit')
                    output.write(chunk)
        snapshot = Path(folder)/'metro.sqlite3'
        ingest.import_gtfs(path, snapshot)
        with sqlite3.connect(snapshot) as source, database.connect() as target:
            target.execute('SELECT pg_advisory_xact_lock(41404)')
            names = list(ingest.TABLES) + ['metadata']
            target.execute('TRUNCATE '+','.join('"'+name+'"' for name in names))
            for name in names:
                copy_table(source,target,name,name)
            target.commit()


if __name__ == '__main__':
    refresh()
