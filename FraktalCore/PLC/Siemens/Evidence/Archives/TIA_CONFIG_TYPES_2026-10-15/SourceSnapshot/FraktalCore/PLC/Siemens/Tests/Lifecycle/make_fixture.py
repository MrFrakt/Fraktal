"""Deterministic PLC-side tests of the shared kernel through generated frames."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN
import fraktal_tia_runtime as RUNTIME
from fraktal_tia_binding import PRIVATE


def declaration():
    value = json.loads((HERE.parent / 'Declaration/two_root_forest.json').read_text())
    value['records']['ST_DeclarationParCfg'] = 'STRUCT SchemaVersion : UINT := 2; Timeout : TIME := T#100ms; END_STRUCT'
    value['records']['ST_DeclarationOutImm'] = '''STRUCT
Sample : DINT; InitCount : DINT; StartCount : DINT; CyclicCount : DINT;
AbortCount : DINT; ErrorAbortCount : DINT; DispatchCount : DINT;
SeenValue : DINT; Ordered : BOOL; Output : BOOL; END_STRUCT'''
    value['records']['ST_DeclarationLeafHal'] = '''STRUCT
Sample : DINT; Permit : BOOL := TRUE; Finish : BOOL; BackgroundFault : BOOL;
Diag : ST_Diagnostic; LaterDiag : ST_Diagnostic; END_STRUCT'''
    for t in value['types']:
        t['commands'] = [{'id': i, 'label': label} for i, label in enumerate(
            ('Finish', 'Wait', 'Hold', 'Fault', 'Pending', 'Instant', 'Adopt'), 1)]
        t['timeout'] = 'Timeout'
        t['logic'] = {'Init': '    #OutImm.InitCount := #OutImm.InitCount + 1;',
                      'CommandStart': '    #OutImm.StartCount := #OutImm.StartCount + 1;\n    #OutImm.Ordered := #OutImm.InitCount = 1;',
                      'cyclic': '    #OutImm.Sample := #OutImm.Sample + 1;'}
    cm = value['types'][2]
    cm['logic'].update({
        'Cyclic': '''    #OutImm.CyclicCount := #OutImm.CyclicCount + 1;
    IF #Hal.BackgroundFault THEN
        "FRK_Fault"(Core := #Core, Status := #Status, ReasonCode := 2901, Description := WSTRING#'test.background');
    END_IF;''',
        'Abort': '    #OutImm.AbortCount := #OutImm.AbortCount + 1;',
        'AbortInError': '    #OutImm.ErrorAbortCount := #OutImm.ErrorAbortCount + 1;',
        'dispatch': '''    #OutImm.DispatchCount := #OutImm.DispatchCount + 1;
    #OutImm.SeenValue := #LatchedParCmd.Value;
    CASE #Core.Command OF
        1: IF #Hal.Finish THEN
               #OutCmd.Result := #LatchedParCmd.Value;
               "FRK_Complete"(Core := #Core, Status := #Status);
           END_IF;
        2: #OutImm.SeenValue := #LatchedParCmd.Value;
        3: IF NOT #Hal.Permit THEN
               "FRK_Hold"(Core := #Core, Status := #Status, ReasonCode := 2003, Description := WSTRING#'test.permit');
           ELSIF #Hal.Finish THEN
               "FRK_Complete"(Core := #Core, Status := #Status);
           END_IF;
        4: "FRK_Fault"(Core := #Core, Status := #Status, ReasonCode := 2901, Description := WSTRING#'test.first');
           "FRK_Fault"(Core := #Core, Status := #Status, ReasonCode := 2001, Description := WSTRING#'test.second');
        5: "FRK_Pending"(Core := #Core, Status := #Status, Diag := #Hal.Diag);
           "FRK_Pending"(Core := #Core, Status := #Status, Diag := #Hal.LaterDiag);
        6: "FRK_Complete"(Core := #Core, Status := #Status);
        7: "FRK_AdoptFault"(Core := #Core, Status := #Status, Diag := #Hal.Diag);
        ELSE "FRK_Fault"(Core := #Core, Status := #Status, ReasonCode := 2008, Description := WSTRING#'std.error.unsupportedHmiRequest');
    END_CASE;''',
        'cyclic': '''    #OutImm.Sample := #Hal.Sample;
    #OutImm.Output := #Core.Exec = 1 AND NOT #Core.Held AND #Hal.Permit;'''
    })
    for t in value['types']:
        t['storage'] = 'ST_DeclarationOutImm'
        t['logic'] = {name: body.replace('#OutImm', '#Device') for name, body in t['logic'].items()}
        t['logic']['cyclic'] += '\n    #OutImm := #Device;'
    return value


def prepare(out, frames):
    value = declaration()
    manifest = GEN.generate(DECL.validate(value), frames, shared_runtime=True)
    runtime = manifest['runtime']
    sources = {p.name: p.read_bytes() for p in frames.iterdir() if p.suffix in ('.scl', '.udt', '.db')}
    cm = '"StationA".Cell.Clamp'
    hal = '"GDB_FraktalHal".Data.StationA.Cell.Clamp'
    checks, rows = [], []

    def row(now, writes=(), assertions=()):
        code = [f'        {len(rows)}:', *['            ' + s for s in writes],
                f'            "FRK_Clock".NowMs := UDINT#{now};',
                '            "StationA"(ParentIndex := 0, Startup := #Startup, Hal := "GDB_FraktalHal".Data.StationA);',
                '            "StationB"(ParentIndex := 0, Startup := #Startup, Hal := "GDB_FraktalHal".Data.StationB);']
        for expr in assertions:
            checks.append(expr)
            code.append('            "FRK_LifecycleAssert"(Passed := ' + expr + ', CaseId := "GDB_Lifecycle".CaseNo);')
        rows.append('\n'.join(code))

    def c(expr): return cm + '.' + expr
    def setc(member, expr): return c(member) + ' := ' + expr + ';'
    def seth(member, expr): return hal + '.' + member + ' := ' + expr + ';'
    idle = [c('Status.State = 0'), 'NOT ' + c('Busy'), 'NOT ' + c('Done'), 'NOT ' + c('Error'), 'NOT ' + c('Aborted'), 'NOT ' + c('Held'), c('ErrorID = DWORD#0')]
    row(0, assertions=idle + [c('OutImm.InitCount = 1'), c('OutImm.CyclicCount = 1'), '"FRK_Registry".Count = 8'])
    row(10, [setc('Command','1'),setc('ParCmd.Value','42'),setc('Execute','TRUE')],
        [c('Busy'), c('OutImm.StartCount = 1'), c('OutImm.Ordered'), c('OutImm.SeenValue = 42')])
    row(20, [setc('ParCmd.Value','99'),setc('Command','4')], [c('Busy'), c('OutImm.SeenValue = 42'),c('Core.Command = 1')])
    row(30, [seth('Finish','TRUE')], [c('Done'), 'NOT '+c('Busy'), c('OutCmd.Result = 42'),c('Timing.LastCmdTime = T#20ms'),c('Timing.Rows[1].Count = 1')])
    row(40, assertions=[c('Done'),c('OutImm.StartCount = 1'),c('Timing.Rows[1].Count = 1')])
    row(50, [setc('Execute','FALSE'),seth('Finish','FALSE')], idle+[c('OutCmd.Result = 42')])
    row(60, [setc('Command','1'),setc('Execute','TRUE')], [c('Busy'),c('OutImm.StartCount = 2')])
    row(70, [setc('Execute','FALSE')], [c('Busy')])
    row(80, [seth('Finish','TRUE')], [c('Done'),c('Timing.Rows[1].Count = 2')])
    row(90, [seth('Finish','FALSE')], idle)
    row(100, [setc('Execute','TRUE'),setc('Command','6')], [c('Done'),c('Timing.LastCmdTime = T#0ms')])
    row(110, [setc('Execute','FALSE')], idle)
    row(120, [setc('Command','2'),setc('Execute','TRUE'),setc('Abort','TRUE')],
        [c('Aborted'),c('OutImm.AbortCount = 1'),c('OutImm.DispatchCount = 7'), 'NOT '+c('OutImm.Output')])
    row(130, assertions=[c('Aborted'),c('OutImm.AbortCount = 1')])
    row(140, [setc('Execute','FALSE')], idle)
    row(150, [setc('Execute','TRUE')], [c('Aborted'),c('OutImm.AbortCount = 2')])
    row(160, [setc('Execute','FALSE'),setc('Abort','FALSE')], idle)
    row(170, [setc('Execute','TRUE'),setc('Command','4')],
        [c('Error'),c('ErrorID = DWORD#2901'),c("Status.Diagnostic.Description = WSTRING#'test.first'"),c('Status.FaultActive')])
    row(180, [setc('Abort','TRUE')], [c('Error'),c('OutImm.ErrorAbortCount = 1'),c('ErrorID = DWORD#2901')])
    row(190, assertions=[c('Error'),c('OutImm.ErrorAbortCount = 1')])
    row(200, [setc('Abort','FALSE')], [c('Error')])
    row(210, [setc('Abort','TRUE')], [c('Error'),c('OutImm.ErrorAbortCount = 2')])
    row(220, [setc('Abort','FALSE'),setc('Execute','FALSE')], idle)
    row(230, [setc('Command','3'),setc('Execute','TRUE'),seth('Permit','FALSE')],
        [c('Busy'),c('Held'),'NOT '+c('Error'),c('Status.Diagnostic.Severity = 0'),'NOT '+c('OutImm.Output'),c('Core.ActiveMs = 0')])
    rows[-1] += '\n            "GDB_Lifecycle".HoldSince := '+c('Status.Diagnostic.Since')+';'
    row(1230, assertions=[c('Busy'),c('Held'),'NOT '+c('Error'),c('Core.ActiveMs = 0'),
                         c('Status.Diagnostic.Since = "GDB_Lifecycle".HoldSince'),
                         'NOT '+c('Status.Diagnostic.TimeSynchronized')])
    row(2230, [seth('Permit','TRUE')], [c('Busy'),'NOT '+c('Held'),c('Status.Diagnostic.ReasonCode = 0'),c('OutImm.Output')])
    row(2240, [seth('Finish','TRUE')], [c('Done'),'NOT '+c('Held'),c('Timing.LastCmdTime = T#2010ms')])
    row(2250, [setc('Execute','FALSE'),seth('Finish','FALSE')], idle)
    row(2260, [setc('Command','2'),setc('Execute','TRUE')], [c('Busy')])
    row(2359, assertions=[c('Busy'),c('Core.ActiveMs = 99')])
    row(2360, assertions=[c('Error'),c('ErrorID = DWORD#2001'),c('Status.Diagnostic.Severity = 1'),c('Timing.LastCmdTime = T#100ms')])
    row(2370, [setc('Execute','FALSE')], idle)
    diag_writes=[seth('Diag.ReasonCode','2002'),seth('Diag.SourcePath',"WSTRING#'Test.Child.Permit'"),
                 seth('Diag.Description',"WSTRING#'test.pending.first'"),seth('Diag.Since','LDT#2026-10-10-12:00:00.123456789'),
                 seth('Diag.TimeSynchronized','TRUE'),seth('Diag.IoTag',"'Input42'"),seth('Diag.IoAddress',"'%I42.0'"),
                 seth('LaterDiag.ReasonCode','2001'),seth('LaterDiag.SourcePath',"WSTRING#'Test.Second'")]
    row(2380, [setc('Command','5'),setc('Execute','TRUE'),*diag_writes], [c('Busy'),c('Status.Diagnostic.ReasonCode = 2002')])
    row(2480, assertions=[c('Error'),c('ErrorID = DWORD#2002'),c("Status.Diagnostic.SourcePath = WSTRING#'Test.Child.Permit'"),
                          c('Status.Diagnostic.Since = LDT#2026-10-10-12:00:00.123456789'),c('Status.Diagnostic.TimeSynchronized'),
                          c("Status.Diagnostic.IoTag = 'Input42'"),c('Status.Diagnostic.Severity = 0')])
    row(2490, [setc('Execute','FALSE')], idle)
    row(2491, [setc('Execute','TRUE'),seth('Diag.ReasonCode','10042')], [c('Busy')])
    row(2591, assertions=[c('Error'),c('ErrorID = DWORD#10042'),c('Status.Diagnostic.Severity = 1')])
    row(2592, [setc('Execute','FALSE'),seth('Diag.ReasonCode','2002')], idle)
    row(2500, [setc('Command','7'),setc('Execute','TRUE'),seth('Diag.Severity','2'),seth('Diag.Category','1')],
        [c('Error'),c('Status.Diagnostic.Severity = 2'),c('Status.Diagnostic.Category = 1'),c('ErrorID = DWORD#2002')])
    row(2510, [setc('Execute','FALSE')], idle)
    row(2520, [setc('Command','99'),setc('Execute','TRUE')], [c('Error'),c('ErrorID = DWORD#2008')])
    row(2530, [setc('Execute','FALSE')], idle)
    row(2540, [setc('Command','1'),setc('ParCfg.Timeout','T#0ms'),setc('Execute','TRUE')], [c('Error'),c('ErrorID = DWORD#2004')])
    row(2550, [setc('Execute','FALSE'),setc('ParCfg.Timeout','T#100ms')], idle)
    row(2560, [seth('BackgroundFault','TRUE')], [c('Error'),'NOT '+c('Core.Armed'),c('ErrorID = DWORD#2901')])
    row(2570, [seth('BackgroundFault','FALSE')], [c('Error'),c('ErrorID = DWORD#2901')])
    row(2580, [setc('Command','2'),setc('Execute','TRUE')], [c('Busy'),c('ErrorID = DWORD#0')])
    row(2590, [setc('Abort','TRUE')], [c('Aborted')])
    row(2600, [setc('Abort','FALSE'),setc('Execute','FALSE')], idle)
    row(2610, [setc('Command','3'),setc('Execute','TRUE'),seth('Permit','FALSE')], [c('Busy'),c('Held')])
    row(2620, [setc('Abort','TRUE')], [c('Aborted'),'NOT '+c('Held'),'NOT '+c('OutImm.Output'),c('OutImm.AbortCount = 4')])
    row(2630, [setc('Execute','FALSE'),setc('Abort','FALSE'),seth('Permit','TRUE')], idle)
    row(4294967290, [setc('Command','1'),setc('Execute','TRUE')], [c('Busy')])
    row(4, [seth('Finish','TRUE')], [c('Done'),c('Timing.LastCmdTime = T#10ms')])
    row(14, [setc('Execute','FALSE'),seth('Finish','FALSE')], idle+
        [c('OutImm.InitCount = 1'), c('OutImm.CyclicCount = %d' % (len(rows)+1)),
         c('Timing.Rows[1].Count = 4'),c('Timing.Rows[1].Minimum = T#0ms'),
         c('Timing.Rows[1].Maximum = T#20ms'),c('Timing.Rows[1].Avg = T#13ms'),
         c("Timing.Rows[1].Label = 'Finish'"),
         '"FRK_Registry".Rows[3].Exec = 0','"FRK_Registry".Rows[3].ReasonCode = 0'])
    body='\n'.join(['FUNCTION "FRK_LifecycleCases" : Void', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1',
        'VAR_TEMP', '    Startup : Bool;', 'END_VAR', 'BEGIN',
        '    #Startup := "GDB_Lifecycle".CaseNo = 0;',
        '    IF #Startup THEN "FRK_Registry".Count := 0; "FRK_Registry".Fault := FALSE; END_IF;',
        '    CASE "GDB_Lifecycle".CaseNo OF', *rows,
        '        ELSE', '            IF "GDB_Lifecycle".CaseNo <> %d THEN "GDB_Lifecycle".Failed := "GDB_Lifecycle".Failed + 1; END_IF;' % len(rows), '    END_CASE;',
        '    IF "GDB_Lifecycle".CaseNo < %d THEN' % len(rows),
        '        "GDB_Lifecycle".CaseNo := "GDB_Lifecycle".CaseNo + 1;',
        '        "GDB_Lifecycle".Passed := "GDB_Lifecycle".CaseNo = %d AND "GDB_Lifecycle".Failed = 0;' % len(rows),
        '    ELSE', '        "GDB_FraktalMain"(Startup := FALSE);', '    END_IF;', 'END_FUNCTION',''])
    sources['38_Cases.scl']=body.encode('ascii')
    sources['05_GDB_Lifecycle.db']=GEN.db('GDB_Lifecycle', [
        'CaseNo : DInt;', 'Checks : DInt;', 'Failed : DInt;', 'FirstFailedCase : DInt;',
        'FirstFailedCheck : DInt;', 'Passed : Bool;', 'HoldSince'+PRIVATE+' : LDT;']).encode('ascii')
    sources['05_GDB_LifecycleDefaults.db']=GEN.db('GDB_LifecycleDefaults', [
        name+PRIVATE+' : "'+record+'";' for name,record in
        [('Core','FRK_Core'),('Diag','ST_Diagnostic'),('Cfg','ST_DeclarationParCfg'),
         ('Cmd','ST_DeclarationParCmd'),('Result','ST_DeclarationOutCmd'),('Live','ST_DeclarationOutImm')]]).encode('ascii')
    sources['15_Assert.scl']='\n'.join(['FUNCTION "FRK_LifecycleAssert" : Void', "{ S7_Optimized_Access := 'TRUE' }",'VERSION : 0.1',
        'VAR_INPUT','    Passed : Bool;','    CaseId : DInt;','END_VAR','BEGIN',
        '    "GDB_Lifecycle".Checks := "GDB_Lifecycle".Checks + 1;',
        '    IF NOT #Passed THEN', '        IF "GDB_Lifecycle".Failed = 0 THEN',
        '            "GDB_Lifecycle".FirstFailedCase := #CaseId;',
        '            "GDB_Lifecycle".FirstFailedCheck := "GDB_Lifecycle".Checks;', '        END_IF;',
        '        "GDB_Lifecycle".Failed := "GDB_Lifecycle".Failed + 1;', '    END_IF;', 'END_FUNCTION','']).encode('ascii')
    resets=[]
    for item in manifest['inventory']['instances']:
        parts=item['path'].split('.')
        path='"'+parts[0]+'"'+''.join('.'+p for p in parts[1:])
        for field,default in [('Core','Core'),('Status.Diagnostic','Diag'),('ParCfg','Cfg'),('ParCmd','Cmd'),('OutCmd','Result'),('OutImm','Live'),('Device','Live')]:
            resets.append('        '+path+'.'+field+' := "GDB_LifecycleDefaults".'+default+';')
        resets.extend('        '+path+'.'+field+' := FALSE;' for field in ('Execute','Abort'))
        resets.append('        '+path+'.Command := 0;')
    for root in ('StationA','StationB'):
        for child in ('Clamp','Gate'):
            path='"GDB_FraktalHal".Data.'+root+'.Cell.'+child
            resets.extend('        '+path+'.'+field+' := '+v+';' for field,v in [('Permit','TRUE'),('Finish','FALSE'),('BackgroundFault','FALSE')])
    sources['40_Main.scl']='\n'.join(['ORGANIZATION_BLOCK "Main"', "{ S7_Optimized_Access := 'TRUE' }",'VERSION : 0.1',
        'VAR_INPUT','    Initial_Call : Bool;','    Remanence : Bool;','END_VAR','BEGIN',
        '    IF #Initial_Call THEN', '        "GDB_Lifecycle".CaseNo := 0;', '        "GDB_Lifecycle".Checks := 0;',
        '        "GDB_Lifecycle".Failed := 0;', '        "GDB_Lifecycle".Passed := FALSE;',
        '        "GDB_Lifecycle".FirstFailedCase := -1;', '        "GDB_Lifecycle".FirstFailedCheck := -1;',
        *resets, '    END_IF;',
        '    "FRK_LifecycleCases"();','END_ORGANIZATION_BLOCK','']).encode('ascii')
    out.mkdir(parents=True,exist_ok=False)
    for name,data in sources.items(): (out/name).write_bytes(data)
    proof={'cases':len(rows),'checks':len(checks),'assertions':checks,'runtime':runtime,
           'generated_frames':manifest['generated'], 'sources':{n:hashlib.sha256(d).hexdigest() for n,d in sources.items()},
           'clock':'Test case clock injection; production composition/clock resumes after cases.'}
    (out/'test_manifest.json').write_bytes((json.dumps(proof,indent=2)+'\n').encode('ascii'))
    print(json.dumps({'cases':len(rows),'checks':len(checks),'sources':len(sources)}))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);p.add_argument('frames',type=Path)
    a=p.parse_args();prepare(a.out,a.frames)
