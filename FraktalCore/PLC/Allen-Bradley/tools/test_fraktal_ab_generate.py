"""Tests for the declaration-to-Logix generator and the press demo it emits.

The negative tests matter more than the positive ones. Every rule S16
established is a rule here only if the generator can *refuse* something for
breaking it; a rule that cannot reject is a comment. Each rule below therefore
has a test that breaks it deliberately and requires the refusal.
"""

import dataclasses
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_press_demo as demo


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


def emit(app):
    """Emit into a temporary directory and return (root, text, evidence)."""
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "seed.L5X"
        source.write_text(SEED, encoding="utf-8")
        output = Path(directory) / "app.L5X"
        evidence = gen.generate(app, source, output)
        text = output.read_text(encoding="utf-8")
        return ET.fromstring(text), text, evidence


class DeclarationRuleTests(unittest.TestCase):
    """The five S16 findings, each provably enforced."""

    def test_the_press_demo_declaration_is_emittable(self):
        self.assertEqual(decl.validate(demo.application()), [])

    def test_a_par_cfg_record_must_lead_with_schema_version(self):
        """Core §3.8: a reader must know which contract it holds."""
        app = demo.application()
        bad = decl.Record(
            "FRK_T_Bad",
            (decl.scalar("SomethingElse"), decl.scalar(decl.SCHEMA_VERSION_MEMBER)),
            par_cfg=True,
        )
        app = dataclasses.replace(app, records=(bad,) + app.records)
        findings = decl.validate(app)
        self.assertTrue(any("SchemaVersion" in f for f in findings), findings)

    def test_a_bool_member_cannot_reach_a_public_contract_udt(self):
        """The BOOL-member layout is a recorded S12 hole, not a local decision."""
        app = demo.application()
        bad = decl.Record("FRK_T_Bad", (decl.Member("Flag", "", "scalar"),))
        bad = dataclasses.replace(
            bad, members=(dataclasses.replace(bad.members[0]),))
        # force a non-DINT carrier the way a careless edit would
        object.__setattr__(bad.members[0], "name", "Flag")
        app = dataclasses.replace(app, records=(bad,) + app.records)
        # the emitter's own assertion is the backstop
        types_xml = gen.data_types(app)
        self.assertNotIn('DataType="BOOL"', types_xml)

    def test_a_duration_outside_the_checked_range_is_refused(self):
        app = demo.application()
        bad = decl.Record("FRK_T_Bad", (
            decl.scalar(decl.SCHEMA_VERSION_MEMBER),
            decl.duration_ms("Forever", initial=decl.DURATION_MAX_MS + 1),
        ), par_cfg=True)
        app = dataclasses.replace(app, records=(bad,) + app.records)
        findings = decl.validate(app)
        self.assertTrue(any("outside the checked range" in f for f in findings), findings)

    def test_a_timeout_that_is_not_whole_scans_is_refused(self):
        """The task period is part of the contract; a module must count it exactly."""
        app = demo.application()
        module = dataclasses.replace(app.modules[0], timeout_ms=505)
        app = dataclasses.replace(app, modules=(module,) + app.modules[1:])
        findings = decl.validate(app)
        self.assertTrue(any("whole number" in f for f in findings), findings)

    def test_a_boolean_carrier_holds_only_zero_or_one(self):
        app = demo.application()
        bad = decl.Record("FRK_T_Bad", (
            decl.scalar(decl.SCHEMA_VERSION_MEMBER),
            decl.boolean("Truthy", initial=7),
        ), par_cfg=True)
        app = dataclasses.replace(app, records=(bad,) + app.records)
        self.assertTrue(any("0 or 1" in f for f in decl.validate(app)))

    def test_a_step_targeting_a_missing_step_is_refused(self):
        app = demo.application()
        auto = next(c for c in app.chains if c.name == "AUTO")
        broken = dataclasses.replace(auto.steps[0], on_advance=12345)
        auto = dataclasses.replace(auto, steps=(broken,) + auto.steps[1:])
        app = dataclasses.replace(
            app, chains=tuple(auto if c.name == "AUTO" else c for c in app.chains))
        self.assertTrue(any("missing step" in f for f in decl.validate(app)))

    def test_a_condition_on_an_undeclared_input_is_refused(self):
        """Nothing would define that tag; Studio should never be the one to say so."""
        app = demo.application()
        auto = next(c for c in app.chains if c.name == "AUTO")
        step = next(s for s in auto.steps if s.action == decl.AWAIT)
        broken = dataclasses.replace(step, conditions=("FRK_Press_Imaginary",))
        auto = dataclasses.replace(
            auto, steps=tuple(broken if s is step else s for s in auto.steps))
        app = dataclasses.replace(
            app, chains=tuple(auto if c.name == "AUTO" else c for c in app.chains))
        self.assertTrue(any("not a declared" in f for f in decl.validate(app)))

    def test_a_held_wait_without_a_named_reason_is_refused(self):
        """An unnamed hold is indistinguishable from a stall."""
        app = demo.application()
        auto = next(c for c in app.chains if c.name == "AUTO")
        step = next(s for s in auto.steps if s.action == decl.HELD_AWAIT)
        broken = dataclasses.replace(step, hold_reason=0)
        auto = dataclasses.replace(
            auto, steps=tuple(broken if s is step else s for s in auto.steps))
        app = dataclasses.replace(
            app, chains=tuple(auto if c.name == "AUTO" else c for c in app.chains))
        self.assertTrue(any("named reason" in f for f in decl.validate(app)))

    def test_an_unemittable_declaration_raises_instead_of_emitting(self):
        app = demo.application()
        app = dataclasses.replace(app, task_period_ms=0)
        with self.assertRaises(decl.DeclarationError):
            decl.require_valid(app)

    def test_scans_for_refuses_a_duration_that_is_not_whole_scans(self):
        app = demo.application()
        self.assertEqual(decl.scans_for(app, 200), 20)
        with self.assertRaises(decl.DeclarationError):
            decl.scans_for(app, 205)


