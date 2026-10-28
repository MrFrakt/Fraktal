"""TC3's run styles (Core §3.4.2) on the Allen-Bradley binding.

A running mode advances CONTINUOUS, SINGLE_STEP (one command per Step request)
or HOLD_TO_RUN (commands issue only while the operator holds the button). TC3
paces the ISSUE, not the motion: its M_TryIssue asks the Unit's _M_StepGate
once per step visit, and a command once issued runs to Done whatever the
button does next. The modules' interlocks decide whether anything moves in
every style; pacing is NON-SAFETY and never a dead-man.

The cycles here run the generated module layer, the mode owner's pacer and one
AUTO rendition in routine order (the harness of test_fraktal_ab_rendition_cycle),
so what is proved is what the plant did - commands issued and completed - in
ST, SFC and LD alike.
"""

import dataclasses
import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_ld_model as ld
import fraktal_ab_mailbox as mailbox
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
import fraktal_ab_st_model as st
from test_fraktal_ab_core_ordinals import core_enum
from test_fraktal_ab_manual import Bench, key
from test_fraktal_ab_rendition_cycle import (APP, AUTO, CYLINDERS, NAMES, ORDER, UNIT,
                                             Press, commands_per_module)


CONTINUOUS, SINGLE_STEP, HOLD_TO_RUN = (decl.RUN_CONTINUOUS, decl.RUN_SINGLE_STEP,
                                        decl.RUN_HOLD_TO_RUN)
COMMANDING = {s.number for s in AUTO.steps
              if s.action in (decl.ISSUE, decl.GUARDED, decl.ADOPT, decl.REPORT)}
PACER = st.parse("\n".join(gen.run_style_logic(APP)))


class Paced(Press):
    """The press with its mode owner's pacer, which runs before the chain."""

    def __init__(self, language, style, start=100):
        super().__init__(language, start)
        self.unit["RunStyle"] = style

    @property
    def unit(self):
        return self.plc.tags[UNIT]

    def scan(self):
        st.Controller({"Ctx": self.unit}).run(PACER)
        super().scan()

    def issued(self):
        return sum(self.ctx(n)["RunCount"] for n in CYLINDERS)

    def completed(self):
        return sum(self.ctx(n)["DoneCount"] for n in CYLINDERS)

    def waiting(self):
        """At a commanding step that has not issued: a stop point."""
        return self.step() in COMMANDING and self.unit["Issued"] == 0

    def stepped_to(self, number, limit=3000):
        """SINGLE_STEP: grant a Step at every stop point before N`number`,
        and stop waiting at it."""
        for _ in range(limit):
            self.scan()
            if self.waiting() and self.step() == number:
                return
            if self.waiting() and self.unit["StepPending"] == 0:
                self.unit["StepPending"] = 1
        raise AssertionError(f"{self.language}: never waited at N{number}")

    def scan_until(self, predicate, limit=400):
        for _ in range(limit):
            self.scan()
            if predicate():
                return
        raise AssertionError(f"{self.language}: still at N{self.step()}")


def stepped_cycle(press, idle=25, limit=6000):
    """One AUTO cycle in SINGLE_STEP. At every stop point the press is left
    alone for `idle` scans before a Step request is given. Returns the number
    of commands issued before the first request and after each one."""
    before, per_request, seen_end, still = press.issued(), [], False, 0
    for _ in range(limit):
        press.scan()
        still = still + 1 if press.waiting() and press.unit["StepPending"] == 0 else 0
        if still >= idle:
            per_request.append(press.issued() - before)
            before, still = press.issued(), 0
            press.unit["StepPending"] = 1          # what STEP_REQUEST writes
        seen_end = seen_end or press.step() == 999
        if seen_end and press.step() == 100:
            per_request.append(press.issued() - before)
            return per_request
    raise AssertionError(f"{press.language}: the stepped cycle did not close")


