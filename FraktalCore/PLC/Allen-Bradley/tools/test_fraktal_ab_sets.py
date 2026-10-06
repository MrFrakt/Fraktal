"""Execute the emitted transaction and the portable host store, offline."""
import copy
import dataclasses
import json
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_gateway as gw
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as mf
import fraktal_ab_set_broker as broker
import fraktal_ab_sets as sets
import fraktal_ab_access as access
import fraktal_ab_st_model as st
import fraktal_ab_station_template as template
from test_fraktal_ab_capture import APP, controller as capture_controller, initial


def controller(app=APP):
    c = capture_controller(app)
    c.tags[gen.config_persist_tag(app)] = initial(gen.config_persist_members())
    c.tags[mb.request_tag_name(app)]['ConfigSet'] = initial(sets.request_members())
    for name, kind, length, _ in mb.REQUEST_MEMBERS:
        if name not in c.tags[mb.request_tag_name(app)]:
            c.tags[mb.request_tag_name(app)][name] = {'LEN': 0, 'DATA': [0] * length} if kind == mb.STRING_MEMBER else 0
    c.tags[mb.request_tag_name(app)].update(Sequence=1, Kind=mb.LOAD_CONFIG_SET, BoolValue=0)
    c.tags[mb.response_tag_name(app)]['AckSequence'] = 0
    c.tags[sets.staged_tag(app)] = initial(sets.request_members())
    c.tags[f'FRK_{app.name}_HmiLastSequence'] = 0
    from fraktal_ab_st_model import cps_structure
    c.calls['CPS'] = cps_structure
    for name in sets.scratch_names(app):
        c.tags[name] = 0
    return c


def document(app=APP, name='commissioning', kind=1):
    records = [{'scope': app.name, 'key': m.write_key, 'rev': mf.config_revision(app),
                'kind': kind, 'type': sets.value_type(m), 'value': ('TRUE' if m.initial else 'FALSE') if m.kind == 'boolean' else str(m.initial)}
               for _ordinal, r, m in gen.editable_values(app) if sets.config_kind(r) == kind]
    return [{'set': name, 'root': app.name, 'schema': 1, 'configRev': mf.config_revision(app),
             'kind': kind, 'model': app.default_model if kind == 0 else '',
             'records': len(records), 'created': 1790899200, 'clock': 0}, *records]


def run(c, app=APP, doc=None, kind=mb.LOAD_CONFIG_SET, **proposal):
    req = c.tags[mb.request_tag_name(app)]
    seq = req['Sequence']
    req['Kind'] = kind
    c.tags[f'FRK_{app.name}_HmiLastSequence'] = seq
    req['ConfigSet'] = broker.staging(app, seq, document=doc,
        name=doc[0]['set'] if doc else 'commissioning', kind=doc[0]['kind'] if doc else 1, operation=kind)
    req['ConfigSet'].update(proposal)
    response = c.tags[mb.response_tag_name(app)]
    response.update(Accepted=0, DiagnosticKey=0)
    if app.access_users is not None:
        import fraktal_ab_data_access as data
        c.tags[access.tag(app, 'Work')]['Permitted'] = 1
        c.run('\n'.join(data.reset_rejection(app) + data.refresh(app)))
    c.run('CASE ' + mb.request_tag_name(app) + '.Kind OF\n' + '\n'.join(sets.dispatch(app)) + '\nEND_CASE;')
    return response


def configurations(c, app=APP):
    return copy.deepcopy({r.name: c.tags[r.name + 'Tag'] for r in app.records})


