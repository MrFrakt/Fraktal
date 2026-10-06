"""TC3's OEE (Core §8.5.1) on the Allen-Bradley binding.

Each scan the Unit attributes its time to exactly one bucket - run (BUSY),
down (ERROR, or a blocking alarm), idle (everything else) - and every minute
pushes a sample into a 60-slot ring. Availability, Performance, Quality and
OEE are derived from those buckets and the part counts, each with a validity
flag: an invalid factor is omitted from the product and never shown as 100 %.

The controller keeps the accounting; the factors are derived by one function
in the projection, for the live figure and every sample alike. These tests run
the generated accounting on the ST model, the reset through the generated
mailbox, and the projection over both.
"""

import dataclasses
import re
import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
import fraktal_ab_st_model as st
from test_fraktal_ab_core_ordinals import CORE_DUTS
from test_fraktal_ab_manual import Bench
from test_fraktal_ab_projection import oee_values


APP = demo.application()
N = APP.name
UNIT, OEE, ALARM = f"FRK_{N}_Unit", gen.oee_tag(APP), gen.alarm_active_tag(APP)
CFG = f"{APP.records[0].name}Tag"
PERIOD = APP.task_period_ms
ACCOUNT = st.parse("\n".join(gen.oee_logic(APP)))
RESET = st.parse("\n".join(gen.oee_reset_lines(APP)))


def pl_fraktal(name):
    gvl = (CORE_DUTS.parent / "Params" / "PL_Fraktal.TcGVL").read_text(encoding="utf-8")
    found = re.search(rf"\b{name}\s*:\s*\w+\s*:=\s*(\d+)", gvl)
    assert found, f"PL_Fraktal no longer declares {name}"
    return int(found.group(1))


class Station:
    """The routine's OEE accounting, scan by scan, over the tags it reads."""

    def __init__(self):
        self.tags = {
            UNIT: st.structure(gen.unit_context_members(APP)),
            OEE: st.structure(gen.oee_members()),
            ALARM: st.structure(gen.alarm_active_members()),
            CFG: st.structure(APP.records[0].members),
        }
        self.plc = st.Controller(self.tags)

    @property
    def unit(self):
        return self.tags[UNIT]

    @property
    def oee(self):
        return self.tags[OEE]

    def scan(self, count=1):
        for _ in range(count):
            self.plc.run(ACCOUNT)

    def reset(self):
        self.plc.run(RESET)

    def ms(self, bucket):
        return self.oee[f"{bucket}S"] * 1000 + self.oee[f"{bucket}Ms"]

    def published(self):
        return projection.oee_status(APP, self.oee, self.unit,
                                     {APP.records[0].name: self.tags[CFG]})


class TheContract(unittest.TestCase):
    def test_the_ring_is_tc3s(self):
        """The HMI walks exactly 60 slots, one a minute."""
        self.assertEqual(gen.OEE_SAMPLES, pl_fraktal("MAX_OEE_SAMPLES"))
        self.assertEqual(gen.OEE_SAMPLE_MS, pl_fraktal("OEE_SAMPLE_MS"))

    def test_the_ideal_cycle_is_per_model_config_under_tc3s_keys(self):
        member = next(m for m in APP.records[0].members if m.name == "IdealCycleMs")
        self.assertEqual((member.write_key, member.label_key, member.minimum,
                          member.maximum), ("press.recipe.idealCycleMs",
                                            "project.config.idealCycleMs", 0, 600000))
        self.assertEqual([m.values["IdealCycleMs"] for m in APP.models], [950, 1350, 750])
        self.assertGreaterEqual(APP.records[0].schema_version, 3, "3 added IdealCycleMs")

    def test_an_ideal_cycle_outside_parcfg_is_refused(self):
        findings = decl.validate(dataclasses.replace(APP, ideal_cycle_member="Nope"))
        self.assertTrue(any("ideal_cycle_member Nope" in f for f in findings))

    def test_reset_oee_is_routed(self):
        self.assertIn(mailbox.RESET_OEE, mailbox.SUPPORTED)
        self.assertNotIn(mailbox.RESET_OEE, mailbox.refused_for(APP))


