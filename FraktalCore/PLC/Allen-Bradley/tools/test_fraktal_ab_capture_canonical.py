"""C5b1: Core capture/browse transport with independent machine observations."""
import asyncio
from contextlib import contextmanager
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import fraktal_ab_fixture_reads as views
import fraktal_ab_harness_commands as gateway
import fraktal_ab_phase5_execute as phase5
import fraktal_ab_phase6_execute as capture
import fraktal_ab_press_s6_collapse_echo38 as profile
from test_fraktal_ab_harness_commands import Socket

APP = profile.application()


class Capture(unittest.TestCase):
    def test_core_capture_uses_live_revision_identity_and_ignorable_candidate(self):
        with patch.object(capture, 'APP', APP), patch.object(views, 'revision', return_value=71), \
                patch.object(capture.mb, 'resolve_batch', side_effect=AssertionError('legacy encoder')), \
                patch.object(capture.px, 'command', return_value={'accepted': True}) as command:
            capture.capture(object(), 4)
        self.assertEqual(command.call_args.kwargs, dict(settle=4, TargetPath='Press', NameValue=capture.KEY,
            IntValue=71, BoolValue=False, TextValue='999999', User='phase6-fixture'))

    def test_explicit_stale_revision_and_foreign_scope_reach_the_plc_unchanged(self):
        with patch.object(capture, 'APP', APP), patch.object(views, 'revision', side_effect=AssertionError()), \
                patch.object(capture.px, 'command') as command:
            capture.capture(object(), 4, key='not.registered', revision=123, scope='Other')
        args = command.call_args.kwargs
        self.assertEqual((args['IntValue'], args['TargetPath'], args['NameValue']), (123, 'Other', 'not.registered'))

    def test_restoration_write_uses_typed_text_and_live_revision(self):
        with patch.object(phase5, 'APP', APP), patch.object(views, 'revision', return_value=19), \
                patch.object(phase5.px, 'command') as command:
            phase5.write_config(object(), capture.KEY, 950, 4)
        self.assertEqual(command.call_args.kwargs, dict(settle=4, TargetPath='Press', NameValue=capture.KEY,
            TextValue='950', IntValue=19, DurationMs=0))

    def test_raw_configuration_and_audit_are_accounted_not_projected(self):
        with patch.object(capture, 'APP', APP), patch.object(views, 'surface', return_value={'native': -1}) as read:
            self.assertEqual(capture.configuration('comm'), {'native': -1})
            self.assertEqual(capture.audit_rows('comm'), {'native': -1})
        self.assertEqual([c.args for c in read.call_args_list], [('comm', 'Cfg0'), ('comm', 'ConfigAudit')])

    def test_read_only_gateway_browses_without_committing_and_refuses_start(self):
        calls = []
        class Viewer:
            def read_configuration_page(self, root):
                calls.append(('read', root))
                return gateway.BatchReply(True, {'EntryCount': 1, 'Entries[1]/WriteKey': capture.KEY}, None)
            def write_batch(self, root, sequence, **args):
                calls.append(('write', root, sequence, args))
                return gateway.BatchReply(False, None, 'read only')
        @contextmanager
        def viewer(*args, **kwargs):
            try:
                yield Viewer()
            finally:
                calls.append('closed')
        with patch.object(capture, 'APP', APP), patch.object(views, 'viewer', viewer), \
                patch.object(capture.px, 'seed_sequence', return_value=0xffffffff):
            rows = asyncio.run(capture.viewer_rows(object(), '601FC87B', 4))
        self.assertTrue(all(row['passed'] for row in rows))
        self.assertEqual(calls, [('read', 'Press'), ('write', 'Press', 0, {'Kind': capture.mb.START}), 'closed'])

    def test_viewer_failure_or_changed_sequence_cannot_pass(self):
        for page, sequence in ((gateway.BatchReply(False, None, 'lost'), (5, 5, 5)),
                               (gateway.BatchReply(True, {'EntryCount': 1, 'Entries[1]/WriteKey': capture.KEY}, None), (5, 6, 6))):
            @contextmanager
            def viewer(*args, **kwargs):
                yield NS(read_configuration_page=lambda root: page,
                         write_batch=lambda *a, **k: gateway.BatchReply(False, None, 'read only'))
            with patch.object(capture, 'APP', APP), patch.object(views, 'viewer', viewer), \
                    patch.object(capture.px, 'seed_sequence', side_effect=sequence):
                rows = asyncio.run(capture.viewer_rows(object(), '601FC87B', 4))
            self.assertFalse(all(row['passed'] for row in rows))


