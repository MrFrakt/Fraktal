import re
import tempfile
import unittest
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from fraktal_ab_s16_fixture import (
    AXIS_AOI,
    CTX_MEMBERS,
    CTX_TYPE,
    MODE_AOI,
    REASON_DEVICE_FAULT,
    REASON_HELD_PERMISSIVE,
    STATE_ABORTED,
    STATE_BUSY,
    STATE_DONE,
    STATE_ERROR,
    STATE_READY,
    WRITABLE_INPUTS,
    all_generated_logic,
    generate,
    main_routine_logic,
)


EMPTY = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<RSLogix5000Content TargetType="Controller" TargetName="FraktalPhase0">
<Controller Use="Target" Name="FraktalPhase0" ProcessorType="1769-L24ER-QB1B" MajorRev="33" SFCExecutionControl="CurrentActive" SFCRestartPosition="MostRecent" SFCLastScan="DontScan">
<DataTypes/>
<Modules><Module Name="Discrete_IO" Inhibited="false"/></Modules>
<AddOnInstructionDefinitions/>
<Tags/>
<Programs/>
<Tasks/>
</Controller>
</RSLogix5000Content>
"""


def build(temporary: str) -> tuple[dict[str, object], str]:
    source = Path(temporary) / "empty.L5X"
    output = Path(temporary) / "fixture.L5X"
    source.write_text(EMPTY, encoding="utf-8")
    return generate(source, output), output.read_text(encoding="utf-8")


class S16FixtureTests(unittest.TestCase):
    def test_output_is_well_formed_xml(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, text = build(temporary)
            ElementTree.fromstring(text)

    def test_generates_exactly_the_module_and_mode_aois(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, text = build(temporary)
            names = {
                definition.get("Name")
                for definition in ElementTree.fromstring(text).iter(
                    "AddOnInstructionDefinition"
                )
            }
            self.assertEqual(names, {AXIS_AOI, MODE_AOI})
            self.assertEqual(result["AoiDefinitions"], 2)

    def test_context_uses_only_types_s12_proved(self):
        """S12 removed TIME/TIME32/LREAL and made LINT transport-only."""
        with tempfile.TemporaryDirectory() as temporary:
            _, text = build(temporary)
            data_type = next(
                candidate
                for candidate in ElementTree.fromstring(text).iter("DataType")
                if candidate.get("Name") == CTX_TYPE
            )
            used = {member.get("DataType") for member in data_type.iter("Member")}
            self.assertEqual(used, {"DINT"})
            for excluded in ("TIME", "TIME32", "LREAL", "LINT"):
                self.assertNotIn(excluded, used)

    def test_duration_is_a_dint_of_milliseconds(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, _ = build(temporary)
            self.assertIn("DINT milliseconds", result["DurationCarrier"])
            names = {member.name for member in CTX_MEMBERS}
            self.assertIn("Par_TimeoutMs", names)
            self.assertIn("ElapsedMs", names)

    def test_module_aoi_is_called_before_the_mode_owner(self):
        """The S11 ordering rule: root logic runs ahead of sequence intent."""
        logic = main_routine_logic()
        axis_at = next(i for i, line in enumerate(logic) if line.startswith(AXIS_AOI))
        mode_at = next(i for i, line in enumerate(logic) if line.startswith(MODE_AOI))
        self.assertLess(axis_at, mode_at)

    def test_mode_owner_faults_when_the_module_has_not_run(self):
        self.assertIn("Ctx.ModuleScan <> Scan", all_generated_logic())
        self.assertIn("Ctx.OrderFail := Ctx.OrderFail + 1;", all_generated_logic())

    def test_execute_drop_resets_terminal_state(self):
        logic = all_generated_logic()
        self.assertIn("IF Ctx.Execute = 0 THEN", logic)
        self.assertIn("Ctx.ResetCount := Ctx.ResetCount + 1;", logic)

    def test_parcmd_is_latched_on_the_rising_edge_only(self):
        logic = all_generated_logic()
        self.assertIn("IF (Ctx.Execute <> 0) AND (Ctx.ExecutePrev = 0) THEN", logic)
        self.assertIn("Ctx.ParCmd_Latched := Ctx.ParCmd_Target;", logic)

    def test_held_is_busy_with_a_low_reason_and_no_error(self):
        """Core §6.1: a suspended command is not a failed one."""
        logic = all_generated_logic()
        held = logic[logic.index("ELSIF Hold <> 0 THEN"):logic.index("ELSE")]
        self.assertIn(f"Ctx.OutImm_Reason := {REASON_HELD_PERMISSIVE};", held)
        self.assertIn(f"Ctx.OutImm_ExecState := {STATE_BUSY};", held)
        self.assertNotIn("Ctx.Error := 1;", held)
        self.assertNotIn("Ctx.ElapsedMs", held)

    def test_timeout_does_not_accumulate_while_held(self):
        """Held must auto-resume, so the timeout clock is frozen while held."""
        logic = all_generated_logic()
        held_start = logic.index("ELSIF Hold <> 0 THEN")
        held_end = logic.index("ELSE", held_start)
        self.assertNotIn("ElapsedMs", logic[held_start:held_end])

    def test_abort_is_terminal_and_does_not_self_resume(self):
        logic = all_generated_logic()
        self.assertIn("IF (Ctx.Abort <> 0) AND (Ctx.Busy <> 0) THEN", logic)
        self.assertIn(f"Ctx.OutImm_ExecState := {STATE_ABORTED};", logic)

    def test_fault_raises_error_with_an_error_id(self):
        logic = all_generated_logic()
        self.assertIn(f"Ctx.ErrorID := {REASON_DEVICE_FAULT};", logic)
        self.assertIn(f"Ctx.OutImm_ExecState := {STATE_ERROR};", logic)

    def test_all_five_exec_states_are_reachable(self):
        logic = all_generated_logic()
        for state in (STATE_READY, STATE_BUSY, STATE_DONE, STATE_ERROR, STATE_ABORTED):
            self.assertIn(f"Ctx.OutImm_ExecState := {state};", logic)

    def test_no_physical_io_operand(self):
        self.assertIsNone(
            re.search(r"\b(?:Local|Discrete_IO):[IOC]", all_generated_logic())
        )

    def test_embedded_io_inhibited_and_output_updates_disabled(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, text = build(temporary)
            self.assertTrue(result["EmbeddedIoInhibited"])
            self.assertTrue(result["TaskOutputUpdatesDisabled"])
            self.assertIn('Inhibited="true"', text)
            self.assertIn('DisableUpdateOutputs="true"', text)
            self.assertEqual(result["PhysicalIoReferences"], 0)

    def test_every_routine_is_reached_from_the_main_routine(self):
        """S4 rule: an unreachable routine makes Studio warn about dead code."""
        with tempfile.TemporaryDirectory() as temporary:
            result, text = build(temporary)
            root = ElementTree.fromstring(text)
            program = next(root.iter("Program"))
            routines = [routine.get("Name") for routine in program.iter("Routine")]
            self.assertEqual(routines, [program.get("MainRoutineName")])
            self.assertEqual(result["Routines"], 1)

    def test_write_surface_is_the_five_declared_command_tags(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, text = build(temporary)
            self.assertEqual(result["WritableInputs"], list(WRITABLE_INPUTS))
            for name in WRITABLE_INPUTS:
                self.assertIn(f'<Tag Name="{name}"', text)

    def test_scope_excludes_runtime_base_structure(self):
        """The fixture is disposable: it must not grow a runtime base."""
        with tempfile.TemporaryDirectory() as temporary:
            _, text = build(temporary)
            for forbidden in (
                "Recipe",
                "ParCfg",
                "Manifest",
                "Registry",
                "Mailbox",
                "Traceability",
                "ReleaseReport",
            ):
                self.assertNotIn(forbidden, text, f"fixture grew {forbidden}")

    def test_refuses_to_overwrite_an_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "empty.L5X"
            output = Path(temporary) / "fixture.L5X"
            source.write_text(EMPTY, encoding="utf-8")
            output.write_text("existing", encoding="utf-8")
            with self.assertRaises(ValueError):
                generate(source, output)

    def test_rejects_a_source_that_is_not_the_empty_v33_fixture(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "wrong.L5X"
            source.write_text(EMPTY.replace("MajorRev=\"33\"", "MajorRev=\"38\""),
                              encoding="utf-8")
            with self.assertRaises(ValueError):
                generate(source, Path(temporary) / "out.L5X")

    def test_reports_hashes_for_source_and_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, _ = build(temporary)
            self.assertRegex(str(result["SourceSha256"]), r"^[0-9A-F]{64}$")
            self.assertRegex(str(result["OutputSha256"]), r"^[0-9A-F]{64}$")


if __name__ == "__main__":
    unittest.main()
