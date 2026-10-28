"""TC3's MachineState (Core §8.11.3) and ReworkCount (§8.11.2) on AB.

The machine state is one of a fixed set, chosen every scan in TC3's priority:
a fault (or a blocking alarm) first, then the planned states - CHANGEOVER mode
- then line attribution (blocked, starved), then producing, stopped or idle.
AB derives it in the projection from what the Unit already publishes, the way
it derives Starved and Blocked; nothing on the controller is latched for it.
"""

import dataclasses
import unittest

import fraktal_ab_generate as gen
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
from test_fraktal_ab_core_ordinals import core_enum
from test_fraktal_ab_projection import alarm_values, build, unit_values


APP = demo.application()
AUTO = next(c for c in APP.chains if c.name == "AUTO")
STATE = projection.MACHINE_STATES
CLEAR = {"Blocking": 0}


def state(unit, active=CLEAR, app=APP):
    return projection.machine_state(app, unit, active)["MachineState"]


def unit(**overrides):
    return unit_values(**{"Mode": demo.MODE_AUTO, "Step": 110, **overrides})


def waiting(time_class):
    """The press with N100 classed as an external wait, as a line station's
    part-await would be. TC3's press declares none, and neither does AB's."""
    chain = dataclasses.replace(AUTO, steps=tuple(
        dataclasses.replace(s, time_class=time_class) if s.number == 100 else s
        for s in AUTO.steps))
    return dataclasses.replace(APP, chains=tuple(
        chain if c.name == "AUTO" else c for c in APP.chains))


class TheContract(unittest.TestCase):
    def test_the_states_are_tc3s(self):
        self.assertEqual(STATE, core_enum("E_MachineState"))

    def test_changeover_is_the_core_mode(self):
        self.assertEqual(projection.MODE_CHANGEOVER, core_enum("E_Mode")["CHANGEOVER"])
        self.assertEqual(projection.MODE_CHANGEOVER, demo.MODE_CHANGEOVER)

    def test_the_press_never_waits_on_the_line(self):
        """No step of either binding's press is an upstream or downstream
        wait, so it is never STARVED or BLOCKED on the bench."""
        classes = {s.time_class for c in APP.chains for s in c.steps}
        self.assertFalse(classes & {"WAIT_UPSTREAM", "WAIT_DOWNSTREAM"})


class TheClassification(unittest.TestCase):
    def test_idle(self):
        self.assertEqual(state(unit()), STATE["IDLE"])

    def test_producing_while_running(self):
        self.assertEqual(state(unit(Running=1)), STATE["PRODUCING"])

    def test_a_fault_is_down_whatever_else_holds(self):
        for extra in ({}, {"Running": 1}, {"Mode": demo.MODE_CHANGEOVER},
                      {"Aborted": 1}):
            with self.subTest(extra):
                self.assertEqual(state(unit(Error=1, **extra)), STATE["DOWN"])

    def test_a_blocking_alarm_is_down_even_while_running(self):
        """TC3's order here, which is not its OEE accounting's: there BUSY is
        tested first, so the same scan is run time and DOWN."""
        self.assertEqual(state(unit(Running=1), {"Blocking": 1}), STATE["DOWN"])
        self.assertEqual(state(unit(), {"Blocking": 1}), STATE["DOWN"])

    def test_changeover_mode_is_changeover_running_or_not(self):
        for extra in ({}, {"Running": 1}, {"Aborted": 1}):
            with self.subTest(extra):
                self.assertEqual(state(unit_values(Mode=demo.MODE_CHANGEOVER, **extra)),
                                 STATE["CHANGEOVER"])

    def test_an_aborted_unit_is_stopped_until_reset(self):
        """TC3's STOPPED is `_stopReq OR ABORTED`; its graceful stop holds
        `_stopReq` only while BUSY, so it is ABORTED - AB's STOP."""
        self.assertEqual(state(unit(Aborted=1)), STATE["STOPPED"])

    def test_producing_before_stopped(self):
        """TC3's order: a Stop still pending while BUSY is PRODUCING. AB never
        holds Running and Aborted together (the abort drops Running and the
        run latch refuses while aborted), so this pins the order, not a state
        the bench can reach."""
        self.assertEqual(state(unit(Running=1, Aborted=1)), STATE["PRODUCING"])

    def test_starved_and_blocked_before_producing(self):
        for time_class, expected in (("WAIT_UPSTREAM", "STARVED"),
                                     ("WAIT_DOWNSTREAM", "BLOCKED")):
            with self.subTest(time_class):
                app = waiting(time_class)
                at_wait = unit_values(Mode=demo.MODE_AUTO, Step=100, Running=1)
                self.assertEqual(state(at_wait, app=app), STATE[expected])
                self.assertEqual(state(dict(at_wait, Running=0), app=app), STATE["IDLE"])

    def test_one_derivation_of_starved_and_blocked(self):
        """MachineState and the published Starved/Blocked agree, because
        they are the same function."""
        app = waiting("WAIT_UPSTREAM")
        at_wait = unit_values(Mode=demo.MODE_AUTO, Step=100, Running=1)
        published = projection.step_status(app, at_wait, None)
        self.assertEqual((published["Starved"], published["Blocked"]),
                         projection.wait_attribution(app, at_wait))

    def test_nothing_without_the_alarm_log(self):
        self.assertEqual(projection.machine_state(APP, unit(), None), {})


class ThePublishedValues(unittest.TestCase):
    def test_machine_state_and_rework_count_where_the_hmi_reads_them(self):
        out = build(unit=unit(Running=1, ReworkCount=4),
                    alarm_state=alarm_values())["values"]
        self.assertEqual(out[f"{APP.name}/MachineState"], STATE["PRODUCING"])
        self.assertEqual(out[f"{APP.name}/ReworkCount"], 4)

    def test_rework_is_a_counter_on_the_controller(self):
        self.assertIn("ReworkCount", {m.name for m in gen.unit_context_members(APP)})


if __name__ == "__main__":
    unittest.main()
