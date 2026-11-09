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
import struct
import fraktal_ab_st_model as st

def f32(v):
    return struct.unpack('f', struct.pack('f', float(v)))[0]

class NativeRealModel(st.Controller):
    def eval(self, node):
        if node[0] == 'bin':
            op = node[1]
            a = self.eval(node[2])
            b = self.eval(node[3])
            if type(a) is float or type(b) is float:
                if op in ('+', '-', '*', '/'):
                    a, b = f32(a), f32(b)
                    if op == '/':
                        return f32(a / b)
                    return f32({'+': lambda: a + b, '-': lambda: a - b, '*': lambda: a * b}[op]())
                return {'=': a == b, '<>': a != b, '<': a < b, '>': a > b, '<=': a <= b, '>=': a >= b}[op]
        return super().eval(node)

    def write(self, ref, value):
        holder, key = self._container(ref)
        if type(holder[key]) is bool:
            holder[key] = bool(value)
        elif type(holder[key]) is float:
            holder[key] = f32(value)
        else:
            super().write(ref, value)

def topology(app, io_state: dict | None):
    if not app.io_modules:
        return {}
    root = f"{app.name}Fieldbus/Topology"
    values = {
        f"{root}/NodeCount": len(app.io_modules),
        f"{root}/MappingValid": True,
        f"{root}/MappingDiagnostic": "",
    }
    for index, module in enumerate(app.io_modules, start=1):
        node = f"{root}/Nodes[{index}]"
        state = (io_state or {}).get(module.address)
        live = state is not None and all(key in state for key in ("input", "output", "fault"))
        fault_known = state is not None and "fault" in state
        faults = (state or {}).get("fault", 0)
        forced = (state or {}).get("forced", 0)
        force_permitted = bool((state or {}).get("forcePermitted", 0))
        mask = (1 << module.data_width) - 1
        inhibited = live and (faults & mask) == mask
        if not live or inhibited:
            node_state = 0
        elif faults:
            node_state = 5
        else:
            node_state = 4
        values.update({
            f"{node}/Name": module.name,
            f"{node}/DescriptionKey": module.description_key,
            f"{node}/TypeId": module.type_id,
            f"{node}/Address": module.address,
            f"{node}/State": node_state,
            f"{node}/LinkOk": node_state == 4,
            f"{node}/ParentIdx": 0,
            f"{node}/ChannelCount": len(module.channels),
        })
        for position, channel in enumerate(module.channels, start=1):
            leaf = f"{node}/Channels[{position}]"
            outward = channel.direction == 1
            direction = "output" if outward else "input"
            sampled = state is not None and direction in state
            word = (state or {}).get(direction, 0)
            faulted = bool(faults >> channel.bit & 1) if fault_known else False
            valid = sampled and fault_known and not faulted
            is_forced = bool(forced >> channel.bit & 1) if outward and live else False
            values.update({
                f"{leaf}/Name": channel.name,
                f"{leaf}/DescriptionKey": channel.description_key,
                f"{leaf}/Address": f"{module.address}:{'O' if outward else 'I'}.{channel.bit}",
                f"{leaf}/Path": f"{module.name}.{channel.name}",
                f"{leaf}/ModulePath": f"{app.name}.{channel.module_path}" if channel.module_path else app.name,
                f"{leaf}/Dir": channel.direction,
                f"{leaf}/Kind": channel.kind,
                f"{leaf}/BoolValue": bool((word >> channel.bit) & 1) if sampled else False,
                f"{leaf}/AnalogValue": 0,
                f"{leaf}/Unit": channel.unit,
                f"{leaf}/Quality": valid,
                f"{leaf}/FaultActive": faulted,
                f"{leaf}/Diagnostic": "",
                f"{leaf}/Forced": is_forced,
                f"{leaf}/Forceable": outward and valid and force_permitted,
            })
    return values

def reference_values(app, samples, *, mapping_valid=True):
    if len(samples) != len(app.io_modules):
        raise ValueError('one sample per declared I/O module required')
    if not app.io_modules:
        return {}
    io = {}
    for module, s in zip(app.io_modules, samples):
        io[module.address] = dict(forced=s['ForcedWord'], forcePermitted=0)
        for key, word, valid in (('input', 'InputWord', 'InputValid'), ('output', 'OutputWord', 'OutputValid'), ('fault', 'FaultWord', 'FaultValid')):
            if s[valid] == 1:
                io[module.address][key] = s[word] & ((1 << module.data_width) - 1)
    old = topology(app, io)
    root = app.name + 'Fieldbus/Topology'
    result = {
        root + '/NodeCount': 0,
        root + '/MappingValid': mapping_valid,
        root + '/MappingDiagnostic': '' if mapping_valid else 'std.error.fieldbusChannelMappingInvalid',
    }
    for index, module in enumerate(app.io_modules, 1):
        source = f'{root}/Nodes[{index}]'
        groups = [('', module.channels)] if len(module.channels) <= 16 else [('', ()), ('.I', tuple(c for c in module.channels if c.direction == 0)), ('.O', tuple(c for c in module.channels if c.direction == 1))]
        parent = result[root + '/NodeCount'] + 1
        for suffix, channels in groups:
            if suffix and not channels:
                continue
            result[root + '/NodeCount'] += 1
            n = result[root + '/NodeCount']
            target = f'{root}/Nodes[{n}]'
            for field in ('Name', 'DescriptionKey', 'TypeId', 'Address', 'State', 'LinkOk', 'ParentIdx', 'ChannelCount'):
                v = old[source + '/' + field]
                if field == 'Name':
                    v = module.name + suffix
                elif field == 'Address':
                    v = module.address + (':' + suffix[1:] if suffix else '')
                elif field == 'ParentIdx':
                    v = parent if suffix else 0
                elif field == 'ChannelCount':
                    v = len(channels)
                result[target + '/' + field] = v
            for slot, channel in enumerate(channels, 1):
                original = module.channels.index(channel) + 1
                prefix = f'{source}/Channels[{original}]/'
                dest = f'{target}/Channels[{slot}]/'
                for path, value in old.items():
                    if path.startswith(prefix):
                        field = path[len(prefix):]
                        if field == 'AnalogValue':
                            value = float(value)
                        if field == 'Quality':
                            value = value and mapping_valid
                        result[dest + field] = value
    return result


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
        expected=reference_values(self.app,self.tags[bus.samples_tag(self.app)],mapping_valid=valid)
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
        self.assertEqual(reference_values(app,[]),{})
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