class TheFactors(unittest.TestCase):
    """TC3's _M_OeeCompute, case by case."""

    def test_nothing_counted_is_nothing_valid(self):
        f = projection.oee_factors(0, 0, 0, 0, 950)
        self.assertEqual((f["AvailValid"], f["PerfValid"], f["QualValid"],
                          f["OeeValid"], f["Oee"]), (False, False, False, False, 0.0))

    def test_availability_excludes_idle(self):
        f = projection.oee_factors(3000, 1000, 0, 0, 0)
        self.assertEqual((f["Availability"], f["AvailValid"]), (0.75, True))

    def test_performance_needs_an_ideal_cycle_and_is_capped(self):
        self.assertFalse(projection.oee_factors(10000, 0, 5, 0, 0)["PerfValid"])
        self.assertAlmostEqual(projection.oee_factors(10000, 0, 5, 0, 950)["Performance"],
                               0.475)
        self.assertEqual(projection.oee_factors(1000, 0, 5, 0, 950)["Performance"], 1.0)

    def test_quality_is_good_over_parts(self):
        self.assertAlmostEqual(projection.oee_factors(1, 0, 3, 1, 0)["Quality"], 0.75)

    def test_oee_is_the_product_of_the_valid_factors_only(self):
        """No ideal cycle: P is omitted, never taken as 100 % (O7)."""
        f = projection.oee_factors(3000, 1000, 3, 1, 0)
        self.assertFalse(f["PerfValid"])
        self.assertAlmostEqual(f["Oee"], 0.75 * 0.75)
        g = projection.oee_factors(10000, 0, 5, 0, 950)
        self.assertAlmostEqual(g["Oee"], 1.0 * 0.475 * 1.0)


