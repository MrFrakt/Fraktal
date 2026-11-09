"""C5b3 Phase 5 metrics/reports: canonical views, O10 facts and health precondition."""
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import fraktal_ab_declaration as decl
import fraktal_ab_fixture_reads as views
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_manifest as manifest
import fraktal_ab_phase5_execute as phase5
import fraktal_ab_press_execute as px
import fraktal_ab_press_s6_collapse_echo38 as base
import fraktal_ab_press_s6_shelving_echo38 as shelving
from test_fraktal_ab_s6_shelving_profile import Bench

APP = base.application()


class Views(unittest.TestCase):
    def test_run_style_offer_uses_canonical_zero_lower_bound(self):
        calls = []
        def read(_comm, paths, app):
            calls.append(tuple(paths))
            return {'Press/SupportedRunStylesPublished[0]': True,
                    'Press/SupportedRunStylesPublished[1]': True,
                    'Press/SupportedRunStylesPublished[2]': True,
                    'Press/RunStyle': 1}
        with patch.object(views, '_session', return_value=NS(root='Press')), \
                patch.object(views, 'values', side_effect=read):
            self.assertEqual(views.run_style_offer(object(), app=APP), ([True, True, True], 1))
        self.assertEqual(calls, [('Press/SupportedRunStylesPublished[0]',
                                  'Press/SupportedRunStylesPublished[1]',
                                  'Press/SupportedRunStylesPublished[2]',
                                  'Press/RunStyle')])

    def test_state_flags_refuse_invalid_or_changed_counts(self):
        for seq in (({'Press/StateFlagCount': -1},), ({'Press/StateFlagCount': 3},),
                    ({'Press/StateFlagCount': 2}, {'Press/StateFlagCount': 1})):
            it = iter(seq)
            with self.subTest(seq=seq), patch.object(views, '_session', return_value=NS(root='Press')), \
                    patch.object(views, 'values', side_effect=lambda *a, **k: next(it)), \
                    self.assertRaises(ValueError):
                views.state_flags(object(), app=APP)

    def test_collapsed_down_time_brackets_canonical_oee_acquisition(self):
        ticks = [0.0]
        def advance(seconds):
            ticks[0] += seconds
        cards = [
            {'Oee/RunMs': 4000, 'Oee/DownMs': 1700, 'Oee/IdleMs': 0, 'Oee/Availability': 4000 / 5700},
            {'Oee/RunMs': 4000, 'Oee/DownMs': 3500, 'Oee/IdleMs': 0, 'Oee/Availability': 4000 / 7500},
        ]
        def read_card(_comm, *, app):
            advance(0.4)
            return cards.pop(0)
        with patch.object(phase5, 'APP', APP), \
                patch.object(phase5.time, 'monotonic', side_effect=lambda: ticks[0]), \
                patch.object(phase5.time, 'sleep', side_effect=advance), \
                patch.object(views, 'oee_card', side_effect=read_card), \
                patch.object(projection, 'read_records', side_effect=AssertionError('unexpected legacy read')):
            row, second = phase5.down_time_row(None, {'Error': 1})
        self.assertTrue(row['passed'], row)
        self.assertEqual(row['observed']['grew']['Oee/DownMs'], 1800)
        self.assertEqual(row['observed']['sampleIntervalMs'], [1000.0, 1800.0])
        self.assertEqual(second['Oee/DownMs'], 3500)

    def test_refusal_keys_resolve_from_deployed_command_metadata(self):
        reader = NS(command_keys=lambda root: {mailbox.RUN_STYLE_REFUSED_KEY: 912})
        with patch.object(phase5, 'APP', APP), \
                patch.object(views, '_session', return_value=NS(root='Press', reader=reader)), \
                patch.object(manifest, 'numeric_key', side_effect=AssertionError('unexpected generator key table')):
            self.assertEqual(phase5.key(object(), mailbox.RUN_STYLE_REFUSED_KEY), 912)


class HealthPrecondition(unittest.TestCase):
    def run_rows(self, profile_app, *, samples=2):
        b = Bench(profile_app)
        for _ in range(samples):
            b.scan()
        facet = {
            'Present': bool(b.health['Present']), 'Healthy': bool(b.health['Healthy']),
            'TaskAvailable': bool(b.health['TaskAvailable']), 'TaskCycleUs': b.probe['IntervalUs'],
            'TaskJitterUs': b.probe['JitterUs'], 'TaskOverrun': bool(b.health['TaskOverrun']),
            'ControllerAvailable': False, 'CpuLoadPct': 0.0, 'MemoryAvailableMb': 0,
            'IpcAvailable': False, 'IpcTemperatureC': 0.0, 'FanHealthy': False,
            'StorageHealthPct': 0.0, 'FieldbusAvailable': False, 'FieldbusMasterHealthy': False,
            'LostFrameCount': 0, 'SlaveErrorCount': 0, 'DcAvailable': False,
            'DcSynchronized': False, 'TimeQuality/Available': True,
            'TimeQuality/Synchronized': bool(b.probe['TimeIsSynchronized']),
            'TimeQuality/Source': '', 'TimeQuality/OffsetUs': 0,
        }
        with patch.object(phase5, 'APP', profile_app), \
                patch.object(px, '_idle'), \
                patch.object(phase5.time, 'sleep'), \
                patch.object(views, 'system_health', return_value=facet), \
                patch.object(views, 'read_alarm_log', return_value=(b.active, b.ring)):
            return phase5.health_rows(object(), ack=1.0, settle=4.0)

    def test_shelving_profile_satisfies_both_phase5_health_rows_after_second_sample(self):
        app = shelving.application()
        self.assertEqual([r['passed'] for r in self.run_rows(app, samples=1)], [False, False])
        rows = self.run_rows(app, samples=2)
        self.assertEqual([r['passed'] for r in rows], [True, True], rows)
        self.assertEqual(rows[1]['observed']['held'],
                         [{'ReasonCode': 21, 'Severity': 0, 'ResetClass': gen.RESET_AUTO, 'SourceModuleId': 1}])

    def test_normal_press_keeps_metrics_exclusion_and_fails_phase5_health_precondition(self):
        rows = self.run_rows(base.application(), samples=2)
        self.assertEqual([r['passed'] for r in rows], [False, False])
        self.assertTrue(rows[0]['observed']['Healthy'])
        self.assertEqual(rows[1]['observed']['held'], [])


if __name__ == '__main__':
    unittest.main()
