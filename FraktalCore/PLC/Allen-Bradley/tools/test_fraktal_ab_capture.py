"""Execute generated capture ST: one authority, validation and bounded audit."""
import copy
import dataclasses
import unittest

import fraktal_ab_config as config
import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as mf
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
import fraktal_ab_station_template as template
from fraktal_ab_st_model import Controller

APP = demo.application()
KEY = 'press.recipe.baselineWorkMs'


def initial(members):
    return {m.name: [m.initial] * m.dimension if m.dimension else m.initial for m in members}


def controller(app=APP):
    tags = {gen.capture_source_tag(app, f'{p}.SchemaVersion').rsplit('.', 1)[0]: initial(ms)
            for p, ms in gen.root_field_records(app)}
    for module in app.modules:
        tags[gen.ctx_tag_for(app, module.name)] = initial(gen.module_members(module))
        for m in gen.module_members(module):
            if m.name.startswith('OutImm_'):
                tags[gen.ctx_tag_for(app, module.name)][m.name] = 1
    if app.access_users is not None:
        import fraktal_ab_access as access
        tags[access.tag(app, 'State')].update(CurrentLevel=4, UserLength=5, UserBytes=list(b'owner') + [0] * 27)
    tags[f'FRK_{app.name}_Unit']['Mode'] = app.manual_mode
    tags[f'FRK_{app.name}_Profiler']['LastWork'] = 970
    tags[gen.model_cfg_tag(app)] = [initial(ms) for ms in gen.model_cfg_elements(app)]
    tags[config.candidate_tag(app)] = 0
    tags.update({n: 0 for n in config.scratch_names(app)})
    tags[f'FRK_{app.name}_HmiWipe'] = 0
    tags[f'FRK_{app.name}_HmiLastSequence'] = 0
    tags[f'FRK_{app.name}_NowDate'] = 20261001
    tags[f'FRK_{app.name}_NowTime'] = 210000000
    tags[mb.request_tag_name(app)] = {
        'Kind': mb.CAPTURE_CONFIG, 'IntValue': mb.config_ordinal(app, KEY),
        'BoolValue': 999999, 'DurationMs': mf.config_revision(app), 'Sequence': 1,
        'User': {'LEN': 5, 'DATA': list(b'owner') + [0] * (mb.USER_LENGTH - 5)}}
    tags[mb.response_tag_name(app)] = {'Accepted': 0, 'DiagnosticKey': 0}
    # A commissioned controller after its first scan: the station image is
    # stamped (live documents leave it at zero only until their restore).
    station = gen.station_cfg_record(app)
    tags[f'{station.name}Tag']['SchemaVersion'] = station.schema_version
    c = Controller(tags)
    if app.line is not None:
        import fraktal_ab_line as line
        c.tags[line.tag(app, 'Work')] = initial(line.work_members())
    if app.access_users is not None:
        import fraktal_ab_access as access
        import fraktal_ab_data_access as data
        from test_fraktal_ab_data_access import level_controller
        fixture = level_controller(app)
        for name, value in fixture.tags.items():
            if name not in {access.tag(app, 'State'), mb.request_tag_name(app), f'FRK_{app.name}_HmiLastSequence'}:
                c.tags[name] = value
        c.tags[access.tag(app, 'Work')] = initial(access.work_members())
        c.calls.update(fixture.calls)
        c.run('\n'.join(data.cyclic(app)))
    from fraktal_ab_st_model import parse, StError
    audit = parse('\n'.join(config.audit_logic(app)))
    previous = c.calls.get('JSR')
    def jsr(plc, args):
        if app.line is not None:
            body = dict(line.routines(app)).get(args[0][1][0][1])
            if body is not None:
                return plc.run('\n'.join(body))
        if args[0][1][0][1] == config.audit_routine_name(app):
            return plc.run(audit)
        if previous:
            return previous(plc, args)
        raise StError('unexpected JSR ' + args[0][1][0][1])
    c.calls['JSR'] = jsr
    if app.model_capacity:
        import fraktal_ab_models as models
        import fraktal_ab_sets as sets
        c.tags[models.tag(app)] = initial(models.members(app))
        c.tags[gen.config_persist_tag(app)] = initial(gen.config_persist_members())
        for name in sets.scratch_names(app):
            c.tags[name] = 0
        c.run('\n'.join(gen._model_restore_logic(app, gen.config_persist_tag(app))))
    return c


