"""Execute the emitted S3h ST against independently projected owner records."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import struct
import unittest
from unittest.mock import patch

import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_traceability as trace
import fraktal_ab_canonical_status as clock
import fraktal_ab_genealogy_s3h_demo as demo
import fraktal_ab_host_events as host
import fraktal_ab_part as part
import fraktal_ab_signal_tower as tower
import fraktal_ab_st_model as st
import fraktal_ab_s3h_reference as reference
import fraktal_ab_s3h_equivalence as contract
import fraktal_ab_canonical_reader as reader


class DoubleModel(st.Controller):
    def eval(self,node):
        if node[0]=='bin':
            op=node[1];a=self.eval(node[2]);b=self.eval(node[3])
            if type(a) is float or type(b) is float:
                if op in ('+','-','*','/'):
                    return {'+':lambda:a+b,'-':lambda:a-b,'*':lambda:a*b,'/':lambda:a/b}[op]()
                return {'=':a==b,'<>':a!=b,'<':a<b,'>':a>b,'<=':a<=b,'>=':a>=b}[op]
        return super().eval(node)

    def write(self,ref,value):
        holder,key=self._container(ref)
        if type(holder[key]) is bool:holder[key]=bool(value)
        elif type(holder[key]) is float:holder[key]=float(value)
        else:super().write(ref,value)


class TraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.app=app=demo.application();self.schema=schema=pub.schema(app)
        def value(kind,initial=None):
            if kind.startswith(pub.PREFIX+'String'):
                raw=(initial or '').encode();return dict(LEN=len(raw),DATA=list(raw)+[0]*(pub.string_width(kind)-len(raw)))
            if kind=='BOOL':return bool(initial)
            if kind in ('REAL','LREAL'):return float(initial or 0)
            if kind not in schema:return initial or 0
            initial=initial or {}
            return {m.name:([value(m.kind,x) for x in initial.get(m.name,[None]*m.count)] if m.count else value(m.kind,initial.get(m.name))) for m in schema[kind]}
        self.value=value;self.root=value(pub.root_type(app),pub.initial(app));self.work=value(trace.WORK)
        self.raw_part=st.structure(part.members(app));self.raw_host=st.structure(host.members(app));self.raw_host['EpochLow']=1
        self.raw_tower=st.structure(tower.members());self.codes=[m.code for m in app.models]
        self.root['AvailableModelCount']=len(self.codes)
        for i,code in enumerate(self.codes):self.root['AvailableModels'][i]['ModelCode']=value(pub.string_type(80),code)
        labels=dict(Entries=[dict(Name=r.name,Unit=r.unit,Scale=float(r.scale),Minimum=r.minimum/r.scale,
            Maximum=r.maximum/r.scale,Target=r.target/r.scale) for r in app.part_carrier.records])
        tags={app.name:self.root,trace.state_tag(app):self.work,trace.definitions_tag(app):value(trace.DEFINITIONS,labels),
            clock.work_tag(app):value(clock.WORK),pub.header_tag(app):dict(Valid=True),'S:FS':False,
            part.tag(app):self.raw_part,host.tag(app):self.raw_host,tower.tag(app):self.raw_tower}
        routines=dict(trace.routines(app));routines[clock.timestamp_routine_name(app)]=clock.epoch_logic(app,stamped=False)
        self.plc=DoubleModel(tags,calls={'CPS':st.cps_structure},routines=routines)
        self.body=st.parse('\n'.join(trace.cyclic(app)))

    def scan(self):
        self.plc.tags[pub.header_tag(self.app)]['Valid']=True
        with patch.object(st,'_wrap',lambda x:(x+(1<<63))%(1<<64)-(1<<63)):self.plc.run(self.body)

    def actual(self):
        result={}
        def walk(kind,data,prefix):
            for m in self.schema[kind]:
                values=enumerate(data[m.name],m.lower) if m.count else ((None,data[m.name]),)
                for index,v in values:
                    if m.count_path and index>=m.lower+self.root['HostEvents']['Count']:continue
                    p=prefix+'/'+m.name+(f'[{index}]' if index is not None else '')
                    if m.kind in self.schema:walk(m.kind,v,p)
                    elif m.kind.startswith(pub.PREFIX+'String'):result[p]=bytes(x&255 for x in v['DATA'][:v['LEN']]).decode()
                    else:result[p]=reader.timestamp_ns(v) if m.kind=='LDT' else v&0xffffffff if m.logical=='BITSTRING32' else v
        for m in self.schema[pub.root_type(self.app)]:
            if m.name not in ('Part','HostEvents','Nameplate','SignalTower','MachineState'):continue
            if m.kind in self.schema:walk(m.kind,self.root[m.name],m.name)
            else:result[m.name]=self.root[m.name]
        return result

    def assert_exact(self):
        self.assertIs(self.plc.tags[pub.header_tag(self.app)]['Valid'],True)
        expected=reference.values(self.app,self.raw_part,host.decode(self.app,self.raw_host,self.codes),self.raw_tower)
        actual=self.actual();self.assertEqual(actual,expected)
        self.assertEqual({p:type(v) for p,v in actual.items()},{p:type(v) for p,v in expected.items()})
        self.assertEqual({self.app.name+'/'+p for p in actual},contract.trace_paths(self.app,count=self.raw_host['Count']))

    def uid(self,target,text,offset=0):
        target[offset:offset+64]=list(text.encode().ljust(64,b'\0'))

    def ring(self,newest):
        h=self.raw_host;cap=self.app.host_event_capacity
        h.update(NewestSequence=newest,Count=min(newest,cap),Head=(newest-1)%cap+1 if newest else 0,
            Wrapped=int(newest>cap),DataRevision=newest*2)
        for n in range(max(1,newest-cap+1),newest+1):
            i=(n-1)%cap;h['Sequence'][i]=n;h['Kind'][i]=9;h['Value'][i]=1
            h['Date'][i]=20261023;h['Time'][i]=120034567;h['TimeSynchronized'][i]=1

    def test_empty_and_partial_full_wrapped_ring_exact_logical_path_set(self):
        for newest in (0,1,7,16,17,44):
            with self.subTest(newest=newest):self.ring(newest);self.scan();self.assert_exact()
        self.assertEqual(len(self.actual()),278)

    def test_exact_lreal_scaling_populated_stamp_and_stale_result_parent_clear(self):
        p=self.raw_part;p.update(Present=1,DataRevision=2,RecordCount=2,Date=20240229,Time=10203004,ParentCount=2)
        self.uid(p['Uid'],'CHILD');self.uid(p['Parents'],'PARENT-A');self.uid(p['Parents'],'PARENT-B',64)
        p['RecordKind'][:2]=[1,2];p['RecordValue'][:2]=[1001,100];p['RecordInTol'][:2]=[1,1]
        self.scan();self.assert_exact();self.assertEqual(self.actual()['Part/Result/Records[1]/Value'],1.001)
        r=self.app.part_carrier.records[0]
        self.assertNotEqual(1.001,struct.unpack('<f',struct.pack('<f',1.001))[0])
        p.update(DataRevision=4,RecordCount=0,Date=0,Time=0,ParentCount=0)
        p['Parents'][:]=[0]*len(p['Parents']);self.scan();self.assert_exact()
        self.assertEqual(self.actual()['Part/Result/Stamp'],0)
        self.assertEqual(self.actual()['Part/Parents[1]'],'')
        self.assertEqual(self.actual()['Part/Result/Records[1]/Value'],0.0)

    def test_native_division_uses_double_before_division_including_one_third(self):
        p=self.raw_part;p.update(DataRevision=2,RecordCount=1)
        p['RecordKind'][0]=1;p['RecordValue'][0]=1;p['RecordInTol'][0]=0
        self.plc.tags[trace.definitions_tag(self.app)]['Entries'][0].update(Scale=3.0,Minimum=50/3,Maximum=10000/3,Target=100.0)
        self.scan();self.assertIs(self.plc.tags[pub.header_tag(self.app)]['Valid'],True)
        self.assertEqual(self.actual()['Part/Result/Records[1]/Value'],1/3)

    def test_captured_resource_text_numeric_limits_models_and_historical_parents(self):
        self.ring(16);h=self.raw_host
        for i,number in enumerate((-2147483648,-1,0,2147483647)):
            h['Kind'][i]=7;h['Value'][i]=number;self.uid(h['Uid'],'RESOURCE',i*64)
        h['Kind'][4]=8;h['Value'][4]=0;h['ValueFormat'][4]=1;self.uid(h['Uid'],'MATERIAL',4*64)
        raw=b'A captured $value ]]>'.ljust(84,b'\0');h['ValueText'][4*21:5*21]=list(struct.unpack('<21i',raw))
        h['Kind'][5]=6;h['ModelOrdinal'][5]=2
        h['Kind'][6]=5;h['ModelOrdinal'][6]=0
        h['Kind'][7]=3;h['Value'][7]=0;h['Verdict'][7]=1;self.uid(h['Uid'],'OLD-CHILD',7*64)
        h['ParentCount'][7]=2
        raw=b'HISTORICAL-A'.ljust(64,b'\0')+b'HISTORICAL-B'.ljust(64,b'\0')
        h['ParentWords'][7*32:8*32]=list(struct.unpack('<32i',raw))
        self.scan();self.assert_exact()
        self.assertEqual(self.actual()['HostEvents/Ring[1]/Value'],'-2147483648')
        self.assertEqual(self.actual()['HostEvents/Ring[8]/Parents[1]'],'HISTORICAL-A')
        self.raw_part['DataRevision']=2;self.scan();self.assert_exact()
        self.assertEqual(self.actual()['HostEvents/Ring[8]/Parents[1]'],'HISTORICAL-A')

    def test_cache_rebuild_after_epoch_reset_clears_inactive_slots(self):
        self.ring(20);self.scan();self.assert_exact()
        self.ring(0);self.raw_host['EpochLow']=2;self.scan();self.assert_exact()
        self.assertTrue(all(row['Sequence']==0 and row['PartUid']['LEN']==0 for row in self.root['HostEvents']['Ring']))
        self.ring(1);self.scan();self.assert_exact()

    def test_bad_bounds_and_timestamp_fail_closed_before_indexing(self):
        self.ring(1)
        for name,value in (('Count',17),('Head',-1),('DataRevision',3),('Failed',1)):
            with self.subTest(name=name):
                saved=self.raw_host[name];self.raw_host[name]=value;self.scan()
                self.assertIs(self.plc.tags[pub.header_tag(self.app)]['Valid'],False);self.raw_host[name]=saved
        self.raw_host['Date'][0]=20260230;self.scan()
        self.assertIs(self.plc.tags[pub.header_tag(self.app)]['Valid'],False)

    def test_single_tower_owner_mirrored_for_all_semantic_outputs(self):
        for state in range(7):
            self.raw_tower.update(MachineState=state,**{n:(state+i)%2 for i,n in enumerate(tower.OUTPUTS)})
            self.scan();self.assert_exact()

    def test_all_278_paths_and_only_36_approved_type_corrections(self):
        inventory=json.loads((Path(__file__).resolve().parents[4]/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S3H_INVENTORY_2026-10-23.json').read_text())
        self.ring(16);self.scan();self.assert_exact()
        paths={self.app.name+'/'+p for p in self.actual()};self.assertEqual(paths,set(inventory['paths']))
        fields={}
        native={'BOOL':'Boolean','DINT':'Int32','INT':'Int16','LREAL':'Double','LDT':'DateTime'}
        def walk(kind,prefix):
            for m in self.schema[kind]:
                for n in ([f'{m.name}[{i}]' for i in range(m.lower,m.lower+m.count)] if m.count else [m.name]):
                    path=prefix+'/'+n
                    if m.kind in self.schema:walk(m.kind,path)
                    else:fields[path]='UInt32' if m.logical=='BITSTRING32' else 'String' if m.kind.startswith(pub.PREFIX+'String') else native.get(m.kind,m.kind)
        for m in self.schema[pub.root_type(self.app)]:
            if m.name in ('Part','HostEvents','Nameplate','SignalTower'):walk(m.kind,self.app.name+'/'+m.name)
            elif m.name=='MachineState':fields[self.app.name+'/MachineState']='Int32'
        self.assertEqual(fields,{p:r['proposedCoreType'] for p,r in inventory['paths'].items()})
        self.assertEqual(sum(fields[p]!=r['legacyType'] for p,r in inventory['paths'].items()),36)

    def test_core_text_and_capacity_limits_refuse_generation_without_clipping(self):
        app=self.app
        self.assertEqual(pub.validate(app),[])
        bad=replace(app,nameplate=replace(app.nameplate,serial='A'*41))
        self.assertTrue(any('Core width' in v for v in trace.validate(bad)))
        bad=replace(app,host_event_capacity=33)
        self.assertTrue(any('MAX_HOST_EVENTS' in v for v in trace.validate(bad)))

    def test_generated_identifiers_fit_native_limit_and_module_plates_keep_contract(self):
        import xml.etree.ElementTree as ET
        app=self.app;module=app.modules[0]
        app=replace(app,modules=(replace(module,nameplate=app.nameplate),*app.modules[1:]))
        schema=pub.schema(app)
        root={m.name:m.kind for m in schema[pub.root_type(app)]}
        old=pub.schema(self.app);original={m.name:m.kind for m in old[pub.root_type(self.app)]}
        self.assertEqual(schema[root[module.name]][:-1],old[original[module.name]])
        self.assertEqual(schema[root[module.name]][-1].name,'Nameplate')
        self.assertEqual(root[app.modules[1].name],original[app.modules[1].name])
        self.assertEqual(pub.initial(app)[module.name]['Nameplate']['SerialNumber'],app.nameplate.serial)
        for fragment in (*pub.data_types(app),*pub.tags(app)):
            self.assertLessEqual(len(ET.fromstring(fragment).get('Name')),40)

    def test_ascii_nonzero_tails_and_unknown_measurement_kind_fail_closed(self):
        self.raw_part.update(DataRevision=2,RecordCount=1)
        self.raw_part['RecordKind'][0]=999
        self.scan();self.assertIs(self.plc.tags[pub.header_tag(self.app)]['Valid'],False)

        self.raw_part.update(DataRevision=4,RecordCount=0)
        self.raw_part['Uid'][:4]=[65,0,66,0]
        self.scan();self.assertIs(self.plc.tags[pub.header_tag(self.app)]['Valid'],False)

    def test_stage_path_callback_accepts_boolean_selector_and_independent_ring_count(self):
        codes=[m.code for m in self.app.models]
        for count in (0,3,16):
            for canonical in (False,True):
                paths=contract.subset_paths(self.app,codes,canonical=canonical,count=count)
                previous=contract.previous.subset_paths(self.app,codes,canonical=canonical)
                self.assertEqual(paths-previous,contract.trace_paths(self.app,count=count))

    def test_live_runner_uses_held_owner_count_after_warmup(self):
        calls=[]
        def runner(comm,**kwargs):
            kwargs['additional_inputs'](object())
            kwargs['additional_inputs'](object())
            for canonical in (True,False):
                actual=kwargs['path_contract'](self.app,self.codes,canonical=canonical)
                wanted=contract.subset_paths(self.app,self.codes,canonical=canonical,count=3)
                self.assertEqual(actual,wanted);calls.append(canonical)
            return 'checked'
        with patch.object(contract,'additional_inputs',side_effect=[{'host':{'metadata':{'Count':0}}},{'host':{'metadata':{'Count':3}}}]),patch.object(contract.shared,'run',side_effect=runner):
            self.assertEqual(contract.run(object()),'checked')
        self.assertEqual(calls,[True,False])


if __name__=='__main__':unittest.main()
