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



class SfcEmissionTests(unittest.TestCase):
    """The chart is a real SFC rendering, not an ST chain wearing a chart."""

    def setUp(self):
        self.app = demo.application()
        self.auto = next(c for c in self.app.chains if c.name == "AUTO")
        self.root = emit_project()
        self.chart = [r for r in self.root.findall(".//Program/Routines/Routine")
                      if r.get("Type") == "SFC"][0].find(".//SFCContent")

    def test_one_step_and_one_action_per_declared_step(self):
        steps = self.chart.findall("./Step")
        self.assertEqual(len(steps), len(self.auto.steps))
        for step in steps:
            self.assertEqual(len(step.findall("./Action")), 1)

    def test_one_transition_per_declared_edge(self):
        edges = gen.sfc_edges(self.auto)
        self.assertEqual(len(self.chart.findall("./Transition")), len(edges))

    def test_the_first_step_is_the_initial_step_and_the_only_one(self):
        initial = [s for s in self.chart.findall("./Step")
                   if s.get("InitialStep") == "true"]
        self.assertEqual(len(initial), 1)
        first = sorted(self.auto.steps, key=lambda s: s.number)[0]
        self.assertEqual(initial[0].get("Operand"),
                         gen.sfc_step_tag(self.app, self.auto, first.number))

    def test_a_selection_diverge_wherever_a_step_has_two_outgoing_edges(self):
        forks = [s for s in self.auto.steps if s.on_jump != -1]
        diverges = [b for b in self.chart.findall("./Branch")
                    if b.get("BranchFlow") == "Diverge"]
        self.assertEqual(len(diverges), len(forks))
        for branch in diverges:
            self.assertEqual(branch.get("BranchType"), "Selection")

    def test_a_selection_converge_wherever_a_step_has_several_parents(self):
        """Logix accepts one directed link into a step; the graph converges twice."""
        incoming = {}
        for source, target, kind in gen.sfc_edges(self.auto):
            incoming.setdefault(target, []).append(source)
        joins = [t for t, sources in incoming.items() if len(sources) > 1]
        converges = [b for b in self.chart.findall("./Branch")
                     if b.get("BranchFlow") == "Converge"]
        self.assertEqual(len(converges), len(joins))
        self.assertEqual(sorted(len(b.findall("./Leg")) for b in converges),
                         sorted(len(incoming[t]) for t in joins))

    def test_no_step_takes_more_than_one_directed_link(self):
        step_ids = {s.get("ID") for s in self.chart.findall("./Step")}
        incoming = {}
        for link in self.chart.findall("./DirectedLink"):
            incoming.setdefault(link.get("ToID"), []).append(link.get("FromID"))
        for target, sources in incoming.items():
            if target in step_ids:
                self.assertEqual(len(sources), 1, f"step {target} has {sources}")

    def test_the_action_does_the_work_and_the_transition_carries_the_condition(self):
        """Splitting them is what makes this SFC rather than ST in a chart."""
        names = gen.Names(self.app, in_aoi=False)
        issue = next(s for s in self.auto.steps if s.action == decl.ISSUE)
        action = "\n".join(gen.sfc_action_logic(
            self.app, self.auto, issue, 0, names))
        self.assertIn("ParCmd_Command", action)
        self.assertNotIn(f"Step := {issue.on_advance};", action)
        condition = gen.sfc_condition(self.app, issue, "A", names)
        self.assertIn("Done", condition)

    def test_the_runner_is_the_generated_jsr_sfr_wrapper(self):
        runner = [r for r in self.root.findall(".//Program/Routines/Routine")
                  if r.get("Name") == gen.sfc_runner_name(self.app, self.auto)][0]
        body = "\n".join((l.text or "") for l in runner.findall(".//STContent/Line"))
        self.assertIn("SFR(", body)
        self.assertIn("JSR(", body)

    def test_the_controller_executes_current_active_steps_only(self):
        """One JSR advances one step, which is what makes traces comparable."""
        controller = self.root.find(".//Controller")
        self.assertEqual(controller.get("SFCExecutionControl"), "CurrentActive")
        self.assertEqual(controller.get("SFCRestartPosition"), "InitialStep")
        self.assertEqual(controller.get("SFCLastScan"), "DontScan")

    def test_the_chart_declares_its_step_action_and_transition_tags(self):
        tags = {t.get("Name"): t.get("DataType")
                for t in self.root.findall(".//Program/Tags/Tag")}
        for step in self.auto.steps:
            self.assertEqual(tags.get(gen.sfc_step_tag(self.app, self.auto, step.number)),
                             "SFC_STEP")
            self.assertEqual(tags.get(gen.sfc_action_tag(self.app, self.auto, step.number)),
                             "SFC_ACTION")

    def test_a_chart_with_a_bent_link_is_rejected_by_the_gate(self):
        """The gate must notice when the chart stops matching the declaration."""
        root = copy.deepcopy(self.root)
        chart = [r for r in root.findall(".//Program/Routines/Routine")
                 if r.get("Type") == "SFC"][0].find(".//SFCContent")
        steps = {s.get("Operand"): s.get("ID") for s in chart.findall("./Step")}
        first = gen.sfc_step_tag(self.app, self.auto, 110)
        last = gen.sfc_step_tag(self.app, self.auto, 999)
        for link in chart.findall("./DirectedLink"):
            if link.get("ToID") == steps[first]:
                link.set("ToID", steps[last])
                break
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.L5X"
            path.write_bytes(ET.tostring(root))
            report = gate.compare(self.app, path)
        self.assertFalse(report["Equal"])
        self.assertTrue(any("SFC" in f for f in report["Findings"]))