class TheContract(unittest.TestCase):
    def test_run_styles_are_tc3s(self):
        self.assertEqual({"CONTINUOUS": CONTINUOUS, "SINGLE_STEP": SINGLE_STEP,
                          "HOLD_TO_RUN": HOLD_TO_RUN}, core_enum("E_RunStyle"))
        self.assertEqual(decl.RUN_STYLES, (CONTINUOUS, SINGLE_STEP, HOLD_TO_RUN))

    def test_the_press_offers_all_three_as_tc3s_press_does(self):
        self.assertEqual(APP.run_styles, decl.RUN_STYLES)

    def test_every_commanding_step_is_a_stop_point(self):
        """TC3's press calls M_TryIssue(Steppable := TRUE) at every command."""
        self.assertTrue(all(s.steppable for s in AUTO.steps if s.number in COMMANDING))

    def test_a_unit_without_styles_carries_none_of_it(self):
        plain = dataclasses.replace(APP, run_styles=(CONTINUOUS,))
        names = {m.name for m in gen.unit_context_members(plain)}
        self.assertFalse(names & {"RunStyle", "StepPending", "HoldRun", "StepPermit",
                                  "Issued"})
        self.assertEqual(gen.run_style_logic(plain), [])
        self.assertEqual(mailbox.run_style_dispatch(plain), [])
        self.assertNotIn("StepPermit", "\n".join(gen.chain_st_logic(plain, AUTO)))
        for kind in (mailbox.SET_RUN_STYLE, mailbox.STEP_REQUEST, mailbox.SET_HOLD_RUN):
            self.assertIn(kind, mailbox.refused_for(plain))

    def test_a_declaration_must_keep_continuous(self):
        self.assertIn("a Unit always runs CONTINUOUS; run_styles must include it",
                      decl.validate(dataclasses.replace(APP, run_styles=(SINGLE_STEP,))))
        self.assertIn("run style 3 is not a Core E_RunStyle",
                      decl.validate(dataclasses.replace(APP, run_styles=(CONTINUOUS, 3))))


class Continuous(unittest.TestCase):
    def test_the_pacer_changes_nothing(self):
        """The default style runs exactly as an unpaced press did."""
        for language in AUTO.renditions:
            with self.subTest(language):
                paced = Paced(language, CONTINUOUS).one_cycle()
                plain = Press(language).one_cycle()
                for field in ("runs", "dones", "steps", "scans"):
                    self.assertEqual(paced[field], plain[field], field)


class SingleStep(unittest.TestCase):
    def test_one_command_per_step_request(self):
        """Nothing issues before the first request, and each request issues
        exactly one command: the whole cycle, one stop point at a time."""
        for language in AUTO.renditions:
            with self.subTest(language):
                per_request = stepped_cycle(Paced(language, SINGLE_STEP))
                self.assertEqual(per_request[0], 0, "issued before any request")
                self.assertEqual(per_request[1:], [1] * sum(commands_per_module().values()))

    def test_the_stepped_cycle_commands_what_the_continuous_one_does(self):
        for language in AUTO.renditions:
            with self.subTest(language):
                press = Paced(language, SINGLE_STEP)
                runs = {n: press.ctx(n)["RunCount"] for n in CYLINDERS}
                stepped_cycle(press)
                self.assertEqual({n: press.ctx(n)["RunCount"] - runs[n] for n in CYLINDERS},
                                 commands_per_module())

    def test_a_request_during_motion_is_kept_for_the_next_stop_point(self):
        """TC3: M_TryIssue does not ask the gate once issued, so a request
        made while the slide moves stays pending and releases the door."""
        for language in AUTO.renditions:
            with self.subTest(language):
                press = Paced(language, SINGLE_STEP)
                press.stepped_to(150)
                door = press.ctx("Door")["RunCount"]
                press.unit["StepPending"] = 1
                press.scan_until(lambda: press.ctx("PartSlide")["Busy"] != 0)
                press.unit["StepPending"] = 1           # pressed again, mid-motion
                press.scan_until(lambda: press.ctx("Door")["RunCount"] == door + 1)
                self.assertEqual((press.step(), press.unit["StepPending"]), (180, 0),
                                 "the door consumed it")
                press.scan_until(lambda: press.step() == 200)
                for _ in range(40):
                    press.scan()
                self.assertTrue(press.waiting(), "one request, one command")


