import argparse
import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("fraktal_ab_phase0_execute.py")
SPEC = importlib.util.spec_from_file_location("fraktal_ab_phase0_execute", MODULE_PATH)
assert SPEC and SPEC.loader
EXECUTE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXECUTE
SPEC.loader.exec_module(EXECUTE)


class Reply:
    def __init__(self, value, status="Success"):
        self.Value = value
        self.Status = status


class Device:
    ProductName = "1769-L24ER-QB1B/A LOGIX5324ER"
    Revision = "33.14"
    SerialNumber = "11111111"


class WrongController:
    def __init__(self):
        self.writes = []

    def GetDeviceProperties(self):
        return Reply(Device())

    def Write(self, tag, value):
        self.writes.append((tag, value))
        raise AssertionError("serial guard allowed a write")


class Phase0ExecutionTests(unittest.TestCase):
    def test_checksum_matches_fixture_equation(self):
        self.assertEqual(EXECUTE._expected_checksum(), 87151)
        self.assertEqual(EXECUTE._expected_large_checksum(), 55047)

    def test_serial_mismatch_prevents_every_write(self):
        controller = WrongController()
        evidence = EXECUTE.execute_fixture(controller, "7036B510", settle_seconds=0)
        self.assertFalse(evidence["execution_passed"])
        self.assertFalse(evidence["serial_matches"])
        self.assertEqual(controller.writes, [])

    def test_write_surface_is_fixed_fixture_memory_only(self):
        tags = [tag for tag, _ in EXECUTE.WRITE_VECTOR + EXECUTE.CLEANUP_VECTOR]
        self.assertTrue(all(
            tag.startswith("FRK_Write") or tag == EXECUTE.PROGRAM_WRITE_TAG
            for tag in tags
        ))
        self.assertFalse(any(tag.startswith(("Local:", "Discrete_IO:")) for tag in tags))

    def test_none_access_tag_must_be_hidden_from_browse(self):
        self.assertIn("FRK_NoAccess", EXECUTE.EXPECTED_TAGS)
        self.assertNotIn("FRK_NoAccess", EXECUTE.BROWSE_TAGS)

    def test_arm_flag_is_mandatory(self):
        with self.assertRaises(SystemExit):
            EXECUTE._arguments(["192.0.2.1", "--expect-serial", "7036B510"])

    def test_serial_validation(self):
        self.assertEqual(EXECUTE._normalize_serial("0x7036b510"), "7036B510")
        with self.assertRaises(argparse.ArgumentTypeError):
            EXECUTE._normalize_serial("not-a-serial")


if __name__ == "__main__":
    unittest.main()
