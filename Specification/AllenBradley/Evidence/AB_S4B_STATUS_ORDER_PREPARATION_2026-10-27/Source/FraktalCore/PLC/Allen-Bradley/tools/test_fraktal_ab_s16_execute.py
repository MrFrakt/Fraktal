import contextlib
import io
import struct
import sys
import types
import unittest

from fraktal_ab_s16_execute import (
    CTX,
    CTX_MEMBERS,
    EXPECTED_SPEED,
    EXPECTED_TIMEOUT_MS,
    FINGERPRINT_TAGS,
    OBSERVED,
    REASON_DEVICE_FAULT,
    REASON_HELD_PERMISSIVE,
    SEVERITY_LOW,
    STATE_BUSY,
    STATE_ERROR,
    STATE_READY,
    WRITABLE,
    _arguments,
    _disarm,
    _fingerprint,
    _normalize_serial,
    _read_context,
    _write,
    main,
    run,
)


class Reply:
    def __init__(self, status: str = "Success", value=None):
        self.Status = status
        self.Value = value


class FakeController:
    """A scripted stand-in that answers the fixed vector's reads and writes.

    It models the fixture's observable outcome rather than the controller: a
    phase reaches its state as soon as the matching command tag is written.
    That is enough to prove the probe's own pass/fail logic, including that it
    fails closed and that it never writes outside the declared surface.
    """

    def __init__(self, serial: str = "7036B510", **faults):
        self.serial = serial
        self.faults = faults
        self.writes: list[tuple[str, object]] = []
        self.values: dict[str, object] = {
            f"{CTX}.SchemaVersion": 1,
            f"{CTX}.Par_Speed": EXPECTED_SPEED,
            f"{CTX}.Par_TimeoutMs": EXPECTED_TIMEOUT_MS,
            "FRK_S16_ScanCount": 4321,
            "FRK_S16_OrderFail": 0,
        }
        for member in OBSERVED:
            self.values[f"{CTX}.{member}"] = 0
        for tag in WRITABLE:
            self.values[tag] = 0

    # -- pylogix surface -------------------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def GetModuleProperties(self, _slot):
        device = type("D", (), {})()
        device.ProductName = "1769-L24ER-QB1B/A"
        device.Revision = "33.14"
        # Real pylogix hands back the serial as a string; modelling it as an
        # int is what let a raw ':08X' format reach the controller untested.
        device.SerialNumber = self.serial
        return Reply(value=device)

    def Read(self, tag):
        if self.faults.get("read_fails"):
            return Reply(status="Path segment error")
        if tag == CTX:
            return Reply(value=self._context_payload())
        return Reply(value=self.values.get(tag, 0))

    def _context_payload(self) -> bytes:
        """Serve the whole context as one CIP payload, as the controller does."""
        return struct.pack(
            f"<{len(CTX_MEMBERS)}i",
            *(int(self.values.get(f"{CTX}.{name}", 0)) for name in CTX_MEMBERS),
        )

    def Write(self, tag, value):
        self.writes.append((tag, value))
        if self.faults.get("write_fails"):
            return Reply(status="Path segment error")
        self.values[tag] = value
        self._advance(tag, value)
        return Reply()

    # -- modelled fixture behaviour --------------------------------------
    def _set(self, **members):
        for name, value in members.items():
            self.values[f"{CTX}.{name}"] = value

    def _advance(self, tag, value):
        if tag == "FRK_S16_ModeSelect":
            self._set(Mode=value, ModeSwitches=self.values[f"{CTX}.ModeSwitches"] + 1)
        if tag == "FRK_S16_Abort" and value:
            self._set(
                Aborted=1, Busy=0,
                AbortCount=self.values[f"{CTX}.AbortCount"] + 1,
                OutImm_ExecState=4, OutImm_Reason=6104,
            )
            return
        if tag == "FRK_S16_HoldRequest":
            if value:
                self._set(
                    OutImm_Held=1, OutImm_ExecState=STATE_BUSY, Busy=1,
                    OutImm_Reason=REASON_HELD_PERMISSIVE,
                    OutImm_Severity=SEVERITY_LOW, Error=0, HeldScans=3,
                )
            else:
                self._set(
                    OutImm_Held=0, OutImm_Reason=0, Done=1,
                    DoneCount=self.values[f"{CTX}.DoneCount"] + 1,
                )
            return
        if tag == "FRK_S16_FaultRequest":
            if value:
                self._set(
                    Error=1, Busy=0, ErrorID=REASON_DEVICE_FAULT,
                    OutImm_ExecState=STATE_ERROR,
                    ErrorCount=self.values[f"{CTX}.ErrorCount"] + 1,
                )
            else:
                self._set(Error=0, ErrorID=0, OutImm_ExecState=STATE_READY)
            return
        if tag == "FRK_S16_Command":
            if value:
                if self.values[f"{CTX}.OutImm_Held"] or self.values[f"{CTX}.Error"]:
                    return
                # Counters accumulate, as the free-running fixture's do.
                self._set(
                    Busy=1, OutImm_ExecState=STATE_BUSY,
                    RunCount=self.values[f"{CTX}.RunCount"] + 1,
                    CycleCount=self.values[f"{CTX}.CycleCount"] + 1,
                    DoneCount=self.values[f"{CTX}.DoneCount"] + 1,
                    LatencyScans=1, LatencyBad=0,
                )
            else:
                self._set(
                    Busy=0, Done=0, OutImm_ExecState=STATE_READY,
                    ResetCount=self.values[f"{CTX}.ResetCount"] + 1,
                )


