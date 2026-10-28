"""Execute emitted S3g ST; compare exact values with independent Core math."""
from copy import deepcopy
from pathlib import Path
import json
import random
import struct
import unittest
from unittest.mock import patch

import fraktal_ab_canonical_metrics as metrics
import fraktal_ab_canonical_publication as pub
import fraktal_ab_genealogy_s3g_demo as demo
import fraktal_ab_generate as gen
import fraktal_ab_st_model as st
import fraktal_ab_s3g_reference as reference
import fraktal_ab_s3g_equivalence as contract
import fraktal_ab_projection as legacy


def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]


class NativeRealModel(st.Controller):
    """Add native REAL cells to the integer interpreter, without skipping ST.

    LINT expressions use its established 64-bit test mode; typed REAL writes
    round binary32. Integer-only expressions retain the existing interpreter.
    Native compiler/read-back gates separately verify accepted operand types.
    """
    def eval(self,node):
        if node[0]=='bin':
            op=node[1];a=self.eval(node[2]);b=self.eval(node[3])
            if type(a) is float or type(b) is float:
                if op in ('+','-','*','/'):
                    a,b=f32(a),f32(b)
                    if op=='/':return f32(a/b)
                    return f32({'+':lambda:a+b,'-':lambda:a-b,'*':lambda:a*b}[op]())
                return {'=':a==b,'<>':a!=b,'<':a<b,'>':a>b,'<=':a<=b,'>=':a>=b}[op]
        return super().eval(node)

    def write(self,ref,value):
        holder,key=self._container(ref)
        if type(holder[key]) is bool:holder[key]=bool(value)
        elif type(holder[key]) is float:holder[key]=f32(value)
        else:super().write(ref,value)


