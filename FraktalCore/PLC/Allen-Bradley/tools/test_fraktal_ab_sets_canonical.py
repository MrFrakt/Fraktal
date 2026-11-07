"""C5b2 operator path, independent observations and cleanup failure boundaries."""
import asyncio
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, Mock, patch

import fraktal_ab_phase6_sets_execute as fixture
import fraktal_ab_press_s6_collapse_echo38 as profile
import fraktal_ab_fixture_reads as views
import fraktal_ab_harness_documents as documents
import fraktal_ab_harness_host as host
import fraktal_ab_harness_commands as gateway
import fraktal_ab_part_execute as part
import test_fraktal_ab_phase6_execute as legacy_fixture

APP = profile.application()


class Commands(unittest.IsolatedAsyncioTestCase):
    def make(self):
        client = fixture.Client.__new__(fixture.Client)
        client.comm = object()
        client._own_host = False
        client.host = NS(serial='601FC87B', guard=Mock(return_value=True))
        return client

    async def test_operator_request_uses_core_once_and_store_waits_for_receipt(self):
        client = self.make()
        client.wait_store = Mock()
        with patch.object(fixture, 'APP', APP), patch.object(fixture.px, 'command', return_value={'accepted': True}) as send, \
                patch.object(fixture.gateway, 'MailboxWriter', side_effect=AssertionError('legacy writer')):
            await client.command(fixture.mb.SAVE_CONFIG_SET, TextValue='phase6-station', IntValue=1)
        self.assertEqual(send.call_count, 1)
        self.assertEqual(send.call_args.kwargs, dict(settle=4, User='phase6-fixture', TextValue='phase6-station', IntValue=1))
        client.wait_store.assert_called_once()

    async def test_partial_import_has_no_store_wait_and_caller_user_is_preserved(self):
        client = self.make()
        client.wait_store = Mock()
        with patch.object(fixture, 'APP', APP), patch.object(fixture.px, 'command', return_value={'accepted': True}) as send:
            await client.command(fixture.mb.IMPORT_CONFIG_SET, BoolValue=0, TextValue='piece')
            await client.command(fixture.mb.LOGIN, User='operator', Secret='synthetic')
            self.assertEqual(send.call_args.kwargs['User'], 'operator')
        client.wait_store.assert_not_called()

    async def test_failed_adapter_blocks_sets_but_not_explicit_ordinary_cleanup(self):
        client = self.make()
        client.host.guard.return_value = False
        with patch.object(fixture, 'APP', APP), patch.object(fixture.px, 'command', return_value={'accepted': True}) as send:
            with self.assertRaisesRegex(RuntimeError, 'no command written'):
                await client.command(fixture.mb.LOAD_CONFIG_SET, TextValue='phase6-station')
            send.assert_not_called()
            await client.command(fixture.mb.OPERATOR_RESET)
            self.assertEqual(send.call_count, 1)
            with self.assertRaises(ValueError):
                await client.command(fixture.mb.LIST_CONFIG_SETS, state=object())

    async def test_typed_restore_uses_the_current_controller_revision(self):
        client = self.make()
        client.command = AsyncMock(return_value={'accepted': True})
        with patch.object(fixture, 'APP', APP), patch.object(views, 'revision', return_value=991):
            await client.write_config('station.number', 41)
        self.assertEqual(client.command.await_args.kwargs,
            dict(TargetPath='Press', IntValue=991, NameValue='station.number', TextValue='41', DurationMs=0))

    async def test_exports_and_catalog_reads_use_independent_cip_not_python_state(self):
        client = self.make()
        client.command = AsyncMock(return_value={'accepted': True})
        values = {'Press/ConfigSetDocumentLine': 0, 'Press/ConfigSetDocumentLines': 0,
                  'Press/ConfigSetDocument': '{"set":"one","root":"Press","schema":1,"configRev":7,"kind":1,"model":"","records":0,"created":0,"clock":0}'}
        with patch.object(fixture, 'APP', APP), patch.object(views, 'values', return_value=values) as read:
            result = await client.export_document('one')
        self.assertEqual(result[0]['set'], 'one')
        self.assertEqual(read.call_count, 1)
        self.assertEqual(set(read.call_args.args[1]), set(values))
        self.assertFalse(hasattr(client, 'state'))

    async def test_real_read_only_gateway_refusal_subject_has_no_native_commit(self):
        client = self.make()
        @contextmanager
        def viewer(*args, **kwargs):
            yield NS(write_batch=Mock(return_value=gateway.BatchReply(False, None, 'read only')))
        with patch.object(fixture, 'APP', APP), patch.object(views, 'viewer', viewer), \
                patch.object(fixture.px, 'seed_sequence', return_value=8):
            self.assertTrue(await client.viewer_refuses())


