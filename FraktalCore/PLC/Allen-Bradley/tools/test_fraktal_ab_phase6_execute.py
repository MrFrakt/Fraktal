"""Fixture authorization, identity and restoration without a controller."""
import contextlib
import io
import json
import sys
import types
import unittest
from unittest.mock import patch

import fraktal_ab_phase6_execute as fixture


class HarnessGuards(unittest.TestCase):
    def invoke(self, *, serial='7036B510', fingerprint=True, armed=False,
               failure=False, restore_failure=False, disarm_failure=False, sets=False, access=False, data_classes=False, shelving=False):
        comm = types.SimpleNamespace()
        comm.GetModuleProperties = lambda _: types.SimpleNamespace(
            Status='Success', Value=types.SimpleNamespace(SerialNumber=serial))
        class Connection:
            def __enter__(self):
                return comm
            def __exit__(self, *args):
                return False
        success = {'accepted': True}
        output = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules, {'pylogix': types.SimpleNamespace(PLC=Connection)}))
            stack.enter_context(patch.object(fixture.px, 'fingerprint', return_value={'passed': fingerprint}))
            stack.enter_context(patch.object(fixture, 'read_rows', return_value=[{'passed': True}]))
            stack.enter_context(patch.object(fixture, 'configuration', return_value={'BaselineWorkMs': 950}))
            stack.enter_context(patch.object(fixture.px, 'read_unit', return_value={'Mode': 5, 'RunStyle': 0}))
            run = stack.enter_context(patch.object(fixture, 'run', side_effect=RuntimeError('fixture failed') if failure else None,
                                                   return_value={'passed': True}))
            if sets:
                import fraktal_ab_phase6_sets_execute as sf
                stack.enter_context(patch.object(sf, 'read_rows', return_value=[{'passed': True}]))
                run = stack.enter_context(patch.object(sf, 'run', side_effect=RuntimeError('fixture failed') if failure else None,
                                                      return_value={'passed': True}))
            if access:
                import fraktal_ab_phase6_access_execute as af
                stack.enter_context(patch.object(af, 'read_rows', return_value=[{'passed': True}]))
                run = stack.enter_context(patch.object(af, 'run', side_effect=RuntimeError('fixture failed') if failure else None,
                                                      return_value={'passed': True}))
            if data_classes:
                import fraktal_ab_phase6_data_execute as df
                stack.enter_context(patch.object(df, 'read_rows', return_value=[{'passed': True}]))
                run = stack.enter_context(patch.object(df, 'run', side_effect=RuntimeError('fixture failed') if failure else None,
                                                      return_value={'passed': True}))
            if shelving:
                import fraktal_ab_phase6_shelving_execute as sf
                stack.enter_context(patch.object(sf, 'read_rows', return_value=[{'passed': True}]))
                run = stack.enter_context(patch.object(sf, 'run', side_effect=RuntimeError('fixture failed') if failure else None,
                                                      return_value={'passed': True}))
            write = stack.enter_context(patch.object(fixture.px, 'write', return_value=True))
            stack.enter_context(patch.object(fixture.px, '_idle'))
            baseline = stack.enter_context(patch.object(fixture.phase5, 'write_config',
                                                         side_effect=RuntimeError('restore failed') if restore_failure else None,
                                                         return_value=success))
            command = stack.enter_context(patch.object(fixture.px, 'command', return_value=success))
            disarm = stack.enter_context(patch.object(fixture.px, 'disarm', return_value={'fixture': 'FAILED' if disarm_failure else 'cleared'}))
            with contextlib.redirect_stdout(output):
                status = fixture.main(['test-host', '--expect-serial', '7036B510'] + (['--execute-fixture'] if armed else []) + (['--sets'] if sets else []) + (['--access'] if access else []) + (['--data-classes'] if data_classes else []) + (['--shelving'] if shelving else []))
        return status, json.loads(output.getvalue()), (run, write, baseline, command, disarm)

    def test_wrong_serial_or_fingerprint_writes_nothing(self):
        for args in ({'serial': 'DEADBEEF'}, {'fingerprint': False}):
            status, evidence, calls = self.invoke(armed=True, **args)
            self.assertEqual(status, 1)
            self.assertFalse(evidence['wrote'])
            for call in calls:
                call.assert_not_called()

    def test_unarmed_mode_reads_only(self):
        status, evidence, calls = self.invoke()
        self.assertEqual(status, 0)
        self.assertFalse(evidence['wrote'])
        for call in calls:
            call.assert_not_called()

    def test_failure_still_restores_all_original_values_and_disarms(self):
        status, evidence, (_, write, baseline, command, disarm) = self.invoke(armed=True, failure=True)
        self.assertEqual(status, 1)
        self.assertEqual(evidence['error'], 'fixture failed')
        self.assertEqual(evidence['restored'], evidence['original'])
        write.assert_called_once()
        baseline.assert_called_once()
        self.assertEqual(command.call_count, 2)
        disarm.assert_called_once()

    def test_restore_failure_does_not_skip_other_restorations_or_disarm(self):
        status, evidence, (_, _, _, command, disarm) = self.invoke(armed=True, restore_failure=True)
        self.assertEqual(status, 1)
        self.assertFalse(evidence['restore']['baseline']['accepted'])
        self.assertEqual(command.call_count, 2)
        disarm.assert_called_once()

    def test_uncleared_fixture_fails_the_evidence(self):
        status, evidence, _ = self.invoke(armed=True, disarm_failure=True)
        self.assertEqual(status, 1)
        self.assertFalse(evidence['passed'])

    def test_sets_variant_retains_serial_fingerprint_and_explicit_arm(self):
        for args in ({'serial': 'DEADBEEF', 'armed': True}, {'fingerprint': False, 'armed': True}, {'armed': False}):
            status, evidence, calls = self.invoke(sets=True, **args)
            self.assertFalse(evidence['wrote'])
            for call in calls:
                call.assert_not_called()

    def test_sets_failure_still_runs_parent_restoration_and_disarm(self):
        status, evidence, (_, _, baseline, command, disarm) = self.invoke(sets=True, armed=True, failure=True)
        self.assertEqual(status, 1)
        baseline.assert_called_once()
        self.assertEqual(command.call_count, 2)
        disarm.assert_called_once()

    def test_access_variant_retains_serial_fingerprint_and_explicit_arm(self):
        for args in ({'serial': 'DEADBEEF', 'armed': True}, {'fingerprint': False, 'armed': True}, {'armed': False}):
            status, evidence, calls = self.invoke(access=True, **args)
            self.assertFalse(evidence['wrote'])
            for call in calls:
                call.assert_not_called()

    def test_access_failure_still_runs_parent_restoration_and_disarm(self):
        status, evidence, (_, _, baseline, command, disarm) = self.invoke(access=True, armed=True, failure=True)
        self.assertEqual(status, 1)
        baseline.assert_called_once()
        self.assertEqual(command.call_count, 2)
        disarm.assert_called_once()

    def test_data_variant_retains_serial_fingerprint_and_explicit_arm(self):
        for args in ({'serial': 'DEADBEEF', 'armed': True}, {'fingerprint': False, 'armed': True}, {'armed': False}):
            status, evidence, calls = self.invoke(data_classes=True, **args)
            self.assertFalse(evidence['wrote'])
            for call in calls:
                call.assert_not_called()

    def test_data_failure_still_runs_parent_restoration_and_disarm(self):
        status, evidence, (_, _, baseline, command, disarm) = self.invoke(data_classes=True, armed=True, failure=True)
        self.assertEqual(status, 1)
        baseline.assert_called_once()
        self.assertEqual(command.call_count, 2)
        disarm.assert_called_once()

    def test_shelving_variant_retains_serial_fingerprint_and_explicit_arm(self):
        for args in ({'serial': 'DEADBEEF', 'armed': True}, {'fingerprint': False, 'armed': True}, {'armed': False}):
            status, evidence, calls = self.invoke(shelving=True, **args)
            self.assertFalse(evidence['wrote'])
            for call in calls:
                call.assert_not_called()

    def test_shelving_failure_still_runs_parent_restoration_and_disarm(self):
        status, evidence, (_, _, baseline, command, disarm) = self.invoke(shelving=True, armed=True, failure=True)
        self.assertEqual(status, 1)
        baseline.assert_called_once()
        self.assertEqual(command.call_count, 2)
        disarm.assert_called_once()

    def test_shelving_rechecks_identity_before_each_primitive_write(self):
        import fraktal_ab_phase6_shelving_execute as sf
        comm = types.SimpleNamespace(Write=unittest.mock.Mock(return_value='accepted'))
        wrapper = sf.GuardedPLC(comm, '7036B510')
        with patch.object(sf.projection, 'verify_serial', side_effect=[('7036B510', True), ('DEADBEEF', False)]):
            self.assertEqual(wrapper.Write('fixture', 1), 'accepted')
            with self.assertRaisesRegex(ValueError, 'serial changed'):
                wrapper.Write('fixture', 0)
        comm.Write.assert_called_once_with('fixture', 1)

    def test_shelving_cleanup_failure_still_restores_other_gates_and_owner(self):
        import asyncio
        import fraktal_ab_generate as gen
        import fraktal_ab_st_model as st
        import fraktal_ab_phase6_shelving_execute as sf
        admin = {'user': 'fixture-admin', 'level': 4}
        operator = {'user': 'fixture-operator', 'level': 1}
        state = {'Required': [0] * 12, 'SessionTimeout': 0, 'CurrentLevel': 4,
                 'UserLength': len(admin['user']), 'UserBytes': list(admin['user'].encode('ascii')),
                 'LoginFailed': 0}
        active = st.structure(gen.alarm_active_members())
        active['ActState'][0], active['ActReasonCode'][0] = gen.ALARM_OPEN, sf.STANDING
        calls = []
        class Client:
            login_timings = []
            def __init__(self, *args):
                self.logins = 0
            async def login(self, account):
                self.logins += 1
                if self.logins == 1:
                    raise RuntimeError('body abort')
                calls.append('login')
                return {'accepted': True}, state
            async def command(self, kind, **args):
                calls.append((kind, args))
                if kind == sf.mb.SET_ACCESS_LEVEL and args['IntValue'] == 0:
                    raise RuntimeError('gate restore failed')
                return {'accepted': True}
        evidence = {}
        with patch.object(sf.users, 'credentials', return_value={4: admin, 1: operator}), \
             patch.object(sf.users, 'Client', Client), \
             patch.object(sf.projection, 'read_access', return_value=state), \
             patch.object(sf.projection, 'read_alarm_log', return_value=(active, {})):
            with self.assertRaisesRegex(RuntimeError, 'body abort'):
                asyncio.run(sf.fixture(object(), '7036B510', 4, [], evidence, 'unused'))
        self.assertFalse(evidence['shelving_cleanup_passed'])
        self.assertFalse(evidence['shelving_restore']['gate_0']['accepted'])
        self.assertTrue(evidence['shelving_restore']['gate_11']['accepted'])
        self.assertTrue(evidence['shelving_restore']['timeout']['accepted'])
        self.assertTrue(evidence['shelving_restore']['original_session']['accepted'])
        self.assertEqual(calls.count('login'), 2)

    def test_shelving_cannot_be_combined_with_another_fixture(self):
        for other in ('--sets', '--access', '--data-classes'):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                fixture.main(['test-host', '--expect-serial', '7036B510', '--shelving', other])
            self.assertEqual(raised.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
