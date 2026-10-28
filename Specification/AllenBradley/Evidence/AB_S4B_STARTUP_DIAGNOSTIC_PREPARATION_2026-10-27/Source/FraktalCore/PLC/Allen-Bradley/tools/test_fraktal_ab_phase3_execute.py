"""Latency in setup must count toward the native watchdog observation."""
import unittest
from unittest.mock import patch

import fraktal_ab_phase3_execute as phase3


class StallObservation(unittest.TestCase):
    def test_setup_and_snapshot_time_are_not_subtracted_from_the_stall(self):
        clock = [0.0]
        observed = dict(Step=100, StepTimedOut=1, StallMs=30000)
        awaits = []

        def start(_comm, _settle):
            clock[0] += .5

        def await_unit(_comm, predicate, settle):
            awaits.append(settle)
            if len(awaits) == 1:
                clock[0] += .5
                unit = dict(observed, StepTimedOut=0, StallMs=1000)
            else:
                # Reproduce the failed native vector's remaining wait. The
                # full observation still exceeds the declared thirty seconds.
                clock[0] += 28.97
                unit = observed
            self.assertTrue(predicate(unit))
            return unit, 28970

        def document(_comm):
            clock[0] += .2
            return {phase3.ROOT + '/CurrentStepTimedOut': False}

        with patch.object(phase3.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(phase3.px, 'start_cycle', side_effect=start), \
             patch.object(phase3.px, 'await_unit', side_effect=await_unit), \
             patch.object(phase3, 'document', side_effect=document):
            unit, elapsed, early = phase3.observe_stall(object(), 4)
        self.assertEqual(unit, observed)
        self.assertAlmostEqual(elapsed, 30170)
        self.assertFalse(early)
        self.assertEqual(awaits, [4, phase3.APP.stall_time_ms / 1000 + 4])

    def test_missing_timed_out_read_is_returned_as_failure_evidence(self):
        with patch.object(phase3.px, 'start_cycle'), \
             patch.object(phase3.px, 'await_unit', return_value=(None, 100)), \
             patch.object(phase3, 'document', return_value={}):
            unit, _elapsed, early = phase3.observe_stall(object(), 4)
        self.assertIsNone(unit)
        self.assertIsNone(early)


if __name__ == '__main__':
    unittest.main()
