"""Native GRAPH recovery on simulated child modules; no physical press bench."""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))
from fraktal_tia_binding import Catalog, PRIVATE, READONLY
from fraktal_tia_examples import bind
from fraktal_tia_generate import db
import fraktal_tia_graph as GRAPH


def prepare(out, frames):
    spec = importlib.util.spec_from_file_location('profile_fixture', HERE.parent / 'CycleProfile/make_runtime_fixture.py')
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    fixture.prepare(out, frames)
    args = [('Enabled', 'Bool'), ('RestartOnStart', 'Bool'), ('Fault', 'Bool'),
            ('Finish', 'Bool'), ('Permit', 'Bool'), ('LateTimeout', 'Bool'), ('AbortPLC', 'Bool'), ('RequestSeq', 'UDInt')]
    public = [('AckSeq', 'UDInt'), ('Seq', '"FRK_SequenceCtx"'), ('EntryCount', 'UDInt'),
              ('IssueCount', 'UDInt'), ('EventCount', 'UDInt'), ('LowScans', 'UDInt'), ('Running', 'Bool'),
              ('Delay', 'Time'), ('Frozen', 'Bool'), ('ResumePending', 'Bool')]
    (out / '08_GDB_RecoveryTest.db').write_bytes(db('GDB_RecoveryTest',
        [n+' : '+ty+';' for n, ty in args]+[n+READONLY+' : '+ty+';' for n, ty in public]).encode('ascii'))
    (out / '08_GDB_RecoveryWork.db').write_bytes(db('GDB_RecoveryWork',
        [n+PRIVATE+' : '+ty+';' for n, ty in args[:-1]]+
        [n+PRIVATE+' : '+ty+';' for n, ty in [('Seq', '"FRK_SequenceCtx"'),
            ('Row', '"FRK_SequenceRow"'), ('Lease', '"ST_SequenceCommandLease"'),
            ('Ready', 'Bool'), ('Zero', 'Time')]]).encode('ascii'))
    actions = []
    for step, successor in ((0, 42), (42, 99), (99, 0)):
        actions.append({'no': step, 'next': successor, 'when': {'eq': ['#Seq.RetVal', Catalog.read().enums['E_StepResult']['ADVANCE']]},
                        'actions': [{'text': GRAPH.call_text('F_RecoveryStep',
                            [('StepNo', str(step)), ('Seq', '#Seq'), ('Target', '#Target'),
                             ('Core', '#Core'), ('Status', '#Status')])}]})
    chart = {'name': 'FB_GRAPH_RecoveryTest', 'number': 870, 'steps': actions,
             'inout': [('Seq', 'FRK_SequenceCtx'), ('Target', 'FB_DeclarationCylinder'),
                       ('Core', 'FRK_Core'), ('Status', 'ST_ModuleStatus')],
             'graph_settings': {'acknowledge_errors_required': False}}
    reference = HERE.parents[1] / 'Spikes/S11_Graph/reference/FB_GraphSample.xml'
    xml = GRAPH.generate(chart, reference.read_text('utf-8-sig'))
    (out / '27_FB_GRAPH_RecoveryTest.xml').write_bytes(xml.encode('ascii'))
    (out.parent / 'recovery_graph.json').write_text(json.dumps(GRAPH.dump(xml), indent=2)+'\n', encoding='ascii')
    (out / '29_GDB_GRAPH_RecoveryTest.db').write_bytes(('DATA_BLOCK "GDB_GRAPH_RecoveryTest"\n'
        "{ S7_Optimized_Access := 'TRUE' }\nVERSION : 0.1\nNON_RETAIN\n"
        '"FB_GRAPH_RecoveryTest"\nBEGIN\nEND_DATA_BLOCK\n').encode('ascii'))
    source = '''FUNCTION "F_RecoveryStep" : Void
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
VAR_INPUT StepNo : DInt; END_VAR
VAR_IN_OUT Seq : "FRK_SequenceCtx"; Target : "FB_DeclarationCylinder";
    Core : "FRK_Core"; Status : "ST_ModuleStatus"; END_VAR
VAR_TEMP EventNow : Bool; END_VAR
BEGIN
    "FRK_SeqStep"(Seq := #Seq, Row := "GDB_RecoveryWork".Row, StepNo := #StepNo,
        StepName := 'test.recovery', AwaitingLabel := 'test.recovery.command', AwaitsPath := #Target.Status.Name,
        TimeClass := @E_TimeClass.WORK@, ExpectedTime := T#0ms);
    CASE #StepNo OF
        0:
            "GDB_RecoveryTest".EntryCount := "GDB_RecoveryTest".EntryCount + 1;
            "FRK_SeqSelect"(Seq := #Seq, AdvanceOk := TRUE, Jump1Ok := FALSE);
        42:
            #EventNow := "FRK_SeqOnce"(Seq := #Seq, Enable := TRUE, Token := 42);
            IF #EventNow THEN "GDB_RecoveryTest".EventCount := "GDB_RecoveryTest".EventCount + 1; END_IF;
            "GDB_RecoveryWork".Ready := "FRK_SeqCommand"(Seq := #Seq, Lease := "GDB_RecoveryWork".Lease,
                Execute := #Target.Execute, Command := #Target.Command, Value := 3, Label := 'RECOVERY',
                TargetIndex := #Target.Core.RegIndex, OwnFailure := FALSE);
            IF #Seq.CommandIssued THEN "GDB_RecoveryTest".IssueCount := "GDB_RecoveryTest".IssueCount + 1; END_IF;
            #EventNow := "FRK_SeqDelay"(Seq := #Seq, Permit := TRUE, PT := T#1h, Delta := T#1ms);
            IF "GDB_RecoveryWork".Fault THEN
                "FRK_Fault"(Core := #Core, Status := #Status, ReasonCode := 10041,
                    Description := WSTRING#'test.recovery.fault');
                "FRK_SeqOwnerStatus"(Seq := #Seq, Core := #Core, Status := #Status);
            END_IF;
            "FRK_SeqSelect"(Seq := #Seq, AdvanceOk := "GDB_RecoveryWork".Ready, Jump1Ok := FALSE);
        99:
            "FRK_SeqSelect"(Seq := #Seq, AdvanceOk := FALSE, Jump1Ok := FALSE);
    END_CASE;
END_FUNCTION
'''
    (out / '26_RecoveryActions.scl').write_bytes(bind(source, Catalog.read()).encode('ascii'))
    snapshot = '\n'.join('        "GDB_RecoveryWork".'+n+' := "GDB_RecoveryTest".'+n+';' for n, _ in args[:-1])
    owner = '''FUNCTION "F_TestRecovery" : Void
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
VAR_INPUT Owner : DInt; END_VAR
VAR_IN_OUT Target : "FB_DeclarationCylinder"; Core : "FRK_Core"; Status : "ST_ModuleStatus"; END_VAR
BEGIN
    IF #Owner <> 1 THEN RETURN; END_IF;
    IF "GDB_RecoveryTest".RequestSeq <> "GDB_RecoveryTest".AckSeq THEN
@SNAPSHOT@
        "GDB_RecoveryTest".AckSeq := "GDB_RecoveryTest".RequestSeq;
    END_IF;
    "FRK_SeqGraphBegin"(Run := #Core.Exec = @E_ExecState.BUSY@ AND "GDB_RecoveryWork".Enabled,
        Reset := #Core.EvCommandStart AND "GDB_RecoveryWork".RestartOnStart,
        OwnerIndex := #Owner, ChainIndex := 10, BranchIndex := 0, ViewOffset := 0, ViewDepth := 0,
        Delta := T#1ms, Seq := "GDB_RecoveryWork".Seq);
    "FRK_SeqLease"(Seq := "GDB_RecoveryWork".Seq, Lease := "GDB_RecoveryWork".Lease,
        Execute := #Target.Execute, Abort := #Target.Abort, TargetIndex := #Target.Core.RegIndex);
    IF NOT "GDB_RecoveryWork".Seq.Frozen OR "GDB_RecoveryWork".Seq.RestartPending THEN
        "GDB_GRAPH_RecoveryTest"(Seq := "GDB_RecoveryWork".Seq, Target := #Target, Core := #Core, Status := #Status,
            INIT_SQ := "GDB_RecoveryWork".Seq.Restart AND "GDB_RecoveryWork".Seq.Running, OFF_SQ := NOT "GDB_RecoveryWork".Seq.Running);
    END_IF;
    "FRK_SeqOwnerStatus"(Seq := "GDB_RecoveryWork".Seq, Core := #Core, Status := #Status);
    "FRK_SeqLease"(Seq := "GDB_RecoveryWork".Seq, Lease := "GDB_RecoveryWork".Lease,
        Execute := #Target.Execute, Abort := #Target.Abort, TargetIndex := #Target.Core.RegIndex);
    IF NOT #Target.Execute THEN "GDB_RecoveryTest".LowScans := "GDB_RecoveryTest".LowScans + 1; END_IF;
    "GDB_RecoveryTest".Seq := "GDB_RecoveryWork".Seq;
    "GDB_RecoveryTest".Running := "GDB_RecoveryWork".Seq.Running;
    "GDB_RecoveryTest".Delay := "GDB_RecoveryWork".Seq.DelayElapsed;
    "GDB_RecoveryTest".Frozen := "GDB_RecoveryWork".Seq.Frozen;
    "GDB_RecoveryTest".ResumePending := "GDB_RecoveryWork".Seq.ResumePending;
    IF "GDB_RecoveryWork".LateTimeout AND #Core.Exec = @E_ExecState.BUSY@ THEN
        #Core.TimeoutMs := 1; #Core.ActiveMs := 1;
        "GDB_RecoveryWork".LateTimeout := FALSE;
    END_IF;
END_FUNCTION
'''.replace('@SNAPSHOT@', snapshot)
    (out / '28_RecoveryOwner.scl').write_bytes(bind(owner, Catalog.read()).encode('ascii'))
    for path in out.glob('20_*.scl'):
        text = path.read_text('ascii')
        anchor = '    "F_TestSequenceView"(Owner := #Core.RegIndex);'
        if anchor in text:
            assert text.count(anchor) == 1
            text = text.replace(anchor, anchor+'\n    "F_TestRecovery"(Owner := #Core.RegIndex, Target := #Cell.Clamp, Core := #Core, Status := #Status);')
            path.write_bytes(text.encode('ascii'))
    path = out / '38_ConfigBenchRoutines.scl'
    text = path.read_text('ascii')
    marker = 'FUNCTION "F_ConfigBenchObserve"'
    before, after = text.split(marker, 1)
    before = before.replace('END_FUNCTION', '''    "StationA".Abort := "GDB_RecoveryWork".AbortPLC;
    IF "GDB_RecoveryWork".Enabled THEN
        "GDB_FraktalHal".Data.StationA.Cell.Clamp.Permit := "GDB_RecoveryWork".Permit;
        "GDB_FraktalHal".Data.StationA.Cell.Clamp.Finish := "GDB_RecoveryWork".Finish;
    END_IF;
END_FUNCTION''')
    path.write_bytes((before+marker+after).encode('ascii'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('frames', type=Path)
    args = parser.parse_args()
    prepare(args.out, args.frames)
