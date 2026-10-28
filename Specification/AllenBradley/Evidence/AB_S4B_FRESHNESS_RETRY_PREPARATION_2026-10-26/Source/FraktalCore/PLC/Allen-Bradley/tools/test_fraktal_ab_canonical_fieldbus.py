"""Execute emitted S3j ST against an independent legacy-word oracle."""
from copy import deepcopy
from dataclasses import replace
import json
import random
import re
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import fraktal_ab_canonical_fieldbus as bus
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_manifest as wire
import fraktal_ab_genealogy_s3j_demo as demo
import fraktal_ab_genealogy_s3i_demo as prior
import fraktal_ab_s3j_reference as reference
import fraktal_ab_st_model as st
from test_fraktal_ab_s3g_metrics import NativeRealModel


def value(schema,kind,initial=None):
    if kind.startswith(pub.PREFIX+'String'):
        raw=(initial or '').encode();return dict(LEN=len(raw),DATA=list(raw)+[0]*(pub.string_width(kind)-len(raw)))
    if kind=='BOOL':return bool(initial)
    if kind in ('REAL','LREAL'):return float(initial or 0)
    if kind not in schema:return initial or 0
    initial=initial or {}
    return {m.name:([value(schema,m.kind,x) for x in initial.get(m.name,[None]*m.count)] if m.count
            else value(schema,m.kind,initial.get(m.name))) for m in schema[kind]}


class FieldbusBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.app=app=demo.application();self.schema=s=pub.schema(app)
        self.root=value(s,bus.TOPOLOGY,bus.initial(app))
        self.work=value(s,bus.WORK,dict(BadDiagnostic=bus.BAD_MAPPING,ModuleMasks=[65535],NodeSources=[0,0,0]))
        self.sample={n:0 for n in bus.SAMPLE_FIELDS}
        self.tags={bus.tag(app):self.root,bus.work_tag(app):self.work,
            bus.samples_tag(app):[dict(self.sample)],bus.descriptors_tag(app):bus.descriptor_rows(app),
            app.io_modules[0].sample_tag:self.sample,'S:FS':True,
            'FRK_Press_ForceMask':0,'FRK_Press_ForcePermitted':0}
        self.plc=NativeRealModel(self.tags,calls={'CPS':st.cps_structure},routines=dict(bus.routines(app)))

    def scan(self):
        with patch.object(st,'_wrap',lambda n:(n+(1<<63))%(1<<64)-(1<<63)):
            self.plc.run(st.parse('\n'.join(bus.cyclic(self.app))))
        self.tags['S:FS']=False

    def actual(self):
        result={}
        def walk(kind,data,path):
            if kind.startswith(pub.PREFIX+'String'):
                result[path]=bytes(x&255 for x in data['DATA'][:data['LEN']]).decode();return
            for m in self.schema[kind]:
                target=path+'/'+m.name
                if m.count:
                    count=data[m.count_path.rsplit('/',1)[-1]] if m.count_path else m.extent or m.count
                    for i,item in enumerate(data[m.name][:count],m.lower):walk(m.kind,item,target+f'[{i}]') if m.kind in self.schema or m.kind.startswith(pub.PREFIX+'String') else result.update({target+f'[{i}]':item})
                elif m.kind in self.schema or m.kind.startswith(pub.PREFIX+'String'):walk(m.kind,data[m.name],target)
                else:result[target]=bool(data[m.name]) if m.kind=='BOOL' else data[m.name]
        walk(bus.TOPOLOGY,self.root,bus.canonical_root(self.app))
        return result

    def assert_oracle(self,*,valid=True):
        expected=reference.values(self.app,self.tags[bus.samples_tag(self.app)],mapping_valid=valid)
        actual=self.actual();self.assertEqual(actual,expected)
        self.assertEqual({p:type(v) for p,v in actual.items()},{p:type(v) for p,v in expected.items()})

    def test_operational_fault_inhibited_offline_and_partial_samples(self):
        vectors=[{},dict(InputValid=1,OutputValid=1,FaultValid=1),dict(InputValid=1,OutputValid=1,FaultValid=1,FaultWord=4),
                 dict(InputValid=1,OutputValid=1,FaultValid=1,FaultWord=65535),dict(InputValid=1,FaultValid=1),
                 dict(OutputValid=1,FaultValid=1),dict(InputValid=1,OutputValid=1),dict(InputValid=2,OutputValid=1,FaultValid=1)]
        for v in vectors:
            self.sample.update({k:0 for k in self.sample});self.sample.update(v,InputWord=0x49,OutputWord=0x85)
            self.scan();self.assert_oracle()

    def test_random_word_vectors_and_fault_masks_match_exactly(self):
        rng=random.Random(20261024)
        for unused in range(40):
            self.sample.update(InputWord=rng.randrange(-2**31,2**31),OutputWord=rng.randrange(-2**31,2**31),
                               FaultWord=rng.randrange(-2**31,2**31),InputValid=rng.randrange(2),OutputValid=rng.randrange(2),FaultValid=rng.randrange(2))
            self.scan();self.assert_oracle()

    def test_partial_input_sample_is_good_without_claiming_module_operational(self):
        self.sample.update(InputValid=1,FaultValid=1);self.scan();self.assert_oracle()
        self.assertEqual(self.root['Nodes'][0]['State'],0)
        self.assertTrue(self.root['Nodes'][1]['Channels'][0]['Quality'])
        self.assertFalse(self.root['Nodes'][2]['Channels'][0]['Quality'])

    def test_duplicate_identity_or_corrupt_mapping_fails_closed(self):
        for mutation in ('name','path','dir','count','name_length','path_length'):
            self.setUp();self.sample.update(InputValid=1,OutputValid=1,FaultValid=1)
            a,b=self.root['Nodes'][1]['Channels'][:2]
            if mutation=='name':b['Name']=deepcopy(a['Name'])
            elif mutation=='path':b['Path']=deepcopy(a['Path'])
            elif mutation=='dir':a['Dir']=8
            elif mutation=='name_length':a['Name']['LEN']=81
            elif mutation=='path_length':a['Path']['LEN']=256
            else:self.root['Nodes'][1]['ChannelCount']=13
            self.scan();self.assertFalse(self.root['MappingValid'])
            self.assertFalse(any(c['Quality'] for n in self.root['Nodes'] for c in n['Channels']))
            diag=self.root['MappingDiagnostic'];self.assertEqual(bytes(diag['DATA'][:diag['LEN']]).decode(),bus.BAD_MAPPING)

    def test_gate_absent_means_no_force_capability_and_no_physical_write(self):
        self.sample.update(InputValid=1,OutputValid=1,FaultValid=1)
        self.tags.update(FRK_Press_ForceMask=1,FRK_Press_ForcePermitted=1)
        self.scan();self.assert_oracle()
        self.assertTrue(self.root['Nodes'][2]['Channels'][0]['Forced'])
        self.assertFalse(any(c['Forceable'] for n in self.root['Nodes'] for c in n['Channels']))
        lines='\n'.join(bus.forcing(self.app));self.assertNotIn('Local:',lines);self.assertIn('ForcePermitted := 0;',lines)


