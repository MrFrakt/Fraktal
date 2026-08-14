import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("fraktal_ab_time_probe.py")
SPEC = importlib.util.spec_from_file_location("fraktal_ab_time_probe", MODULE_PATH)
assert SPEC and SPEC.loader
PROBE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PROBE
SPEC.loader.exec_module(PROBE)


class Reply:
    def __init__(self, value, status="Success"):
        self.Value = value
        self.Status = status


class Device:
    ProductName = "fixture"
    Revision = "33.14"
    SerialNumber = "11111111"


class WrongController:
    def __init__(self):
        self.set_calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def GetDeviceProperties(self):
        return Reply(Device())

    def SetPLCTime(self, dst=0):
        self.set_calls += 1
        raise AssertionError("serial guard allowed clock set")


class Factory:
    def __init__(self):
        self.controller = WrongController()

    def __call__(self, target):
        return self.controller


class S2Controller:
    SocketTimeout = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def GetDeviceProperties(self):
        device = Device()
        device.SerialNumber = "7036B510"
        return Reply(device)

    def Read(self, tag):
        if tag == "FRK_S2_Complete":
            return Reply(True)
        return Reply(None, "Path segment error")

    def GetPLCTime(self, raw=True):
        return Reply(0)


class TimeProbeTests(unittest.TestCase):
    def test_serial_mismatch_prevents_clock_set(self):
        factory = Factory()
        evidence = PROBE.run_probe(factory, "192.0.2.1", "7036B510", 1, True, 1)
        self.assertFalse(evidence["passed"])
        self.assertEqual(factory.controller.set_calls, 0)

    def test_iso_is_utc(self):
        self.assertEqual(PROBE._iso(0), "1970-01-01T00:00:00Z")

    def test_s2_fixture_is_an_explicit_clock_read_fingerprint(self):
        evidence = PROBE.run_probe(
            lambda _: S2Controller(), "192.0.2.1", "7036B510", 1, False, 1
        )
        self.assertTrue(evidence["passed"])
        self.assertEqual(
            evidence["fixture_fingerprint"]["fixture"], "s2-nested-aoi"
        )


if __name__ == "__main__":
    unittest.main()
