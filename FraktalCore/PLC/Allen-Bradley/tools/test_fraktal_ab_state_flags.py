"""TC3's derived state flags (Core §3.12) on the Allen-Bradley binding.

A state flag is TRUE RIGHT NOW: recomputed from the modules every scan, never
latched, published with the moment it last changed. TC3's press publishes two
on its Unit - at load position, and ready for a two-hand start - and AB
publishes the same two under the same keys, derived on the controller and
stamped by the controller's clock.
"""

import dataclasses
import re
import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_press_demo as demo
import fraktal_ab_st_model as st
from test_fraktal_ab_oee import pl_fraktal


APP = demo.application()
N = APP.name
FLAGS = gen.state_flags_tag(APP)
LOGIC = st.parse("\n".join(gen.state_flags_logic(APP)))
AT_LOAD, START_READY = 0, 1


class Station:
    """The flags' logic over every module's context and the clock."""

    def __init__(self):
        self.tags = {gen.ctx_tag_for(APP, m.name): st.structure(gen.module_members(m))
                     for m in APP.modules}
        self.tags.update({FLAGS: st.structure(gen.state_flags_members(APP)),
                          f"FRK_{N}_NowDate": 20261001, f"FRK_{N}_NowTime": 120000000})
        self.plc = st.Controller(self.tags)
        for name in ("Door", "PartSlide", "PressRam"):
            self.ctx(name).update(OutImm_Retracted=1, OutImm_Extended=0)
        self.ctx("TwoHand")["OutImm_Armed"] = 1
        self.ctx("PartPresentSensor").update(OutImm_Value=1, OutImm_Quality=1)
        self.ctx("AirPressureMonitor")["OutImm_PressureOk"] = 1

    def ctx(self, name):
        return self.tags[gen.ctx_tag_for(APP, name)]

    def scan(self, at=None):
        if at is not None:
            self.tags[f"FRK_{N}_NowTime"] = at
        self.plc.run(LOGIC)
        return self.tags[FLAGS]


class TheContract(unittest.TestCase):
    def test_the_bound_is_tc3s(self):
        self.assertEqual(decl.MAX_STATE_FLAGS, pl_fraktal("MAX_STATE_FLAGS"))

    def test_the_press_publishes_tc3s_two_flags_in_its_order(self):
        self.assertEqual([f.key for f in APP.state_flags],
                         ["project.state.pressAtLoadPosition",
                          "project.state.pressTwoHandStartReady"])

    def test_no_flag_expression_passes_the_studio_limit(self):
        """Studio v33 refuses a sixth operator of a kind in one expression."""
        for line in gen.state_flags_logic(APP):
            for op in (" AND ", " OR "):
                self.assertLessEqual(line.count(op), 5, line)


class AtLoadPosition(unittest.TestCase):
    def test_every_cylinder_retracted_and_none_extended(self):
        self.assertEqual(Station().scan()["Value"][AT_LOAD], 1)

    def test_any_cylinder_away_clears_it(self):
        for name in ("Door", "PartSlide", "PressRam"):
            for away in ({"OutImm_Retracted": 0}, {"OutImm_Extended": 1},
                         {"OutImm_Retracted": 0, "OutImm_Extended": 0}):
                with self.subTest(name=name, away=away):
                    s = Station()
                    s.ctx(name).update(away)
                    self.assertEqual(s.scan()["Value"][AT_LOAD], 0)

    def test_it_is_never_latched(self):
        """A jog off the position in MANUAL clears it, and back sets it."""
        s = Station()
        self.assertEqual(s.scan()["Value"][AT_LOAD], 1)
        s.ctx("PressRam").update(OutImm_Retracted=0)
        self.assertEqual(s.scan()["Value"][AT_LOAD], 0)
        s.ctx("PressRam").update(OutImm_Retracted=1)
        self.assertEqual(s.scan()["Value"][AT_LOAD], 1)


class ReadyForATwoHandStart(unittest.TestCase):
    def test_armed_part_and_air(self):
        self.assertEqual(Station().scan()["Value"][START_READY], 1)

    def test_each_condition_is_needed(self):
        for name, member in (("TwoHand", "OutImm_Armed"),
                             ("PartPresentSensor", "OutImm_Value"),
                             ("PartPresentSensor", "OutImm_Quality"),
                             ("AirPressureMonitor", "OutImm_PressureOk")):
            with self.subTest(member=f"{name}.{member}"):
                s = Station()
                s.ctx(name)[member] = 0
                self.assertEqual(s.scan()["Value"][START_READY], 0)


class Since(unittest.TestCase):
    def test_a_flag_false_from_the_start_is_stamped_too(self):
        """FALSE at the first scan is no change from the download's 0, so only
        the first-scan clause gives it a Since - else it would have none."""
        s = Station()
        s.ctx("TwoHand")["OutImm_Armed"] = 0
        flags = s.scan(at=120000000)
        self.assertEqual(flags["Value"][START_READY], 0)
        self.assertEqual((flags["SinceDate"][START_READY], flags["SinceTime"][START_READY]),
                         (20261001, 120000000))

    def test_stamped_at_first_and_on_each_change_only(self):
        s = Station()
        flags = s.scan(at=120000000)
        self.assertEqual((flags["SinceDate"][AT_LOAD], flags["SinceTime"][AT_LOAD]),
                         (20261001, 120000000), "the first scan stamps it")
        s.scan(at=120001000)
        self.assertEqual(flags["SinceTime"][AT_LOAD], 120000000, "unchanged, unstamped")
        s.ctx("Door")["OutImm_Retracted"] = 0
        s.scan(at=120002000)
        self.assertEqual(flags["SinceTime"][AT_LOAD], 120002000, "a change stamps it")
        self.assertEqual(flags["SinceTime"][START_READY], 120000000, "the other kept its own")


class TheDeclaration(unittest.TestCase):
    def flagged(self, *flags):
        return decl.validate(dataclasses.replace(APP, state_flags=flags))

    def test_an_unknown_module_is_refused(self):
        findings = self.flagged(decl.StateFlag("project.state.x", (
            decl.ModuleState("Nope", ("OutImm_Value",)),)))
        self.assertTrue(any("unknown module 'Nope'" in f for f in findings))

    def test_a_flag_reads_module_states_only(self):
        findings = self.flagged(decl.StateFlag("project.state.x", (
            decl.UnitState(("Running",)),)))
        self.assertTrue(any("derived from module states" in f for f in findings))

    def test_the_bound_and_duplicates(self):
        flag = APP.state_flags[0]
        self.assertTrue(any("declared twice" in f for f in self.flagged(flag, flag)))
        many = tuple(dataclasses.replace(flag, key=f"project.state.f{i}")
                     for i in range(decl.MAX_STATE_FLAGS + 1))
        self.assertTrue(any("at most 12" in f for f in self.flagged(*many)))


if __name__ == "__main__":
    unittest.main()
