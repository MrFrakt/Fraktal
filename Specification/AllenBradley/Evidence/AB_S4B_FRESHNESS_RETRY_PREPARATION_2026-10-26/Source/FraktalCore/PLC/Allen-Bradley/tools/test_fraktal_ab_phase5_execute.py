"""The hardware fixture must still test motion when CIP staging is slow."""

import unittest
from unittest.mock import patch

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_phase5_execute as fixture
import fraktal_ab_press_execute as px
import fraktal_ab_st_model as st
from test_fraktal_ab_run_styles import Paced


class SlowFixture(unittest.TestCase):
    def down_time(self, *, rate=1, grows=None, faulted=1, missing=False):
        tick = [0.0]

        def advance(seconds):
            tick[0] += seconds

        def sample(_comm):
            advance(.5)
            if missing:
                return None
            raw = {m.name: [0] * m.dimension if m.dimension else 0 for m in gen.oee_members()}
            raw.update(Epoch=1, RunS=4)
            raw['DownS'], raw['DownMs'] = divmod(1200 + round(tick[0] * 1000 * rate), 1000)
            if grows:
                raw[grows + 'S'], raw[grows + 'Ms'] = divmod(round(tick[0] * 1000), 1000)
            return raw

        def unit(_comm):
            advance(.7)
            return dict(GoodCount=1, ScrapCount=0)

        def records(_comm):
            advance(.7)
            return {fixture.APP.records[0].name: {fixture.APP.ideal_cycle_member: 950}}

        with patch.object(fixture.time, 'monotonic', side_effect=lambda: tick[0]), \
             patch.object(fixture.time, 'sleep', side_effect=advance), \
             patch.object(fixture, 'oee_raw', side_effect=sample), \
             patch.object(px, 'read_unit', side_effect=unit), \
             patch.object(fixture.projection, 'read_records', side_effect=records):
            return fixture.down_time_row(None, {'Error': faulted})[0]

    def test_down_time_uses_native_sample_interval_with_slow_reads(self):
        row = self.down_time()
        self.assertTrue(row['passed'], row)
        self.assertEqual(row['observed']['grew']['Oee/DownMs'], 2900)
        self.assertEqual(row['observed']['sampleIntervalMs'], [2400, 3400])

    def test_down_time_refuses_wrong_rate_and_nonfault_buckets(self):
        for arguments in ({'rate': 0}, {'rate': .5}, {'rate': 2}, {'grows': 'Run'},
                          {'grows': 'Idle'}, {'faulted': 0}, {'missing': True}):
            with self.subTest(arguments=arguments):
                self.assertFalse(self.down_time(**arguments)['passed'])

    def test_release_during_motion_survives_slow_argument_staging(self):
        for language in fixture.AUTO.renditions:
            with self.subTest(language=language):
                press = Paced(language, decl.RUN_HOLD_TO_RUN, start=110)
                for tag in px.WRITABLE:
                    press.plc.tags.setdefault(tag, 0)
                # Unlike the ordinary rendition model, this fixture needs its
                # declared simulation fault/hold inputs wired into the modules.
                keys = gen.localization_numbers(px.APP)
                modules = {gen.ctx_tag_for(px.APP, module.name): module for module in px.APP.modules}
                press.modules = [(ctx, st.parse("\n".join(gen.module_setup_lines(
                    px.APP, modules[ctx], keys))), body) for ctx, _setup, body in press.modules]
                press.plc.tags[px.PART_PRESENT] = 0

                def advance(seconds):
                    for _ in range(round(seconds * 100)):
                        press.scan()

                def read_unit(_comm):
                    press.scan()
                    return dict(press.unit, Step=press.step())

                def await_unit(_comm, predicate, settle):
                    last = None
                    for _ in range(round(settle * 100)):
                        last = read_unit(None)
                        if predicate(last):
                            return last, 0
                    return last, settle * 1000

                def command(_comm, kind, settle, **arguments):
                    # Longer than an unheld slide/door motion: the original
                    # fixture released too late under this exact guard cost.
                    advance(0.6)
                    if kind == mailbox.SET_HOLD_RUN:
                        press.unit['HoldRun'] = arguments['BoolValue']
                    elif kind == mailbox.STOP:
                        press.unit['Running'] = 0
                    else:
                        self.fail(f'unexpected command {kind}')
                    press.scan()
                    return {'accepted': True}

                def await_module(_comm, name, predicate, settle):
                    for _ in range(round(settle * 100)):
                        press.scan()
                        last = dict(press.ctx(name))
                        if predicate(last):
                            return last, 0
                    return last, settle * 1000

                def write(_comm, tag, value):
                    self.assertIn(tag, px.WRITABLE)
                    press.plc.tags[tag] = value
                    press.scan()
                    return True

                opened = {'style': {'accepted': True}, 'start': {'accepted': True}, 'pastStart': True}
                with patch.object(fixture, 'begin', return_value=opened), \
                     patch.object(fixture, 'issued', side_effect=lambda _comm: press.issued()), \
                     patch.object(fixture.time, 'sleep', side_effect=advance), \
                     patch.object(px, 'read_unit', side_effect=read_unit), \
                     patch.object(px, 'read_module', side_effect=lambda _comm, name: dict(press.ctx(name))), \
                     patch.object(px, 'await_module', side_effect=await_module), \
                     patch.object(px, 'await_unit', side_effect=await_unit), \
                     patch.object(px, 'command', side_effect=command), \
                     patch.object(px, 'write', side_effect=write):
                    result = fixture.held_cycle(None, language, ack=1, settle=4)
                self.assertEqual(result['motionAtRelease'], {'Busy': 1, 'OutImm_Held': 1}, result)
                self.assertEqual(result['issuedUnheld'], 0)
                self.assertEqual(result['releasedAt'], {'Step': fixture.DOOR_CLOSE, 'Issued': 0, 'HoldRun': 0})
                self.assertEqual(result['issuedBeforeRelease'], 3)
                self.assertEqual(result['slideArrived'], 1)
                self.assertEqual(result['issuedInCycle'], fixture.DECLARED)
                self.assertTrue(result['cycleClosed'])
                self.assertEqual(press.plc.tags[px.HOLD['PartSlide']], 0)

    def test_fixture_hold_is_restored_when_release_fails(self):
        writes = []
        with patch.object(fixture, 'begin', return_value={}), \
             patch.object(fixture, 'issued', return_value=0), \
             patch.object(fixture.time, 'sleep'), \
             patch.object(px, 'read_unit', return_value={}), \
             patch.object(px, 'read_module', return_value={'Busy': 1, 'OutImm_Held': 1}), \
             patch.object(px, 'await_module', return_value=({'Busy': 1, 'OutImm_Held': 1}, 0)), \
             patch.object(px, 'await_unit', return_value=({}, 0)), \
             patch.object(px, 'command', side_effect=[{'accepted': True}, AssertionError('release failed')]), \
             patch.object(px, 'write', side_effect=lambda _comm, tag, value: writes.append((tag, value)) or True):
            with self.assertRaisesRegex(AssertionError, 'release failed'):
                fixture.held_cycle(None, decl.ST, ack=1, settle=4)
        self.assertEqual(writes, [(px.HOLD['PartSlide'], 1), (px.HOLD['PartSlide'], 0)])


if __name__ == '__main__':
    unittest.main()
