"""TC3's cycle-time profile (Core §8.11.4(b)/(f)) on the Allen-Bradley binding.

Every step a chain runs is timed when it closes; the finish marker closes the
cycle, which is published as the last cycle's waterfall and pushed into a
60-cycle trend; every step keeps Count/Last/Minimum/Maximum/Avg, Avg being TC3's
integer running mean. Time is split by E_TimeClass, so WORK time - the real
cycle time - is published beside the total.

AB feeds the profile from ONE observer at the end of the routine, for every
rendition, so the tests that matter run whole AUTO cycles in ST, SFC and LD and
require the same waterfall from each.
"""

import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_projection as projection
import fraktal_ab_st_model as st
from test_fraktal_ab_oee import pl_fraktal
from test_fraktal_ab_projection import profiler_values
from test_fraktal_ab_rendition_cycle import APP, AUTO, Press, UNIT, CHART, SCAN


PROF = gen.profiler_tag(APP)
CFG = f"{APP.records[0].name}Tag"
PERIOD = APP.task_period_ms
ORDER = gen.ordered_steps(APP)
OBSERVE = st.parse("\n".join(gen.profiler_logic(APP)))
CLASS = {name: i for i, name in enumerate(decl.TIME_CLASSES)}


class Profiled(Press):
    """The press, with the profile's observer after the chain each scan."""

    def __init__(self, language):
        super().__init__(language)
        self.plc.tags[PROF] = st.structure(gen.profiler_members(APP))

    @property
    def prof(self):
        return self.plc.tags[PROF]

    def scan(self):
        super().scan()
        self.plc.run(OBSERVE)

    def again(self):
        """A fresh two-hand start for the next cycle (N999 drops the latch)."""
        self.plc.tags[UNIT]["StartLatched"] = 1
        return self.one_cycle()


def last_waterfall(prof):
    base = (1 - prof["CurBuf"]) * gen.PROFILE_STEPS
    return [(prof["WfStepNo"][base + i], prof["WfDurMs"][base + i])
            for i in range(prof["LastN"])]


class Station:
    """The observer alone, over the tags it reads, driven step by step."""

    def __init__(self):
        self.tags = {UNIT: st.structure(gen.unit_context_members(APP)),
                     CHART: st.structure(gen.chart_members(APP)),
                     PROF: st.structure(gen.profiler_members(APP)),
                     CFG: st.structure(APP.records[0].members),
                     SCAN: 0}
        self.plc = st.Controller(self.tags)
        self.tags[UNIT].update(Running=1, Mode=AUTO.mode_ordinal)

    @property
    def prof(self):
        return self.tags[PROF]

    def scan(self, count=1):
        for _ in range(count):
            self.tags[SCAN] += 1
            self.plc.run(OBSERVE)

    def step_to(self, number, scans, finish=False, expected=0):
        """The chain enters `number` and runs it for `scans` scans, writing on
        entry what every rendition's step writes: StepScan, the chart's active
        step and its row - and a finish step its CycleCount mark."""
        unit, chart = self.tags[UNIT], self.tags[CHART]
        self.tags[SCAN] += 1
        unit.update(Step=number, StepScan=self.tags[SCAN], StepExpectedMs=expected)
        chart.update(ActiveStepNumber=number, StepCursor=ORDER.index(number))
        if finish:
            unit["CycleCount"] += 1
        self.plc.run(OBSERVE)
        self.scan(scans - 1)


class TheContract(unittest.TestCase):
    def test_the_bounds_are_tc3s(self):
        self.assertEqual(gen.PROFILE_STEPS, pl_fraktal("MAX_PROFILE_STEPS"))
        self.assertEqual(gen.CYCLE_HISTORY, pl_fraktal("MAX_CYCLE_HISTORY"))

    def test_every_chart_row_has_a_statistics_row(self):
        self.assertLessEqual(len(ORDER), APP.chart_steps)
        self.assertLessEqual(APP.chart_steps, gen.PROFILE_STEPS)


