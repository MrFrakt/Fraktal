"""TC3's N220 on the Allen-Bradley binding: a dwell that pauses.

TC3's AUTO N220 presses for the recipe dwell with the two-hand held. Releasing
it is the designed way to stop pressing, so it is a named wait - record 1,
`twoHandHeldDuringPress` - and not a fault and not a hold: the dwell stands
still and pressing again finishes the time that remained. A dwell that went
on counting while released would credit a part with dwell it spent unpressed.

AB's delay used to read the step clock, which counts the pause. It now keeps
its own clock (`Chart.DelayMs`) that runs only while the step's conditions
hold, in every rendition; a plain delay is the same clock with nothing to wait
for. These tests run each rendition of the real AUTO chain - ST and the SFC
action on the ST model, the ladder on the ladder model - scan by scan.
"""

import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_ld_model as ld
import fraktal_ab_press_demo as demo
import fraktal_ab_st_model as st
from test_fraktal_ab_digital_input import run_passive_modules


APP = demo.application()
N = APP.name
AUTO = next(c for c in APP.chains if c.name == "AUTO")
CHART, UNIT = f"FRK_{N}_Chart", f"FRK_{N}_Unit"
CFG = f"{APP.records[0].name}Tag"
SCAN = f"FRK_{N}_ScanCount"
TWO_HAND = f"FRK_{N}_TwoHand"
PROBE = "FRK_Test_Transition"
PERIOD = APP.task_period_ms
DWELL = next(s for s in AUTO.steps if s.number == 220)
SETTLE = next(s for s in AUTO.steps if s.number == 170)
NAMES = gen.Names(APP, in_aoi=False)
ORDER = gen.ordered_steps(APP)


def controller():
    tags = {
        UNIT: st.structure(gen.unit_context_members(APP)),
        CHART: st.structure(gen.chart_members(APP)),
        **{f"{r.name}Tag": st.structure(r.members) for r in APP.records},
        SCAN: 1,
        gen.ld_advanced_tag(APP): 0,
        gen.ld_scratch_tag(APP): 0,
        PROBE: 0,
    }
    for module in APP.modules:
        tags[gen.ctx_tag_for(APP, module.name)] = st.structure(gen.module_members(module))
    for tag in APP.sim_inputs:
        tags[tag] = 0
    return st.Controller(tags, routines={gen.step_mark_routine_name(APP): gen.step_mark_logic(APP)})


class Rendition:
    """One rendition of AUTO, scanned from the entry of one step until it
    leaves it. The scan order is the routine's: modules, then the chain."""

    def __init__(self, language, step, dwell_ms=300, two_hand=1):
        self.language, self.step = language, step
        self.plc = controller()
        self.plc.tags[CFG]["PressDwellMs"] = dwell_ms
        self.plc.tags[TWO_HAND] = two_hand
        self.plc.tags[UNIT].update(Step=step.number, PrevStep=-1, Running=1)
        index = ORDER.index(step.number)
        if language == decl.ST:
            self.logic = st.parse("\n".join(gen.chain_st_logic(APP, AUTO)))
        elif language == decl.SFC:
            self.action = st.parse("\n".join(
                gen.sfc_action_logic(APP, AUTO, step, index, NAMES)))
            # The chart's outgoing transitions, in its own priority order:
            # the advance, then the jump.
            self.transitions = [
                (target, st.parse(f"IF {gen.sfc_condition(APP, step, kind, NAMES)} "
                                  f"THEN {PROBE} := 1; ELSE {PROBE} := 0; END_IF;"))
                for kind, target in (("A", step.on_advance), ("J", step.on_jump))
                if target != -1]
        else:
            self.rungs = [ld.parse_rung(r) for r in gen.chain_ld_rungs(APP, AUTO)]
        self.scans = 0
        self.left = False
        self.went_to = None

    @property
    def chart(self):
        return self.plc.tags[CHART]

    @property
    def unit(self):
        return self.plc.tags[UNIT]

    def press(self, held):
        self.plc.tags[TWO_HAND] = 1 if held else 0

    def scan(self):
        assert not self.left, "the step was already left"
        self.plc.tags[SCAN] += 1
        self.scans += 1
        run_passive_modules(APP, self.plc.tags, scan=self.plc.tags[SCAN])
        if self.language == decl.SFC:
            self.plc.run(self.action)
            for target, transition in self.transitions:
                self.plc.run(transition)
                if self.plc.tags[PROBE] == 1:
                    self.left, self.went_to = True, target
                    break
            return self.left
        if self.language == decl.ST:
            self.plc.run(self.logic)
        else:
            ld.run_rungs(self.plc, self.rungs)
        if self.unit["Step"] != self.step.number:
            self.left, self.went_to = True, self.unit["Step"]
        return self.left

    def scan_until_left(self, limit=10_000):
        for _ in range(limit):
            if self.scan():
                return self.scans
        raise AssertionError(f"{self.language} never left N{self.step.number}")


LANGUAGES = AUTO.renditions


