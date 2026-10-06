"""The third library type: TC3's FB_TwoHandStartCM, and the press's use of it.

A start EDGE from a certified two-hand result, not a level: it arms only when
both buttons are released, and a SafeActive rising edge while armed is one
StartPulse. TC3's press turns that pulse into two things, and so does this:

* a start from ready in AUTO, through the same rule an operator START uses;
* `StartLatched`, set only when the part and air are already present - a
  press made before the part was loaded never starts the stroke when the part
  arrives - which N100 waits on, and which cycle end, abort, reset and a mode
  change clear.

N180 holds on the module's SafeActive. The whole generated Unit AOI is run on
the ST model here, so the latch and its clears are tested where they live.
"""

import dataclasses
import unittest

import fraktal_ab_generate as gen
import fraktal_ab_library as library
import fraktal_ab_mailbox as mailbox
import fraktal_ab_press_demo as demo
import fraktal_ab_st_model as st
from test_fraktal_ab_digital_input import run_passive_modules


APP = demo.application()
N = APP.name
TWO_HAND = next(m for m in APP.modules if m.name == "TwoHand")
AUTO_MODE, MANUAL_MODE = demo.MODE_AUTO, demo.MODE_MANUAL
REFUSED = library.TWO_HAND.reasons["UNSUPPORTED_COMMAND"]


class Buttons:
    """The type's AOI body against one context."""

    def __init__(self, **ctx):
        self.ctx = st.structure(gen.module_context_members(library.TWO_HAND))
        self.ctx.update(RawHealthy=1, **ctx)
        self.plc = st.Controller({"Ctx": self.ctx, "Scan": 0})
        self.logic = st.parse("\n".join(gen.type_logic(library.TWO_HAND)))

    def scan(self, pressed=None, **raw):
        if pressed is not None:
            raw.update(RawLeft=pressed, RawRight=pressed, RawSafe=pressed)
        self.ctx.update(raw)
        self.plc.tags["Scan"] += 1
        self.plc.run(self.logic)
        return self.ctx["OutImm_StartPulse"]


class TheType(unittest.TestCase):
    def test_a_release_then_a_press_is_one_pulse(self):
        b = Buttons()
        self.assertEqual(b.scan(pressed=0), 0)
        self.assertEqual(b.ctx["OutImm_Armed"], 1)
        self.assertEqual(b.scan(pressed=1), 1)
        self.assertEqual(b.ctx["OutCmd_StartAccepted"], 1)
        self.assertEqual(b.scan(pressed=1), 0)     # one scan, not a level
        self.assertEqual(b.ctx["OutImm_SafeActive"], 1)

    def test_holding_the_buttons_never_starts_again(self):
        """Anti-repeat: no second start without a release (TC3's default)."""
        b = Buttons()
        b.scan(pressed=0)
        b.scan(pressed=1)
        pulses = sum(b.scan(pressed=p) for p in (1, 1, 1))
        self.assertEqual(pulses, 0)
        self.assertEqual(b.ctx["OutImm_Armed"], 0)

    def test_pressed_since_power_up_is_not_a_start(self):
        b = Buttons()
        self.assertEqual(b.scan(pressed=1), 0)
        self.assertEqual(b.ctx["OutImm_Armed"], 0)

    def test_without_the_release_rule_every_edge_starts(self):
        b = Buttons(Par_RequireRelease=0)
        b.scan(pressed=1)
        b.scan(RawSafe=0)          # the result drops, buttons still held
        self.assertEqual(b.scan(RawSafe=1), 1)
        # still an EDGE: holding it is one start, not one per scan
        self.assertEqual(b.scan(RawSafe=1), 0)

    def test_an_unhealthy_bus_is_never_safe_and_disarms(self):
        b = Buttons()
        b.scan(pressed=0)
        self.assertEqual(b.scan(pressed=1, RawHealthy=0), 0)
        self.assertEqual((b.ctx["OutImm_SafeActive"], b.ctx["OutImm_Armed"]), (0, 0))

    def test_a_command_is_refused(self):
        b = Buttons()
        b.scan(Execute=1)
        self.assertEqual((b.ctx["Error"], b.ctx["ErrorID"]), (1, REFUSED))


def aoi_scope():
    """The Unit AOI's parameters, bound to fresh contexts: Ctx, Chart, Cfg,
    Ctx<Module>, Scan and In<sim>, as unit_parameters declares them."""
    tags = {
        "Ctx": st.structure(gen.unit_context_members(APP)),
        "Chart": st.structure(gen.chart_members(APP)),
        "Cfg": st.structure(APP.records[0].members),
        "Scan": 1,
    }
    for module in APP.modules:
        ctx = st.structure(gen.module_members(module))
        ctx["ModuleScan"] = 1
        tags[gen._module_ref(APP, module.name)] = ctx
    for tag in APP.sim_inputs:
        tags[gen.sim_param(APP, tag)] = 1
    return tags