class MetricsBehaviorTests(unittest.TestCase):
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
        self.value=value
        self.owner=owner=st.structure(gen.oee_members())
        self.prof=prof=st.structure(gen.profiler_members(app))
        self.unit=unit=dict(GoodCount=1,ScrapCount=2)
        owner.update(RunS=1,DownS=2,Epoch=1)
        self.records={r.name:st.structure(r.members) for r in app.records}
        self.records[app.records[0].name][app.ideal_cycle_member]=100
        labels=dict(Entries=[dict(StepNo=s.number,Label='project.step.'+s.name,TimeClass=legacy.decl.TIME_CLASSES.index(s.time_class)) for s in metrics.first_steps(app)])
        self.root=value(pub.root_type(app),pub.initial(app));self.work=value(metrics.WORK)
        tags={app.name:self.root,metrics.state_tag(app):self.work,metrics.labels_tag(app):value(metrics.LABELS,labels),
            gen.oee_tag(app):owner,gen.profiler_tag(app):prof,f'FRK_{app.name}_Unit':unit,
            pub.header_tag(app):dict(Valid=1),'S:FS':False,
            gen.system_health_tag(app):st.structure(gen.system_health_members()),gen.health_probe_tag(app):st.structure(gen.health_probe_members())}
        tags.update({r.name+'Tag':self.records[r.name] for r in app.records})
        self.controller=NativeRealModel(tags,calls={'CPS':st.cps_structure},routines=dict(metrics.routines(app)))
        self.body=st.parse('\n'.join(metrics.cyclic(app)))

    def scan(self):
        with patch.object(st,'_wrap',lambda x:(x+(1<<63))%(1<<64)-(1<<63)):
            self.controller.run(self.body)

    def actual(self):
        result={}
        def walk(kind,data,prefix):
            for member in self.schema[kind]:
                values=enumerate(data[member.name],member.lower) if member.count else ((None,data[member.name]),)
                for index,value in values:
                    path=prefix+'/'+member.name+(f'[{index}]' if index is not None else '')
                    if member.kind in self.schema:walk(member.kind,value,path)
                    elif member.kind.startswith(pub.PREFIX+'String'):result[path]=bytes(x&255 for x in value['DATA'][:value['LEN']]).decode()
                    else:result[path]=value&0xffffffff if member.logical=='BITSTRING32' else value
        for member in self.schema[pub.root_type(self.app)]:
            if member.name not in ('Oee','OeeTrend','OeeTrendHead','Profiler','SystemHealth'):continue
            if member.count:
                for i,v in enumerate(self.root[member.name],member.lower):walk(member.kind,v,f'{member.name}[{i}]')
            elif member.kind in self.schema:walk(member.kind,self.root[member.name],member.name)
            else:result[member.name]=self.root[member.name]
        return result

    def expected(self):
        tags=self.controller.tags;app=self.app
        return {**reference.oee_values(app,self.owner,self.unit,self.records),**reference.profiler_values(app,self.prof),
            **reference.health_values(app,tags[gen.system_health_tag(app)],tags[gen.health_probe_tag(app)])}

    def assert_exact(self):
        actual,expected=self.actual(),self.expected()
        self.assertEqual(actual,expected)
        self.assertEqual({p:type(v) for p,v in actual.items()},{p:type(v) for p,v in expected.items()})
        self.assertEqual(len(actual),1055)

    def test_all_1055_paths_at_initial_and_populated_owners(self):
        self.scan();self.assert_exact()
        p=self.prof;p.update(LastCycleNo=8,LastN=3,LastTotal=120,LastWork=70,CurBuf=0,HistoryHead=2,LastCycleTime=120,MinCycleTime=100)
        steps=metrics.first_steps(self.app)
        for i in range(3):
            p['WfStepNo'][32+i]=steps[i].number;p['WfDurMs'][32+i]=10+i;p['WfExpMs'][32+i]=100+i
            p['StatCount'][i]=i+1;p['StatAvg'][i]=13+i;p['StatMax'][i]=20+i
        p['HisCycleNo'][1]=8;p['HisTotal'][1]=120;p['HisWork'][1]=70;p['HisByClass'][5:10]=[70,10,15,20,5]
        self.scan();self.assert_exact()

    def test_exact_float32_operations_and_u32_boundary_factors(self):
        vectors=[(1,2,1,2,1),(0,0,0,0,0),(4294967296,0,0,0,1000),
            (2147483648,2147483648,4294967295,1,1000),
            (100,10,1,1,1000),(1,1,0,0,0),(4294967295,1,1,0,1),
            (16777217,3,16777217,2,1)]
        randomizer=random.Random(61023)
        vectors += [tuple(randomizer.randrange(1<<32) for _ in range(4))+(randomizer.randrange(1<<30),) for _ in range(40)]
        for run,down,good,nok,ideal in vectors:
            with self.subTest(vector=(run,down,good,nok,ideal)):
                self.owner.update(RunS=run//1000,RunMs=run%1000,DownS=down//1000,DownMs=down%1000,GoodBase=0,NokBase=0)
                self.unit.update(GoodCount=good if good<1<<31 else good-(1<<32),ScrapCount=nok if nok<1<<31 else nok-(1<<32))
                self.records[self.app.records[0].name][self.app.ideal_cycle_member]=ideal
                self.scan();self.assert_exact()

    def test_epoch_invalidates_all_trend_slots_and_ring_wrap(self):
        for i in range(60):
            self.owner['SmpEpoch'][i]=1;self.owner['SmpRunMs'][i]=1;self.owner['SmpDownMs'][i]=2
        self.scan();self.assert_exact()
        for head in (1,60,1):
            self.owner['Head']=head;self.owner['SmpRunMs'][head-1]+=1
            self.scan();self.assert_exact()
        self.owner['Epoch']=2;self.owner['Head']=0;self.scan();self.assert_exact()
        self.assertFalse(any(self.root['OeeTrend'][i]['OeeValid'] for i in range(60)))

    def test_high_bit_counts_keep_all_dependent_row_values_visible(self):
        for i,count in enumerate((1,-2147483648,-1,0)):
            self.prof['StatCount'][i]=count;self.prof['StatAvg'][i]=55;self.prof['StatMax'][i]=77
        self.prof.update(LastCycleNo=-1,LastN=0,HistoryHead=60)
        self.prof['HisCycleNo'][59]=-2147483648
        self.scan();self.assert_exact()
        self.assertEqual(self.root['Profiler']['StepStats'][1]['Label']['LEN']>0,True)

    def test_no_rebuilding_unchanged_rows_and_first_scan_republishes_retained_state(self):
        self.prof['StatCount'][0]=1;self.prof['StatAvg'][0]=20;self.scan()
        original=deepcopy(self.root['Profiler']['StepStats'][0])
        # Deliberate out-of-owner mutation proves the cache, not accepted input.
        self.prof['StatAvg'][0]=99;self.scan()
        self.assertEqual(self.root['Profiler']['StepStats'][0],original)
        self.controller.tags['S:FS']=True;self.scan();self.assert_exact()

    def test_reference_types_and_path_contract_are_bound_to_review_inventory(self):
        inventory=json.loads((Path(__file__).resolve().parents[4]/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S3G_INVENTORY_2026-10-23.json').read_text())
        paths=contract.metric_paths(self.app)
        self.assertEqual(paths,set(inventory['paths']))
        self.scan();values={self.app.name+'/'+p:v for p,v in self.actual().items()}
        types={p:'Boolean' if type(v) is bool else 'String' if type(v) is str else 'Int32' for p,v in values.items()}
        types.update(contract.logical_types(self.app,paths))
        self.assertEqual(types,{p:v['proposedCoreType'] for p,v in inventory['paths'].items()})

    def test_corrupt_waterfall_bounds_invalidate_manifest_without_faulting(self):
        self.prof.update(LastCycleNo=1,LastN=33,CurBuf=9)
        self.scan()
        self.assertEqual(self.controller.tags[pub.header_tag(self.app)]['Valid'],0)
        self.assertEqual(self.root['Profiler']['LastCycle']['NSteps'],0)

    def test_native_first_scan_apparatus_executes_production_st_and_restores_six_cells(self):
        import fraktal_ab_s3g_native_checks as checks
        checks.definitions(self.app,self.schema)
        self.controller.tags[checks.tag(self.app)]=self.value(checks.BENCH,checks.initial())
        saved=deepcopy(self.prof)
        with patch.object(st,'_wrap',lambda x:(x+(1<<63))%(1<<64)-(1<<63)):
            self.controller.run('\n'.join(checks.logic(self.app)))
        self.assertEqual(self.prof,saved)
        result=self.controller.tags[checks.tag(self.app)]
        self.assertEqual(checks.verify_result(self.app,result),dict(passed=True,oeeVectors=9,profilerHighBitVectors=2,readOnly=True))
        self.scan();self.assert_exact()
        result['OeeResults'][0]['Availability']=0.5
        with self.assertRaisesRegex(ValueError,'native OEE vector 0 differs'):checks.verify_result(self.app,result)

    def test_only_finite_approved_numeric_and_dependent_value_paths_may_differ(self):
        inventory=json.loads((Path(__file__).resolve().parents[4]/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S3G_INVENTORY_2026-10-23.json').read_text())
        typed={p for p,v in inventory['paths'].items() if v['legacyType']!=v['proposedCoreType']}
        dependent={self.app.name+'/Oee/'+n for n in ('AvailValid','PerfValid','QualValid','OeeValid')}
        dependent.update(self.app.name+f'/OeeTrend[{i}]/OeeValid' for i in range(1,61))
        dependent.update(self.app.name+f'/Profiler/StepStats[{i}]/'+n for i in range(1,33) for n in ('Id','Label','TimeClass','Avg','Maximum'))
        self.assertEqual((len(typed),len(dependent),len(typed|dependent)),(200,224,424))
        self.owner.update(RunS=4294967,RunMs=296,Epoch=0)
        self.unit.update(GoodCount=-1,ScrapCount=1)
        for i in range(min(32,len(gen.ordered_steps(self.app)))):
            self.prof['StatCount'][i]=-2147483648;self.prof['StatAvg'][i]=123;self.prof['StatMax'][i]=456
        self.scan()
        old={**legacy.oee_status(self.app,self.owner,self.unit,self.records),**legacy.profiler_status(self.app,self.prof),
            **legacy.system_health_status(self.app,self.controller.tags[gen.system_health_tag(self.app)],self.controller.tags[gen.health_probe_tag(self.app)])}
        for path,value in self.actual().items():
            if self.app.name+'/'+path not in typed|dependent:
                self.assertEqual(value,old[path],path);self.assertIs(type(value),type(old[path]),path)


if __name__=='__main__':unittest.main()
