import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import fraktal_ab_reference_suite as suite
from fraktal_ab_reference_execute import (
    COMMAND_A,
    COMMAND_B,
    CROSS_TALK,
    CTX_A,
    CTX_B,
    CTX_MEMBERS,
    FINGERPRINT_TAGS,
    LATENCY_BAD,
    ORDER_FAIL,
    SCAN_COUNT,
    WRITABLE,
    arguments,
    disarm,
    fingerprint,
    read_context,
    run,
    write,
)


SEED = """<?xml version="1.0" encoding="UTF-8"?>
<RSLogix5000Content SchemaRevision="1.0" TargetName="FraktalPhase0" ExportDate="x">
<Controller Use="Target" Name="FraktalPhase0" ProcessorType="1769-L24ER-QB1B" MajorRev="33">
<DataTypes/>
<Modules>
<Module Name="Local" Inhibited="false"></Module>
<Module Name="Discrete_IO" Inhibited="false"></Module>
</Modules>
<AddOnInstructionDefinitions/>
<Tags/>
<Programs/>
<Tasks/>
</Controller>
</RSLogix5000Content>
"""


def generated_root():
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "seed.L5X"
        source.write_text(SEED, encoding="utf-8")
        output = Path(directory) / "suite.L5X"
        evidence = suite.generate(source, output)
        return ET.parse(output).getroot(), output.read_text(encoding="utf-8"), evidence


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.root, self.text, self.evidence = generated_root()

    def test_the_document_is_well_formed_and_targets_v33(self):
        controller = self.root.find(".//Controller")
        self.assertEqual(controller.get("ProcessorType"), "1769-L24ER-QB1B")
        self.assertEqual(controller.get("MajorRev"), "33")

    def test_exactly_two_reference_types(self):
        aois = self.root.findall(".//AddOnInstructionDefinition")
        self.assertEqual(
            [a.get("Name") for a in aois],
            [suite.MODULE_AOI, suite.MODE_AOI],
        )

    def test_the_module_type_is_instantiated_twice(self):
        """The whole point of a reference type is that it composes more than once."""
        tags = [t.get("Name") for t in self.root.findall(".//Controller/Tags/Tag")]
        self.assertIn(suite.MODULE_INSTANCE_A, tags)
        self.assertIn(suite.MODULE_INSTANCE_B, tags)
        self.assertEqual(self.evidence["ModuleInstances"], 2)

    def test_two_independent_contexts_exist(self):
        tags = [t.get("Name") for t in self.root.findall(".//Controller/Tags/Tag")]
        self.assertIn(CTX_A, tags)
        self.assertIn(CTX_B, tags)

    def test_the_public_context_carries_no_bool_member(self):
        """A BOOL member in a public UDT is a recorded S12 hole, not a local call."""
        for data_type in self.root.findall(".//DataType"):
            kinds = {m.get("DataType") for m in data_type.findall("./Members/Member")}
            self.assertEqual(kinds, {"DINT"})
        self.assertEqual(self.evidence["BoolMembersInPublicUdt"], 0)

    def test_only_types_s12_proved(self):
        for forbidden in ("TIME", "TIME32", "LREAL", "LINT", "BOOL"):
            self.assertNotIn(
                f'<Member Name="x" DataType="{forbidden}"', self.text
            )
        for data_type in self.root.findall(".//DataType"):
            for member in data_type.findall("./Members/Member"):
                self.assertEqual(member.get("DataType"), "DINT")

    def test_no_physical_io_reference(self):
        self.assertEqual(self.evidence["PhysicalIoReferences"], 0)
        for routine in self.root.findall(".//STContent"):
            body = "".join(line.text or "" for line in routine.findall("./Line"))
            self.assertNotIn("Local:", body)
            self.assertNotIn("Discrete_IO:", body)

    def test_embedded_io_inhibited_and_outputs_disabled(self):
        modules = {m.get("Name"): m.get("Inhibited") for m in self.root.findall(".//Module")}
        self.assertEqual(modules["Discrete_IO"], "true")
        task = self.root.find(".//Task")
        self.assertEqual(task.get("DisableUpdateOutputs"), "true")

    def test_both_module_instances_are_called_before_sequence_intent(self):
        body = "\n".join(
            "".join(line.text or "" for line in routine.findall("./Line"))
            for routine in self.root.findall(".//Program//STContent")
        )
        first = body.index(suite.MODULE_INSTANCE_A)
        second = body.index(suite.MODULE_INSTANCE_B)
        intent = body.index(suite.MODE_INSTANCE)
        self.assertLess(first, intent)
        self.assertLess(second, intent)

    def test_the_suite_carries_its_own_cross_talk_check(self):
        body = "\n".join(
            "".join(line.text or "" for line in routine.findall("./Line"))
            for routine in self.root.findall(".//Program//STContent")
        )
        self.assertIn("FRK_Ref_CrossTalk", body)
        self.assertIn("FRK_Ref_ShadowRunB", body)

    def test_scope_excludes_runtime_base_structure(self):
        """The suite is gate tooling; it must not grow into the runtime library."""
        for term in suite.EXCLUDED_TERMS:
            self.assertNotIn(term, self.text)

    def test_single_program_routine_and_task(self):
        self.assertEqual(len(self.root.findall(".//Program")), 1)
        self.assertEqual(len(self.root.findall(".//Program//Routine")), 1)
        self.assertEqual(len(self.root.findall(".//Task")), 1)

    def test_it_refuses_to_overwrite_an_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "seed.L5X"
            source.write_text(SEED, encoding="utf-8")
            output = Path(directory) / "suite.L5X"
            output.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                suite.generate(source, output)

    def test_it_rejects_a_source_that_is_not_the_empty_v33_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "seed.L5X"
            source.write_text("<RSLogix5000Content/>", encoding="utf-8")
            with self.assertRaises(ValueError):
                suite.generate(source, Path(directory) / "suite.L5X")

    def test_it_is_labelled_disposable(self):
        self.assertTrue(self.evidence["Disposable"])


