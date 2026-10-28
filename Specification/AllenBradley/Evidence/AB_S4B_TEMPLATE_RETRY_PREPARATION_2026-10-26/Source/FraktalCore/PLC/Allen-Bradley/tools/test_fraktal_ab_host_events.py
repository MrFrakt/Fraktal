import copy
import dataclasses
import json
import struct
import tempfile
import unittest
import io
from contextlib import redirect_stderr
from unittest.mock import patch
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_host_demo as fixture
import fraktal_ab_host_events as host
import fraktal_ab_ld_model as ld
import fraktal_ab_manifest as manifest
import fraktal_ab_press_demo as press
import fraktal_ab_st_model as st
import fraktal_ab_counting as counting


APP = fixture.application()
CODES = [m.code for m in APP.models]


def ring(app=APP):
    value = st.structure(host.members(app))
    value.update(NowDate=20261018, NowTime=123456789, NowSynchronized=0,
                 EpochLow=12345, EpochHigh=67890)
    return value


def callback(app):
    # Execute the actual generated AOI body, with its passed arguments. The
    # callback binds parameters; it contains no ring or lifecycle algorithm.
    def run(plc, args):
        self = st.Controller(dict(Ring=plc.read(args[1]), Slot=0,
            **{name: plc.eval(arg) for name, arg in zip(
                ('Kind', 'ModelOrdinal', 'EventValue', 'Verdict', 'Reason'), args[2:])}))
        self.run('\n'.join(host.emit_logic(app)))
    return run


def append(raw, kind='MODE_CHANGED', value=0, model=0, reason=0, app=APP):
    plc = st.Controller({host.tag(app): raw}, calls={host.emitter_name(app): callback(app)})
    plc.run(host.call(app, kind, value=str(value), model=str(model), reason=reason) + ';')


def packed(raw, app=APP):
    values = []
    for member in host.members(app):
        value = raw[member.name]
        values.extend(value if member.dimension else [value])
    return struct.pack('<' + 'i'*len(values), *values)


