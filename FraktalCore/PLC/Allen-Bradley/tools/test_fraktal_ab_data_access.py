"""Execute the emitted PLC authority; TC3/Core semantics are the expectations."""
import copy
import dataclasses
import unittest
import xml.etree.ElementTree as ET

import fraktal_ab_access as access
import fraktal_ab_data_access as data
import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as mf
import fraktal_ab_projection as projection
import fraktal_ab_press_demo as demo
import fraktal_ab_set_broker as broker
import fraktal_ab_sets as sets
import fraktal_ab_st_model as st
import fraktal_ab_station_template as template

APP = demo.application()
COUNTER, CALIBRATION = 'station.number', 'station.airPressureMinKpa'


def with_access(app, key, **arguments):
    return dataclasses.replace(app, records=tuple(dataclasses.replace(record, members=tuple(
        dataclasses.replace(member, **arguments) if member.write_key == key else member
        for member in record.members)) for record in app.records))


def level_controller(app=APP, level=4):
    tags = {access.tag(app, 'State'): st.structure(access.state_members(app)),
            data.tag(app, 'Policy'): data.policy_data(app),
            data.tag(app, 'Levels'): st.structure(data.levels_members(app)),
            data.tag(app, 'Work'): st.structure(data.work_members())}
    tags[access.tag(app, 'State')]['CurrentLevel'] = level
    resolver = st.parse('\n'.join(data.resolver(app)))
    refresh = st.parse('\n'.join(data.refresh(app)))
    tags[mb.request_tag_name(app)] = {'Sequence': 0}
    tags[f'FRK_{app.name}_HmiLastSequence'] = 0
    def jsr(c, args):
        name = args[0][1][0][1]
        c.run(resolver if name == data.tag(app, 'ResolveLevel') else refresh)
    return st.Controller(tags, {'JSR': jsr})


def effective_levels(app=APP, level=4):
    c = level_controller(app, level)
    c.run('\n'.join(data.refresh(app)))
    return c.tags[data.tag(app, 'Levels')]


def controller(app=APP, level=4):
    from test_fraktal_ab_access import controller as complete
    c = complete(app)
    c.tags[access.tag(app, 'State')].update(CurrentLevel=level, UserLength=5, UserBytes=list(b'actor') + [0] * 27)
    c.tags[sets.state_tag(app)] = st.structure(sets.state_members(app))
    c.tags[gen.health_probe_tag(app)] = st.structure(gen.health_probe_members())
    return c


def request(c, kind, app=APP, **arguments):
    from test_fraktal_ab_access import request as send
    return send(c, kind, app, **arguments)


def entries(app, held, values=None):
    if values is None:
        values = {record.name: {m.name: m.initial for m in record.members} for record in app.records}
    page = projection.config_page(app, mf.content(app), values, data_levels=held)
    out = {}
    for i in range(1, page['HmiResponse/ConfigPage/EntryCount'] + 1):
        prefix = f'HmiResponse/ConfigPage/Entries[{i}]/'
        row = {key[len(prefix):]: value for key, value in page.items() if key.startswith(prefix)}
        out[row['WriteKey']] = row
    return page, out