class OneObserverForEveryRendition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = {}
        for language in AUTO.renditions:
            press = Profiled(language)
            first = press.one_cycle()
            cls.runs[language] = (press, first, dict(press.prof,
                                                     waterfall=last_waterfall(press.prof)))

    def test_the_waterfall_is_the_steps_the_chain_ran(self):
        """From N100, where the press was started, to the finish step: a step
        entered and left in one scan (N100 with the start latched, N999) is
        recorded like any other."""
        for language, (press, cycle, prof) in self.runs.items():
            with self.subTest(language):
                self.assertEqual(prof["LastCycleNo"], 1)
                self.assertEqual([n for n, _ in prof["waterfall"]],
                                 [100] + cycle["steps"][:-1])

    def test_every_rendition_profiles_the_same_cycle(self):
        reference = self.runs[decl.ST][2]
        for language in AUTO.renditions[1:]:
            with self.subTest(language):
                prof = self.runs[language][2]
                self.assertEqual(prof["waterfall"], reference["waterfall"])
                self.assertEqual((prof["LastTotal"], prof["LastWork"]),
                                 (reference["LastTotal"], reference["LastWork"]))

    def test_the_total_is_its_steps_and_the_work_is_the_total_less_its_waits(self):
        for language, (press, _, prof) in self.runs.items():
            with self.subTest(language):
                durations = dict(prof["waterfall"])
                self.assertEqual(sum(d for _, d in prof["waterfall"]), prof["LastTotal"])
                self.assertEqual(prof["LastCycleTime"], prof["LastTotal"])
                self.assertEqual(prof["LastTotal"] - prof["LastWork"], durations[100],
                                 "N100, TC3's operator wait, is the only wait")
                self.assertTrue(all(d % PERIOD == 0 and d > 0 for _, d in prof["waterfall"]))

    def test_the_trend_holds_the_cycle_split_by_class(self):
        prof = self.runs[decl.ST][2]
        classes = len(decl.TIME_CLASSES)
        self.assertEqual((prof["HistoryHead"], prof["HisCycleNo"][0], prof["HisTotal"][0],
                          prof["HisWork"][0]),
                         (1, 1, prof["LastTotal"], prof["LastWork"]))
        split = prof["HisByClass"][:classes]
        self.assertEqual(sum(split), prof["LastTotal"])
        self.assertEqual(split[CLASS["WAIT_OPERATOR"]], dict(prof["waterfall"])[100])

    def test_each_step_counted_once_with_its_duration(self):
        prof = self.runs[decl.ST][2]
        for number, duration in prof["waterfall"]:
            row = ORDER.index(number)
            with self.subTest(number):
                self.assertEqual((prof["StatCount"][row], prof["StatLast"][row],
                                  prof["StatMin"][row], prof["StatMax"][row],
                                  prof["StatAvg"][row]),
                                 (1, duration, duration, duration, duration))


class TheSecondCycle(unittest.TestCase):
    def test_last_cycle_is_the_newest_and_the_stats_accumulate(self):
        press = Profiled(decl.ST)
        press.one_cycle()
        first = last_waterfall(press.prof)
        press.again()
        prof = press.prof
        self.assertEqual((prof["LastCycleNo"], prof["HistoryHead"]), (2, 2))
        second = last_waterfall(prof)
        self.assertEqual((first[0][0], second[0][0]), (100, 100),
                         "each cycle starts at the start step")
        self.assertEqual((first[-1][0], second[-1][0]), (999, 999),
                         "and ends at the finish step")
        row = ORDER.index(110)
        self.assertEqual(prof["StatCount"][row], 2)
        self.assertEqual(prof["MinCycleTime"], min(prof["HisTotal"][0], prof["HisTotal"][1]))
        classes = len(decl.TIME_CLASSES)
        for slot in (0, 1):
            with self.subTest(cycle=slot + 1):
                self.assertEqual(sum(prof["HisByClass"][slot * classes:(slot + 1) * classes]),
                                 prof["HisTotal"][slot], "each cycle's own split")