class Publisher(unittest.TestCase):
    def test_publisher_epoch_initialization_is_bracketed_and_clock_runs_once_per_scan(self):
        raw = st.structure(host.members(APP))
        tags = {host.tag(APP): raw, 'FRK_Press_ScanCount': 0}
        for name, dimension in gen.clock_tags(APP).items():
            tags[name] = [0]*dimension if dimension else 0
        calls = []
        standard = st.gsv({('TimeSynchronize', None, 'IsSynchronized'): 1},
                          now=lambda: (2026,10,18,1,2,3,456000))
        def gsv(plc, args):
            attribute = args[2][1][0][1]
            calls.append(attribute)
            if attribute == 'CurrentValue':
                self.assertEqual(raw['DataRevision'], 1)
                for offset, value in enumerate((12345,67890)):
                    holder, key = plc.element(args[3], offset)
                    holder[key] = value
            else:
                standard(plc, args)
        plc = st.Controller(tags, calls={'GSV': gsv})
        plc.run('\n'.join(host.start_scan(APP)))
        self.assertEqual(raw['DataRevision'], 2)
        self.assertEqual(raw['NowSynchronized'], 1)
        host.decode(APP, raw)
        tags['FRK_Press_ScanCount'] = 1
        plc.run('\n'.join(host.start_scan(APP)))
        self.assertEqual(calls.count('CurrentValue'), 1)
        self.assertEqual(calls.count('DateTime'), 2)

    def test_host_kind_and_nok_verdict_ordinals_match_the_core_duts(self):
        from test_fraktal_ab_core_ordinals import core_enum
        self.assertEqual(host.KINDS, {k:v for k,v in core_enum('E_HostEventKind').items() if k != 'NONE'})
        self.assertEqual(core_enum('E_Verdict')['NOK'], 2)

    def test_mode_change_and_accepted_start_emit_from_the_unit_owner_once(self):
        raw = ring()
        tags = dict(Ctx=st.structure(gen.unit_context_members(APP)),
                    Chart=st.structure(gen.chart_members(APP)),
                    Cfg=st.structure(APP.records[0].members), HostEvents=raw, Scan=1)
        for module in APP.modules:
            tags['Ctx' + module.name] = st.structure(gen.module_members(module))
            tags['Ctx' + module.name]['ModuleScan'] = 1
        for name in APP.sim_inputs:
            tags[gen.sim_param(APP, name)] = 0
        tags['Ctx'].update(ModeRequest=3, RunRequest=1, ModelRequest=1)
        tags['CycleVerdict'] = st.structure(counting.members())
        plc = st.Controller(tags, calls={host.emitter_name(APP): callback(APP)})
        plc.run('\n'.join(gen.unit_logic(APP)))
        batch = host.decode(APP, raw, CODES)
        self.assertEqual([e['Kind'] for e in batch['events']], [9, 5])
        self.assertEqual([e['Value'] for e in batch['events']], ['3', CODES[0]])
        plc.run('\n'.join(gen.unit_logic(APP)))
        self.assertEqual(raw['Count'], 2)

    def test_new_fixture_is_valid_and_legacy_output_is_opt_in(self):
        self.assertEqual(decl.validate(APP), [])
        legacy = press.application()
        self.assertNotIn('HostEmitter', gen.aoi_definitions(legacy))
        self.assertEqual(manifest.content(legacy)['Roots'][0]['HostEventId'], 0)
        self.assertEqual(manifest.content(APP)['Roots'][0]['HostEventId'], 1)
        self.assertNotEqual(gen.unit_aoi_name(APP), gen.unit_aoi_name(legacy))
        self.assertNotEqual(gen.unit_aoi_name(APP), gen.unit_aoi_name(dataclasses.replace(APP, host_event_capacity=16)))

    def test_capacity_and_unattributed_nok_are_refused(self):
        for bound in (-1, 65, True, 2.5):
            self.assertTrue(host.validate(dataclasses.replace(APP, host_event_capacity=bound)))
        self.assertTrue(host.validate(dataclasses.replace(press.application(), host_event_capacity=8)))

    def test_fast_events_survive_without_a_poll(self):
        raw = ring()
        for mode in [1, 2, 3, 0]:
            append(raw, value=mode)
        batch = host.decode(APP, raw, CODES)
        self.assertEqual([e['Value'] for e in batch['events']], ['1', '2', '3', '0'])
        self.assertEqual([e['Sequence'] for e in batch['events']], [1, 2, 3, 4])
        self.assertTrue(all(not e['TimeSynchronized'] and e['PartUid'] == '' for e in batch['events']))

    def test_wrap_keeps_the_last_capacity_events_and_announces_loss(self):
        raw = ring()
        for _ in range(12):
            append(raw)
        batch = host.decode(APP, raw, CODES)
        self.assertEqual([e['Sequence'] for e in batch['events']], list(range(5, 13)))
        self.assertEqual(raw['Wrapped'], 1)
        captured = []
        host.Cursor(APP.name).deliver(batch, lambda r: captured.append(r) or True)
        self.assertEqual(captured[0]['kind'], 'dataLoss')
        self.assertEqual((captured[0]['firstMissing'], captured[0]['lastMissing']), (1, 4))

    def test_full_ring_is_not_wrapped_until_the_first_overwrite(self):
        raw = ring()
        for _ in range(APP.host_event_capacity):
            append(raw)
        self.assertEqual(raw['Wrapped'], 0)
        host.decode(APP, raw, CODES)

    def test_single_slot_and_revision_wrap_are_bounded(self):
        app = dataclasses.replace(APP, host_event_capacity=1)
        raw = ring(app)
        raw['DataRevision'] = host.LIMIT - 1
        append(raw, app=app)
        self.assertEqual(raw['DataRevision'], 2)
        append(raw, value=1, app=app)
        self.assertEqual(host.decode(app, raw)['events'][0]['Sequence'], 2)
        self.assertEqual((raw['Head'], raw['Count'], raw['Wrapped']), (1, 1, 1))

    def test_sequence_exhaustion_never_wraps_to_a_reused_key(self):
        raw = ring()
        raw['NewestSequence'] = host.LIMIT
        append(raw)
        self.assertEqual((raw['NewestSequence'], raw['Failed']), (host.LIMIT, 1))
        with self.assertRaises(host.HostEventsBad):
            host.decode(APP, raw)

    def test_one_nok_count_emits_one_reason_coded_record_in_st_and_ld(self):
        step = next(s for c in APP.chains for s in c.steps if s.nok_reason)
        outcomes = []
        for language in ('ST', 'LD'):
            raw = ring()
            names = gen.Names(APP, in_aoi=False)
            plc = st.Controller({host.tag(APP): raw, names.unit: dict(ScrapCount=0, ReportedReason=12021),
                                 counting.tag(APP): st.structure(counting.members())},
                                calls={host.emitter_name(APP): callback(APP)})
            if language == 'ST':
                plc.run('\n'.join(gen._st_marks(step, names)))
            else:
                ld.run_rung(plc, ''.join(gen._ld_marks(step, names)) + ';')
            self.assertEqual(plc.tags[names.unit]['ScrapCount'], 1)
            outcomes.append(host.decode(APP, raw)['events'])
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual((outcomes[0][0]['Kind'], outcomes[0][0]['Verdict'],
                          outcomes[0][0]['ReasonCode']), (10, 2, 12021))

    def test_sfc_action_uses_the_same_single_nok_owner(self):
        step = next(s for c in APP.chains for s in c.steps if s.nok_reason)
        chain = next(c for c in APP.chains if step in c.steps)
        body = '\n'.join(gen.sfc_action_logic(APP, chain, step, gen.ordered_steps(APP).index(step.number), gen.Names(APP, in_aoi=False)))
        self.assertEqual(body.count(host.emitter_name(APP) + '('), 1)

    def test_modeled_aoi_on_false_ladder_power_does_not_run(self):
        calls = []
        plc = st.Controller({}, calls={'FRK_HostEmit': lambda *args: calls.append(args)})
        ld.run_rung(plc, 'EQU(1,0)FRK_HostEmit(0);')
        self.assertEqual(calls, [])
        ld.run_rung(plc, 'EQU(1,1)FRK_HostEmit(0);')
        self.assertEqual(len(calls), 1)

    def test_changeover_completion_waits_for_success_and_emits_once(self):
        raw, u = ring(), dict(Mode=3, Complete=0, ModelOrdinal=2)
        plc = st.Controller({host.tag(APP): raw, 'FRK_Press_Unit': u},
                            calls={host.emitter_name(APP): callback(APP)})
        logic = '\n'.join(host.finish_scan(APP))
        plc.run(logic)
        self.assertEqual(raw['Count'], 0)
        u['Complete'] = 1
        for _ in range(3):
            plc.run(logic)
        event = host.decode(APP, raw, CODES)['events'][0]
        self.assertEqual((raw['Count'], event['Kind'], event['Value']), (1, 6, CODES[1]))

    def test_emitted_surface_is_read_only_and_capacity_is_declared_once(self):
        tags = ET.fromstring(gen.controller_tags(APP))
        self.assertEqual(tags.find(f"Tag[@Name='{host.tag(APP)}']").get('ExternalAccess'), 'Read Only')
        self.assertEqual(tags.find(f"Tag[@Name='{host.instance_tag(APP)}']").get('ExternalAccess'), 'None')
        fields = manifest.content(APP)['Fields']
        keys = {r['NumericKey']:r['PortableKey'] for r in manifest.content(APP)['Localization']}
        self.assertTrue(any(keys[r['PathKey']] == 'HostEvents.Sequence' and r['Dimensions'] == 8 for r in fields))
        self.assertFalse(any(keys[r['PathKey']] == 'HostEvents.CompleteSeen' for r in fields))


