"""Durable outbox/SQLite acceptance on the existing isolated simulator bench."""
import argparse,importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('recovery_fixture',HERE.parent/'AlarmRecovery/make_fixture.py')
RECOVERY=importlib.util.module_from_spec(spec);spec.loader.exec_module(RECOVERY)
STREAM='78f23c0b-7bce-4521-96d5-3f5ee7e3f4ce'

def prepare(out,frames):
    value=RECOVERY.HISTORY.ACCESS.SETS.CONFIG.declaration()
    value['alarm_delivery']={'scopes':['StationA','StationA.Satellite','StationB'],'capacity':8,'stream_id':STREAM}
    RECOVERY.prepare(out,frames,value)
    from fraktal_tia_generate import db
    from fraktal_tia_binding import READONLY,PRIVATE
    (out/'05_GDB_DeliveryTest.db').write_bytes(db('GDB_DeliveryTest',[
        'Operation : Int;', 'Text : WString[255];', 'Reason : DInt;', 'UnicodeMode : Bool;',
        'Applied'+READONLY+' : Bool;', 'EventSlot'+READONLY+' : Int;',
        'RecoveryCheck'+READONLY+' : Int;', 'RecoveryIndex'+READONLY+' : Int;',
        'Diag'+PRIVATE+' : "ST_Diagnostic";']).replace('END_VAR\nBEGIN','END_VAR\nVAR RETAIN\n    Scope : String[80];\n    Damage : Int;\nEND_VAR\nBEGIN').encode('ascii'))
    (out/'39e_EventDeliveryBench.scl').write_bytes((HERE/'bench.scl.in').read_bytes())
    p=out/'39d_AlarmRecoveryBench.scl';text=p.read_text('ascii')
    for scope in ('"StationA"','"StationA".Satellite','"StationB"'):
        anchor='                "FRK_AlarmRecoveryClosePrepare"(AlarmLog := '+scope+'.AlarmLog, EventSlot := #EventSlot);'
        assert text.count(anchor)==1
        text=text.replace(anchor,'                "FRK_DeliveryCapture"(AlarmLog := '+scope+'.AlarmLog, Ev := '+scope+'.AlarmLog.Active[#EventSlot]);\n'+anchor)
    p.write_bytes(text.encode('ascii'))
    p=out/'38_ConfigBenchRoutines.scl';text=p.read_text('ascii')
    anchor='    "F_AlarmRecoveryDamage"(Startup := #Startup);';assert text.count(anchor)==1
    text=text.replace(anchor,anchor+'\n    "F_RecoveryCheckpointInspect"(Startup := #Startup);\n    "F_DeliveryDamage"(Startup := #Startup);')
    anchor='    "F_AlarmRecoveryBench"();';assert text.count(anchor)==1
    text=text.replace(anchor,anchor+'\n    "F_DeliveryBench"();')
    p.write_bytes(text.encode('ascii'))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('out',type=Path);parser.add_argument('frames',type=Path)
    args=parser.parse_args();prepare(args.out,args.frames)
