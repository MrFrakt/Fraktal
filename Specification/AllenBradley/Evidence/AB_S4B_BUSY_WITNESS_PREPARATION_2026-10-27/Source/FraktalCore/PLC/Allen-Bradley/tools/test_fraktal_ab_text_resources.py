import copy
import contextlib
from dataclasses import replace
import json
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_host_events as host
import fraktal_ab_host_sink as sink
import fraktal_ab_ld_model as ld
import fraktal_ab_manifest as manifest
import fraktal_ab_resource_demo as numeric
import fraktal_ab_resources as resources
import fraktal_ab_sets as sets
import fraktal_ab_st_model as st
import fraktal_ab_text_resource_demo as fixture
import test_fraktal_ab_part as part_helpers

APP = fixture.application()
CHAIN = next(chain for chain in APP.chains if chain.name == 'AUTO')
STEP = next(step for step in CHAIN.steps if step.number == 230)


def changed(step, **app_values):
    return replace(APP, chains=tuple(replace(chain, steps=tuple(
        step if item.number == step.number else item for item in chain.steps))
        if chain.name == CHAIN.name else chain for chain in APP.chains), **app_values)


def setup(app=APP):
    with patch.object(part_helpers, 'APP', app):
        plc = part_helpers.setup()
    plc.tags[gen.Names(app,in_aoi=False).cfg] = st.structure(app.records[0].members)
    def emit(model, args):
        local = st.Controller(dict(Ring=model.read(args[1]), Slot=0, ByteIndex=0, UidIndex=0,
            TextActive=0, TextEnd=0, SourceIndex=0,
            **{name: model.eval(value) for name,value in zip(
                ('Kind','ModelOrdinal','EventValue','Verdict','Reason'),args[2:])}))
        local.run('\n'.join(host.emit_logic(app)))
    def service(model, args):
        with patch.object(part_helpers, 'APP', app):
            part_helpers.service_callback(model, args, emit=emit)
    plc.calls.update({host.emitter_name(app): emit, part_helpers.part.service_name(app): service})
    return plc


def events(plc, app=APP):
    return host.decode(app, plc.tags[host.tag(app)], [model.code for model in app.models])['events']


def mark(plc, step=STEP, app=APP):
    plc.run('\n'.join(resources.marks(app, step, gen.Names(app, in_aoi=False))))


class Declaration(unittest.TestCase):
    def test_opt_in_versions_compact_data_and_exact_prior_declaration(self):
        old = numeric.application()
        self.assertEqual(decl.validate(APP), [])
        self.assertEqual((host.schema(old), host.schema(APP)), (3,4))
        self.assertEqual(resources.without_text(APP), old)
        self.assertNotEqual(gen.unit_aoi_name(old), gen.unit_aoi_name(APP))
        self.assertNotEqual(part_helpers.part.service_name(old), part_helpers.part.service_name(APP))
        self.assertEqual(sum((m.dimension or 1)*4 for m in host.members(APP))
            -sum((m.dimension or 1)*4 for m in host.members(old)), 1736)
        self.assertEqual(host.emitter(APP), host.emitter(replace(APP, part_carrier=None)))

    def test_literal_bounds_ascii_and_mutually_exclusive_sources(self):
        for text in ('', 'a'*80, 'Quotes: \' " $ ]]> \\', '~'*80):
            self.assertEqual(resources.validate(changed(replace(STEP,
                resource_value=decl.ResourceText(literal=text)))), [])
        for value in (decl.ResourceText(), decl.ResourceText(literal='a'*81),
                      decl.ResourceText(literal='é'), decl.ResourceText(literal='a\0b'),
                      decl.ResourceText(literal='a\nb'), decl.ResourceText(literal='\x7f'),
                      decl.ResourceText(literal='x',source='PressRam.TimLast'),
                      decl.ResourceText(literal='x',source=0),
                      decl.ResourceText(source='PressRam.TimLast[0]'),
                      decl.ResourceText(source='PressRam.TimLast + 1'),
                      decl.ResourceText(source='Cfg.PressDwellMs'), decl.ResourceText(source='Unknown.Text')):
            with self.subTest(value=value):
                self.assertTrue(resources.validate(changed(replace(STEP,resource_value=value))))
        self.assertEqual(resources.validate(changed(replace(STEP,
            resource_value=decl.ResourceText(source='PressRam.TimLast')))), [])

    def test_exact_prior_config_revision_accepted_unrelated_refused(self):
        guard = sets.revision_rejected(APP, 'Revision')
        for app in (APP, numeric.application(), resources.without(APP)):
            plc = st.Controller(dict(Revision=manifest.config_revision(app), Refused=0))
            plc.run('Refused := ' + guard + ';')
            self.assertFalse(plc.tags['Refused'])
        plc = st.Controller(dict(Revision=123, Refused=0))
        plc.run('Refused := ' + guard + ';')
        self.assertTrue(plc.tags['Refused'])

    def test_text_literal_source_and_subject_bind_build_identity(self):
        baseline = manifest.content_hash(APP)
        for values in (dict(resource_value=decl.ResourceText(literal=fixture.VALUE+'X')),
                       dict(resource_value=decl.ResourceText(source='PressRam.TimLast')),
                       dict(resource_subject='OtherSubject')):
            self.assertNotEqual(baseline, manifest.content_hash(changed(replace(STEP,**values))))