class ControllerTransactions(unittest.TestCase):
    def test_grouped_snapshots_keep_unselected_kinds_and_selected_model(self):
        for app in (APP, template.application()):
            for selected in (0, 1, 2) if app.line is not None else (0, 1):
                with self.subTest(station=app.name, kind=selected):
                    c = controller(app)
                    state = c.tags[sets.state_tag(app)]
                    state['Snapshot'] = [-777] * len(gen.editable_values(app))
                    # Export another bank: current model and live ParCfg must
                    # stay untouched while only the selected kind is sampled.
                    c.tags[mb.request_tag_name(app)]['DurationMs'] = 2
                    records_before = configurations(c, app)
                    banks_before = copy.deepcopy(c.tags[gen.model_cfg_tag(app)])
                    self.assertEqual(run(c, app, kind=mb.EXPORT_CURRENT_CONFIG, Kind=selected)['Accepted'], 1)
                    wanted = 0
                    for ordinal, record, member in gen.editable_values(app):
                        expected = -777
                        if sets.config_kind(record) == selected:
                            wanted += 1
                            expected = (banks_before[1][member.name]
                                        if gen.is_model_scoped(app, record, member.name)
                                        else records_before[record.name][member.name])
                        self.assertEqual(state['Snapshot'][ordinal - 1], expected, member.write_key)
                    self.assertEqual(state['Count'], wanted)
                    self.assertEqual(configurations(c, app), records_before)
                    self.assertEqual(c.tags[gen.model_cfg_tag(app)], banks_before)

    def test_each_inclusive_range_bound_is_accepted(self):
        for ordinal, record, member in gen.editable_values(APP):
            if not record.station_cfg:
                continue
            for value in (member.minimum, member.maximum):
                c = controller()
                doc = document()
                target = next(r for r in doc[1:] if r['key'] == member.write_key)
                target['value'] = str(value)
                self.assertEqual(run(c, doc=doc)['Accepted'], 1, (member.name, value))
                self.assertEqual(c.tags[record.name + 'Tag'][member.name], value)

    def test_valid_station_set_commits_the_entire_staged_transaction(self):
        c, doc = controller(), document()
        for record, (_ordinal, _r, m) in zip(doc[1:], ((o, r, m) for o, r, m in gen.editable_values(APP) if r.station_cfg)):
            record['value'] = 'FALSE' if m.kind == 'boolean' else str(m.minimum)
        doc[1]['value'] = '41'
        self.assertEqual(run(c, doc=doc)['Accepted'], 1)
        for _ordinal, record, member in gen.editable_values(APP):
            if record.station_cfg:
                expected = 41 if member.write_key == 'station.number' else member.minimum
                self.assertEqual(c.tags[record.name + 'Tag'][member.name], expected)
        audit = c.tags[sets.state_tag(APP)]
        self.assertEqual((audit['AuditAccepted'][0], audit['AuditRecords'][0]), (1, len(doc) - 1))
        self.assertEqual(c.tags['FRK_Press_Unit']['ReportedReason'], APP.reasons['EVENT_CONFIG_SET_APPLIED'])

    def test_invalid_last_record_cannot_apply_the_valid_first_record(self):
        for change in ({'value': '2147483647'}, {'key': 'unknown'}, {'scope': 'Other'},
                       {'rev': 0}, {'type': 1}, {'kind': 0}, {'value': '3.5'}, {'value': '2147483648'}):
            with self.subTest(change=change):
                c, doc = controller(), document()
                before = configurations(c)
                doc[1]['value'] = '41'
                doc[-1].update(change)
                self.assertEqual(run(c, doc=doc)['Accepted'], 0)
                self.assertEqual(configurations(c), before)
                self.assertEqual(c.tags[sets.state_tag(APP)]['RejectIndex'], len(doc) - 1)

    def test_foreign_root_schema_revision_kind_and_stale_payload_refuse(self):
        for key, value in (('RootId', 0), ('SetSchema', 2), ('ConfigRev', 0),
                           ('Kind', 2), ('Sequence', 0), ('Valid', 0),
                           ('Count', -1), ('Count', sets.MAX_RECORDS + 1),
                           ('SchemaVersion', 0), ('NameLength', 81)):
            c = controller()
            before = configurations(c)
            self.assertEqual(run(c, doc=document(), **{key: value})['Accepted'], 0, key)
            self.assertEqual(configurations(c), before)

    def test_duplicate_record_addresses_refuse_the_whole_set(self):
        c, doc = controller(), document()
        doc.append(dict(doc[1], value='41'))
        doc[0]['records'] += 1
        before = configurations(c)
        self.assertEqual(run(c, doc=doc)['Accepted'], 0)
        self.assertEqual(configurations(c), before)
        self.assertEqual(c.tags[sets.state_tag(APP)]['RejectIndex'], len(doc) - 1)

    def test_external_payload_changes_after_staging_cannot_change_the_commit(self):
        c, doc = controller(), document()
        doc[1]['value'] = '41'
        copy_instruction = c.calls['CPS']
        def after_copy(plc, arguments):
            copy_instruction(plc, arguments)
            request = plc.tags[mb.request_tag_name(APP)]['ConfigSet']
            request['Value'][:len(doc) - 1] = [2147483647] * (len(doc) - 1)
        c.calls['CPS'] = after_copy
        self.assertEqual(run(c, doc=doc)['Accepted'], 1)
        record = next(r for r in APP.records if r.station_cfg)
        self.assertEqual(c.tags[record.name + 'Tag']['StationNumber'], 41)
        self.assertEqual(c.tags[record.name + 'Tag']['RequireTwoHandStart'], 1)

    def test_model_load_preserves_both_live_and_stored_model_values(self):
        c = controller()
        before = configurations(c), copy.deepcopy(c.tags[gen.model_cfg_tag(APP)])
        self.assertEqual(run(c, doc=document(kind=0))['DiagnosticKey'], mf.numeric_key(APP, sets.MODEL_KEY))
        self.assertEqual((configurations(c), c.tags[gen.model_cfg_tag(APP)]), before)

    def test_root_ready_is_checked_on_the_controller(self):
        for flag in ('Running', 'Error', 'Aborted', 'Complete'):
            for kind in (mb.LOAD_CONFIG_SET, mb.SAVE_CONFIG_SET, mb.IMPORT_CONFIG_SET, mb.DELETE_CONFIG_SET):
                c = controller()
                c.tags['FRK_Press_Unit'][flag] = 1
                self.assertEqual(run(c, doc=document(), kind=kind)['Accepted'], 0, (flag, kind))
        c = controller()
        c.tags['FRK_Press_Unit']['Running'] = 1
        for kind in (mb.LIST_CONFIG_SETS, mb.EXPORT_CONFIG_SET):
            self.assertEqual(run(c, kind=kind)['Accepted'], 1)

    def test_save_samples_values_not_the_gateway_proposal(self):
        c = controller()
        doc = document()
        for r in doc[1:]:
            r['value'] = '41'
        self.assertEqual(run(c, doc=doc, kind=mb.SAVE_CONFIG_SET)['Accepted'], 1)
        s = c.tags[sets.state_tag(APP)]
        for ordinal, record, member in gen.editable_values(APP):
            if record.station_cfg:
                self.assertEqual(s['Snapshot'][ordinal - 1], member.initial)
        result = broker.snapshot_document(APP, doc[0]['set'], 1, s)
        self.assertEqual([r['value'] for r in result[1:]], [r['value'] for r in document()[1:]])
        self.assertEqual(c.tags[gen.config_persist_tag(APP)]['Pending'], 1)

    def test_store_receipt_and_timeout_are_controller_authoritative(self):
        for result, failed in ((1, 0), (2, 1)):
            c = controller()
            run(c, kind=mb.SAVE_CONFIG_SET)
            req = c.tags[mb.request_tag_name(APP)]['ConfigSet']
            req.update(StoreAck=0, StoreResult=result)
            c.run('\n'.join(sets.cyclic(APP)))
            self.assertEqual(c.tags[gen.config_persist_tag(APP)]['Pending'], 1)
            req['StoreAck'] = 1
            c.run('\n'.join(sets.cyclic(APP)))
            self.assertEqual(c.tags[gen.config_persist_tag(APP)]['Pending'], 0)
            self.assertEqual(c.tags[gen.config_persist_tag(APP)]['Failed'], failed)
        c = controller()
        run(c, kind=mb.SAVE_CONFIG_SET)
        c.tags[sets.state_tag(APP)]['PendingMs'] = sets.WINDOW_MS
        c.run('\n'.join(sets.cyclic(APP)))
        self.assertEqual(c.tags[gen.config_persist_tag(APP)]['Failed'], 1)

    def test_list_during_pending_does_not_replace_the_store_receipt_sequence(self):
        c = controller()
        run(c, kind=mb.SAVE_CONFIG_SET)
        c.tags[mb.request_tag_name(APP)]['Sequence'] = 2
        run(c, kind=mb.LIST_CONFIG_SETS)
        self.assertEqual(c.tags[sets.state_tag(APP)]['PendingSequence'], 1)
        c.tags[mb.request_tag_name(APP)]['ConfigSet'].update(StoreAck=1, StoreResult=1)
        c.run('\n'.join(sets.cyclic(APP)))
        self.assertEqual(c.tags[gen.config_persist_tag(APP)]['Pending'], 0)

    def test_audit_is_bounded_and_records_refusals_names_and_claimed_users(self):
        c = controller()
        for sequence in range(1, sets.AUDIT_CAPACITY + 4):
            c.tags[mb.request_tag_name(APP)]['Sequence'] = sequence
            run(c, doc=document(), Valid=0)
        audit = c.tags[sets.state_tag(APP)]
        self.assertEqual((audit['Head'], audit['AuditCount']), (3, sets.AUDIT_CAPACITY))
        self.assertEqual(audit['AuditSequence'][2], sets.AUDIT_CAPACITY + 3)
        self.assertEqual(audit['AuditAccepted'][2], 0)
        offset = 2 * sets.NAME_MAX
        self.assertEqual(bytes(audit['AuditNameBytes'][offset:offset + audit['AuditNameLength'][2]]).decode(), 'commissioning')

    def test_template_uses_the_same_controller_transaction(self):
        app = template.application()
        c = controller(app)
        self.assertEqual(run(c, app, document(app))['Accepted'], 1)


