"""Core numeric schema and declaration-boundary checks, before native gates."""
from dataclasses import replace
import json
from pathlib import Path
import unittest
import tempfile
import fraktal_ab_generate as gen
import fraktal_ab_projection as legacy
import fraktal_ab_st_model as st
import fraktal_ab_canonical_metrics as metrics
import fraktal_ab_canonical_publication as pub
import fraktal_ab_genealogy_s3f_demo as previous


class MetricsSchemaTests(unittest.TestCase):
    def app(self):return replace(previous.application(),canonical_publication_stage=9)

    def test_incomplete_stage_cannot_generate_a_deployment_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'candidate.L5X'
            with self.assertRaisesRegex(ValueError,'S3g generation is gated'):
                gen.generate(self.app(),Path(temporary)/'unused_seed.L5X',output)
            self.assertFalse(output.exists())

    def test_exact_consumed_path_set_and_200_core_numeric_types(self):
        app=self.app();schema=pub.schema(app)
        inventory=json.loads((Path(__file__).resolve().parents[4]/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S3G_INVENTORY_2026-10-23.json').read_text())
        fields={}
        native={'BOOL':'Boolean','DINT':'Int32','INT':'Int16','REAL':'Float','LREAL':'Double'}
        def walk(kind,prefix):
            for member in schema[kind]:
                names=[f'{member.name}[{i}]' for i in range(member.lower,member.lower+member.count)] if member.count else [member.name]
                for name in names:
                    path=prefix+'/'+name
                    if member.kind in schema:walk(member.kind,path)
                    else:fields[path]='UInt32' if member.logical=='BITSTRING32' else 'String' if member.kind.startswith(pub.PREFIX+'String') else native[member.kind]
        for member in schema[pub.root_type(app)]:
            if member.name not in ('Oee','OeeTrend','OeeTrendHead','Profiler','SystemHealth'):continue
            if member.count:
                for i in range(member.lower,member.lower+member.count):walk(member.kind,f'{app.name}/{member.name}[{i}]')
            elif member.kind in schema:walk(member.kind,app.name+'/'+member.name)
            else:fields[app.name+'/'+member.name]=native[member.kind]
        self.assertEqual(set(fields),set(inventory['paths']))
        self.assertEqual({p:row['proposedCoreType'] for p,row in inventory['paths'].items()},fields)

    def test_int16_step_numbers_are_refused_without_clipping(self):
        app=self.app();chain=app.chains[0];step=chain.steps[0]
        for number in (-32769,32768):
            bad=replace(app,chains=(replace(chain,steps=(replace(step,number=number),*chain.steps[1:])),*app.chains[1:]))
            self.assertTrue(any('INT range' in finding for finding in metrics.validate(bad)))
        self.assertEqual(metrics.validate(app),[])

    def test_health_owner_values_unavailability_and_full_unsigned_wire_bits(self):
        app=self.app();schema=pub.schema(app)
        def value(kind):
            if kind.startswith(pub.PREFIX+'String'):return dict(LEN=0,DATA=[0]*pub.string_width(kind))
            if kind=='BOOL':return False
            if kind in ('REAL','LREAL'):return 0.0
            if kind not in schema:return 0
            return {m.name:([value(m.kind) for i in range(m.count)] if m.count else value(m.kind)) for m in schema[kind]}
        health=st.structure(gen.system_health_members());probe=st.structure(gen.health_probe_members())
        health.update(Present=1,Healthy=0,TaskAvailable=1,TaskOverrun=1)
        probe.update(IntervalUs=-1,JitterUs=-2147483648,TimeIsSynchronized=1,TimePtpEnable=1)
        root=value(pub.root_type(app))
        class Typed(st.Controller):
            def write(self,ref,v):
                holder,key=self._container(ref)
                if type(holder[key]) is bool:holder[key]=bool(v)
                elif type(holder[key]) is float:holder[key]=float(v)
                else:super().write(ref,v)
        plc=Typed({app.name:root,gen.system_health_tag(app):health,gen.health_probe_tag(app):probe})
        for ptp in (1,0):
            probe['TimePtpEnable']=ptp;plc.run('\n'.join(metrics.health(app)))
            actual={}
            def flat(kind,held,prefix):
                for m in schema[kind]:
                    p=prefix+'/'+m.name;v=held[m.name]
                    if m.kind in schema:flat(m.kind,v,p)
                    elif m.kind.startswith(pub.PREFIX+'String'):actual[p]=bytes(v['DATA'][:v['LEN']]).decode()
                    else:actual[p]=v&0xffffffff if m.logical=='BITSTRING32' else v
            flat(metrics.HEALTH,root['SystemHealth'],'SystemHealth')
            expected=legacy.system_health_status(app,health,probe)
            for name in ('TaskCycleUs','TaskJitterUs'):expected['SystemHealth/'+name]&=0xffffffff
            self.assertEqual(actual,expected)
            self.assertIs(actual['SystemHealth/ControllerAvailable'],False)