class HoldToRun(unittest.TestCase):
    def test_nothing_issues_until_held(self):
        for language in AUTO.renditions:
            with self.subTest(language):
                press = Paced(language, HOLD_TO_RUN)
                for _ in range(100):
                    press.scan()
                self.assertEqual((press.step(), press.issued()), (110, 0))

    def test_held_throughout_it_runs_the_continuous_cycle(self):
        for language in AUTO.renditions:
            with self.subTest(language):
                press = Paced(language, HOLD_TO_RUN)
                press.unit["HoldRun"] = 1
                cycle = press.one_cycle()
                self.assertEqual(cycle["runs"], commands_per_module())
                self.assertEqual(cycle["steps"], Press(language).one_cycle()["steps"])

    def test_a_release_mid_motion_finishes_the_motion_and_stops_there(self):
        """The ISSUE is paced, not the motion (TC3 M_TryIssue): letting go
        while the slide goes in lets it arrive, the settle runs (not a stop
        point), and the door is not commanded to close."""
        for language in AUTO.renditions:
            with self.subTest(language):
                press = Paced(language, HOLD_TO_RUN)
                press.unit["HoldRun"] = 1
                press.scan_until(lambda: press.ctx("PartSlide")["Busy"] != 0)
                press.unit["HoldRun"] = 0
                door = press.ctx("Door")["RunCount"]
                done = press.ctx("PartSlide")["DoneCount"]
                press.scan_until(lambda: press.step() == 180)
                for _ in range(60):
                    press.scan()
                self.assertEqual(press.ctx("PartSlide")["DoneCount"], done + 1)
                self.assertEqual((press.step(), press.ctx("Door")["RunCount"]),
                                 (180, door))
                press.unit["HoldRun"] = 1
                press.scan_until(lambda: press.ctx("Door")["RunCount"] == door + 1)


class NotRunningClearsBoth(unittest.TestCase):
    def test_a_stopped_unit_holds_no_request_and_no_hold(self):
        """A stop, fault, reset, abort or mode change drops Running, and
        whatever an operator held or asked for is gone with it."""
        for style in (SINGLE_STEP, HOLD_TO_RUN):
            press = Paced(decl.ST, style)
            press.unit.update(StepPending=1, HoldRun=1, Running=0)
            press.scan()
            self.assertEqual((press.unit["StepPending"], press.unit["HoldRun"],
                              press.issued()), (0, 0, 0), style)

    def test_a_running_unit_keeps_them(self):
        press = Paced(decl.ST, HOLD_TO_RUN)
        press.unit["HoldRun"] = 1
        press.scan()
        self.assertEqual(press.unit["HoldRun"], 1)


class NotAStopPoint(unittest.TestCase):
    """TC3's Steppable := FALSE: a step that runs straight through in every
    style (several motions as one operator step, or one unsafe to pause)."""

    def test_a_non_steppable_step_issues_without_a_request(self):
        steps = tuple(dataclasses.replace(s, steppable=False) if s.number == 110 else s
                      for s in AUTO.steps)
        chain = dataclasses.replace(AUTO, steps=steps)
        app = dataclasses.replace(APP, chains=tuple(chain if c is AUTO else c
                                                    for c in APP.chains))
        for language in AUTO.renditions:
            with self.subTest(language):
                press = Paced(language, SINGLE_STEP)
                if language == decl.ST:
                    press.logic = st.parse("\n".join(gen.chain_st_logic(app, chain)))
                elif language == decl.LD:
                    press.rungs = [ld.parse_rung(r) for r in gen.chain_ld_rungs(app, chain)]
                else:
                    step = steps[[s.number for s in steps].index(110)]
                    press.actions[110] = st.parse("\n".join(gen.sfc_action_logic(
                        app, chain, step, ORDER.index(110), NAMES)))
                press.scan_until(lambda: press.step() == 130)
                for _ in range(60):
                    press.scan()
                self.assertEqual((press.ctx("PressRam")["DoneCount"],
                                  press.ctx("Door")["RunCount"]), (1, 0))