class PortableLinesAndStore(unittest.TestCase):
    def test_codec_matches_the_tc3_header_and_record_field_order(self):
        doc = document()
        self.assertEqual(sets.render_line(doc[1]), '{"scope":"Press","key":"station.number","rev":' + str(mf.config_revision(APP)) + ',"kind":1,"type":0,"value":"1"}')
        for value in doc:
            self.assertEqual(sets.parse_line(sets.render_line(value)), value)

    def test_quote_backslash_control_and_255_to_480_byte_lines_round_trip(self):
        r = dict(document()[1], scope='s' * 80, key='k' * 160, value='\\"\n' + '9' * 77)
        line = sets.render_line(r)
        self.assertGreater(len(line), 255)
        self.assertEqual(sets.parse_line(line), r)
        r['value'] = '\\' * 80
        r['key'] = '\\' * 160
        with self.assertRaises(sets.SetRejected):
            sets.render_line(r)

    def test_malformed_ambiguous_and_oversized_json_is_refused(self):
        duplicate = sets.render_line(document()[0]).replace('"set":"commissioning"', '"set":"old","set":"commissioning"')
        for line in ('{}', '[]', 'null', '{"set":"a","set":"b"}', duplicate,
                     json.dumps(dict(document()[0], records=True)),
                     json.dumps(dict(document()[0], root='x' * 81)), 'x' * 481):
            with self.subTest(line=line[:40]), self.assertRaises(sets.SetRejected):
                sets.parse_line(line)

    def test_import_fragments_commit_only_the_complete_document(self):
        session, doc = sets.Session(), document()
        for index, value in enumerate(doc):
            line = sets.render_line(value)
            self.assertIsNone(session.piece(line[:40], True, False))
            result = session.piece(line[40:], False, index == len(doc) - 1)
        self.assertEqual(result, doc)
        self.assertIsNone(session.document)

    def test_interruption_bad_piece_count_overflow_and_early_commit_abort(self):
        for action in ('interrupt', 'oversize', 'bad', 'early'):
            s = sets.Session()
            s.piece(sets.render_line(document()[0]), False, False)
            if action == 'interrupt':
                s.interrupt()
                with self.assertRaises(sets.SetRejected):
                    s.piece(sets.render_line(document()[1]), False, True)
            else:
                with self.assertRaises(sets.SetRejected):
                    if action == 'oversize':
                        s.piece('x' * 255, True, False)
                        s.piece('x' * 226, True, False)
                    elif action == 'bad':
                        s.piece('invalid', False, False)
                    else:
                        s.piece('half', True, True)
            self.assertIsNone(s.document)
            self.assertEqual(s.partial, '')

    def test_record_count_mismatch_never_commits(self):
        s = sets.Session()
        with self.assertRaises(sets.SetRejected):
            s.piece(sets.render_line(document()[0]), False, True)

    def test_store_survives_reopen_and_delete_releases_a_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            store = sets.FileStore(directory)
            for index in range(sets.MAX_SETS):
                store.save(document(name=str(index)))
            with self.assertRaises(sets.SetRejected):
                store.save(document(name='full'))
            store.save(document(name='0'))  # replacing a name costs no slot
            reopened = sets.FileStore(directory)
            self.assertEqual(reopened.read('0'), document(name='0'))
            reopened.delete('0')
            reopened.save(document(name='full'))
            self.assertEqual(len(reopened.list()), sets.MAX_SETS)

    def test_path_like_names_are_data_and_failed_replacement_preserves_old_file(self):
        with tempfile.TemporaryDirectory() as directory:
            store, doc = sets.FileStore(directory), document(name='../commissioning')
            store.save(doc)
            replacement = copy.deepcopy(doc)
            replacement[-1]['value'] = '41'
            with mock.patch.object(sets.os, 'replace', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    store.save(replacement)
            self.assertEqual(store.read(doc[0]['set']), doc)
            self.assertTrue(all(p.parent == Path(directory) for p in Path(directory).iterdir()))
            self.assertFalse(list(Path(directory).glob('.pending-*')))

    def test_import_store_accepts_foreign_identity_but_never_applies_it(self):
        with tempfile.TemporaryDirectory() as directory:
            doc = document()
            doc[0]['root'] = 'Other'
            doc[-1]['key'] = 'unknown'
            store = sets.FileStore(directory)
            store.save(doc)
            c = controller()
            before = configurations(c)
            self.assertEqual(run(c, doc=store.read(doc[0]['set']))['Accepted'], 0)
            self.assertEqual(configurations(c), before)


class Emission(unittest.TestCase):
    def test_only_the_mailbox_grows_and_its_old_prefix_is_preserved(self):
        import xml.etree.ElementTree as ET
        root = ET.fromstring(gen.data_types(APP))
        record = root.find(f"DataType[@Name='{mb.request_type_name(APP)}']")
        members = list(record.find('Members'))
        self.assertEqual([m.get('Name') for m in members[:-1]], [m[0] for m in mb.REQUEST_MEMBERS] + ['ConfigSet'])
        self.assertEqual(members[-1].get('Name'), 'Frame')
        self.assertTrue(mb.request_type_name(APP).endswith('V3'))
        tags = ET.fromstring(gen.controller_tags(APP))
        private = tags.find(f"Tag[@Name='{sets.staged_tag(APP)}']")
        self.assertEqual(private.get('ExternalAccess'), 'None')
        disabled = dataclasses.replace(APP, config_sets=False)
        self.assertNotIn(sets.state_name(), gen.data_types(disabled))
        self.assertEqual(mb.refused_for(disabled)[mb.LOAD_CONFIG_SET], mb.REFUSED[mb.LOAD_CONFIG_SET])
        writer = gw.MailboxWriter('unused', 0, '7036B510')
        for path in ('Press/HmiRequest/ConfigSet/Value', 'Press/HmiRequest/ConfigSet', 'Press/ConfigSetState/Sequence'):
            with self.assertRaises(gw.WriteRefused):
                writer.tag_for(path)

    def test_fixed_catalog_paths_do_not_depend_on_stored_names(self):
        self.assertEqual(set(sets.empty_values('Press')), set(sets.list_values('Press', [document()[0]])))


class NativeComm:
    """CIP-shaped offline adapter; committed requests execute generated ST."""
    def __init__(self, app=APP):
        self.app, self.c = app, controller(app)
        import fraktal_ab_mailbox_frame as frame
        self.c.tags[mb.request_tag_name(app)]['Frame'] = {'Words': [0] * frame.word_count(app)}
        self.c.tags[frame.sample_tag(app)] = {'Words': [0] * frame.word_count(app)}
        for name in ('Cursor', 'Word', 'Byte', 'Valid', 'Field'):
            self.c.tags[f'FRK_{app.name}_HmiFrame{name}'] = 0
        self.c.calls['CPS'] = st.cps_structure
        self.decode = '\n'.join(frame.logic(app))
        self.writes = []
        self.fail_tag = ''

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def GetDeviceProperties(self):
        return SimpleNamespace(Status='Success', Value=SimpleNamespace(SerialNumber='7036B510'))

    def Write(self, target, value):
        self.writes.append((target, value))
        if target == self.fail_tag:
            return SimpleNamespace(Status='failure')
        parts = target.split('.')
        obj = self.c.tags
        for part in parts[:-1]:
            obj = obj[part]
        leaf = parts[-1]
        if isinstance(value, list):
            obj[leaf][:len(value)] = value
        else:
            obj[leaf] = int(value)
        if target == mb.request_tag_name(self.app) + '.Sequence':
            self.c.run(self.decode)
            self.c.tags[f'FRK_{self.app.name}_HmiLastSequence'] = value
            response = self.c.tags[mb.response_tag_name(self.app)]
            response.update(Accepted=0, DiagnosticKey=0)
            if self.app.access_users is not None:
                import fraktal_ab_data_access as data
                self.c.tags[access.tag(self.app, 'Work')]['Permitted'] = 1
                self.c.run('\n'.join(data.reset_rejection(self.app) + data.refresh(self.app)))
            self.c.run('CASE ' + mb.request_tag_name(self.app) + '.Kind OF\n' + '\n'.join(sets.dispatch(self.app)) + '\nEND_CASE;')
            response['AckSequence'] = value
        if target == mb.request_tag_name(self.app) + '.ConfigSet.StoreAck':
            self.c.run('\n'.join(sets.cyclic(self.app)))
        return SimpleNamespace(Status='Success')

    def Read(self, target):
        if target.endswith('.AckSequence'):
            return SimpleNamespace(Status='Success', Value=self.c.tags[mb.response_tag_name(self.app)]['AckSequence'])
        layouts = {sets.state_tag(self.app): sets.state_members(self.app),
                   gen.config_persist_tag(self.app): gen.config_persist_members(),
                   mb.response_tag_name(self.app): tuple(decl.scalar(n) for n, *_ in mb.RESPONSE_MEMBERS)}
        value = self.c.tags[target]
        names = [m.name for m in layouts[target]] if target in layouts else list(value)
        flattened = []
        for name in names:
            field = value[name]
            flattened.extend(field if isinstance(field, list) else [field])
        return SimpleNamespace(Status='Success', Value=struct.pack('<' + 'i' * len(flattened), *flattened))


def batch(kind, sequence, **arguments):
    supplied = dict(Kind=kind, Sequence=sequence, **arguments)
    return [(f'Press/HmiRequest/{n}', 'string' if t == mb.STRING_MEMBER else 'uint32' if n == 'Sequence' else 'int32',
             supplied.get(n, '' if t == mb.STRING_MEMBER else 0)) for n, t, *_ in mb.REQUEST_MEMBERS]


class BrokerAndController(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = sets.FileStore(self.directory.name)
        self.comm = NativeComm()
        self.writer = gw.MailboxWriter('unused', 0, '7036B510', set_store=self.store)
        self.session = sets.Session()
        self.sequence = 0

    def command(self, kind, **arguments):
        self.sequence += 1
        self.assertTrue(broker.process(self.comm, APP, self.store, self.session,
            batch(kind, self.sequence, **arguments), self.writer._write_base))
        return self.comm.c.tags[mb.response_tag_name(APP)]

    def test_save_change_load_list_export_and_delete_use_one_sequence_each(self):
        self.assertEqual(self.command(mb.SAVE_CONFIG_SET, TextValue='commissioning', IntValue=1)['Accepted'], 1)
        saved = self.store.read('commissioning')
        self.assertEqual(self.comm.c.tags[gen.config_persist_tag(APP)]['Pending'], 0)
        first = next(r for r in APP.records if r.station_cfg)
        self.comm.c.tags[first.name + 'Tag']['StationNumber'] = 41
        self.assertEqual(self.command(mb.LOAD_CONFIG_SET, TextValue='commissioning')['Accepted'], 1)
        self.assertEqual(self.comm.c.tags[first.name + 'Tag']['StationNumber'], 1)
        self.command(mb.LIST_CONFIG_SETS)
        self.assertEqual(self.session.values['Press/ConfigSetCount'], 1)
        for index, line in enumerate(saved):
            self.command(mb.EXPORT_CONFIG_SET, TextValue='commissioning', IntValue=index)
            self.assertEqual(sets.parse_line(self.session.values['Press/ConfigSetDocument']), line)
        self.command(mb.DELETE_CONFIG_SET, TextValue='commissioning')
        self.assertEqual(self.store.list(), [])
        commits = [v for t, v in self.comm.writes if t == mb.request_tag_name(APP) + '.Sequence']
        self.assertEqual(commits, list(range(1, self.sequence + 1)))

    def test_export_denial_clears_old_line_and_names_inaccessible_record(self):
        self.command(mb.SAVE_CONFIG_SET, TextValue='commissioning', IntValue=1)
        self.command(mb.EXPORT_CONFIG_SET, TextValue='commissioning', IntValue=0)
        self.assertTrue(self.session.values['Press/ConfigSetDocument'])
        held = self.comm.c.tags[access.tag(APP, 'State')]
        held['Required'][0], held['CurrentLevel'] = 3, 2
        answer = self.command(mb.EXPORT_CONFIG_SET, TextValue='commissioning', IntValue=0)
        self.assertEqual((answer['Accepted'], answer['DiagnosticKey']), (0, mf.numeric_key(APP, access.DENIED)))
        self.assertEqual(self.session.values['Press/ConfigSetDocument'], '')
        self.assertEqual(self.session.values['Press/ConfigPersist/LastRejectKey'], 'station.ramExtendLimitMs')

    def test_import_never_applies_and_bad_load_reports_the_offending_record(self):
        doc = document()
        doc[-1]['key'] = 'unknown'
        before = configurations(self.comm.c)
        for i, row in enumerate(doc):
            self.command(mb.IMPORT_CONFIG_SET, TextValue=sets.render_line(row), BoolValue=int(i == len(doc) - 1))
        self.assertEqual(configurations(self.comm.c), before)
        answer = self.command(mb.LOAD_CONFIG_SET, TextValue=doc[0]['set'])
        self.assertEqual(answer['Accepted'], 0)
        self.assertEqual(self.session.values['Press/ConfigPersist/LastRejectScope'], 'Press')
        self.assertEqual(self.session.values['Press/ConfigPersist/LastRejectKey'], 'unknown')
        self.assertEqual(configurations(self.comm.c), before)

    def test_a_failed_import_preserves_an_existing_named_document(self):
        self.command(mb.SAVE_CONFIG_SET, TextValue='commissioning', IntValue=1)
        previous = self.store.read('commissioning')
        self.command(mb.IMPORT_CONFIG_SET, TextValue=sets.render_line(previous[0]))
        answer = self.command(mb.IMPORT_CONFIG_SET, TextValue='invalid', BoolValue=1)
        self.assertEqual(answer['Accepted'], 0)
        self.assertEqual(self.store.read('commissioning'), previous)
        self.assertEqual(self.session.partial, '')
        self.assertIsNone(self.session.document)

    def test_failed_file_io_is_refused_by_the_controller_receipt_and_keeps_old_file(self):
        self.command(mb.SAVE_CONFIG_SET, TextValue='commissioning', IntValue=1)
        before = self.store.read('commissioning')
        with mock.patch.object(sets.os, 'replace', side_effect=OSError('disk full')):
            answer = self.command(mb.SAVE_CONFIG_SET, TextValue='commissioning', IntValue=1)
        self.assertEqual(answer['Accepted'], 0)
        self.assertEqual(answer['DiagnosticKey'], mf.numeric_key(APP, sets.STORE_FAILED_KEY))
        self.assertEqual(self.comm.c.tags[gen.config_persist_tag(APP)]['Failed'], 1)
        self.assertEqual(self.store.read('commissioning'), before)

    def test_a_staging_failure_never_writes_the_main_sequence(self):
        self.comm.fail_tag = mb.request_tag_name(APP) + '.ConfigSet.ValueType'
        with self.assertRaises(sets.SetRejected):
            self.command(mb.SAVE_CONFIG_SET, TextValue='commissioning', IntValue=1)
        self.assertFalse(any(t.endswith('.Sequence') and '.ConfigSet.' not in t for t, _ in self.comm.writes))
        self.assertEqual(self.store.list(), [])

    def test_access_denial_needs_no_new_set_state_or_host_mutation(self):
        self.command(mb.SAVE_CONFIG_SET, TextValue='commissioning', IntValue=1)
        previous = self.store.read('commissioning')
        self.comm.c.tags[sets.state_tag(APP)]['RejectIndex'] = 1
        old_state = copy.deepcopy(self.comm.c.tags[sets.state_tag(APP)])
        native_write = self.comm.Write
        commit_tag = mb.request_tag_name(APP) + '.Sequence'
        def deny_commit(target, value):
            if target != commit_tag:
                return native_write(target, value)
            # The root's access gate acknowledges before set dispatch. The
            # previous set state remains untouched, as on the real controller.
            self.comm.writes.append((target, value))
            self.comm.c.tags[mb.request_tag_name(APP)]['Sequence'] = value
            self.comm.c.tags[mb.response_tag_name(APP)].update(
                AckSequence=value, Accepted=0,
                DiagnosticKey=mf.numeric_key(APP, access.DENIED))
            return SimpleNamespace(Status='Success')
        with mock.patch.object(self.comm, 'Write', side_effect=deny_commit):
            for kind in sets.SET_KINDS:
                with self.subTest(kind=kind):
                    text = sets.render_line(previous[0]) if kind == mb.IMPORT_CONFIG_SET else 'commissioning'
                    start = len(self.comm.writes)
                    answer = self.command(kind, TextValue=text)
                    self.assertEqual(answer['Accepted'], 0)
                    self.assertEqual(answer['AckSequence'], self.sequence)
                    self.assertEqual(self.session.committed_sequence, self.sequence)
                    self.assertEqual(self.comm.c.tags[sets.state_tag(APP)], old_state)
                    self.assertEqual(self.store.read('commissioning'), previous)
                    self.assertEqual(self.session.partial, '')
                    self.assertIsNone(self.session.document)
                    if kind == mb.LOAD_CONFIG_SET:
                        self.assertEqual(self.session.values['Press/ConfigPersist/LastRejectScope'], '')
                        self.assertEqual(self.session.values['Press/ConfigPersist/LastRejectKey'], 'commissioning')
                    self.assertFalse(any(t.endswith('.StoreAck') and v != 0
                                         for t, v in self.comm.writes[start:]))

    def test_accepted_set_requires_its_own_state_before_host_io(self):
        old_state = copy.deepcopy(self.comm.c.tags[sets.state_tag(APP)])
        with mock.patch.object(broker, 'read_state', return_value=old_state):
            with self.assertRaisesRegex(sets.SetRejected, 'another sequence'):
                self.command(mb.SAVE_CONFIG_SET, TextValue='commissioning', IntValue=1)
        self.assertEqual(self.store.list(), [])

    def test_serial_mismatch_stops_all_controller_and_store_writes(self):
        self.comm.GetDeviceProperties = lambda: SimpleNamespace(Value=SimpleNamespace(SerialNumber='00000123'))
        with mock.patch('pylogix.PLC', return_value=self.comm):
            self.assertFalse(self.writer.set_command(batch(mb.SAVE_CONFIG_SET, 1, TextValue='commissioning', IntValue=1), 'Press/HmiRequest', self.session))
        self.assertEqual(self.comm.writes, [])
        self.assertEqual(self.store.list(), [])

    def test_gateway_writer_executes_the_same_guarded_transaction(self):
        with mock.patch('pylogix.PLC', return_value=self.comm):
            self.assertTrue(self.writer.set_command(batch(mb.SAVE_CONFIG_SET, 1, TextValue='commissioning', IntValue=1), 'Press/HmiRequest', self.session))
        self.assertEqual(self.store.read('commissioning')[0]['root'], 'Press')


class GatewaySetProtocol(unittest.IsolatedAsyncioTestCase):
    def fixture(self, *, write_token='fixture', authenticated=True, writer=None):
        values = sets.empty_values('Press')
        values.update({'Press/HmiRequest/Sequence': 4})
        station = gw.Station(lambda: {'values': dict(values)}, cache_ttl=0)
        g = gw.Gateway(station, write_token=write_token, write_roots=frozenset({'Press'}), write_fn=writer)
        state = gw._ConnState()
        state.authenticated = authenticated
        return g, state

    def params(self, kind, sequence=5):
        return {'writes': [{'path': p, 'valueType': t, 'value': v} for p, t, v in batch(kind, sequence, TextValue='fixture', IntValue=1)]}

    async def test_all_set_kinds_and_restore_ack_keep_the_write_gate(self):
        for kind in (*sets.SET_KINDS, mb.ACK_CONFIG_RESTORE):
            for options in ({'write_token': ''}, {'authenticated': False}):
                writer = mock.Mock(return_value=True)
                g, state = self.fixture(writer=writer, **options)
                with self.assertRaises(gw.WriteRefused):
                    await g._write_batch(state, self.params(kind))
                writer.assert_not_called()

    async def test_set_answers_are_connection_local_and_excluded_from_cyclic_snapshots(self):
        g, state = self.fixture()
        doc = await g.station.document()
        state.sets.values = sets.list_values('Press', [document()[0]])
        other = gw._ConnState()
        self.assertEqual(g._values_for(state, doc)['Press/ConfigSetCount'], 1)
        self.assertEqual(g._values_for(other, doc)['Press/ConfigSetCount'], 0)
        paths = g.station.paths
        excluded = [i for i, p in enumerate(paths) if '/ConfigSet' in p]
        await g._set_read_tiers(state, {'revision': g.station.revision, 'excluded': excluded})
        snapshot = await g._snapshot(state)
        self.assertFalse(any('/ConfigSet' in p for p in snapshot['values']))
        read = await g._read_values(state, {'revision': g.station.revision, 'indices': [paths.index('Press/ConfigSetCount')]})
        self.assertEqual(read['Press/ConfigSetCount'], 1)

    async def test_post_commit_read_failure_cannot_replay_a_load(self):
        class Writer:
            def set_command(self, writes, mailbox, session):
                session.committed_sequence = 5
                raise sets.SetRejected('acknowledgement connection lost')
        g, state = self.fixture(writer=Writer())
        with self.assertRaises(sets.SetRejected):
            await g._write_batch(state, self.params(mb.LOAD_CONFIG_SET))
        self.assertEqual(g._mailbox_sequences['Press/HmiRequest'], 5)
        with self.assertRaises(gw.WriteRefused):
            await g._write_batch(state, self.params(mb.LOAD_CONFIG_SET))

    async def test_other_commands_discard_incomplete_import(self):
        g, state = self.fixture(writer=lambda *_: True)
        state.sets.piece(sets.render_line(document()[0]), False, False)
        state.sets.piece('partial', True, False)
        await g._write_batch(state, self.params(mb.STOP))
        self.assertEqual(state.sets.partial, '')
        self.assertIsNone(state.sets.document)


if __name__ == '__main__':
    unittest.main()
