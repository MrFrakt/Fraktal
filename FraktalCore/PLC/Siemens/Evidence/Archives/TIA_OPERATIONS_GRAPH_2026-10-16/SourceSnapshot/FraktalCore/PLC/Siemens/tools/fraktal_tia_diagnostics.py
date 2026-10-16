"""Consumed diagnostic samples; no root-FB dependency in sequence services."""
import hashlib
from pathlib import Path
from fraktal_tia_binding import PRIVATE, REPO, type_source, literal

TEMPLATE=Path(__file__).resolve().parents[1]/'Framework/Core/diagnostic_services.scl.in'


def consumers(model):
    types={t.name:t for t in model.types}
    scopes=[i.path for i in model.instances if types[i.type_name].sequence_view]
    return [i for i in model.instances if any(i.path==p or i.path.startswith(p+'.') for p in scopes)]


def build(model,catalog):
    from fraktal_tia_generate import db
    nodes=consumers(model)
    fields={'Valid':'Bool','Index':'DInt','State':'DInt','Held':'Bool',
            'Timeout':'Time','Diagnostic':'"ST_Diagnostic"'}
    summary={'Valid':'Bool','State':'DInt','Fault':'Bool','Held':'Bool',
             'Timeout':'Time','Diagnostic':'"ST_Diagnostic"'}
    sources={}
    for name,members in [('FRK_DiagSample',fields),('FRK_DiagSummary',summary)]:
        sources['07_'+name+'.udt']=type_source(name,[{'member':n,'native_type':t,'accessible':False,'initial':''} for n,t in members.items()])
    sources['08_FRK_Diagnostics.db']=db('FRK_Diagnostics',[
        'Samples'+PRIVATE+' : Array[1..'+str(len(nodes))+'] of "FRK_DiagSample";',
        'Empty'+PRIVATE+' : "FRK_DiagSummary";'])
    text=TEMPLATE.read_text('ascii')
    text=text.replace('@SLOT_CASES@','\n'.join('        '+str(i.index)+': #FRK_DiagSlot := '+str(slot)+';' for slot,i in enumerate(nodes,1)))
    text=text.replace('@NAME_CASES@','\n'.join('        '+str(i.index)+': #FRK_DiagName := '+literal(i.path)+';' for i in nodes))
    text=text.replace('@COUNT@',str(len(nodes))).replace('@CAPACITY@',str(model.registry_capacity))
    text=text.replace('@NAME_WIDTH@',str(model.core.name_width))
    for enum,members in catalog.enums.items():
        for name,value in members.items():text=text.replace('@'+enum+'.'+name+'@',str(value))
    assert '@' not in text
    sources['18_DiagnosticServices.scl']=text
    return sources,{p.relative_to(REPO).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (TEMPLATE,Path(__file__))}


def sync(t,model,owner='#',withdraw=False):
    if not any(i.type_name==t.name for i in consumers(model)):return []
    return ['    "FRK_DiagSync"(Index := '+owner+'Core.RegIndex, Withdraw := '+('TRUE' if withdraw else 'FALSE')+',',
            '        Status := '+owner+'Status, Held := '+owner+'Core.Held,',
            '        Timeout := '+('T#0ms' if withdraw or not t.timeout else owner+'ParCfg.'+t.timeout)+', ActiveTimeoutMs := '+owner+'Core.TimeoutMs);']