class Persistence(unittest.TestCase):
    def make(self):
        client = fixture.Client.__new__(fixture.Client)
        client.comm = object()
        client.host = NS(serial='601FC87B', guard=lambda **target: True)
        return client

    def status(self, pending, failed=False):
        return {'Press/ConfigPersist/Pending': pending, 'Press/ConfigPersist/Failed': failed,
                'Press/ConfigPersist/WindowMs': 5000}

    def test_ack_is_not_enough_the_pending_store_receipt_must_complete(self):
        client = self.make()
        client.values = Mock(side_effect=[self.status(True), self.status(True), self.status(False)])
        with patch.object(fixture, 'APP', APP), patch.object(fixture.time, 'sleep'):
            client.wait_store()
        self.assertEqual(client.values.call_count, 3)

    def test_failure_or_window_expiry_cannot_be_called_durable(self):
        client = self.make()
        client.values = Mock(return_value=self.status(False, True))
        with patch.object(fixture, 'APP', APP), self.assertRaises(RuntimeError):
            client.wait_store()
        client.values = Mock(return_value=self.status(True))
        with patch.object(fixture, 'APP', APP), patch.object(fixture.time, 'monotonic', side_effect=[0, 6]), \
                self.assertRaises(TimeoutError):
            client.wait_store()

    def test_original_restore_entry_uses_dart_and_never_constructs_the_python_keeper(self):
        run = part.Run.__new__(part.Run)
        run.comm, run.app, run.evidence = object(), APP, {}
        with patch.object(documents, 'restore_configuration', return_value={'restoring': False}) as restore, \
                patch.object(part.live, 'Keeper', side_effect=AssertionError('Python keeper')):
            run.restore_configuration()
        restore.assert_called_once_with(run.comm, APP)
        self.assertEqual(run.evidence['configuration'], {'restoring': False})

    def test_full_record_comparison_refuses_an_unaccounted_partial_fixture(self):
        with patch.object(views, '_session', return_value=None), self.assertRaisesRegex(ValueError, 'collapsed fixture'):
            views.read_records(object(), app=APP)
        session = NS(fields={'Cfg0': ('SchemaVersion',)}, surface=Mock())
        with patch.object(views, '_session', return_value=session), self.assertRaisesRegex(ValueError, 'every original'):
            views.read_records(object(), app=APP)
        session.surface.assert_not_called()

    def test_failed_restore_start_is_armed_before_any_adapter_write_can_occur(self):
        runner = legacy_fixture.HarnessGuards('test_unarmed_mode_reads_only')
        with patch.object(legacy_fixture.fixture, 'APP', APP), \
                patch.object(documents, 'restore_configuration', side_effect=RuntimeError('adapter failed')):
            status, evidence, (run, write, baseline, command, disarm) = runner.invoke(armed=True)
        self.assertEqual(status, 1)
        self.assertTrue(evidence['wrote'])
        self.assertEqual(evidence['error'], 'adapter failed')
        self.assertIn('published V6.11 host bindings', evidence['write_surface'])
        run.assert_not_called()
        write.assert_not_called()

    def test_failure_in_one_final_check_still_checks_the_original_medium_and_closes(self):
        client = NS(comm=object(), store=NS(directory=Path('unused')),
                    host=NS(originals_unchanged=Mock(return_value=True)), close=Mock())
        original = {'station.number': 41}
        evidence = {}
        async def restore(c, o, settle, target):
            target['sets_restore_passed'] = True
        with patch.object(fixture, 'APP', APP), patch.object(fixture, 'Client', return_value=client), \
                patch.object(fixture, 'station_values', return_value=original), \
                patch.object(fixture, 'read_records', side_effect=[{'one': 1}, RuntimeError('read failed')]), \
                patch.object(fixture, 'exercise', AsyncMock(side_effect=RuntimeError('case failed'))), \
                patch.object(fixture, 'restore', restore), \
                patch.object(documents, 'ready', return_value={'restoring': False}) as ready:
            with self.assertRaisesRegex(RuntimeError, 'case failed'):
                fixture.run(client.comm, '601FC87B', 4, [], evidence)
        client.host.originals_unchanged.assert_called_once()
        ready.assert_called_once()
        client.close.assert_called_once()
        self.assertFalse(evidence['sets_restore_passed'])
        self.assertIn('sets_all_records_restored', evidence['sets_final_check_errors'])


if __name__ == '__main__':
    unittest.main()
