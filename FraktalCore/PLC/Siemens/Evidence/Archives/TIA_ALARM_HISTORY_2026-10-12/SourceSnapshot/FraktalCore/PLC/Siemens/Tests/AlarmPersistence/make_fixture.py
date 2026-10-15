"""Closed-ring retention on the two-root, six-Unit simulator bench."""
import argparse
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('access_fixture',HERE.parent/'AccessPersistence/make_fixture.py')
ACCESS=importlib.util.module_from_spec(spec);spec.loader.exec_module(ACCESS)
def prepare(out,frames):
    value=ACCESS.SETS.CONFIG.declaration()
    value['alarm_history']={'scopes':['StationA','StationA.Satellite','StationB']}
    ACCESS.prepare(out,frames,value)
    from fraktal_tia_generate import db
    from fraktal_tia_binding import PRIVATE,READONLY
    (out/'05_GDB_AlarmPersistTest.db').write_bytes(db('GDB_AlarmPersistTest',[
        'Operation : Int;', 'UnicodeMode : Int;', 'Scope : String[80];', 'Text : WString[255];', 'Reason : DInt;',
        'Slot'+READONLY+' : Int;', 'Generation'+READONLY+' : UDInt;',
        'Checksum'+READONLY+' : DWord;', 'Used'+READONLY+' : Int;', 'Applied'+READONLY+' : Bool;',
    ]).encode('ascii'))
    (out/'39c_AlarmPersistenceBench.scl').write_bytes((HERE/'bench.scl.in').read_bytes())
    path=out/'38_ConfigBenchRoutines.scl';text=path.read_text('ascii')
    anchor='    "F_AccessPersistenceBench"(Startup := #Startup);'
    assert text.count(anchor)==1
    path.write_bytes(text.replace(anchor,anchor+'\n    "F_AlarmPersistenceBench"();').encode('ascii'))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);p.add_argument('frames',type=Path)
    a=p.parse_args();prepare(a.out,a.frames)
