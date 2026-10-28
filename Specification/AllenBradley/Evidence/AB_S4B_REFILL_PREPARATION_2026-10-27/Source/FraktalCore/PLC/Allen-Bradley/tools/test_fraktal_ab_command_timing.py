"""TC3's command timing (Core §8.11.4(a)) and degradation watch (d) on AB.

(a) Every command a module runs is timed from acceptance to its end - DONE,
ERROR or ABORTED, holds included - into one row per command ordinal: Count,
Last, Minimum, Maximum and TC3's integer running mean. It is written once, in
the library type, so every instance of every commanded type has it.

(d) A cycle whose WORK time passes its model's baseline by more than 20 %
latches once per excursion and becomes ONE maintenance occurrence in the alarm
log - LOW, AUTO_RESET, from the Unit - data, never downtime.
"""

import unittest

import fraktal_ab_generate as gen
import fraktal_ab_library as library
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
import fraktal_ab_st_model as st
from test_fraktal_ab_alarm_log import Bench as AlarmBench
from test_fraktal_ab_oee import pl_fraktal
from test_fraktal_ab_profiler import Profiled, Station
from test_fraktal_ab_rendition_cycle import APP, CYLINDERS
import fraktal_ab_declaration as decl


PERIOD = APP.task_period_ms
TYPE = st.parse("\n".join(gen.type_logic(library.CYLINDER)))
EXTEND, RETRACT = 1, 2


class Cylinder:
    """One library cylinder, alone, scan by scan."""

    def __init__(self):
        self.ctx = st.structure(gen.module_context_members(library.CYLINDER))
        self.ctx["Par_TaskPeriodMs"] = PERIOD
        self.scans = 0

    def scan(self, count=1):
        for _ in range(count):
            self.scans += 1
            st.Controller({"Ctx": self.ctx, "Scan": self.scans}).run(TYPE)

    def command(self, ordinal, target, hold=0, abort_after=None):
        """Run one command to its end: Execute up until a terminal state, with
        `hold` scans of HoldRequest after the first, then Execute down."""
        c = self.ctx
        c.update(ParCmd_Command=ordinal, ParCmd_Target=target, Execute=1)
        self.scan()
        if hold:
            c["HoldRequest"] = 1
            self.scan(hold)
            c["HoldRequest"] = 0
        for i in range(200):
            if abort_after is not None and i == abort_after:
                c["Abort"] = 1
            if c["Done"] or c["Error"] or c["Aborted"]:
                break
            self.scan()
        c.update(Execute=0, Abort=0)
        self.scan()

    def row(self, ordinal):
        i = ordinal - 1
        return tuple(self.ctx[m][i] for m in ("TimCount", "TimLast", "TimMin",
                                               "TimMax", "TimAvg"))


class TheContract(unittest.TestCase):
    def test_eight_rows_as_tc3(self):
        self.assertEqual(gen.CMD_STATS, pl_fraktal("MAX_CMD_STATS"))

    def test_cycle_time_degraded_is_registered_core(self):
        self.assertEqual(APP.reasons["CYCLE_TIME_DEGRADED"], 2007)

    def test_the_baseline_is_per_model_config_under_tc3s_keys(self):
        member = next(m for m in APP.records[0].members if m.name == "BaselineWorkMs")
        self.assertEqual((member.write_key, member.label_key, member.minimum,
                          member.maximum), ("press.recipe.baselineWorkMs",
                                            "project.config.baselineWorkMs", 0, 600000))
        self.assertEqual([m.values["BaselineWorkMs"] for m in APP.models],
                         [m.values["IdealCycleMs"] for m in APP.models])


class CommandTiming(unittest.TestCase):
    def test_a_stroke_is_timed_from_acceptance_to_done(self):
        c = Cylinder()
        c.command(EXTEND, library.CYLINDER_EXTENDED)       # 4 scans at 25/scan
        self.assertEqual(c.row(EXTEND), (1, 40, 40, 40, 40))

    def test_a_command_already_at_its_end_is_timed_too(self):
        """Accepted and done in one scan: TC3 leaves no BUSY edge and never
        times it. Core §8.11.4(a) says every command."""
        c = Cylinder()
        c.command(RETRACT, library.CYLINDER_RETRACTED)
        self.assertEqual(c.row(RETRACT), (1, PERIOD, PERIOD, PERIOD, PERIOD))

    def test_a_hold_is_part_of_the_commands_time(self):
        """Acceptance to end, as TC3 measures it - while the timeout clock,
        rightly, stood still."""
        c = Cylinder()
        c.command(EXTEND, library.CYLINDER_EXTENDED, hold=6)
        self.assertEqual(c.row(EXTEND)[1], 40 + 6 * PERIOD)
        self.assertEqual(c.ctx["HeldScans"], 6, "it really was held, and the "
                         "timeout clock does not run while held")

    def test_a_timeout_and_an_abort_close_their_rows(self):
        c = Cylinder()
        c.ctx["FaultRequest"] = 1
        c.command(EXTEND, library.CYLINDER_EXTENDED)
        self.assertEqual(c.ctx["Error"], 0, "released by the Execute drop")
        self.assertEqual(c.row(EXTEND)[0], 1)
        self.assertGreaterEqual(c.row(EXTEND)[1], c.ctx["Par_TimeoutMs"])
        c.ctx["FaultRequest"] = 0
        c.command(RETRACT, library.CYLINDER_RETRACTED - 50, abort_after=1)
        self.assertEqual(c.row(RETRACT)[0], 1)

    def test_tc3s_running_mean_in_integers(self):
        c = Cylinder()
        expected, durations = 0, []
        for n, hold in enumerate((0, 7, 2, 11, 0), start=1):
            c.command(EXTEND, library.CYLINDER_EXTENDED, hold=hold)
            c.command(RETRACT, library.CYLINDER_RETRACTED)
            d = 40 + hold * PERIOD
            durations.append(d)
            expected += int((d - expected) / n)
        self.assertEqual(c.row(EXTEND), (5, durations[-1], min(durations),
                                         max(durations), expected))

    def test_an_ordinal_past_the_rows_is_said_not_lost(self):
        c = Cylinder()
        c.command(gen.CMD_STATS + 1, library.CYLINDER_EXTENDED)
        self.assertEqual(c.ctx["TimTrunc"], 1)
        self.assertEqual(sum(c.ctx["TimCount"]), 0)


