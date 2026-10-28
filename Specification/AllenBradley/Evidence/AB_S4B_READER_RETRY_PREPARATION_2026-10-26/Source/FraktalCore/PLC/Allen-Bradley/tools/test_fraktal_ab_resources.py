import copy
import contextlib
from dataclasses import replace
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_host_events as host
import fraktal_ab_ld_model as ld
import fraktal_ab_manifest as manifest
import fraktal_ab_resource_demo as fixture
import fraktal_ab_resources as resource
import fraktal_ab_sets as sets
import fraktal_ab_st_model as st
import fraktal_ab_tower_demo as tower
import test_fraktal_ab_part as helpers

APP = fixture.application()
CHAIN = next(chain for chain in APP.chains if chain.name == 'AUTO')
STEP = next(step for step in CHAIN.steps if step.number == 145)


def changed(step, **app_values):
    return replace(APP, chains=tuple(replace(chain, steps=tuple(
        step if item.number == step.number else item for item in chain.steps))
        if chain.name == CHAIN.name else chain for chain in APP.chains), **app_values)


class Declaration(unittest.TestCase):
    def test_opt_in_versions_and_same_bounded_identity_storage(self):
        self.assertEqual(decl.validate(APP), [])
        old = tower.application()
        self.assertEqual((host.schema(old), host.schema(APP)), (2, 3))
        self.assertNotEqual(gen.unit_aoi_name(old), gen.unit_aoi_name(APP))
        self.assertNotEqual(helpers.part.service_name(old), helpers.part.service_name(APP))
        self.assertEqual([(m.name, m.dimension) for m in host.members(old)],
                         [(m.name, m.dimension) for m in host.members(APP)])
        self.assertNotEqual(manifest.content_hash(old), manifest.content_hash(APP))

    def test_invalid_kind_subject_and_value_refuse_before_emission(self):
        cases = [dict(resource_kind='FAULT'), dict(resource_kind=''), dict(resource_subject=''),
                 dict(resource_subject='x'*64), dict(resource_subject='nonascii-é'),
                 dict(resource_subject='line\nbreak'), dict(resource_value=True),
                 dict(resource_value=2**31), dict(resource_value=-2**31-1),
                 dict(resource_value='Cfg.PressDwellMs + 1'), dict(resource_value='Unknown.Value'),
                 dict(action=decl.AWAIT)]
        for values in cases:
            with self.subTest(values=values):
                self.assertTrue(resource.validate(changed(replace(STEP, **values))))
        self.assertTrue(resource.validate(replace(APP, host_event_capacity=0)))

    def test_only_exact_existing_scalar_or_literal_is_admitted(self):
        for value in (-2**31, 2**31-1, 0, 'Cfg.PressDwellMs', 'Ctx.GoodCount', 'PressRam.OutImm_Pos'):
            with self.subTest(value=value):
                self.assertEqual(resource.validate(changed(replace(STEP, resource_value=value))), [])

    def test_old_configuration_identity_is_exact_and_unrelated_revision_refuses(self):
        old = tower.application()
        self.assertEqual(resource.without(APP), old)
        guard = sets.revision_rejected(APP, 'Revision')
        for revision, refused in ((manifest.config_revision(old), False),
                                  (manifest.config_revision(APP), False), (123, True)):
            plc = st.Controller(dict(Revision=revision, Refused=0))
            plc.run('Refused := ' + guard + ';')
            self.assertEqual(bool(plc.tags['Refused']), refused)

    def test_every_producer_fact_changes_manifest_identity(self):
        for values in (dict(resource_subject='OtherDie'), dict(resource_value=315),
                       dict(resource_kind='MATERIAL_CHANGED')):
            self.assertNotEqual(manifest.content_hash(APP),
                                manifest.content_hash(changed(replace(STEP, **values))))

    def test_named_v3_emitter_has_one_body_with_or_without_part_composition(self):
        self.assertEqual(host.emitter(APP), host.emitter(replace(APP, part_carrier=None)))


