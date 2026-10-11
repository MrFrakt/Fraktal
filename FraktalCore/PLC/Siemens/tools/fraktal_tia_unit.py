"""Emit the Unit mode/mailbox and local carrier services from Core authorities."""
from pathlib import Path
import re

from fraktal_tia_binding import PRIVATE, type_source
from fraktal_tia_generate import db

TEMPLATE = Path(__file__).resolve().parents[1] / 'Framework/Core/unit_services.scl.in'
ROUTING = TEMPLATE.with_name('unit_routing.scl.in')
CONFIG = TEMPLATE.with_name('config_manifest.scl.in')


def build(catalog):
    mode_count = len(catalog.enums['E_Mode'])
    fields = {
        'Initialized':'Bool', 'Mode':'DInt', 'RequestedMode':'DInt', 'ModePending':'Bool',
        'ExitFirst':'Bool', 'RunReq':'Bool', 'AbortReq':'Bool', 'StopReq':'Bool',
        'ModeSince':'UDInt',
        'ReleaseChildren':'Bool', 'Clearing':'Bool', 'FaultLatched':'Bool', 'PrevError':'Bool',
        'EvReset':'Bool', 'SeenSequence':'UDInt', 'RequestPending':'Bool',
        'Request':'"ST_HmiRequest"', 'Permit':'Bool', 'PermitDiag':'"ST_Diagnostic"',
        'CarrierIndex':'DInt', 'Good':'UDInt', 'Nok':'UDInt', 'Rework':'UDInt', 'NokReason':'DInt',
        'CascadePending':'Bool', 'CascadeKind':'DInt', 'CascadeMode':'DInt', 'FollowStart':'Bool',
    }
    access = {'CurrentLevel':'DInt', 'CurrentUser':'String[32]', 'LoginFailed':'Bool', 'Policy':'"ST_AccessPolicy"'}
    carrier = {'Enabled':'Bool','Kind':'DInt','Serial':'UDInt','Context':'"ST_PartContext"',
               'Written':'"ST_PartContext"','Writes':'UDInt'}
    condition = {'Used':'Bool','Value':'DInt','Ok':'Bool','Diag':'"ST_Diagnostic"','Bypassable':'Bool'}
    sources={}
    for name, members in [('FRK_Unit',fields), ('FRK_Access',access), ('FRK_Carrier',carrier), ('FRK_ManualConditionRow',condition), ('FRK_ConfigCursor', {'Position':'DInt', 'First':'DInt'})]:
        sources['02_'+name+'.udt']=type_source(name,[{'member':n,'native_type':v,'accessible':False if name!='FRK_Access' else True,'initial':''} for n,v in members.items()])
    # Capacity is substituted by the structural generator for this station.
    sources['05_FRK_Carriers.db']=db('FRK_Carriers',['Slots'+PRIVATE+' : Array[0..@CAPACITY@] of "FRK_Carrier";'])
    sources['05_FRK_UnitScratch.db']=db('FRK_UnitScratch',['Response'+PRIVATE+' : \"ST_HmiResponse\";', 'EmptyDiagnostic'+PRIVATE+' : \"ST_Diagnostic\";', 'EmptyConfigEntry'+PRIVATE+' : \"ST_ConfigEntry\";'])
    text=TEMPLATE.read_text(encoding='ascii')+'\n'+ROUTING.read_text(encoding='ascii')
    for enum, members in catalog.enums.items():
        for member,value in members.items(): text=text.replace('@'+enum+'.'+member+'@',str(value))
    for name,value in catalog.capacities.items():text=text.replace('@'+name+'@',str(value))
    text=text.replace('@MODE_COUNT@',str(mode_count))
    text=text.replace('@MODE_LAST@',str(mode_count-1))
    if re.search(r'@(?!CAPACITY@)[A-Z_\.]+@',text):raise ValueError('unresolved Unit template token')
    sources['13_UnitServices.scl']=text
    text=CONFIG.read_text(encoding='ascii')
    for enum, members in catalog.enums.items():
        for member,value in members.items(): text=text.replace('@'+enum+'.'+member+'@',str(value))
    for name,value in catalog.capacities.items():text=text.replace('@'+name+'@',str(value))
    text=text.replace('@MODE_LAST@',str(mode_count-1))
    if '@' in text:raise ValueError('unresolved manifest template token')
    sources['14_ConfigManifest.scl']=text
    return sources
