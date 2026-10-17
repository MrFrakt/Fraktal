"""Narrow port of Core's health expression method, with native condition edges.

This accepts that method's simple declarations/expressions only. New helpers
in the Core method must receive an explicit binding rather than disappearing.
"""
import hashlib
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from fraktal_tia_expressions import locals_in

from fraktal_tia_binding import CORE,PRIVATE,READONLY,REPO,type_source
from fraktal_tia_config import function

AUTHORITY=CORE/'BaseClasses/FB_SystemHealthPublisher.TcPOU'
PROBE=Path(__file__).resolve().parents[1]/'Framework/Core/s7_health_probe.scl.in'
RECORDS=('ST_SystemHealthInput','ST_SystemHealthStatus','ST_SystemHealthParCfg')


def build(catalog):
    from fraktal_tia_generate import db
    method=next(m for m in ET.parse(AUTHORITY).findall('.//Method') if m.get('Name')=='Cyclic')
    declaration=method.findtext('Declaration');body=method.findtext('Implementation/ST')
    local=re.search(r'(?m)^VAR\s*\n(.*?)^END_VAR',declaration,re.S)[1]
    temps=[];locals_=[]
    for names,kind in re.findall(r'([A-Za-z_, ]+)\s*:\s*(BOOL)\s*;',local):
        for name in names.split(','):locals_.append(name.strip());temps.append(name.strip()+' : Bool;')
    calls=list(re.finditer(r"_M_UpdateAlarm\(Active := (\w+), Reason := E_Reason\.(\w+),\s*Text := '([^']+)', Slot := (_\w+)\);",body))
    if not calls:raise ValueError('Core health condition inventory is empty')
    slot_names=[m[4] for m in calls]
    def alarm(match):
        slot=slot_names.index(match[4])+1
        return '"FRK_ConditionEvent"(Active := '+match[1]+', Reason := '+str(catalog.enums['E_Reason'][match[2]])+", Description := WSTRING#'"+match[3]+"', Source := STRING_TO_WSTRING(Scope), Slot := Book.Slots[%d], AlarmLog := AlarmLog);"%slot
    body=re.sub(r"_M_UpdateAlarm\(Active := (\w+), Reason := E_Reason\.(\w+),\s*Text := '([^']+)', Slot := (_\w+)\);",alarm,body)
    if '_M_' in body:raise ValueError('Core health method added an unbound helper')
    body=body.replace('_sourcePath','STRING_TO_WSTRING(Scope)').replace('Cyclic :=','FRK_HealthCyclic :=')
    variables={*locals_,'Input','ParCfg','Configured','Status','Scope','Book','AlarmLog','FRK_HealthCyclic'}
    # Strings/comments and qualified members are never rewritten.
    body=locals_in(body,variables)
    text=function('FRK_HealthCyclic',['Configured : Bool;','Scope : String;'],[
        'Input : "ST_SystemHealthInput";','ParCfg : "ST_SystemHealthParCfg";',
        'Status : "ST_SystemHealthStatus";','Book : "FRK_HealthBook";','AlarmLog : "FRK_AlarmLog";'],temps,
        ['    '+line.rstrip() if line.strip() else '' for line in body.splitlines()],'Bool')
    sources={'02_FRK_HealthBook.udt':type_source('FRK_HealthBook',[
        dict(member='Slots',native_type='Array[1..%d] of Int'%len(calls),accessible=False,initial='')]),
        '05_FRK_HealthDefaults.db':db('FRK_HealthDefaults',['Config'+PRIVATE+' : "ST_SystemHealthParCfg";']),
        '05_FRK_HealthProbe.db':db('FRK_HealthProbe',[
            'Input'+PRIVATE+' : "ST_SystemHealthInput";','HaveSample'+PRIVATE+' : Bool;','LastCycleUs'+PRIVATE+' : UDInt;']),
        '16c_HealthServices.scl':text+'\n'+PROBE.read_text('ascii')}
    inputs={p.relative_to(REPO).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (AUTHORITY,PROBE,Path(__file__))}
    return sources,inputs


def declarations():return ['    SystemHealth'+READONLY+' : "ST_SystemHealthStatus";',
    '    HealthBook'+PRIVATE+' : "FRK_HealthBook";','    HealthConfig'+PRIVATE+' : "ST_SystemHealthParCfg";']


def frame(t):
    lines=['    #HealthConfig := "FRK_HealthDefaults".Config;']
    names={'max_task_cycle':'MaxTaskCycleUs','max_task_jitter':'MaxTaskJitterUs','require_time_sync':'RequireTimeSync'}
    lines+=['    #HealthConfig.'+names[key]+' := #'+member+';' for key,member in t.health]
    lines+=['    #HealthResult := "FRK_HealthCyclic"(Configured := TRUE, Scope := #Status.Name, Input := "FRK_HealthProbe".Input, ParCfg := #HealthConfig, Status := #SystemHealth, Book := #HealthBook, AlarmLog := #AlarmLog);']
    return lines
