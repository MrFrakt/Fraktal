"""Core §6.9(b) on the Allen-Bradley binding: what the step is waiting for.

TC3 records each condition a step waits on with M_Await(Idx, Label, Ok): the
label says what it is, Ok says whether it holds, and the step writes both from
the same evaluation its transition uses. AB carries the label in the
declaration and the truth in `Chart.CondOk`, written by the step in every
rendition. These tests run the generated ST of the real AUTO chain on the ST
model, read the ladder rung, and hold the projection's join to the rule that
it must never label one step's evaluation with another step's names.
"""

import dataclasses
import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
import fraktal_ab_st_model as st
from test_fraktal_ab_digital_input import run_passive_modules


APP = demo.application()
N = APP.name
AUTO = next(c for c in APP.chains if c.name == "AUTO")
CHART, UNIT = f"FRK_{N}_Chart", f"FRK_{N}_Unit"
PART, AIR, TWO_HAND = (f"FRK_{N}_PartPresent", f"FRK_{N}_AirOk",
                       f"FRK_{N}_TwoHand")


def step(number, chain=AUTO):
    return next(s for s in chain.steps if s.number == number)


def controller():
    tags = {
        UNIT: st.structure(gen.unit_context_members(APP)),
        CHART: st.structure(gen.chart_members(APP)),
        **{f"{r.name}Tag": st.structure(r.members) for r in APP.records},
        f"FRK_{N}_ScanCount": 1,
    }
    for module in APP.modules:
        tags[gen.ctx_tag_for(APP, module.name)] = st.structure(
            gen.module_members(module))
    for tag in APP.sim_inputs:
        tags[tag] = 0
    return st.Controller(tags, routines={gen.step_mark_routine_name(APP): gen.step_mark_logic(APP)})


class TheStepWritesWhatItReads(unittest.TestCase):
    """The ST rendition of AUTO, run at N100."""

    def run_n100(self, part, air, two_hand, prev_step=-1):
        plc = controller()
        plc.tags.update({PART: part, AIR: air})
        # N100's third record is TC3's latched two-hand start, not the buttons
        plc.tags[UNIT].update(Step=100, PrevStep=prev_step, StartLatched=two_hand)
        run_passive_modules(APP, plc.tags)     # the sensor, fed from PART
        plc.run("\n".join(gen.chain_st_logic(APP, AUTO)))
        return plc.tags

    def test_each_record_is_its_own_condition_in_declared_order(self):
        tags = self.run_n100(part=1, air=0, two_hand=1)
        self.assertEqual(tags[CHART]["CondOk"][:3], [1, 0, 1])
        self.assertEqual(tags[CHART]["ActiveStepNumber"], 100)

    def test_the_step_does_not_advance_while_a_record_is_false(self):
        tags = self.run_n100(part=1, air=0, two_hand=1)
        self.assertEqual(tags[UNIT]["Step"], 100)
        self.assertNotEqual(tags[CHART]["StallReason"], 0)

    def test_all_records_true_is_exactly_when_it_advances(self):
        tags = self.run_n100(part=1, air=1, two_hand=1)
        self.assertEqual(tags[CHART]["CondOk"][:3], [1, 1, 1])
        self.assertEqual(tags[UNIT]["Step"], step(100).on_advance)

    def test_a_record_falls_when_its_condition_does(self):
        """Written every scan, not latched: a condition lost is shown lost."""
        plc = controller()
        plc.tags.update({PART: 1, AIR: 0, TWO_HAND: 0})
        plc.tags[UNIT].update(Step=100, PrevStep=-1)
        logic = st.parse("\n".join(gen.chain_st_logic(APP, AUTO)))
        run_passive_modules(APP, plc.tags)
        plc.run(logic)
        self.assertEqual(plc.tags[CHART]["CondOk"][0], 1)
        plc.tags[PART] = 0
        run_passive_modules(APP, plc.tags, scan=2)
        plc.run(logic)
        self.assertEqual(plc.tags[CHART]["CondOk"][0], 0)

    def test_a_guarded_command_records_its_guard(self):
        """TC3's N180 records twoHandHeldDuringDoorClose as its record 1."""
        plc = controller()
        plc.tags[TWO_HAND] = 0
        plc.tags[UNIT].update(Step=180, PrevStep=-1)
        run_passive_modules(APP, plc.tags)
        plc.run("\n".join(gen.chain_st_logic(APP, AUTO)))
        self.assertEqual(plc.tags[CHART]["CondOk"][0], 0)

    def test_a_policy_off_satisfies_its_condition(self):
        """RequireTwoHandStart cleared: the two-hand records hold whatever
        the buttons do, as TC3's `SafeActive OR NOT RequireTwoHandStart`."""
        station = next(r for r in APP.records if r.station_cfg)
        plc = controller()
        plc.tags[f"{station.name}Tag"]["RequireTwoHandStart"] = 0
        plc.tags[TWO_HAND] = 0
        plc.tags[UNIT].update(Step=180, PrevStep=-1)
        run_passive_modules(APP, plc.tags)
        plc.run("\n".join(gen.chain_st_logic(APP, AUTO)))
        self.assertEqual(plc.tags[CHART]["CondOk"][0], 1)


