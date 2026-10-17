"""Opt-in local demonstration logs; never enabled in Cloud Run."""
import json
import logging
import os
import sqlite3
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from .config import ROOT

request_id = ContextVar('demo_request_id', default='startup')
logger = logging.getLogger('metro.demo')


def enabled():
    return os.getenv('METRO_DEMO_LOG') == '1' and not os.getenv('K_SERVICE') and os.getenv('DB_BACKEND') != 'postgres'


def configure():
    if not enabled() or logger.handlers:
        return
    path = ROOT / 'logs' / 'demo.log'
    path.parent.mkdir(exist_ok=True)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in (logging.StreamHandler(), RotatingFileHandler(path, maxBytes=5_000_000, backupCount=2)):
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt='%H:%M:%S'))
        logger.addHandler(handler)


def event(stage, **fields):
    if enabled():
        logger.info('[%s] %s %s', request_id.get(), stage, json.dumps(fields, default=str, ensure_ascii=False))


class Cursor(sqlite3.Cursor):
    """Observe consumed rows without changing or eagerly buffering query results."""
    def execute(self, sql, parameters=()):
        self.query_id = os.urandom(3).hex()
        self.count = 0
        self.sample = []
        event('SQL', query_id=self.query_id, statement=' '.join(sql.split()), parameters=parameters)
        return super().execute(sql, parameters)

    def record(self, rows, complete):
        self.count += len(rows)
        for row in rows[:max(0, 2-len(self.sample))]:
            self.sample.append(dict(row) if isinstance(row, sqlite3.Row) else row)
        event('DB_ROWS', query_id=self.query_id, rows_consumed=self.count, complete=complete, sample=self.sample)

    def fetchall(self):
        rows = super().fetchall()
        self.record(rows, True)
        return rows

    def fetchone(self):
        row = super().fetchone()
        self.record([] if row is None else [row], row is None)
        return row

    def __next__(self):
        try:
            row = super().__next__()
        except StopIteration:
            self.record([], True)
            raise
        self.count += 1
        if len(self.sample) < 2:
            self.sample.append(dict(row) if isinstance(row, sqlite3.Row) else row)
        return row


class Connection(sqlite3.Connection):
    def execute(self, sql, parameters=()):
        return self.cursor(factory=Cursor).execute(sql, parameters)

    def executemany(self, sql, parameters):
        # Routing writes only request-local TEMP tables on this read-only connection.
        event('SQL_TEMP', statement=sql, storage='temporary connection tables; not saved to database file')
        return super().executemany(sql, parameters)
