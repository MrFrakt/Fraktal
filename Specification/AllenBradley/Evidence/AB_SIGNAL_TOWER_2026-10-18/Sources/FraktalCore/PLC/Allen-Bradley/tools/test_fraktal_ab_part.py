import copy
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_host_demo as old_fixture
import fraktal_ab_host_events as host
import fraktal_ab_ld_model as ld
import fraktal_ab_manifest as manifest
import fraktal_ab_part as part
import fraktal_ab_part_demo as fixture
import fraktal_ab_projection as projection
import fraktal_ab_st_model as st

APP = fixture.application()


def emitter_callback(plc, args):
    model = st.Controller(dict(Ring=plc.read(args[1]), Slot=0, ByteIndex=0, UidIndex=0,
        **{n: plc.eval(v) for n, v in zip(
            ('Kind', 'ModelOrdinal', 'EventValue', 'Verdict', 'Reason'), args[2:])}))
    model.run('\n'.join(host.emit_logic(APP)))


def service_callback(plc, args, emit=emitter_callback):
    model = st.Controller(dict(**{n: plc.read(v) for n,v in zip(
        ('Part', 'Carrier', 'Ring', 'Ctx'), args[1:5])}, Index=0, WordValue=0, Nibble=0, Digit=0, IdentityMismatch=0,
        **{n: plc.eval(v) for n,v in zip(
            ('Operation', 'Verdict', 'Reason', 'RecordKind', 'MeasuredValue'), args[5:])}),
        calls={host.emitter_name(APP): emit})
    model.run('\n'.join(part.logic(APP)))


def setup():
    ring = st.structure(host.members(APP))
    ring.update(NowDate=20261018, NowTime=123456789, EpochLow=-1, EpochHigh=12345)
    values = {part.tag(APP): st.structure(part.members(APP)),
              part.carrier_tag(APP): st.structure(part.carrier_members(APP)),
              host.tag(APP): ring, 'FRK_Press_Unit': st.structure(gen.unit_context_members(APP)),
              'FRK_Press_Chart': st.structure(gen.chart_members(APP)),
              'FRK_Press_ParCfg': st.structure(APP.records[0].members), 'FRK_Press_ScanCount': 1}
    return st.Controller(values, calls={part.service_name(APP): service_callback,
                                       host.emitter_name(APP): emitter_callback},
                         routines={gen.step_mark_routine_name(APP): '\n'.join(gen.step_mark_logic(APP))})


def perform(plc, action, **kwargs):
    plc.run(part.call(APP, action, **kwargs) + ';')


def events(plc):
    return host.decode(APP, plc.tags[host.tag(APP)], [m.code for m in APP.models])['events']


