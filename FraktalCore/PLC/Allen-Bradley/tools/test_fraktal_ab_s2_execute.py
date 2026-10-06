import unittest

from fraktal_ab_s2_execute import _arguments, _normalize_serial


class S2ExecutionToolTests(unittest.TestCase):
    def test_serial_is_normalized(self):
        self.assertEqual(_normalize_serial("0x7036b510"), "7036B510")

    def test_serial_must_be_exactly_eight_hex_digits(self):
        for value in ("", "7036B51", "7036B5100", "ZZZZZZZZ"):
            with self.subTest(value=value):
                with self.assertRaises(Exception):
                    _normalize_serial(value)

    def test_arm_flag_is_required(self):
        with self.assertRaises(SystemExit):
            _arguments(["192.0.2.1", "--expect-serial", "7036B510"])

    def test_no_arbitrary_tag_or_value_arguments(self):
        with self.assertRaises(SystemExit):
            _arguments([
                "192.0.2.1", "--expect-serial", "7036B510",
                "--execute-fixture", "--tag", "Arbitrary",
            ])


if __name__ == "__main__":
    unittest.main()