class EffectiveAuthority(unittest.TestCase):
    def test_dynamic_value_lookup_uses_requested_slot_and_preserves_iteration(self):
        # Execute both endpoints and an interior value with distinct read/write
        # policies. Seed the reused scratch with a stale index on every request.
        size = len(gen.editable_values(APP))
        for ordinal in (1, size // 2, size):
            for for_write in (False, True):
                for required in (2, 4, -1, 5):
                    with self.subTest(ordinal=ordinal, write=for_write, required=required):
                        c = controller(level=3)
                        d = c.tags[data.tag(APP, 'Levels')]
                        d['ReadLevel'][:] = [4] * size
                        d['WriteLevel'][:] = [4] * size
                        direction = 'WriteLevel' if for_write else 'ReadLevel'
                        d[direction][ordinal - 1] = required
                        c.tags[data.tag(APP, 'Work')]['Index'] = size + 99
                        c.tags[sets.scratch_names(APP)[0]] = 1
                        c.tags['RequestedOrdinals'] = [size, ordinal, 1]
                        c.tags[access.tag(APP, 'Work')]['Permitted'] = 1
                        c.tags[f'FRK_{APP.name}_HmiLastSequence'] = 71
                        c.run('\n'.join(data.reset_rejection(APP) + data.check_value(
                            APP, 'RequestedOrdinals[' + sets.scratch_names(APP)[0] + ']',
                            for_write=for_write)))
                        allowed = required == 2
                        self.assertEqual(c.tags[access.tag(APP, 'Work')]['Permitted'], int(allowed))
                        self.assertEqual(c.tags[sets.scratch_names(APP)[0]], 1)
                        if not allowed:
                            self.assertEqual((d['RejectSequence'], d['RejectCapability'],
                                              d['RejectRequiredLevel']), (71, ordinal, required))

    def test_builtin_classes_retain_the_two_existing_action_thresholds(self):
        c = level_controller(level=1)
        c.tags[access.tag(APP, 'State')]['Required'][:2] = [2, 3]
        c.run('\n'.join(data.cyclic(APP)))
        _page, rows = entries(APP, c.tags[data.tag(APP, 'Levels')])
        self.assertEqual((rows['press.dwellMs']['ReadLevel'], rows['press.dwellMs']['WriteLevel']), (2, 3))
        self.assertFalse(rows['press.dwellMs']['Readable'])
        self.assertEqual(rows['press.dwellMs']['ValueText'], '')
        self.assertTrue(rows[COUNTER]['Readable'])

    def test_public_class_is_independent_of_builtin_levels(self):
        c = controller(level=1)
        c.tags[access.tag(APP, 'State')]['Required'][:2] = [3, 3]
        self.assertEqual(request(c, mb.QUERY_CONFIG)['Accepted'], 1)
        self.assertEqual(request(c, mb.WRITE_CONFIG, IntValue=mb.config_ordinal(APP, COUNTER), BoolValue=41)['Accepted'], 1)
        self.assertEqual(c.tags[APP.records[1].name + 'Tag']['StationNumber'], 41)
        self.assertEqual(request(c, mb.WRITE_CONFIG, IntValue=mb.config_ordinal(APP, 'press.dwellMs'), BoolValue=500)['Accepted'], 0)
        self.assertEqual(c.tags[APP.records[0].name + 'Tag']['PressDwellMs'], 300)

    def test_value_minimum_can_only_raise_class_write_level(self):
        for level in range(5):
            c = controller(level=level)
            answer = request(c, mb.WRITE_CONFIG, IntValue=mb.config_ordinal(APP, CALIBRATION), BoolValue=600)
            self.assertEqual(answer['Accepted'], int(level >= 3), level)
            self.assertEqual(c.tags[APP.records[1].name + 'Tag']['AirPressureMinKpa'], 600 if level >= 3 else 450)

    def test_undeclared_class_requires_admin_for_read_and_write(self):
        app = with_access(APP, COUNTER, class_id='ghost')
        for level in range(5):
            c = controller(app, level)
            answer = request(c, mb.WRITE_CONFIG, app, IntValue=mb.config_ordinal(app, COUNTER), BoolValue=41)
            self.assertEqual(answer['Accepted'], int(level == 4))
            _page, rows = entries(app, c.tags[data.tag(app, 'Levels')])
            self.assertEqual((rows[COUNTER]['ReadLevel'], rows[COUNTER]['WriteLevel']), (4, 4))
            self.assertEqual(rows[COUNTER]['Readable'], level == 4)

    def test_corrupt_class_and_builtin_levels_fail_closed_at_admin(self):
        for bad in (-1, 5, 2147483647):
            c = level_controller(level=3)
            c.tags[data.tag(APP, 'Policy')]['ReadLevel'][0] = bad
            c.tags[access.tag(APP, 'State')]['Required'][1] = bad
            c.run('\n'.join(data.cyclic(APP)))
            _page, rows = entries(APP, c.tags[data.tag(APP, 'Levels')])
            self.assertEqual(rows[COUNTER]['ReadLevel'], 4)
            self.assertFalse(rows[COUNTER]['Readable'])
            self.assertEqual(rows['press.dwellMs']['WriteLevel'], 4)

    def test_corrupt_count_does_not_index_outside_class_storage(self):
        for bad in (-1, 3, 2147483647):
            c = level_controller(level=3)
            c.tags[data.tag(APP, 'Policy')]['Count'] = bad
            c.run('\n'.join(data.cyclic(APP)))
            _page, rows = entries(APP, c.tags[data.tag(APP, 'Levels')])
            self.assertEqual(rows[COUNTER]['ReadLevel'], 4)

    def test_query_metadata_is_not_blanket_gated_by_data_read(self):
        c = controller(level=0)
        c.tags[access.tag(APP, 'State')]['Required'][0] = 4
        self.assertEqual(request(c, mb.QUERY_CONFIG)['Accepted'], 1)
        _page, rows = entries(APP, c.tags[data.tag(APP, 'Levels')])
        self.assertTrue(rows[COUNTER]['Readable'])
        self.assertFalse(rows['press.dwellMs']['Readable'])
        self.assertEqual(rows['press.dwellMs']['ValueText'], '')
        self.assertEqual(rows['press.dwellMs']['LabelKey'], 'project.config.pressDwellMs')

    def test_capture_rechecks_the_value_before_sampling_or_committing(self):
        app = with_access(APP, 'press.recipe.baselineWorkMs', min_write_level=3)
        c = controller(app, 2)
        c.tags[gen.profiler_tag(app)]['LastWork'] = 2000
        answer = request(c, mb.CAPTURE_CONFIG, app, IntValue=mb.config_ordinal(app, 'press.recipe.baselineWorkMs'),
                         DurationMs=mf.config_revision(app), BoolValue=1)
        self.assertEqual((answer['Accepted'], answer['DiagnosticKey']), (0, mf.numeric_key(app, access.DENIED)))
        self.assertEqual(c.tags[app.records[0].name + 'Tag']['BaselineWorkMs'], 950)

    def test_other_model_uses_same_value_permission(self):
        app = with_access(APP, 'press.dwellMs', min_write_level=3)
        c = controller(app, 2)
        before = copy.deepcopy(c.tags[gen.model_cfg_tag(app)])
        self.assertEqual(request(c, mb.WRITE_CONFIG, app, IntValue=mb.config_ordinal(app, 'press.dwellMs'), BoolValue=500, DurationMs=2)['Accepted'], 0)
        self.assertEqual(c.tags[gen.model_cfg_tag(app)], before)

    def test_denied_audit_names_actual_actor_value_and_required_level(self):
        c = controller(level=1)
        answer = request(c, mb.WRITE_CONFIG, IntValue=mb.config_ordinal(APP, CALIBRATION), BoolValue=600, User='claimed_admin')
        self.assertEqual(answer['Accepted'], 0)
        audit = c.tags[access.tag(APP, 'Audit')]
        slot = audit['Head'] - 1
        self.assertEqual(audit['Key'][slot], mf.numeric_key(APP, data.DENIED))
        self.assertEqual(audit['DataCapability'][slot], mb.config_ordinal(APP, CALIBRATION))
        self.assertEqual(audit['DataRequiredLevel'][slot], 3)
        messages = access.audit_status(APP, mf.content(APP), audit, c.tags[gen.alarm_ring_tag(APP)])
        description = messages[f'AlarmLog/Ring[{slot + 1}]/Description']
        self.assertIn('actor', description)
        self.assertIn(CALIBRATION, description)
        self.assertIn('required=3', description)
        self.assertNotIn('claimed_admin', description)


class PolicyAndProjection(unittest.TestCase):
    def test_snapshot_publishes_controller_class_policy_and_hides_a_missing_table(self):
        from test_fraktal_ab_projection import build
        held = data.policy_data(APP)
        held['ReadLevel'][0], held['WriteLevel'][0] = 2, 3
        values = build(data_policy=held)['values']
        self.assertEqual(values['Press/Access/ClassCount'], 2)
        self.assertEqual(values['Press/Access/Classes[1]/ClassId'], 'public')
        self.assertEqual(values['Press/Access/Classes[1]/ReadLevel'], 2)
        self.assertEqual(values['Press/Access/Classes[1]/WriteLevel'], 3)
        self.assertEqual(build()['values']['Press/Access/ClassCount'], 0)

    def test_edit_is_access_policy_gated_and_recomputes_levels_same_scan(self):
        c = controller(level=1)
        c.tags[access.tag(APP, 'State')]['Required'][8] = 3
        p = c.tags[data.tag(APP, 'Policy')]
        self.assertEqual(request(c, mb.SET_CLASS_LEVEL, NameValue='public', IntValue=2, BoolValue=1)['Accepted'], 0)
        self.assertEqual(p['WriteLevel'][0], 0)
        c.tags[access.tag(APP, 'State')]['CurrentLevel'] = 3
        self.assertEqual(request(c, mb.SET_CLASS_LEVEL, NameValue='public', IntValue=2, BoolValue=1)['Accepted'], 1)
        self.assertEqual(c.tags[data.tag(APP, 'Levels')]['WriteLevel'][mb.config_ordinal(APP, COUNTER) - 1], 2)

    def test_native_invalid_class_or_level_cannot_mutate_policy(self):
        for name, value, direction in (('', 1, 0), ('unknown', 1, 0), ('public', -1, 0), ('public', 5, 1), ('public', 2, 2)):
            c = controller()
            before = copy.deepcopy(c.tags[data.tag(APP, 'Policy')])
            self.assertEqual(request(c, mb.SET_CLASS_LEVEL, NameValue=name, IntValue=value, BoolValue=direction)['Accepted'], 0)
            self.assertEqual(c.tags[data.tag(APP, 'Policy')], before)

    def test_startup_keeps_edited_class_levels(self):
        c = controller()
        request(c, mb.SET_CLASS_LEVEL, NameValue='public', IntValue=2, BoolValue=1)
        c.tags['S:FS'] = True
        c.run('\n'.join(access.startup(APP)))
        c.run('\n'.join(data.cyclic(APP)))
        self.assertEqual(c.tags[data.tag(APP, 'Policy')]['WriteLevel'][0], 2)

    def test_read_minimum_raises_class_and_policy_change_moves_page_revision(self):
        app = with_access(APP, COUNTER, min_read_level=2)
        c = controller(app, 1)
        request(c, mb.QUERY_CONFIG, app)
        before, rows = entries(app, c.tags[data.tag(app, 'Levels')])
        self.assertEqual(rows[COUNTER]['ReadLevel'], 2)
        self.assertEqual(rows[COUNTER]['ValueText'], '')
        c.tags[access.tag(app, 'State')]['CurrentLevel'] = 4
        request(c, mb.SET_CLASS_LEVEL, app, NameValue='public', IntValue=3, BoolValue=0)
        after, rows = entries(app, c.tags[data.tag(app, 'Levels')])
        self.assertEqual(rows[COUNTER]['ReadLevel'], 3)
        self.assertNotEqual(before['Status/ConfigRev'], after['Status/ConfigRev'])

    def test_gateway_projects_plc_levels_without_recomputing_defaults(self):
        held = effective_levels()
        slot = mb.config_ordinal(APP, COUNTER) - 1
        held['ReadLevel'][slot], held['WriteLevel'][slot], held['Readable'][slot] = 4, 2, 0
        _page, rows = entries(APP, held)
        self.assertEqual((rows[COUNTER]['ReadLevel'], rows[COUNTER]['WriteLevel'], rows[COUNTER]['Readable'], rows[COUNTER]['ValueText']), (4, 2, False, ''))

    def test_missing_or_corrupt_levels_keep_metadata_without_value(self):
        for held in (None, {'SchemaVersion': 2}, {'SchemaVersion': 1, 'Count': 9, 'ReadLevel': []}):
            _page, rows = entries(APP, held, values={})
            self.assertEqual(len(rows), len(gen.editable_values(APP)))
            self.assertTrue(all(not row['Readable'] and row['ValueText'] == '' for row in rows.values()))

    def test_retained_class_policy_is_separate_and_external_read_only(self):
        self.assertEqual(access.STATE_SCHEMA, 3)
        root = ET.fromstring('<Tags>' + '\n'.join(data.tags(APP)) + '</Tags>')
        self.assertEqual({t.get('Name'): t.get('ExternalAccess') for t in root},
                         {data.tag(APP, 'Policy'): 'Read Only', data.tag(APP, 'Levels'): 'Read Only', data.tag(APP, 'Work'): 'None'})
        self.assertNotIn('Data', '\n'.join(access.startup(APP)))

    def test_template_and_press_both_declare_and_assign_classes(self):
        for app in (APP, template.application()):
            self.assertFalse(decl.validate(app))
            self.assertEqual({item.class_id for item in app.data_classes}, {'public', 'commissioning'})
            self.assertTrue(any(m.min_write_level == 3 for _o, _r, m in gen.editable_values(app)))

    def test_invalid_declarations_are_rejected_and_unknown_assignment_is_safe(self):
        for classes in ((decl.DataClass('', 'project.label'),), (decl.DataClass('x', 'std.label'),),
                        (decl.DataClass('x', 'project.label', -1),), (decl.DataClass('x', 'project.label', 0, 5),),
                        (decl.DataClass('x', 'project.label'),) * 2):
            self.assertTrue(decl.validate(dataclasses.replace(APP, data_classes=classes)))
        self.assertFalse(decl.validate(with_access(APP, COUNTER, class_id='ghost')))


class SetTransactions(unittest.TestCase):
    def send(self, c, document, kind, app=APP):
        q = c.tags[mb.request_tag_name(app)]
        sequence = q['Sequence'] + 1
        proposal = broker.staging(app, sequence, document=document, name=document[0]['set'], operation=kind)
        from test_fraktal_ab_access import string
        for n, k, width, _ in mb.REQUEST_MEMBERS:
            q[n] = string('', width) if k == mb.STRING_MEMBER else 0
        q.update(Kind=kind, Sequence=sequence, ConfigSet=proposal)
        c.run('\n'.join(mb.handler_logic(app)))
        return c.tags[mb.response_tag_name(app)]

    def test_set_load_refuses_first_inaccessible_record_before_any_commit(self):
        from test_fraktal_ab_sets import document
        c, doc = controller(level=2), document()
        before = copy.deepcopy(c.tags[APP.records[1].name + 'Tag'])
        doc[1]['value'] = '41'
        denied_index = next(i for i, record in enumerate(doc) if record.get('key') == CALIBRATION)
        answer = self.send(c, doc, mb.LOAD_CONFIG_SET)
        self.assertEqual((answer['Accepted'], answer['DiagnosticKey']), (0, mf.numeric_key(APP, access.DENIED)))
        self.assertEqual(c.tags[APP.records[1].name + 'Tag'], before)
        self.assertEqual(c.tags[sets.state_tag(APP)]['RejectIndex'], denied_index)
        c.tags[access.tag(APP, 'State')]['CurrentLevel'] = 3
        self.assertEqual(self.send(c, doc, mb.LOAD_CONFIG_SET)['Accepted'], 1)
        self.assertEqual(c.tags[APP.records[1].name + 'Tag']['StationNumber'], 41)

    def test_export_checks_every_record_even_when_requesting_only_header(self):
        from test_fraktal_ab_sets import document
        app = with_access(APP, CALIBRATION, min_read_level=3)
        c, doc = controller(app, 2), document(app)
        answer = self.send(c, doc, mb.EXPORT_CONFIG_SET, app)
        self.assertEqual((answer['Accepted'], answer['DiagnosticKey']), (0, mf.numeric_key(app, access.DENIED)))
        self.assertEqual(c.tags[sets.state_tag(app)]['RejectIndex'], next(i for i, row in enumerate(doc) if row.get('key') == CALIBRATION))
        c.tags[access.tag(app, 'State')]['CurrentLevel'] = 3
        self.assertEqual(self.send(c, doc, mb.EXPORT_CONFIG_SET, app)['Accepted'], 1)

    def test_save_and_delete_do_not_require_record_read_or_write_levels(self):
        c = controller(level=0)
        self.assertEqual(request(c, mb.SET_CLASS_LEVEL, NameValue='public', IntValue=4, BoolValue=0)['Accepted'], 1)
        for kind in (mb.SAVE_CONFIG_SET, mb.DELETE_CONFIG_SET):
            c.tags[gen.config_persist_tag(APP)]['Pending'] = 0
            doc = [{'set': 'saved', 'root': APP.name, 'schema': 1, 'configRev': mf.config_revision(APP), 'kind': 1, 'model': '', 'records': 0, 'created': 1790899200, 'clock': 0}]
            self.assertEqual(self.send(c, doc, kind)['Accepted'], 1)


if __name__ == '__main__':
    unittest.main()
