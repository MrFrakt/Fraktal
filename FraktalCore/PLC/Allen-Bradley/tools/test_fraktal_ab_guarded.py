"""TC3's N180 on the Allen-Bradley binding: a close the operator can abandon.

TC3's AUTO N180 closes the door while the two-hand is held. Releasing a button
mid-close is the operator abandoning it, not a fault: TC3 drops the close,
raises PRESS_TWO_HAND_RELEASED as a §6.9(e) warning (LOW, once per visit, on
the Unit and on the step's §3.13 row), reopens the door (N185), slides the
part out (N190) and returns to the two-hand wait with the start latch
dropped. Completion wins if the door finished in the same scan.

AB declares that as a guarded command (`decl.GUARDED`), with N190's latch
drop as a completion mark, and the guard - like N100's latch and N220's dwell
- counts only while the station's RequireTwoHandStart policy asks for it.
These tests scan each rendition of the real chain: ST and the SFC action on
the ST model, the ladder on the ladder model.
"""

import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
from test_fraktal_ab_dwell import APP, AUTO, ORDER, LANGUAGES, Rendition


STATION = next(r for r in APP.records if r.station_cfg)
CLOSE = next(s for s in AUTO.steps if s.number == 180)
REOPEN = next(s for s in AUTO.steps if s.number == 185)
SLIDE_OUT = next(s for s in AUTO.steps if s.number == 190)
WARNING = demo.REASONS["TWO_HAND_RELEASED"]
ROW = ORDER.index(180)


def ctx(r, name):
    return r.plc.tags[gen.ctx_tag_for(APP, name)]


class ReleasingAbandonsTheClose(unittest.TestCase):
    def test_released_it_warns_and_takes_the_recovery_jump(self):
        for language in LANGUAGES:
            with self.subTest(language):
                r = Rendition(language, CLOSE, two_hand=0)
                self.assertFalse(r.scan(), "the entry scan only drops Execute")
                self.assertTrue(r.scan())
                self.assertEqual(r.went_to, REOPEN.number)
                self.assertEqual(ctx(r, "Door")["Execute"], 0, "the close is released")
                self.assertEqual(
                    (r.unit["ReportedReason"], r.unit["ReportedSource"],
                     r.unit["ReportedCount"]), (WARNING, 0, 1),
                    "one warning, from the Unit itself")
                self.assertEqual((r.chart["WarnReason"][ROW], r.chart["WarnSource"][ROW]),
                                 (WARNING, 0), "and on N180's row")
                self.assertEqual(r.unit["Error"], 0, "a warning, not a fault")
                self.assertEqual(r.chart["CondOk"][0], 0)

    def test_held_it_commands_the_close_and_completes(self):
        for language in LANGUAGES:
            with self.subTest(language):
                r = Rendition(language, CLOSE, two_hand=1)
                for _ in range(20):
                    self.assertFalse(r.scan())
                self.assertEqual(ctx(r, "Door")["Execute"], 1)
                self.assertEqual(ctx(r, "Door")["ParCmd_Command"], 1)    # EXTEND
                ctx(r, "Door")["Done"] = 1
                self.assertTrue(r.scan())
                self.assertEqual(r.went_to, CLOSE.on_advance)
                self.assertEqual(r.unit["ReportedCount"], 0)

    def test_completion_wins_in_the_same_scan(self):
        for language in LANGUAGES:
            with self.subTest(language):
                r = Rendition(language, CLOSE, two_hand=1)
                for _ in range(3):
                    r.scan()
                ctx(r, "Door")["Done"] = 1
                r.press(False)
                self.assertTrue(r.scan())
                self.assertEqual(r.went_to, CLOSE.on_advance)
                self.assertEqual(r.unit["ReportedCount"], 0, "nothing was abandoned")

    def test_without_the_policy_a_release_abandons_nothing(self):
        for language in LANGUAGES:
            with self.subTest(language):
                r = Rendition(language, CLOSE, two_hand=0)
                r.plc.tags[f"{STATION.name}Tag"]["RequireTwoHandStart"] = 0
                for _ in range(20):
                    self.assertFalse(r.scan())
                self.assertEqual(r.chart["CondOk"][0], 1)
                self.assertEqual(r.unit["ReportedCount"], 0)

    def test_every_rendition_abandons_the_same_way(self):
        def walk(language):
            r = Rendition(language, CLOSE, two_hand=1)
            trace = []
            for k in range(12):
                r.press(k < 5)
                left = r.scan()
                trace.append((ctx(r, "Door")["Execute"], r.unit["ReportedCount"],
                              r.chart["CondOk"][0], left, r.went_to))
                if left:
                    break
            return trace
        reference = walk(decl.ST)
        for language in LANGUAGES[1:]:
            with self.subTest(language):
                self.assertEqual(walk(language), reference)


class TheRecoveryReturnsToTheStart(unittest.TestCase):
    def test_the_door_reopens_then_the_slide_goes_out(self):
        for language in LANGUAGES:
            with self.subTest(language):
                r = Rendition(language, REOPEN)
                r.scan()
                r.scan()
                self.assertEqual((ctx(r, "Door")["Execute"],
                                  ctx(r, "Door")["ParCmd_Command"]), (1, 2))  # RETRACT
                ctx(r, "Door")["Done"] = 1
                self.assertTrue(r.scan())
                self.assertEqual(r.went_to, SLIDE_OUT.number)

    def test_the_slide_out_drops_the_start_latch_when_it_completes(self):
        """TC3's N190: the cycle cannot resume without a fresh press."""
        for language in LANGUAGES:
            with self.subTest(language):
                r = Rendition(language, SLIDE_OUT)
                r.unit["StartLatched"] = 1
                for _ in range(5):
                    r.scan()
                self.assertEqual(r.unit["StartLatched"], 1, "not before it completes")
                ctx(r, "PartSlide")["Done"] = 1
                self.assertTrue(r.scan())
                self.assertEqual(r.went_to, 100)
                self.assertEqual(r.unit["StartLatched"], 0)


class TheExpectedTimeIsPublished(unittest.TestCase):
    """TC3's ExpectedTime, on the current step and on each §3.13 row."""

    def test_the_current_step_carries_what_the_controller_times_it_by(self):
        unit = {"Mode": AUTO.mode_ordinal, "Step": 220, "Running": 1, "Error": 0,
                "StepExpectedMs": 450}
        self.assertEqual(projection.step_status(APP, unit)["CurrentStep/ExpectedTime"], 450)

    def test_a_row_carries_its_steps_expectation_from_the_live_recipe(self):
        import fraktal_ab_st_model as st
        chart = st.structure(gen.chart_members(APP))
        chart.update(RowEpoch=1, RowCount=3)
        for row, number in enumerate((170, 180, 220), start=1):
            index = ORDER.index(number)
            chart["RowEpochOf"][index], chart["RowOf"][index] = 1, row
        recipe = {APP.records[0].name: {"TransferSettleMs": 250, "PressDwellMs": 700}}
        unit = {"Mode": AUTO.mode_ordinal, "Step": 220}
        out = projection.sequence_status(APP, unit, chart, recipe)
        self.assertEqual([out[f"SequenceSteps[{i}]/ExpectedTime"] for i in (1, 2, 3)],
                         [250, 0, 700])
        self.assertEqual(projection.sequence_status(APP, unit, chart)
                         ["SequenceSteps[3]/ExpectedTime"], 0, "no recipe read, no claim")


if __name__ == "__main__":
    unittest.main()