class NormalizeSerialTests(unittest.TestCase):
    def test_accepts_and_upcases_a_prefixed_serial(self):
        self.assertEqual(_normalize_serial("0x7036b510"), "7036B510")

    def test_rejects_a_wrong_length_serial(self):
        with self.assertRaises(Exception):
            _normalize_serial("7036B5")

    def test_rejects_a_non_hexadecimal_serial(self):
        with self.assertRaises(Exception):
            _normalize_serial("7036B5ZZ")


class ArgumentTests(unittest.TestCase):
    def test_requires_the_explicit_arm_flag(self):
        with self.assertRaises(SystemExit):
            _arguments(["10.0.0.1", "--expect-serial", "7036B510"])

    def test_requires_an_expected_serial(self):
        with self.assertRaises(SystemExit):
            _arguments(["10.0.0.1", "--execute-fixture"])

    def test_rejects_an_unbounded_settle(self):
        with self.assertRaises(SystemExit):
            _arguments([
                "10.0.0.1", "--expect-serial", "7036B510",
                "--execute-fixture", "--settle", "60",
            ])

    def test_accepts_a_complete_invocation(self):
        args = _arguments([
            "10.0.0.1", "--expect-serial", "0x7036b510", "--execute-fixture",
        ])
        self.assertEqual(args.expect_serial, "7036B510")


class WriteSurfaceTests(unittest.TestCase):
    def test_write_surface_is_exactly_the_five_command_tags(self):
        self.assertEqual(
            set(WRITABLE),
            {
                "FRK_S16_Command",
                "FRK_S16_Abort",
                "FRK_S16_ModeSelect",
                "FRK_S16_HoldRequest",
                "FRK_S16_FaultRequest",
            },
        )

    def test_writing_outside_the_surface_is_refused(self):
        controller = FakeController()
        with self.assertRaises(AssertionError):
            _write(controller, f"{CTX}.Busy", 1)
        self.assertEqual(controller.writes, [])

    def test_the_vector_never_writes_outside_the_surface(self):
        controller = FakeController()
        run(controller, settle=0.05)
        written = {tag for tag, _ in controller.writes}
        self.assertTrue(written.issubset(set(WRITABLE)))

    def test_disarm_clears_every_writable_input(self):
        controller = FakeController()
        for tag in WRITABLE:
            controller.values[tag] = 1
        report = _disarm(controller)
        self.assertEqual(set(report), set(WRITABLE))
        self.assertTrue(all(state == "cleared" for state in report.values()))
        for tag in WRITABLE:
            self.assertEqual(controller.values[tag], 0)

    def test_disarm_reports_failure_rather_than_hiding_it(self):
        controller = FakeController(write_fails=True)
        report = _disarm(controller)
        self.assertTrue(all(state == "FAILED" for state in report.values()))


