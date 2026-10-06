"""TC3's system-health publisher (Core §8.12) on AB, over S3's measured subset.

The publisher judges the probe against the station's thresholds every scan:
each condition that holds is an AUTO_RESET event while it lasts - raised once,
closed into the ring when it clears, never blocking a start - and the status
is published where the HMI's health facet reads it. A group this controller
cannot measure (CPU, memory, IPC, distributed clock) is unavailable, never
healthy; and a station whose CPU and memory cannot be read says so, by TC3's
own rule, as CONTROLLER_METRICS_UNAVAILABLE.
"""

import dataclasses
import re
import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
import fraktal_ab_reasons as reasons
import fraktal_ab_st_model as st
from test_fraktal_ab_alarm_log import Bench as AlarmBench
from test_fraktal_ab_core_ordinals import CORE_DUTS


APP = demo.application()
H, P, C = gen.system_health_tag(APP), gen.health_probe_tag(APP), gen.health_cfg_tag(APP)
LOGIC = st.parse("\n".join(gen.system_health_logic(APP)))
EVENT = {name: i for i, name in enumerate(gen.HEALTH_EVENTS)}
PERIOD_US = APP.task_period_ms * 1000


class Station:
    def __init__(self, **cfg):
        self.tags = {H: st.structure(gen.system_health_members()),
                     P: st.structure(gen.health_probe_members()),
                     C: st.structure(gen.health_cfg_members(APP))}
        self.tags[C].update(cfg)
        self.plc = st.Controller(self.tags)

    @property
    def h(self):
        return self.tags[H]

    def scan(self, **probe):
        p = self.tags[P]
        p["Samples"] += 1
        p.update({"IntervalUs": PERIOD_US, "JitterUs": 0, **probe})
        self.plc.run(LOGIC)
        return self.h

    def bad(self):
        return {name for name, i in EVENT.items() if self.h["Bad"][i]}


class TheContract(unittest.TestCase):
    def test_the_schema_is_tc3s(self):
        text = (CORE_DUTS / "ST_SystemHealthParCfg.TcDUT").read_text(encoding="utf-8")
        found = re.search(r"SchemaVersion\s*:\s*UINT\s*:=\s*(\d+)", text)
        self.assertEqual(int(found.group(1)), gen.HEALTH_SCHEMA)

    def test_every_event_is_a_registered_core_reason(self):
        for name in gen.HEALTH_EVENTS:
            with self.subTest(name):
                self.assertTrue(reasons.registered(name))
                self.assertEqual(APP.reasons[name], reasons.CORE[name])

    def test_the_press_requires_only_what_this_bench_has(self):
        h = APP.system_health
        self.assertEqual((h.require_time_sync, h.require_fieldbus, h.require_dc_sync),
                         (False, False, False))
        self.assertGreater(h.max_task_cycle_us, PERIOD_US)

    def test_a_threshold_inside_the_period_is_refused(self):
        findings = decl.validate(dataclasses.replace(
            APP, system_health=dataclasses.replace(APP.system_health,
                                                   max_task_cycle_us=PERIOD_US)))
        self.assertTrue(any("max_task_cycle_us" in f for f in findings))


class ThePublisher(unittest.TestCase):
    def test_nothing_is_judged_on_the_first_sample(self):
        """TC3's MAIN skips the sample with no prior scan: no false overrun
        at a download, and nothing claimed healthy either."""
        s = Station()
        s.scan(IntervalUs=0)
        self.assertEqual((s.bad(), s.h["TaskAvailable"], s.h["Healthy"]), (set(), 0, 0))

    def test_steady_the_only_condition_is_the_metrics_it_cannot_read(self):
        s = Station()
        s.scan()
        s.scan()
        self.assertEqual(s.bad(), {"CONTROLLER_METRICS_UNAVAILABLE"})
        self.assertEqual((s.h["Present"], s.h["TaskAvailable"], s.h["Healthy"]), (1, 1, 0))

    def test_an_overlap_is_an_overrun_for_that_scan(self):
        s = Station()
        s.scan(TaskOverlapCount=4)                 # a count from before: not now
        self.assertEqual(s.h["TaskOverrun"], 0, "not even published for a scan")
        s.scan()
        self.assertNotIn("TASK_OVERRUN", s.bad())
        s.scan(TaskOverlapCount=5)
        self.assertIn("TASK_OVERRUN", s.bad())
        self.assertEqual(s.h["TaskOverrun"], 1)
        s.scan()
        self.assertNotIn("TASK_OVERRUN", s.bad())

    def test_a_long_period_is_an_overrun(self):
        s = Station()
        s.scan()
        s.scan(IntervalUs=APP.system_health.max_task_cycle_us + 1)
        self.assertIn("TASK_OVERRUN", s.bad())
        s.scan(IntervalUs=APP.system_health.max_task_cycle_us)
        self.assertNotIn("TASK_OVERRUN", s.bad())

    def test_jitter_past_its_threshold(self):
        s = Station()
        s.scan()
        s.scan(JitterUs=APP.system_health.max_task_jitter_us + 1)
        self.assertIn("TASK_JITTER_HIGH", s.bad())
        s.scan(JitterUs=APP.system_health.max_task_jitter_us)
        self.assertNotIn("TASK_JITTER_HIGH", s.bad())

    def test_a_requirement_this_bench_cannot_meet_is_bad(self):
        for member, event in (("RequireFieldbus", "FIELDBUS_MASTER_FAULT"),
                              ("RequireDcSync", "DC_SYNC_LOST"),
                              ("RequireTimeSync", "TIME_SYNC_LOST")):
            with self.subTest(member):
                s = Station(**{member: 1})
                s.scan()
                s.scan()
                self.assertIn(event, s.bad())

    def test_time_sync_is_met_by_a_synchronized_clock(self):
        s = Station(RequireTimeSync=1)
        s.scan()
        s.scan(TimeIsSynchronized=1)
        self.assertNotIn("TIME_SYNC_LOST", s.bad())

    def test_invalid_thresholds_are_not_present_and_judge_nothing(self):
        for cfg in ({"SchemaVersion": 2}, {"MaxTaskCycleUs": 0}, {"MaxTaskJitterUs": 0}):
            with self.subTest(cfg):
                s = Station(**cfg)
                s.scan()
                s.scan()
                self.assertEqual((s.h["Present"], s.bad(), s.h["Healthy"]), (0, set(), 0))