class TheArithmetic(unittest.TestCase):
    def test_tc3s_running_mean_in_integers(self):
        """avg += (d - avg) / count, truncating toward zero, like TC3."""
        s = Station()
        durations = [7, 3, 11, 2]          # scans
        expected, count = 0, 0
        s.step_to(110, 1)
        for scans in durations:
            s.step_to(130, scans)
            s.step_to(110, 1)
            count += 1
            d = scans * PERIOD
            delta = d - expected
            expected += int(delta / count)
        row = ORDER.index(130)
        self.assertEqual(s.prof["StatAvg"][row], expected)
        self.assertEqual((s.prof["StatMin"][row], s.prof["StatMax"][row]),
                         (2 * PERIOD, 11 * PERIOD))

    def test_expected_is_recorded_as_the_step_opens(self):
        s = Station()
        s.step_to(170, 3, expected=200)
        s.step_to(180, 2, expected=0)
        s.step_to(999, 1, finish=True)
        base = (1 - s.prof["CurBuf"]) * gen.PROFILE_STEPS
        self.assertEqual(s.prof["WfExpMs"][base:base + 2], [200, 0])

    def test_a_cycle_longer_than_the_waterfall_is_truncated_not_lost(self):
        s = Station()
        for i in range(gen.PROFILE_STEPS + 3):
            s.step_to((110, 130)[i % 2], 1)
        s.step_to(999, 1, finish=True)
        p = s.prof
        self.assertEqual((p["LastN"], p["LastTrunc"]), (gen.PROFILE_STEPS, 1))
        self.assertEqual(p["LastTotal"], (gen.PROFILE_STEPS + 4) * PERIOD,
                         "the total still counts every step")

    def test_the_same_step_entered_again_is_a_new_visit(self):
        """The entry record, not the step number, says a step began: TC3's
        StepChanged is called on every entry."""
        s = Station()
        s.step_to(110, 2)
        s.step_to(110, 3)
        s.step_to(999, 1, finish=True)
        base = (1 - s.prof["CurBuf"]) * gen.PROFILE_STEPS
        self.assertEqual(s.prof["WfStepNo"][base:base + 3], [110, 110, 999])
        self.assertEqual(s.prof["StatCount"][ORDER.index(110)], 2)

    def test_a_duration_saturates_rather_than_wraps(self):
        s = Station()
        s.step_to(110, 1)
        s.prof["OpenMs"] = gen.PROFILE_SATURATE_MS
        s.scan(5)
        self.assertEqual(s.prof["OpenMs"], gen.PROFILE_SATURATE_MS)

    def test_the_trend_wraps(self):
        s = Station()
        s.prof["HistoryHead"] = gen.CYCLE_HISTORY
        s.step_to(110, 1)
        s.step_to(999, 1, finish=True)
        self.assertEqual(s.prof["HistoryHead"], 1)


class AStopAbandonsTheCycle(unittest.TestCase):
    def test_a_cycle_stood_down_is_never_published(self):
        """TC3's CycleAbandon, applied to a stop, a fault, an abort or a mode
        change alike: the fragment is not a production cycle."""
        s = Station()
        s.step_to(110, 4)
        s.step_to(130, 4)
        s.tags[UNIT]["Running"] = 0
        s.scan()
        self.assertEqual((s.prof["Open"], s.prof["CycleOpen"]), (0, 0))
        s.tags[UNIT]["Running"] = 1
        s.step_to(100, 1)
        self.assertEqual(s.prof["LastCycleNo"], 0, "nothing published")
        self.assertEqual(s.prof["StatCount"][ORDER.index(110)], 1,
                         "a step that closed before the stop still counts")
        self.assertEqual(s.prof["StatCount"][ORDER.index(130)], 0,
                         "the step it stopped in does not")


class ThePublishedProfile(unittest.TestCase):
    def test_where_the_hmi_reads_it(self):
        press = Profiled(decl.ST)
        press.one_cycle()
        out = projection.profiler_status(APP, press.prof)
        prof = press.prof
        self.assertEqual(out["Profiler/LastCycle/CycleNo"], 1)
        self.assertEqual(out["Profiler/LastCycle/NSteps"], prof["LastN"])
        self.assertEqual(out["Profiler/LastCycle/WaitTime"],
                         prof["LastTotal"] - prof["LastWork"])
        self.assertEqual(out["Profiler/LastCycle/Steps[1]/StepNo"], 100)
        self.assertEqual(out["Profiler/LastCycle/Steps[1]/StepName"],
                         "project.step.awaitTwoHandStart")
        self.assertEqual(out["Profiler/LastCycle/Steps[1]/TimeClass"], CLASS["WAIT_OPERATOR"])
        row = ORDER.index(110) + 1
        self.assertEqual((out[f"Profiler/StepStats[{row}]/Id"],
                          out[f"Profiler/StepStats[{row}]/Count"]), (110, 1))
        self.assertEqual(out["Profiler/HistoryHead"], 1)
        self.assertEqual(out["Profiler/History[1]/ByClass[3]"],
                         out["Profiler/LastCycle/WaitTime"])

    def test_the_path_set_never_moves_with_a_cycle(self):
        empty = projection.profiler_status(APP, profiler_values())
        press = Profiled(decl.ST)
        press.one_cycle()
        self.assertEqual(set(projection.profiler_status(APP, press.prof)), set(empty))
        self.assertEqual(sum(1 for k in empty if k.startswith("Profiler/History[")),
                         gen.CYCLE_HISTORY * (4 + len(decl.TIME_CLASSES)))

    def test_an_unvisited_step_is_an_empty_row(self):
        out = projection.profiler_status(APP, profiler_values())
        self.assertEqual((out["Profiler/StepStats[1]/Count"], out["Profiler/StepStats[1]/Label"]),
                         (0, ""))
        self.assertEqual(out["Profiler/LastCycle/CycleNo"], 0)

    def test_nothing_without_the_profile(self):
        self.assertEqual(projection.profiler_status(APP, None), {})


if __name__ == "__main__":
    unittest.main()
