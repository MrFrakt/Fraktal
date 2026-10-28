import unittest

from fraktal_ab_s11_execute import (
    BROWSE_TAGS,
    EXPECTED_TRACE,
    HIDDEN_INSTANCES,
    _arguments,
    _normalize_serial,
    execute_fixture,
)


class Reply:
    def __init__(self, status: str = "Success", value=None):
        self.Status = status
        self.Value = value


class Device:
    ProductName = "1769-L24ER-QB1B/A"
    Revision = "33.14"

    def __init__(self, serial: str):
        self.SerialNumber = serial


class TagEntry:
    def __init__(self, name: str):
        self.TagName = name


class FakeController:
    """A scripted stand-in that answers the fixed vector's reads and writes.

    It models the fixture's observable outcome, not the controller: a run
    completes as soon as the command is written. That is enough to prove the
    probe's own pass/fail logic, including that it fails closed.
    """

    def __init__(self, serial: str = "7036B510", **faults):
        self.serial = serial
        self.faults = faults
        self.writes: list[tuple[str, object]] = []
        self.scan = 1000
        self.values: dict[str, object] = {
            "FRK_S11_Command": 0,
            "FRK_S11_ResetRequest": 0,
            "FRK_S11_Complete": True,
            "FRK_S11_ScanCount": self.scan,
            "FRK_S11_JsrCount": 0,
            "FRK_S11_SfrCount": 0,
            "FRK_S11_ParityOk": 1,
            "FRK_S11_OrderFail": 0,
        }
        for context in ("FRK_S11_StCtx", "FRK_S11_SfcCtx"):
            self.values.update(
                {
                    f"{context}.TraceCount": 0,
                    f"{context}.Done": 0,
                    f"{context}.Busy": 0,
                    f"{context}.ScansToComplete": 0,
                    f"{context}.LatencyScans": faults.get("latency", 1),
                    f"{context}.LatencyBad": 0,
                    f"{context}.ModuleScans": 500,
                    f"{context}.ModuleOrder": 1,
                    f"{context}.SeqOrder": 2 if not faults.get("bad_order") else 1,
                    f"{context}.RunCount": 0,
                    f"{context}.ResetCount": 0,
                    f"{context}.TraceOverflow": 0,
                }
            )

    # -- pylogix surface -------------------------------------------------
    def GetDeviceProperties(self):
        return Reply(value=Device(self.serial))

    def GetTagList(self, _programs):
        names = set(BROWSE_TAGS)
        if self.faults.get("expose_private"):
            names.update(HIDDEN_INSTANCES)
        if self.faults.get("missing_tag"):
            names.discard("FRK_S11_ParityOk")
        return Reply(value=[TagEntry(name) for name in sorted(names)])

    def Read(self, tag: str):
        # every read advances the modelled task scan so liveness checks pass
        self.scan += 1
        self.values["FRK_S11_ScanCount"] = self.scan
        for context in ("FRK_S11_StCtx", "FRK_S11_SfcCtx"):
            key = f"{context}.ModuleScans"
            self.values[key] = int(self.values[key]) + 1
        if tag not in self.values:
            return Reply(status="Path segment error")
        return Reply(value=self.values[tag])

    def Write(self, tag: str, value):
        self.writes.append((tag, value))
        if tag not in ("FRK_S11_Command", "FRK_S11_ResetRequest"):
            return Reply(status="Path segment error")
        if self.faults.get("cleanup_fails") and value == 0:
            return Reply(status="Path segment error")
        self.values[tag] = value
        if tag == "FRK_S11_Command" and value == 1:
            self._complete_run()
        if tag == "FRK_S11_ResetRequest" and value == 1:
            self._reset()
        return Reply()

    # -- modelled fixture behaviour --------------------------------------
    def _complete_run(self):
        trace = list(self.faults.get("trace", EXPECTED_TRACE))
        self.values["FRK_S11_SfrCount"] = int(self.values["FRK_S11_SfrCount"]) + 1
        self.values["FRK_S11_JsrCount"] = int(self.values["FRK_S11_JsrCount"]) + 5
        for context in ("FRK_S11_StCtx", "FRK_S11_SfcCtx"):
            self.values[f"{context}.RunCount"] = (
                int(self.values[f"{context}.RunCount"]) + 1
            )
            self.values[f"{context}.TraceCount"] = len(trace)
            for index, step in enumerate(trace):
                self.values[f"{context}.Trace[{index}]"] = step
            self.values[f"{context}.Done"] = 1
            self.values[f"{context}.Busy"] = 0
            self.values[f"{context}.ScansToComplete"] = 4
        if self.faults.get("scan_mismatch"):
            self.values["FRK_S11_SfcCtx.ScansToComplete"] = 7

    def _reset(self):
        for context in ("FRK_S11_StCtx", "FRK_S11_SfcCtx"):
            self.values[f"{context}.TraceCount"] = 0
            self.values[f"{context}.Done"] = 0
            self.values[f"{context}.ResetCount"] = (
                int(self.values[f"{context}.ResetCount"]) + 1
            )