class EveryRenditionRecords(unittest.TestCase):
    def test_the_sfc_action_writes_the_same_records(self):
        names = gen.Names(APP, in_aoi=False)
        index = gen.ordered_steps(APP).index(100)
        plc = controller()
        plc.tags.update({PART: 0, AIR: 1})
        plc.tags[UNIT].update(Step=100, PrevStep=-1, StartLatched=1)
        run_passive_modules(APP, plc.tags)
        plc.run("\n".join(gen.sfc_action_logic(APP, AUTO, step(100), index, names)))
        self.assertEqual(plc.tags[CHART]["CondOk"][:3], [0, 1, 1])

    def test_the_ladder_rung_carries_one_leg_per_truth_value(self):
        names = gen.Names(APP, in_aoi=False)
        index = gen.ordered_steps(APP).index(100)
        rung = gen.ld_step_rung(APP, AUTO, step(100), index, names)
        for i, (cond, _) in enumerate(decl.step_conditions(step(100))):
            self.assertIn(f"{gen.ld_holds(cond, names)}MOV(1,{CHART}.CondOk[{i}])", rung)
            # a condition fails when ANY of its terms is zero: a parallel branch
            self.assertIn(f"{gen.ld_fails((cond,), names)}MOV(0,{CHART}.CondOk[{i}])",
                          rung)

    def test_a_policy_is_a_branch_around_its_condition(self):
        names = gen.Names(APP, in_aoi=False)
        station = next(r for r in APP.records if r.station_cfg)
        policy = f"{station.name}Tag.RequireTwoHandStart"
        latched = f"{UNIT}.StartLatched"
        cond = decl.step_conditions(step(100))[2][0]
        self.assertEqual(gen.ld_holds(cond, names), f"[NEQ({latched},0),EQU({policy},0)]")
        self.assertEqual(gen.ld_fails((cond,), names), f"NEQ({policy},0)EQU({latched},0)")
        self.assertEqual(gen.cond_st(cond, names),
                         f"((({latched} <> 0)) OR ({policy} = 0))")

    def test_a_step_without_conditions_writes_no_record(self):
        names = gen.Names(APP, in_aoi=False)
        index = gen.ordered_steps(APP).index(110)
        self.assertNotIn("CondOk", "\n".join(
            gen.sfc_action_logic(APP, AUTO, step(110), index, names)))
        self.assertNotIn("CondOk", gen.ld_step_rung(APP, AUTO, step(110), index, names))


