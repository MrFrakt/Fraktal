"""Shared production accounting; public shapes/ordinals derive from Core."""
import hashlib
from pathlib import Path

from fraktal_tia_binding import Catalog, PRIVATE, REPO, type_source

TEMPLATE=Path(__file__).resolve().parents[1]/'Framework/Core/production_services.scl.in'
RECORDS=('ST_Oee','ST_OeeSample','ST_ShiftCalendarV3','ST_ShiftRecordV3')


def build(catalog=None, *, include_types=True):
    from fraktal_tia_generate import db
    catalog=catalog or Catalog.read()
    sources={}
    if include_types:
        for i,(name,fields) in enumerate(catalog.resolve(RECORDS).items()):
            sources['00_OP%03d_%s.udt'%(i,name)]=type_source(name,fields)
    fields={'HaveClock':'Bool','LastMs':'UDInt','SampleMs':'UDInt','TrendHead':'Int',
            'GoodBase':'UDInt','NokBase':'UDInt',
            'ShiftInitialized':'Bool','ShiftEnd':'LDT','ShiftLastNow':'LDT',
            'CalendarRevision':'UDInt','ShiftSynchronized':'Bool','ManualReset':'Bool',
            'CycleSeen':'UDInt','WorkSamples':'UDInt','WorkTotalMs':'LReal','Degraded':'Bool',
            'BaselineSeen':'UDInt','BandSeen':'UInt'}
    sources['02_FRK_Production.udt']=type_source('FRK_Production',[
        dict(member=n,native_type=t,accessible=False,initial='') for n,t in fields.items()])
    sources['05_FRK_ProductionDefaults.db']=db('FRK_ProductionDefaults',[
        'Book'+PRIVATE+' : "FRK_Production";', 'Oee'+PRIVATE+' : "ST_Oee";',
        'Sample'+PRIVATE+' : "ST_OeeSample";', 'Shift'+PRIVATE+' : "ST_ShiftRecordV3";'])
    sources['05_FRK_ProductionScratch.db']=db('FRK_ProductionScratch',[
        'Calendar'+PRIVATE+' : "ST_ShiftCalendarV3";'])
    text=TEMPLATE.read_text('ascii')
    for name,values in catalog.enums.items():
        for member,value in values.items():text=text.replace('@'+name+'.'+member+'@',str(value))
    for name,value in {**catalog.defaults,**catalog.capacities}.items():text=text.replace('@'+name+'@',str(value))
    if '@' in text:raise ValueError('unresolved production service token')
    sources['16a_ProductionServices.scl']=text
    inputs={p.relative_to(REPO).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (TEMPLATE,Path(__file__))}
    return sources,inputs


def published_types(oee_capacity,shift_capacity,shifts=True):
    fields={'MachineState':'DInt','Oee':'"ST_Oee"',
            'OeeTrend':'Array[1..%d] of "ST_OeeSample"'%oee_capacity,'OeeTrendHead':'Int'}
    if shifts:fields.update({'CurrentShift':'Int','ShiftStartedAt':'LDT','ShiftProductionTarget':'UDInt',
        'ShiftHistory':'Array[1..%d] of "ST_ShiftRecordV3"'%shift_capacity,
        'ShiftHistoryCount':'Int','ShiftHistoryTruncated':'Bool'})
    return fields


def declarations(catalog,shifts=False):
    from fraktal_tia_binding import READONLY
    fields=published_types(catalog.capacities['MAX_OEE_SAMPLES'],catalog.capacities['MAX_SHIFT_HISTORY'],shifts)
    return ['    ProductionBook'+PRIVATE+' : "FRK_Production";',
            *['    '+n+READONLY+' : '+t+';' for n,t in fields.items()]]


def operand(t,key,default='0'):
    member=dict(t.production).get(key)
    return '#'+member if member else default


def frame(t, catalog):
    ideal=operand(t,'ideal_cycle')
    baseline=operand(t,'baseline')
    band=operand(t,'degradation_percent')
    return [
        '    IF #Startup THEN #ProductionBook := "FRK_ProductionDefaults".Book; #Oee := "FRK_ProductionDefaults".Oee; END_IF;',
        '    #MachineState := "FRK_MachineState"(Exec := #Core.Exec, Mode := #Unit.Mode, Blocking := #Unit.AlarmBlocking, Starved := #Starved, Blocked := #Blocked, StopRequested := #Unit.StopReq);',
        '    "FRK_OeeTick"(NowMs := "FRK_Clock".NowMs, Exec := #Core.Exec, Blocking := #Unit.AlarmBlocking, Good := #Unit.Good, Nok := #Unit.Nok, IdealCycleMs := '+ideal+', Book := #ProductionBook, Oee := #Oee, Trend := #OeeTrend);',
        '    #OeeTrendHead := #ProductionBook.TrendHead;',
        *(['    IF "FRK_WorkDegradation"(CycleNo := #Profiler.LastCycle.CycleNo, WorkMs := TIME_TO_UDINT(#Profiler.LastCycle.WorkTime), BaselineMs := '+baseline+', BandPercent := '+band+', Book := #ProductionBook) THEN',
           '        "FRK_AlarmMessage"(AlarmLog := #AlarmLog, Reason := '+str(catalog.enums['E_Reason']['CYCLE_TIME_DEGRADED'])+', Description := WSTRING#\'std.maintenance.cycleTimeDegraded\', SourcePath := STRING_TO_WSTRING(#Status.Name));',
           '    END_IF;'] if 'baseline' in dict(t.production) else [])]


def request_call():
    return ['    "FRK_ProductionRequest"(Unit := #Unit, Access := #Access, Response := #HmiResponse, Book := #ProductionBook, Oee := #Oee, Trend := #OeeTrend, AlarmLog := #AlarmLog, Scope := #Status.Name);']


def shift_frame():
    return ['    IF #Core.ParentIndex = 0 AND "FRK_LineScope"(Scope := #Status.Name) AND "FRK_Line".Data.Applied THEN',
            '        "FRK_LineCalendar"(Values := "FRK_Line".Data.Values, Calendar := "FRK_ProductionScratch".Calendar);',
            '        #ProductionChanged := "FRK_ShiftTick"(Now := "FRK_Now"(), Synchronized := FALSE, Revision := "FRK_Line".Data.Status.Revision, Scope := #Status.Name, Calendar := "FRK_ProductionScratch".Calendar, Book := #ProductionBook, Unit := #Unit, Oee := #Oee, CurrentShift := #CurrentShift, StartedAt := #ShiftStartedAt, ProductionTarget := #ShiftProductionTarget, History := #ShiftHistory, Count := #ShiftHistoryCount, Truncated := #ShiftHistoryTruncated, AlarmLog := #AlarmLog);',
            '    END_IF;']
