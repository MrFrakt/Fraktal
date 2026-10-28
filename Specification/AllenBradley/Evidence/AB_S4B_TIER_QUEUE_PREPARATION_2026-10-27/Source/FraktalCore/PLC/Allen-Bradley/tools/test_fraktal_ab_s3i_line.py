"""Execute emitted S3i ST and compare it with independently read Line owners."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import random
import unittest
from unittest.mock import patch

import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_line as line
import fraktal_ab_canonical_metrics as metrics
import fraktal_ab_canonical_status as clock
import fraktal_ab_canonical_reader as decoder
import fraktal_ab_genealogy_s3i_demo as demo
import fraktal_ab_generate as gen
import fraktal_ab_line as owner
import fraktal_ab_manifest as manifest
import fraktal_ab_st_model as st
import fraktal_ab_s3i_reference as reference
import fraktal_ab_s3i_equivalence as contract
import fraktal_ab_s3i_native_checks as native
from test_fraktal_ab_s3g_metrics import NativeRealModel


class LineBehaviorTests(unittest.TestCase):
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
        self.root=value(pub.root_type(app),pub.initial(app));self.work=value(line.WORK,dict(EmptyShift=dict(SchemaVersion=3)))
        self.state=st.structure(owner.state_members(app));self.shift=st.structure(owner.shift_members())
        self.state.update(LineIdKey=manifest.numeric_key(app,app.line.line_id),OwnerIdKey=manifest.numeric_key(app,app.line.owner_id))
        self.shift['AppliedRevision']=1
        self.factor=value(metrics.WORK);self.factor.update(Wrap=1<<32,SignedEdge=1<<31)
        self.clock=value(clock.WORK)
        self.tags={app.name:self.root,line.state_tag(app):self.work,metrics.state_tag(app):self.factor,
            owner.tag(app,'State'):self.state,owner.tag(app,'Shift'):self.shift,
            clock.work_tag(app):self.clock,pub.header_tag(app):dict(Valid=True),'S:FS':False}
        routines=dict(line.routines(app));routines[metrics.factor_routine(app)]=metrics.factor_logic(app)
        routines[clock.timestamp_routine_name(app)]=clock.epoch_logic(app,stamped=False)
        self.plc=NativeRealModel(self.tags,calls={'CPS':st.cps_structure},routines=routines)
        self.body=st.parse('\n'.join(line.cyclic(app)))

    def scan(self):
        self.tags[pub.header_tag(self.app)]['Valid']=True
        with patch.object(st,'_wrap',lambda x:(x+(1<<63))%(1<<64)-(1<<63)):self.plc.run(self.body)

    def actual(self):
        result={}
        def walk(kind,data,path):
            for m in self.schema[kind]:
                pairs=enumerate(data[m.name],m.lower) if m.count else ((None,data[m.name]),)
                for i,v in pairs:
                    if m.count_path and i-m.lower>=self.root['ShiftHistoryCount']:continue
                    p=path+'/'+m.name+(f'[{i}]' if i is not None else '')
                    if m.kind in self.schema:walk(m.kind,v,p)
                    elif m.kind.startswith(pub.PREFIX+'String'):result[p]=bytes(x&255 for x in v['DATA'][:v['LEN']]).decode()
                    else:result[p]=decoder.timestamp_ns(v) if m.kind=='LDT' else v&0xffffffff if m.logical=='BITSTRING32' else v
        for m in self.schema[pub.root_type(self.app)]:
            if m.name not in ('Line','ShiftHistory',*line.ROOT_FIELDS):continue
            if m.name=='ShiftHistory':
                for i,v in enumerate(self.root[m.name][:self.root['ShiftHistoryCount']],1):walk(m.kind,v,f'ShiftHistory[{i}]')
            elif m.kind in self.schema:walk(m.kind,self.root[m.name],m.name)
            else:
                v=self.root[m.name];result[m.name]=decoder.timestamp_ns(v) if m.kind=='LDT' else v&0xffffffff if m.logical=='BITSTRING32' else v
        return result

    def assert_exact(self):
        self.assertTrue(self.tags[pub.header_tag(self.app)]['Valid'])
        expected=reference.values(self.app,self.state,self.shift)
        expected={p.replace('Line/OwnerId','Line/Owner').replace('Line/LastUpdatedAt','Line/LastUpdate'):v for p,v in expected.items()}
        actual=self.actual();self.assertEqual(actual,expected)
        self.assertEqual({p:type(v) for p,v in actual.items()},{p:type(v) for p,v in expected.items()})
        self.assertEqual({self.app.name+'/'+p for p in actual},contract.line_paths(self.app,canonical=True,count=self.shift['Count']))

    def populate(self,count):
        s=self.shift;s.update(Count=count,ClosedSequence=s['ClosedSequence']+1,Current=2,StartedMinute=29000000,StartedMs=55001,
            EndsMinute=29000480,TimeSynchronized=1,ProductionTarget=123,Truncated=int(count==owner.HISTORY))
        for i in range(count):
            for n,v in dict(Index=i%6,StartMinute=28999520-i*480,StartMs=123,EndMinute=29000000-i*480,EndMs=456,
                    TimeSynchronized=i%2,ManualReset=(i+1)%2,Good=10+i,Nok=i,Rework=2*i,
                    OeeGood=100+i,OeeNok=3+i,RunS=100+i,RunMs=1,DownS=20+i,DownMs=2,
                    IdleS=30+i,IdleMs=3,IdealMs=100,ProductionTarget=200+i).items():s['History'+n][i]=v

    def test_empty_then_partial_full_and_wrapped_history_path_set(self):
        self.scan();self.assert_exact();self.assertEqual(len(self.actual()),18)
        for count in (1,4,8,8,1,0):
            with self.subTest(count=count):
                self.populate(count);self.scan();self.assert_exact();self.assertEqual(len(self.actual()),18+21*count)
        self.assertEqual(self.root['ShiftHistory'][0]['SchemaVersion'],3)
        self.assertEqual(self.root['ShiftHistory'][0]['GoodCount'],0)

    def test_stored_line_update_quality_does_not_follow_current_probe(self):
        self.tags[gen.health_probe_tag(self.app)]=dict(TimeIsSynchronized=1)
        self.state.update(UpdatedDate=20240229,UpdatedClock=10203004,TimeSynchronized=0)
        self.scan();self.assert_exact();self.assertFalse(self.actual()['Line/TimeSynchronized'])
        self.tags[gen.health_probe_tag(self.app)]['TimeIsSynchronized']=0
        self.state.update(Revision=2,UpdatedClock=10203005,TimeSynchronized=1)
        self.scan();self.assert_exact();self.assertTrue(self.actual()['Line/TimeSynchronized'])

    def test_owner_commit_records_time_quality_in_versioned_state_only(self):
        app=self.app;probe=gen.health_probe_tag(app)
        self.tags.update({probe:dict(TimeIsSynchronized=1),f'FRK_{app.name}_NowDate':20261024,f'FRK_{app.name}_NowTime':112233444})
        self.plc.run(st.parse('\n'.join(owner.accepted(app))))
        self.assertEqual((self.state['TimeSynchronized'],self.state['SourceError'],self.state['UpdatedClock']),(1,0,112233444))
        self.assertEqual(owner.state_schema(replace(app,canonical_publication_stage=10)),1)
        self.assertNotIn('TimeSynchronized','\n'.join(owner.accepted(replace(app,canonical_publication_stage=10))))

    def test_line_and_shift_revisions_and_latched_target_are_distinct(self):
        self.populate(1);self.scan();self.assert_exact()
        self.state['Revision']=3;self.scan();self.assert_exact()
        self.assertTrue(self.actual()['ShiftCalendarPending'])
        self.assertEqual(self.actual()['ShiftHistory[1]/ProductionTarget'],200)
        self.assertEqual(self.actual()['ShiftProductionTarget'],123)
        self.shift.update(AppliedRevision=3,ProductionTarget=999);self.scan();self.assert_exact()
        self.assertFalse(self.actual()['ShiftCalendarPending']);self.assertEqual(self.actual()['ShiftHistory[1]/ProductionTarget'],200)

    def test_exact_float32_and_unsigned_wrap_from_saved_oee_counts(self):
        self.populate(1);r=random.Random(61024)
        vectors=[(1<<32,0,-2147483648,-1,1),(16777217,3,16777217,2,1),((1<<32)-1,1,1,0,1000),(0,0,0,0,0)]
        vectors += [(r.randrange(1<<32),r.randrange(1<<32),r.randrange(-(1<<31),1<<31),r.randrange(-(1<<31),1<<31),r.randrange(1<<20)) for _ in range(24)]
        for run,down,good,nok,ideal in vectors:
            with self.subTest(vector=(run,down,good,nok,ideal)):
                s=self.shift;s['ClosedSequence']+=1
                for n,v in dict(RunS=run//1000,RunMs=run%1000,DownS=down//1000,DownMs=down%1000,
                    OeeGood=good,OeeNok=nok,IdealMs=ideal,Good=-1,Nok=-2147483648,Rework=-1,ProductionTarget=-1).items():s['History'+n][0]=v
                self.scan();self.assert_exact()
        self.assertEqual(self.actual()['ShiftHistory[1]/GoodCount'],4294967295)

    def test_cached_history_republishes_on_first_scan_and_owner_marker(self):
        self.populate(1);self.scan();self.assert_exact();before=deepcopy(self.root['ShiftHistory'][0])
        # An out-of-owner mutation has no commit marker, proving the cache.
        self.shift['HistoryGood'][0]=888;self.scan();self.assertEqual(self.root['ShiftHistory'][0],before)
        self.tags['S:FS']=True;self.scan();self.assert_exact();self.tags['S:FS']=False
        self.shift['HistoryGood'][0]=999;self.shift['ClosedSequence']+=1;self.scan();self.assert_exact()

    def test_minute_stamp_exact_native_limit_and_zero(self):
        for minute,millis in ((0,0),(1,1),(29000000,59999),(153722867,16854)):
            with self.subTest(minute=minute,millis=millis):
                self.shift.update(StartedMinute=minute,StartedMs=millis);self.scan();self.assert_exact()
        self.assertEqual(self.root['ShiftStartedAt'],9223372036854000000)

    def test_out_of_range_stamps_fail_closed_without_overflow(self):
        for minute,millis in ((-1,0),(153722868,0),(153722867,16855),(1,-1),(1,60000)):
            with self.subTest(minute=minute,millis=millis):
                self.shift.update(StartedMinute=minute,StartedMs=millis);self.scan()
                self.assertFalse(self.tags[pub.header_tag(self.app)]['Valid']);self.assertEqual(self.root['ShiftStartedAt'],0)

    def test_invalid_counts_and_indices_never_index_outside_owner(self):
        for count in (-1,9,2147483647):
            self.shift['Count']=count;self.scan();self.assertFalse(self.tags[pub.header_tag(self.app)]['Valid'])
        self.populate(1)
        for index in (-1,6):
            self.shift['HistoryIndex'][0]=index;self.scan();self.assertFalse(self.tags[pub.header_tag(self.app)]['Valid'])

    def test_invalid_schema_identity_and_quality_are_rejected(self):
        saved=deepcopy(self.state)
        for n,v in (('SchemaVersion',1),('Revision',0),('LineIdKey',0),('OwnerIdKey',0),('TimeSynchronized',2),('SourceError',12)):
            with self.subTest(n=n):
                self.state.update(saved);self.state[n]=v;self.scan();self.assertFalse(self.tags[pub.header_tag(self.app)]['Valid'])

    def test_canonical_width_checks_never_truncate_declared_line_identity(self):
        self.assertFalse(line.validate(self.app))
        self.assertTrue(line.validate(replace(self.app,line=replace(self.app.line,line_id='X'*41))))
        self.assertFalse(line.validate(replace(self.app,line=replace(self.app.line,line_id='X'*40,owner_id='Y'*80))))

    def test_new_owner_layout_is_versioned_and_old_prefix_unchanged(self):
        old=replace(self.app,canonical_publication_stage=10)
        self.assertEqual([m.name for m in owner.state_members(self.app)][:6],[m.name for m in owner.state_members(old)])
        self.assertEqual(owner.records(old)[0].name,'FRK_T_LineStateV1')
        self.assertEqual(owner.records(self.app)[0].name,'FRK_T_LineStateV2')
        self.assertEqual(owner.state_members(old)[0].initial,1)
        self.assertEqual(owner.state_members(self.app)[0].initial,2)

    def test_optional_line_adds_no_orphan_surface(self):
        app=replace(self.app,line=None,canonical_observation_period_ms=0)
        self.assertFalse(line.validate(app));self.assertEqual(line.cyclic(app),[]);self.assertEqual(line.routines(app),[])
        self.assertNotIn('Line',{m.name for m in pub.schema(app)[pub.root_type(app)]})

    def test_occupied_history_fields_and_types_match_the_approved_inventory(self):
        path=Path(__file__).resolve().parents[4]/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_REMAINING_S3_INVENTORY_2026-10-24.json'
        reviewed=json.loads(path.read_text())['dynamicShiftHistory']['paths']
        target=json.loads(path.with_name('AB_FROZEN_CONTRACTS_V2.json').read_text())['logicalTypes']['uint16']
        schema_member=self.schema[line.SHIFT][0]
        self.assertEqual((schema_member.kind,schema_member.logical),(target['logix'],target['manifestLogicalType']))
        actual=contract.line_paths(self.app,canonical=True,count=8)
        self.assertEqual({p for p in actual if '/ShiftHistory[' in p},set(reviewed))
        types=contract.logical_types(self.app,set(reviewed))
        for p,row in reviewed.items():self.assertEqual(types[p],row['logicalType'])

    def test_native_apparatus_executes_production_body_and_restores_both_owners(self):
        native.definitions(self.app,self.schema)
        # The model has separate typed values rather than raw storage. Its only
        # extra CPS shapes here are identical arrays and all-DINT owner words.
        value=deepcopy(self.root)
        results=[]
        for _ in native.CASES:
            results.append(dict(Valid=False,**{n:deepcopy(value[n]) for n in ('Line','ShiftHistory',*line.ROOT_FIELDS)}))
        self.tags[native.tag(self.app)]=dict(Completed=False,Results=results,
            **{label:[0]*native.member_words(layout) for label,layout in (
                ('SavedState',owner.state_members(self.app)),('RestoredState',owner.state_members(self.app)),
                ('SavedShift',owner.shift_members()),('RestoredShift',owner.shift_members()))})
        for kind,layout in (('State',owner.state_members(self.app)),('Shift',owner.shift_members())):
            self.tags[native.saved_tag(self.app,kind)]=st.structure(layout)
        def cps(controller,args):
            source,dest=controller.read(args[0]),controller.read(args[1]);count=controller.eval(args[2])
            source_holder,source_key=controller._container(args[0]);dest_holder,dest_key=controller._container(args[1])
            if isinstance(source_holder,list) and isinstance(dest_holder,list) and isinstance(source,dict):
                self.assertEqual(count,8);dest_holder[dest_key:dest_key+count]=deepcopy(source_holder[source_key:source_key+count])
            elif isinstance(source,dict) and isinstance(dest,int):
                words=[item for v in source.values() for item in (v if isinstance(v,list) else [v])]
                self.assertEqual(count,len(words));holder,key=controller._container(args[1]);holder[key:key+count]=words
            elif isinstance(source,list):
                self.assertEqual(count,len(source));holder,key=controller._container(args[1]);holder[key]=deepcopy(source)
            else:st.cps_structure(controller,args)
        self.plc.calls['CPS']=cps
        original={kind:deepcopy(self.tags[owner.tag(self.app,kind)]) for kind in ('State','Shift')}
        with patch.object(st,'_wrap',lambda x:(x+(1<<63))%(1<<64)-(1<<63)):
            self.plc.run(st.parse('\n'.join(native.logic(self.app))))
        for kind in ('State','Shift'):self.assertEqual(self.tags[owner.tag(self.app,kind)],original[kind])
        def decoded(value):
            if isinstance(value,dict) and set(value)=={'LEN','DATA'}:
                return dict(string=True,bytes=bytes(x&255 for x in value['DATA'][:value['LEN']]).hex())
            if isinstance(value,dict):return {k:decoded(v) for k,v in value.items()}
            if isinstance(value,list):return [decoded(v) for v in value]
            return value
        result=decoded(self.tags[native.tag(self.app)])
        self.assertTrue(native.verify_result(self.app,result)['ownersRestoredExactly'])
        result['RestoredShift'][0]^=1
        with self.assertRaisesRegex(ValueError,'restoration'):native.verify_result(self.app,result)

    def test_observation_frame_adds_exactly_the_two_new_oracle_owners(self):
        import fraktal_ab_canonical_observation as frame
        old=replace(self.app,canonical_publication_stage=10)
        self.assertEqual(set(frame.legacy_sources(self.app))-set(frame.legacy_sources(old)),
            {owner.tag(self.app,'State'),owner.tag(self.app,'Shift')})
        self.assertEqual(len(frame.sources(self.app)),33)
        self.assertEqual(frame._declared(self.app)[owner.tag(self.app,'State')][0],'FRK_T_LineStateV2')


if __name__=='__main__':unittest.main()
