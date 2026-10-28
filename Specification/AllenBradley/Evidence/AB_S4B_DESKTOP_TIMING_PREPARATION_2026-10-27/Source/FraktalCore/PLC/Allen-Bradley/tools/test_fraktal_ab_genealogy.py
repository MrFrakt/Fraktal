import copy
import contextlib
import io
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fraktal_ab_declaration as decl
import fraktal_ab_genealogy as gene
import fraktal_ab_genealogy_demo as fixture
import fraktal_ab_generate as gen
import fraktal_ab_host_events as host
import fraktal_ab_host_sink as sink
import fraktal_ab_ld_model as ld
import fraktal_ab_manifest as manifest
import fraktal_ab_part as part
import fraktal_ab_resources as resources
import fraktal_ab_sets as sets
import fraktal_ab_st_model as st
import fraktal_ab_text_resource_demo as old
import test_fraktal_ab_part as helpers
import test_fraktal_ab_text_resources as text_helpers

APP = fixture.application()
CHAIN = next(chain for chain in APP.chains if chain.name=='AUTO')
STEP = next(step for step in CHAIN.steps if step.number==230)


class FixtureGuards(unittest.TestCase):
    def test_refuses_unarmed_wrong_declaration_serial_and_existing_output(self):
        import fraktal_ab_genealogy_execute as execute
        for armed,declaration,serial in ((False,'fraktal_ab_genealogy_demo','601FC87B'),
                (True,'fraktal_ab_text_resource_demo','601FC87B'),
                (True,'fraktal_ab_genealogy_demo','00000001')):
            with self.subTest(armed=armed,declaration=declaration,serial=serial), \
                 patch.object(execute.station,'module_name',return_value=declaration), \
                 contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                execute.main([*(['--execute-fixture'] if armed else []),'--expect-serial',serial,
                    '--credential-file','absent.json','--output','absent.json'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'evidence.json'
            path.write_text('preserve')
            with patch.object(execute.station,'module_name',return_value='fraktal_ab_genealogy_demo'), \
                 contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                execute.main(['--execute-fixture','--expect-serial','601FC87B',
                    '--credential-file','absent.json','--output',str(path)])
            self.assertEqual(path.read_text(),'preserve')


def setup(app=APP):
    return text_helpers.setup(app)


def perform(plc, action, app=APP, **kwargs):
    plc.run(part.call(app,action,**kwargs)+';')


def confirm(plc, values=fixture.PARENTS, app=APP):
    step = replace(STEP,part_parents=tuple(decl.AsciiSource(literal=value) for value in values))
    plc.run('\n'.join(gene.marks(app,step,gen.Names(app,in_aoi=False))))


def events(plc, app=APP):
    return host.decode(app,plc.tags[host.tag(app)],[model.code for model in app.models])['events']


class Declaration(unittest.TestCase):
    def test_opt_in_new_types_and_exact_previous_declaration(self):
        self.assertEqual(decl.validate(APP),[])
        self.assertEqual(gene.without(APP),old.application())
        self.assertEqual((part.schema(APP),host.schema(APP)),(2,5))
        for owner in (part.type_name,part.carrier_name,part.service_name,gen.unit_aoi_name,host.type_name,host.emitter_name):
            self.assertNotEqual(owner(APP),owner(old.application()))
        no_text = resources.without_text(APP)
        self.assertNotEqual(host.type_name(APP),host.type_name(no_text))
        self.assertNotEqual(host.emitter_name(APP),host.emitter_name(no_text))
        self.assertNotEqual(gen.unit_aoi_name(APP),gen.unit_aoi_name(no_text))
        self.assertNotIn('ValueText',{member.name for member in host.members(no_text)})
        self.assertIn('ParentWords',{member.name for member in host.members(no_text)})

    def test_bad_capacity_missing_consumer_and_unsupported_parent_sources_refuse(self):
        for capacity in (-1,9,True,'2'):
            app = replace(APP,part_carrier=replace(APP.part_carrier,genealogy_capacity=capacity))
            self.assertTrue(decl.validate(app))
        for values in ((),(decl.AsciiSource(literal=''),),(decl.AsciiSource(literal='x'*65),),
                       (decl.AsciiSource(literal='é'),),(decl.AsciiSource(source='Ctx.GoodCount'),)):
            app = replace(APP,chains=tuple(replace(chain,steps=tuple(replace(step,part_parents=values)
                if step.number==230 else step for step in chain.steps)) if chain.name=='AUTO' else chain for chain in APP.chains))
            self.assertTrue(gene.validate(app))
        self.assertTrue(part.validate(replace(APP,part_carrier=None)))
        self.assertTrue(gene.validate(replace(APP,part_carrier=replace(APP.part_carrier,genealogy_capacity=0))))

    def test_identity_binds_parent_values_and_cfg_accepts_only_exact_predecessor(self):
        app = replace(APP,part_carrier=replace(APP.part_carrier,genealogy_capacity=3))
        self.assertNotEqual(manifest.content_hash(APP),manifest.content_hash(app))
        app = replace(APP,chains=tuple(replace(chain,steps=tuple(replace(step,
            part_parents=(decl.AsciiSource(literal='OTHER-COMPONENT'),)) if step.number==230 else step
            for step in chain.steps)) if chain.name=='AUTO' else chain for chain in APP.chains))
        self.assertNotEqual(manifest.content_hash(APP),manifest.content_hash(app))
        guard = sets.revision_rejected(APP,'Revision')
        for revision, expected in ((manifest.config_revision(APP),False),
                (manifest.config_revision(old.application()),False),(123,True)):
            plc = st.Controller(dict(Revision=revision,Refused=0))
            plc.run('Refused := '+guard+';')
            self.assertEqual(bool(plc.tags['Refused']),expected)


class Runtime(unittest.TestCase):
    def test_parent_only_mark_failure_blocks_each_language_transition(self):
        step = replace(STEP,part_action='',part_record=0,part_value='',
                       part_parents=(decl.AsciiSource(source='PressRam.TimLast'),),
                       resource_kind='',resource_subject='',resource_value=0)
        names = gen.Names(APP,in_aoi=False)
        for language in ('ST','SFC','LD'):
            with self.subTest(language=language):
                plc = setup()
                perform(plc,'receive')
                module = next(module for module in APP.modules if module.name=='PressRam')
                plc.tags[names.module('PressRam')] = st.structure(gen.module_members(module))
                plc.tags[names.unit]['Step'] = step.number
                if language == 'LD':
                    plc.tags[gen.ld_advanced_tag(APP)] = 0
                    ld.run_rung(plc,gen.ld_step_rung(APP,CHAIN,step,0,names))
                    self.assertEqual(plc.tags[gen.ld_advanced_tag(APP)],0)
                elif language == 'SFC':
                    plc.run('\n'.join(gen.sfc_action_logic(APP,CHAIN,step,0,names)))
                else:
                    plc.run('\n'.join(gen.step_logic(APP,CHAIN,step,0,names)[1:]))
                self.assertEqual(plc.tags[names.unit]['ErrorID'],part.REASONS['RESULT_RECORD_REJECTED'])
                self.assertNotEqual(plc.tags[names.unit]['Step'],step.on_advance)
                plc.tags['TransitionAllowed'] = 1
                plc.run('TransitionAllowed := '+gen.sfc_condition(APP,step,'A',names)+';')
                self.assertFalse(plc.tags['TransitionAllowed'])
                self.assertEqual(plc.tags[part.tag(APP)]['ParentCount'],0)

    def test_confirm_replay_commit_before_event_and_new_part_clears_only_live_context(self):
        plc = setup()
        perform(plc,'receive')
        identity = part.uid(plc.tags[part.tag(APP)]['Uid'])
        confirm(plc)
        confirm(plc)
        context,carrier = plc.tags[part.tag(APP)],plc.tags[part.carrier_tag(APP)]
        self.assertEqual(context['ParentCount'],2)
        self.assertEqual(len(events(plc)),1)
        self.assertEqual(gene.uids(context['Parents'],2,2,identity),list(fixture.PARENTS))
        emitter = plc.calls[host.emitter_name(APP)]
        seen = []
        def checked_emit(model,args):
            if model.eval(args[2])==3:
                seen.append(carrier['Writes'])
                self.assertEqual(carrier['LastParentCount'],2)
                self.assertEqual(carrier['LastParents'],context['Parents'])
            emitter(model,args)
        # The Part service owns its emitter closure. Rebind its call through a
        # modeled native service with the checking emitter at its actual call.
        def checked_service(model,args):
            with patch.object(helpers,'APP',APP): helpers.service_callback(model,args,emit=checked_emit)
        plc.calls[part.service_name(APP)] = checked_service
        perform(plc,'processed',verdict=1)
        self.assertEqual(seen,[1])
        self.assertEqual(events(plc)[-1]['Parents'],list(fixture.PARENTS))
        perform(plc,'receive')
        self.assertEqual(context['ParentCount'],0)
        self.assertFalse(any(context['Parents']))
        self.assertEqual(events(plc)[1]['Parents'],list(fixture.PARENTS))
        self.assertEqual(events(plc)[-1]['Parents'],[])
        self.assertEqual(carrier['LastParentCount'],2)

    def test_batch_rejection_is_atomic_for_empty_control_tail_self_and_capacity(self):
        cases = [('GOOD',''),('GOOD','bad\n'),('GOOD','A\0B')]
        for values in cases:
            plc = setup()
            perform(plc,'receive')
            context = plc.tags[part.tag(APP)]
            before = context['Parents'][:]
            confirm(plc,values)
            self.assertEqual((context['ParentCount'],context['Parents']),(0,before))
            self.assertEqual(plc.tags['FRK_Press_Unit']['ErrorID'],part.REASONS['RESULT_RECORD_REJECTED'])
        plc = setup()
        perform(plc,'receive')
        identity = part.uid(plc.tags[part.tag(APP)]['Uid'])
        confirm(plc,(identity,))
        self.assertEqual(plc.tags[part.tag(APP)]['ParentCount'],0)
        plc = setup()
        perform(plc,'receive')
        confirm(plc,('FIRST',))
        before = plc.tags[part.tag(APP)]['Parents'][:]
        confirm(plc,('SECOND','THIRD'))
        self.assertEqual(plc.tags[part.tag(APP)]['ParentCount'],1)
        self.assertEqual(plc.tags[part.tag(APP)]['Parents'],before)

    def test_duplicate_inputs_are_idempotent_and_full_width_uid_is_preserved(self):
        plc = setup()
        perform(plc,'receive')
        confirm(plc,('~'*64,'~'*64))
        self.assertEqual(plc.tags[part.tag(APP)]['ParentCount'],1)
        perform(plc,'processed',verdict=1)
        self.assertEqual(events(plc)[-1]['Parents'],['~'*64])

    def test_live_array_snapshot_and_part_projection_are_bounded_and_stable(self):
        plc = setup()
        perform(plc,'receive')
        names = gen.Names(APP,in_aoi=False)
        module = next(module for module in APP.modules if module.name=='PressRam')
        plc.tags[names.module('PressRam')] = st.structure(gen.module_members(module))
        plc.tags[names.module('PressRam')]['TimLast'] = [65,66,67,0,0,0,0,0]
        step = replace(STEP,part_parents=(decl.AsciiSource(source='PressRam.TimLast'),))
        plc.run('\n'.join(gene.marks(APP,step,names)))
        plc.tags[names.module('PressRam')]['TimLast'][:] = [88]*8
        projected = part.project(APP,plc.tags[part.tag(APP)])
        self.assertEqual(projected['Part/Parents[1]'],'ABC')
        self.assertEqual(projected['Part/Parents[2]'],'')
        self.assertEqual(projected['Part/ParentCapacity'],2)
        perform(plc,'aborted')
        self.assertEqual(events(plc)[-1]['Parents'],['ABC'])
        self.assertEqual(plc.tags[part.carrier_tag(APP)]['Writes'],0)
        self.assertEqual(set(projected),set(part.project(APP,plc.tags[part.tag(APP)])))

    def test_complete_step_and_cycle_st_sfc_ld_parity(self):
        import test_fraktal_ab_rendition_cycle as cycle
        for language in CHAIN.renditions:
            with self.subTest(language=language),patch.multiple(cycle,APP=APP,AUTO=CHAIN,
                    ORDER=gen.ordered_steps(APP),NAMES=gen.Names(APP,in_aoi=False)):
                bench,stores = cycle.Press(language),setup()
                for key in (part.tag(APP),part.carrier_tag(APP),host.tag(APP)):
                    bench.plc.tags[key] = stores.tags[key]
                bench.plc.calls.update(stores.calls)
                bench.one_cycle()
                rows = events(bench.plc)
                self.assertEqual([row['Kind'] for row in rows],[1,8,2,7,8,3])
                self.assertTrue(all(not row['Parents'] for row in rows[:-1]))
                self.assertEqual(rows[-1]['Parents'],list(fixture.PARENTS))
                self.assertEqual(bench.plc.tags[part.carrier_tag(APP)]['LastParentCount'],2)

    def test_bad_host_and_live_genealogy_never_project_as_good(self):
        plc = setup()
        perform(plc,'receive')
        confirm(plc)
        perform(plc,'processed',verdict=1)
        valid = plc.tags[host.tag(APP)]
        for field,index,value in [('ParentCount',1,3),('ParentCount',1,True),
                ('ParentWords',32,-1),('ParentWords',32,31),('ParentCount',0,1)]:
            raw = copy.deepcopy(valid)
            raw[field][index] = value
            with self.subTest(field=field,value=value),self.assertRaises(host.HostEventsBad): host.decode(APP,raw)
        raw = copy.deepcopy(plc.tags[part.tag(APP)])
        raw['ParentCount'] = 3
        with self.assertRaises(part.PartBad): part.project(APP,raw)
        raw = copy.deepcopy(plc.tags[part.tag(APP)])
        raw['Parents'][64:128] = raw['Parents'][:64]
        with self.assertRaises(part.PartBad): part.project(APP,raw)

    def test_host_wrap_and_durable_replay_keep_historical_parents(self):
        plc = setup()
        for index in range(10):
            perform(plc,'receive')
            confirm(plc,(f'COMPONENT-{index}',))
            perform(plc,'processed',verdict=1)
        batch = host.decode(APP,plc.tags[host.tag(APP)])
        processed = [row for row in batch['events'] if row['Kind']==3]
        self.assertEqual([row['Parents'] for row in processed],[[f'COMPONENT-{i}'] for i in range(2,10)])
        projected = host.project(batch)
        self.assertTrue(any(value=='COMPONENT-9' for key,value in projected.items() if '/Parents[' in key))
        with tempfile.TemporaryDirectory() as directory:
            with sink.SqliteSink(Path(directory)/'genealogy.sqlite',APP.name,source='fixture') as database:
                for _ in range(2):
                    self.assertTrue(host.Cursor(APP.name,source='fixture').deliver(batch,database))
                self.assertEqual(database.connection.execute('SELECT COUNT(*) FROM Events').fetchone(),(17,))


if __name__=='__main__': unittest.main()