class Reply:
    def __init__(self, status="Success", value=None):
        self.Status = status
        self.Value = value


class FakeSuiteController:
    """A scripted stand-in serving two independent contexts as the suite does."""

    def __init__(self, **faults):
        self.faults = faults
        self.writes: list[tuple[str, object]] = []
        self.reads: list[str] = []
        self.ctx = {
            CTX_A: {name: 0 for name in CTX_MEMBERS},
            CTX_B: {name: 0 for name in CTX_MEMBERS},
        }
        for context in self.ctx.values():
            context["SchemaVersion"] = 1
            context["Par_Speed"] = 25
            context["Par_TimeoutMs"] = 500
            context["LatencyScans"] = 1
        self.scalars = {
            SCAN_COUNT: 4321, ORDER_FAIL: 0, LATENCY_BAD: 0, CROSS_TALK: 0,
        }
        for tag in WRITABLE:
            self.scalars[tag] = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def _payload(self, tag):
        record = self.ctx[tag]
        return struct.pack(f"<{len(CTX_MEMBERS)}i",
                           *(int(record[name]) for name in CTX_MEMBERS))

    def Read(self, tag):
        self.reads.append(tag)
        if self.faults.get("read_fails"):
            return Reply(status="Path segment error")
        if tag in self.ctx:
            return Reply(value=self._payload(tag))
        if "." in tag:
            base, member = tag.split(".", 1)
            return Reply(value=self.ctx[base][member])
        return Reply(value=self.scalars.get(tag, 0))

    def Write(self, tag, value):
        self.writes.append((tag, value))
        self.scalars[tag] = value
        self._advance(tag, value)
        return Reply()

    def _advance(self, tag, value):
        a = self.ctx[CTX_A]
        b = self.ctx[CTX_B]
        if tag == COMMAND_A:
            if value:
                if a["OutImm_Held"] or a["Error"]:
                    return
                a.update(Busy=1, OutImm_ExecState=1,
                         RunCount=a["RunCount"] + 1,
                         CycleCount=a["CycleCount"] + 1,
                         DoneCount=a["DoneCount"] + 1, LatencyScans=1)
            else:
                a.update(Busy=0, OutImm_ExecState=0, Aborted=0)
        elif tag == "FRK_Ref_HoldA":
            if value:
                a.update(OutImm_Held=1, OutImm_ExecState=1, Busy=1,
                         OutImm_Reason=6101, OutImm_Severity=0, Error=0)
            else:
                a.update(OutImm_Held=0, OutImm_Reason=0)
        elif tag == "FRK_Ref_FaultA":
            if value:
                a.update(Error=1, Busy=0, ErrorID=6102, OutImm_ExecState=3,
                         OutImm_Severity=2, ErrorCount=a["ErrorCount"] + 1)
            else:
                a.update(Error=0, ErrorID=0, OutImm_ExecState=0, OutImm_Severity=0)
        elif tag == "FRK_Ref_AbortA":
            if value:
                a.update(Aborted=1, Busy=0, OutImm_ExecState=4,
                         AbortCount=a["AbortCount"] + 1)
        elif tag == COMMAND_B:
            if value:
                b.update(Busy=1, OutImm_ExecState=1, RunCount=b["RunCount"] + 1)
            else:
                b.update(Busy=0, OutImm_ExecState=0)