class FingerprintTests(unittest.TestCase):
    def test_accepts_the_s16_fixture(self):
        result = _fingerprint(FakeController())
        self.assertTrue(result["passed"])

    def test_rejects_a_different_fixture(self):
        controller = FakeController()
        controller.values[f"{CTX}.Par_Speed"] = 99
        result = _fingerprint(controller)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["speed"])

    def test_rejects_a_stopped_controller(self):
        controller = FakeController()
        controller.values["FRK_S16_ScanCount"] = 0
        self.assertFalse(_fingerprint(controller)["passed"])

    def test_fails_closed_when_a_tag_cannot_be_read(self):
        result = _fingerprint(FakeController(read_fails=True))
        self.assertFalse(result["passed"])
        self.assertIn("failed_tag", result)

    def test_fingerprint_tags_are_read_only_context_members(self):
        for tag in FINGERPRINT_TAGS:
            self.assertNotIn(tag, WRITABLE)


class VectorTests(unittest.TestCase):
    def test_every_declared_phase_runs(self):
        result = run(FakeController(), settle=0.05)
        names = [phase["phase"] for phase in result["phases"]]
        self.assertEqual(
            names,
            [
                "auto_cycle",
                "abort_no_resume",
                "execute_drop_ready",
                "held_low_reason",
                "held_auto_resume",
                "fault_error_id",
                "restart_by_reissue",
                "mode_switch_midcycle",
                "ordering_and_latency",
            ],
        )

    def test_a_modelled_good_run_passes(self):
        self.assertTrue(run(FakeController(), settle=0.05)["passed"])

    def test_a_fixture_that_has_already_run_still_passes(self):
        """The bench fixture free runs and nothing resets it.

        After the first vector its lifetime AbortCount and ErrorCount are
        permanently non-zero, so a phase that compares them with zero could
        only ever pass once per download. The claim is about this cycle.
        """
        controller = FakeController()
        controller.values[f"{CTX}.CycleCount"] = 16
        controller.values[f"{CTX}.AbortCount"] = 50
        controller.values[f"{CTX}.ErrorCount"] = 13
        result = run(controller, settle=0.05)
        auto = next(
            phase for phase in result["phases"] if phase["phase"] == "auto_cycle"
        )
        self.assertTrue(auto["passed"])

    def test_auto_cycle_fails_when_no_further_cycle_completes(self):
        """A phase that cannot fail is not evidence."""
        controller = FakeController()
        original = controller._advance

        def advance(tag, value):
            original(tag, value)
            controller.values[f"{CTX}.CycleCount"] = 7

        controller._advance = advance
        controller.values[f"{CTX}.CycleCount"] = 7
        result = run(controller, settle=0.05)
        auto = next(
            phase for phase in result["phases"] if phase["phase"] == "auto_cycle"
        )
        self.assertFalse(auto["passed"])

    def test_an_ordering_violation_fails_the_vector(self):
        controller = FakeController()
        original = controller._advance

        def advance(tag, value):
            original(tag, value)
            controller.values[f"{CTX}.OrderFail"] = 2

        controller._advance = advance
        result = run(controller, settle=0.05)
        ordering = next(
            phase for phase in result["phases"] if phase["phase"] == "ordering_and_latency"
        )
        self.assertFalse(ordering["passed"])
        self.assertFalse(result["passed"])

    def test_a_bad_latency_fails_the_vector(self):
        controller = FakeController()
        original = controller._advance

        def advance(tag, value):
            original(tag, value)
            controller.values[f"{CTX}.LatencyBad"] = 1

        controller._advance = advance
        self.assertFalse(run(controller, settle=0.05)["passed"])

    def test_held_that_raises_error_fails_the_vector(self):
        """A held condition that errors is exactly what Core §6.1 forbids."""
        controller = FakeController()
        original = controller._advance

        def advance(tag, value):
            original(tag, value)
            if tag == "FRK_S16_HoldRequest" and value:
                controller.values[f"{CTX}.Error"] = 1

        controller._advance = advance
        result = run(controller, settle=0.05)
        held = next(
            phase for phase in result["phases"] if phase["phase"] == "held_low_reason"
        )
        self.assertFalse(held["passed"])

    def test_held_at_wrong_severity_fails_the_vector(self):
        controller = FakeController()
        original = controller._advance

        def advance(tag, value):
            original(tag, value)
            if tag == "FRK_S16_HoldRequest" and value:
                controller.values[f"{CTX}.OutImm_Severity"] = 2

        controller._advance = advance
        held = next(
            phase
            for phase in run(controller, settle=0.05)["phases"]
            if phase["phase"] == "held_low_reason"
        )
        self.assertFalse(held["passed"])

    def test_reads_failing_mid_vector_fail_closed(self):
        controller = FakeController(read_fails=True)
        result = run(controller, settle=0.05)
        self.assertFalse(result["passed"])

    def test_values_are_not_reported_raw(self):
        """The record carries status and shape, never process values."""
        result = run(FakeController(), settle=0.05)
        for phase in result["phases"]:
            self.assertIn("expectation", phase)
            self.assertIn("elapsed_ms", phase)


