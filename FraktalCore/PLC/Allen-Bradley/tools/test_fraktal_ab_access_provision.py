"""Commissioning emits hashes; the hardware fixture must always restore policy."""
import contextlib
import io
import unittest
from unittest.mock import AsyncMock, Mock, patch

import fraktal_ab_access as access
import fraktal_ab_access_provision as provision
import fraktal_ab_phase6_access_execute as fixture


class Provisioning(unittest.TestCase):
    def test_fresh_salts_and_tc3_hash_without_plaintext_output(self):
        first = provision.registration('test-admin', 4, 'test-only-pin')
        second = provision.registration('test-admin', 4, 'test-only-pin')
        self.assertNotEqual(first.salt, second.salt)
        self.assertEqual(first.pin_hash, access.pin_hash(bytes.fromhex(first.salt), b'test-only-pin').hex())
        output = io.StringIO()
        with patch.object(provision.getpass, 'getpass', return_value='test-only-pin'), contextlib.redirect_stdout(output):
            self.assertEqual(provision.main(['test-admin', '--level', '4']), 0)
        self.assertNotIn('test-only-pin', output.getvalue())
        self.assertIn('access.User(', output.getvalue())

    def test_bad_pin_or_registration_is_rejected(self):
        for pin in ('', 'p' * 33, '\n', '\u00e9'):
            with self.assertRaises(ValueError):
                provision.registration('test-admin', 4, pin)
        for name, level in (('', 4), ('x' * 33, 4), ('valid', 0), ('valid', 5)):
            with self.assertRaises(ValueError):
                provision.registration(name, level, 'test-only-pin')


class Restoration(unittest.IsolatedAsyncioTestCase):
    async def test_policy_failure_does_not_skip_remaining_gates_value_timeout_or_logout(self):
        client = Mock()
        admin = {'user': 'test-admin', 'level': 4}
        authenticated = {'CurrentLevel': 4, 'UserLength': 10, 'UserBytes': list(b'test-admin'), 'LoginFailed': 0}
        client.login = AsyncMock(return_value=({'accepted': True}, authenticated))
        client.command = AsyncMock(side_effect=[RuntimeError('first gate failed')] + [{'accepted': True}] * 13)
        client.write_config = AsyncMock(return_value={'accepted': True})
        client.native.return_value = {'accepted': True}
        original = {'Required': [0] * 12, 'SessionTimeout': 0, 'station.number': 1}
        evidence = {}
        state = {'Required': [0] * 12, 'SessionTimeout': 0, 'CurrentLevel': 0, 'UserLength': 0}
        with patch.object(fixture.projection, 'read_access', return_value=state), patch.object(fixture.sets_fixture, 'station_values', return_value={'station.number': 1}):
            self.assertFalse(await fixture.restore(client, original, admin, evidence))
        self.assertEqual(client.command.await_count, 14)
        client.write_config.assert_awaited_once()
        self.assertEqual(client.command.await_args_list[-1].args, (fixture.mb.LOGOUT,))

    async def test_native_probe_checks_serial_before_any_write(self):
        client = fixture.Client.__new__(fixture.Client)
        client.comm, client.serial, client.directory = Mock(), '7036B510', 'unused'
        with patch.object(fixture.projection, 'verify_serial', return_value=('other', False)), patch.object(fixture.px, 'command') as write:
            with self.assertRaises(ValueError):
                client.native(fixture.mb.SET_MODE, IntValue=0)
            write.assert_not_called()
