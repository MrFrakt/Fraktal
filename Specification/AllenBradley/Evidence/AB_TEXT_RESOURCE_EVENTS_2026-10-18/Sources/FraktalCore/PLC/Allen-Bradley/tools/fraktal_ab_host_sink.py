"""Optional local transactional HostEvents sink; no PLC or network writes.

SQLite owns transactions and duplicate exclusion. Cursor delivery stays at
least once; identical replay returns acceptance, conflicting replay fails.
This database is a dedicated sink for one station/controller/build identity.
"""
from __future__ import annotations

import json
import sqlite3


class SinkBad(ValueError):
    pass


class SqliteSink:
    def __init__(self, path, station, *, source=''):
        self.station, self.source = station, source
        self.connection = sqlite3.connect(path, timeout=0, isolation_level='IMMEDIATE')
        try:
            if self.connection.execute('PRAGMA journal_mode').fetchone()[0] in ('off', 'memory'):
                raise SinkBad('HostEvents sink requires an on-disk transaction journal')
            self.connection.execute('PRAGMA synchronous=FULL')
            with self.connection:
                self.connection.execute('BEGIN IMMEDIATE')
                tables = {row[0] for row in self.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                if not tables:
                    self.connection.execute('CREATE TABLE Metadata '
                        '(SchemaVersion INTEGER NOT NULL, Station TEXT NOT NULL, Source TEXT NOT NULL)')
                    self.connection.execute('INSERT INTO Metadata VALUES (1, ?, ?)', (station, source))
                    self.connection.execute('CREATE TABLE Events '
                        '(Id INTEGER PRIMARY KEY, IdempotencyKey TEXT UNIQUE NOT NULL, Record TEXT NOT NULL)')
                elif tables != {'Metadata', 'Events'}:
                    raise SinkBad('not a dedicated HostEvents sink database')
                if self.connection.execute('SELECT * FROM Metadata').fetchall() != [(1, station, source)]:
                    raise SinkBad('sink schema or station/controller/build identity differs')
        except BaseException:
            self.connection.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.connection.close()

    def __call__(self, record):
        key = record.get('idempotencyKey')
        if (record.get('kind') not in ('event', 'dataLoss') or not isinstance(key, list)
                or len(key) < 5 or key[:2] != [self.source, self.station]):
            raise SinkBad('missing or differently scoped HostEvents idempotency key')
        key_json = json.dumps(key, separators=(',', ':'), allow_nan=False)
        payload = json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False)
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            existing = self.connection.execute(
                'SELECT Record FROM Events WHERE IdempotencyKey=?', (key_json,)).fetchone()
            if existing is None:
                self.connection.execute('INSERT INTO Events (IdempotencyKey, Record) VALUES (?, ?)',
                                        (key_json, payload))
            elif existing[0] != payload:
                raise SinkBad('HostEvents key replayed with different content')
        # Commit (including its failure) precedes the caller's acknowledgement.
        return True