class TheUnitLatch(unittest.TestCase):
    """The generated Unit AOI, whole."""

    def unit(self, **ctx):
        tags = aoi_scope()
        state = dict(Mode=AUTO_MODE, ModeRequest=AUTO_MODE, RunRequest=1,
                     Running=1, Step=100, PrevStep=100)
        state.update(ctx)
        tags["Ctx"].update(state)
        return tags

    def scan_unit(self, tags, pulse=0, part=1, air=1):
        tags["CtxTwoHand"]["OutImm_StartPulse"] = pulse
        tags["CtxPartPresentSensor"].update(OutImm_Value=part, OutImm_Quality=1)
        tags["CtxAirPressureMonitor"]["OutImm_PressureOk"] = air
        st.Controller(tags).run("\n".join(gen.unit_logic(APP)))
        return tags["Ctx"]

    def test_a_pulse_with_part_and_air_latches_and_stays_latched(self):
        """N100 advancing on the latch is the chain's (AUTO runs in the
        rendition routines, not in this AOI): test_fraktal_ab_step_conditions."""
        tags = self.unit()
        self.assertEqual(self.scan_unit(tags, pulse=1)["StartLatched"], 1)
        self.assertEqual(self.scan_unit(tags)["StartLatched"], 1)

    def test_a_press_before_the_part_never_starts_the_stroke(self):
        """TC3: the latch counts only when the part and air are there."""
        tags = self.unit()
        ctx = self.scan_unit(tags, pulse=1, part=0)
        self.assertEqual(ctx["StartLatched"], 0)
        ctx = self.scan_unit(tags, part=1)           # the part arrives afterwards
        self.assertEqual((ctx["StartLatched"], ctx["Step"]), (0, 100))

    def test_a_pulse_in_another_mode_does_not_latch(self):
        tags = self.unit(Mode=MANUAL_MODE, ModeRequest=MANUAL_MODE)
        self.assertEqual(self.scan_unit(tags, pulse=1)["StartLatched"], 0)

    def test_reset_abort_and_a_mode_change_each_clear_it(self):
        for request in ({"ResetRequest": 1}, {"AbortRequest": 1},
                        {"ModeRequest": MANUAL_MODE}):
            tags = self.unit(StartLatched=1, **request)
            self.assertEqual(self.scan_unit(tags)["StartLatched"], 0, request)

    def test_the_cycle_end_clears_it(self):
        auto = next(c for c in APP.chains if c.name == "AUTO")
        end = next(s for s in auto.steps if s.number == 999)
        self.assertIn("Ctx.StartLatched := 0", end.marks)


class ThePhysicalStart(unittest.TestCase):
    def routine_fragment(self):
        # The start rule is the release report the routine computes just
        # before it (Core 7.8), so the fragment is both, in routine order.
        return "\n".join(gen.start_release_logic(APP) + gen.physical_start_logic(APP))

    def start(self, pulse, mode=AUTO_MODE, running=0, blocking=0):
        unit = st.structure(gen.unit_context_members(APP))
        unit.update(Mode=mode, Running=running)
        tags = {
            f"FRK_{N}_CtxTwoHand": {"OutImm_StartPulse": pulse},
            f"FRK_{N}_CtxAirPressureMonitor": {"OutImm_PressureOk": 1},
            f"FRK_{N}_Unit": unit,
            gen.alarm_active_tag(APP): {"Blocking": blocking},
            gen.start_release_tag(APP): st.structure(gen.release_report_members()),
            f"FRK_{N}_RunRequest": 0,
        }
        plc = st.Controller(tags)
        from test_fraktal_ab_access import add_access
        add_access(plc, APP)
        plc.run(self.routine_fragment())
        return tags[f"FRK_{N}_RunRequest"]

    def test_a_pulse_in_auto_starts_from_ready(self):
        self.assertEqual(self.start(pulse=1), 1)

    def test_it_obeys_the_start_rule_an_operator_start_obeys(self):
        self.assertEqual(self.start(pulse=1, blocking=1), 0)
        self.assertIn(f"IF NOT {gen.start_predicate(APP)} THEN",
                      "\n".join(mailbox.handler_logic(APP)))
        self.assertIn(gen.start_predicate(APP), self.routine_fragment())

    def test_not_in_another_mode_and_not_while_running(self):
        self.assertEqual(self.start(pulse=1, mode=MANUAL_MODE), 0)
        self.assertEqual(self.start(pulse=0), 0)

    def test_it_runs_after_the_modules_and_before_the_unit(self):
        routine = list(gen.routine_logic(APP))
        start = next(i for i, l in enumerate(routine) if "A physical start" in l)
        two_hand_call = next(i for i, l in enumerate(routine)
                             if l.startswith(f"{gen.type_aoi_name(library.TWO_HAND)}("))
        unit_call = next(i for i, l in enumerate(routine)
                         if l.startswith(f"{gen.unit_aoi_name(APP)}("))
        self.assertLess(two_hand_call, start)
        self.assertLess(start, unit_call)


class N180IsGuardedByTheCertifiedResult(unittest.TestCase):
    def test_every_rendition_reads_safe_active(self):
        auto = next(c for c in APP.chains if c.name == "AUTO")
        n180 = next(s for s in auto.steps if s.number == 180)
        names = gen.Names(APP, in_aoi=False)
        index = gen.ordered_steps(APP).index(180)
        expected = f"{gen.ctx_tag_for(APP, 'TwoHand')}.OutImm_SafeActive"
        for text in ("\n".join(gen.chain_st_logic(APP, auto)),
                     gen.sfc_condition(APP, n180, "J", names),
                     "\n".join(gen.sfc_action_logic(APP, auto, n180, index, names)),
                     gen.ld_step_rung(APP, auto, n180, index, names)):
            self.assertIn(expected, text)

    def test_its_buttons_are_bound_to_their_channels(self):
        roles = {c.name: (c.module_path, c.role) for io in APP.io_modules
                 for c in io.channels if c.module_path == "TwoHand"}
        self.assertEqual(roles, {"_101S101": ("TwoHand", "right"),
                                 "_101S102": ("TwoHand", "left")})


if __name__ == "__main__":
    unittest.main()
