"""Active manual-reset recovery on the history/config/decision simulator bench."""
import argparse,importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('history_fixture',HERE.parent/'AlarmPersistence/make_fixture.py')
HISTORY=importlib.util.module_from_spec(spec);spec.loader.exec_module(HISTORY)
def prepare(out,frames):
    value=HISTORY.ACCESS.SETS.CONFIG.declaration()
    value['alarm_recovery']={'scopes':['StationA','StationA.Satellite']}
    HISTORY.prepare(out,frames,value)
    from fraktal_tia_generate import db
    from fraktal_tia_binding import PRIVATE,READONLY
    (out/'05_GDB_AlarmRecoveryTest.db').write_bytes(db('GDB_AlarmRecoveryTest',[
        'Operation : Int;', 'EventSlot : Int;', 'Reason : DInt;',
        'ResetClass : DInt;', 'Text : WString[255];', 'Automatic : Bool;',
        'ReturnSlot'+READONLY+' : Int;', 'Generation'+READONLY+' : UDInt;',
        'Elapsed'+READONLY+' : UDInt;', 'CauseSlot'+READONLY+' : Int;',
        'DamageApplied'+READONLY+' : Bool;', 'StartupBlocked'+READONLY+' : Bool;',
        'Diag'+PRIVATE+' : "ST_Diagnostic";',
    ]).replace('END_VAR\nBEGIN','END_VAR\nVAR RETAIN\n    Scope : String[80];\n    Damage : Int;\n    StickyCause : Bool;\nEND_VAR\nBEGIN').encode('ascii'))
    (out/'05_GDB_RecoveryStamp.db').write_bytes(db('GDB_RecoveryStamp',['Data'+PRIVATE+' : DTL;']).encode('ascii'))
    (out/'39d_AlarmRecoveryBench.scl').write_bytes((HERE/'bench.scl.in').read_bytes())
    path=out/'38_ConfigBenchRoutines.scl';text=path.read_text('ascii')
    anchor='    "F_AlarmPersistenceBench"();'
    assert text.count(anchor)==1
    text=text.replace(anchor,anchor+'\n    "F_AlarmRecoveryBench"();')
    first=text.index('\nBEGIN\n',text.index('FUNCTION "F_ConfigBenchPrepare"'))+len('\nBEGIN\n')
    text=text[:first]+'    "F_AlarmRecoveryDamage"(Startup := #Startup);\n'+text[first:]
    path.write_bytes(text.encode('ascii'))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);p.add_argument('frames',type=Path)
    a=p.parse_args();prepare(a.out,a.frames)
