"""Actual file/SQLite/process-boundary proofs of acknowledged sink recovery."""
import copy
import json
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path

import fraktal_ab_host_events as host
from fraktal_ab_host_sink import SinkBad, SqliteSink
import test_fraktal_ab_host_events as event_tests

APP = event_tests.APP


CHILD = '''
import json, os, sys
from pathlib import Path
import fraktal_ab_host_events as host
from fraktal_ab_host_sink import SqliteSink
cursor_path, batch_path, sink_path, mode = map(str, sys.argv[1:])
batch = json.loads(Path(batch_path).read_text(encoding='utf-8'))
station = batch['events'][0]['StationPath']
cursor = host.Cursor(station, cursor_path)
with SqliteSink(sink_path, station) as sink:
    if mode == 'before_replace':
        host.os.replace = lambda *args: os._exit(72)
    elif mode == 'after_sink':
        cursor._commit = lambda *args: os._exit(71)
    def accept(record):
        if mode == 'after_ack' and record.get('event', {}).get('Sequence') == 2:
            os._exit(73)
        if mode == 'active':
            Path(cursor_path + '.ready').write_text('ready')
            sys.stdin.buffer.read(1)
        return sink(record)
    cursor.deliver(batch, accept)
'''


class DurableDelivery(unittest.TestCase):
    def batch(self, count=3):
        return event_tests.Delivery().batch(count)

    def records(self, database):
        with closing(sqlite3.connect(database)) as connection:
            self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone(), ('ok',))
            return [json.loads(row[0]) for row in connection.execute('SELECT Record FROM Events ORDER BY Id')]

    def child(self, cursor, batch, database, mode):
        batch_path = cursor.with_suffix('.batch.json')
        batch_path.write_text(json.dumps(batch), encoding='utf-8')
        return subprocess.Popen([sys.executable, '-c', CHILD, str(cursor), str(batch_path),
                                 str(database), mode], cwd=Path(__file__).parent,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_process_crash_reopens_without_duplicate_events_or_loss_notices(self):
        for mode in ('after_sink', 'before_replace', 'after_ack', 'overwritten', 'epoch'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                cursor, database = Path(folder)/'cursor.json', Path(folder)/'events.sqlite'
                batch = self.batch(12 if mode == 'overwritten' else 3)
                if mode == 'epoch':
                    with SqliteSink(database, APP.name) as sink:
                        host.Cursor(APP.name, cursor).deliver(batch, sink)
                    batch = self.batch(1)
                    batch['metadata']['EpochLow'] += 1
                process = self.child(cursor, batch, database,
                    mode if mode in ('before_replace', 'after_ack') else 'after_sink')
                stdout, stderr = process.communicate(timeout=15)
                self.assertEqual(process.returncode,
                    {'before_replace': 72, 'after_ack': 73}.get(mode, 71), stderr.decode())
                if mode == 'before_replace':
                    self.assertEqual(len(list(Path(folder).glob('*.pending'))), 1)
                    self.assertFalse(cursor.exists())
                with SqliteSink(database, APP.name) as sink:
                    recovered = host.Cursor(APP.name, cursor)
                    self.assertTrue(recovered.deliver(batch, sink))
                    self.assertEqual(recovered.state['sequence'], batch['metadata']['NewestSequence'])
                    self.assertTrue(recovered.deliver(batch, sink))
                records = self.records(database)
                self.assertEqual(len(records), {'overwritten': 9, 'epoch': 5}.get(mode, 3))
                self.assertEqual(len({json.dumps(r['idempotencyKey']) for r in records}), len(records))

    def test_active_process_excludes_other_writer_and_kill_releases_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            cursor, database = Path(folder)/'cursor.json', Path(folder)/'events.sqlite'
            process = self.child(cursor, self.batch(), database, 'active')
            try:
                ready, deadline = Path(str(cursor) + '.ready'), time.monotonic() + 10
                while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(ready.exists(), 'child did not acquire the delivery guard')
                sent = []
                with self.assertRaises(BlockingIOError):
                    host.Cursor(APP.name, cursor).deliver(self.batch(), lambda r: sent.append(r) or True)
                self.assertEqual(sent, [])
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate(timeout=10)
            with SqliteSink(database, APP.name) as sink:
                self.assertTrue(host.Cursor(APP.name, cursor).deliver(self.batch(), sink))
            self.assertEqual(len(self.records(database)), 3)

    def test_reentrant_cursor_cannot_reenter_delivery(self):
        with tempfile.TemporaryDirectory() as folder:
            cursor = host.Cursor(APP.name, Path(folder)/'cursor.json')
            def sink(record):
                with self.assertRaises(BlockingIOError):
                    cursor.deliver(self.batch(), lambda r: True)
                return True
            self.assertTrue(cursor.deliver(self.batch(), sink))

    def test_exception_releases_guard_and_leaves_failed_record_unacknowledged(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'cursor.json'
            def fail(record):
                raise OSError('sink unavailable')
            with self.assertRaises(OSError):
                host.Cursor(APP.name, path).deliver(self.batch(), fail)
            self.assertFalse(path.exists())
            self.assertTrue(host.Cursor(APP.name, path).deliver(self.batch(), lambda r: True))

    def test_conflicting_replay_fails_without_acknowledging_or_replacing_original(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder)/'events.sqlite'
            with SqliteSink(database, APP.name) as sink:
                host.Cursor(APP.name).deliver(self.batch(), sink)
                bad = self.batch()
                bad['events'][0]['Value'] += '-different'
                cursor = host.Cursor(APP.name)
                with self.assertRaises(SinkBad):
                    cursor.deliver(bad, sink)
                self.assertEqual(cursor.state['sequence'], 0)
            self.assertEqual(len(self.records(database)), 3)

    def test_busy_database_leaves_cursor_unacknowledged_and_retry_succeeds(self):
        with tempfile.TemporaryDirectory() as folder:
            database, path = Path(folder)/'events.sqlite', Path(folder)/'cursor.json'
            with SqliteSink(database, APP.name) as sink, closing(sqlite3.connect(database)) as blocker:
                blocker.execute('BEGIN IMMEDIATE')
                cursor = host.Cursor(APP.name, path)
                with self.assertRaises(sqlite3.OperationalError):
                    cursor.deliver(self.batch(), sink)
                self.assertFalse(path.exists())
                blocker.rollback()
                self.assertTrue(cursor.deliver(self.batch(), sink))

    def test_sink_write_failure_does_not_acknowledge_event(self):
        with tempfile.TemporaryDirectory() as folder:
            with SqliteSink(Path(folder)/'events.sqlite', APP.name) as sink:
                sink.connection.execute('PRAGMA query_only=ON')
                cursor = host.Cursor(APP.name)
                with self.assertRaises(sqlite3.OperationalError):
                    cursor.deliver(self.batch(), sink)
                self.assertEqual(cursor.state['sequence'], 0)

    def test_sink_commit_failure_rolls_back_and_does_not_acknowledge_event(self):
        with tempfile.TemporaryDirectory() as folder:
            database, path = Path(folder)/'events.sqlite', Path(folder)/'cursor.json'
            with SqliteSink(database, APP.name) as sink, closing(sqlite3.connect(database)) as reader:
                reader.execute('BEGIN')
                reader.execute('SELECT * FROM Metadata').fetchall()
                cursor = host.Cursor(APP.name, path)
                with self.assertRaises(sqlite3.OperationalError):
                    cursor.deliver(self.batch(), sink)
                self.assertFalse(path.exists())
                reader.rollback()
                self.assertEqual(sink.connection.execute('SELECT COUNT(*) FROM Events').fetchone(), (0,))
                self.assertTrue(cursor.deliver(self.batch(), sink))

    def test_sink_refuses_other_identity_and_foreign_database(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder)/'events.sqlite'
            with SqliteSink(database, APP.name, source='serial:hash'):
                pass
            for station, source in [('Other', 'serial:hash'), (APP.name, 'other:hash')]:
                with self.subTest(station=station, source=source), self.assertRaises(SinkBad):
                    SqliteSink(database, station, source=source)
            other = Path(folder)/'foreign.sqlite'
            with closing(sqlite3.connect(other)) as connection:
                connection.execute('CREATE TABLE Other (Value INTEGER)')
            with self.assertRaises(SinkBad):
                SqliteSink(other, APP.name)
            with closing(sqlite3.connect(other)) as connection:
                self.assertEqual(connection.execute('SELECT name FROM sqlite_master').fetchall(), [('Other',)])

    def test_sink_requires_a_scoped_key_including_loss_notices(self):
        with tempfile.TemporaryDirectory() as folder:
            sent = []
            host.Cursor(APP.name).deliver(self.batch(12), lambda r: sent.append(r) or True)
            with SqliteSink(Path(folder)/'events.sqlite', APP.name) as sink:
                for record in sent:
                    self.assertTrue(sink(record))
                    for bad_key in (None, ['wrong-source', *record['idempotencyKey'][1:]]):
                        bad = copy.deepcopy(record)
                        bad['idempotencyKey'] = bad_key
                        with self.assertRaises(SinkBad):
                            sink(bad)


if __name__ == '__main__':
    unittest.main()