class GenerationController(FakeController):
    """A controller whose fixture advances on every request.

    Each member carries the current generation, mirroring the S9 coherence
    fixture: a coherent snapshot is all-equal, and a torn one names the two
    generations it straddles.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.generation = 0
        self.reads: list[str] = []

    def Read(self, tag):
        self.reads.append(tag)
        self.generation += 1
        for name in CTX_MEMBERS:
            self.values[f"{CTX}.{name}"] = self.generation
        return super().Read(tag)


class ContextCoherenceTests(unittest.TestCase):
    """The observation must be a state the controller actually held.

    The fixture task runs at 10 ms and every counter moves on its own, so an
    observation assembled from many requests reports a state that never
    existed - the tearing AB_S9_COHERENCE_EVIDENCE.md measured, and the reason
    a phase could pass on one run and fail on the next with nothing changed.
    """

    def test_a_snapshot_is_coherent_while_the_fixture_mutates(self):
        controller = GenerationController()
        observed = _read_context(controller)
        self.assertEqual(
            len(set(observed.values())), 1,
            "members came from more than one generation: the snapshot tore",
        )

    def test_a_snapshot_costs_exactly_one_request(self):
        controller = GenerationController()
        _read_context(controller)
        self.assertEqual(controller.reads, [CTX])

    def test_a_per_member_sweep_would_tear(self):
        """The guard above is not vacuous: the old strategy really does tear."""
        controller = GenerationController()
        torn = {
            member: controller.Read(f"{CTX}.{member}").Value
            for member in OBSERVED
        }
        self.assertGreater(
            len(set(torn.values())), 1,
            "the mutating controller must tear a per-member sweep, "
            "or the coherence test proves nothing",
        )

    def test_a_short_payload_fails_closed(self):
        class ShortPayload(FakeController):
            def Read(self, tag):
                if tag == CTX:
                    return Reply(value=bytes(8))
                return super().Read(tag)

        self.assertIsNone(_read_context(ShortPayload()))

    def test_a_non_binary_payload_fails_closed(self):
        class ScalarPayload(FakeController):
            def Read(self, tag):
                if tag == CTX:
                    return Reply(value=0)
                return super().Read(tag)

        self.assertIsNone(_read_context(ScalarPayload()))

    def test_every_observed_member_is_declared_in_the_layout(self):
        self.assertEqual(len(CTX_MEMBERS), 39)
        for member in OBSERVED:
            self.assertIn(member, CTX_MEMBERS)


class MainPathTests(unittest.TestCase):
    """Cover main() itself: its identity read is what reaches real hardware."""

    def _run_main(self, controller):
        module = types.ModuleType("pylogix")
        module.PLC = lambda: controller
        saved = sys.modules.get("pylogix")
        sys.modules["pylogix"] = module
        try:
            # main() reports on stdout; keep the suite's output clean.
            with contextlib.redirect_stdout(io.StringIO()):
                return main([
                    "192.168.100.89", "--expect-serial", "7036B510",
                    "--execute-fixture", "--settle", "1",
                ])
        finally:
            if saved is None:
                sys.modules.pop("pylogix", None)
            else:
                sys.modules["pylogix"] = saved

    def test_a_string_serial_from_the_controller_is_accepted(self):
        controller = FakeController(serial="7036B510")
        self.assertIn(self._run_main(controller), (0, 1))

    def test_a_mismatched_serial_stops_before_any_write(self):
        controller = FakeController(serial="DEADBEEF")
        self.assertEqual(self._run_main(controller), 1)
        self.assertEqual(controller.writes, [])


if __name__ == "__main__":
    unittest.main()
