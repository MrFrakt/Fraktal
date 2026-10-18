import contextlib
import io
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mb
import fraktal_ab_part_demo as fixture
import fraktal_ab_part_execute as live


class FixtureWriteBoundary(unittest.TestCase):
    def setUp(self):
        self.app = fixture.application()
        self.native = Mock(IPAddress='127.0.0.1', ProcessorSlot=0)
        self.identity = SimpleNamespace(SerialNumber='0x601FC87B',
            ProductName='Emulate 5580 Controller', Revision='38.11')
        self.native.GetDeviceProperties.return_value = SimpleNamespace(Status='Success', Value=self.identity)
        self.native.Write.return_value = SimpleNamespace(Status='Success')
        self.comm = live.Guarded(self.native, 0x601FC87B, self.app)
        self.target = next(iter(gen.externally_writable(self.app)))

    def test_wrong_serial_or_nonlocal_target_never_writes(self):
        for field, value in (('SerialNumber','0x12345678'), ('ProductName','Physical Controller'),
                             ('Revision','37.11')):
            with self.subTest(field=field):
                previous = getattr(self.identity, field)
                setattr(self.identity, field, value)
                with self.assertRaises(live.FixtureRefused):
                    self.comm.Write(self.target, 0)
                setattr(self.identity, field, previous)
        self.native.IPAddress = '192.168.0.1'
        with self.assertRaises(live.FixtureRefused):
            self.comm.Write(self.target, 0)
        self.native.Write.assert_not_called()

    def test_provider_and_unlisted_set_members_never_reach_native_write(self):
        for target in ('FRK_Press_Carrier.ReadFailed', 'FRK_Press_Unit.Running',
                       mb.request_tag_name(self.app)+'.ConfigSet.Unlisted'):
            with self.assertRaises(live.FixtureRefused):
                self.comm.Write(target, 1)
        self.native.Write.assert_not_called()
        self.native.GetDeviceProperties.assert_not_called()

    def test_manifest_refusal_precedes_every_write(self):
        with patch.object(live.reader, '_read_raw', return_value=(b'x','Success',0)), \
             patch.object(live.reader, 'decode_header', return_value={}), \
             patch.object(live.projection, 'validate') as validate:
            self.comm.Write(self.target, 0)
            validate.side_effect = live.projection.ProjectionRefused('different image')
            with self.assertRaises(live.projection.ProjectionRefused):
                self.comm.Write(self.target, 1)
        self.assertEqual(self.native.GetDeviceProperties.call_count, 2)
        self.native.Write.assert_called_once_with(self.target, 0)

    def test_cli_requires_explicit_arm_before_opening_credentials(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            live.main(['--expect-serial','601FC87B','--credential-file','absent.json',
                       '--output','absent-output.json'])


if __name__ == '__main__':
    unittest.main()
