"""The set fixture must restore each named field and file independently."""
import dataclasses
import unittest
from unittest.mock import AsyncMock, Mock, patch
import fraktal_ab_phase6_sets_execute as fixture


class ContractVersion(unittest.TestCase):
    def test_only_the_declared_version_is_accepted_with_or_without_line(self):
        ordinary = dataclasses.replace(fixture.APP, line=None,
            records=tuple(r for r in fixture.APP.records if not r.line_cfg))
        for app, expected in ((ordinary, 1), (fixture.APP, 3)):
            for observed in (1, 2, 3):
                with self.subTest(line=app.line is not None, observed=observed), \
                     patch.object(fixture, 'APP', app), \
                     patch.object(fixture.broker, 'read_state', return_value={
                         'SchemaVersion': observed, 'AuditSequence': [0] * fixture.sets.AUDIT_CAPACITY}), \
                     patch.object(fixture.projection, 'read_persist', return_value={'RestoreLost': 0}):
                    self.assertEqual(fixture.read_rows(object())[0]['passed'], observed == expected)


class Restoration(unittest.IsolatedAsyncioTestCase):
    async def test_a_failed_field_restore_does_not_skip_other_fields_or_file_cleanup(self):
        client = Mock()
        client.idle = AsyncMock()
        client.write_config = AsyncMock(side_effect=[RuntimeError('first restore failed'), {'accepted': True}])
        client.command = AsyncMock(return_value={'accepted': True})
        client.store.list.side_effect = [
            [{'set': name} for name in fixture.FIXTURE_NAMES]
            for _ in fixture.FIXTURE_NAMES] + [[]]
        original = {'station.first': 1, 'station.second': 2}
        evidence = {}
        with patch.object(fixture, 'station_values', return_value=original):
            await fixture.restore(client, original, 4, evidence)
        self.assertEqual(client.write_config.await_count, 2)
        self.assertEqual(client.command.await_count, len(fixture.FIXTURE_NAMES))
        self.assertFalse(evidence['sets_restore_passed'])
        self.assertTrue(evidence['sets_store_empty'])


class MailboxOwnership(unittest.IsolatedAsyncioTestCase):
    async def test_idle_and_typed_writes_use_the_same_gateway_command_path(self):
        client = fixture.Client.__new__(fixture.Client)
        client.comm = Mock()
        client.command = AsyncMock(return_value={'accepted': True})
        with patch.object(fixture.px, 'write'), patch.object(fixture.px, 'command', side_effect=AssertionError('direct command bypassed the gateway')):
            await client.idle(4)
            await client.write_config('station.number', 41)
        self.assertEqual([call.args[0] for call in client.command.await_args_list],
            [fixture.mb.STOP, fixture.mb.OPERATOR_RESET, fixture.mb.SET_RUN_STYLE, fixture.mb.WRITE_CONFIG])
        payload = client.command.await_args_list[-1].kwargs
        self.assertEqual((payload['NameValue'], payload['TextValue'], payload['TargetPath']),
            ('station.number', '41', fixture.APP.name))
        self.assertEqual(payload['IntValue'], fixture.mf.config_revision(fixture.APP))