class TheAccounting(unittest.TestCase):
    def test_every_scan_lands_in_exactly_one_bucket(self):
        s = Station()
        s.unit["Running"] = 1
        s.scan(250)
        s.unit.update(Running=0, Error=1)
        s.scan(130)
        s.unit["Error"] = 0
        s.scan(70)
        self.assertEqual((s.ms("Run"), s.ms("Down"), s.ms("Idle")),
                         (250 * PERIOD, 130 * PERIOD, 70 * PERIOD))

    def test_milliseconds_carry_into_seconds(self):
        s = Station()
        s.unit["Running"] = 1
        s.scan(1000 // PERIOD + 3)
        self.assertEqual((s.oee["RunS"], s.oee["RunMs"]), (1, 3 * PERIOD))

    def test_a_period_that_does_not_divide_a_second_loses_nothing(self):
        """30 ms: the carry lands on 1020, and the 20 past it are kept."""
        s = Station()
        s.unit.update(Running=1, Par_TaskPeriodMs=30)
        s.scan(100)
        self.assertEqual((s.oee["RunS"], s.oee["RunMs"]), (3, 0))
        s.scan(1)
        self.assertEqual(s.ms("Run"), 3030)

    def test_a_blocking_alarm_is_down_time(self):
        s = Station()
        s.tags[ALARM]["Blocking"] = 1
        s.scan(10)
        self.assertEqual((s.ms("Down"), s.ms("Idle")), (10 * PERIOD, 0))

    def test_busy_comes_first(self):
        """TC3 tests BUSY before ERROR: a running Unit with an alarm still
        open is producing, not down."""
        s = Station()
        s.unit["Running"] = 1
        s.tags[ALARM]["Blocking"] = 1
        s.scan(10)
        self.assertEqual((s.ms("Run"), s.ms("Down")), (10 * PERIOD, 0))

    def test_a_sample_a_minute_of_what_the_accounting_held(self):
        s = Station()
        s.unit.update(Running=1, GoodCount=7, ScrapCount=2)
        s.oee.update(GoodBase=4, NokBase=1)
        s.scan(gen.OEE_SAMPLE_MS // PERIOD - 1)
        self.assertEqual(s.oee["Head"], 0, "not before the minute")
        s.scan()
        o = s.oee
        self.assertEqual(o["Head"], 1)
        self.assertEqual([o[f"Smp{c}"][0] for c, _ in gen.OEE_SAMPLE_COLUMNS],
                         [o["Epoch"], 60, 0, 0, 0, 3, 1, 950])

    def test_the_ring_wraps_to_its_first_slot(self):
        s = Station()
        s.oee.update(Head=gen.OEE_SAMPLES, SampleMs=gen.OEE_SAMPLE_MS - PERIOD)
        s.scan()
        self.assertEqual(s.oee["Head"], 1)


class TheReset(unittest.TestCase):
    def test_reset_oee_through_the_mailbox(self):
        bench = Bench()
        oee = bench.tags[OEE]
        bench.unit.update(GoodCount=40, ScrapCount=3)
        oee.update(RunS=500, DownS=20, IdleS=9, Head=7, SampleMs=1234)
        self.assertEqual(bench.request(mailbox.RESET_OEE), (1, 0))
        self.assertEqual((oee["Epoch"], oee["RunS"], oee["DownS"], oee["Head"],
                          oee["SampleMs"], oee["GoodBase"], oee["NokBase"]),
                         (2, 0, 0, 0, 0, 40, 3))

    def test_a_reset_retires_every_sample(self):
        s = Station()
        s.unit["Running"] = 1
        s.scan(gen.OEE_SAMPLE_MS // PERIOD)
        self.assertTrue(s.published()["OeeTrend[1]/OeeValid"])
        s.reset()
        out = s.published()
        self.assertEqual(out["OeeTrendHead"], 0)
        self.assertFalse(out["OeeTrend[1]/OeeValid"], "an older epoch's sample")

    def test_after_a_reset_performance_counts_only_the_new_parts(self):
        """TC3's ResetOee zeroes the time but not the counts, so every part
        ever made is divided by the run time since the reset: Performance
        saturates at 100 % and Quality is the lifetime's. The baseline keeps
        time and parts in one window."""
        s = Station()
        s.unit.update(GoodCount=500, ScrapCount=20)
        s.reset()
        s.unit["Running"] = 1
        s.scan(10000 // PERIOD)
        s.unit.update(GoodCount=505, ScrapCount=20)
        out = s.published()
        self.assertAlmostEqual(out["Oee/Performance"], 950 * 5 / 10000)
        self.assertEqual(out["Oee/Quality"], 1.0)
        tc3 = projection.oee_factors(10000, 0, 505, 20, 950)
        self.assertEqual(tc3["Performance"], 1.0, "what TC3 would publish")


class ThePublishedCard(unittest.TestCase):
    def test_tc3s_paths_where_the_hmi_reads_them(self):
        s = Station()
        s.unit.update(Running=1, GoodCount=2)
        s.scan(gen.OEE_SAMPLE_MS // PERIOD)
        out = s.published()
        for leaf in ("Availability", "AvailValid", "Performance", "PerfValid",
                     "Quality", "QualValid", "Oee", "OeeValid", "RunMs", "DownMs",
                     "IdleMs"):
            self.assertIn(f"Oee/{leaf}", out)
        for slot in range(1, gen.OEE_SAMPLES + 1):
            self.assertIn(f"OeeTrend[{slot}]/Oee", out)
            self.assertIn(f"OeeTrend[{slot}]/OeeValid", out)
        self.assertNotIn("OeeTrend[0]/Oee", out, "1-based, as TC3's ring")
        self.assertEqual(out["Oee/RunMs"], gen.OEE_SAMPLE_MS)

    def test_a_sample_is_the_live_formula_at_that_minute(self):
        s = Station()
        s.unit.update(Running=1, GoodCount=50)
        s.scan(gen.OEE_SAMPLE_MS // PERIOD)
        out = s.published()
        self.assertEqual(out["OeeTrend[1]/Oee"], out["Oee/Oee"])
        self.assertTrue(out["OeeTrend[1]/OeeValid"])

    def test_the_live_ideal_is_the_running_models(self):
        s = Station()
        s.tags[CFG]["IdealCycleMs"] = 0
        s.unit.update(Running=1, GoodCount=1)
        s.scan(100)
        self.assertFalse(s.published()["Oee/PerfValid"])

    def test_nothing_is_published_without_the_accounting(self):
        self.assertEqual(projection.oee_status(APP, None, Station().unit, None), {})

    def test_the_fixture_is_a_fresh_reset(self):
        out = projection.oee_status(APP, oee_values(), Station().unit, None)
        self.assertEqual((out["OeeTrendHead"], out["Oee/OeeValid"]), (0, False))


if __name__ == "__main__":
    unittest.main()
