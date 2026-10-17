"""Core fixed host records and bounded per-deployed-Unit event ownership.

The private store lets shared part services emit without application forwarding.
The public view is refreshed only on an event, never accumulated by an HMI.
"""
import hashlib
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from fraktal_tia_binding import CORE,PRIVATE,READONLY,REPO,type_source,literal

TEMPLATE=Path(__file__).resolve().parents[1]/'Framework/Core/host_events.scl.in'
AUTHORITY=CORE/'BaseClasses/FB_HostEventPublisher.TcPOU'


def build(model,catalog):
    from fraktal_tia_generate import db
    types={t.name for t in model.types if t.unit_modes}
    paths=[i.path for i in model.instances if i.type_name in types]
    count=max(1,len(paths));capacity=catalog.capacities['MAX_HOST_EVENTS']
    view=type_source('FRK_HostEvents',[
        dict(member=n,native_type=t,accessible=True,writable=False,initial='') for n,t in (
            ('Ring','Array[1..%d] of "ST_HostEvent"'%capacity),('RingHead','Int'),
            ('Count','Int'),('Capacity','Int'),('Wrapped','Bool'))])
    book=type_source('FRK_HostBook',[
        dict(member=n,native_type=t,accessible=False,initial='') for n,t in (
            ('View','"FRK_HostEvents"'),('Sequence','UDInt'))])
    text=TEMPLATE.read_text('ascii')
    slots='\n'.join('    IF #Scope = '+literal(path)+' THEN #FRK_HostSlot := %d; RETURN; END_IF;'%i for i,path in enumerate(paths,1))
    emit=next(m for m in ET.parse(AUTHORITY).findall('.//Method') if m.get('Name')=='Emit')
    kinds=[str(catalog.enums['E_HostEventKind'][k]) for k in re.findall(r'E_HostEventKind\.(\w+)',emit.findtext('Implementation/ST').split('END_CASE')[0])]
    if not kinds or len(kinds)!=len(set(kinds)):raise ValueError('Core fixed host kind inventory is invalid')
    text=text.replace('@SLOTS@',slots).replace('@VALID_KINDS@',', '.join(kinds)).replace('@CAPACITY@',str(capacity)).replace('@UNIT_COUNT@',str(count))
    from fraktal_tia_config import width
    for key,member in [('PART_WIDTH','PartUid'),('SUBJECT_WIDTH','Subject'),('VALUE_WIDTH','Value')]:text=text.replace('@'+key+'@',str(width(catalog,'ST_HostEvent',member)))
    sources={'02_FRK_HostEvents.udt':view,'02_FRK_HostStoreBook.udt':book,
        '05_FRK_HostStore.db':db('FRK_HostStore',['Rows'+PRIVATE+' : Array[1..%d] of "FRK_HostBook";'%count])}
    return sources,text,{p.relative_to(REPO).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (TEMPLATE,AUTHORITY,Path(__file__))}


def declarations():return ['    HostEvents'+READONLY+' : "FRK_HostEvents";',
    '    HostSeenSequence'+PRIVATE+' : UDInt;','    HostDoneSeen'+PRIVATE+' : Bool;']


def frame(t,model,config,catalog):
    value='#Model.ModelCode' if config and t.name in config.roots and model.model_config else "''"
    return ['    IF #Core.Exec = %d AND NOT #HostDoneSeen AND #Unit.Mode = %d THEN'%(catalog.enums['E_ExecState']['DONE'],catalog.enums['E_Mode']['CHANGEOVER']),
        '        "FRK_HostEmit"(Kind := %d, Scope := #Status.Name, PartUid := \'\', Subject := \'Model\', Value := '%catalog.enums['E_HostEventKind']['CHANGEOVER_DONE']+value+', Verdict := 0, Reason := 0);','    END_IF;',
        '    #HostDoneSeen := #Core.Exec = %d;'%catalog.enums['E_ExecState']['DONE'],
        '    "FRK_HostMirror"(Scope := #Status.Name, Startup := #Startup, Seen := #HostSeenSequence, View := #HostEvents);']
