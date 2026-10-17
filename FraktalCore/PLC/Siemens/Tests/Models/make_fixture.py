"""Root-scoped model creation, atomic persistence and restart fault injection."""
import argparse
import importlib.util
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('models_classes_fixture',HERE.parent/'DataClasses/make_fixture.py')
BASE=importlib.util.module_from_spec(spec);spec.loader.exec_module(BASE)


def declaration():
    value=BASE.declaration();value['model_config']['capacity']=3
    return value


def prepare(out,frames):
    BASE.prepare(out,frames,declaration())
    from fraktal_tia_binding import Catalog,PRIVATE,READONLY
    from fraktal_tia_config import function
    from fraktal_tia_generate import db
    info=json.loads((frames/'manifest.json').read_bytes())
    slot=next(d['index'] for d in info['runtime']['persistence']['documents'] if d['role']=='models' and d['root']==1)
    pool=int(re.search(r'Array\[1\.\.(\d+)\] of "FRK_ConfigSlot"',(out/'05_FRK_ConfigStore.db').read_text('ascii'))[1])
    reservations=Catalog.read().capacities['MAX_SET_RECORDS']
    (out/'05_GDB_ModelTest.db').write_bytes(db('GDB_ModelTest',[
        'PoisonPulse : Bool;','DamagePulse : Bool;',
        'DropCachePulse : Bool;','DamageSetPulse : Bool;','RepairSetPulse : Bool;',
        'CacheDropped'+READONLY+' : Bool;','SetDamaged'+READONLY+' : Bool;','SetRepaired'+READONLY+' : Bool;',
        'Poisoned'+READONLY+' : Bool;','Damaged'+READONLY+' : Bool;',
        'Done'+READONLY+' : Bool;','Checks'+READONLY+' : Int;','Failures'+READONLY+' : Int;',
        'FirstFailure'+READONLY+' : Int;','PendingSeen'+READONLY+' : Bool;',
        'PrematurePublication'+READONLY+' : Bool;','StagedPreset'+READONLY+' : DInt;',
        'ModelDocument'+READONLY+' : Int := %d;'%slot,
        'Result'+PRIVATE+' : "FRK_TestResult";',
        'SavedRecord'+PRIVATE+' : "ST_ConfigRecord";',
    ]).encode('ascii'))
    cat='"FRK_ModelStore".Rows[1]';work='"FRK_ModelRuntime".Rows[1]'
    consumer='"FRK_PersistConsumers".Rows[%d]'%slot
    body=['    "GDB_ModelTest".StagedPreset := "StationA".ConfigStageParCfg.Preset;',
        '    IF '+work+'.State = 1 THEN',
        '        "GDB_ModelTest".PendingSeen := TRUE;',
        '        IF '+cat+'.Count = '+work+'.Stage.Count AND ('+consumer+'.Ticket <> 0 OR '+consumer+'.Dirty) THEN "GDB_ModelTest".PrematurePublication := TRUE; END_IF;',
        '    END_IF;',
        '    IF "GDB_ModelTest".DropCachePulse THEN',
        '        #TargetSlot := "FRK_ConfigFind"(Scope := \'StationA\', Key := \'preset\', ModelCode := \'MODEL_B\');',
        '        IF #TargetSlot > 0 THEN "FRK_ConfigStore".Rows[#TargetSlot].Used := FALSE; "GDB_ModelTest".CacheDropped := TRUE; END_IF;',
        '        "GDB_ModelTest".DropCachePulse := FALSE;', '    END_IF;',
        '    IF "GDB_ModelTest".DamageSetPulse AND "FRK_SetStore".Sets[2, 1].Info.Used THEN',
        '        #Index := "FRK_SetStore".Sets[2, 1].Info.RecordCount;',
        '        "GDB_ModelTest".SavedRecord := "FRK_SetStore".Sets[2, 1].Records[#Index];',
        '        "FRK_SetStore".Sets[2, 1].Records[#Index].Revision := "FRK_SetStore".Sets[2, 1].Records[#Index].Revision + 1;',
        '        "GDB_ModelTest".SetDamaged := TRUE; "GDB_ModelTest".DamageSetPulse := FALSE;', '    END_IF;',
        '    IF "GDB_ModelTest".RepairSetPulse THEN',
        '        #Index := "FRK_SetStore".Sets[2, 1].Info.RecordCount;',
        '        IF #Index > 0 THEN "FRK_SetStore".Sets[2, 1].Records[#Index] := "GDB_ModelTest".SavedRecord; END_IF;',
        '        "GDB_ModelTest".SetRepaired := TRUE; "GDB_ModelTest".RepairSetPulse := FALSE;', '    END_IF;',
        '    IF "GDB_ModelTest".PoisonPulse THEN',
        '        '+cat+'.Codes[3] := \'POISON\'; '+cat+'.Checksum := DWORD#0;',
        '        "GDB_ModelTest".Poisoned := TRUE; "GDB_ModelTest".PoisonPulse := FALSE;', '    END_IF;',
        '    IF "GDB_ModelTest".DamagePulse THEN',
        '        "FRK_PersistAnchors".RowsA[%d].Checksum := "FRK_PersistAnchors".RowsA[%d].Checksum XOR DWORD#1;'%(slot,slot),
        '        "FRK_PersistAnchors".RowsB[%d].Checksum := "FRK_PersistAnchors".RowsB[%d].Checksum XOR DWORD#1;'%(slot,slot),
        '        "GDB_ModelTest".Damaged := TRUE; "GDB_ModelTest".DamagePulse := FALSE;', '    END_IF;',
        '    IF "GDB_ModelTest".Done OR NOT "FRK_ModelRuntime".Rows[1].Ready THEN RETURN; END_IF;',
        '    #Image := '+cat+';']
    labels=[]
    def assertion(label,expr):
        labels.append(label)
        body.append('    "FRK_TestAssert"(Condition := '+expr+', Code := %d, Result := "GDB_ModelTest".Result);'%len(labels))
    assertion('accepted catalog','"FRK_ModelValid"(RootIndex := 1, Catalog := #Image)')
    for label,mutation in [('schema','SchemaVersion := 2'),('generation','Generation := 0'),
        ('count','Count := 4'),('capacity','Capacity := 4'),('seed prefix',"Codes[1] := 'wrong'"),
        ('checksum','Checksum := #Image.Checksum XOR DWORD#1')]:
        body+=['    #Image := '+cat+'; #Image.'+mutation+';']
        assertion(label+' refused','NOT "FRK_ModelValid"(RootIndex := 1, Catalog := #Image)')
    body+=['    #Image := '+cat+';']
    assertion('peer scope refused','NOT "FRK_ModelValid"(RootIndex := 2, Catalog := #Image)')
    assertion('empty code refused','NOT "FRK_ModelCodeValid"(Code := \'\')')
    assertion('printable code accepted','"FRK_ModelCodeValid"(Code := \'MODEL_NEW\')')
    assertion('control character refused','NOT "FRK_ModelCodeValid"(Code := \'$0A\')')
    assertion('out of bound index empty','"FRK_ConfigModelCode"(RootIndex := 1, ModelIndex := 4) = \'\'')
    body+=['    FOR #PoolIndex := 1 TO %d DO'%pool,
        '        #SavedUsed[#PoolIndex] := "FRK_ConfigStore".Rows[#PoolIndex].Used;',
        '        "FRK_ConfigStore".Rows[#PoolIndex].Used := TRUE;', '    END_FOR;',
        '    FOR #Index := 1 TO %d DO #Reserved[#Index] := 0; END_FOR;'%reservations,
        '    #TargetSlot := "FRK_ConfigReserve"(Scope := \'__NoSuchScope\', Key := \'reserved\', ModelCode := \'__New\', Reserved := #Reserved);']
    assertion('full pool reservation returns zero','#TargetSlot = 0')
    body+=['    "FRK_ConfigStore".Rows[%d].Used := FALSE;'%(pool-1),
        '    "FRK_ConfigStore".Rows[%d].Used := FALSE;'%pool,
        '    #Reserved[1] := "FRK_ConfigReserve"(Scope := \'__NoSuchScope\', Key := \'reserved\', ModelCode := \'__New\', Reserved := #Reserved);',
        '    #Reserved[2] := "FRK_ConfigReserve"(Scope := \'__NoSuchScope\', Key := \'reserved\', ModelCode := \'__New\', Reserved := #Reserved);']
    assertion('reservation consumes first free slot','#Reserved[1] = %d'%(pool-1))
    assertion('next reservation never aliases prior target','#Reserved[2] = %d'%pool)
    body+=['    FOR #PoolIndex := 1 TO %d DO "FRK_ConfigStore".Rows[#PoolIndex].Used := #SavedUsed[#PoolIndex]; END_FOR;'%pool]
    body+=['    "GDB_ModelTest".Checks := "GDB_ModelTest".Result.Checks;',
        '    "GDB_ModelTest".Failures := "GDB_ModelTest".Result.Failures;',
        '    "GDB_ModelTest".FirstFailure := "GDB_ModelTest".Result.FirstFailure;',
        '    "GDB_ModelTest".Done := NOT "GDB_ModelTest".Result.ProtocolError;']
    (out/'39h_ModelBench.scl').write_bytes(function('F_ModelBench',[],[],[
        'Image : "FRK_ModelCatalog";','PoolIndex : DInt;','Index : Int;','TargetSlot : Int;',
        'SavedUsed : Array[1..%d] of Bool;'%pool,'Reserved : Array[1..%d] of Int;'%reservations],body).encode('ascii'))
    (out/'model_assertions.json').write_text(json.dumps(labels,indent=2)+'\n',encoding='ascii')
    p=out/'38_ConfigBenchRoutines.scl';text=p.read_text('ascii');anchor='    "F_ClassPolicyBench"();'
    assert text.count(anchor)==1
    p.write_bytes(text.replace(anchor,anchor+'\n    "F_ModelBench"();').encode('ascii'))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('out',type=Path);parser.add_argument('frames',type=Path)
    args=parser.parse_args();prepare(args.out,args.frames)
