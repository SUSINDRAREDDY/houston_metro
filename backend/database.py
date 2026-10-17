"""PostgreSQL connections with the row interface used by the transit router."""
import os
import re
import threading

_engine = None
_connector = None
_lock = threading.Lock()


def managed():
    return os.getenv('DB_BACKEND') == 'postgres'


class Row:
    def __init__(self, names, values):
        self._names, self._values = names, values
    def __getitem__(self, key):
        return self._values[self._names.index(key)] if isinstance(key, str) else self._values[key]
    def keys(self):
        return self._names
    def __iter__(self):
        return iter(self._values)
    def __len__(self):
        return len(self._values)


def sql_parameters(sql):
    # Only translate placeholders outside quoted SQL literals. SQL text is static;
    # all user input remains separately bound to parameters.
    parts = re.split(r"('(?:''|[^'])*')", sql)
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(r'\bLIKE\b', 'ILIKE', parts[i], flags=re.I).replace('?', '%s')
    return ''.join(parts)


class Cursor:
    def __init__(self, cursor):
        self.cursor = cursor
        self.names = [d[0] for d in cursor.description] if cursor.description else []
    def fetchone(self):
        row = self.cursor.fetchone()
        return None if row is None else Row(self.names, row)
    def fetchall(self):
        return [Row(self.names, row) for row in self.cursor.fetchall()]
    def __iter__(self):
        while (row := self.fetchone()) is not None:
            yield row


class Connection:
    def __init__(self, raw):
        self.raw = raw
    def execute(self, sql, parameters=()):
        cursor = self.raw.cursor()
        cursor.execute(sql_parameters(sql), tuple(parameters))
        return Cursor(cursor)
    def executemany(self, sql, parameters):
        values = list(parameters)
        if not values:
            return
        cursor = self.raw.cursor()
        cursor.executemany(sql_parameters(sql), values)
        return Cursor(cursor)
    def commit(self):
        self.raw.commit()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        # Discard request-local temporary tables and unfinished writes before reuse.
        try:
            self.raw.rollback()
        finally:
            self.raw.close()


def engine():
    global _engine, _connector
    with _lock:
        if _engine is None:
            import sqlalchemy
            from google.cloud.sql.connector import Connector, IPTypes
            from . import secrets
            if os.getenv('DATABASE_URL'):
                # Used only for local PostgreSQL integration tests.
                _engine = sqlalchemy.create_engine(os.environ['DATABASE_URL'], pool_size=3, max_overflow=1, pool_pre_ping=True)
            else:
                _connector = Connector(refresh_strategy='LAZY')
                def create_connection():
                    return _connector.connect(
                        os.environ['INSTANCE_CONNECTION_NAME'], 'pg8000',
                        user=os.getenv('DB_USER', 'metroai_app'),
                        password=secrets.get('DB_PASSWORD'),
                        db=os.getenv('DB_NAME', 'metroai'), ip_type=IPTypes.PRIVATE,
                    )
                _engine = sqlalchemy.create_engine('postgresql+pg8000://', creator=create_connection,
                    pool_size=3, max_overflow=1, pool_timeout=20, pool_recycle=1800, pool_pre_ping=True)
        return _engine


def connect():
    return Connection(engine().raw_connection())


def ready():
    with connect() as db:
        return bool(db.execute('SELECT 1 FROM stops LIMIT 1').fetchone())


def state_get(key):
    import json
    with connect() as db:
        row = db.execute('SELECT value FROM application_state WHERE key=?', (key,)).fetchone()
    return json.loads(row[0]) if row else None


def state_put(key, value):
    import json
    with connect() as db:
        db.execute('INSERT INTO application_state(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value', (key, json.dumps(value)))
        db.commit()
