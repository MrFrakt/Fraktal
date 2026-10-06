"""The controller health probe - Core §8.12's input, measured by AB spike S3.

TC3's FB_TcSystemHealthProbe takes the task's real period from its monotonic
clock and the rest from the platform. AB takes the period from the wall clock
the routine already reads, and the rest from the TASK, TimeSynchronize and
FaultLog objects through GSV. These tests run the generated probe on the ST
model with those objects modelled; which attributes the CONTROLLER answers is
S3's to measure, and Studio's import is the arbiter of their names.
"""

import re
import unittest

import fraktal_ab_generate as gen
import fraktal_ab_press_demo as demo
import fraktal_ab_st_model as st


APP = demo.application()
PROBE = gen.health_probe_tag(APP)
CLOCK = next(iter(gen.clock_tags(APP)))
PERIOD_US = APP.task_period_ms * 1000
LOGIC = st.parse("\n".join(gen.health_probe_logic(APP)))
# S3's candidate set: every attribute DINT-typed, so no destination needs a
# type the binding's DINT-only structures do not have.
EXPECTED_GSV = {
    ("TASK", APP.task_name, "LastScanTime"), ("TASK", APP.task_name, "MaxScanTime"),
    ("TASK", APP.task_name, "OverlapCount"),
    ("TimeSynchronize", None, "IsSynchronized"), ("TimeSynchronize", None, "PTPEnable"),
    ("FaultLog", None, "MinorFaultBits"), ("FaultLog", None, "MajorFaultBits"),
}


class Probe:
    def __init__(self, objects=None):
        self.tags = {PROBE: st.structure(gen.health_probe_members()), CLOCK: [0] * 7}
        table = {key: 0 for key in EXPECTED_GSV}
        table.update(objects or {})
        self.plc = st.Controller(self.tags, {"GSV": st.gsv(table)})

    @property
    def p(self):
        return self.tags[PROBE]

    def scan_at(self, second, micro):
        """One scan whose wall-clock reading (taken earlier in the routine)
        was `second`.`micro`."""
        self.tags[CLOCK][5], self.tags[CLOCK][6] = second, micro
        self.plc.run(LOGIC)


class TheReads(unittest.TestCase):
    def test_exactly_s3s_dint_attributes(self):
        found = set()
        for line in gen.health_probe_logic(APP):
            m = re.match(r"GSV\((\w+),(\w*),(\w+),", line)
            if m:
                found.add((m.group(1), m.group(2) or None, m.group(3)))
        self.assertEqual(found, EXPECTED_GSV)

    def test_every_destination_is_a_probe_dint(self):
        members = {m.name for m in gen.health_probe_members()}
        for line in gen.health_probe_logic(APP):
            if line.startswith("GSV("):
                dest = line.rstrip(");").split(",")[-1]
                self.assertTrue(dest.startswith(f"{PROBE}."), line)
                self.assertIn(dest.split(".", 1)[1], members, line)

    def test_the_objects_are_copied_every_scan(self):
        probe = Probe({("TASK", APP.task_name, "LastScanTime"): 812,
                       ("TASK", APP.task_name, "OverlapCount"): 3,
                       ("TimeSynchronize", None, "IsSynchronized"): 0,
                       ("FaultLog", None, "MinorFaultBits"): 0x40})
        probe.scan_at(1, 0)
        self.assertEqual((probe.p["TaskLastScanUs"], probe.p["TaskOverlapCount"],
                          probe.p["TimeIsSynchronized"], probe.p["MinorFaultBits"]),
                         (812, 3, 0, 0x40))

    def test_it_runs_right_after_the_clock_is_read(self):
        lines = list(gen.routine_logic(APP))
        clock = next(i for i, l in enumerate(lines) if l.startswith("GSV(WallClockTime"))
        probe = next(i for i, l in enumerate(lines) if l.startswith("GSV(TASK"))
        self.assertLess(clock, probe, "the period is measured from this scan's reading")


class ThePeriod(unittest.TestCase):
    def test_no_interval_on_the_first_scan(self):
        probe = Probe()
        probe.scan_at(10, 0)
        self.assertEqual((probe.p["Samples"], probe.p["IntervalUs"]), (1, 0))

    def test_the_real_period_and_its_jitter(self):
        probe = Probe()
        probe.scan_at(10, 0)
        probe.scan_at(10, PERIOD_US)
        self.assertEqual((probe.p["IntervalUs"], probe.p["JitterUs"]), (PERIOD_US, 0))
        probe.scan_at(10, 2 * PERIOD_US + 2500)
        self.assertEqual((probe.p["IntervalUs"], probe.p["JitterUs"]), (PERIOD_US + 2500, 2500))
        probe.scan_at(10, 3 * PERIOD_US + 500)
        self.assertEqual((probe.p["IntervalUs"], probe.p["JitterUs"]), (PERIOD_US - 2000, 2000))

    def test_the_minute_wrap(self):
        probe = Probe()
        probe.scan_at(59, 995_000)
        probe.scan_at(0, 5_000)
        self.assertEqual(probe.p["IntervalUs"], PERIOD_US)

    def test_a_window_publishes_its_extremes_and_starts_again(self):
        probe = Probe()
        t = 0
        probe.scan_at(0, t)
        for i in range(gen.HEALTH_WINDOW_SCANS):
            t += PERIOD_US + (3000 if i == 40 else -1000 if i == 70 else 0)
            probe.scan_at(t // 1_000_000, t % 1_000_000)
        self.assertEqual((probe.p["MaxIntervalUs"], probe.p["MinIntervalUs"],
                          probe.p["MaxJitterUs"], probe.p["WinScans"]),
                         (PERIOD_US + 3000, PERIOD_US - 1000, 3000, 0))
        t += PERIOD_US
        probe.scan_at(t // 1_000_000, t % 1_000_000)
        self.assertEqual(probe.p["WinMaxIntervalUs"], PERIOD_US, "a new window")
        self.assertEqual(probe.p["MaxIntervalUs"], PERIOD_US + 3000, "the last full one stands")


if __name__ == "__main__":
    unittest.main()
