"""Tests for multi-language renditions and the graph-equality gate.

The negative tests are the point. A gate that compares three renditions is only
worth having if it can tell when they disagree, so each check below is paired
with a deliberately broken rendition that it must reject.
"""

import copy
import dataclasses
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_press_demo as demo
import fraktal_ab_rendition_gate as gate
from test_fraktal_ab_generate import SEED, emit


def emit_project():
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "seed.L5X"
        source.write_text(SEED, encoding="utf-8")
        output = Path(directory) / "app.L5X"
        gen.generate(demo.application(), source, output)
        return ET.fromstring(output.read_text(encoding="utf-8"))


class DeclarationRenditionTests(unittest.TestCase):
    def test_auto_is_multi_rendition_and_the_others_are_not(self):
        app = demo.application()
        auto = next(c for c in app.chains if c.name == "AUTO")
        self.assertTrue(auto.multi_rendition)
        self.assertEqual(auto.renditions[0], decl.ST)
        for chain in app.chains:
            if chain.name != "AUTO":
                self.assertFalse(chain.multi_rendition, chain.name)
                self.assertEqual(chain.renditions, (decl.ST,))

    def test_st_must_be_the_first_rendition(self):
        """ST is the reference every other rendition is compared against."""
        app = demo.application()
        auto = next(c for c in app.chains if c.name == "AUTO")
        broken = dataclasses.replace(auto, renditions=(decl.LD, decl.ST))
        app = dataclasses.replace(
            app, chains=tuple(broken if c.name == "AUTO" else c for c in app.chains))
        self.assertTrue(any("reference rendition" in f for f in decl.validate(app)))

    def test_an_unknown_rendition_is_refused(self):
        app = demo.application()
        auto = next(c for c in app.chains if c.name == "AUTO")
        broken = dataclasses.replace(auto, renditions=(decl.ST, "FBD"))
        app = dataclasses.replace(
            app, chains=tuple(broken if c.name == "AUTO" else c for c in app.chains))
        self.assertTrue(any("unknown rendition" in f for f in decl.validate(app)))

    def test_a_duplicate_rendition_is_refused(self):
        app = demo.application()
        auto = next(c for c in app.chains if c.name == "AUTO")
        broken = dataclasses.replace(auto, renditions=(decl.ST, decl.LD, decl.LD))
        app = dataclasses.replace(
            app, chains=tuple(broken if c.name == "AUTO" else c for c in app.chains))
        self.assertTrue(any("duplicate renditions" in f for f in decl.validate(app)))


class LadderEmissionTests(unittest.TestCase):
    def setUp(self):
        self.app = demo.application()
        self.auto = next(c for c in self.app.chains if c.name == "AUTO")
        self.rungs = gen.chain_ld_rungs(self.app, self.auto)

    def test_one_rung_per_declared_step(self):
        gated = [r for r in self.rungs if r.startswith("EQU(")]
        self.assertEqual(len(gated), len(self.auto.steps))

    def test_rungs_ascend_by_step_number(self):
        """Rung order is execution order, so the text reads as it runs."""
        numbers = [int(m.group(1)) for r in self.rungs
                   if (m := re.match(r"EQU\(\S+?\.Step,(\d+)\)", r))]
        self.assertEqual(numbers, sorted(numbers))

    def test_every_step_rung_carries_the_one_step_per_scan_guard(self):
        """Without it a forward transition falls into the next rung same scan."""
        advanced = gen.ld_advanced_tag(self.app)
        for rung in self.rungs:
            if rung.startswith("EQU("):
                self.assertIn(f"EQU({advanced},0)", rung)

    def test_the_guard_is_cleared_once_per_scan_and_set_by_every_transition(self):
        advanced = gen.ld_advanced_tag(self.app)
        self.assertIn(f"MOV(0,{advanced})", self.rungs[0])
        movers = [r for r in self.rungs
                  if re.search(r"MOV\(-?\d+,\S+?\.Step\)", r)]
        for rung in movers:
            self.assertIn(f"MOV(1,{advanced})", rung)

    def test_the_step_clock_uses_a_scratch_tag_not_a_chained_result(self):
        """Never feed one instruction's result into another's condition."""
        scratch = gen.ld_scratch_tag(self.app)
        clock = self.rungs[1]
        self.assertIn(f"SUB(", clock)
        self.assertIn(scratch, clock)
        self.assertIn("MUL(", clock)

    def test_the_held_step_publishes_a_low_reason_and_no_error(self):
        held = next(s for s in self.auto.steps if s.action == decl.HELD_AWAIT)
        rung = next(r for r in self.rungs
                    if r.startswith(f"EQU(FRK_Press_Unit.Step,{held.number})"))
        self.assertIn(f"MOV({held.hold_reason},FRK_Press_Unit.HeldReason)", rung)
        self.assertNotIn("MOV(1,FRK_Press_Unit.Error)", rung)


