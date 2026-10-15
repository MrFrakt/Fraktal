"""A wrong target or identification must never send a control request."""
import contextlib
import io
import unittest
from unittest.mock import Mock

import s7_bench_mode as mode


class Guards(unittest.TestCase):
    def test_native_stop_state_is_recognized(self):
        for code, expected in ((3, "stop"), (4, "stop"), (6, "startup"), (8, "run")):
            session = Mock()
            session.szl.return_value = [bytes((2, 81, 255, code))]
            self.assertEqual(mode.state(session), expected)

    def test_wrong_address_is_rejected_before_identification(self):
        session = Mock()
        with self.assertRaises(ValueError):
            mode.change(session, "stop", "192.168.0.11")
        session.szl.assert_not_called()
        session._send_dt.assert_not_called()

    def test_wrong_order_or_firmware_never_sends_control(self):
        valid = b"\x00\x07" + mode.ORDER.encode().ljust(20) + b"\x00\x00" + mode.FIRMWARE
        for record in (valid.replace(b"214", b"215"), valid[:-1] + b"\x04", b"", None):
            session = Mock()
            session.szl.return_value = [record] if record is not None else None
            with self.assertRaises(ValueError):
                mode.change(session, "stop", mode.HOST)
            session._send_dt.assert_not_called()

    def test_unrecognized_state_never_sends_control(self):
        valid = b"\x00\x07" + mode.ORDER.encode().ljust(20) + b"\x00\x00" + mode.FIRMWARE
        session = Mock()
        session.szl.side_effect = [[valid], [b"\x02\x51\xff\x00"]]
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
            mode.change(session, "stop", mode.HOST)
        session._send_dt.assert_not_called()

    def test_cpu_refusal_is_reported_without_replay(self):
        valid = b"\x00\x07" + mode.ORDER.encode().ljust(20) + b"\x00\x00" + mode.FIRMWARE
        session = Mock()
        session.szl.side_effect = [[valid], [b"\x02\x51\xff\x08"]]
        session._header.return_value = bytes(10)
        session._recv.return_value = b"\x02\xf0\x80" + bytes.fromhex("320200000004000000008104")
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "0x8104"):
            mode.change(session, "stop", mode.HOST)
        session._send_dt.assert_called_once()