class Acquisition(unittest.TestCase):
    def test_start_before_model_selection_is_valid_but_completion_without_model_is_bad(self):
        raw = ring(); append(raw, 'CHANGEOVER_STARTED')
        self.assertEqual(host.decode(APP, raw)['events'][0]['Value'], '')
        raw = ring(); append(raw, 'CHANGEOVER_DONE')
        with self.assertRaises(host.HostEventsBad):
            host.decode(APP, raw)

    def test_active_record_corruption_never_becomes_a_shorter_good_stream(self):
        for change in [lambda r:r.update(Count=9), lambda r:r.update(Head=9),
                       lambda r:r['Sequence'].__setitem__(0, 0),
                       lambda r:r['Kind'].__setitem__(0, 123),
                       lambda r:r['Date'].__setitem__(0, 20260230),
                       lambda r:r['TimeSynchronized'].__setitem__(0, 2),
                       lambda r:r.update(DataRevision=1),
                       lambda r:r['Sequence'].pop()]:
            with self.subTest(change=change):
                raw = ring(); append(raw); change(raw)
                with self.assertRaises(host.HostEventsBad):
                    host.decode(APP, raw)

    def test_negative_control_nok_without_reason_is_bad(self):
        raw = ring()
        append(raw, 'NOK')
        self.assertEqual(raw['Failed'], 1)

    def test_model_reference_must_resolve_without_inventing_a_code(self):
        raw = ring(); append(raw, 'CHANGEOVER_STARTED', model=2)
        with self.assertRaises(host.HostEventsBad):
            host.decode(APP, raw, ())

    def test_coherent_read_retries_a_moving_revision_and_preserves_every_event(self):
        old, current = ring(), ring()
        append(current)
        sequence = [packed(old), packed(current), packed(current)] + [packed(current)]*3
        class Reader:
            def Read(self, name):
                return SimpleNamespace(Status='Success', Value=sequence.pop(0))
        batch = host.read(Reader(), APP)
        self.assertEqual(len(batch['events']), 1)
        self.assertEqual(sequence, [])

    def test_read_outage_and_continuously_torn_data_are_bad(self):
        class Reader:
            def Read(self, name):
                return SimpleNamespace(Status='Timeout', Value=None)
        with self.assertRaises(host.HostEventsBad):
            host.read(Reader(), APP)
        raw = ring(); raw['DataRevision'] = 1
        class Busy:
            def Read(self, name):
                return SimpleNamespace(Status='Success', Value=packed(raw))
        with self.assertRaises(host.HostEventsBad):
            host.read(Busy(), APP)

    def test_projection_keeps_physical_slots_and_no_unproduced_part_events(self):
        raw = ring()
        for _ in range(10): append(raw)
        values = host.project(host.decode(APP, raw))
        self.assertEqual(values['HostEvents/RingHead'], 2)
        self.assertEqual(values['HostEvents/Ring[3]/Sequence'], 3)
        self.assertEqual(values['HostEvents/Ring[2]/Sequence'], 10)
        self.assertEqual(values['HostEvents/Ring[2]/PartUid'], '')


