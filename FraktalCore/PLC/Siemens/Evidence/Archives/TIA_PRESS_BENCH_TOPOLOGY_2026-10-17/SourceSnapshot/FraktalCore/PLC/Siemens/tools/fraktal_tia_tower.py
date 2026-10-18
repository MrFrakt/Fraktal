"""The Core signal-tower mapping, fed by the Unit's authoritative summary."""
import hashlib
import re
from pathlib import Path
import xml.etree.ElementTree as ET
from fraktal_tia_binding import CORE,REPO,PRIVATE,READONLY,type_source
from fraktal_tia_expressions import locals_in

AUTHORITY=CORE/'BaseClasses/FB_SignalTower.TcPOU'
TEMPLATE=Path(__file__).resolve().parents[1]/'Framework/Core/signal_tower.scl.in'
RECORDS=('ST_SignalTowerOut','ST_SignalTowerParCfg')


def build(catalog):
    from fraktal_tia_generate import db
    method=next(m for m in ET.parse(AUTHORITY).findall('.//Method') if m.get('Name')=='Cyclic')
    body=method.findtext('Implementation/ST')
    if body.count('Status.Red := FALSE;')!=1 or not body.endswith('Cyclic := TRUE;'):raise ValueError('Core tower mapping boundary changed')
    mapping=body[body.index('Status.Red := FALSE;'):].removesuffix('Cyclic := TRUE;').replace('_testActive','TestActive')
    # TwinCAT permits empty instructions and an omitted block terminator ';'.
    # TIA needs an executable statement for those otherwise empty branches.
    mapping=re.sub(r'\bEND_(IF|CASE)\b(?!\s*;)',r'END_\1;',mapping)
    mapping=re.sub(r'(?m)^(\s*);\s*$',r'\1Status.TestActive := TestActive;',mapping)
    mapping=mapping.replace('ELSE ; END_IF;','ELSE Status.TestActive := TestActive; END_IF;')
    for name,values in catalog.enums.items():
        for member,value in values.items():mapping=mapping.replace(name+'.'+member,str(value))
    if 'E_' in mapping or '_M_' in mapping:raise ValueError('Unbound Core tower expression')
    mapping=locals_in(mapping,{'Status','MachineState','AlarmActive','HighestSeverity','OperatorActionRequired','ParCfg','TestActive'})
    text=TEMPLATE.read_text('ascii').replace('@MAPPING@',mapping)
    for name,values in catalog.enums.items():
        for member,value in values.items():text=text.replace('@'+name+'.'+member+'@',str(value))
    for name,value in catalog.capacities.items():text=text.replace('@'+name+'@',str(value))
    return {'02_FRK_TowerBook.udt':type_source('FRK_TowerBook',[dict(member=n,native_type=t,accessible=False,initial='') for n,t in [('TestActive','Bool'),('StartedMs','UDInt'),('DurationMs','UDInt')]]),
        '05_FRK_TowerDefaults.db':db('FRK_TowerDefaults',['Config'+PRIVATE+' : "ST_SignalTowerParCfg";']),
        '16d_SignalTower.scl':text},{p.relative_to(REPO).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (AUTHORITY,TEMPLATE,Path(__file__))}


def declarations():return ['    SignalTower'+READONLY+' : "ST_SignalTowerOut";',
    '    TowerBook'+PRIVATE+' : "FRK_TowerBook";','    TowerConfig'+PRIVATE+' : "ST_SignalTowerParCfg";']


def config(t):
    fields={'lamp_test_duration':'LampTestDuration','horn_on_high':'HornOnHigh','operator_uses_white':'OperatorUsesWhite'}
    return ['    #TowerConfig := "FRK_TowerDefaults".Config;',*['    #TowerConfig.'+fields[key]+' := #'+value+';' for key,value in t.tower]]


def request():return ['    "FRK_TowerRequest"(Scope := #Status.Name, Core := #Core, Unit := #Unit, Access := #Access, Response := #HmiResponse, Book := #TowerBook, ParCfg := #TowerConfig);']


def frame():return ['    IF #Startup THEN #TowerBook.TestActive := FALSE; END_IF;',
    '    "FRK_TowerFrame"(MachineState := #MachineState, OperatorActionRequired := #Decision.Prompt <> WSTRING#\'\' OR "FRK_Registry".Rows[#Core.RegIndex].StepWait, ParCfg := #TowerConfig, Book := #TowerBook, AlarmLog := #AlarmLog, Status := #SignalTower);']