def execute(c, app=APP, **request):
    c.tags[mb.request_tag_name(app)].update(request)
    c.tags[mb.response_tag_name(app)].update(Accepted=0, DiagnosticKey=0)
    c.run(f'CASE {mb.request_tag_name(app)}.Kind OF\n' + '\n'.join(config.write_dispatch(app)) + '\nEND_CASE;')
    return c.tags[mb.response_tag_name(app)]


class CaptureBehavior(unittest.TestCase):
    def test_every_grouped_capability_keeps_its_own_inclusive_range(self):
        for app in (APP, template.application()):
            for ordinal, record, member in gen.editable_values(app):
                for value in (member.minimum, member.maximum):
                    with self.subTest(station=app.name, key=member.write_key, value=value):
                        c = controller(app)
                        answer = execute(c, app, Kind=mb.WRITE_CONFIG, DurationMs=0,
                                         IntValue=ordinal, BoolValue=value)
                        self.assertEqual(answer['Accepted'], 1)
                        self.assertEqual(c.tags[record.name + 'Tag'][member.name], value)
                for value in (member.minimum - 1, member.maximum + 1):
                    if not -(2 ** 31) <= value < 2 ** 31:
                        continue  # values outside the native DINT are not wire candidates
                    with self.subTest(station=app.name, key=member.write_key, invalid=value):
                        c = controller(app)
                        before = copy.deepcopy({r.name: c.tags[r.name + 'Tag'] for r in app.records})
                        audit = copy.deepcopy(c.tags[config.audit_tag(app)])
                        answer = execute(c, app, Kind=mb.WRITE_CONFIG, DurationMs=0,
                                         IntValue=ordinal, BoolValue=value)
                        self.assertEqual(answer['Accepted'], 0)
                        self.assertEqual({r.name: c.tags[r.name + 'Tag'] for r in app.records}, before)
                        self.assertEqual(c.tags[config.audit_tag(app)], audit)

    def test_shared_audit_records_every_capability_with_its_own_metadata(self):
        c = controller()
        scoped = {m.name for m in gen.model_scoped_members(APP)}
        for ordinal, record, member in gen.editable_values(APP):
            answer = execute(c, Kind=mb.WRITE_CONFIG, IntValue=ordinal,
                             BoolValue=member.initial, DurationMs=0, Sequence=ordinal)
            self.assertEqual(answer['Accepted'], 1, member.write_key)
            audit = c.tags[config.audit_tag(APP)]
            slot = audit['Head'] - 1
            self.assertEqual((audit['Sequence'][slot], audit['Capability'][slot],
                              audit['Value'][slot], audit['SourceKey'][slot]),
                             (ordinal, ordinal, member.initial, 0), member.write_key)
            expected_model = c.tags[f'FRK_{APP.name}_Unit']['ModelOrdinal'] if member.name in scoped else 0
            self.assertEqual(audit['ModelOrdinal'][slot], expected_model, member.write_key)
            self.assertEqual(bytes(audit['UserBytes'][slot * 32:slot * 32 + audit['UserLength'][slot]]), b'owner')
        self.assertEqual(audit['Count'], min(config.AUDIT_CAPACITY, len(gen.editable_values(APP))))

    def test_one_native_audit_body_serves_all_declared_writes(self):
        import xml.etree.ElementTree as ET
        routines = ET.fromstring(gen.programs(APP)).findall('.//Routine')
        matches = [r for r in routines if r.get('Name') == config.audit_routine_name(APP)]
        self.assertEqual(len(matches), 1)
        body = '\n'.join(n.text or '' for n in matches[0].findall('.//Line'))
        self.assertEqual(body.count(config.audit_tag(APP) + '.UserBytes['), 2)  # copy or zero in the one loop
        mailbox = '\n'.join(mb.handler_logic(APP))
        self.assertEqual(mailbox.count(f'JSR({config.audit_routine_name(APP)},0);'), 1)
        self.assertNotIn(f'{config.audit_tag(APP)}.Head :=', mailbox)

    def test_the_machine_value_wins_over_a_client_candidate(self):
        c = controller()
        self.assertEqual(execute(c)['Accepted'], 1)
        self.assertEqual(c.tags[APP.records[0].name + 'Tag']['BaselineWorkMs'], 970)
        self.assertEqual(c.tags[config.audit_tag(APP)]['Value'][0], 970)

    def test_range_failure_changes_neither_configuration_nor_audit(self):
        for value in (-1, 600001):
            with self.subTest(value=value):
                c = controller()
                c.tags[gen.profiler_tag(APP)]['LastWork'] = value
                answer = execute(c)
                self.assertEqual(answer['DiagnosticKey'], mf.numeric_key(APP, mb.CONFIG_OUT_OF_RANGE_KEY))
                self.assertEqual(answer['Accepted'], 0)
                self.assertEqual(c.tags[APP.records[0].name + 'Tag']['BaselineWorkMs'], 950)
                self.assertEqual(c.tags[config.audit_tag(APP)]['Count'], 0)

    def test_both_inclusive_bounds_are_accepted(self):
        for value in (0, 600000):
            c = controller()
            c.tags[gen.profiler_tag(APP)]['LastWork'] = value
            self.assertEqual(execute(c)['Accepted'], 1)

    def test_an_editable_field_without_a_capture_refuses(self):
        c = controller()
        answer = execute(c, IntValue=mb.config_ordinal(APP, 'station.number'))
        self.assertEqual(answer['DiagnosticKey'], mf.numeric_key(APP, config.CAPTURE_UNAVAILABLE_KEY))
        self.assertEqual(c.tags[config.audit_tag(APP)]['Count'], 0)

    def test_unknown_ordinal_and_stale_revision_refuse(self):
        for req, reason in (({'IntValue': 0}, mb.CONFIG_KEY_UNKNOWN_KEY),
                            ({'DurationMs': 0}, config.CAPTURE_REVISION_KEY)):
            c = controller()
            self.assertEqual(execute(c, **req)['DiagnosticKey'], mf.numeric_key(APP, reason))
            self.assertEqual(c.tags[config.audit_tag(APP)]['Count'], 0)

    def test_ready_and_setup_are_controller_guards(self):
        for field, value in (('Running', 1), ('Mode', 0), ('Error', 1), ('Aborted', 1)):
            c = controller()
            c.tags[f'FRK_{APP.name}_Unit'][field] = value
            self.assertEqual(execute(c)['Accepted'], 0, field)
            self.assertEqual(c.tags[config.audit_tag(APP)]['Count'], 0)

    def test_a_missing_permissive_refuses(self):
        c = controller()
        for module in APP.modules:
            if module.name == 'AirPressureMonitor':
                c.tags[gen.ctx_tag_for(APP, module.name)]['OutImm_PressureOk'] = 0
        self.assertEqual(execute(c)['Accepted'], 0)

    def test_typed_write_uses_the_same_storage_and_audit(self):
        c = controller()
        self.assertEqual(execute(c, Kind=mb.WRITE_CONFIG, DurationMs=0, BoolValue=1100)['Accepted'], 1)
        audit = c.tags[config.audit_tag(APP)]
        self.assertEqual((audit['Value'][0], audit['Kind'][0], audit['SourceKey'][0]), (1100, mb.WRITE_CONFIG, 0))

    def test_a_running_model_blocks_its_write_but_not_preparing_another(self):
        c = controller()
        c.tags[f'FRK_{APP.name}_Unit']['Running'] = 1
        self.assertEqual(execute(c, Kind=mb.WRITE_CONFIG, DurationMs=0, BoolValue=1100)['Accepted'], 0)
        self.assertEqual(execute(c, Kind=mb.WRITE_CONFIG, DurationMs=2, BoolValue=1200)['Accepted'], 1)
        self.assertEqual(c.tags[APP.records[0].name + 'Tag']['BaselineWorkMs'], 950)
        self.assertEqual(c.tags[gen.model_cfg_tag(APP)][1]['BaselineWorkMs'], 1200)
        audit = c.tags[config.audit_tag(APP)]
        self.assertEqual(audit['ModelOrdinal'][0], 2)
        self.assertEqual(audit['Revision'][0], mf.config_revision(APP))

    def test_a_short_actor_replaces_all_bytes_of_the_previous_actor(self):
        c = controller()
        for seq in range(1, config.AUDIT_CAPACITY + 1):
            execute(c, Sequence=seq)
        import fraktal_ab_access as access
        c.tags[access.tag(APP, 'State')].update(UserLength=1, UserBytes=[ord('a')] + [ord('x')] * 31)
        execute(c, Sequence=config.AUDIT_CAPACITY + 1, User={'LEN': 7, 'DATA': list(b'spoofed') + [0] * 25})
        audit = c.tags[config.audit_tag(APP)]
        self.assertEqual(audit['UserBytes'][:mb.USER_LENGTH], [ord('a')] + [0] * (mb.USER_LENGTH - 1))

    def test_audit_wraps_with_no_missing_or_out_of_bounds_entry(self):
        c = controller()
        for seq in range(1, config.AUDIT_CAPACITY + 4):
            c.tags[gen.profiler_tag(APP)]['LastWork'] = 1000 + seq
            self.assertEqual(execute(c, Sequence=seq)['Accepted'], 1)
        audit = c.tags[config.audit_tag(APP)]
        self.assertEqual((audit['Head'], audit['Count']), (3, config.AUDIT_CAPACITY))
        self.assertEqual(audit['Sequence'][2], config.AUDIT_CAPACITY + 3)
        page = projection.config_audit_status(APP, mf.content(APP), audit)
        self.assertEqual(page['ConfigAudit/Entries[1]/ValueText'], str(1000 + config.AUDIT_CAPACITY + 3))
        self.assertEqual(page['ConfigAudit/Entries[1]/User'], 'owner')
        self.assertEqual(page['ConfigAudit/Entries[1]/CaptureSource'], 'Profiler.LastWork')
        self.assertEqual(page['ConfigAudit/Entries[1]/WriteKey'], KEY)

    def test_the_template_executes_the_same_mechanism(self):
        app = template.application()
        c = controller(app)
        self.assertEqual(execute(c, app, IntValue=mb.config_ordinal(app, 'cell.recipe.baselineWorkMs'))['Accepted'], 1)