class Delivery(unittest.TestCase):
    def batch(self, count=3):
        raw = ring()
        for _ in range(count): append(raw)
        return host.decode(APP, raw)

    def test_reconnect_reads_the_acknowledged_cursor_without_duplicate_delivery(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'sink.json'
            sent = []
            sink = lambda item: sent.append(item) or True
            host.Cursor(APP.name, path).deliver(self.batch(), sink)
            host.Cursor(APP.name, path).deliver(self.batch(), sink)
            self.assertEqual(len(sent), 3)
            self.assertEqual(json.loads(path.read_text())['sequence'], 3)

    def test_failed_sink_does_not_acknowledge_the_failed_record(self):
        cursor = host.Cursor(APP.name)
        captured = []
        def sink(item):
            captured.append(item)
            return item['event']['Sequence'] < 2
        self.assertFalse(cursor.deliver(self.batch(), sink))
        self.assertEqual(cursor.state['sequence'], 1)
        sent = []
        cursor.deliver(self.batch(), lambda r: sent.append(r) or True)
        self.assertEqual([r['event']['Sequence'] for r in sent], [2, 3])

    def test_rejected_loss_notice_does_not_skip_to_the_oldest_available_event(self):
        cursor = host.Cursor(APP.name)
        self.assertFalse(cursor.deliver(self.batch(12), lambda r: False))
        self.assertEqual(cursor.state['sequence'], 0)

    def test_new_publisher_epoch_is_explicit_and_keyed_separately(self):
        cursor = host.Cursor(APP.name)
        cursor.deliver(self.batch(), lambda r: True)
        changed = self.batch(1); changed['metadata']['EpochLow'] += 1
        sent = []
        cursor.deliver(changed, lambda r: sent.append(r) or True)
        self.assertEqual(sent[0]['reason'], 'publisherEpochChanged')
        self.assertEqual(sent[1]['event']['Sequence'], 1)

    def test_corrupt_or_wrong_station_cursor_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'cursor.json'
            path.write_text(json.dumps(dict(schema=1, station='Other', epoch=[1,2], sequence=3)))
            with self.assertRaises(host.HostEventsBad):
                host.Cursor(APP.name, path)

    def test_regressed_sequence_in_same_epoch_is_bad(self):
        cursor = host.Cursor(APP.name)
        cursor.deliver(self.batch(), lambda r: True)
        with self.assertRaises(host.HostEventsBad):
            cursor.deliver(self.batch(1), lambda r: True)

    def test_second_cursor_instance_refreshes_ack_before_delivery(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'sink.json'
            first, second = host.Cursor(APP.name, path), host.Cursor(APP.name, path)
            first.deliver(self.batch(), lambda r: True)
            sent = []
            second.deliver(self.batch(), lambda r: sent.append(r) or True)
            self.assertEqual(sent, [])
            self.assertFalse(path.with_name(path.name + '.lock').exists())

    def test_active_writer_or_stale_lock_is_never_deleted_by_another_cursor(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'sink.json'
            lock = path.with_name(path.name + '.lock')
            lock.write_text('busy')
            with self.assertRaises(FileExistsError):
                host.Cursor(APP.name, path).deliver(self.batch(), lambda r: True)
            self.assertEqual(lock.read_text(), 'busy')

    def test_malformed_later_record_is_rejected_before_any_acknowledgement(self):
        for field, value in [('StationPath', 'Other'), ('Sequence', 42)]:
            batch = self.batch()
            batch['events'][-1][field] = value
            sent = []
            with self.assertRaises(host.HostEventsBad):
                host.Cursor(APP.name).deliver(batch, lambda r: sent.append(r) or True)
            self.assertEqual(sent, [])

    def test_cursor_is_scoped_to_the_controller_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'sink.json'
            host.Cursor(APP.name, path, source='serial1').deliver(self.batch(), lambda r: True)
            with self.assertRaises(host.HostEventsBad):
                host.Cursor(APP.name, path, source='serial2')


class CommandGuards(unittest.TestCase):
    def test_disabled_profile_refuses_before_connecting_or_creating_files(self):
        import fraktal_ab_station as station
        with tempfile.TemporaryDirectory() as folder, patch.object(station, 'application', return_value=press.application()):
            cursor, output = Path(folder)/'cursor', Path(folder)/'events'
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as failure:
                host.main(['127.0.0.1', '--expect-serial', '1234', '--cursor', str(cursor), '--output', str(output)])
            self.assertEqual(failure.exception.code, 2)
            self.assertFalse(cursor.exists() or output.exists())

    def test_cursor_cannot_overwrite_the_sink(self):
        import fraktal_ab_station as station
        with tempfile.TemporaryDirectory() as folder, patch.object(station, 'application', return_value=APP):
            path = Path(folder)/'events'
            path.write_text('kept')
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as failure:
                host.main(['127.0.0.1', '--expect-serial', '1234', '--cursor', str(path), '--output', str(path)])
            self.assertEqual(failure.exception.code, 2)
            self.assertEqual(path.read_text(), 'kept')

    def test_cursor_companions_and_sqlite_sidecars_cannot_overlap(self):
        import fraktal_ab_station as station
        with tempfile.TemporaryDirectory() as folder, patch.object(station, 'application', return_value=APP):
            path = Path(folder)/'events'
            cases = [('--output', path, Path(str(path) + '.guard')),
                     ('--output', path, Path(str(path) + '.lock')),
                     ('--sqlite-output', path, path),
                     ('--sqlite-output', Path(str(path) + '-journal'), path),
                     ('--sqlite-output', Path(str(path) + '-wal'), path),
                     ('--sqlite-output', Path(str(path) + '-shm'), path)]
            for option, cursor, output in cases:
                with self.subTest(option=option, cursor=cursor), redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as failure:
                        host.main(['127.0.0.1', '--expect-serial', '1234', '--cursor', str(cursor),
                                   option, str(output)])
                    self.assertEqual(failure.exception.code, 2)
            self.assertEqual(list(Path(folder).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
