"""Deterministic native profile cases and generated-Unit integration on LOAD_DB."""
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


def prepare(out, frames):
    spec = importlib.util.spec_from_file_location('diagnostic_fixture', HERE.parent / 'SequenceDiagnostics/make_fixture.py')
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    fixture.prepare(out, frames)
    checks, body = [], []
    work = '"GDB_ProfileWork".'
    args = 'Book := ' + work + 'Book, Steps := ' + work + 'Steps, Stats := ' + work + 'Stats'
    finish_args = args + ', LastSteps := ' + work + 'LastSteps, History := ' + work + 'History'

    def check(label, expression):
        checks.append(label)
        body.append('    "GDB_ProfileCases".Passed[%d] := %s;' % (len(checks), expression))

    def reset():
        body.extend(['    ' + work + 'Book := ' + work + 'EmptyBook;',
                     '    FOR #Index := 1 TO 4 DO',
                     '        ' + work + 'Steps[#Index] := "FRK_ProfileScratch".Step;',
                     '        ' + work + 'LastSteps[#Index] := "FRK_ProfileScratch".Step;',
                     '        ' + work + 'Stats[#Index] := ' + work + 'EmptyRow;',
                     '    END_FOR;',
                     '    FOR #Index := 1 TO 60 DO ' + work + 'History[#Index] := "FRK_ProfileScratch".Summary; END_FOR;',
                     '    "FRK_ProfilePrepare"(Run := TRUE, Withdraw := FALSE, Book := ' + work + 'Book);'])

    def step(number, visit, now, time_class=0, expected=0, name='test.profile'):
        body.append('    "FRK_ProfileStep"(StepNo := %s, Visit := %s, StepName := \'%s\', TimeClass := %s, Expected := T#%sms, NowMs := UDINT#%s, Stamp := LDT#2026-10-14-12:00:00.123456789, %s);' % (number, visit, name, time_class, expected, now, args))

    def complete(now):
        body.append('    "FRK_ProfileComplete"(NowMs := UDINT#%s, %s);' % (now, finish_args))

    reset()
    step(10, 1, 100, expected=20, name='x' * 120)
    step(10, 1, 105, expected=30)
    step(20, 1, 120, time_class=1, expected=40)
    complete(150)
    for label, expr in [
        ('one completed cycle', 'Book.Last.CycleNo = 1'),
        ('total monotonic duration', 'Book.Last.Total = T#50ms'),
        ('work split', 'Book.Last.WorkTime = T#20ms'),
        ('wait split', 'Book.Last.WaitTime = T#30ms'),
        ('same visit does not reopen', 'Book.LastNSteps = 2'),
        ('first duration preserved', 'LastSteps[1].Duration = T#20ms'),
        ('full step label', "LastSteps[1].StepName = '" + 'x' * 120 + "'"),
        ('refreshed guard', 'LastSteps[1].Expected = T#30ms'),
        ('terminal duration included', 'LastSteps[2].Duration = T#30ms'),
        ('timestamp precision', 'LastSteps[1].Started = LDT#2026-10-14-12:00:00.123456789'),
        ('step UTC quality remains unclaimed', 'NOT LastSteps[1].StartedTimeSynchronized'),
        ('cycle UTC quality remains unclaimed', 'NOT Book.Last.StartedTimeSynchronized'),
        ('first history head', 'Book.Head = 1'),
        ('first rolling minimum', 'Book.MinCycleTime = T#50ms'),
    ]:
        check(label, 'NOT ' + work + expr[4:] if expr.startswith('NOT ') else work + expr)
    complete(170)
    step(20, 1, 180)
    complete(200)
    check('terminal visit cannot complete twice', work + 'Book.Last.CycleNo = 1')
    step(10, 2, 200)
    complete(210)
    check('fresh visit starts another cycle', work + 'Book.Last.CycleNo = 2')
    check('step statistics count', work + 'Stats[1].Count = 2')
    check('step statistics integer mean', work + 'Stats[1].Avg = T#15ms')
    check('step statistics minimum', work + 'Stats[1].Minimum = T#10ms')
    check('step statistics maximum', work + 'Stats[1].Maximum = T#20ms')
    check('cycle minimum updates', work + 'Book.MinCycleTime = T#10ms')
    step(10, 3, 220)
    complete(220)
    step(10, 4, 230)
    complete(240)
    check('zero duration best survives later cycles', work + 'Book.MinCycleTime = T#0ms')

    reset()
    step(10, 1, 4294967290)
    complete(10)
    check('UDINT clock rollover duration', work + 'Book.Last.Total = T#16ms')
    check('UDINT clock rollover step duration', work + 'LastSteps[1].Duration = T#16ms')

    reset()
    step(10, 1, 0)
    complete(2147483648)
    check('TIME saturation remains positive', work + 'Book.Last.Total = T#2147483647ms')
    check('TIME saturation signals truncation', work + 'Book.LastTruncated')
    check('TIME saturation row', work + 'LastSteps[1].Duration = T#2147483647ms')

    reset()
    for number in range(1, 7):
        step(number, 1, number * 10, time_class=(number - 1) % 5)
    complete(70)
    check('waterfall remains bounded', work + 'Book.LastNSteps = 4')
    check('waterfall overflow visible', work + 'Book.LastTruncated')
    check('stat pool overflow visible', work + 'Book.StatsTruncated')
    check('overflow keeps total', work + 'Book.Last.Total = T#60ms')
    check('overflow keeps work split', work + 'Book.Last.WorkTime = T#20ms')
    for number in range(5):
        check('time class %d accumulated' % number,
              work + 'Book.Last.ByClass[%d] = T#%dms' % (number, 20 if number == 0 else 10))

    reset()
    for number, cls, expected in ((-1, 0, 0), (40000, 0, 0), (10, 5, 0), (10, 0, -1)):
        step(number, 1, 10, time_class=cls, expected=expected)
    check('invalid inputs do not start a cycle', 'NOT ' + work + 'Book.Running')
    check('invalid inputs are visible', work + 'Book.StatsTruncated')
    step(10, 1, 20)
    step(20, 1, 25, time_class=-1)
    complete(30)
    check('invalid active cycle is not published', work + 'Book.Last.CycleNo = 0')
    check('invalid active cycle does not enter history', work + 'Book.Head = 0')

    reset()
    step(10, 1, 10)
    complete(20)
    step(20, 1, 30)
    body.append('    "FRK_ProfilePrepare"(Run := FALSE, Withdraw := TRUE, Book := ' + work + 'Book);')
    complete(50)
    check('withdraw abandons open timing', 'NOT ' + work + 'Book.HasOpen')
    check('withdraw preserves previous complete cycle', work + 'Book.Last.CycleNo = 1')
    check('withdraw preserves previous history', work + 'History[1].Total = T#10ms')
    step(30, 1, 60)
    check('inactive collector ignores steps', 'NOT ' + work + 'Book.Running')

    reset()
    body.append('    FOR #Index := 1 TO 65 DO')
    step(10, 'INT_TO_UDINT(#Index)', 0)
    complete(1)
    body.append('    END_FOR;')
    check('cycle ring head wraps', work + 'Book.Head = 5')
    check('cycle ring newest entry', work + 'History[5].CycleNo = 65')
    check('cycle ring oldest retained entry', work + 'History[6].CycleNo = 6')
    body.append('    ' + work + 'Book.Last.CycleNo := UDINT#4294967295;')
    step(20, 66, 2)
    complete(3)
    check('cycle counter saturates', work + 'Book.Last.CycleNo = UDINT#4294967295')

    reset()
    step(10, 1, 0)
    body.append('    "FRK_ProfileRequest"(Book := ' + work + 'Book);')
    body.append('    "FRK_ProfileEnd"(StepNo := 10, Expected := T#700ms, NowMs := 20, ' + finish_args + ');')
    check('finish uses frame-resolved guard', work + 'LastSteps[1].Expected = T#700ms')
    check('finish request consumed once', 'NOT ' + work + 'Book.CompleteRequested')

    body.append('    ' + work + 'Row := ' + work + 'EmptyRow;')
    for duration in (100, 300, 0):
        body.append('    "FRK_TimingUpdate"(DurationMs := %d, Row := %sRow);' % (duration, work))
    for label, expr in [('shared row count', 'Row.Count = 3'),
                        ('shared row minimum zero', 'Row.Minimum = T#0ms'),
                        ('shared row maximum', 'Row.Maximum = T#300ms'),
                        ('shared row incremental mean', 'Row.Avg = T#134ms')]:
        check(label, work + expr)
    body.append('    ' + work + 'Row.Count := UDINT#4294967295;')
    body.append('    "FRK_TimingUpdate"(DurationMs := UDINT#4294967295, Row := ' + work + 'Row);')
    check('shared row count saturation', work + 'Row.Count = UDINT#4294967295')
    check('shared row TIME saturation', work + 'Row.Last = T#2147483647ms')

    (out / '08_GDB_ProfileWork.db').write_bytes(db('GDB_ProfileWork', [
        'Book' + PRIVATE + ' : "FRK_ProfileBook";', 'EmptyBook' + PRIVATE + ' : "FRK_ProfileBook";',
        'Steps' + PRIVATE + ' : Array[1..4] of "ST_StepTiming";',
        'LastSteps' + PRIVATE + ' : Array[1..4] of "ST_StepTiming";',
        'Stats' + PRIVATE + ' : Array[1..4] of "ST_TimingRow";',
        'History' + PRIVATE + ' : Array[1..60] of "ST_CycleSummary";',
        'Row' + PRIVATE + ' : "ST_TimingRow";', 'EmptyRow' + PRIVATE + ' : "ST_TimingRow";',
    ]).encode('ascii'))
    (out / '08_GDB_ProfileCases.db').write_bytes(db('GDB_ProfileCases', [
        'Complete' + READONLY + ' : Bool;', 'Count' + READONLY + ' : Int;',
        'Passed' + READONLY + ' : Array[1..%d] of Bool;' % len(checks),
    ]).encode('ascii'))
    source = '''FUNCTION "F_TestProfileCases" : Void
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
VAR_TEMP Index : Int; END_VAR
BEGIN
    IF "GDB_ProfileCases".Complete THEN RETURN; END_IF;
''' + '\n'.join(body) + '\n    "GDB_ProfileCases".Count := %d;\n    "GDB_ProfileCases".Complete := TRUE;\nEND_FUNCTION\n' % len(checks)
    (out / '39j_ProfileCases.scl').write_bytes(source.encode('ascii'))

    controls = ['Owner : DInt;', 'Enabled : Bool;', 'StepNo : DInt;', 'Branch : DInt;',
                'TimeClass : DInt;', 'Expected : Time;', 'Finish : Bool;', 'ForceLateTimeout : Bool;', 'RequestSeq : UDInt;',
                'AckSeq' + READONLY + ' : UDInt;']
    (out / '08_GDB_ProfileIntegration.db').write_bytes(db('GDB_ProfileIntegration', controls).encode('ascii'))
    # Snapshot test arguments on the final request sequence, just like the real
    # mailbox. Bulk network writes can span PLC scans; activation must be last.
    c = '"GDB_ProfileIntegration".'
    w = '"GDB_ProfileIntegrationWork".'
    (out / '08_GDB_ProfileIntegrationWork.db').write_bytes(db('GDB_ProfileIntegrationWork', [
        n + PRIVATE + ' : ' + ty + ';' for n, ty in [('Owner', 'DInt'), ('Enabled', 'Bool'),
            ('StepNo', 'DInt'), ('Branch', 'DInt'), ('TimeClass', 'DInt'), ('Expected', 'Time'),
            ('Finish', 'Bool'), ('ForceLateTimeout', 'Bool'), ('ResetPulse', 'Bool'), ('Seq', '"FRK_SequenceCtx"'), ('Row', '"FRK_SequenceRow"')]
    ]).encode('ascii'))
    snapshot = '\n'.join('        ' + w + n + ' := ' + c + n + ';' for n in
                         ('Owner', 'Enabled', 'StepNo', 'Branch', 'TimeClass', 'Expected', 'Finish', 'ForceLateTimeout'))
    integration = '''FUNCTION "F_TestProfileIntegration" : Void
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
VAR_INPUT Owner : DInt; Run : Bool; END_VAR
VAR_IN_OUT Core : "FRK_Core"; END_VAR
BEGIN
    IF #Owner = 1 AND %sRequestSeq <> %sAckSeq THEN
%s
        %sResetPulse := NOT %sSeq.Running;
        %sAckSeq := %sRequestSeq;
    END_IF;
    IF #Owner <> %sOwner THEN RETURN; END_IF;
    "FRK_SeqBegin"(Run := #Run AND %sEnabled, Reset := %sResetPulse, OwnerIndex := #Owner,
        ChainIndex := 9, BranchIndex := %sBranch, ViewOffset := 0, ViewDepth := 0,
        Delta := T#1ms, Seq := %sSeq);
    %sResetPulse := FALSE;
    IF NOT %sSeq.Running THEN RETURN; END_IF;
    %sSeq.Step := %sStepNo;
    "FRK_SeqStep"(Steppable := TRUE, StepNo := %sStepNo, StepName := 'test.profile.integration', AwaitingLabel := '',
        AwaitsPath := '', TimeClass := %sTimeClass, ExpectedTime := %sExpected, Seq := %sSeq, Row := %sRow);
    IF %sFinish THEN "FRK_SeqCycleEnd"(Seq := %sSeq); %sFinish := FALSE; END_IF;
    IF "GDB_ProfileIntegrationWork".ForceLateTimeout THEN
        // Test-only injection: the shared kernel resolves this AFTER sequence
        // policy. A queued cycle finish must not publish that failed cycle.
        #Core.TimeoutMs := 1; #Core.ActiveMs := 1;
        "GDB_ProfileIntegrationWork".ForceLateTimeout := FALSE;
    END_IF;
END_FUNCTION
''' % (c, c, snapshot, w, w, c, c, w, w, w, w, w, w, w, w, w, w, w, w, w, w, w, w, w)
    (out / '39k_ProfileIntegration.scl').write_bytes(integration.encode('ascii'))
    for path in out.glob('20_*.scl'):
        text = path.read_text('ascii')
        anchor = '    "F_TestSequenceView"(Owner := #Core.RegIndex);'
        if anchor in text:
            assert text.count(anchor) == 1
            text = text.replace(anchor, anchor + '\n    "F_TestProfileIntegration"(Owner := #Core.RegIndex, Run := #Core.Exec = @E_ExecState.BUSY@, Core := #Core);')
            path.write_bytes(bind(text, Catalog.read()).encode('ascii'))
    path = out / '38_ConfigBenchRoutines.scl'
    text = path.read_text('ascii')
    marker = 'FUNCTION "F_ConfigBenchObserve"'
    before, after = text.split(marker, 1)
    assert after.count('END_FUNCTION') == 1
    after = after.replace('END_FUNCTION', '    "F_TestProfileCases"();\nEND_FUNCTION')
    path.write_bytes((before + marker + after).encode('ascii'))
    (out.parent / 'profile_cases.json').write_text(json.dumps(checks, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'native_profile_cases': len(checks)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('frames', type=Path)
    args = parser.parse_args()
    prepare(args.out, args.frames)
