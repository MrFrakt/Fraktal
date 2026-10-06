"""The hardware fixture waits for its own authoritative login result."""
import unittest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

import fraktal_ab_phase6_access_execute as fixture
import fraktal_ab_mailbox as mb


class LoginResult(unittest.IsolatedAsyncioTestCase):
    def client(self, accepted=True):
        client = object.__new__(fixture.Client)
        client.comm = object()
        client.login_timings = []
        client.command = AsyncMock(return_value={'accepted': accepted, 'sequence': 9})
        return client

    def state(self, sequence, busy=0, failed=0):
        user = b'fixture-admin'
        return dict(LoginResultSequence=sequence, LoginBusy=busy, LoginFailed=failed,
                    CurrentLevel=4, UserLength=len(user), UserBytes=list(user))

    async def test_old_failure_and_busy_result_cannot_settle_a_new_login(self):
        client = self.client()
        with patch.object(fixture.projection, 'read_access', side_effect=[
                self.state(8, failed=1), self.state(9, busy=1), self.state(9)]) as read:
            answer, state = await client.login({'user': 'fixture-admin', 'level': 4, 'pin': 'test-only'})
        self.assertEqual(read.call_count, 3)
        self.assertEqual(state['LoginResultSequence'], answer['sequence'])
        self.assertTrue(client.login_timings[0]['authenticated'])
        self.assertGreaterEqual(client.login_timings[0]['resultMs'], client.login_timings[0]['consumedMs'])
        self.assertFalse(any('pin' in str(key).lower() for key in client.login_timings[0]))

    async def test_consumption_refusal_is_not_a_previous_same_user_success(self):
        client = self.client(accepted=False)
        with patch.object(fixture.projection, 'read_access',
                          side_effect=AssertionError('a refused request has no new login result')) as read:
            with self.assertRaisesRegex(ValueError, 'refused'):
                await client.login({'user': 'fixture-admin', 'level': 4, 'pin': 'test-only'})
        read.assert_not_called()
        self.assertEqual(client.login_timings, [])


class NativeSequence(unittest.TestCase):
    def test_native_probe_after_gateway_command_cannot_replay_its_ack(self):
        client = object.__new__(fixture.Client)
        request = mb.request_tag_name(fixture.APP)
        response = mb.response_tag_name(fixture.APP)
        values = {request + '.Sequence': 10, response + '.AckSequence': 10,
                  response + '.Accepted': 1, response + '.DiagnosticKey': 0}
        writes = []
        def write(target, value):
            writes.append((target, value))
            if target == request + '.Sequence' and value > values[target]:
                values.update({target: value, response + '.AckSequence': value,
                               response + '.Accepted': 0, response + '.DiagnosticKey': 524})
            return SimpleNamespace(Status='Success')
        comm = SimpleNamespace(Read=lambda tag: SimpleNamespace(Status='Success', Value=values[tag]), Write=write)
        client.comm, client.serial, client.directory = comm, '7036B510', 'unused'
        # A gateway command seeded 9, then committed 10 independently. The
        # native probe must consume 11 rather than replay the successful 10.
        with patch.dict(fixture.px._SEQUENCE, {'value': 9}), \
                patch.object(fixture.projection, 'verify_serial', return_value=('7036B510', True)) as guard, \
                patch.object(fixture.Client, '__init__', return_value=None):
            answer = client.native(mb.SET_ACCESS_LEVEL, IntValue=8, TextValue='0', User='claimed-admin')
        guard.assert_called_once_with(comm, '7036B510')
        self.assertEqual(answer, {'sequence': 11, 'accepted': False, 'diagnosticKey': 524})
        self.assertEqual([value for target, value in writes if target == request + '.Sequence'], [11])
