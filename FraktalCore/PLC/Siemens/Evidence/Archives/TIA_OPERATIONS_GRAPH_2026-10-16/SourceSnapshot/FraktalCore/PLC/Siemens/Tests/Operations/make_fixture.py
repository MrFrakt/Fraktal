"""Production accounting/weekly shifts against the actual reference-1500 code."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
TIA=HERE.parents[1]
sys.path.insert(0,str(TIA/'tools'))
from fraktal_tia_binding import Catalog,READONLY,PRIVATE
from fraktal_tia_generate import db
from fraktal_tia_operations import build as operations
from fraktal_tia_test_runtime import build as test_runtime,signature,seal_signature


def build():
    spec=importlib.util.spec_from_file_location('line_fixture',HERE.parent/'Line/make_fixture.py')
    line=importlib.util.module_from_spec(spec);spec.loader.exec_module(line)
    sources,_=line.build()
    for name in ('37_LineTest.scl','39_GDB_LineTest.db'):sources.pop(name)
    sources.update(operations()[0]);sources.update(test_runtime())
    facts=Catalog.read();labels=[];body=[]
    from fraktal_tia_health import build as health,RECORDS
    from fraktal_tia_platform import build as platform
    from fraktal_tia_binding import type_source
    for index,(name,fields) in enumerate(facts.resolve(RECORDS).items()):
        sources['00_health_%03d_%s.udt'%(index,name)]=type_source(name,fields)
    sources.update(health(facts)[0]);sources.update(platform(SimpleNamespace(engineering_gates=(tuple(dict(name='USE_SIMULATION',description='std.engineering.simulation',active=True).items()),)),facts)[0])
    from fraktal_tia_tower import build as tower,RECORDS as TOWER_RECORDS
    for index,(name,fields) in enumerate(facts.resolve(TOWER_RECORDS).items()):sources['00_tower_%03d_%s.udt'%(index,name)]=type_source(name,fields)
    sources.update(tower(facts)[0])
    def emit(*lines):body.extend('        '+s for s in lines)
    def check(condition,label):
        labels.append(label);emit('"FRK_TestAssert"(Condition := '+condition+', Code := '+str(len(labels))+', Result := #Result);')
    def reset():
        emit('#Book := "FRK_ProductionDefaults".Book;','#Oee := "FRK_ProductionDefaults".Oee;',
             '#Unit.Good := 0; #Unit.Nok := 0; #Unit.Rework := 0;')
    def tick(now,exec_name='BUSY',blocking=False,good=0,nok=0,ideal=100):
        emit('"FRK_OeeTick"(NowMs := %d, Exec := %d, Blocking := %s, Good := %d, Nok := %d, IdealCycleMs := %d, Book := #Book, Oee := #Oee, Trend := #Trend);'%(now,facts.enums['E_ExecState'][exec_name],str(blocking).upper(),good,nok,ideal))
    def interval(stamp):
        emit('#Ok := "FRK_ShiftInterval"(Now := LDT#'+stamp+', Calendar := #Calendar, ShiftIndex => #Selected, StartAt => #StartAt, EndAt => #EndAt, Target => #Target);')
    def shift(stamp,revision=1,sync=True):
        emit('#Ok := "FRK_ShiftTick"(Now := LDT#'+stamp+', Synchronized := '+str(sync).upper()+', Revision := '+str(revision)+', Scope := \'Operations\', Calendar := #Calendar, Book := #Book, Unit := #Unit, Oee := #Oee, CurrentShift := #CurrentShift, StartedAt := #StartedAt, ProductionTarget := #ProductionTarget, History := #History, Count := #HistoryCount, Truncated := #Truncated, AlarmLog := #AlarmLog);')
    def calendar():
        emit('#Calendar.SchemaVersion := 3; #Calendar.UtcOffsetMin := 0;',
             'FOR #Index := 1 TO %d DO'%facts.capacities['MAX_WEEKLY_SHIFTS'],
             '    #Calendar.Rows[#Index].StartMin := -1; #Calendar.Rows[#Index].DurationMin := 1440;',
             '    #Calendar.Rows[#Index].ActiveDays := 0; #Calendar.Rows[#Index].ProductionTarget := 0;', 'END_FOR;')
    reset();tick(0,ideal=0)
    check('NOT #Oee.OeeValid AND NOT #Oee.AvailValid AND NOT #Oee.PerfValid AND NOT #Oee.QualValid','zero-time factors invalid, never invented100percent')
    tick(1000,good=3,nok=1)
    check('#Oee.RunMs = 1000 AND #Oee.DownMs = 0 AND #Oee.IdleMs = 0','first monotonic origin0 accepted')
    check('ABS(#Oee.Quality - 0.75) < 0.00001 AND ABS(#Oee.Performance - 0.4) < 0.00001 AND ABS(#Oee.Oee - 0.3) < 0.00001','A/P/Q product from authoritative counts')
    tick(2000,blocking=True,good=3,nok=1)
    check('#Oee.RunMs = 1000 AND #Oee.DownMs = 1000','blocking alarm has priority over BUSY for downtime')
    tick(2500,exec_name='READY',good=3,nok=1,ideal=0)
    check('#Oee.IdleMs = 500 AND NOT #Oee.PerfValid AND ABS(#Oee.Oee - 0.375) < 0.00001','idle excluded from availability, unconfigured performance omitted')
    reset();tick(4294967290);tick(4)
    check('#Oee.RunMs = 10','duration wrap remains10ms')
    emit('#Oee.RunMs := UDINT#4294967290;');tick(14)
    check('#Oee.RunMs = UDINT#4294967295','released UDInt accumulator saturates instead of wrapping')
    reset();tick(0);tick(facts.defaults['OEE_SAMPLE_MS'],good=1000,ideal=1000)
    check('#Book.TrendHead = 1 AND #Trend[1].OeeValid AND #Oee.Performance = 1.0','trend sampling and performance cap')
    emit('"FRK_OeeReset"(Good := 1000, Nok := 0, Book := #Book, Oee := #Oee, Trend := #Trend);')
    check('#Book.TrendHead = 0 AND #Book.ManualReset AND #Book.GoodBase = 1000 AND NOT #Oee.OeeValid','manual OEE reset clears ring and captures count bases')
    for exec_name,mode,blocking,starved,blocked,stop,wanted in [
        ('ERROR','AUTO',False,False,False,False,'DOWN'),('BUSY','AUTO',True,True,True,False,'DOWN'),
        ('BUSY','CHANGEOVER',False,True,True,False,'CHANGEOVER'),('BUSY','AUTO',False,True,True,False,'BLOCKED'),
        ('BUSY','AUTO',False,True,False,False,'STARVED'),('BUSY','AUTO',False,False,False,False,'PRODUCING'),
        ('READY','MANUAL',False,False,False,True,'STOPPED'),('READY','MANUAL',False,False,False,False,'IDLE')]:
        emit('#Machine := "FRK_MachineState"(Exec := %d, Mode := %d, Blocking := %s, Starved := %s, Blocked := %s, StopRequested := %s);'%(facts.enums['E_ExecState'][exec_name],facts.enums['E_Mode'][mode],*[str(x).upper() for x in (blocking,starved,blocked,stop)]))
        check('#Machine = '+str(facts.enums['E_MachineState'][wanted]),'machine state '+wanted+(' blocking' if blocking else ''))
    calendar();emit('#Ok := "FRK_ShiftValidate"(Calendar := #Calendar);')
    check('#Ok','empty V3 calendar valid')
    for change,label in [('#Calendar.SchemaVersion := 2;','wrong schema'),('#Calendar.UtcOffsetMin := 841;','offset'),
        ('#Calendar.Rows[1].StartMin := 1440;','start'),('#Calendar.Rows[1].DurationMin := 0;','duration'),
        ('#Calendar.Rows[1].ActiveDays := 128;','day mask'),('#Calendar.Rows[1].ProductionTarget := -1;','target')]:
        calendar();emit(change,'#Ok := "FRK_ShiftValidate"(Calendar := #Calendar);');check('NOT #Ok','reject calendar '+label)
    calendar();emit('#Calendar.Rows[1].StartMin := 480; #Calendar.Rows[1].DurationMin := 720; #Calendar.Rows[1].ActiveDays := 96; #Calendar.Rows[1].ProductionTarget := 500;')
    interval('2026-10-17-08:00:00');check('#Ok AND #Selected = 1 AND #Target = 500 AND #EndAt = LDT#2026-10-17-20:00:00','weekend half-open start and target')
    interval('2026-10-17-20:00:00');check('#Ok AND #Selected = 0 AND #Target = 0 AND #EndAt = LDT#2026-10-18-08:00:00','off-time interval preserves next boundary')
    emit('#Calendar.UtcOffsetMin := 60;');interval('2026-10-17-07:00:00')
    check('#Ok AND #Selected = 1 AND #StartAt = LDT#2026-10-17-07:00:00','UTC offset explicit, no guessed DST')
    calendar();emit('#Calendar.Rows[1].StartMin := 1380; #Calendar.Rows[1].DurationMin := 120; #Calendar.Rows[1].ActiveDays := 64;')
    interval('2026-10-19-00:30:00');check('#Ok AND #Selected = 1 AND #StartAt = LDT#2026-10-18-23:00:00','Sunday overnight belongs to starting day')
    emit('#Calendar.Rows[2].StartMin := 0; #Calendar.Rows[2].DurationMin := 60; #Calendar.Rows[2].ActiveDays := 1;', '#Ok := "FRK_ShiftValidate"(Calendar := #Calendar);')
    check('NOT #Ok','weekly wrap intersection refused')
    emit('#Calendar.Rows[2].StartMin := 60;', '#Ok := "FRK_ShiftValidate"(Calendar := #Calendar);')
    check('#Ok','adjacent half-open intervals permitted')
    calendar();reset();emit('#HistoryCount := 0; #Truncated := FALSE;')
    shift('2026-10-17-06:00:00');check('NOT #Ok AND #CurrentShift = 0','empty-calendar interval initialized without fabricated prior record')
    emit('#Unit.Good := 7; #Oee.RunMs := 1000;');shift('2026-10-17-07:00:00')
    check('NOT #Ok AND #Unit.Good = 7 AND #StartedAt = LDT#2026-10-17-06:00:00','empty calendar keeps accrued interval')
    emit('#Calendar.Rows[1].StartMin := 480; #Calendar.Rows[1].DurationMin := 720; #Calendar.Rows[1].ActiveDays := 96; #Calendar.Rows[1].ProductionTarget := 500;')
    shift('2026-10-17-07:00:00',revision=2)
    check('NOT #Ok AND #Unit.Good = 7 AND #Book.ShiftEnd = LDT#2026-10-17-08:00:00','empty edit schedules next boundary without erasing production')
    shift('2026-10-17-08:00:00',revision=2)
    check('#Ok AND #HistoryCount = 1 AND #History[1].GoodCount = 7 AND #History[1].ShiftIndex = 0 AND #Unit.Good = 0','close unscheduled interval before scheduled shift')
    check('#CurrentShift = 1 AND #ProductionTarget = 500 AND #History[1].ProductionTarget = 0','target latched only on entry')
    emit('#Unit.Good := 9; #Unit.Nok := 1; #Unit.Rework := 2; #Oee.RunMs := 1000;', '#Calendar.Rows[1].ProductionTarget := 900;')
    shift('2026-10-17-09:00:00',revision=3)
    check('NOT #Ok AND #ProductionTarget = 500 AND #Unit.Good = 9','calendar target edit deferred until finite boundary')
    emit('#Book.ManualReset := TRUE;');shift('2026-10-17-20:00:00',revision=3)
    check('#Ok AND #History[1].ProductionTarget = 500 AND #History[1].GoodCount = 9 AND #History[1].NokCount = 1 AND #History[1].ReworkCount = 2 AND #History[1].ManualReset','closed record snapshots target, all counts and partial-reset quality')
    check('#History[1].TimeSynchronized AND #CurrentShift = 0 AND #ProductionTarget = 0 AND #Oee.RunMs = 0','scheduled close and off-time reset atomically')
    shift('2026-10-18-08:00:00',revision=3)
    check('#Ok AND #CurrentShift = 1 AND #ProductionTarget = 900','next interval adopts changed target')
    shift('2026-10-18-07:00:00',revision=3)
    check('NOT #Ok AND NOT #Book.ShiftSynchronized AND #History[1].EndAt >= #History[1].StartAt','backward clock marks quality without negative record')
    shift('2026-10-20-12:00:00',revision=3)
    check('#Ok AND #HistoryCount = 4 AND NOT #History[1].TimeSynchronized','forward jump closes observed interval once, does not fabricate missed shifts')
    calendar();reset();emit('#HistoryCount := 0; #Truncated := FALSE; #Calendar.Rows[1].StartMin := 0; #Calendar.Rows[1].DurationMin := 1440; #Calendar.Rows[1].ActiveDays := 127;')
    shift('2026-10-01-00:00:00')
    for day in range(2,12):shift('2026-10-%02d-00:00:00'%day)
    check('#HistoryCount = %d AND #Truncated AND #History[1].StartAt = LDT#2026-10-10-00:00:00'%facts.capacities['MAX_SHIFT_HISTORY'],'bounded newest-first history truncates explicitly')
    reset();emit('#Ok := "FRK_WorkDegradation"(CycleNo := 1, WorkMs := 1200, BaselineMs := 1000, BandPercent := 10, Book := #Book);')
    check('#Ok AND #Book.Degraded','work-only degradation excursion')
    emit('#Ok := "FRK_WorkDegradation"(CycleNo := 1, WorkMs := 9999, BaselineMs := 1000, BandPercent := 10, Book := #Book);')
    check('NOT #Ok AND #Book.WorkSamples = 1','one sample per completed cycle')
    emit('#Ok := "FRK_WorkDegradation"(CycleNo := 2, WorkMs := 200, BaselineMs := 1000, BandPercent := 10, Book := #Book);')
    check('NOT #Ok AND NOT #Book.Degraded','average recovery rearms maintenance')
    emit('#Ok := "FRK_WorkDegradation"(CycleNo := 3, WorkMs := 3000, BaselineMs := 1000, BandPercent := 10, Book := #Book);')
    check('#Ok','new degradation excursion after recovery')
    emit('#Ok := "FRK_WorkDegradation"(CycleNo := 3, WorkMs := 9999, BaselineMs := 2000, BandPercent := 10, Book := #Book);')
    check('NOT #Ok AND #Book.WorkSamples = 0 AND NOT #Book.Degraded','model baseline change discards prior-model samples')
    emit('#Unit.RequestPending := TRUE; #Unit.Request.Kind := %d;'%facts.enums['E_HmiRequestKind']['RESET_OEE'],
         '#Access.CurrentLevel := 0; #Access.Policy.Required[%d] := 2;'%facts.enums['E_GatedAction']['DATA_WRITE'],
         '#Oee.RunMs := 1000;',
         '"FRK_ProductionRequest"(Unit := #Unit, Access := #Access, Response := #Response, Book := #Book, Oee := #Oee, Trend := #Trend, AlarmLog := #AlarmLog, Scope := \'Operations\');')
    check('NOT #Response.Accepted AND #Oee.RunMs = 1000 AND NOT #Response.Report.Released','OEE reset access gate refuses without mutation')
    emit('#Access.CurrentLevel := 2;',
         '"FRK_ProductionRequest"(Unit := #Unit, Access := #Access, Response := #Response, Book := #Book, Oee := #Oee, Trend := #Trend, AlarmLog := #AlarmLog, Scope := \'Operations\');')
    check('#Response.Accepted AND #Response.Report.Released AND #Oee.RunMs = 0 AND #Book.ManualReset','permitted OEE reset clears accounting and reports partial shift')
    emit('"FRK_AlarmBegin"(Startup := TRUE, AlarmLog := #AlarmLog);',
         '#HealthConfig := "FRK_HealthDefaults".Config;',
         '#HealthInput.TaskAvailable := TRUE; #HealthInput.TaskCycleUs := 1000;',
         '#HealthInput.ControllerAvailable := TRUE; #HealthInput.MemoryAvailableMb := 1024;',
         '#HealthInput.TimeQuality.Available := TRUE; #HealthInput.TimeQuality.Synchronized := TRUE;')
    def health_tick():emit('#Ok := "FRK_HealthCyclic"(Configured := TRUE, Scope := \'Operations\', Input := #HealthInput, ParCfg := #HealthConfig, Status := #HealthStatus, Book := #HealthBook, AlarmLog := #AlarmLog);')
    health_tick();check('#Ok AND #HealthStatus.Present AND #HealthStatus.Healthy AND #AlarmLog.NActive = 0','valid healthy metrics have no standing events')
    emit('#HealthInput.ControllerAvailable := FALSE; #HealthInput.TimeQuality.Synchronized := FALSE;')
    health_tick();check('#Ok AND NOT #HealthStatus.Healthy AND #AlarmLog.NActive = 2 AND NOT #AlarmLog.Blocking','unavailable controller and unqualified sync explicit LOW nonblocking conditions')
    health_tick();check('#AlarmLog.NActive = 2','condition events edge once across repeated scans')
    emit('"FRK_AlarmOperatorReset"(AlarmLog := #AlarmLog);')
    check('#AlarmLog.NActive = 2','operator reset cannot conceal standing auto-reset conditions')
    emit('#HealthInput.ControllerAvailable := TRUE; #HealthInput.TimeQuality.Synchronized := TRUE;')
    health_tick();check('#HealthStatus.Healthy AND #AlarmLog.NActive = 0','restored metrics close only their condition occurrences')
    emit('#HealthInput.TaskCycleUs := 100001; #HealthInput.TaskJitterUs := 10001;')
    health_tick();check('NOT #HealthStatus.Healthy AND #AlarmLog.NActive = 2','task duration and jitter thresholds evaluated independently')
    emit('#HealthInput.TaskCycleUs := 1000; #HealthInput.TaskJitterUs := 0;',
         '#HealthInput.FanAvailable := TRUE; #HealthInput.StorageAvailable := TRUE; #HealthInput.IpcAvailable := FALSE;')
    health_tick();check('#HealthStatus.Healthy AND NOT #HealthStatus.FanAvailable AND NOT #HealthStatus.StorageAvailable','optional unsupported IPC metrics stay unavailable rather than zero alarms')
    emit('#HealthConfig.RequireFieldbus := TRUE;')
    health_tick();check('NOT #HealthStatus.Healthy AND #AlarmLog.NActive = 1','required unavailable fieldbus is diagnosed')
    emit('#HealthConfig.SchemaVersion := 0;')
    health_tick();check('NOT #Ok AND NOT #HealthStatus.Present AND NOT #HealthStatus.Healthy AND #AlarmLog.NActive = 0','invalid health config never claims present or healthy')
    emit('"FRK_EngineeringTick"(Scope := \'Operations\', Slots := #EngineeringSlots, AlarmLog := #AlarmLog);',
         '"FRK_AlarmOperatorReset"(AlarmLog := #AlarmLog);')
    check('#AlarmLog.NActive = 1 AND #AlarmLog.Active[#EngineeringSlots[1]].ReasonCode = %d AND NOT #AlarmLog.Blocking'%facts.enums['E_Reason']['COMMISSIONING_GATE_ACTIVE'],'active build gate survives operator reset as standard standing nonblocking event')
    emit('"FRK_EngineeringTick"(Scope := \'Operations\', Slots := #EngineeringSlots, AlarmLog := #AlarmLog);')
    check('#AlarmLog.NActive = 1','engineering gate does not flood alarm history')
    emit('#Ok := "FRK_AlarmShelve"(Slot := #EngineeringSlots[1], DurationMs := 1000, AlarmLog := #AlarmLog);')
    check('NOT #Ok AND NOT #AlarmLog.Active[#EngineeringSlots[1]].Shelved','commissioning gate rationalization refuses shelving')
    emit('"FRK_AlarmBegin"(Startup := TRUE, AlarmLog := #AlarmLog);',
         '#TestDiag := "FRK_UnitScratch".EmptyDiagnostic; #TestDiag.SourcePath := WSTRING#\'Operations\'; #TestDiag.Description := WSTRING#\'std.system.taskJitterHigh\';',
         '#TestDiag.ReasonCode := %d; #TestDiag.Severity := %d; #TestDiag.Category := %d;'%(facts.enums['E_Reason']['TASK_JITTER_HIGH'],facts.enums['E_Severity']['LOW'],facts.enums['E_Category']['SYSTEM']),
         '#ShelfSlot := "FRK_AlarmRaise"(Diag := #TestDiag, ResetClass := %d, AlarmLog := #AlarmLog);'%facts.enums['E_ResetClass']['MANUAL_RESET'],
         '#Ok := "FRK_AlarmShelve"(Slot := #ShelfSlot, DurationMs := 0, AlarmLog := #AlarmLog);')
    check('NOT #Ok','zero duration shelf refused')
    emit('"FRK_Clock".NowMs := UDINT#4294967290;', '#Ok := "FRK_AlarmShelve"(Slot := #ShelfSlot, DurationMs := 10, AlarmLog := #AlarmLog);')
    check('#Ok AND #AlarmLog.Active[#ShelfSlot].Shelved AND #AlarmLog.Blocking','shelving never removes blocking control or alarm occurrence')
    emit('"FRK_Clock".NowMs := 3; "FRK_AlarmShelfTick"(AlarmLog := #AlarmLog);')
    check('#AlarmLog.Active[#ShelfSlot].Shelved','monotonic shelf stays active until full interval')
    emit('"FRK_Clock".NowMs := 4; "FRK_AlarmShelfTick"(AlarmLog := #AlarmLog);')
    check('NOT #AlarmLog.Active[#ShelfSlot].Shelved AND #AlarmLog.Blocking','shelf auto expires across millisecond wrap without clearing fault')
    emit('#Ok := "FRK_AlarmShelve"(Slot := #ShelfSlot, DurationMs := UDINT#4294967295, AlarmLog := #AlarmLog);')
    check('#Ok AND #AlarmLog.ShelfDuration[#ShelfSlot] = %d'%(facts.capacities['MAX_SHELF_S']*1000),'excessive shelf duration capped by Core authority')
    emit('#AlarmLog.ShelfDuration[#ShelfSlot] := 0; "FRK_AlarmShelfTick"(AlarmLog := #AlarmLog);')
    check('NOT #AlarmLog.Active[#ShelfSlot].Shelved','no monotonic witness after restore cannot leave a permanent shelf')
    emit('#TestDiag.ReasonCode := 19001; #TestDiag.Category := %d;'%facts.enums['E_Category']['SAFETY'],
         '#ShelfSlot := "FRK_AlarmRaise"(Diag := #TestDiag, ResetClass := %d, AlarmLog := #AlarmLog);'%facts.enums['E_ResetClass']['MANUAL_RESET'],
         '#Ok := "FRK_AlarmShelve"(Slot := #ShelfSlot, DurationMs := 1000, AlarmLog := #AlarmLog);')
    check('NOT #Ok','Safety and unrationalized project reasons fail closed')
    emit('#TowerConfig := "FRK_TowerDefaults".Config; #TowerConfig.LampTestDuration := T#60s;',
         '#Unit.RequestPending := TRUE; #Unit.Request.Kind := %d; #Access.CurrentLevel := 2; #Access.Policy.Required[%d] := 2;'%(facts.enums['E_HmiRequestKind']['LAMP_TEST'],facts.enums['E_GatedAction']['MANUAL']),
         '#TestCore.Exec := %d;'%facts.enums['E_ExecState']['BUSY'],
         '"FRK_TowerRequest"(Scope := \'Operations\', Core := #TestCore, Unit := #Unit, Access := #Access, Response := #Response, Book := #TowerBook, ParCfg := #TowerConfig);')
    check('NOT #Response.Accepted AND NOT #TowerBook.TestActive','lamp test refused while BUSY')
    emit('#TestCore.Exec := %d;'%facts.enums['E_ExecState']['READY'],
         '"FRK_TowerRequest"(Scope := \'Operations\', Core := #TestCore, Unit := #Unit, Access := #Access, Response := #Response, Book := #TowerBook, ParCfg := #TowerConfig);')
    check('#Response.Accepted AND #TowerBook.DurationMs = 30000','lamp test permission accepted and interval clamped to30seconds')
    def tower_tick(machine,alarm=False,severity='LOW',operator=False):
        emit('"FRK_TowerTick"(MachineState := %d, AlarmActive := %s, HighestSeverity := %d, OperatorActionRequired := %s, ParCfg := #TowerConfig, Book := #TowerBook, Status := #TowerStatus);'%(facts.enums['E_MachineState'][machine],str(alarm).upper(),facts.enums['E_Severity'][severity],str(operator).upper()))
    tower_tick('STOPPED')
    check('#TowerStatus.TestActive AND #TowerStatus.Red AND #TowerStatus.Amber AND #TowerStatus.Green AND #TowerStatus.Blue AND #TowerStatus.White AND #TowerStatus.Horn','test drives all semantic outputs including horn')
    emit('"FRK_Clock".NowMs := "FRK_Clock".NowMs + 30000;');tower_tick('STOPPED')
    check('NOT #TowerStatus.TestActive AND NOT #TowerStatus.Red AND NOT #TowerStatus.Green AND NOT #TowerStatus.Horn','test expires without client refresh and returns mapped stopped state')
    tower_tick('PRODUCING')
    check('#TowerStatus.Green AND NOT #TowerStatus.Red','productive summary maps green')
    tower_tick('PRODUCING',True,'HIGH')
    check('#TowerStatus.Red AND NOT #TowerStatus.Green AND #TowerStatus.Horn','high alarm overrides productive green and sounds configured horn')
    emit('#TowerConfig.OperatorUsesWhite := TRUE;');tower_tick('BLOCKED',False,operator=True)
    check('#TowerStatus.Amber AND #TowerStatus.White AND NOT #TowerStatus.Blue','blocked and operator-action semantics follow one Core mapping')
    emit('"FRK_Registry".Count := 1; "FRK_Registry".Fault := FALSE; "FRK_Registry".Rows[1].Valid := TRUE;',
         '"FRK_Registry".Rows[1].RunStyle := %d;'%facts.enums['E_RunStyle']['CONTINUOUS'],
         '#Ok := "FRK_StepGate"(Owner := 1, Steppable := TRUE);')
    check('#Ok','continuous style passes ordinary boundary')
    emit('"FRK_Registry".Rows[1].RunStyle := %d;'%facts.enums['E_RunStyle']['SINGLE_STEP'],
         '#Ok := "FRK_StepGate"(Owner := 1, Steppable := TRUE);')
    check('NOT #Ok AND "FRK_Registry".Rows[1].StepWait','single step waits without a request')
    emit('#Ok := "FRK_StepGate"(Owner := 1, Steppable := FALSE);')
    check('#Ok','non-stop step bypasses pacing without a project reset')
    emit('"FRK_Registry".Rows[1].StepToken := TRUE;', '#Ok := "FRK_StepGate"(Owner := 1, Steppable := TRUE);')
    check('#Ok AND NOT "FRK_Registry".Rows[1].StepToken','one single-step token consumed at one ready boundary')
    emit('#Ok := "FRK_StepGate"(Owner := 1, Steppable := TRUE);')
    check('NOT #Ok','one token cannot advance a second concurrent boundary')
    emit('"FRK_Registry".Rows[1].RunStyle := %d;'%facts.enums['E_RunStyle']['HOLD_TO_RUN'],
         '#Ok := "FRK_StepGate"(Owner := 1, Steppable := TRUE);')
    check('NOT #Ok','hold run waits while released')
    emit('"FRK_Registry".Rows[1].HoldRun := TRUE;', '#Ok := "FRK_StepGate"(Owner := 1, Steppable := TRUE);')
    check('#Ok AND "FRK_Registry".Rows[1].HoldRun','hold permits boundaries without consuming its held state')
    emit('#Access.PolicyLost := TRUE; #Support[0] := TRUE; #Support[1] := TRUE; #Support[2] := TRUE;',
         '"FRK_RunStylePrepare"(Owner := 1, Startup := FALSE, Exec := %d, Access := #Access, Supported := #Support);'%facts.enums['E_ExecState']['BUSY'])
    check('NOT "FRK_Registry".Rows[1].HoldRun AND NOT "FRK_Registry".Rows[1].StepToken','policy loss withdraws pacing permits')
    emit('#Unit.Request.Kind := %d; #Unit.Request.BoolValue := FALSE;'%facts.enums['E_HmiRequestKind']['SET_HOLD_RUN'],
         '"FRK_RunStyleRequest"(Owner := 1, Scope := \'Operations\', Exec := 0, Supported := #Support, Unit := #Unit, Access := #Access, Response := #Response);')
    check('#Response.Accepted','hold release cannot be denied by a lost session or policy')
    emit('#Access.PolicyLost := FALSE; #Access.CurrentLevel := 4; #Unit.Request.Kind := %d; #Unit.Request.IntValue := 99;'%facts.enums['E_HmiRequestKind']['SET_RUN_STYLE'],
         '"FRK_RunStyleRequest"(Owner := 1, Scope := \'Operations\', Exec := 0, Supported := #Support, Unit := #Unit, Access := #Access, Response := #Response);')
    check('NOT #Response.Accepted','invalid run-style ordinal refused before array access')
    emit('#Unit.Request.IntValue := 1; #Support[1] := FALSE;',
         '"FRK_RunStyleRequest"(Owner := 1, Scope := \'Operations\', Exec := 0, Supported := #Support, Unit := #Unit, Access := #Access, Response := #Response);')
    check('NOT #Response.Accepted','unsupported mode style refused')
    host=facts.enums['E_HostEventKind'];host_capacity=facts.capacities['MAX_HOST_EVENTS']
    def host_emit(kind,scope='StationA',uid='part-17',verdict=0,reason=0):
        emit('"FRK_HostEmit"(Kind := %d, Scope := \'%s\', PartUid := \'%s\', Subject := \'Tool\', Value := \'T17\', Verdict := %d, Reason := %d);'%(kind,scope,uid,verdict,reason))
    host_emit(0);host_emit(999);host_emit(host['MODE_CHANGED'],scope='unknown')
    check('"FRK_HostStore".Rows[1].View.Count = 0','invalid host kind and foreign identity cannot publish')
    host_emit(host['NOK'],verdict=facts.enums['E_Verdict']['NOK'],reason=10001)
    emit('"FRK_HostMirror"(Scope := \'StationA\', Startup := TRUE, Seen := #HostSeen, View := #HostView);')
    check('#HostView.Count = 1 AND #HostView.Capacity = %d AND #HostView.RingHead = 1 AND NOT #HostView.Wrapped'%host_capacity,'host ring publishes actual count, capacity and cursor')
    check('#HostView.Ring[1].Sequence = 1 AND #HostView.Ring[1].Kind = %d AND #HostView.Ring[1].StationPath = WSTRING#\'StationA\' AND #HostView.Ring[1].PartUid = \'part-17\' AND #HostView.Ring[1].ReasonCode = 10001'%host['NOK'],'host record preserves sequence, fixed kind, identity, part and reason')
    check('NOT #HostView.Ring[1].TimeSynchronized AND #HostView.Ring[1].Stamp > LDT#2026-01-01-00:00:00','host time is native but synchronization stays explicitly unqualified')
    check('"FRK_HostStore".Rows[2].View.Count = 0','host ring remains scoped to the producing Unit')
    emit('FOR #Index := 1 TO %d DO'%host_capacity)
    host_emit(host['TOOL_CHANGED'])
    emit('END_FOR;','"FRK_HostMirror"(Scope := \'StationA\', Startup := FALSE, Seen := #HostSeen, View := #HostView);')
    check('#HostView.Count = %d AND #HostView.RingHead = 1 AND #HostView.Wrapped AND #HostView.Ring[1].Sequence = %d'%(host_capacity,host_capacity+1),'overwritten host records set explicit loss indicator and retain ordering')
    emit('"FRK_HostStore".Rows[1].Sequence := UDINT#4294967295;')
    host_emit(host['MATERIAL_CHANGED'])
    check('"FRK_HostStore".Rows[1].Sequence = 1 AND "FRK_HostStore".Rows[1].View.Wrapped','sequence exhaustion restarts a marked ring instead of silently overflowing')
    # Keep the normal result projection consumed by the common SDK runner.
    text='\n'.join(['FUNCTION_BLOCK "FB_OperationsTest"',"{ S7_Optimized_Access := 'TRUE' }",'VERSION : 0.1',
        'VAR_OUTPUT',*['    '+n+READONLY+' : '+t+';' for n,t in [('Done','Bool'),('Checks','Int'),('Failures','Int'),('FirstFailure','Int')]],'END_VAR',
        'VAR','    Result'+READONLY+' : "FRK_TestResult";',*['    '+n+PRIVATE+' : '+t+';' for n,t in [
            ('Ran','Bool'),('Book','"FRK_Production"'),('Oee','"ST_Oee"'),('Trend','Array[1..%d] of "ST_OeeSample"'%facts.capacities['MAX_OEE_SAMPLES']),
            ('Unit','"FRK_Unit"'),('Calendar','"ST_ShiftCalendarV3"'),('AlarmLog','"FRK_AlarmLog"'),('Access','"FRK_Access"'),('Response','"ST_HmiResponse"'),('Ok','Bool'),('Index','Int'),('Machine','DInt'),
            ('Selected','Int'),('StartAt','LDT'),('EndAt','LDT'),('Target','UDInt'),('CurrentShift','Int'),('StartedAt','LDT'),('ProductionTarget','UDInt'),
            ('History','Array[1..%d] of "ST_ShiftRecordV3"'%facts.capacities['MAX_SHIFT_HISTORY']),('HistoryCount','Int'),('Truncated','Bool')]],
        *['    '+n+PRIVATE+' : '+t+';' for n,t in [('HealthInput','"ST_SystemHealthInput"'),('HealthConfig','"ST_SystemHealthParCfg"'),('HealthStatus','"ST_SystemHealthStatus"'),('HealthBook','"FRK_HealthBook"'),('EngineeringSlots','Array[1..1] of Int')]],
        '    ShelfSlot'+PRIVATE+' : Int;','    TestDiag'+PRIVATE+' : "ST_Diagnostic";',
        *['    '+n+PRIVATE+' : '+t+';' for n,t in [('TowerConfig','"ST_SignalTowerParCfg"'),('TowerBook','"FRK_TowerBook"'),('TowerStatus','"ST_SignalTowerOut"'),('TestCore','"FRK_Core"')]],
        '    Support'+PRIVATE+' : Array[0..2] of Bool;',
        '    HostView'+PRIVATE+' : "FRK_HostEvents";','    HostSeen'+PRIVATE+' : UDInt;',
        'END_VAR','BEGIN','    IF NOT #Ran THEN',*body,'        #Ran := TRUE;','    END_IF;',
        '    #Done := #Ran AND NOT #Result.ProtocolError; #Checks := #Result.Checks; #Failures := #Result.Failures; #FirstFailure := #Result.FirstFailure;', 'END_FUNCTION_BLOCK',''])
    sources['37_OperationsTest.scl']=text
    sources['39_GDB_OperationsTest.db']='\n'.join(['DATA_BLOCK "GDB_OperationsTest"',"{ S7_Optimized_Access := 'TRUE' }",'VERSION : 0.1','NON_RETAIN','"FB_OperationsTest"','BEGIN','END_DATA_BLOCK',''])
    results=json.loads((HERE/'bench.json').read_bytes())['results']
    sources['39_GDB_OperationsResultTest.db']=db(results,['Status'+READONLY+' : "FRK_TestStatus";'])
    sources['40_Main.scl']='\n'.join(['ORGANIZATION_BLOCK "Main"',"{ S7_Optimized_Access := 'TRUE' }",'VERSION : 0.1','BEGIN','    "GDB_OperationsTest"();',
        '    "FRK_TestPublish"(Complete := "GDB_OperationsTest".Done, '+', '.join('Image%d := DWORD#@IMAGE_HASH_%d@'%(i,i) for i in range(8))+', Result := "GDB_OperationsTest".Result, Status := "'+results+'".Status);','END_ORGANIZATION_BLOCK',''])
    sources=seal_signature(sources,labels)
    return sources,labels


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);a=p.parse_args()
    sources,labels=build();a.out.mkdir(parents=True,exist_ok=False)
    for name,text in sources.items():(a.out/name).write_bytes(text.encode('ascii'))
    digest=signature(sources,labels)
    (a.out/'image_hash.json').write_text(json.dumps(dict(sha256=digest),indent=2)+'\n',encoding='ascii')
    (a.out/'assertions.json').write_text(json.dumps(dict(enumerate(labels,1)),indent=2)+'\n',encoding='ascii')
    print(json.dumps(dict(sources=len(sources),checks=len(labels))))