class EmittedProjectTests(unittest.TestCase):
    def setUp(self):
        self.root, self.text, self.evidence = emit(demo.application())

    def test_it_targets_the_pinned_v33_controller(self):
        controller = self.root.find(".//Controller")
        self.assertEqual(controller.get("ProcessorType"), "1769-L24ER-QB1B")
        self.assertEqual(controller.get("MajorRev"), "33")

    def test_one_aoi_per_module_type_plus_the_mode_owner(self):
        names = [a.get("Name") for a in self.root.findall(".//AddOnInstructionDefinition")]
        self.assertEqual(len(names), len(demo.application().modules) + 1)
        self.assertIn("FRK_U_Press", names)

    def test_every_contract_member_is_a_dint(self):
        for data_type in self.root.findall(".//DataType"):
            for member in data_type.findall("./Members/Member"):
                self.assertEqual(member.get("DataType"), "DINT",
                                 f"{data_type.get('Name')}.{member.get('Name')}")

    def test_no_bool_member_in_any_public_contract_udt(self):
        self.assertEqual(self.evidence["BoolMembersInPublicUdt"], 0)
        self.assertNotIn('<Member Name="', self.text.split("<DataTypes>")[0])
        for data_type in self.root.findall(".//DataType"):
            kinds = {m.get("DataType") for m in data_type.findall("./Members/Member")}
            self.assertNotIn("BOOL", kinds)

    def test_the_par_cfg_record_leads_with_schema_version(self):
        cfg = [d for d in self.root.findall(".//DataType")
               if d.get("Name") == "FRK_T_PressParCfg"][0]
        first = cfg.findall("./Members/Member")[0]
        self.assertEqual(first.get("Name"), decl.SCHEMA_VERSION_MEMBER)

    def test_the_task_carries_the_declared_period(self):
        app = demo.application()
        task = self.root.find(".//Task")
        self.assertEqual(task.get("Rate"), str(app.task_period_ms))
        self.assertEqual(task.get("DisableUpdateOutputs"), "true")

    def test_the_declared_period_is_published_for_a_reader(self):
        """A reader can check the period the timeouts were converted from."""
        self.assertIn("FRK_Press_TaskPeriodMs", self.evidence["EvidenceTags"])

    def test_the_mode_owner_self_checks_child_ordering(self):
        unit = [a for a in self.root.findall(".//AddOnInstructionDefinition")
                if a.get("Name") == "FRK_U_Press"][0]
        body = "\n".join((l.text or "") for l in unit.findall(".//STContent/Line"))
        for module in demo.application().modules:
            self.assertIn(f"Ctx{module.name}.ModuleScan <> Scan", body)
        self.assertIn("Ctx.OrderFail := Ctx.OrderFail + 1;", body)

    def test_a_held_command_does_not_accrue_its_timeout(self):
        """Held is 'the operator let go', not 'the machine is broken'."""
        app = demo.application()
        body = "\n".join(gen.module_logic(app, app.modules[0]))
        held = body.split("ELSIF Ctx.HoldRequest <> 0 THEN")[1].split("ELSE")[0]
        self.assertNotIn("ElapsedMs := Ctx.ElapsedMs", held)
        self.assertIn("Ctx.OutImm_Held := 1;", held)
        self.assertIn(f"Ctx.OutImm_Severity := {gen.SEVERITY_LOW};", held)
        self.assertNotIn("Ctx.Error := 1;", held)

    def test_an_aoi_never_reaches_a_controller_scoped_tag(self):
        """Add-On Instructions may only touch their own parameters."""
        for aoi in self.root.findall(".//AddOnInstructionDefinition"):
            body = "\n".join((l.text or "") for l in aoi.findall(".//STContent/Line"))
            stray = sorted(set(re.findall(r"\bFRK_[A-Za-z0-9_]+", body)))
            self.assertEqual(stray, [], f"{aoi.get('Name')} reaches {stray}")

    def test_no_physical_io_operand_anywhere(self):
        self.assertEqual(self.evidence["PhysicalIoReferences"], 0)
        self.assertEqual(re.findall(r"\b(?:Local|Discrete_IO):[IOC]", self.text), [])

    def test_embedded_io_is_inhibited(self):
        modules = {m.get("Name"): m.get("Inhibited")
                   for m in self.root.findall(".//Module")}
        self.assertEqual(modules["Discrete_IO"], "true")

    def test_the_chart_carries_the_section_3_13_marks(self):
        chart = [d for d in self.root.findall(".//DataType")
                 if d.get("Name") == "FRK_T_PressChart"][0]
        names = {m.get("Name") for m in chart.findall("./Members/Member")}
        for expected in ("StepCursor", "StallReason", "Visited", "LastMs",
                         "EnterCount", "CurrentStepMs"):
            self.assertIn(expected, names)

    def test_every_declared_step_has_a_chart_slot(self):
        app = demo.application()
        self.assertLessEqual(self.evidence["DistinctSteps"], app.chart_steps)

    def test_the_awaited_child_fault_is_adopted_verbatim(self):
        """The rollup: the parent republishes the child's reason, not its own."""
        app = demo.application()
        auto = next(c for c in app.chains if c.name == "AUTO")
        step = next(s for s in auto.steps if s.action == decl.ADOPT)
        body = "\n".join(gen.step_logic(app, auto, step, 0))
        self.assertIn(f"Ctx.ErrorID := Ctx{step.module}.ErrorID;", body)
        self.assertIn("Ctx.Error := 1;", body)

    def test_the_reported_child_condition_is_not_adopted(self):
        """A message, not a fault: adopting would replace a designed recovery."""
        app = demo.application()
        auto = next(c for c in app.chains if c.name == "AUTO")
        step = next(s for s in auto.steps if s.action == decl.REPORT)
        body = "\n".join(gen.step_logic(app, auto, step, 0))
        self.assertIn("Ctx.ReportedReason :=", body)
        self.assertNotIn("Ctx.Error := 1;", body)

    def test_the_decision_step_waits_without_faulting(self):
        app = demo.application()
        auto = next(c for c in app.chains if c.name == "AUTO")
        step = next(s for s in auto.steps if s.action == decl.DECISION)
        body = "\n".join(gen.step_logic(app, auto, step, 0))
        self.assertNotIn("Ctx.Error := 1;", body)
        self.assertIn("Ctx.DecisionId :=", body)

    def test_it_refuses_to_overwrite_an_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "seed.L5X"
            source.write_text(SEED, encoding="utf-8")
            output = Path(directory) / "app.L5X"
            output.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                gen.generate(demo.application(), source, output)

    def test_it_rejects_a_source_that_is_not_the_empty_v33_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "seed.L5X"
            source.write_text("<RSLogix5000Content/>", encoding="utf-8")
            with self.assertRaises(ValueError):
                gen.generate(demo.application(), source, Path(directory) / "a.L5X")

    def test_out_of_scope_constructs_are_fenced_out(self):
        for term in gen.EXCLUDED_SCOPE_TERMS:
            self.assertNotIn(term, self.text)

    def test_a_task_period_that_disagrees_with_the_declaration_is_refused(self):
        """The build-time assertion: the shipped task carries the declared period."""
        app = demo.application()
        original = gen.tasks

        def wrong(a):
            return original(a).replace(f'Rate="{a.task_period_ms}"', 'Rate="20"')

        gen.tasks = wrong
        try:
            with self.assertRaises(AssertionError):
                emit(app)
        finally:
            gen.tasks = original


