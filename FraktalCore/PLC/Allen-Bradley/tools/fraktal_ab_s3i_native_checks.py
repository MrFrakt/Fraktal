"""Generate separately authorized, first-scan Line/shift acceptance vectors.

The generator emits all L5X. The apparatus saves/restores the two fixed Line
owner records in the same scan, exercises the production publication body,
then lets normal publication rebuild the live tree. No clock, input, command,
or arbitrary tag write is offered. Native result tags are read-only.
"""
import argparse
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

import fraktal_ab_canonical_line as line
import fraktal_ab_canonical_metrics as metrics
import fraktal_ab_canonical_publication as pub
import fraktal_ab_genealogy_s3i_demo as demo
import fraktal_ab_generate as gen
import fraktal_ab_line as owner
import fraktal_ab_manifest as manifest
import fraktal_ab_s3i_reference as reference

BENCH=pub.PREFIX+'NativeLineBenchS3iV63'
RESULT=pub.PREFIX+'NativeLineResultS3iV63'
CASES=('empty','full_unscheduled_manual_wrap','unchanged_marker_cache','pending_calendar_latched_target',
    'partial_history','empty_after_history','ldt_upper_limit','ldt_overflow_refused')


def tag(app):return f'FRK_{app.name}_S3iNativeChecks'
def routine(app):return f'FRK_{app.name}_S3iNativeChecks'
def saved_tag(app,kind):return f'FRK_{app.name}_S3iSavedLine{kind}'


def member_words(members):return sum(m.dimension or 1 for m in members)


def vectors(app):
    """Fixed legacy owners: independent of the canonical schema or decoder."""
    state={m.name:m.initial for m in owner.state_members(app)}
    state.update(LineIdKey=manifest.numeric_key(app,app.line.line_id),OwnerIdKey=manifest.numeric_key(app,app.line.owner_id))
    shifts={m.name:([m.initial]*m.dimension if m.dimension else m.initial) for m in owner.shift_members()}
    shifts['AppliedRevision']=1;out=[(deepcopy(state),deepcopy(shifts),True)]
    state.update(Revision=2,UpdatedDate=20240229,UpdatedClock=10203004,TimeSynchronized=1)
    shifts.update(Count=8,ClosedSequence=1,Current=0,StartedMinute=29000000,StartedMs=55001,
        EndsMinute=29000480,TimeSynchronized=1,ProductionTarget=123,Truncated=1,AppliedRevision=2)
    for i in range(8):
        for n,v in dict(Index=i%6,StartMinute=28999520-i*480,StartMs=123,EndMinute=29000000-i*480,EndMs=456,
            TimeSynchronized=i%2,ManualReset=(i+1)%2,Good=-1 if i==0 else i+10,Nok=-2147483648 if i==1 else i,
            Rework=-1,ProductionTarget=200+i,RunS=4294967 if i==0 else 100+i,RunMs=296 if i==0 else 1,
            DownS=20+i,DownMs=2,IdleS=30+i,IdleMs=3,OeeGood=16777217 if i==1 else 100+i,
            OeeNok=3+i,IdealMs=100).items():shifts['History'+n][i]=v
    out.append((deepcopy(state),deepcopy(shifts),True))
    # Case 2 deliberately repeats the committed frame: the native routine
    # changes one uncommitted owner cell and proves that it is not published.
    out.append((deepcopy(state),deepcopy(shifts),True))
    state['Revision']=3;shifts['ProductionTarget']=999
    out.append((deepcopy(state),deepcopy(shifts),True))
    shifts.update(Count=3,ClosedSequence=2);out.append((deepcopy(state),deepcopy(shifts),True))
    shifts.update(Count=0,ClosedSequence=3);out.append((deepcopy(state),deepcopy(shifts),True))
    shifts.update(StartedMinute=153722867,StartedMs=16854);out.append((deepcopy(state),deepcopy(shifts),True))
    shifts['StartedMs']=16855;out.append((deepcopy(state),deepcopy(shifts),False))
    return out


def definitions(app,held):
    M=pub.Member;names={'Line','ShiftHistory',*line.ROOT_FIELDS}
    held[RESULT]=(M('Valid','BOOL'),*(m for m in held[pub.root_type(app)] if m.name in names))
    held[BENCH]=(M('Completed','BOOL'),M('Results',RESULT,count=len(CASES)),
        *(M(label,'DINT',count=member_words(layout)) for label,layout in (
            ('SavedState',owner.state_members(app)),('RestoredState',owner.state_members(app)),
            ('SavedShift',owner.shift_members()),('RestoredShift',owner.shift_members()))))