class ReadOnlyRpc(unittest.TestCase):
    def test_read_only_rpc_has_no_command_arguments_and_uses_same_framing(self):
        socket = Socket([lambda request: dict(id=request['id'], ok=True, result={'EntryCount': 2})])
        client = gateway.GatewayCommands('ws://127.0.0.1:8080/fraktal', connect=lambda *a, **k: socket)
        try:
            self.assertEqual(client.read_configuration_page('Press', 2).result, {'EntryCount': 2})
            self.assertEqual(socket.sent, [dict(protocol=gateway.PROTOCOL, id=1, method='readConfigurationPage',
                                                params=dict(root='Press', model=2))])
        finally:
            client.close()
        self.assertTrue(socket.closed)

    def test_bad_model_refuses_before_connect_and_failed_rpc_never_retries(self):
        socket = Socket(fail=OSError('gone'))
        calls = []
        client = gateway.GatewayCommands('ws://127.0.0.1:8080/fraktal',
                                        connect=lambda *a, **k: (calls.append(1) or socket))
        for model in (True, -1, 1.0):
            with self.assertRaises(ValueError):
                client.read_configuration_page('Press', model)
        self.assertEqual(calls, [])
        with self.assertRaises(gateway.GatewayCommandUnavailable):
            client.read_configuration_page('Press')
        with self.assertRaises(gateway.GatewayCommandUnavailable):
            client.read_configuration_page('Press')
        self.assertEqual(calls, [1])
        self.assertTrue(socket.closed)


class PublishedMetadata(unittest.TestCase):
    def session(self, *, count=2, changed=False, duplicate=False):
        prefix = 'IndependentCatalogue/ReadView'
        values = {prefix + '/DefinitionCount': count}
        for i in range(count):
            for name, value in dict(WriteKey=capture.KEY if i == 1 or duplicate else 'other.key',
                                    CaptureSource='Profiler.LastWork', CanCapture=True).items():
                values[f'{prefix}/Definitions[{i}]/{name}'] = value
        class Reader:
            _manifest = {'readServices': [dict(RootSymbol='Press', Kind=1, Version=1, CanonicalRoot=prefix)]}
            calls = []
            def read_row(self, paths):
                self.calls.append(paths)
                found = {p: values[p] for p in paths}
                if changed and len(self.calls) > 1:
                    found[prefix + '/DefinitionCount'] += 1
                return {'values': found}
        return NS(reader=Reader(), root='Press')

    def test_definition_reads_follow_published_root_and_one_owner_proof(self):
        session = self.session()
        with patch.object(views, '_session', return_value=session):
            definition = views.capture_definition(object(), capture.KEY, app=APP)
        self.assertEqual(definition, dict(WriteKey=capture.KEY, CaptureSource='Profiler.LastWork', CanCapture=True))
        self.assertEqual(len(session.reader.calls), 2)
        self.assertEqual(len(session.reader.calls[1]), 7)
        self.assertTrue(all(path.startswith('IndependentCatalogue/ReadView/')
                            for paths in session.reader.calls for path in paths))

    def test_changed_count_or_ambiguous_key_never_returns_a_definition(self):
        for session in (self.session(changed=True), self.session(duplicate=True), self.session(count=0)):
            with patch.object(views, '_session', return_value=session), self.assertRaises(ValueError):
                views.capture_definition(object(), capture.KEY, app=APP)

    def test_refusal_keys_come_from_live_binding_not_generator_ordinals(self):
        session = NS(root='Press', reader=NS(command_keys=lambda root: {'known.reason': 731}))
        with patch.object(views, '_session', return_value=session):
            self.assertEqual(views.numeric_key(object(), 'known.reason', app=APP), 731)
            with self.assertRaisesRegex(ValueError, 'absent'):
                views.numeric_key(object(), 'missing.reason', app=APP)


if __name__ == '__main__':
    unittest.main()