class EveryCommandOfACycle(unittest.TestCase):
    def test_each_cylinder_times_every_command_it_ran(self):
        press = Profiled(decl.ST)
        press.one_cycle()
        for name in CYLINDERS:
            with self.subTest(name):
                ctx = press.ctx(name)
                self.assertEqual(sum(ctx["TimCount"]), ctx["RunCount"])
                self.assertTrue(all(ctx["TimLast"][i] % PERIOD == 0
                                    for i in range(gen.CMD_STATS)))


class ThePublishedRows(unittest.TestCase):
    def test_one_row_per_ordinal_named_by_its_command(self):
        c = Cylinder()
        c.command(EXTEND, library.CYLINDER_EXTENDED)
        out = projection.command_timing(APP, "Door", c.ctx)
        self.assertEqual((out["Timing/Rows[1]/Id"], out["Timing/Rows[1]/Label"],
                          out["Timing/Rows[1]/Count"], out["Timing/Rows[1]/Last"],
                          out["Timing/Rows[1]/Avg"]), (1, "std.command.extend", 1, 40, 40))
        self.assertEqual((out["Timing/Rows[2]/Id"], out["Timing/Rows[2]/Count"]), (2, 0))
        self.assertEqual((out["Timing/Rows[3]/Id"], out["Timing/Rows[3]/Label"]), (0, ""))
        self.assertEqual(sum(1 for k in out if k.endswith("/Count")), gen.CMD_STATS)

    def test_a_module_without_commands_publishes_no_timing(self):
        sensor = next(m for m in APP.modules if not m.commands)
        context = st.structure(gen.module_members(sensor))
        self.assertEqual(projection.command_timing(APP, sensor.name, context), {})


class Degradation(unittest.TestCase):
    """At cycle close, WORK time against the running model's baseline."""

    def cycle(self, s, work_scans, wait_scans=1):
        s.step_to(100, wait_scans)          # TC3's operator wait: not WORK
        s.step_to(110, work_scans)
        s.step_to(999, 1, finish=True)

    def station(self, baseline):
        s = Station()
        s.tags[f"{APP.records[0].name}Tag"]["BaselineWorkMs"] = baseline
        return s

    def test_once_per_excursion_and_rearmed_below_the_band(self):
        s = self.station(100)
        self.cycle(s, 30)                   # 310 ms of work against 120
        p = s.prof
        self.assertEqual((p["Degraded"], p["DegradedCount"], p["DegradedWorkMs"]),
                         (1, 1, 310))
        self.cycle(s, 30)
        self.assertEqual(p["DegradedCount"], 1, "still the same excursion")
        self.cycle(s, 10)                   # 110: inside the band
        self.assertEqual(p["Degraded"], 0)
        self.cycle(s, 30)
        self.assertEqual(p["DegradedCount"], 2)

    def test_the_band_is_tc3s_twenty_percent(self):
        s = self.station(100)
        self.cycle(s, 11)                   # 120 = 100 + 20 %: not past it
        self.assertEqual(s.prof["DegradedCount"], 0)
        self.cycle(s, 12)                   # 130
        self.assertEqual(s.prof["DegradedCount"], 1)

    def test_waiting_is_not_work(self):
        s = self.station(100)
        self.cycle(s, 5, wait_scans=200)
        self.assertEqual(s.prof["DegradedCount"], 0)

    def test_a_new_baseline_rearms_it(self):
        s = self.station(100)
        self.cycle(s, 30)
        s.tags[f"{APP.records[0].name}Tag"]["BaselineWorkMs"] = 110
        self.cycle(s, 30)
        self.assertEqual(s.prof["DegradedCount"], 2)

    def test_a_zero_baseline_is_off(self):
        s = self.station(0)
        self.cycle(s, 300)
        self.assertEqual(s.prof["DegradedCount"], 0)

    def test_each_excursion_is_one_maintenance_occurrence(self):
        bench = AlarmBench()
        prof = bench.controller.tags[gen.profiler_tag(APP)]
        prof["DegradedCount"] = 1
        bench.scan()
        ring, log = bench.ring, bench.log
        self.assertEqual((log["RingHead"], log["NActive"], log["Blocking"]), (1, 0, 0))
        self.assertEqual((ring["RingReasonCode"][0], ring["RingSeverity"][0],
                          ring["RingResetClass"][0], ring["RingSourceModuleId"][0],
                          ring["RingIoRoles"][0]),
                         (2007, 0, gen.RESET_AUTO, 1, 0))
        self.assertEqual(ring["RingComeTime"][0], ring["RingGoneTime"][0])
        bench.scan(3)
        self.assertEqual(log["RingHead"], 1, "logged once")


if __name__ == "__main__":
    unittest.main()
