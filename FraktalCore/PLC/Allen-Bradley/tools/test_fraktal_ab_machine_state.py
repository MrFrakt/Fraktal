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
import fraktal_ab_machine_state as ms
import fraktal_ab_press_demo as demo
from test_fraktal_ab_core_ordinals import core_enum


APP = demo.application()
AUTO = next(c for c in APP.chains if c.name == "AUTO")
STATE = ms.STATES
CLEAR = {"Blocking": 0}


def unit_values(**overrides):
    values = {m.name: m.initial for m in gen.unit_storage_members(APP)}
    values.update(overrides)
    return values


def state(unit, active=CLEAR, app=APP):
    return ms.classify(app, unit, bool(active.get("Blocking", 0)))


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
        self.assertEqual(ms.CHANGEOVER, core_enum("E_Mode")["CHANGEOVER"])
        self.assertEqual(ms.CHANGEOVER, demo.MODE_CHANGEOVER)

    def test_the_press_never_waits_on_the_line(self):
        """No step of either binding's press is an upstream or downstream
        wait, so it is never STARVED or BLOCKED on the bench."""
        classes = {s.time_class for c in APP.chains for s in c.steps}
        self.assertFalse(classes & {"WAIT_UPSTREAM", "WAIT_DOWNSTREAM"})

    def test_rework_is_a_counter_on_the_controller(self):
        self.assertIn("ReworkCount", {m.name for m in gen.unit_storage_members(APP)})


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
        self.assertEqual(ms.waits(app, at_wait), (True, False))


if __name__ == "__main__":
    unittest.main()