class RenditionGateTests(unittest.TestCase):
    def setUp(self):
        self.app = demo.application()
        self.root = emit_project()

    def test_every_rendition_equals_the_declaration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.L5X"
            path.write_bytes(ET.tostring(self.root))
            report = gate.compare(self.app, path)
        self.assertTrue(report["Equal"], report["Findings"])
        for chain in report["Chains"].values():
            for rendition in chain["renditions"]:
                self.assertTrue(chain[rendition]["equalsDeclaration"])

    def _compare_mutated(self, mutate):
        root = copy.deepcopy(self.root)
        mutate(root)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.L5X"
            path.write_bytes(ET.tostring(root))
            return gate.compare(self.app, path)

    def test_a_ladder_rendition_that_lost_a_step_is_rejected(self):
        def drop_a_rung(root):
            for routine in root.findall(".//Routine"):
                if routine.get("Type") != "RLL":
                    continue
                content = routine.find(".//RLLContent")
                rungs = content.findall("./Rung")
                content.remove(rungs[-1])

        report = self._compare_mutated(drop_a_rung)
        self.assertFalse(report["Equal"])
        self.assertTrue(any("step set differs" in f for f in report["Findings"]))

    def test_a_ladder_rendition_that_jumps_somewhere_else_is_rejected(self):
        def bend_a_transition(root):
            for routine in root.findall(".//Routine"):
                if routine.get("Type") != "RLL":
                    continue
                for rung in routine.findall(".//RLLContent/Rung"):
                    text = rung.find("Text")
                    if "MOV(130,FRK_Press_Unit.Step)" in (text.text or ""):
                        text.text = text.text.replace(
                            "MOV(130,FRK_Press_Unit.Step)",
                            "MOV(999,FRK_Press_Unit.Step)")
                        return

        report = self._compare_mutated(bend_a_transition)
        self.assertFalse(report["Equal"])
        self.assertTrue(any("goes to" in f for f in report["Findings"]))

    def test_rungs_out_of_step_order_are_rejected(self):
        def reverse_rungs(root):
            for routine in root.findall(".//Routine"):
                if routine.get("Type") != "RLL":
                    continue
                content = routine.find(".//RLLContent")
                rungs = content.findall("./Rung")
                gated = [r for r in rungs
                         if (r.find("Text").text or "").startswith("EQU(")]
                for rung in gated:
                    content.remove(rung)
                for rung in reversed(gated):
                    content.append(rung)
                return

        report = self._compare_mutated(reverse_rungs)
        self.assertFalse(report["Equal"])
        self.assertTrue(any("ascending step order" in f for f in report["Findings"]))

    def test_a_rendition_that_cannot_be_parsed_fails_rather_than_passing(self):
        """Silence is not parity: an unreadable rendition is a failure."""
        def blank_the_ladder(root):
            for routine in root.findall(".//Routine"):
                if routine.get("Type") != "RLL":
                    continue
                content = routine.find(".//RLLContent")
                for rung in content.findall("./Rung"):
                    content.remove(rung)
                return

        report = self._compare_mutated(blank_the_ladder)
        self.assertFalse(report["Equal"])
        self.assertTrue(any("no step rungs" in f for f in report["Findings"]))

    def test_a_missing_routine_is_a_failure_not_a_skip(self):
        def delete_the_ladder(root):
            for program in root.findall(".//Program"):
                routines = program.find("./Routines")
                for routine in routines.findall("./Routine"):
                    if routine.get("Type") == "RLL":
                        routines.remove(routine)
                        return

        report = self._compare_mutated(delete_the_ladder)
        self.assertFalse(report["Equal"])
        self.assertTrue(any("is not in the emitted project" in f
                            for f in report["Findings"]))


class EmittedRenditionTests(unittest.TestCase):
    def setUp(self):
        self.root = emit_project()
        self.app = demo.application()

    def test_the_program_carries_one_routine_per_rendition(self):
        names = {r.get("Name"): r.get("Type")
                 for r in self.root.findall(".//Program/Routines/Routine")}
        auto = next(c for c in self.app.chains if c.name == "AUTO")
        for rendition in auto.renditions:
            expected = {"ST": "ST", "LD": "RLL", "SFC": "SFC"}[rendition]
            name = gen.chain_routine_name(self.app, auto, rendition)
            self.assertIn(name, names)
            self.assertEqual(names[name], expected)

    def test_exactly_one_rendition_is_dispatched_per_scan(self):
        main = [r for r in self.root.findall(".//Program/Routines/Routine")
                if r.get("Name") == self.app.routine][0]
        body = "\n".join((l.text or "") for l in main.findall(".//STContent/Line"))
        select = gen.rendition_tag(self.app)
        auto = next(c for c in self.app.chains if c.name == "AUTO")
        for rendition in auto.renditions:
            self.assertIn(f"IF {select} = {gen.rendition_ordinal(rendition)} THEN", body)

    def test_the_single_rendition_chains_stay_in_the_owner_aoi(self):
        unit = [a for a in self.root.findall(".//AddOnInstructionDefinition")
                if a.get("Name") == gen.unit_aoi_name(self.app)][0]
        body = "\n".join((l.text or "") for l in unit.findall(".//STContent/Line"))
        for chain in self.app.chains:
            if chain.multi_rendition:
                continue
            self.assertIn(f"IF Ctx.Mode = {chain.mode_ordinal} THEN", body)

    def test_the_multi_rendition_chain_is_not_also_in_the_aoi(self):
        """One graph, one place per rendition - never a fourth hidden copy."""
        unit = [a for a in self.root.findall(".//AddOnInstructionDefinition")
                if a.get("Name") == gen.unit_aoi_name(self.app)][0]
        body = "\n".join((l.text or "") for l in unit.findall(".//STContent/Line"))
        auto = next(c for c in self.app.chains if c.name == "AUTO")
        self.assertNotIn(f"IF Ctx.Mode = {auto.mode_ordinal} THEN", body)


if __name__ == "__main__":
    unittest.main()