class CarrierLifecycle(unittest.TestCase):
    def test_measurement_paths_remain_stable_between_cycles(self):
        plc = setup()
        raw = plc.tags[part.tag(APP)]
        empty = part.project(APP, raw)
        perform(plc, 'receive')
        perform(plc, 'record', record=1, value=300)
        active = part.project(APP, raw)
        self.assertEqual(set(empty), set(active))
        self.assertEqual(active['Part/Result/Records[1]/Name'], APP.part_carrier.records[0].name)
        perform(plc, 'aborted')
        perform(plc, 'receive')
        cleared = part.project(APP, raw)
        self.assertEqual(set(active), set(cleared))
        self.assertEqual(cleared['Part/Result/Records[1]/Name'], '')
        self.assertEqual(cleared['Part/Result/Records[1]/Value'], 0.)

    def test_fixture_and_canonical_reason_ordinals(self):
        from test_fraktal_ab_core_ordinals import core_enum
        self.assertEqual(decl.validate(APP), [])
        self.assertEqual({k:core_enum('E_Reason')[k] for k in part.REASONS}, part.REASONS)
        self.assertEqual(core_enum('E_CarrierKind')['BY_POSITION'], 2)

    def test_read_start_measure_write_before_event_and_identity_retained(self):
        plc = setup()
        carrier = plc.tags[part.carrier_tag(APP)]
        writes_seen = []
        def checked_emit(model, args):
            if model.eval(args[2]) == host.KINDS['PROCESSED']:
                writes_seen.append(carrier['Writes'])
                self.assertEqual(carrier['LastRecordValue'][0], 300)
                self.assertEqual(carrier['LastUid'], plc.tags[part.tag(APP)]['Uid'])
            emitter_callback(model, args)
        def checked_service(model, args):
            service_callback(model, args, emit=checked_emit)
        plc.calls[part.service_name(APP)] = checked_service
        perform(plc, 'receive')
        identity = part.uid(plc.tags[part.tag(APP)]['Uid'])
        self.assertEqual(identity, 'OFFLINE-PRESS-00003039FFFFFFFF00000001')
        perform(plc, 'start')
        perform(plc, 'record', record=1, value=300)
        perform(plc, 'processed', verdict=1)
        self.assertEqual(writes_seen, [1])
        self.assertEqual([e['Kind'] for e in events(plc)], [1,2,3])
        self.assertTrue(all(e['PartUid'] == identity for e in events(plc)))
        self.assertFalse(plc.tags[part.tag(APP)]['Present'])
        view = part.project(APP, plc.tags[part.tag(APP)])
        self.assertEqual(view['Part/Result/Records[1]/Value'], .3)
        self.assertTrue(view['Part/Result/Records[1]/InTol'])
        self.assertEqual(plc.tags['FRK_Press_Unit']['GoodCount'], 1)
        perform(plc, 'processed', verdict=1)
        self.assertEqual(carrier['Writes'], 1)
        self.assertEqual(len(events(plc)), 3)

    def test_rework_entry_keeps_identity_and_new_part_clears_old_result(self):
        plc = setup()
        perform(plc, 'receive')
        first = part.uid(plc.tags[part.tag(APP)]['Uid'])
        perform(plc, 'start')
        perform(plc, 'receive')  # a handling loop is still the same part
        perform(plc, 'start')
        self.assertEqual([e['Kind'] for e in events(plc)], [1,2,2])
        self.assertEqual(plc.tags[part.carrier_tag(APP)]['Serial'], 1)
        perform(plc, 'record', record=1, value=49)
        self.assertFalse(part.project(APP, plc.tags[part.tag(APP)])['Part/Result/Records[1]/InTol'])
        perform(plc, 'processed', verdict=3)
        self.assertEqual(plc.tags['FRK_Press_Unit']['ReworkCount'], 1)
        perform(plc, 'receive')
        self.assertNotEqual(part.uid(plc.tags[part.tag(APP)]['Uid']), first)
        self.assertEqual(plc.tags[part.tag(APP)]['RecordCount'], 0)
        self.assertEqual(plc.tags[part.tag(APP)]['Verdict'], 0)

    def test_nok_counts_once_after_commit_and_nonpart_event_does_not_leak_uid(self):
        plc = setup()
        perform(plc, 'receive')
        perform(plc, 'processed', verdict=2, reason=2001)
        self.assertEqual(plc.tags['FRK_Press_Unit']['ScrapCount'], 1)
        self.assertEqual(plc.tags['FRK_Press_Unit']['GoodCount'], 0)
        self.assertEqual([e['Kind'] for e in events(plc)], [1,3,10])
        self.assertEqual(events(plc)[-1]['PartUid'], '')
        self.assertEqual(events(plc)[1]['ReasonCode'], 2001)

    def test_read_failure_reaches_consumer_without_received_event(self):
        for field, value in [('ProviderKind', 2), ('ProviderIdx', 0), ('SchemaVersion', 2),
                             ('Serial', host.LIMIT), ('Serial', -1)]:
            with self.subTest(field=field, value=value):
                plc = setup()
                plc.tags[part.carrier_tag(APP)][field] = value
                perform(plc, 'receive')
                self.assertEqual(plc.tags['FRK_Press_Unit']['ErrorID'], 2020)
                self.assertEqual(events(plc), [])

    def test_uid_mismatch_prevents_result_assignment_to_wrong_part(self):
        plc = setup()
        perform(plc, 'receive')
        plc.tags[part.tag(APP)]['Uid'][0] = ord('X')
        perform(plc, 'processed', verdict=1)
        self.assertEqual(plc.tags['FRK_Press_Unit']['ErrorID'], 2022)
        self.assertEqual(plc.tags[part.carrier_tag(APP)]['Writes'], 0)
        self.assertEqual([e['Kind'] for e in events(plc)], [1])

    def test_signed_epoch_hex_and_serial_exhaustion_do_not_reuse_identity(self):
        for high,low in [(-2**31,-2**31), (-1,-1), (2**31-1,2**31-1), (0,1)]:
            with self.subTest(high=high,low=low):
                plc = setup()
                plc.tags[host.tag(APP)].update(EpochLow=low, EpochHigh=high)
                perform(plc, 'receive')
                expected = f'OFFLINE-PRESS-{high & 0xffffffff:08X}{low & 0xffffffff:08X}00000001'
                self.assertEqual(part.uid(plc.tags[part.tag(APP)]['Uid']), expected)
        plc = setup()
        plc.tags[part.carrier_tag(APP)]['Serial'] = host.LIMIT-1
        perform(plc, 'receive')
        perform(plc, 'processed', verdict=1)
        perform(plc, 'receive')
        self.assertEqual(plc.tags['FRK_Press_Unit']['ErrorID'], 2020)
        self.assertEqual(len(events(plc)), 2)

    def test_unsupported_operation_fails_closed(self):
        plc = setup()
        plc.run(part.call(APP, 'receive').replace(',1,0,0,0,0)', ',99,0,0,0,0)') + ';')
        self.assertEqual(plc.tags['FRK_Press_Unit']['ErrorID'], 2023)

    def test_write_failure_never_emits_processed_or_counts_and_fault_aborts_once(self):
        plc = setup()
        perform(plc, 'receive')
        plc.tags[part.carrier_tag(APP)]['ProviderIdx'] = 0
        perform(plc, 'processed', verdict=1)
        self.assertEqual(plc.tags['FRK_Press_Unit']['ErrorID'], 2021)
        self.assertEqual(plc.tags['FRK_Press_Unit']['GoodCount'], 0)
        self.assertEqual(plc.tags[part.carrier_tag(APP)]['Writes'], 0)
        plc.run('\n'.join(part.finish_scan(APP)))
        plc.run('\n'.join(part.finish_scan(APP)))
        self.assertEqual([e['Kind'] for e in events(plc)], [1,4])
        self.assertEqual(events(plc)[-1]['ReasonCode'], 2021)
        self.assertFalse(plc.tags[part.tag(APP)]['Present'])

    def test_nok_missing_reason_invalid_verdict_counter_or_record_exhaustion_fault(self):
        for kwargs in [dict(verdict=2), dict(verdict=4)]:
            plc = setup()
            perform(plc, 'receive')
            perform(plc, 'processed', **kwargs)
            self.assertEqual(plc.tags['FRK_Press_Unit']['ErrorID'], 2023)
            self.assertEqual(plc.tags[part.carrier_tag(APP)]['Writes'], 0)
        plc = setup()
        perform(plc, 'receive')
        plc.tags['FRK_Press_Unit']['GoodCount'] = host.LIMIT
        perform(plc, 'processed', verdict=1)
        self.assertEqual(plc.tags['FRK_Press_Unit']['ErrorID'], 2023)
        plc = setup()
        perform(plc, 'receive')
        for _ in range(APP.part_carrier.result_capacity):
            perform(plc, 'record', record=1, value=300)
        perform(plc, 'record', record=1, value=300)
        self.assertEqual(plc.tags['FRK_Press_Unit']['ErrorID'], 2023)
        self.assertEqual(plc.tags[part.tag(APP)]['RecordCount'], 4)

    def test_mode_reset_abort_release_present_part_before_state_clear(self):
        for trigger in ('ModeRequest', 'ResetRequest', 'AbortRequest'):
            plc = setup()
            perform(plc, 'receive')
            u = plc.tags['FRK_Press_Unit']
            # Bind AOI parameters to the same actual stores.
            plc.tags.update(Ctx=u, Chart=plc.tags['FRK_Press_Chart'],
                Cfg=plc.tags['FRK_Press_ParCfg'], Part=plc.tags[part.tag(APP)],
                Carrier=plc.tags[part.carrier_tag(APP)], HostEvents=plc.tags[host.tag(APP)], Scan=1)
            for m in APP.modules:
                plc.tags['Ctx'+m.name] = st.structure(gen.module_members(m))
                plc.tags['Ctx'+m.name]['ModuleScan'] = 1
            for name in APP.sim_inputs:
                plc.tags[gen.sim_param(APP, name)] = 0
            u[trigger] = 1
            plc.run('\n'.join(gen.unit_logic(APP)))
            plc.run('\n'.join(gen.unit_logic(APP)))
            self.assertEqual([e['Kind'] for e in events(plc)].count(4), 1)
            self.assertFalse(plc.tags[part.tag(APP)]['Present'])

    def test_revision_wrap_is_even_and_bounded(self):
        plc = setup()
        plc.tags[part.tag(APP)]['DataRevision'] = host.LIMIT-1
        perform(plc, 'receive')
        self.assertEqual(plc.tags[part.tag(APP)]['DataRevision'], 2)
        part.project(APP, plc.tags[part.tag(APP)])