def logic(app):
    b=tag(app);s=owner.tag(app,'State');h=owner.tag(app,'Shift');w=line.state_tag(app);bad=pub.header_tag(app)+'.Valid'
    lines=[f'{b}.Completed := 0;',f'CPS({s},{saved_tag(app,"State")},1);',f'CPS({h},{saved_tag(app,"Shift")},1);']
    for label,layout,source in (('SavedState',owner.state_members(app),s),('SavedShift',owner.shift_members(),h)):
        lines.append(f'CPS({source},{b}.{label}[0],{member_words(layout)});')
    lines += [f'{w}.Initialized := 0;']
    previous={}
    for index,(state,shifts,valid) in enumerate(vectors(app)):
        if index!=2:
            for prefix,values in ((s,state),(h,shifts)):
                for name,value in values.items():
                    for suffix,v in (([(f'[{i}]',v) for i,v in enumerate(value)]) if isinstance(value,list) else [('',value)]):
                        cell=f'{prefix}.{name}{suffix}'
                        if previous.get(cell)!=v:lines.append(f'{cell} := {v};')
                        previous[cell]=v
        else:lines.append(f'{h}.HistoryGood[0] := 888;')
        lines += [f'{bad} := 1;',f'JSR({line.publish_routine(app)},0);',f'{b}.Results[{index}].Valid := {bad};']
        for name in ('Line','ShiftHistory',*line.ROOT_FIELDS):
            source=app.name+'.'+name;target=f'{b}.Results[{index}].{name}'
            lines += ([f'CPS({source}[0],{target}[0],{owner.HISTORY});'] if name=='ShiftHistory' else
                      [f'CPS({source},{target},1);'] if name=='Line' else [f'{target} := {source};'])
        if index==2:lines.append(f'{h}.HistoryGood[0] := -1;')
    lines += [f'CPS({saved_tag(app,"State")},{s},1);',f'CPS({saved_tag(app,"Shift")},{h},1);']
    for label,layout,source in (('RestoredState',owner.state_members(app),s),('RestoredShift',owner.shift_members(),h)):
        lines.append(f'CPS({source},{b}.{label}[0],{member_words(layout)});')
    return lines+[f'{bad} := 1;',f'{w}.Initialized := 0;',f'{b}.Completed := 1;']


def generate(seed,output):
    app=demo.application();augment,tags,cyclic,routines=line.augment,line.tags,line.cyclic,line.routines
    def with_definitions(app,held):augment(app,held);definitions(app,held)
    def with_tags(app,serialize):
        return tags(app,serialize)+[serialize(tag(app),BENCH,{})]+[
            gen._structure_tag(saved_tag(app,kind),dtype,members,external_access='None') for kind,dtype,members in (
                ('State',owner.state_type(app),owner.state_members(app)),('Shift','FRK_T_ShiftStateV3',owner.shift_members()))]
    def with_cyclic(app):return [f'IF S:FS THEN JSR({routine(app)},0); END_IF;']+cyclic(app)
    def with_routines(app):
        return routines(app)+[(routine(app),logic(app))]
    with ExitStack() as stack:
        for name,value in (('augment',with_definitions),('tags',with_tags),('cyclic',with_cyclic),('routines',with_routines)):
            stack.enter_context(patch.object(line,name,value))
        return gen.generate(app,seed,output)


def verify_result(app,result):
    if result['Completed'] is not True:raise ValueError('S3i first-scan checks incomplete')
    for kind in ('State','Shift'):
        if result['Saved'+kind]!=result['Restored'+kind]:raise ValueError('S3i owner restoration differs')
    if len(result['Results'])!=len(CASES):raise ValueError('S3i result count differs')
    for i,(state,shifts,valid) in enumerate(vectors(app)):
        record=result['Results'][i]
        if record['Valid'] is not valid:raise ValueError(f'S3i native validity differs at {CASES[i]}')
        if not valid:
            if record['ShiftStartedAt']!=0:raise ValueError('S3i overflow did not return zero')
            continue
        expected=reference.values(app,state,shifts)
        expected={p.replace('Line/OwnerId','Line/Owner').replace('Line/LastUpdatedAt','Line/LastUpdate'):v for p,v in expected.items()}
        import fraktal_ab_canonical_reader as reader
        def walk(value,path=''):
            if isinstance(value,dict) and value.get('string'):
                yield path,bytes.fromhex(value['bytes']).decode('utf-8')
            elif isinstance(value,dict):
                for name,item in value.items():
                    if name!='Valid':yield from walk(item,path+'/'+name if path else name)
            elif isinstance(value,list):
                for slot,item in enumerate(value[:shifts['Count']],1):yield from walk(item,path+f'[{slot}]')
            else:
                leaf=path.rsplit('/',1)[-1]
                if leaf in ('LastUpdate','ShiftStartedAt','ShiftEndsAt','StartAt','EndAt'):value=reader.timestamp_ns(value)
                elif leaf in ('Revision','ProductionTarget','ShiftProductionTarget','GoodCount','NokCount','ReworkCount','RunMs','DownMs','IdleMs'):value&=0xffffffff
                yield path,value
        actual=dict(walk(record))
        if actual!=expected or {p:type(v) for p,v in actual.items()}!={p:type(v) for p,v in expected.items()}:
            raise ValueError(f'S3i native values differ at {CASES[i]}')
    return dict(passed=True,cases=len(CASES),readOnly=True,ownersRestoredExactly=True)


def read_results(comm):
    import fraktal_ab_canonical_reader as reader
    import fraktal_ab_s3f_fixture_execute as fixture
    device=comm.GetDeviceProperties()
    if device.Status!='Success' or device.Value is None or (str(device.Value.SerialNumber).lower(),device.Value.ProductName,device.Value.Revision)!=('0x601fc87b','Emulate 5580 Controller','38.11'):
        raise ValueError('fixed local Echo identity guard failed')
    app=demo.application();unused,capture=reader.read_document(comm,expect_serial='601FC87B')
    if capture['manifest']['contentHash']!=fixture.expected_manifest(app):raise ValueError('S3i publication required')
    symbol=next(s for s in capture['symbols'] if s['name']==tag(app));response=comm.Read(tag(app))
    if response.Status!='Success' or not isinstance(response.Value,bytes):raise ValueError('S3i result read failed')
    result=reader.decode_record(response.Value,symbol['handle'],capture['templates'])
    return dict(verify_result(app,result),result=result,rawHex=response.Value.hex(),symbol=symbol,templates=capture['templates'])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--seed',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv)
    if args.output.exists():parser.error('new generated output required')
    report=generate(args.seed,args.output);print(json.dumps(report,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