class CaptureDeclaration(unittest.TestCase):
    def test_only_an_editable_root_scalar_can_be_a_capture(self):
        member = next(m for m in APP.records[0].members if m.capture_source)
        for replacement in (dataclasses.replace(member, write_key=''),
                            dataclasses.replace(member, dimension=2),
                            dataclasses.replace(member, capture_source='Profiler.HistoryWork'),
                            dataclasses.replace(member, capture_source='Door.OutImm_Extended'),
                            dataclasses.replace(member, capture_source='Profiler.LastWork; Bad := 1')):
            record = dataclasses.replace(APP.records[0], members=tuple(replacement if m == member else m for m in APP.records[0].members))
            app = dataclasses.replace(APP, records=(record,) + APP.records[1:])
            self.assertTrue(any('capture' in f for f in decl.validate(app)))

    def test_duplicate_write_keys_and_private_sources_are_rejected(self):
        record = APP.records[0]
        members = tuple(dataclasses.replace(m, write_key=KEY) if m.write_key else m for m in record.members)
        app = dataclasses.replace(APP, records=(dataclasses.replace(record, members=members),) + APP.records[1:])
        self.assertTrue(any('duplicate configuration write keys' in f for f in decl.validate(app)))
        members = tuple(dataclasses.replace(m, external_access='None') if m.name == 'BaselineWorkMs' else m
                        for m in record.members)
        # A private source is not a published scalar, even if the target is editable.
        members = tuple(dataclasses.replace(m, capture_source=record.name + '.BaselineWorkMs') if m.capture_source else m for m in members)
        app = dataclasses.replace(APP, records=(dataclasses.replace(record, members=members),) + APP.records[1:])
        self.assertTrue(any('capture source' in f for f in decl.validate(app)))

    def test_manifest_major_4_preserves_capture_in_the_enlarged_row(self):
        self.assertEqual(mf.MANIFEST_SCHEMA_MAJOR, 4)
        table = next(t for t in mf.tables(APP) if t.name == 'WriteCapabilities')
        self.assertTrue(table.row_type.endswith('V4'))
        rows = mf.content(APP)
        cap = next(r for r in rows['WriteCapabilities'] if r['CapabilityIndex'] == mb.config_ordinal(APP, KEY))
        self.assertEqual(cap['CaptureSourceKey'], mf.numeric_key(APP, 'Profiler.LastWork'))

    def test_gateway_cannot_supply_the_captured_value_or_retain_an_unknown_identity(self):
        prefix = APP.name + '/HmiRequest/'
        body = [('Kind', 'int32', mb.CAPTURE_CONFIG), ('TargetPath', 'string', APP.name),
                ('NameValue', 'string', KEY), ('IntValue', 'int32', mf.config_revision(APP)),
                ('BoolValue', 'int32', 777), ('Sequence', 'uint32', 9)]
        for target, name, ordinal in ((APP.name, KEY, mb.config_ordinal(APP, KEY)), ('Other', KEY, 0), (APP.name, 'absent', 0)):
            writes = [(prefix + m, t, target if m == 'TargetPath' else name if m == 'NameValue' else v) for m, t, v in body]
            resolved = mb.resolve_batch(APP, writes)
            fields = {p.rsplit('/', 1)[-1]: v for p, _t, v in resolved}
            self.assertEqual((fields['IntValue'], fields['BoolValue'], fields['DurationMs']), (ordinal, 0, mf.config_revision(APP)))
            self.assertEqual(resolved[-1], writes[-1])


if __name__ == '__main__':
    unittest.main()
