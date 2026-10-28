"""Execute the emitted PLC catalog transactions, including refusals."""
import copy
import unittest

import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mb
import fraktal_ab_models as models
import fraktal_ab_press_demo as demo
import fraktal_ab_sets as sets
import fraktal_ab_set_broker as broker
from test_fraktal_ab_sets import controller, document
from test_fraktal_ab_sets import BrokerAndController

APP = demo.application()


def command(c, code='NEW', source=1, doc=None, *, operation=mb.CREATE_MODEL, model_index=0, **changes):
    req = c.tags[mb.request_tag_name(APP)]
    req.update(Kind=operation, BoolValue=int(doc is not None), IntValue=source, DurationMs=model_index)
    c.tags[f'FRK_{APP.name}_HmiLastSequence'] = req['Sequence']
    q = broker.staging(APP, req['Sequence'], document=doc, name=code, kind=0, operation=operation)
    q['NameLength'] = len(code)
    q['NameBytes'] = list(code.encode()) + [0] * (80 - len(code))
    q.update(changes)
    req['ConfigSet'] = q
    response = c.tags[mb.response_tag_name(APP)]
    response.update(Accepted=0, DiagnosticKey=0)
    import fraktal_ab_access as access
    import fraktal_ab_data_access as data
    c.tags[access.tag(APP, 'Work')]['Permitted'] = 1
    c.run('\n'.join(data.reset_rejection(APP) + data.refresh(APP)))
    c.run('CASE ' + mb.request_tag_name(APP) + '.Kind OF\n' + '\n'.join(sets.dispatch(APP)) + '\nEND_CASE;')
    req['Sequence'] += 1
    return response['Accepted']


class Catalog(unittest.TestCase):
    def test_current_export_rejects_invalid_index_even_with_corrupt_count(self):
        for count, index in ((3, 9), (100, 99)):
            c = controller()
            c.tags[models.tag(APP)]['Count'] = count
            self.assertEqual(command(c, operation=mb.EXPORT_CURRENT_CONFIG, model_index=index), 0)

    def test_creation_clones_commissioned_values_and_does_not_activate(self):
        c = controller()
        c.tags[gen.model_cfg_tag(APP)][0]['PressDwellMs'] = 451
        active = copy.deepcopy(c.tags[APP.records[0].name + 'Tag'])
        ordinal = c.tags['FRK_Press_Unit']['ModelOrdinal']
        self.assertEqual(command(c), 1)
        self.assertEqual(models.decode(APP, c.tags[models.tag(APP)]), ['M-100', 'M-200', 'M-050', 'NEW'])
        self.assertEqual(c.tags[gen.model_cfg_tag(APP)][3]['PressDwellMs'], 451)
        self.assertEqual(c.tags[APP.records[0].name + 'Tag'], active)
        self.assertEqual(c.tags['FRK_Press_Unit']['ModelOrdinal'], ordinal)
        # A boot keeps the commissioned appended recipe and its stable index.
        c.run('\n'.join(gen._model_restore_logic(APP, gen.config_persist_tag(APP))))
        self.assertEqual(c.tags[gen.model_cfg_tag(APP)][3]['PressDwellMs'], 451)
        self.assertEqual(models.decode(APP, c.tags[models.tag(APP)])[-1], 'NEW')

    def test_duplicate_full_invalid_source_and_permission_fail_without_mutation(self):
        for code, source, change in [('M-100', 1, {}), ('BAD CODE', 1, {}), ('NEW', 9, {}),
                                     ('NEW', 1, {'NameLength': 81}), ('NEW', 1, {'ConfigRev': 0})]:
            c = controller()
            before = copy.deepcopy((c.tags[models.tag(APP)], c.tags[gen.model_cfg_tag(APP)]))
            self.assertEqual(command(c, code, source, **change), 0)
            self.assertEqual((c.tags[models.tag(APP)], c.tags[gen.model_cfg_tag(APP)]), before)
        c = controller()
        for index in range(5):
            self.assertEqual(command(c, 'NEW' + str(index)), 1)
        before = copy.deepcopy(c.tags[gen.model_cfg_tag(APP)])
        self.assertEqual(command(c, 'FULL'), 0)
        self.assertEqual(c.tags[gen.model_cfg_tag(APP)], before)
        import fraktal_ab_access as access
        c = controller()
        c.tags[access.tag(APP, 'State')]['CurrentLevel'] = 0
        c.tags[access.tag(APP, 'State')]['Required'][1] = 3
        import fraktal_ab_data_access as data
        c.tags[data.tag(APP, 'Policy')]['WriteLevel'] = [3] * len(APP.data_classes)
        self.assertEqual(command(c), 0)
        self.assertEqual(c.tags[models.tag(APP)]['Count'], 3)

    def test_complete_model_set_creates_a_recipe_and_bad_last_record_is_atomic(self):
        doc = document(APP, kind=0)
        doc[-1]['value'] = '1000'
        c = controller()
        self.assertEqual(command(c, doc=doc), 1)
        self.assertEqual(c.tags[gen.model_cfg_tag(APP)][3]['BaselineWorkMs'], 1000)
        for change in ('missing', 'duplicate', 'range', 'type', 'station'):
            c = controller()
            bad = copy.deepcopy(doc)
            if change == 'missing': bad.pop(); bad[0]['records'] -= 1
            if change == 'duplicate': bad[-1] = copy.deepcopy(bad[1])
            if change == 'range': bad[-1]['value'] = '2147483647'
            if change == 'type': bad[-1]['type'] = 2
            if change == 'station': bad[-1]['kind'] = 1
            before = copy.deepcopy(c.tags[gen.model_cfg_tag(APP)])
            self.assertEqual(command(c, doc=bad), 0, change)
            self.assertEqual(c.tags[gen.model_cfg_tag(APP)], before, change)

    def test_corrupt_retained_catalog_fails_closed(self):
        for member, value in [('Count', 9), ('SchemaVersion', 2), ('CodeLength', 100000)]:
            c = controller()
            if member == 'CodeLength': c.tags[models.tag(APP)][member][0] = value
            else: c.tags[models.tag(APP)][member] = value
            c.run('\n'.join(models.restore(APP, gen.config_persist_tag(APP))))
            self.assertEqual(c.tags[models.tag(APP)]['Count'], 0)
            self.assertEqual(c.tags[gen.config_persist_tag(APP)]['RestoreLost'], 1)

    def test_changeover_start_ignores_air_and_home_auto_keep_it(self):
        import fraktal_ab_st_model as st
        from test_fraktal_ab_capture import initial
        c = controller()
        c.tags[gen.start_release_tag(APP)] = initial(gen.release_report_members())
        c.tags[gen.alarm_active_tag(APP)]['Blocking'] = 0
        c.tags[gen.ctx_tag_for(APP, 'AirPressureMonitor')]['OutImm_PressureOk'] = 0
        for mode, blocked in [(demo.MODE_AUTO, True), (demo.MODE_HOME, True), (demo.MODE_CHANGEOVER, False)]:
            c.tags['FRK_Press_Unit']['Mode'] = mode
            c.run('\n'.join(gen.start_release_logic(APP)))
            report = c.tags[gen.start_release_tag(APP)]
            keys = report['Key'][:report['Count']]
            import fraktal_ab_manifest as mf
            self.assertEqual(mf.numeric_key(APP, 'project.condition.airPressureOk') in keys, blocked)
        # Module movement still requires air in every mode.
        self.assertTrue(all(m.area_safe for m in APP.modules if m.commands))