class ThePublishedRecords(unittest.TestCase):
    def publish(self, step_no, active, cond_ok, running=1, error=0, mode=None):
        unit = {"Mode": AUTO.mode_ordinal if mode is None else mode,
                "Step": step_no, "Running": running, "Error": error}
        chart = {"ActiveStepNumber": active,
                 "CondOk": cond_ok + [0] * (decl.MAX_STEP_CONDS - len(cond_ok))}
        return projection.step_status(APP, unit, chart)

    def test_labels_are_the_declarations_and_ok_is_the_controllers(self):
        out = self.publish(100, 100, [1, 0, 1])
        self.assertEqual(out["CurrentStep/Conds[1]/Label"], "project.condition.partPresent")
        self.assertEqual(out["CurrentStep/Conds[2]/Label"], "project.condition.airPressureOk")
        self.assertEqual(out["CurrentStep/Conds[3]/Label"], "project.condition.twoHandStart")
        self.assertEqual([out[f"CurrentStep/Conds[{i}]/Ok"] for i in (1, 2, 3)],
                         [True, False, True])

    def test_the_scan_after_a_transition_names_nothing(self):
        """Unit.Step already says 180 while the chart still holds N100's view:
        publishing N180's label over N100's truth would be a lie."""
        out = self.publish(180, 100, [1, 1, 1])
        self.assertEqual(out["CurrentStep/Conds[1]/Label"], "")
        self.assertFalse(out["CurrentStep/Conds[1]/Ok"])

    def test_every_slot_is_always_published(self):
        for step_no in (100, 110, 999):
            out = self.publish(step_no, step_no, [])
            slots = {k for k in out if k.startswith("CurrentStep/Conds[")}
            self.assertEqual(len(slots), 2 * decl.MAX_STEP_CONDS)

    def test_an_unused_slot_is_never_ok(self):
        out = self.publish(100, 100, [1, 1, 1, 1, 1, 1, 1, 1])
        self.assertFalse(out["CurrentStep/Conds[4]/Ok"])

    def test_awaiting_label_is_tc3s_module_dot_command(self):
        self.assertEqual(self.publish(110, 110, [])["CurrentStep/AwaitingLabel"],
                         "PressRam.RETRACT")
        self.assertEqual(self.publish(100, 100, [])["CurrentStep/AwaitingLabel"], "")

    def test_time_class_is_the_core_ordinal(self):
        self.assertEqual(self.publish(100, 100, [])["CurrentStep/TimeClass"],
                         decl.TIME_CLASSES.index("WAIT_OPERATOR"))
        self.assertEqual(self.publish(110, 110, [])["CurrentStep/TimeClass"], 0)

    def test_starved_and_blocked_follow_fb_unitbase(self):
        """BUSY in a step classed WAIT_UPSTREAM / WAIT_DOWNSTREAM, and only then."""
        upstream = dataclasses.replace(step(100), time_class="WAIT_UPSTREAM")
        chain = dataclasses.replace(AUTO, steps=tuple(
            upstream if s.number == 100 else s for s in AUTO.steps))
        app = dataclasses.replace(APP, chains=tuple(
            chain if c.name == "AUTO" else c for c in APP.chains))
        unit = {"Mode": AUTO.mode_ordinal, "Step": 100, "Running": 1, "Error": 0}
        out = projection.step_status(app, unit, None)
        self.assertTrue(out["Starved"])
        self.assertFalse(out["Blocked"])
        self.assertFalse(projection.step_status(app, dict(unit, Error=1), None)["Starved"])
        self.assertFalse(projection.step_status(app, dict(unit, Running=0), None)["Starved"])
        self.assertFalse(self.publish(100, 100, [])["Starved"])


class DeclarationRules(unittest.TestCase):
    def findings(self, **changes):
        bad = dataclasses.replace(step(100), **changes)
        chain = dataclasses.replace(AUTO, steps=tuple(
            bad if s.number == 100 else s for s in AUTO.steps))
        return decl._validate_chain(APP, chain)

    def test_the_press_is_clean(self):
        self.assertEqual(decl._validate_chain(APP, AUTO), [])

    def test_a_condition_without_a_label_is_refused(self):
        found = self.findings(condition_labels=step(100).condition_labels[:2])
        self.assertTrue(any("label" in f for f in found), found)

    def test_a_label_must_be_a_key(self):
        found = self.findings(condition_labels=("Part present", "b.c", "d.e"))
        self.assertTrue(any("not a localization key" in f for f in found), found)

    def test_a_guard_needs_a_label(self):
        bad = dataclasses.replace(step(180), condition_labels=())
        chain = dataclasses.replace(AUTO, steps=tuple(
            bad if s.number == 180 else s for s in AUTO.steps))
        found = decl._validate_chain(APP, chain)
        self.assertTrue(any("each needs one" in f for f in found), found)

    def test_a_policy_is_not_readable_inside_an_aoi(self):
        """A policy lives in the StationCfg tag; an AOI cannot reach it."""
        with self.assertRaises(decl.DeclarationError):
            gen.cond_st(decl.step_conditions(step(180))[0][0],
                        gen.Names(APP, in_aoi=True))

    def test_more_than_the_core_bound_is_refused(self):
        many = (PART,) * (decl.MAX_STEP_CONDS + 1)
        found = self.findings(conditions=many,
                              condition_labels=("project.condition.x",) * len(many))
        self.assertTrue(any("more than" in f for f in found), found)

    def test_an_unknown_time_class_is_refused(self):
        found = self.findings(time_class="WAITING")
        self.assertTrue(any("E_TimeClass" in f for f in found), found)


if __name__ == "__main__":
    unittest.main()
