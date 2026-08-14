import argparse
import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("fraktal_ab_transport_budget_probe.py")
SPEC = importlib.util.spec_from_file_location("fraktal_ab_transport_budget_probe", MODULE_PATH)
assert SPEC and SPEC.loader
PROBE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PROBE
SPEC.loader.exec_module(PROBE)


class TransportBudgetProbeTests(unittest.TestCase):
    def test_serial_and_csv_validation(self):
        self.assertEqual(PROBE._serial("0x7036b510"), "7036B510")
        self.assertEqual(PROBE._csv_ints("128,500,500", 128, 4002), (128, 500))
        with self.assertRaises(argparse.ArgumentTypeError):
            PROBE._serial("bad")
        with self.assertRaises(argparse.ArgumentTypeError):
            PROBE._csv_ints("1,500", 128, 4002)

    def test_latency_summary(self):
        self.assertEqual(
            PROBE._latency_summary([3.0, 1.0, 2.0]),
            {"minimum_ms": 1.0, "median_ms": 2.0, "maximum_ms": 3.0},
        )

    def test_surface_is_fixed_read_only_fixture(self):
        self.assertEqual(
            {PROBE.LARGE_TAG, PROBE.HEARTBEAT_TAG, PROBE.COMPLETE_TAG},
            {"FRK_WriteLargeArray[0]", "FRK_Heartbeat", "FRK_TestComplete"},
        )


if __name__ == "__main__":
    unittest.main()