class Runtime(unittest.TestCase):
    def test_literal_capture_empty_and_maximum_width_and_json_escape(self):
        for text in ('', fixture.VALUE, '~'*80):
            plc = setup()
            mark(plc, replace(STEP,resource_value=decl.ResourceText(literal=text)))
            event = events(plc)[0]
            self.assertEqual((event['Value'],event['Subject'],event['PartUid']), (text,fixture.SUBJECT,''))
            self.assertEqual(json.loads(json.dumps(event)), event)

    def test_live_array_captured_once_and_later_change_cannot_rewrite_history(self):
        plc = setup()
        source = gen.Names(APP,in_aoi=False).module('PressRam')
        plc.tags[source] = st.structure(gen.module_members(next(m for m in APP.modules if m.name=='PressRam')))
        plc.tags[source]['TimLast'] = [ord(c) for c in 'LOT-A']+[0]*3
        mark(plc,replace(STEP,resource_value=decl.ResourceText(source='PressRam.TimLast')))
        plc.tags[source]['TimLast'][:] = [88]*8
        self.assertEqual(events(plc)[0]['Value'],'LOT-A')
        mark(plc,replace(STEP,resource_value=decl.ResourceText(source='PressRam.TimLast')))
        self.assertEqual([event['Value'] for event in events(plc)],['LOT-A','XXXXXXXX'])

    def test_literal_and_array_have_st_sfc_ld_parity_after_regular_marks(self):
        for language in decl.RENDITIONS:
            for step in (STEP, replace(STEP,part_action='',part_record=0,part_value='',
                    resource_value=decl.ResourceText(source='PressRam.TimLast'))):
                with self.subTest(language=language, value=step.resource_value):
                    plc = setup()
                    names = gen.Names(APP,in_aoi=False)
                    module = next(m for m in APP.modules if m.name=='PressRam')
                    plc.tags[names.module('PressRam')] = st.structure(gen.module_members(module))
                    plc.tags[names.module('PressRam')]['TimLast'] = [76,79,84,0,0,0,0,0]
                    with patch.object(part_helpers,'APP',APP): part_helpers.perform(plc,'receive')
                    plc.tags[names.unit].update(Step=230,PrevStep=230,Running=1)
                    index = gen.ordered_steps(APP).index(230)
                    if language==decl.LD:
                        plc.tags[gen.ld_advanced_tag(APP)] = 0
                        ld.run_rung(plc,gen.ld_step_rung(APP,CHAIN,step,index,names))
                    elif language==decl.SFC:
                        plc.run('\n'.join(gen.sfc_action_logic(APP,CHAIN,step,index,names)))
                    else:
                        plc.run('\n'.join(gen.step_logic(APP,CHAIN,step,index,names)[1:]))
                    self.assertEqual(events(plc)[-1]['Value'],fixture.VALUE if step==STEP else 'LOT')

    def test_bad_source_latches_stream_failure_before_any_partial_append(self):
        for cells in ([65,0,66]+[0]*78, [-1]+[0]*80, [127]+[0]*80, [65]*81):
            plc = setup()
            mark(plc)
            ring = plc.tags[host.tag(APP)]
            before = copy.deepcopy(ring)
            ring['PendingText'][:] = cells
            plc.run(host.call(APP,'MATERIAL_CHANGED')+';')
            self.assertEqual(ring['Failed'],1)
            for name in (*host.META[:-1],*host.COLUMNS,'Uid','ValueFormat','ValueText'):
                self.assertEqual(ring[name],before[name],name)
            with self.assertRaises(host.HostEventsBad): events(plc)

    def test_text_numeric_and_nonresource_records_clear_each_others_storage(self):
        plc = setup()
        mark(plc,replace(STEP,resource_value=decl.ResourceText(literal='x'*80)))
        numeric_step = next(step for step in CHAIN.steps if step.number==145)
        mark(plc,numeric_step)
        plc.run(host.call(APP,'MODE_CHANGED',value='0')+';')
        self.assertEqual([event['Value'] for event in events(plc)],['x'*80,'314','0'])
        ring = plc.tags[host.tag(APP)]
        self.assertEqual(ring['ValueFormat'][:3],[1,0,0])
        self.assertFalse(any(ring['ValueText'][resources.TEXT_WORDS:3*resources.TEXT_WORDS]))
        self.assertEqual(ring['PendingTextEnabled'],0)

    def test_part_event_ignores_stale_text_capture_and_clears_its_slot(self):
        plc = setup()
        mark(plc)
        with patch.object(part_helpers,'APP',APP): part_helpers.perform(plc,'receive')
        rows = events(plc)
        self.assertEqual([row['Kind'] for row in rows],[8,1])
        self.assertEqual(rows[1]['Value'],'')
        ring = plc.tags[host.tag(APP)]
        self.assertEqual(ring['PendingTextEnabled'],1)
        self.assertEqual(ring['ValueFormat'][:2],[1,0])
        self.assertFalse(any(ring['ValueText'][resources.TEXT_WORDS:2*resources.TEXT_WORDS]))

    def test_wrong_physical_schema_and_pending_format_refused(self):
        plc = setup()
        mark(plc)
        with self.assertRaises(host.HostEventsBad): host.decode(numeric.application(),plc.tags[host.tag(APP)])
        raw = copy.deepcopy(plc.tags[host.tag(APP)])
        raw['SchemaVersion'] = 3
        with self.assertRaises(host.HostEventsBad): host.decode(APP,raw)
        ring = plc.tags[host.tag(APP)]
        before = ring['NewestSequence']
        ring['PendingTextEnabled'] = 2
        plc.run(host.call(APP,'MATERIAL_CHANGED')+';')
        self.assertEqual((ring['NewestSequence'],ring['Failed']),(before,1))

    def test_wrap_empty_value_and_long_tail_clear_with_no_client_accumulation(self):
        plc = setup()
        for index in range(20):
            mark(plc,replace(STEP,resource_value=decl.ResourceText(literal=str(index) if index%2 else '')))
        batch = host.decode(APP,plc.tags[host.tag(APP)])
        self.assertEqual([event['Value'] for event in batch['events']],
                         [str(index) if index%2 else '' for index in range(4,20)])
        output = []
        self.assertTrue(host.Cursor(APP.name).deliver(batch,lambda row:output.append(row) or True))
        self.assertEqual(output[0]['reason'],'ringOverwritten')

    def test_malformed_wire_format_bytes_tail_and_nonresource_text_refused(self):
        plc = setup()
        mark(plc)
        valid = plc.tags[host.tag(APP)]
        cases = [('ValueFormat',0,2), ('ValueFormat',0,True), ('ValueFormat',0,0),
                 ('ValueText',0,-1), ('ValueText',0,2**31), ('ValueText',0,True),
                 ('ValueText',0,31), ('ValueText',20,65), ('Value',0,1), ('Kind',0,9)]
        for field,index,value in cases:
            raw = copy.deepcopy(valid)
            raw[field][index] = value
            with self.subTest(field=field,value=value), self.assertRaises(host.HostEventsBad):
                host.decode(APP,raw)
        for field in ('ValueText','ValueFormat'):
            raw = copy.deepcopy(valid)
            raw[field].pop()
            with self.assertRaises(host.HostEventsBad): host.decode(APP,raw)

    def test_whole_cycle_in_all_languages_and_transactional_sink_replay(self):
        import test_fraktal_ab_rendition_cycle as cycle
        for language in CHAIN.renditions:
            with self.subTest(language=language), patch.multiple(cycle,APP=APP,AUTO=CHAIN,
                    ORDER=gen.ordered_steps(APP),NAMES=gen.Names(APP,in_aoi=False)):
                bench,stores = cycle.Press(language),setup()
                for key in (part_helpers.part.tag(APP),part_helpers.part.carrier_tag(APP),host.tag(APP)):
                    bench.plc.tags[key] = stores.tags[key]
                bench.plc.calls.update(stores.calls)
                bench.one_cycle()
                rows = events(bench.plc)
                self.assertEqual([row['Kind'] for row in rows],[1,8,2,7,8,3])
                self.assertEqual(rows[-2]['Value'],fixture.VALUE)
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory)/'events.sqlite'
                    batch = host.decode(APP,bench.plc.tags[host.tag(APP)])
                    with sink.SqliteSink(path,APP.name,source='fixture') as database:
                        for _ in range(2):
                            self.assertTrue(host.Cursor(APP.name,source='fixture').deliver(batch,database))
                        self.assertEqual(database.connection.execute('SELECT COUNT(*) FROM Events').fetchone(),(6,))


class FixtureGuards(unittest.TestCase):
    def test_arm_declaration_serial_and_existing_output_refuse_before_credentials(self):
        import fraktal_ab_text_resource_execute as execute
        for armed,declaration,serial in ((False,'fraktal_ab_text_resource_demo','601FC87B'),
                (True,'fraktal_ab_resource_demo','601FC87B'),
                (True,'fraktal_ab_text_resource_demo','00000001')):
            with self.subTest(armed=armed,declaration=declaration,serial=serial), \
                 patch.object(execute.station,'module_name',return_value=declaration), \
                 contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                execute.main([*(['--execute-fixture'] if armed else []),'--expect-serial',serial,
                    '--credential-file','absent.json','--output','absent.json'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'evidence.json'
            path.write_text('preserve')
            with patch.object(execute.station,'module_name',return_value='fraktal_ab_text_resource_demo'), \
                 contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                execute.main(['--execute-fixture','--expect-serial','601FC87B',
                    '--credential-file','absent.json','--output',str(path)])
            self.assertEqual(path.read_text(),'preserve')


if __name__=='__main__': unittest.main()