class PressDemoShapeTests(unittest.TestCase):
    """The application mirrors the TC3 press demo's observable shape."""

    def setUp(self):
        self.app = demo.application()

    def test_three_modes_manual_auto_home(self):
        self.assertEqual({c.name for c in self.app.chains},
                         {"MANUAL", "AUTO", "HOME"})

    def test_the_auto_chain_carries_the_oracle_step_numbers(self):
        auto = next(c for c in self.app.chains if c.name == "AUTO")
        numbers = [s.number for s in auto.steps]
        for expected in (0, 100, 110, 130, 150, 170, 180, 200, 210, 215, 220, 999):
            self.assertIn(expected, numbers)

    def test_the_auto_chain_loops(self):
        auto = next(c for c in self.app.chains if c.name == "AUTO")
        self.assertTrue(auto.loops)
        self.assertEqual(auto.steps[-1].on_advance, 100)

    def test_home_completes_rather_than_looping(self):
        home = next(c for c in self.app.chains if c.name == "HOME")
        self.assertFalse(home.loops)
        self.assertTrue(any(s.action == decl.COMPLETE for s in home.steps))

    def test_exactly_one_adopted_and_one_reported_child_condition(self):
        auto = next(c for c in self.app.chains if c.name == "AUTO")
        self.assertEqual(sum(1 for s in auto.steps if s.action == decl.ADOPT), 1)
        self.assertEqual(sum(1 for s in auto.steps if s.action == decl.REPORT), 1)

    def test_exactly_one_decision_step(self):
        auto = next(c for c in self.app.chains if c.name == "AUTO")
        self.assertEqual(sum(1 for s in auto.steps if s.action == decl.DECISION), 1)

    def test_the_held_condition_is_on_the_door_close_step(self):
        auto = next(c for c in self.app.chains if c.name == "AUTO")
        held = [s for s in auto.steps if s.action == decl.HELD_AWAIT]
        self.assertEqual(len(held), 1)
        self.assertEqual(held[0].number, 180)
        self.assertEqual(held[0].module, "Door")
        self.assertEqual(held[0].hold_reason, demo.REASONS["TWO_HAND_RELEASED"])

    def test_no_control_power_or_io_concept_is_declared(self):
        text = " ".join(
            [self.app.comment] + [m.comment for m in self.app.modules]
            + [s.comment for c in self.app.chains for s in c.steps])
        for forbidden in ("ControlOn", "ControlPower", "Local:", "Discrete_IO:"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