class TheDwellPauses(unittest.TestCase):
    def test_n220_is_tc3s_named_wait(self):
        self.assertEqual(DWELL.action, decl.DELAY)
        self.assertEqual(decl.step_conditions(DWELL),
                         ((decl.RequiredBy(decl.ModuleState("TwoHand", ("OutImm_SafeActive",)),
                                           "RequireTwoHandStart"),
                           "project.condition.twoHandHeldDuringPress"),))

    def test_held_throughout_it_takes_exactly_the_dwell(self):
        for language in LANGUAGES:
            with self.subTest(language):
                r = Rendition(language, DWELL, dwell_ms=300)
                # the entry scan is time zero: 300 ms is 30 more scans
                self.assertEqual(r.scan_until_left(), 300 // PERIOD + 1)
                self.assertEqual(r.chart["DelayMs"], 300)

    def test_released_it_stands_still_without_fault_or_hold(self):
        for language in LANGUAGES:
            with self.subTest(language):
                r = Rendition(language, DWELL, dwell_ms=300)
                for _ in range(11):
                    r.scan()
                ran = r.chart["DelayMs"]
                self.assertEqual(ran, 10 * PERIOD)
                r.press(False)
                for _ in range(200):          # two seconds, far past the dwell
                    self.assertFalse(r.scan(), "a released dwell must not finish")
                self.assertEqual(r.chart["DelayMs"], ran, "the dwell clock paused")
                self.assertEqual(r.unit["Step"], 220)
                # TC3's N220 is a wait, not a hold and not a fault
                self.assertEqual(r.unit["Error"], 0)
                self.assertEqual(r.chart["CondOk"][0], 0)
                self.assertEqual(r.chart["StallReason"], demo.REASONS["WAIT_CONDITION"])

    def test_pressing_again_finishes_only_what_remained(self):
        for language in LANGUAGES:
            with self.subTest(language):
                r = Rendition(language, DWELL, dwell_ms=300)
                for _ in range(11):
                    r.scan()
                r.press(False)
                for _ in range(200):
                    r.scan()
                r.press(True)
                before = r.scans
                after = r.scan_until_left() - before
                self.assertEqual(after, (300 - 10 * PERIOD) // PERIOD)
                self.assertEqual(r.chart["DelayMs"], 300,
                                 "the part was pressed for the dwell, no more, no less")
                self.assertEqual(r.chart["CondOk"][0], 1)
                # the step's own duration still counts the pause
                self.assertGreaterEqual(r.chart["LastMs"][ORDER.index(220)], 300 + 2000)

    def test_each_visit_starts_from_zero(self):
        """N170's settle runs just before, and leaves its own time on the
        clock. The dwell must not inherit it."""
        for language in LANGUAGES:
            with self.subTest(language):
                r = Rendition(language, DWELL, dwell_ms=300)
                r.chart["DelayMs"] = 200
                self.assertEqual(r.scan_until_left(), 300 // PERIOD + 1)

    def test_a_release_at_entry_never_starts_the_dwell(self):
        for language in LANGUAGES:
            with self.subTest(language):
                r = Rendition(language, DWELL, dwell_ms=300, two_hand=0)
                for _ in range(50):
                    r.scan()
                self.assertEqual(r.chart["DelayMs"], 0)
                self.assertFalse(r.left)

    def test_every_rendition_walks_the_same_dwell(self):
        def walk(language):
            r = Rendition(language, DWELL, dwell_ms=250)
            trace = []
            for k in range(60):
                r.press(not 8 <= k < 20)
                left = r.scan()
                trace.append((r.chart["DelayMs"], r.chart["CondOk"][0],
                              r.chart["StallReason"], left))
                if left:
                    break
            return trace
        reference = walk(decl.ST)
        for language in LANGUAGES[1:]:
            with self.subTest(language):
                self.assertEqual(walk(language), reference)


class ThePolicy(unittest.TestCase):
    """RequireTwoHandStart, the cell's own policy: cleared, the dwell does
    not wait for the buttons, as TC3's `SafeActive OR NOT RequireTwoHandStart`."""

    def test_without_the_policy_a_release_does_not_pause_it(self):
        station = next(r for r in APP.records if r.station_cfg)
        for language in LANGUAGES:
            with self.subTest(language):
                r = Rendition(language, DWELL, dwell_ms=300, two_hand=0)
                r.plc.tags[f"{station.name}Tag"]["RequireTwoHandStart"] = 0
                self.assertEqual(r.scan_until_left(), 300 // PERIOD + 1)
                self.assertEqual(r.chart["CondOk"][0], 1)


class APlainDelayIsUnchanged(unittest.TestCase):
    """N170 has nothing to wait for: its clock is the step clock it used to read."""

    def test_the_settle_takes_its_declared_time_in_every_rendition(self):
        settle = APP.records[0].members
        initial = next(m.initial for m in settle if m.name == "TransferSettleMs")
        for language in LANGUAGES:
            with self.subTest(language):
                r = Rendition(language, SETTLE)
                self.assertEqual(r.scan_until_left(), initial // PERIOD + 1)
                self.assertEqual(r.chart["DelayMs"], r.chart["CurrentStepMs"])

    def test_a_two_hand_release_does_not_pause_it(self):
        for language in LANGUAGES:
            with self.subTest(language):
                r = Rendition(language, SETTLE, two_hand=0)
                self.assertEqual(r.scan_until_left(),
                                 Rendition(language, SETTLE).scan_until_left())


class TheDeclarationRule(unittest.TestCase):
    def test_a_delay_may_wait_on_conditions(self):
        self.assertEqual(decl.validate(APP), [])

    def test_a_delay_condition_needs_its_label(self):
        import dataclasses
        bad = dataclasses.replace(DWELL, condition_labels=())
        chain = dataclasses.replace(AUTO, steps=tuple(
            bad if s.number == 220 else s for s in AUTO.steps))
        app = dataclasses.replace(APP, chains=tuple(
            chain if c.name == "AUTO" else c for c in APP.chains))
        self.assertTrue(any("label" in f for f in decl.validate(app)))


if __name__ == "__main__":
    unittest.main()
