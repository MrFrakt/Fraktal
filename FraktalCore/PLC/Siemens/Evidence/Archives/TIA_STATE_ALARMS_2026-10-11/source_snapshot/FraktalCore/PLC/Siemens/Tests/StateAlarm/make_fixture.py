"""State/event native bench; provider secrets stay in the existing DPAPI wrapper."""
import argparse
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('access_fixture',HERE.parent/'Access/make_fixture.py')
ACCESS=importlib.util.module_from_spec(spec);spec.loader.exec_module(ACCESS)


def declaration():
    value=ACCESS.MANIFEST.ROUTING.declaration()
    value['event_sink']='F_TestEventSink'
    value['records']['ST_UnitProbeImm']=value['records']['ST_UnitProbeImm'].replace('END_STRUCT','AtHome : BOOL; END_STRUCT')
    for t in value['types']:
        if 'unit' in t:
            t['logic']['cyclic']+='\n    #OutImm.AtHome := "FRK_State"(Idx := 1, Key := \'project.state.atHome\', Ok := #Hal.Cell.Clamp.Sample = 0);'
    return value


def prepare(out,frames):
    ACCESS.prepare(out,frames,declaration())
    import fraktal_tia_generate as GEN
    from fraktal_tia_binding import Catalog,READONLY,PRIVATE
    cap=Catalog.read().capacities['MAX_STATE_FLAGS']
    (out/'05_GDB_StateAlarmTest.db').write_bytes(GEN.db('GDB_StateAlarmTest',[
        *[n+' : Bool;' for n in ('ClearLog','RaisePulse','GonePulse','FillPulse','CauseLive','PublishState','StateValue')],
        'Position : DInt;', 'StateIndex : Int;', 'ResetClass : DInt;', 'FillCount : Int;',
        'Diag : "ST_Diagnostic";',
        *[n+READONLY+' : '+typ+';' for n,typ in (
            ('Slot','Int'),('GoneAccepted','Bool'),('SinkCome','UDInt'),('SinkClose','UDInt'),
            ('SinkLast','"ST_AlarmEvent"'),('NativeFaultSlot','Int'),('StandaloneCount','Int'),
            ('StandaloneReturn','Bool'),('StandaloneFlags','Array[1..%d] of "ST_StateFlag"'%cap))],
        'CauseSlot'+PRIVATE+' : Int;', 'Touched'+PRIVATE+' : Array[1..%d] of Bool;'%cap
    ]).encode('ascii'))
    sink='''FUNCTION "F_TestEventSink" : Void
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
VAR_INPUT
    Ev : "ST_AlarmEvent";
END_VAR
BEGIN
    "GDB_StateAlarmTest".SinkLast := #Ev;
    IF #Ev.State = 0 THEN
        "GDB_StateAlarmTest".SinkClose := "GDB_StateAlarmTest".SinkClose + 1;
    ELSE
        "GDB_StateAlarmTest".SinkCome := "GDB_StateAlarmTest".SinkCome + 1;
    END_IF;
END_FUNCTION
'''
    (out/'08_EventSink.scl').write_bytes(sink.encode('ascii'))
    path=out/'40_Main.scl';text=path.read_text('ascii')
    text=text.replace('    ResultCode : Int;','    ResultCode : Int;\n    SlotIndex : Int;\n    Taken : Int;\n    Accepted : Bool;')
    anchor='    "GDB_FraktalMain"(Startup := #Initial_Call);';assert text.count(anchor)==1
    wiring='''    "StationA".AlarmLog.SinkEnabled := TRUE;
    "StationB".AlarmLog.SinkEnabled := TRUE;
    "GDB_FraktalHal".Data.StationA.Cell.Clamp.Sample := "GDB_StateAlarmTest".Position;
    IF "GDB_StateAlarmTest".ClearLog THEN
        "FRK_AlarmBegin"(AlarmLog := "StationA".AlarmLog, Startup := TRUE);
        "GDB_StateAlarmTest".SinkCome := 0;
        "GDB_StateAlarmTest".SinkClose := 0;
        "GDB_StateAlarmTest".ClearLog := FALSE;
    END_IF;
    IF "GDB_StateAlarmTest".RaisePulse THEN
        "GDB_StateAlarmTest".Slot := "FRK_AlarmRaise"(AlarmLog := "StationA".AlarmLog, Diag := "GDB_StateAlarmTest".Diag, ResetClass := "GDB_StateAlarmTest".ResetClass);
        "GDB_StateAlarmTest".RaisePulse := FALSE;
    END_IF;
    IF "GDB_StateAlarmTest".GonePulse THEN
        "GDB_StateAlarmTest".GoneAccepted := "FRK_AlarmGone"(AlarmLog := "StationA".AlarmLog, Slot := "GDB_StateAlarmTest".Slot);
        "GDB_StateAlarmTest".GonePulse := FALSE;
    END_IF;
    IF "GDB_StateAlarmTest".FillPulse THEN
        FOR #SlotIndex := 1 TO "GDB_StateAlarmTest".FillCount DO
            #Taken := "FRK_AlarmRaise"(AlarmLog := "StationA".AlarmLog, Diag := "GDB_StateAlarmTest".Diag, ResetClass := "GDB_StateAlarmTest".ResetClass);
            IF "GDB_StateAlarmTest".ResetClass = 0 THEN #Accepted := "FRK_AlarmGone"(AlarmLog := "StationA".AlarmLog, Slot := #Taken); END_IF;
        END_FOR;
        "GDB_StateAlarmTest".FillPulse := FALSE;
    END_IF;
    IF "GDB_StateAlarmTest".CauseLive THEN
        IF "GDB_StateAlarmTest".CauseSlot = 0 THEN
            "GDB_StateAlarmTest".CauseSlot := "FRK_AlarmRaise"(AlarmLog := "StationA".AlarmLog, Diag := "GDB_StateAlarmTest".Diag, ResetClass := 1);
        ELSIF "StationA".AlarmLog.Active["GDB_StateAlarmTest".CauseSlot].State = 0 THEN
            "GDB_StateAlarmTest".CauseSlot := "FRK_AlarmRaise"(AlarmLog := "StationA".AlarmLog, Diag := "GDB_StateAlarmTest".Diag, ResetClass := 1);
        END_IF;
    ELSIF "GDB_StateAlarmTest".CauseSlot > 0 THEN
        #Accepted := "FRK_AlarmGone"(AlarmLog := "StationA".AlarmLog, Slot := "GDB_StateAlarmTest".CauseSlot);
        "GDB_StateAlarmTest".CauseSlot := 0;
    END_IF;
    "FRK_StateSweep"(Flags := "GDB_StateAlarmTest".StandaloneFlags, Count := "GDB_StateAlarmTest".StandaloneCount, Touched := "GDB_StateAlarmTest".Touched, Startup := #Initial_Call);
    IF "GDB_StateAlarmTest".PublishState THEN
        "GDB_StateAlarmTest".StandaloneReturn := "FRK_State"(Idx := "GDB_StateAlarmTest".StateIndex, Key := 'project.state.atHome', Ok := "GDB_StateAlarmTest".StateValue, Flags := "GDB_StateAlarmTest".StandaloneFlags, Count := "GDB_StateAlarmTest".StandaloneCount, Touched := "GDB_StateAlarmTest".Touched);
    END_IF;
'''
    text=text.replace(anchor,wiring+anchor+'\n    "GDB_StateAlarmTest".NativeFaultSlot := "StationA".Cell.Gate.Core.FaultSlot;')
    path.write_bytes(text.encode('ascii'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);p.add_argument('frames',type=Path)
    a=p.parse_args();prepare(a.out,a.frames)