class CoherenceTests(unittest.TestCase):
    """An observation must be a state the controller actually held."""

    def test_a_context_costs_exactly_one_request(self):
        controller = FakeSuiteController()
        controller.reads.clear()
        read_context(controller, CTX_A)
        self.assertEqual(controller.reads, [CTX_A])

    def test_a_snapshot_is_coherent_while_the_suite_mutates(self):
        class Mutating(FakeSuiteController):
            def __init__(self):
                super().__init__()
                self.generation = 0

            def Read(self, tag):
                self.generation += 1
                for name in CTX_MEMBERS:
                    self.ctx[CTX_A][name] = self.generation
                return super().Read(tag)

        observed = read_context(Mutating(), CTX_A)
        self.assertEqual(len(set(observed.values())), 1)

    def test_a_short_payload_fails_closed(self):
        class Short(FakeSuiteController):
            def Read(self, tag):
                if tag in self.ctx:
                    return Reply(value=bytes(8))
                return super().Read(tag)

        self.assertIsNone(read_context(Short(), CTX_A))

    def test_a_failed_read_fails_closed(self):
        self.assertIsNone(read_context(FakeSuiteController(read_fails=True), CTX_A))


class WriteSurfaceTests(unittest.TestCase):
    def test_the_surface_is_exactly_the_six_command_tags(self):
        self.assertEqual(set(WRITABLE), {
            "FRK_Ref_CommandA", "FRK_Ref_AbortA", "FRK_Ref_ModeSelectA",
            "FRK_Ref_HoldA", "FRK_Ref_FaultA", "FRK_Ref_CommandB",
        })

    def test_writing_outside_the_surface_is_refused(self):
        with self.assertRaises(AssertionError):
            write(FakeSuiteController(), "FRK_Ref_ScanCount", 1)

    def test_the_vector_never_writes_outside_the_surface(self):
        controller = FakeSuiteController()
        run(controller, settle=0.05)
        self.assertTrue({tag for tag, _ in controller.writes}.issubset(set(WRITABLE)))

    def test_disarm_clears_every_writable_input(self):
        controller = FakeSuiteController()
        run(controller, settle=0.05)
        self.assertEqual(set(disarm(controller).values()), {"cleared"})

    def test_fingerprint_tags_are_never_writable(self):
        for tag in FINGERPRINT_TAGS:
            self.assertNotIn(tag, WRITABLE)


