"""Selected LOAD_DB/view bench with actual CM/EM commands and named waits."""
import argparse,importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent

def prepare(out,frames):
    spec=importlib.util.spec_from_file_location('combined',HERE.parent/'SequenceView/make_medium_fixture.py')
    combined=importlib.util.module_from_spec(spec);spec.loader.exec_module(combined)
    combined.prepare(out,frames)
    from fraktal_tia_generate import db
    from fraktal_tia_binding import READONLY,PRIVATE,Catalog
    from fraktal_tia_examples import bind
    controls=['Owner : DInt;', 'Enabled : Bool;', 'ResetPulse : Bool;', 'Scenario : Int;',
              'StepNo : DInt;', 'Branch : DInt;', 'Guard : Time;', 'Elapsed : Time;',
              'ConditionOne : Bool;', 'ConditionTwo : Bool;', 'CommandValue : DInt;',
              'Permit : Bool;', 'Finish : Bool;', 'Diagnostic : "ST_Diagnostic";', 'LaterDiagnostic : "ST_Diagnostic";',
              'InvalidTarget : DInt;', 'Seq'+READONLY+' : "FRK_SequenceCtx";',
              'Row'+READONLY+' : "FRK_SequenceRow";', 'Completed'+READONLY+' : Bool;',
              'LeaseOne'+PRIVATE+' : "ST_SequenceCommandLease";',
              'LeaseTwo'+PRIVATE+' : "ST_SequenceCommandLease";']
    (out/'08_GDB_SequenceDiagnosticTest.db').write_bytes(db('GDB_SequenceDiagnosticTest',controls).encode('ascii'))
    # Add test stimulus to the existing generated sequence path, without a Main
    # scheduling call. The direct view fixture remains available for regression.
    for p in out.glob('20_*.scl'):
        text=p.read_text('ascii');anchor='    "F_TestSequenceView"(Owner := #Core.RegIndex);'
        if anchor not in text:continue
        assert text.count(anchor)==1
        text=text.replace(anchor,anchor+'''\n    "F_TestSequenceDiagnostics"(Owner := #Core.RegIndex, Run := #Core.Exec = @E_ExecState.BUSY@,
        Target := #Cell.Clamp, Alternate := #Cell.Gate, Container := #Cell, AlarmLog := #AlarmLog);''')
        p.write_bytes(bind(text,Catalog.read()).encode('ascii'))
    source='''FUNCTION "F_TestSequenceDiagnostics" : Void
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
VAR_INPUT Owner : DInt; Run : Bool; END_VAR
VAR_IN_OUT Target : "FB_DeclarationCylinder"; Alternate : "FB_DeclarationCylinder";
    Container : "FB_DeclarationCell"; AlarmLog : "FRK_AlarmLog";
END_VAR
VAR_TEMP ReadyOne : Bool; ReadyTwo : Bool; TargetIndex : DInt; SelectedPath : String[80]; END_VAR
BEGIN
    IF #Owner <> "GDB_SequenceDiagnosticTest".Owner THEN RETURN; END_IF;
    "FRK_SeqBegin"(Run := #Run AND "GDB_SequenceDiagnosticTest".Enabled,
        Reset := "GDB_SequenceDiagnosticTest".ResetPulse, OwnerIndex := #Owner, ChainIndex := 8,
        BranchIndex := "GDB_SequenceDiagnosticTest".Branch, ViewOffset := 0, ViewDepth := 0,
        Delta := T#1ms, Seq := "GDB_SequenceDiagnosticTest".Seq);
    "GDB_SequenceDiagnosticTest".ResetPulse := FALSE;
    "FRK_SeqLease"(Seq := "GDB_SequenceDiagnosticTest".Seq, Lease := "GDB_SequenceDiagnosticTest".LeaseOne,
        Execute := #Target.Execute, Abort := #Target.Abort, TargetIndex := #Target.Core.RegIndex);
    "FRK_SeqLease"(Seq := "GDB_SequenceDiagnosticTest".Seq, Lease := "GDB_SequenceDiagnosticTest".LeaseTwo,
        Execute := #Alternate.Execute, Abort := #Alternate.Abort, TargetIndex := #Alternate.Core.RegIndex);
    IF NOT "GDB_SequenceDiagnosticTest".Seq.Running THEN RETURN; END_IF;
    "GDB_SequenceDiagnosticTest".Seq.Step := "GDB_SequenceDiagnosticTest".StepNo;
    "GDB_SequenceDiagnosticTest".Seq.Elapsed := "GDB_SequenceDiagnosticTest".Elapsed;
    #SelectedPath := #Target.Status.Name;
    IF "GDB_SequenceDiagnosticTest".Scenario = 2 THEN #SelectedPath := #Container.Status.Name; END_IF;
    "FRK_SeqStep"(StepNo := "GDB_SequenceDiagnosticTest".StepNo, StepName := 'test.diagnostic.step',
        AwaitingLabel := 'test.await', AwaitsPath := #SelectedPath, TimeClass := @E_TimeClass.WORK@,
        ExpectedTime := "GDB_SequenceDiagnosticTest".Guard, Seq := "GDB_SequenceDiagnosticTest".Seq,
        Row := "GDB_SequenceDiagnosticTest".Row);
    #ReadyOne := FALSE; #ReadyTwo := TRUE;
    CASE "GDB_SequenceDiagnosticTest".Scenario OF
        0:
            #ReadyOne := "FRK_SeqAwait"(Seq := "GDB_SequenceDiagnosticTest".Seq,
                Label := 'test.condition.first', Ok := "GDB_SequenceDiagnosticTest".ConditionOne);
            #ReadyTwo := "FRK_SeqAwait"(Seq := "GDB_SequenceDiagnosticTest".Seq,
                Label := 'test.condition.second', Ok := "GDB_SequenceDiagnosticTest".ConditionTwo);
        1, 3:
            #TargetIndex := #Target.Core.RegIndex;
            IF "GDB_SequenceDiagnosticTest".InvalidTarget <> 0 THEN #TargetIndex := "GDB_SequenceDiagnosticTest".InvalidTarget; END_IF;
            #ReadyOne := "FRK_SeqCommand"(Seq := "GDB_SequenceDiagnosticTest".Seq,
                Lease := "GDB_SequenceDiagnosticTest".LeaseOne, Execute := #Target.Execute,
                Command := #Target.Command, Value := "GDB_SequenceDiagnosticTest".CommandValue,
                Label := 'TEST', TargetIndex := #TargetIndex, OwnFailure := "GDB_SequenceDiagnosticTest".Scenario = 3);
            IF "GDB_SequenceDiagnosticTest".Scenario = 3 THEN
                "FRK_SeqHandled"(Seq := "GDB_SequenceDiagnosticTest".Seq, ChildCore := #Target.Core);
                IF "GDB_SequenceDiagnosticTest".Seq.CommandFailed THEN
                    "FRK_SeqMessage"(Seq := "GDB_SequenceDiagnosticTest".Seq,
                        Diag := "GDB_SequenceDiagnosticTest".Seq.HandledDiagnostic, AlarmLog := #AlarmLog);
                END_IF;
            END_IF;
        2:
            // The Unit awaits the EM, not this leaf. The test drives the leaf
            // command through the normal CM kernel to prove recursive rollup.
            #Container.Execute := TRUE; #Container.Command := 2;
            #Target.Execute := TRUE; #Target.Command := "GDB_SequenceDiagnosticTest".CommandValue;
            "FRK_SeqViewWatch"(Owner := #Owner, StepNo := "GDB_SequenceDiagnosticTest".Seq.RecordedStep,
                Branch := "GDB_SequenceDiagnosticTest".Branch, Target := #Container.Core.RegIndex,
                Waiting := TRUE, OwnFailure := FALSE);
            #ReadyOne := "FRK_SeqAwait"(Seq := "GDB_SequenceDiagnosticTest".Seq, Label := 'test.container', Ok := FALSE);
        4:
            #ReadyOne := "FRK_SeqCommand"(Seq := "GDB_SequenceDiagnosticTest".Seq,
                Lease := "GDB_SequenceDiagnosticTest".LeaseOne, Execute := #Target.Execute, Command := #Target.Command,
                Value := 2, Label := 'FIRST', TargetIndex := #Target.Core.RegIndex, OwnFailure := FALSE);
            #ReadyTwo := "FRK_SeqCommand"(Seq := "GDB_SequenceDiagnosticTest".Seq,
                Lease := "GDB_SequenceDiagnosticTest".LeaseTwo, Execute := #Alternate.Execute, Command := #Alternate.Command,
                Value := 2, Label := 'SECOND', TargetIndex := #Alternate.Core.RegIndex, OwnFailure := FALSE);
        ELSE
            "FRK_SeqViewFail"(Owner := #Owner, StepNo := "GDB_SequenceDiagnosticTest".Seq.RecordedStep,
                Branch := "GDB_SequenceDiagnosticTest".Branch, Diag := "FRK_UnitScratch".EmptyDiagnostic);
    END_CASE;
    "GDB_SequenceDiagnosticTest".Completed := #ReadyOne AND #ReadyTwo;
END_FUNCTION
'''
    (out/'39i_SequenceDiagnosticBench.scl').write_bytes(bind(source,Catalog.read()).encode('ascii'))
    p=out/'38_ConfigBenchRoutines.scl';text=p.read_text('ascii')
    marker='FUNCTION "F_ConfigBenchObserve"';before,after=text.split(marker,1)
    # Real command timeouts are deliberately long relative to network probes.
    # The declared step elapsed input is synthetic; native command clocks remain real.
    before=before.replace('END_FUNCTION','''    "StationA".Cell.Clamp.ParCfg.Timeout := T#30s;
    "StationA".Cell.Gate.ParCfg.Timeout := T#45s;
    IF "GDB_SequenceDiagnosticTest".Enabled THEN
        "GDB_FraktalHal".Data.StationA.Cell.Clamp.Diag := "GDB_SequenceDiagnosticTest".Diagnostic;
        "GDB_FraktalHal".Data.StationA.Cell.Clamp.LaterDiag := "GDB_SequenceDiagnosticTest".LaterDiagnostic;
        "GDB_FraktalHal".Data.StationA.Cell.Clamp.Permit := "GDB_SequenceDiagnosticTest".Permit;
        "GDB_FraktalHal".Data.StationA.Cell.Clamp.Finish := "GDB_SequenceDiagnosticTest".Finish;
    END_IF;
END_FUNCTION''')
    p.write_bytes((before+marker+after).encode('ascii'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);p.add_argument('frames',type=Path)
    a=p.parse_args();prepare(a.out,a.frames)