class RenditionsAndTransport(unittest.TestCase):
    def test_handled_device_failure_is_one_nok_and_never_a_good_part(self):
        import test_fraktal_ab_rendition_cycle as cycle
        chain = next(c for c in APP.chains if c.name == 'AUTO')
        for language in chain.renditions:
            with self.subTest(language=language), patch.multiple(cycle, APP=APP, AUTO=chain,
                ORDER=gen.ordered_steps(APP), NAMES=gen.Names(APP, in_aoi=False)):
                bench = cycle.Press(language)
                stores = setup()
                for key in (part.tag(APP), part.carrier_tag(APP), host.tag(APP)):
                    bench.plc.tags[key] = stores.tags[key]
                bench.plc.calls.update(stores.calls)
                returned = False
                for _ in range(1000):
                    # Stop the ram's simulated plant only during the press.
                    bench.ctx('PressRam')['FaultRequest'] = int(bench.step() == 200)
                    if bench.step() == 210:
                        bench.plc.tags['FRK_Press_Unit']['DecisionAnswer'] = 1
                    if bench.step() == 999:
                        returned = True
                    bench.scan()
                    if returned and bench.step() == 100:
                        break
                else:
                    self.fail(f'{language} NOK cycle did not close at {bench.step()}')
                u = bench.plc.tags['FRK_Press_Unit']
                self.assertEqual((u['GoodCount'], u['ScrapCount']), (0,1))
                self.assertEqual([e['Kind'] for e in events(bench.plc)], [1,2,3,10])
                self.assertEqual(events(bench.plc)[2]['Verdict'], 2)
                self.assertNotEqual(events(bench.plc)[2]['ReasonCode'], 0)
                self.assertEqual(bench.plc.tags[part.carrier_tag(APP)]['Writes'], 1)

    def test_whole_production_cycle_has_identical_trace_in_every_language(self):
        import test_fraktal_ab_rendition_cycle as cycle
        chain = next(c for c in APP.chains if c.name == 'AUTO')
        for language in chain.renditions:
            with self.subTest(language=language), patch.multiple(cycle, APP=APP, AUTO=chain,
                ORDER=gen.ordered_steps(APP), NAMES=gen.Names(APP, in_aoi=False)):
                bench = cycle.Press(language)
                stores = setup()
                for key in (part.tag(APP), part.carrier_tag(APP), host.tag(APP)):
                    bench.plc.tags[key] = stores.tags[key]
                bench.plc.calls.update(stores.calls)
                outcome = bench.one_cycle()
                self.assertEqual(outcome['errors'], dict.fromkeys(cycle.CYLINDERS, 0))
                self.assertEqual([e['Kind'] for e in events(bench.plc)], [1,2,3])
                self.assertEqual(bench.plc.tags['FRK_Press_Unit']['GoodCount'], 1)
                self.assertEqual(bench.plc.tags[part.carrier_tag(APP)]['Writes'], 1)
                self.assertEqual(bench.plc.tags[part.carrier_tag(APP)]['LastRecordValue'][0], 300)
                self.assertEqual(bench.plc.tags[part.carrier_tag(APP)]['LastRecordValue'][1], 100)
                self.assertEqual(bench.plc.tags[part.carrier_tag(APP)]['LastRecordCount'], 2)

    def test_generic_projection_publishes_part_and_refuses_missing_snapshot(self):
        import test_fraktal_ab_projection as helpers
        plc = setup()
        perform(plc, 'receive')
        perform(plc, 'record', record=1, value=300)
        perform(plc, 'processed', verdict=1)
        with patch.object(projection, 'APP', APP), patch.object(helpers, 'APP', APP):
            header = helpers.good_header(SchemaMajor=manifest.schema_major(APP))
            args = (header, manifest.content(APP), helpers.unit_values(), helpers.contexts())
            kwargs = dict(host_state=host.decode(APP, plc.tags[host.tag(APP)]),
                          part_state=plc.tags[part.tag(APP)])
            doc = projection.project(*args, **kwargs)
            self.assertEqual(doc['values']['Press/Part/Result/Verdict'], 1)
            self.assertEqual(doc['values']['Press/Part/Result/Records[1]/Value'], .3)
            self.assertEqual(doc['values']['Press/Part/Uid'], events(plc)[0]['PartUid'])
            with self.assertRaises(projection.ReadFailed):
                projection.project(*args, **{**kwargs, 'part_state':None})

    def test_all_three_renditions_call_one_service_and_failure_does_not_advance(self):
        chain = next(c for c in APP.chains if c.name == 'AUTO')
        step = next(s for s in chain.steps if s.number == 105)
        index = gen.ordered_steps(APP).index(step.number)
        for rendition in ('ST','SFC','LD'):
            for fails in (False, True):
                with self.subTest(rendition=rendition, fails=fails):
                    plc = setup()
                    u = plc.tags['FRK_Press_Unit']
                    u.update(Step=105, PrevStep=105, Running=1)
                    if fails:
                        plc.tags[part.carrier_tag(APP)]['ProviderIdx'] = 0
                    names = gen.Names(APP, in_aoi=False)
                    if rendition == 'LD':
                        plc.tags[gen.ld_advanced_tag(APP)] = 0
                        ld.run_rung(plc, gen.ld_step_rung(APP, chain, step, index, names))
                    elif rendition == 'SFC':
                        plc.run('\n'.join(gen.sfc_action_logic(APP, chain, step, index, names)))
                        plc.tags['Transition'] = 0
                        plc.run('Transition := ' + gen.sfc_condition(APP, step, 'A', names) + ';')
                        self.assertEqual(bool(plc.tags['Transition']), not fails)
                    else:
                        plc.run('\n'.join(gen.step_logic(APP, chain, step, index, names)[1:]))
                    self.assertEqual(u['Error'], int(fails))
                    if rendition != 'SFC':
                        self.assertEqual(u['Step'], 105 if fails else 110)

    def test_scaled_values_and_uid_fail_closed(self):
        plc = setup()
        perform(plc, 'receive')
        raw = plc.tags[part.tag(APP)]
        for changes in [dict(SchemaVersion=2), dict(DataRevision=1), dict(Present=2),
                        dict(RecordCount=5), dict(Uid=[-1]*64), dict(Uid=[0]*64)]:
            with self.subTest(changes=changes), self.assertRaises(part.PartBad):
                part.project(APP, {**raw, **changes})
        corrupt = copy.deepcopy(plc.tags[host.tag(APP)])
        corrupt['Uid'][0] = 0
        with self.assertRaises(host.HostEventsBad):
            host.decode(APP, corrupt)

    def test_part_coherent_read_retries_and_rejects_failed_acquisition(self):
        raw = setup().tags[part.tag(APP)]
        meta = {k:raw[k] for k in ('SchemaVersion','DataRevision')}
        with patch('fraktal_ab_press_execute.read_layout', side_effect=[meta, raw, {**meta,'DataRevision':2}, meta, raw, meta]) as reader:
            self.assertEqual(part.read(object(), APP), raw)
            self.assertEqual(reader.call_count, 6)
        with patch('fraktal_ab_press_execute.read_layout', return_value=None), self.assertRaises(part.PartBad):
            part.read(object(), APP)
        with patch('fraktal_ab_press_execute.read_layout', side_effect=[meta, raw, {**meta,'DataRevision':2}]*3), self.assertRaises(part.PartBad):
            part.read(object(), APP)

    def test_old_host_layout_is_versioned_and_hash_covers_provider_and_measurements(self):
        old = old_fixture.application()
        self.assertEqual(host.schema(old), 1)
        self.assertEqual(host.schema(APP), 2)
        self.assertNotEqual(host.type_name(old), host.type_name(APP))
        altered = replace(APP, part_carrier=replace(APP.part_carrier, namespace='OTHER'))
        self.assertNotEqual(manifest.content_hash(APP), manifest.content_hash(altered))
        altered = replace(APP, part_carrier=replace(APP.part_carrier, records=(
            replace(APP.part_carrier.records[0], scale=100),)))
        self.assertNotEqual(manifest.content_hash(APP), manifest.content_hash(altered))

    def test_invalid_declarations_and_duplicate_counter_authority_are_refused(self):
        for c in [object(), replace(APP.part_carrier, namespace=''),
                  replace(APP.part_carrier, result_capacity=0),
                  replace(APP.part_carrier, records=(replace(APP.part_carrier.records[0], scale=0),))]:
            self.assertTrue(part.validate(replace(APP, part_carrier=c)))
        self.assertTrue(part.validate(replace(APP, host_event_capacity=0)))
        self.assertTrue(part.validate(replace(APP, part_carrier=None)))
        self.assertTrue(part.validate(replace(APP, reasons={})))
        chain = APP.chains[0]
        step = next(s for s in chain.steps if s.part_action == 'processed')
        def invalid(**changes):
            replaced = replace(step, **changes)
            return replace(APP, chains=(replace(chain, steps=tuple(replaced if s == step else s for s in chain.steps)), *APP.chains[1:]))
        for changes in [dict(part_verdict=2,part_reason=0), dict(action=decl.AWAIT),
                        dict(part_action='unknown'), dict(marks=('Ctx.GoodCount := Ctx.GoodCount + 1',))]:
            self.assertTrue(part.validate(invalid(**changes)))


if __name__ == '__main__':
    unittest.main()