class FieldbusEngineeringTests(unittest.TestCase):
    def test_declared_bounds_word_children_types_and_private_exclusions(self):
        app=demo.application();self.assertEqual(pub.validate(app),[])
        layout=bus.nodes(app);self.assertEqual([(n.name,n.parent,len(n.channels)) for n in layout],[('Discrete_IO',0,0),('Discrete_IO.I',1,12),('Discrete_IO.O',1,8)])
        s=pub.schema(app);m={m.name:m for m in s[bus.NODE]};self.assertEqual(m['Channels'].count,12)
        self.assertEqual({m.name:m.kind for m in s[bus.CHANNEL]}['AnalogValue'],'REAL')
        self.assertFalse({'ForcesEnabled','ForceBool','ForceAnalog'}&{m.name for m in s[bus.CHANNEL]})
        self.assertEqual({m.name:m.kind for m in s[bus.NODE]}['ChannelCount'],'INT')
        tags=ET.fromstring('<Tags>'+''.join(pub.tags(app))+'</Tags>')
        self.assertEqual(tags.find("Tag[@Name='FRK_Press_SimIo']").get('ExternalAccess'),'Read/Write')
        self.assertEqual(tags.find(f"Tag[@Name='{bus.samples_tag(app)}']").get('ExternalAccess'),'None')
        self.assertEqual(tags.find(f"Tag[@Name='{bus.tag(app)}']").get('ExternalAccess'),'Read Only')

    def test_identity_changes_invalidate_the_manifest_binding(self):
        app=demo.application();m=app.io_modules[0]
        changed=replace(app,io_modules=(replace(m,channels=(replace(m.channels[0],name='Changed'),*m.channels[1:])),))
        self.assertNotEqual(pub.manifest_values(app)['ContentHash'],pub.manifest_values(changed)['ContentHash'])
        self.assertNotEqual(bus.tag(app),bus.tag(changed))

    def test_empty_product_does_not_allocate_ceilings_or_dummy_snapshot_rows(self):
        app=replace(demo.application(),io_modules=(),canonical_io_fixture=False)
        h=pub.manifest_values(app);self.assertEqual(h['DataProducts'],[])
        self.assertEqual(reference.values(app,[]),{})
        self.assertNotIn(bus.TOPOLOGY,pub.schema(app))
        self.assertEqual(bus.products(prior.application()),[])

    def test_bad_width_bounds_and_source_aliases_are_refused(self):
        app=demo.application();m=app.io_modules[0]
        for changed in (replace(app,canonical_type_manifest=False),replace(app,canonical_table_driven=False),
                        replace(app,io_modules=(replace(m,data_width=33),)),replace(app,io_modules=(replace(m,type_id='x'*81),)),
                        replace(app,io_modules=(replace(m,sample_tag='bad.path'),)),replace(app,io_modules=(m,m))):
            self.assertTrue(bus.validate(changed))

    def test_generated_st_has_no_array_reference_inside_a_subscript(self):
        lines='\n'.join(x for unused,body in bus.routines(demo.application()) for x in body)
        self.assertNotRegex(lines,r'\[[^\]\n]*\[')


if __name__=='__main__':unittest.main()