class BrokerCatalog(unittest.TestCase):
    setUp = BrokerAndController.setUp
    command = BrokerAndController.command
    def test_export_current_does_not_consume_a_saved_set_slot_and_is_immutable(self):
        answer = self.command(mb.EXPORT_CURRENT_CONFIG, TextValue='current', IntValue=1, DurationMs=0)
        self.assertEqual(answer['Accepted'], 1)
        header = sets.parse_line(self.session.values['Press/ConfigSetDocument'])
        self.assertEqual(header['kind'], 1)
        self.assertEqual(self.store.list(), [])
        station = next(r for r in APP.records if r.station_cfg)
        self.comm.c.tags[station.name + 'Tag']['StationNumber'] = 41
        self.command(mb.EXPORT_CONFIG_SET, TextValue='current', IntValue=1)
        row = sets.parse_line(self.session.values['Press/ConfigSetDocument'])
        self.assertEqual(row['value'], '1')

    def test_create_from_stored_model_set_and_export_new_model(self):
        self.assertEqual(self.command(mb.SAVE_CONFIG_SET, TextValue='recipe', IntValue=0)['Accepted'], 1)
        self.assertEqual(self.command(mb.CREATE_MODEL, NameValue='NEW', TextValue='recipe', BoolValue=True)['Accepted'], 1)
        self.assertEqual(self.command(mb.EXPORT_CURRENT_CONFIG, TextValue='new', IntValue=0, DurationMs=4)['Accepted'], 1)
        header = sets.parse_line(self.session.values['Press/ConfigSetDocument'])
        self.assertEqual(header['model'], 'NEW')

    def test_known_previous_catalog_revision_migrates_but_arbitrary_revision_refuses(self):
        import dataclasses
        import fraktal_ab_manifest as mf
        doc = document(APP, name='older', kind=0)
        # The historical pre-catalog press, which also predates live documents.
        revision = mf.config_revision(dataclasses.replace(APP, model_capacity=0, config_medium=None))
        for row in doc:
            row['configRev' if 'set' in row else 'rev'] = revision
        self.store.save(doc)
        self.assertEqual(self.command(mb.CREATE_MODEL, NameValue='OLDER', TextValue='older', BoolValue=True)['Accepted'], 1)
        for row in doc:
            row['configRev' if 'set' in row else 'rev'] = 42
        self.store.save(doc)
        self.assertEqual(self.command(mb.CREATE_MODEL, NameValue='UNKNOWN', TextValue='older', BoolValue=True)['Accepted'], 0)


class InitialConfiguration(unittest.TestCase):
    def test_image_preserves_only_valid_configuration_and_frozen_tag_serialization(self):
        import fraktal_ab_initial_config as image_module
        from test_fraktal_ab_capture import initial
        image = {'records': {r.name: initial(r.members) for r in APP.records},
                 'models': [initial(m) for m in gen.model_cfg_elements(APP)[:len(APP.models)]],
                 'modelOrdinal': 1}
        for r in APP.records: image['records'][r.name]['SchemaVersion'] = r.schema_version
        for model in image['models']: model['SchemaVersion'] = gen.model_cfg_schema_version(APP)
        station = next(r for r in APP.records if r.station_cfg)
        image['records'][station.name]['AirPressureMinKpa'] = 451
        original = gen.controller_tags(APP)
        applied = image_module.apply(APP, original, image)
        self.assertEqual(applied.count('<![CDATA['), original.count('<![CDATA['))
        self.assertIn('Name="AirPressureMinKpa" DataType="DINT" Radix="Decimal" Value="451"', applied)
        bad = copy.deepcopy(image)
        bad['records'][station.name]['AirPressureMinKpa'] = 2147483647
        with self.assertRaises(ValueError): image_module.apply(APP, original, bad)
        bad = copy.deepcopy(image)
        bad['records'][station.name]['SchemaVersion'] = 99
        with self.assertRaises(ValueError): image_module.apply(APP, original, bad)


if __name__ == '__main__':
    unittest.main()
