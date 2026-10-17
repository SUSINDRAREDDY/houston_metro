"""Apply the SQL migration and copy a read-only SQLite snapshot transactionally.

Run from the VM in the new image. Never point this at a live changing SQLite file;
create the source with sqlite3.Connection.backup first. The script refuses to
overwrite an already populated PostgreSQL database.
"""
import argparse
import csv
import hashlib
import io
import json
import sqlite3
from pathlib import Path
from backend import database


def copy_table(source, target, old, new):
    columns = [r[1] for r in source.execute(f'PRAGMA table_info("{old}")')]
    cursor = source.execute(f'SELECT * FROM "{old}"')
    count = 0
    # pg8000 COPY streams batches rather than sending 1.6 million INSERT calls.
    while rows := cursor.fetchmany(20000):
        stream = io.StringIO()
        writer = csv.writer(stream, lineterminator='\n', quoting=csv.QUOTE_ALL)
        # All old GTFS numeric nulls become the COPY null token, preserving NULL.
        for row in rows:
            writer.writerow(['\\N' if value is None else value for value in row])
        stream.seek(0)
        names = ','.join('"'+c+'"' for c in columns)
        target.raw.cursor().execute(f'''COPY "{new}" ({names}) FROM STDIN WITH (FORMAT CSV, NULL '\\N', FORCE_NULL ({names}))''', stream=stream)
        count += len(rows)
    actual = target.execute(f'SELECT COUNT(*) FROM "{new}"').fetchone()[0]
    if count != actual:
        raise RuntimeError(f'Count mismatch for {old}: {count} vs {actual}')
    return {'old': count, 'new': actual, 'match': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sqlite', required=True, type=Path)
    parser.add_argument('--gis', type=Path)
    parser.add_argument('--alerts', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    schema = Path(__file__).resolve().parents[1]/'migrations/001_managed_state.sql'
    sql = schema.read_text()
    report = {'migration': schema.name, 'migration_sha256': hashlib.sha256(schema.read_bytes()).hexdigest(),
        'source_sha256': hashlib.sha256(args.sqlite.read_bytes()).hexdigest(), 'tables': {}}
    with sqlite3.connect(f'{args.sqlite.resolve().as_uri()}?mode=ro', uri=True) as source, database.connect() as target:
        if target.execute("SELECT to_regclass('public.schema_migrations')").fetchone()[0] is not None:
            raise RuntimeError('Migration already applied; refusing to replace existing state.')
        # Execute the real committed DDL in the same transaction as the data copy.
        target.raw.cursor().execute(sql)
        for name, in source.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            report['tables'][name] = copy_table(source, target, name, name)
        if args.gis:
            with sqlite3.connect(f'{args.gis.resolve().as_uri()}?mode=ro', uri=True) as gis:
                for name in ('stations', 'metadata'):
                    report['tables']['gis.'+name] = copy_table(gis, target, name, 'gis_'+name)
        if args.alerts:
            target.execute('INSERT INTO application_state VALUES (?,?)', ('metro_alerts', args.alerts.read_text()))
        target.execute('INSERT INTO schema_migrations(version,sha256) VALUES (?,?)', (schema.name, report['migration_sha256']))
        target.commit()
        target.execute('ANALYZE')
        target.commit()
    report['all_counts_match'] = all(t['match'] for t in report['tables'].values())
    text = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(text+'\n')
    print(text)


if __name__ == '__main__':
    main()
