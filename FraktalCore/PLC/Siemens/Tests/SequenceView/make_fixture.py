"""Synthetic Core 3.13 events on the guarded config bench; no press plant."""
import argparse
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('config_fixture', HERE.parent/'Config/make_fixture.py')
CONFIG = importlib.util.module_from_spec(spec); spec.loader.exec_module(CONFIG)


def select(value):
    for t in value['types']:
        if 'unit' in t:
            t['sequence_view'] = {'capacity':4, 'branches':2, 'annotations':2}
            t['logic']['Sequences'] = '    "F_TestSequenceView"(Owner := #Core.RegIndex);'
    return value


def prepare(out, frames):
    CONFIG.prepare(out, frames, select(CONFIG.declaration()))
    add_controls(out)


def add_controls(out):
    from fraktal_tia_generate import db
    from fraktal_tia_binding import READONLY
    from fraktal_tia_config import function
    # Exercise the real sequence helper path as well as direct synthetic view
    # events. These shared types/services are the exact press generator output.
    from fraktal_tia_examples import build as press_build
    shared,_,_=press_build()
    for filename,source in shared.items():
        if filename in ('06_FRK_SequenceCtx.udt','06_FRK_SequenceRow.udt','16_SequenceServices.scl') or filename.endswith('_ST_SequenceCommandLease.udt'):
            (out/filename).write_bytes(source.encode('ascii'))
    (out/'08_GDB_SequenceHelperTest.db').write_bytes(db('GDB_SequenceHelperTest',[
        'Seq'+READONLY+' : "FRK_SequenceCtx";', 'Row'+READONLY+' : "FRK_SequenceRow";',
        'Diag : "ST_Diagnostic";', 'WaitOk'+READONLY+' : Bool;']).encode('ascii'))
    fields = ['Owner : DInt;', 'Enabled : Bool;', 'Annotate : Bool;', 'IsError : Bool;',
              'StepNo : DInt;', 'Branch : DInt;', 'Depth : Int;', 'Visit : UDInt;',
              'StepName : String[120];', 'ExpectedTime : Time;', 'Elapsed : Time;',
              'Key : String[120];', 'SourcePath : String[80];', 'FastPulse : Bool;', 'Parent : Bool;',
              'AwaitEnabled : Bool;', 'AwaitOk : Bool;', 'AwaitLabel : String[120];',
              'UseHelper : Bool;', 'HelperReset : Bool;', 'HelperOffset : DInt;',
              'Overflow'+READONLY+' : Bool;']
    (out/'06_GDB_SequenceViewTest.db').write_bytes(db('GDB_SequenceViewTest',fields).encode('ascii'))
    c='"GDB_SequenceViewTest".'
    record='"FRK_SeqViewStep"(Owner := #Owner, StepNo := '+c+'StepNo, Branch := '+c+'Branch, Depth := '+c+'Depth, Visit := '+c+'Visit, StepName := '+c+'StepName, AwaitingLabel := \'test.await\', AwaitsPath := \'StationA.Cell.Clamp\', TimeClass := 0, ExpectedTime := '+c+'ExpectedTime, Elapsed := '+c+'Elapsed);'
    h='"GDB_SequenceHelperTest".'
    helper=['    IF '+c+'UseHelper THEN',
        '        "FRK_SeqBegin"(Run := '+c+'Enabled, Reset := '+c+'HelperReset, OwnerIndex := #Owner, ChainIndex := 7, BranchIndex := '+c+'Branch, ViewOffset := '+c+'HelperOffset, ViewDepth := '+c+'Depth, Delta := T#1ms, Seq := '+h+'Seq);',
        '        '+c+'HelperReset := FALSE;',
        '        IF '+c+'Enabled THEN',
        '            "FRK_SeqStep"(StepNo := '+c+'StepNo, StepName := '+c+'StepName, AwaitingLabel := \'test.helper.await\', AwaitsPath := \'StationA.Cell.Clamp\', TimeClass := 0, ExpectedTime := '+c+'ExpectedTime, Seq := '+h+'Seq, Row := '+h+'Row);',
        '            '+h+'WaitOk := "FRK_SeqAwait"(Label := '+c+'AwaitLabel, Ok := '+c+'AwaitOk, Seq := '+h+'Seq);',
        '            IF '+c+'Annotate THEN "FRK_SeqMessage"(Diag := '+h+'Diag, Seq := '+h+'Seq, AlarmLog := "StationA".AlarmLog); END_IF;',
        '        END_IF;',
        '        RETURN;', '    END_IF;']
    body=['    IF #Owner <> '+c+'Owner THEN RETURN; END_IF;',*helper,
          '    IF '+c+'Enabled THEN', '        '+record,
          '        IF '+c+'FastPulse THEN',
          '            "FRK_SeqViewStep"(Owner := #Owner, StepNo := 11, Branch := 0, Depth := 0, Visit := 1, StepName := \'test.fast\', AwaitingLabel := \'\', AwaitsPath := \'\', TimeClass := 0, ExpectedTime := T#0ms, Elapsed := T#2ms);',
          '            '+c+'FastPulse := FALSE;', '        END_IF;',
          '        IF '+c+'Parent THEN',
          '            "FRK_SeqViewStep"(Owner := #Owner, StepNo := 20, Branch := '+c+'Branch, Depth := 0, Visit := 1, StepName := \'test.parent\', AwaitingLabel := \'\', AwaitsPath := \'\', TimeClass := 0, ExpectedTime := T#0ms, Elapsed := T#0ms);', '        END_IF;',
          '        IF '+c+'AwaitEnabled THEN "FRK_SeqViewAwait"(Owner := #Owner, StepNo := '+c+'StepNo, Branch := '+c+'Branch, Label := '+c+'AwaitLabel, Ok := '+c+'AwaitOk); END_IF;',
          '        IF '+c+'Annotate THEN "FRK_SeqViewNote"(Owner := #Owner, StepNo := '+c+'StepNo, Branch := '+c+'Branch, IsError := '+c+'IsError, Key := '+c+'Key, SourcePath := '+c+'SourcePath); END_IF;',
          '    END_IF;',
          '    IF #Owner = "StationA".Core.RegIndex THEN '+c+'Overflow := "FRK_Views".V001.Book.Overflow; END_IF;']
    (out/'39g_SequenceViewStimulus.scl').write_bytes(function('F_TestSequenceView',['Owner : DInt;'],[],[],body).encode('ascii'))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);p.add_argument('frames',type=Path)
    a=p.parse_args();prepare(a.out,a.frames)