class TheMailbox(unittest.TestCase):
    def running(self, style):
        bench = Bench(mode=AUTO.mode_ordinal)
        self.assertEqual(bench.request(mailbox.SET_RUN_STYLE, value=style), (1, 0))
        self.assertEqual(bench.request(mailbox.START), (1, 0))
        bench.scan()
        self.assertEqual(bench.unit["Running"], 1)
        return bench

    def hold(self, bench, held):
        bench.tags[f"FRK_{APP.name}_HmiRequest"]["BoolValue"] = held
        return bench.request(mailbox.SET_HOLD_RUN)

    def test_a_style_the_unit_offers_is_taken(self):
        bench = Bench()
        for style in decl.RUN_STYLES:
            self.assertEqual(bench.request(mailbox.SET_RUN_STYLE, value=style), (1, 0))
            self.assertEqual(bench.unit["RunStyle"], style)

    def test_a_style_outside_e_runstyle_is_refused_by_tc3s_key(self):
        bench = Bench()
        bench.request(mailbox.SET_RUN_STYLE, value=SINGLE_STEP)
        for style in (-1, 3, 99):
            self.assertEqual(bench.request(mailbox.SET_RUN_STYLE, value=style),
                             (0, key(mailbox.RUN_STYLE_REFUSED_KEY)))
            self.assertEqual(bench.unit["RunStyle"], SINGLE_STEP)

    def test_step_needs_a_running_single_step(self):
        bench = Bench(mode=AUTO.mode_ordinal)
        refused = (0, key(mailbox.STEP_REFUSED_KEY))
        self.assertEqual(bench.request(mailbox.STEP_REQUEST), refused, "CONTINUOUS")
        bench.request(mailbox.SET_RUN_STYLE, value=SINGLE_STEP)
        self.assertEqual(bench.request(mailbox.STEP_REQUEST), refused, "not running")
        bench = self.running(SINGLE_STEP)
        self.assertEqual(bench.request(mailbox.STEP_REQUEST), (1, 0))
        self.assertEqual(bench.unit["StepPending"], 1)

    def test_a_hold_needs_a_running_hold_to_run_and_a_release_never_does(self):
        bench = Bench(mode=AUTO.mode_ordinal)
        refused = (0, key(mailbox.HOLD_RUN_REFUSED_KEY))
        self.assertEqual(self.hold(bench, 1), refused, "CONTINUOUS")
        self.assertEqual(self.hold(bench, 0), (1, 0), "a release is always taken")
        bench = self.running(HOLD_TO_RUN)
        self.assertEqual(self.hold(bench, 1), (1, 0))
        self.assertEqual(bench.unit["HoldRun"], 1)
        self.assertEqual(self.hold(bench, 0), (1, 0))
        self.assertEqual(bench.unit["HoldRun"], 0)

    def test_running_in_another_style_refuses_both(self):
        """Running is not enough: a Step belongs to SINGLE_STEP and a hold to
        HOLD_TO_RUN, and neither may pace a style that does not read it."""
        for style in decl.RUN_STYLES:
            with self.subTest(style):
                bench = self.running(style)
                step = bench.request(mailbox.STEP_REQUEST)
                hold = self.hold(bench, 1)
                self.assertEqual(step[0], int(style == SINGLE_STEP))
                self.assertEqual(hold[0], int(style == HOLD_TO_RUN))
                self.assertEqual((bench.unit["StepPending"], bench.unit["HoldRun"]),
                                 (int(style == SINGLE_STEP), int(style == HOLD_TO_RUN)))

    def test_leaving_a_style_forgets_what_it_held(self):
        bench = self.running(HOLD_TO_RUN)
        self.hold(bench, 1)
        bench.request(mailbox.SET_RUN_STYLE, value=CONTINUOUS)
        bench.request(mailbox.SET_RUN_STYLE, value=HOLD_TO_RUN)
        self.assertEqual(bench.unit["HoldRun"], 0, "a stale hold would run unheld")
        bench.request(mailbox.SET_RUN_STYLE, value=SINGLE_STEP)
        bench.request(mailbox.STEP_REQUEST)
        bench.request(mailbox.SET_RUN_STYLE, value=CONTINUOUS)
        self.assertEqual(bench.unit["StepPending"], 0)

    def test_the_gateway_routes_all_three(self):
        for kind in (mailbox.SET_RUN_STYLE, mailbox.STEP_REQUEST, mailbox.SET_HOLD_RUN):
            self.assertNotIn(kind, mailbox.refused_for(APP))


class ThePublishedStyle(unittest.TestCase):
    def test_runstyle_is_published_where_the_hmi_reads_it(self):
        bench = Bench()
        bench.request(mailbox.SET_RUN_STYLE, value=HOLD_TO_RUN)
        status = projection.unit_status(bench.unit, bench.tags[f"FRK_{APP.name}_Chart"])
        self.assertEqual(status["RunStyle"], HOLD_TO_RUN)

    def test_the_offered_styles_are_published_one_based(self):
        policy = projection.mode_policy(APP)
        self.assertEqual([policy[f"SupportedRunStylesPublished[{s + 1}]"]
                          for s in decl.RUN_STYLES], [True, True, True])
        plain = projection.mode_policy(dataclasses.replace(APP, run_styles=(CONTINUOUS,)))
        self.assertEqual([plain[f"SupportedRunStylesPublished[{s + 1}]"]
                          for s in decl.RUN_STYLES], [True, False, False])


if __name__ == "__main__":
    unittest.main()
