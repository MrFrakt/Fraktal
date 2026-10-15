"""Reject incomplete or ambiguous recovery observations before reporting a pass."""
import importlib.util
import json
import pathlib
import tempfile
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / "Spikes/S11_Graph/Recovery/verify.py"
SPEC = importlib.util.spec_from_file_location("s11_recovery_verify", PATH)
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class RecoveryHarvestTests(unittest.TestCase):
    def test_missing_and_wrong_type_cannot_pass(self):
        with self.assertRaisesRegex(ValueError, "missing tag"):
            VERIFY.require({}, "Execute", False)
        with self.assertRaisesRegex(ValueError, "expected"):
            VERIFY.require({"Execute": 0}, "Execute", False)

    def test_duplicate_observation_cannot_pass(self):
        row = json.dumps({"event": "tag", "name": "S11Recovery.Arm", "value": False})
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "read.log"
            path.write_text(row + "\n" + row + "\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                VERIFY.tags(path)

    def test_idle_rejects_ready_with_an_energized_coil(self):
        values = {"S11Recovery.State": 10, "S11Recovery.Arm": False,
                  "S11Recovery.ErrGraph": False, "S11Recovery.StayedIdle": True,
                  "S11Recovery.RestartDropped": True, "S11Recovery.IdleScans": 1}
        for child in "AB":
            for leaf in ("Execute", "Busy", "Error"):
                values["S11Recovery.Root.Cyl" + child + "." + leaf] = False
            for leaf in ("Extend", "Retract"):
                values["S11Recovery.Hal.Cyl" + child + "." + leaf] = False
        VERIFY.idle(values)
        values["S11Recovery.Hal.CylA.Extend"] = True
        with self.assertRaisesRegex(ValueError, "Hal.CylA.Extend"):
            VERIFY.idle(values)


if __name__ == "__main__":
    unittest.main()