class FingerprintTests(unittest.TestCase):
    def test_it_accepts_the_reference_suite(self):
        self.assertTrue(fingerprint(FakeSuiteController())["passed"])

    def test_it_rejects_a_stopped_controller(self):
        controller = FakeSuiteController()
        controller.scalars[SCAN_COUNT] = 0
        self.assertFalse(fingerprint(controller)["passed"])

    def test_it_rejects_a_different_fixture(self):
        controller = FakeSuiteController()
        controller.ctx[CTX_B]["SchemaVersion"] = 99
        self.assertFalse(fingerprint(controller)["passed"])

    def test_it_fails_closed_when_a_tag_cannot_be_read(self):
        self.assertFalse(fingerprint(FakeSuiteController(read_fails=True))["passed"])


class VectorTests(unittest.TestCase):
    def test_every_row_runs_and_is_named(self):
        result = run(FakeSuiteController(), settle=0.05)
        self.assertEqual([r["test"] for r in result["rows"]], [
            "reference_types_scanning",
            "module_a_completes_cycle",
            "module_b_undisturbed_while_a_runs",
            "module_a_held_is_low_and_not_an_error",
            "module_a_resumes_without_reissue",
            "module_a_fault_carries_error_id",
            "module_a_abort_does_not_self_resume",
            "module_b_runs_independently",
            "ordering_latency_and_cross_talk",
        ])

    def test_a_modelled_good_run_passes(self):
        self.assertTrue(run(FakeSuiteController(), settle=0.05)["passed"])

    def test_summary_carries_the_five_fields_ab_5_7_names(self):
        result = run(FakeSuiteController(), settle=0.05)
        for field in ("suites", "tests", "successful", "failed", "duration_ms"):
            self.assertIn(field, result)
        self.assertEqual(result["successful"] + result["failed"], result["tests"])

    def test_cross_talk_fails_the_suite(self):
        """The independence claim must be falsifiable, or it is not evidence."""
        controller = FakeSuiteController()
        original = controller._advance

        def advance(tag, value):
            original(tag, value)
            controller.scalars[CROSS_TALK] = 3

        controller._advance = advance
        result = run(controller, settle=0.05)
        self.assertFalse(result["passed"])

    def test_a_disturbed_second_instance_fails_the_suite(self):
        controller = FakeSuiteController()
        original = controller._advance

        def advance(tag, value):
            original(tag, value)
            if tag == COMMAND_A and value:
                # A's command wrongly starts B as well.
                controller.ctx[CTX_B]["RunCount"] += 1

        controller._advance = advance
        result = run(controller, settle=0.05)
        row = next(r for r in result["rows"]
                   if r["test"] == "module_b_undisturbed_while_a_runs")
        self.assertFalse(row["passed"])
        self.assertFalse(result["passed"])

    def test_a_bad_ordering_counter_fails_the_suite(self):
        controller = FakeSuiteController()
        controller.scalars[ORDER_FAIL] = 2
        result = run(controller, settle=0.05)
        self.assertFalse(result["passed"])

    def test_reads_failing_mid_vector_fail_closed(self):
        self.assertFalse(run(FakeSuiteController(read_fails=True), settle=0.05)["passed"])

    def test_values_are_not_reported_raw(self):
        result = run(FakeSuiteController(), settle=0.05)
        for row in result["rows"]:
            self.assertIn("expectation", row)
            self.assertIn("elapsed_ms", row)


class ArgumentTests(unittest.TestCase):
    def test_requires_the_explicit_arm_flag(self):
        with self.assertRaises(SystemExit):
            arguments(["10.0.0.1", "--expect-serial", "7036B510"])

    def test_rejects_an_unbounded_settle(self):
        with self.assertRaises(SystemExit):
            arguments(["10.0.0.1", "--expect-serial", "7036B510",
                       "--execute-fixture", "--settle", "60"])

    def test_accepts_a_complete_invocation(self):
        args = arguments(["10.0.0.1", "--expect-serial", "0x7036b510",
                          "--execute-fixture"])
        self.assertEqual(args.expect_serial, "7036B510")


if __name__ == "__main__":
    unittest.main()