class Runtime(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(helpers, 'APP', APP))

    def setup(self):
        plc = helpers.setup()
        plc.tags[gen.Names(APP, in_aoi=False).cfg] = st.structure(APP.records[0].members)
        return plc

    def events(self, plc):
        return host.decode(APP, plc.tags[host.tag(APP)], [m.code for m in APP.models])['events']

    def test_confirmation_snapshots_live_scalar_and_separates_subject_from_part_uid(self):
        plc = self.setup()
        helpers.perform(plc, 'receive')
        identity = self.events(plc)[0]['PartUid']
        names = gen.Names(APP, in_aoi=False)
        step = replace(STEP, resource_value='Cfg.PressDwellMs')
        plc.tags[names.cfg]['PressDwellMs'] = 271
        plc.run('\n'.join(resource.marks(APP, step, names)))
        plc.tags[names.cfg]['PressDwellMs'] = 999
        helpers.perform(plc, 'start')
        rows = self.events(plc)
        self.assertEqual([r['Kind'] for r in rows], [1,7,2])
        self.assertEqual((rows[1]['Subject'], rows[1]['Value'], rows[1]['PartUid']),
                         (STEP.resource_subject, '271', ''))
        self.assertEqual(rows[0]['PartUid'], rows[2]['PartUid'])
        self.assertEqual(rows[2]['PartUid'], identity)
        self.assertTrue(all(not r['Subject'] for r in (rows[0], rows[2])))

    def test_each_rendition_snapshots_the_same_signed_dint_value(self):
        for language in decl.RENDITIONS:
            with self.subTest(language=language):
                plc = self.setup()
                step = replace(STEP, resource_value=-2147483648)
                names = gen.Names(APP, in_aoi=False)
                unit = plc.tags[names.unit]
                helpers.perform(plc, 'receive')
                unit.update(Step=145, PrevStep=145, Running=1)
                index = gen.ordered_steps(APP).index(145)
                if language == decl.LD:
                    plc.tags[gen.ld_advanced_tag(APP)] = 0
                    ld.run_rung(plc, gen.ld_step_rung(APP, CHAIN, step, index, names))
                elif language == decl.SFC:
                    plc.run('\n'.join(gen.sfc_action_logic(APP, CHAIN, step, index, names)))
                else:
                    plc.run('\n'.join(gen.step_logic(APP, CHAIN, step, index, names)[1:]))
                self.assertEqual(self.events(plc)[-1]['Value'], '-2147483648')

    def test_failed_part_confirmation_does_not_publish_a_resource_event(self):
        for language in decl.RENDITIONS:
            with self.subTest(language=language):
                plc = self.setup()
                # Failed carrier read faults the owning receive helper.
                names = gen.Names(APP, in_aoi=False)
                step = next(step for step in CHAIN.steps if step.number == 105)
                plc.tags[helpers.part.carrier_tag(APP)]['ProviderIdx'] = 0
                plc.tags[names.unit].update(Step=105, PrevStep=105, Running=1)
                index = gen.ordered_steps(APP).index(105)
                if language == decl.LD:
                    plc.tags[gen.ld_advanced_tag(APP)] = 0
                    ld.run_rung(plc, gen.ld_step_rung(APP, CHAIN, step, index, names))
                elif language == decl.SFC:
                    plc.run('\n'.join(gen.sfc_action_logic(APP, CHAIN, step, index, names)))
                else:
                    plc.run('\n'.join(gen.step_logic(APP, CHAIN, step, index, names)[1:]))
                self.assertTrue(plc.tags[names.unit]['Error'])
                self.assertEqual(self.events(plc), [])

    def test_resource_value_observes_step_marks_in_every_language(self):
        for language in decl.RENDITIONS:
            with self.subTest(language=language):
                plc = self.setup()
                helpers.perform(plc, 'receive')
                names = gen.Names(APP, in_aoi=False)
                plc.tags[names.unit].update(Step=145, PrevStep=145, Running=1)
                step = replace(STEP, marks=('Ctx.ReportedCount := Ctx.ReportedCount + 1',),
                               resource_value='Ctx.ReportedCount')
                index = gen.ordered_steps(APP).index(145)
                if language == decl.LD:
                    plc.tags[gen.ld_advanced_tag(APP)] = 0
                    ld.run_rung(plc, gen.ld_step_rung(APP, CHAIN, step, index, names))
                elif language == decl.SFC:
                    plc.run('\n'.join(gen.sfc_action_logic(APP, CHAIN, step, index, names)))
                else:
                    plc.run('\n'.join(gen.step_logic(APP, CHAIN, step, index, names)[1:]))
                self.assertEqual(self.events(plc)[-1]['Value'], '1')

    def test_whole_cycle_emits_each_confirmed_resource_once_in_all_languages(self):
        import test_fraktal_ab_rendition_cycle as cycle
        for language in CHAIN.renditions:
            with self.subTest(language=language), patch.multiple(cycle, APP=APP, AUTO=CHAIN,
                ORDER=gen.ordered_steps(APP), NAMES=gen.Names(APP, in_aoi=False)):
                bench, stores = cycle.Press(language), self.setup()
                for key in (helpers.part.tag(APP), helpers.part.carrier_tag(APP), host.tag(APP)):
                    bench.plc.tags[key] = stores.tags[key]
                bench.plc.calls.update(stores.calls)
                bench.one_cycle()
                rows = self.events(bench.plc)
                self.assertEqual([r['Kind'] for r in rows], [1,8,2,7,3])
                self.assertEqual([r['Value'] for r in rows if r['Kind'] in (7,8)], ['20261018','314'])
                self.assertEqual(bench.plc.tags['FRK_Press_Unit']['GoodCount'], 1)

    def test_subject_tail_is_cleared_and_ring_wrap_keeps_captured_values(self):
        plc = self.setup()
        names = gen.Names(APP, in_aoi=False)
        for index in range(20):
            step = replace(STEP, resource_subject='LongSubject' if index == 0 else 'X', resource_value=index)
            plc.run('\n'.join(resource.marks(APP, step, names)))
        batch = host.decode(APP, plc.tags[host.tag(APP)])
        self.assertEqual([r['Value'] for r in batch['events']], list(map(str, range(4,20))))
        self.assertTrue(all(r['Subject'] == 'X' and not r['PartUid'] for r in batch['events']))
        sent = []
        host.Cursor(APP.name).deliver(batch, lambda row: sent.append(row) or True)
        self.assertEqual(sent[0]['reason'], 'ringOverwritten')

    def test_empty_corrupt_or_oversize_subject_and_bad_resource_value_are_bad(self):
        plc = self.setup()
        plc.run('\n'.join(resource.marks(APP, STEP, gen.Names(APP, in_aoi=False))))
        for value in ([0]*64, [65]*64, [-1]+[0]*63, [65,0,66]+[0]*61):
            raw = copy.deepcopy(plc.tags[host.tag(APP)])
            raw['Uid'][:64] = value
            with self.subTest(value=value), self.assertRaises(host.HostEventsBad):
                host.decode(APP, raw)
        raw = copy.deepcopy(plc.tags[host.tag(APP)])
        raw['Value'][0] = 2**31
        with self.assertRaises(host.HostEventsBad):
            host.decode(APP, raw)

    def test_resource_profile_without_carrier_does_not_admit_part_events(self):
        app = replace(APP, part_carrier=None)
        raw = st.structure(host.members(app))
        raw.update(NowDate=20261018, NowTime=123456789, EpochLow=1, EpochHigh=2)
        def emit(plc, args):
            model = st.Controller(dict(Ring=plc.read(args[1]), Slot=0, ByteIndex=0, UidIndex=0,
                **{n:plc.eval(v) for n,v in zip(('Kind','ModelOrdinal','EventValue','Verdict','Reason'),args[2:])}))
            model.run('\n'.join(host.emit_logic(app)))
        plc = st.Controller({host.tag(app):raw}, calls={host.emitter_name(app):emit})
        plc.run('\n'.join(resource.marks(app, STEP, gen.Names(app, in_aoi=False))))
        self.assertEqual(host.decode(app, raw)['events'][0]['Kind'], 7)
        with self.assertRaises(ValueError):
            host.call(app, 'PART_RECEIVED')
        raw['Kind'][0] = 1
        with self.assertRaises(host.HostEventsBad):
            host.decode(app, raw)


class NativeFixtureGuards(unittest.TestCase):
    def test_arm_declaration_and_serial_refuse_before_credentials_or_connection(self):
        import fraktal_ab_resource_execute as execute
        for armed, declaration, serial in ((False,'fraktal_ab_resource_demo','601FC87B'),
                (True,'fraktal_ab_tower_demo','601FC87B'),
                (True,'fraktal_ab_resource_demo','00000001')):
            with self.subTest(armed=armed,declaration=declaration,serial=serial), \
                 patch.object(execute.station,'module_name',return_value=declaration), \
                 contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                execute.main([*(['--execute-fixture'] if armed else []), '--expect-serial',serial,
                    '--credential-file','absent.json','--output','absent.json'])

    def test_existing_output_is_never_replaced(self):
        import fraktal_ab_resource_execute as execute
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'evidence.json'
            path.write_text('preserve')
            with patch.object(execute.station,'module_name',return_value='fraktal_ab_resource_demo'), \
                 contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                execute.main(['--execute-fixture','--expect-serial','601FC87B',
                    '--credential-file','absent.json','--output',str(path)])
            self.assertEqual(path.read_text(), 'preserve')


if __name__ == '__main__':
    unittest.main()
