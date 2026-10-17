"""Two root policies over the same module type and shared line values."""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('classes_operations_fixture', HERE.parent/'Operations/make_frame_fixture.py')
BASE = importlib.util.module_from_spec(spec); spec.loader.exec_module(BASE)


def declaration():
    value = BASE.declaration()
    value['data_classes'] = {
        'StationA': [dict(id='public',label='test.config.preset',read_level=0,write_level=1),
                     dict(id='commissioning',label='test.config.timeout',read_level=3,write_level=3)],
        'StationB': [dict(id='public',label='test.config.preset',read_level=2,write_level=2)],
    }
    unit = next(t for t in value['types'] if 'production' in t)
    for field in unit['config']:
        if field['key'] in ('siteLabel','gain','capturedCycles'): field.update(class_id='public',min_read=0,min_write=0)
        if field['key']=='gain': field['min_write']=3
        if field['key']=='preset': field['class_id']='commissioning'
        if field['key']=='grade': field['class_id']='undeclared'
    for field in value['line']['values']:
        field.update(class_id='public',min_read=0,min_write=0)
    return value


def prepare(out, frames, value=None):
    BASE.OWNER.CONFIG.PERSIST.RECOVERY.prepare(out,frames,declaration() if value is None else value)
    BASE.OWNER.CONFIG.PERSIST.add_controls(out,frames)
    from fraktal_tia_binding import Catalog,PRIVATE,READONLY
    from fraktal_tia_config import function
    from fraktal_tia_generate import db
    from fraktal_tia_test_runtime import build
    for name,text in build().items(): (out/name).write_bytes(text.encode('ascii'))
    info=json.loads((frames/'manifest.json').read_bytes())
    capacity=Catalog.read().capacities['MAX_DATA_CLASSES']
    slot=next(d['index'] for d in info['runtime']['persistence']['documents'] if d['key']=='StationA.classes')
    (out/'05_GDB_ClassPolicyTest.db').write_bytes(db('GDB_ClassPolicyTest',[
        'PoisonPulse : Bool;', 'DamagePulse : Bool;', 'Done'+READONLY+' : Bool;',
        'Poisoned'+READONLY+' : Bool;', 'Damaged'+READONLY+' : Bool;',
        'Checks'+READONLY+' : Int;', 'Failures'+READONLY+' : Int;',
        'FirstFailure'+READONLY+' : Int;', 'ClassDocument'+READONLY+' : Int := %d;'%slot,
        'ClassGeneration'+READONLY+' : UDInt;',
        'Result'+PRIVATE+' : "FRK_TestResult";',
        'EmptyImage'+PRIVATE+' : "FRK_ClassPolicyImage";',
    ]).encode('ascii'))
    result='"GDB_ClassPolicyTest".Result'
    labels=[];body=[]
    def assertion(label,expression):
        labels.append(label)
        body.append('    "FRK_TestAssert"(Condition := '+expression+', Code := %d, Result := '%len(labels)+result+');')
    image='"FRK_ClassPolicies".Rows[1]'
    body += ['    "GDB_ClassPolicyTest".ClassGeneration := '+image+'.Generation;',
             '    IF "GDB_ClassPolicyTest".PoisonPulse THEN',
             '        '+image+'.Rows[1].WriteLevel := 0; '+image+'.Rows[1].ReadLevel := 0;',
             '        '+image+'.Checksum := DWORD#0;',
             '        "GDB_ClassPolicyTest".PoisonPulse := FALSE; "GDB_ClassPolicyTest".Poisoned := TRUE;', '    END_IF;',
             '    IF "GDB_ClassPolicyTest".DamagePulse THEN',
             '        "FRK_PersistAnchors".RowsA[%d].Checksum := "FRK_PersistAnchors".RowsA[%d].Checksum XOR DWORD#1;'%(slot,slot),
             '        "FRK_PersistAnchors".RowsB[%d].Checksum := "FRK_PersistAnchors".RowsB[%d].Checksum XOR DWORD#1;'%(slot,slot),
             '        "GDB_ClassPolicyTest".DamagePulse := FALSE; "GDB_ClassPolicyTest".Damaged := TRUE;', '    END_IF;',
             '    IF "GDB_ClassPolicyTest".Done OR NOT "FRK_ClassValid"(Image := '+image+') THEN RETURN; END_IF;',
             '    #Image := '+image+';']
    assertion('accepted retained class image','"FRK_ClassValid"(Image := #Image)')
    for label,mutation in [('zero count','Count := 0'),('oversize count','Count := %d'%(capacity+1)),('invalid level','Rows[1].WriteLevel := 5'),('duplicate identity','Rows[2].ClassId := #Image.Rows[1].ClassId'),('missing identity','Rows[1].ClassId := \'\''),('invalid checksum','Checksum := #Image.Checksum XOR DWORD#1')]:
        body += ['    #Image := '+image+'; #Image.'+mutation+';']
        assertion(label+' refused','NOT "FRK_ClassValid"(Image := #Image)')
    body += ['    #Image := "GDB_ClassPolicyTest".EmptyImage;']
    assertion('new domain virgin','"FRK_ClassVirgin"(Image := #Image)')
    body += ['    #Image.Rows[%d].WriteLevel := 1;'%capacity]
    assertion('nonzero unused slot never virgin','NOT "FRK_ClassVirgin"(Image := #Image)')
    body += ['    #Access := "StationA".Access; #Access.Policy.Required[0] := 4; #Access.Policy.Required[1] := 4;']
    body += ['    #Access.Classes[1].ReadLevel := 0; #Access.Classes[1].WriteLevel := 1;']
    for label,identity,minimum,write,expected in [('public read lowers blanket','public',0,False,0),('public write lowers blanket','public',0,True,1),('own minimum raises class','public',3,True,3),('unknown class fails admin','unknown',0,True,4),('builtin keeps blanket','',0,True,4),('invalid minimum fails admin','public',5,True,4)]:
        assertion(label,'"FRK_DataLevel"(Access := #Access, ClassId := \''+identity+'\', Minimum := %d, ForWrite := %s) = %d'%(minimum,str(write).upper(),expected))
    body += ['    #Access.ClassesLost := TRUE;']
    assertion('lost class policy blocks writes','NOT "FRK_DataPolicyReady"(Access := #Access)')
    body += ['    "GDB_ClassPolicyTest".Checks := '+result+'.Checks;',
             '    "GDB_ClassPolicyTest".Failures := '+result+'.Failures;',
             '    "GDB_ClassPolicyTest".FirstFailure := '+result+'.FirstFailure;',
             '    "GDB_ClassPolicyTest".Done := NOT '+result+'.ProtocolError;']
    (out/'39g_ClassPolicyBench.scl').write_bytes(function('F_ClassPolicyBench',[],[],['Image : "FRK_ClassPolicyImage";','Access : "FRK_Access";'],body).encode('ascii'))
    (out/'class_assertions.json').write_text(json.dumps(labels,indent=2)+'\n',encoding='ascii')
    p=out/'38_ConfigBenchRoutines.scl';text=p.read_text('ascii');anchor='    "F_AlarmPersistenceBench"();'
    assert text.count(anchor)==1
    p.write_bytes(text.replace(anchor,anchor+'\n    "F_ClassPolicyBench"();').encode('ascii'))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out',type=Path); parser.add_argument('frames',type=Path)
    args=parser.parse_args(); prepare(args.out,args.frames)