class S11ExecutionArgumentTests(unittest.TestCase):
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

    def test_settle_budget_is_bounded(self):
        with self.assertRaises(SystemExit):
            _arguments([
                "192.0.2.1", "--expect-serial", "7036B510",
                "--execute-fixture", "--settle", "600",
            ])


class S11ExecutionVectorTests(unittest.TestCase):
    def test_healthy_fixture_passes_and_is_cleaned(self):
        controller = FakeController()
        evidence = execute_fixture(controller, "7036B510", settle=0.2)
        self.assertTrue(evidence["execution_passed"], evidence)
        self.assertEqual(len(evidence["runs"]), 2)
        self.assertTrue(evidence["cleanup"]["verified"])
        self.assertEqual(controller.values["FRK_S11_Command"], 0)
        self.assertEqual(controller.values["FRK_S11_ResetRequest"], 0)

    def test_only_the_two_declared_inputs_are_ever_written(self):
        controller = FakeController()
        execute_fixture(controller, "7036B510", settle=0.2)
        self.assertEqual(
            {tag for tag, _ in controller.writes},
            {"FRK_S11_Command", "FRK_S11_ResetRequest"},
        )

    def test_wrong_serial_writes_nothing(self):
        controller = FakeController(serial="DEADBEEF")
        evidence = execute_fixture(controller, "7036B510", settle=0.2)
        self.assertFalse(evidence["execution_passed"])
        self.assertIn("serial did not match", evidence["error"])
        self.assertEqual(controller.writes, [])

    def test_missing_fixture_tag_writes_nothing(self):
        controller = FakeController(missing_tag=True)
        evidence = execute_fixture(controller, "7036B510", settle=0.2)
        self.assertFalse(evidence["execution_passed"])
        self.assertIn("fingerprint failed", evidence["error"])
        self.assertEqual(controller.writes, [])

    def test_browsable_private_instance_writes_nothing(self):
        controller = FakeController(expose_private=True)
        evidence = execute_fixture(controller, "7036B510", settle=0.2)
        self.assertFalse(evidence["execution_passed"])
        self.assertEqual(controller.writes, [])

    def test_wrong_step_trace_fails(self):
        controller = FakeController(trace=(10, 2040, 1030, 50))
        evidence = execute_fixture(controller, "7036B510", settle=0.2)
        self.assertFalse(evidence["execution_passed"])
        failed = {
            item["case"]
            for run in evidence["runs"]
            for item in run["checks"]
            if not item["passed"]
        }
        self.assertIn("st_trace", failed)
        self.assertIn("sfc_trace", failed)

    def test_late_intent_consumption_fails(self):
        evidence = execute_fixture(FakeController(latency=2), "7036B510", settle=0.2)
        self.assertFalse(evidence["execution_passed"])
        failed = {
            item["case"]
            for run in evidence["runs"]
            for item in run["checks"]
            if not item["passed"]
        }
        self.assertIn("st_one_scan_latency", failed)

    def test_sequence_running_before_the_module_aoi_fails(self):
        evidence = execute_fixture(FakeController(bad_order=True), "7036B510", settle=0.2)
        self.assertFalse(evidence["execution_passed"])
        failed = {
            item["case"]
            for run in evidence["runs"]
            for item in run["checks"]
            if not item["passed"]
        }
        self.assertIn("st_module_ran_first", failed)

    def test_forms_disagreeing_on_scan_count_fails(self):
        evidence = execute_fixture(
            FakeController(scan_mismatch=True), "7036B510", settle=0.2
        )
        self.assertFalse(evidence["execution_passed"])
        failed = {
            item["case"]
            for run in evidence["runs"]
            for item in run["checks"]
            if not item["passed"]
        }
        self.assertIn("scan_parity", failed)

    def test_failed_cleanup_fails_the_run(self):
        evidence = execute_fixture(
            FakeController(cleanup_fails=True), "7036B510", settle=0.2
        )
        self.assertFalse(evidence["execution_passed"])
        self.assertFalse(evidence["cleanup"]["verified"])


if __name__ == "__main__":
    unittest.main()