class TheEvents(unittest.TestCase):
    def bench(self):
        b = AlarmBench()
        return b, b.controller.tags[H]

    def test_a_condition_is_one_open_auto_reset_event_while_it_lasts(self):
        b, h = self.bench()
        h["Bad"][EVENT["TASK_OVERRUN"]] = 1
        b.scan()
        b.scan()
        log = b.log
        open_slots = b.open_slots()
        self.assertEqual(len(open_slots), 1, "raised once")
        s = open_slots[0]
        self.assertEqual((log["ActReasonCode"][s], log["ActSeverity"][s],
                          log["ActResetClass"][s], log["ActSourceModuleId"][s]),
                         (10, reasons.of(APP, "TASK_OVERRUN").priority, gen.RESET_AUTO, 1))
        self.assertEqual(log["Blocking"], 0, "never blocks a start")

    def test_it_closes_into_the_ring_when_it_clears(self):
        b, h = self.bench()
        h["Bad"][EVENT["TASK_JITTER_HIGH"]] = 1
        b.scan()
        h["Bad"][EVENT["TASK_JITTER_HIGH"]] = 0
        b.scan()
        self.assertEqual((b.open_slots(), b.log["RingHead"]), ([], 1))
        self.assertEqual(b.ring["RingReasonCode"][0], 11)
        self.assertNotEqual(b.ring["RingGoneTime"][0], 0)

    def test_the_registry_rates_each_event(self):
        """TC3's publisher proposes LOW; a registered reason's rationalization
        wins - TASK_OVERRUN is MED and FIELDBUS_MASTER_FAULT HIGH."""
        b, h = self.bench()
        for name in ("TASK_OVERRUN", "FIELDBUS_MASTER_FAULT", "CONTROLLER_METRICS_UNAVAILABLE"):
            h["Bad"][EVENT[name]] = 1
        b.scan()
        severity = {b.log["ActReasonCode"][s]: b.log["ActSeverity"][s] for s in b.open_slots()}
        self.assertEqual(severity, {10: 1, 15: 2, 21: 0})

    def test_an_operator_reset_does_not_close_a_condition_still_true(self):
        b, h = self.bench()
        h["Bad"][EVENT["CONTROLLER_METRICS_UNAVAILABLE"]] = 1
        b.scan()
        b.scan(reset=True)
        self.assertEqual(len(b.open_slots()), 1)


class ThePublishedFacet(unittest.TestCase):
    def test_where_the_hmi_reads_it(self):
        s = Station()
        s.scan()
        health = s.scan(JitterUs=120)
        out = projection.system_health_status(APP, health, s.tags[P])
        self.assertEqual((out["SystemHealth/Present"], out["SystemHealth/Healthy"],
                          out["SystemHealth/TaskAvailable"], out["SystemHealth/TaskCycleUs"],
                          out["SystemHealth/TaskJitterUs"]), (True, False, True, PERIOD_US, 120))

    def test_what_it_cannot_measure_is_unavailable_never_healthy(self):
        s = Station()
        s.scan()
        out = projection.system_health_status(APP, s.scan(), s.tags[P])
        for path in ("ControllerAvailable", "IpcAvailable", "FanHealthy",
                     "FieldbusAvailable", "FieldbusMasterHealthy", "DcAvailable",
                     "DcSynchronized"):
            self.assertIs(out[f"SystemHealth/{path}"], False, path)

    def test_time_quality_is_the_controllers(self):
        s = Station()
        s.scan()
        out = projection.system_health_status(APP, s.scan(TimeIsSynchronized=0, TimePtpEnable=0),
                                              s.tags[P])
        self.assertEqual((out["SystemHealth/TimeQuality/Available"],
                          out["SystemHealth/TimeQuality/Synchronized"],
                          out["SystemHealth/TimeQuality/Source"]), (True, False, ""))

    def test_nothing_without_the_reads(self):
        self.assertEqual(projection.system_health_status(APP, None, None), {})


if __name__ == "__main__":
    unittest.main()