class ParityHarnessTests(unittest.TestCase):
    """The measurement window must be defined by the graph, not by the observer."""

    def setUp(self):
        import fraktal_ab_press_parity as parity
        self.parity = parity
        self.app = demo.application()
        self.auto = next(c for c in self.app.chains if c.name == "AUTO")

    def test_the_park_step_is_where_the_loop_closes(self):
        terminal = max(self.auto.steps, key=lambda s: s.number)
        self.assertEqual(self.parity.PARK_STEP, terminal.on_advance)

    def test_the_withdrawal_point_is_past_the_park_step(self):
        """Waiting for 'not the start step' would fire on the init step."""
        park = next(s for s in self.auto.steps
                    if s.number == self.parity.PARK_STEP)
        self.assertEqual(self.parity.AFTER_PARK, park.on_advance)
        self.assertNotEqual(self.parity.AFTER_PARK, self.parity.PARK_STEP)
        self.assertNotEqual(self.parity.AFTER_PARK,
                            min(s.number for s in self.auto.steps))

    def test_the_withdrawn_condition_is_read_only_by_the_park_step(self):
        """Withdrawing it must not affect the cycle being measured."""
        readers = [s.number for s in self.auto.steps
                   if self.parity.px.PART_PRESENT in s.conditions
                   or s.hold_condition == self.parity.px.PART_PRESENT]
        self.assertEqual(readers, [self.parity.PARK_STEP])

    def test_every_rendition_is_walked(self):
        self.assertEqual(list(self.auto.renditions), list(decl.RENDITIONS))

    def test_the_rendition_selector_is_writable_and_ordinals_are_stable(self):
        self.assertIn(gen.rendition_tag(self.app), self.parity.px.WRITABLE)
        self.assertEqual(gen.rendition_ordinal(decl.ST), 0)
        self.assertEqual(
            [gen.rendition_ordinal(r) for r in decl.RENDITIONS], [0, 1, 2])

    def test_the_entry_vector_covers_every_declared_auto_step(self):
        self.assertEqual(sorted(self.parity.AUTO_INDEXES),
                         sorted(s.number for s in self.auto.steps))


class PublishedContractTests(unittest.TestCase):
    """The published contract describes the graph once, rendition-agnostic.

    The TC3 HMI sees one chart whichever rendition ran, and the AB contract says
    the same thing: which language executed is a property of how this
    application is being measured, not of the machine it describes.
    """

    def setUp(self):
        self.app = demo.application()
        self.selector = gen.rendition_tag(self.app)

    def test_the_rendition_selector_is_harness_only(self):
        self.assertIn(self.selector, gen.harness_only_tags(self.app))

    def test_the_rendition_selector_is_not_published(self):
        """Publishing it would invite a client to choose a language."""
        self.assertNotIn(self.selector, gen.publishable_tags(self.app))

    def test_the_selector_is_still_probe_writable(self):
        """Probe-only means unpublished, not hidden: the harness drives it."""
        self.assertIn(self.selector, gen.writable_inputs(self.app))

    def test_ladder_implementation_tags_are_not_published(self):
        """The guard and scratch are how one rendition happens to work."""
        for tag in (gen.ld_advanced_tag(self.app), gen.ld_scratch_tag(self.app)):
            self.assertIn(tag, gen.harness_only_tags(self.app))
            self.assertNotIn(tag, gen.publishable_tags(self.app))

    def test_the_published_set_does_not_change_with_the_number_of_renditions(self):
        """The load-bearing one: one graph, one published contract.

        Rendering AUTO once or three times must make no difference to what a
        client can see - otherwise the contract would be describing the emission
        rather than the machine.
        """
        auto = next(c for c in self.app.chains if c.name == "AUTO")
        single = dataclasses.replace(auto, renditions=(decl.ST,))
        one_rendition = dataclasses.replace(
            self.app,
            chains=tuple(single if c.name == "AUTO" else c for c in self.app.chains))
        self.assertEqual(gen.publishable_tags(one_rendition),
                         gen.publishable_tags(self.app))

    def test_no_published_tag_names_a_rendition(self):
        for tag in gen.publishable_tags(self.app):
            for rendition in decl.RENDITIONS:
                self.assertNotIn(rendition.title(), tag, tag)
                self.assertNotIn(f"_{rendition}", tag, tag)

    def test_the_contract_structures_are_published(self):
        """Excluding the harness must not exclude the machine."""
        published = gen.publishable_tags(self.app)
        for expected in (f"FRK_{self.app.name}_Unit", f"FRK_{self.app.name}_Chart",
                         f"{self.app.records[0].name}Tag"):
            self.assertIn(expected, published)
        for module in self.app.modules:
            self.assertIn(gen.ctx_tag_for(self.app, module.name), published)

    def test_harness_only_and_published_do_not_overlap(self):
        self.assertEqual(
            set(gen.harness_only_tags(self.app)) & set(gen.publishable_tags(self.app)),
            set())

    def test_an_application_with_no_multi_rendition_chain_has_no_selector(self):
        """A single-rendition application should not carry the concept at all."""
        chains = tuple(dataclasses.replace(c, renditions=(decl.ST,))
                       for c in self.app.chains)
        plain = dataclasses.replace(self.app, chains=chains)
        self.assertNotIn(gen.rendition_tag(plain), gen.writable_inputs(plain))
        self.assertNotIn(gen.rendition_tag(plain), gen.harness_only_tags(plain))

if __name__ == "__main__":
    unittest.main()
