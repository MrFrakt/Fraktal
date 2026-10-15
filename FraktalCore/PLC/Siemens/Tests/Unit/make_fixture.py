"""Generated two-root Unit control bench; native mailbox tests exercise this image."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'tools'))
import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN
spec=importlib.util.spec_from_file_location('lifecycle', HERE.parent/'Lifecycle/make_fixture.py')
LIFE=importlib.util.module_from_spec(spec);spec.loader.exec_module(LIFE)


def declaration():
    value=LIFE.declaration()
    value['records']['ST_DeclarationParCfg']='STRUCT SchemaVersion : UINT := 3; Timeout : TIME := T#2s; END_STRUCT'
    value['records']['ST_DeclarationLeafHal']=value['records']['ST_DeclarationLeafHal'].replace('END_STRUCT','ExitHold : BOOL; Verdict : DINT := 1; END_STRUCT')
    value['records']['ST_UnitProbeDevice']='STRUCT Cycles : UDINT; ExitCalls : UDINT; Changes : UDINT; Resets : UDINT; Received : BOOL; Processed : BOOL; END_STRUCT'
    value['records']['ST_UnitProbeImm']='STRUCT Cycles : UDINT; ExitCalls : UDINT; Changes : UDINT; Resets : UDINT; END_STRUCT'
    root=value['types'][0]
    root['unit']={'modes':['AUTO','MANUAL','HOME','CHANGEOVER'],'initial':'MANUAL','run_command':1}
    root['commands']=[{'id':1,'label':'Run'}]
    root['storage']='ST_UnitProbeDevice';root['contract']['OutImm']='ST_UnitProbeImm'
    root['logic']={
        'CommandStart':'''    #Device.Received := "FRK_PartReceived"(Core := #Core, Unit := #Unit, Status := #Status, Part := #Part, AlarmLog := #AlarmLog);
    IF #Device.Received THEN
        "FRK_PartStarted"(Unit := #Unit, Status := #Status, Part := #Part, AlarmLog := #AlarmLog);
    END_IF;''',
        'Release':'    "FRK_UnitSetPermit"(Unit := #Unit, Ok := #Hal.Cell.Clamp.Permit, Diag := #Hal.Cell.Clamp.Diag);',
        'Cyclic':'''    IF #Hal.Cell.Clamp.BackgroundFault THEN
        "FRK_Fault"(Core := #Core, Status := #Status, ReasonCode := 2901, Description := WSTRING#'test.unit.condition');
    END_IF;''',
        'ModeExit':'''    #Device.ExitCalls := #Device.ExitCalls + 1;
    IF #Hal.Cell.Clamp.ExitHold THEN #Core.HookResult := 1; ELSE #Core.HookResult := 0; END_IF;''',
        'ModeChanged':'    #Device.Changes := #Device.Changes + 1;',
        'OperatorReset':'    #Device.Resets := #Device.Resets + 1;',
        'dispatch':'''    IF #Hal.Cell.Clamp.Finish THEN
        #Device.Processed := FALSE;
        IF #Unit.CarrierIndex = 0 THEN
            #Device.Processed := TRUE;
        ELSE
            #Device.Processed := "FRK_PartProcessed"(Core := #Core, Unit := #Unit, Status := #Status, Part := #Part, AlarmLog := #AlarmLog, Verdict := #Hal.Cell.Clamp.Verdict, Reason := #Hal.Cell.Clamp.Diag.ReasonCode);
        END_IF;
        IF #Device.Processed THEN
            #Device.Cycles := #Device.Cycles + 1;
            IF #Unit.StopReq THEN
                "FRK_Complete"(Core := #Core, Status := #Status);
            ELSE
                #Device.Received := "FRK_PartReceived"(Core := #Core, Unit := #Unit, Status := #Status, Part := #Part, AlarmLog := #AlarmLog);
                IF #Device.Received THEN
                    "FRK_PartStarted"(Unit := #Unit, Status := #Status, Part := #Part, AlarmLog := #AlarmLog);
                END_IF;
            END_IF;
        END_IF;
    END_IF;''',
        'cyclic':'''    #OutImm.Cycles := #Device.Cycles;
    #OutImm.ExitCalls := #Device.ExitCalls;
    #OutImm.Changes := #Device.Changes;
    #OutImm.Resets := #Device.Resets;'''
    }
    return value


def prepare(out, value=None):
    model=DECL.validate(declaration() if value is None else value)
    manifest=GEN.generate(model,out,shared_runtime=True)
    print(json.dumps({'sources':len(manifest['generated']),'types':len(manifest['types']),'instances':len(model.instances)}))


def test_package(out, frames, value=None):
    prepare(frames, value)
    out.mkdir(parents=True,exist_ok=False)
    for path in frames.iterdir():
        if path.suffix in ('.scl','.udt','.db'):shutil.copyfile(path,out/path.name)
    from fraktal_tia_binding import READONLY
    (out/'05_GDB_UnitTest.db').write_bytes(GEN.db('GDB_UnitTest',[
        'FinishCycle : Bool;', 'Permit : Bool := TRUE;', 'FaultRoot : Bool;', 'ExitHold : Bool;',
        'LockStart : Bool;', 'IssueChild : Bool;', 'ChildCommand : DInt := 2;', 'Verdict : DInt := 1;', 'Reason : DInt := 2003;',
        'CarrierControl : DInt;',
        *[n+READONLY+' : '+kind+';' for n,kind in [('Scans','UDInt'),('Restarts','UDInt'),('ChildExecute','Bool'),
            ('ChildState','DInt'),('CarrierWrites','UDInt'),('CarrierSerial','UDInt'),('WrittenUid','String[64]'),
            ('WrittenVerdict','DInt'),('LastEvent','DInt'),('SecretCleared','Bool'),('SnapshotSecretCleared','Bool'),('BootStamp','LDT')]]
    ]).replace('Permit : Bool := TRUE;','Permit : Bool;').replace('ChildCommand : DInt := 2;','ChildCommand : DInt;').replace('Verdict : DInt := 1;','Verdict : DInt;').replace('Reason : DInt := 2003;','Reason : DInt;').encode('ascii'))
    main='''ORGANIZATION_BLOCK "Main"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
VAR_INPUT
    Initial_Call : Bool;
    Remanence : Bool;
END_VAR
VAR_TEMP
    StartupStamp : DTL;
    ResultCode : Int;
END_VAR
BEGIN
    IF #Initial_Call THEN
        #ResultCode := RD_SYS_T(OUT => #StartupStamp);
        IF #ResultCode = 0 THEN "GDB_UnitTest".BootStamp := DTL_TO_LDT(#StartupStamp); END_IF;
        "GDB_UnitTest".Restarts := "GDB_UnitTest".Restarts + 1;
        "GDB_UnitTest".FinishCycle := FALSE;
        "GDB_UnitTest".Permit := TRUE;
        "GDB_UnitTest".FaultRoot := FALSE;
        "GDB_UnitTest".ExitHold := FALSE;
        "GDB_UnitTest".IssueChild := FALSE;
        "GDB_UnitTest".LockStart := FALSE;
        "GDB_UnitTest".ChildCommand := 2;
        "GDB_UnitTest".Verdict := 1;
        "GDB_UnitTest".Reason := 2003;
        "GDB_UnitTest".CarrierControl := 0;
        "FRK_UnitSetLocalCarrier"(Unit := "StationA".Unit, Index := 1);
    END_IF;
    "GDB_FraktalHal".Data.StationA.Cell.Clamp.Finish := "GDB_UnitTest".FinishCycle;
    "GDB_FraktalHal".Data.StationA.Cell.Clamp.Permit := "GDB_UnitTest".Permit;
    "GDB_FraktalHal".Data.StationA.Cell.Clamp.ExitHold := "GDB_UnitTest".ExitHold;
    "GDB_FraktalHal".Data.StationA.Cell.Clamp.BackgroundFault := "GDB_UnitTest".FaultRoot;
    "GDB_FraktalHal".Data.StationA.Cell.Clamp.Verdict := "GDB_UnitTest".Verdict;
    "GDB_FraktalHal".Data.StationA.Cell.Clamp.Diag.ReasonCode := "GDB_UnitTest".Reason;
    "GDB_FraktalHal".Data.StationA.Cell.Clamp.Diag.Description := WSTRING#'test.start.permit';
    "GDB_FraktalHal".Data.StationA.Cell.Clamp.Diag.SourcePath := WSTRING#'StationA.Cell.Clamp';
    IF "GDB_UnitTest".IssueChild THEN
        "StationA".Cell.Clamp.Command := "GDB_UnitTest".ChildCommand;
        "StationA".Cell.Clamp.Execute := TRUE;
        "GDB_UnitTest".IssueChild := FALSE;
    END_IF;
    CASE "GDB_UnitTest".CarrierControl OF
        1: "FRK_UnitSetLocalCarrier"(Unit := "StationA".Unit, Index := 1);
        2: "FRK_Carriers".Slots[1].Enabled := FALSE;
        3: "FRK_Carriers".Slots[1].Context.Uid := 'other';
        ELSE "GDB_UnitTest".CarrierControl := 0;
    END_CASE;
    "GDB_UnitTest".CarrierControl := 0;
    IF "GDB_UnitTest".LockStart THEN "StationA".Access.Policy.Required[5] := 3; ELSE "StationA".Access.Policy.Required[5] := 0; END_IF;
    "GDB_FraktalMain"(Startup := #Initial_Call);
    "GDB_UnitTest".Scans := "GDB_UnitTest".Scans + 1;
    "GDB_UnitTest".ChildExecute := "StationA".Cell.Clamp.Execute;
    "GDB_UnitTest".ChildState := "StationA".Cell.Clamp.Core.Exec;
    "GDB_UnitTest".CarrierWrites := "FRK_Carriers".Slots[1].Writes;
    "GDB_UnitTest".CarrierSerial := "FRK_Carriers".Slots[1].Serial;
    "GDB_UnitTest".WrittenUid := "FRK_Carriers".Slots[1].Written.Uid;
    "GDB_UnitTest".WrittenVerdict := "FRK_Carriers".Slots[1].Written.Result.Verdict;
    IF "StationA".AlarmLog.RingHead > 0 AND "StationA".AlarmLog.RingHead <= @HISTORY@ THEN
        "GDB_UnitTest".LastEvent := "StationA".AlarmLog.Ring["StationA".AlarmLog.RingHead].ReasonCode;
    END_IF;
    "GDB_UnitTest".SecretCleared := "StationA".HmiRequest.Secret = '';
    "GDB_UnitTest".SnapshotSecretCleared := "StationA".Unit.Request.Secret = '';
END_ORGANIZATION_BLOCK
'''
    from fraktal_tia_binding import Catalog
    (out/'40_Main.scl').write_bytes(main.replace('@HISTORY@',str(Catalog.read().capacities['MAX_ALARM_RING'])).encode('ascii'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);p.add_argument('--test-frames',type=Path)
    a=p.parse_args()
    if a.test_frames:test_package(a.out,a.test_frames)
    else:prepare(a.out)
