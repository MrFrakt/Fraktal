"""Combine the qualified LOAD_DB consumers and shared sequence test events."""
import argparse
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


def prepare(out,frames):
    view=module('sequence_view_fixture',HERE/'make_fixture.py')
    persist=module('persistence_fixture',HERE.parent/'Persistence/make_fixture.py')
    value=view.select(persist.RECOVERY.HISTORY.ACCESS.SETS.CONFIG.declaration())
    value['persistence']={'medium':'LOAD_DB','minimum_write_ms':1000,'queue_capacity':4}
    persist.RECOVERY.prepare(out,frames,value)
    persist.add_controls(out,frames)
    view.add_controls(out)
    from fraktal_tia_generate import db
    from fraktal_tia_binding import READONLY
    from fraktal_tia_config import function
    (out/'08_GDB_SequenceQuiesceTest.db').write_bytes(db('GDB_SequenceQuiesceTest',[
        'Enabled : Bool;', 'BeforeActive'+READONLY+' : Bool;', 'AfterActive'+READONLY+' : Bool;',
        'HistorySurvived'+READONLY+' : Bool;']).encode('ascii'))
    root_type=value['roots'][0]['type'];stem=root_type.removeprefix('FB_')
    body=['    IF NOT "GDB_SequenceQuiesceTest".Enabled THEN RETURN; END_IF;',
          '    "GDB_SequenceQuiesceTest".BeforeActive := "StationA".ActiveSteps[0].RowIdx > 0;',
          '    #CountBefore := "StationA".SequenceStepCount; #VisitedBefore := "StationA".SequenceSteps[1].Visited;',
          '    "FRK_Quiesce_'+stem+'"(Module := "StationA", Hal := "GDB_FraktalHal".Data.StationA);',
          '    "GDB_SequenceQuiesceTest".AfterActive := "StationA".ActiveSteps[0].RowIdx > 0;',
          '    "GDB_SequenceQuiesceTest".HistorySurvived := #VisitedBefore AND "StationA".SequenceSteps[1].Visited AND #CountBefore = "StationA".SequenceStepCount;']
    (out/'39h_SequenceQuiesceBench.scl').write_bytes(function('F_TestSequenceQuiesce',[],[],['CountBefore : Int;','VisitedBefore : Bool;'],body).encode('ascii'))
    p=out/'38_ConfigBenchRoutines.scl';text=p.read_text('ascii')
    marker='FUNCTION "F_ConfigBenchObserve"';before,after=text.split(marker,1)
    assert after.count('END_FUNCTION')==1
    after=after.replace('END_FUNCTION','    "F_TestSequenceQuiesce"();\nEND_FUNCTION')
    p.write_bytes((before+marker+after).encode('ascii'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);p.add_argument('frames',type=Path)
    a=p.parse_args();prepare(a.out,a.frames)
