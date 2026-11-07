"""The Dart child owns storage; the apparatus owns only its lease and copy."""
import hashlib
import json
from pathlib import Path
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import fraktal_ab_harness_host as host
from fraktal_ab_harness_process import attach
import fraktal_ab_harness_gateway as gateway


class Process:
    pid = 901
    def __init__(self):
        self.code, self.stops = None, 0
    def poll(self):
        return self.code
    def terminate(self):
        self.stops += 1
        self.code = 0
    def wait(self, timeout):
        return self.code


class Host(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.exe = self.path / 'fraktal_host_adapter.exe'
        self.exe.write_bytes(b'prepared Dart adapter')
        self.digest = hashlib.sha256(self.exe.read_bytes()).hexdigest()
        self.lines = [dict(state='serving', roots=['Press'], eventRings=[])]
        self.process, self.calls, self.now = Process(), [], 0

    def spawn(self, arguments, **options):
        self.calls.append((arguments, options))
        for line in self.lines:
            options['stdout'].write(json.dumps(line) + '\n')
        options['stdout'].flush()
        return self.process

    def sleep(self, seconds):
        self.now += seconds

    def make(self, **extra):
        options = dict(host='127.0.0.1', slot=0, serial='601FC87B', root='Press',
                       directory=self.path / 'logs', store=self.path / 'store',
                       spawn=self.spawn, competitors=lambda: [], clock=lambda: self.now, sleep=self.sleep)
        options.update(extra)
        lease = host.HostLease(self.exe, self.digest, **options)
        self.addCleanup(lease.close)
        return lease

    def append(self, lease, data):
        with lease.log_path.open('ab') as out:
            out.write(data)

    def test_hash_target_arguments_isolated_environment_and_owned_close(self):
        with patch.dict('os.environ', {'UNRELATED_SECRET': 'never log me'}):
            lease = self.make().start()
        args, options = self.calls[0]
        self.assertEqual(args[1:], ['--host', '127.0.0.1', '--port', '44818', '--slot', '0',
                                   '--expect-serial', '601FC87B', '--interval-ms', '20'])
        self.assertEqual(options['env']['FRAKTAL_AB_CONFIG_SET_DIR'], str(lease.store))
        self.assertIs(options['shell'], False)
        self.assertTrue(lease.guard(serial='601FC87B', root='Press'))
        record = (lease.directory / (lease.instance + '.json')).read_text(encoding='utf-8')
        self.assertNotIn('never log me', record)
        lease.close()
        lease.close()
        self.assertEqual(self.process.stops, 1)
        self.assertFalse(lease.guard(serial='601FC87B', root='Press'))
        with self.assertRaises(ValueError):
            lease.start()

    def test_wrong_package_target_or_existing_store_refuses_before_spawn(self):
        for change in (dict(serial='DEADBEEF'), dict(slot=1), dict(host='192.0.2.1'), dict(root='Other')):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.make(**change)
        with self.assertRaises(ValueError):
            host.HostLease(self.exe, '00' * 32, host='127.0.0.1', slot=0, serial='601FC87B', root='Press',
                           directory=self.path / 'logs', store=self.path / 'store')
        (self.path / 'store').mkdir()
        with self.assertRaisesRegex(ValueError, 'new isolated'):
            self.make()
        self.assertEqual(self.calls, [])

    def test_competing_adapter_refuses_without_touching_it(self):
        lease = self.make(competitors=lambda: [444])
        with self.assertRaisesRegex(ValueError, 'another host'):
            lease.start()
        self.assertEqual(self.calls, [])
        self.assertEqual(self.process.stops, 0)
        self.assertFalse(lease.store.exists())

    def test_package_changed_before_start_refuses_and_cannot_restart(self):
        lease = self.make()
        self.exe.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed before startup'):
            lease.start()
        self.assertEqual(self.calls, [])
        with self.assertRaises(ValueError):
            lease.start()

    def test_failure_is_latched_even_if_the_cli_later_reconnects(self):
        lease = self.make().start()
        self.append(lease, b'{"state":"unavailable","error":"link lost"}\n')
        self.assertFalse(lease.guard(serial='601FC87B', root='Press'))
        self.append(lease, b'{"state":"serving","roots":["Press"],"eventRings":[]}\n')
        self.assertFalse(lease.guard(serial='601FC87B', root='Press'))
        self.assertEqual(len(self.calls), 1)

    def test_partial_status_line_waits_for_completion_and_health_failure_refuses(self):
        lease = self.make().start()
        self.append(lease, b'{"root":"Press","health":')
        self.assertTrue(lease.guard(serial='601FC87B', root='Press'))
        self.append(lease, b'{"state":"failed","failed":true}}\n')
        self.assertFalse(lease.guard(serial='601FC87B', root='Press'))

    def test_wrong_root_or_malformed_status_cannot_be_ready(self):
        for row in (dict(state='serving', roots=['Other'], eventRings=[]),
                    dict(state='no host services'), dict(root='Other', health={'failed': False}),
                    dict(root='Press', health={'failed': 1})):
            with self.subTest(row=row):
                self.lines = [row]
                lease = self.make(store=self.path / ('store-' + str(len(self.calls))))
                with self.assertRaises(RuntimeError):
                    lease.start(timeout=.1)
                self.process = Process()

    def test_no_serving_report_times_out_and_an_exited_child_never_looks_ready(self):
        self.lines = []
        lease = self.make()
        with self.assertRaises(TimeoutError):
            lease.start(timeout=.1)
        self.assertEqual(self.process.stops, 1)
        self.process = Process()
        self.lines = [dict(state='serving', roots=['Press'], eventRings=[])]
        self.process.code = 7
        lease = self.make(store=self.path / 'second-store')
        with self.assertRaises(RuntimeError):
            lease.start()

    def test_seed_copy_is_byte_exact_and_the_original_remains_read_only(self):
        source = self.path / 'original'
        (source / 'live').mkdir(parents=True)
        data = b'original bytes\n'
        path = source / 'live/index.json'
        path.write_bytes(data)
        manifest = self.path / 'seed.json'
        manifest.write_text(json.dumps(dict(schema='fraktal.harness.store-seed', schemaVersion=1,
            serial='601FC87B', root='Press', directory=str(source), files=[
                dict(path='live/index.json', sha256=hashlib.sha256(data).hexdigest())])), encoding='utf-8')
        digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
        lease = self.make(seed=manifest, seed_sha256=digest).start()
        self.assertEqual((lease.store / 'live/index.json').read_bytes(), data)
        self.assertTrue(lease.originals_unchanged())
        (lease.store / 'live/index.json').write_bytes(b'working copy changed')
        self.assertEqual(path.read_bytes(), data)
        path.write_bytes(b'outside change')
        self.assertFalse(lease.originals_unchanged())

    def test_seed_hash_target_escape_duplicate_and_changed_bytes_refuse(self):
        source = self.path / 'original'
        source.mkdir()
        manifest = self.path / 'seed.json'
        name = 'a' * 64 + '.jsonl'
        (source / name).write_bytes(b'x')
        good = dict(schema='fraktal.harness.store-seed', schemaVersion=1, serial='601FC87B', root='Press',
                    directory=str(source), files=[dict(path=name, sha256=hashlib.sha256(b'x').hexdigest())])
        cases = [dict(good, root='Other'), dict(good, files=[dict(path='../escape.jsonl', sha256='00')]),
                 dict(good, files=good['files'] * 2), dict(good, files=[dict(path=name, sha256='00')])]
        for i, held in enumerate(cases):
            manifest.write_text(json.dumps(held), encoding='utf-8')
            digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
            destination = self.path / ('copy-' + str(i))
            destination.mkdir()
            with self.subTest(case=i), self.assertRaises(ValueError):
                host.seed_store(destination, manifest, digest, '601FC87B', 'Press')

    def test_read_only_store_has_no_business_write_methods(self):
        store = host.ReadOnlyStore(self.path / 'nothing')
        self.assertEqual(store.list(), [])
        self.assertFalse(any(hasattr(store, name) for name in ('save', 'delete', 'write')))

    def test_close_boundary_drains_both_children_despite_a_cleanup_error(self):
        calls = []
        class Child:
            def __init__(self, name, fail=False):
                self.name, self.fail = name, fail
            def close(self):
                calls.append(self.name)
                if self.fail:
                    raise RuntimeError('close failed')
        connection = NS(close=lambda: calls.append('connection'))
        comm = NS(conn=connection)
        attach(comm, 'gateway', Child('gateway', True))
        attach(comm, 'host', Child('host'))
        with self.assertRaisesRegex(RuntimeError, 'close failed'):
            connection.close()
        self.assertEqual(calls, ['gateway', 'host', 'connection'])

    def test_shared_process_refactor_keeps_real_http_readiness(self):
        lease = gateway.GatewayLease(self.exe, self.digest, host='127.0.0.1', slot=0,
            serial='601FC87B', root='Press', directory=self.path / 'http-logs', spawn=self.spawn)
        self.addCleanup(lease.close)
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                data = json.dumps(dict(instance=lease.instance, status='ready', plcReady=True,
                    writeAccess=dict(enabled=True, allRootMailboxes=False, roots=['Press']))).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', lease.port), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            lease.start(timeout=1)
            self.assertTrue(lease.guard(serial='601FC87B', root='Press', url=lease.url))
        finally:
            lease.close()
            server.shutdown()
            server.server_close()
            thread.join(2)

    def test_restore_requires_the_seed_and_a_fresh_identity_before_start(self):
        import fraktal_ab_fixture_reads as views
        session = NS(root='Press', expected_serial='601FC87B')
        comm = NS(conn=NS())
        pins = {'FRAKTAL_HARNESS_HOST_ADAPTER': str(self.exe),
                'FRAKTAL_HARNESS_HOST_ADAPTER_SHA256': self.digest,
                'FRAKTAL_HARNESS_HOST_SEED': '', 'FRAKTAL_HARNESS_HOST_SEED_SHA256': ''}
        with patch.object(views, '_session', return_value=session), patch.object(views, '_guard_command') as guard, \
                patch.dict(host.os.environ, pins), patch.object(host, 'HostLease') as launch:
            with self.assertRaisesRegex(ValueError, 'original-medium seed'):
                host.bind(comm, object(), require_seed=True)
            launch.assert_not_called()
            guard.side_effect = ValueError('identity changed')
            with self.assertRaisesRegex(ValueError, 'identity changed'):
                host.bind(comm, object(), store=self.path / 'new-store')
            launch.assert_not_called()

    def test_connection_reuses_only_its_live_owned_child_and_never_restarts(self):
        import fraktal_ab_fixture_reads as views
        session = NS(root='Press', expected_serial='601FC87B')
        owned = NS(seed='prepared', guard=lambda **target: True)
        comm = NS(conn=NS(_fraktal_host_lease=owned))
        with patch.object(views, '_session', return_value=session), patch.object(views, '_guard_command'), \
                patch.object(host, 'HostLease') as launch:
            self.assertIs(host.bind(comm, object(), require_seed=True), owned)
            owned.guard = lambda **target: False
            with self.assertRaisesRegex(ValueError, 'no restart'):
                host.bind(comm, object())
            launch.assert_not_called()

    def test_seed_recorder_keeps_original_files_and_excludes_unrelated_data(self):
        from fraktal_ab_harness_seed import record
        from fraktal_ab_live_medium import FileMedium
        source = self.path / 'original-store'
        doc = [dict(set='_live', root='Press', schema=1, configRev=7, kind=1,
                    model='', records=0, created=0, clock=0)]
        FileMedium(source / 'live').write('Press.station', doc)
        (source / 'live' / ('f' * 64 + '.jsonl')).write_text('unconfirmed leftover', encoding='ascii')
        (source / 'credentials.json').write_text('synthetic unrelated data', encoding='utf-8')
        output = self.path / 'recorded-seed.json'
        result = record(source, output, serial='601FC87B', root='Press')
        self.assertEqual(len(result['files']), 2)
        self.assertFalse(any('credentials' in row['path'] for row in result['files']))
        for row in result['files']:
            self.assertEqual(hashlib.sha256((source / row['path']).read_bytes()).hexdigest().upper(), row['sha256'])
        with self.assertRaises(ValueError):
            record(source, source / 'seed.json', serial='601FC87B', root='Press')


if __name__ == '__main__':
    unittest.main()
