"""Static identity and build-gate annunciation from composition declarations."""
import hashlib
from pathlib import Path

from fraktal_tia_binding import PRIVATE,READONLY,REPO,literal
from fraktal_tia_config import function

TEMPLATE=Path(__file__).resolve().parents[1]/'Framework/Core/condition_event.scl.in'


def nameplate_setup(t,model,catalog):
    declarations=dict(model.nameplates)
    if not declarations:return []
    fields={f['member']:f for f in catalog.resolve(['ST_Nameplate'])['ST_Nameplate']}
    body=[]
    for instance in model.instances:
        if instance.type_name!=t.name or instance.path not in declarations:continue
        body+=['        IF #Core.RegIndex = %d THEN'%instance.index]
        for member,value in declarations[instance.path]:
            prefix='WSTRING#' if fields[member]['native_type'].startswith('WString') else ''
            body+=['            #Nameplate.'+member+' := '+prefix+literal(value)+';']
        body+=['        END_IF;']
    return body


def gate_roots(model):
    return {r.name for r in model.roots} if model.engineering_gates else set()


def active_gates(model):return [dict(row) for row in model.engineering_gates if dict(row)['active']]


def gate_declarations(model):
    count=len(active_gates(model))
    return ['    EngineeringSlots'+PRIVATE+' : Array[1..%d] of Int;'%count] if count else []


def gate_frame():
    return ['    IF #Core.ParentIndex = 0 THEN "FRK_EngineeringTick"(Scope := #Status.Name, Slots := #EngineeringSlots, AlarmLog := #AlarmLog); END_IF;']


def build(model,catalog):
    text=TEMPLATE.read_text('ascii')
    for name,values in catalog.enums.items():
        for member,value in values.items():text=text.replace('@'+name+'.'+member+'@',str(value))
    for name,value in catalog.capacities.items():text=text.replace('@'+name+'@',str(value))
    gates=active_gates(model)
    if gates:
        body=[]
        for index,gate in enumerate(gates,1):
            body+=['    "FRK_ConditionEvent"(Active := TRUE, Reason := '+str(catalog.enums['E_Reason']['COMMISSIONING_GATE_ACTIVE'])+', Description := WSTRING#'+literal(gate['description'])+', Source := STRING_TO_WSTRING(#Scope), Slot := #Slots[%d], AlarmLog := #AlarmLog);'%index]
        text+=function('FRK_EngineeringTick',['Scope : String;'],['Slots : Array[1..%d] of Int;'%len(gates),'AlarmLog : "FRK_AlarmLog";'],[],body)
        # The register is static self-description, assembled from the same build
        # declaration as its events; no independently editable runtime mirror.
        body=[]
        values=[('Engineering/Count',str(len(gates)))]
        for index,gate in enumerate(gates,1):
            values.extend([('Engineering/Gates/%d/Name'%index,gate['name']),
                ('Engineering/Gates/%d/DescriptionKey'%index,gate['description'])])
        for item,value in values:
            body+=['    "FRK_ConfigAppend"(Scope := #Scope, Item := '+literal(item)+', ValueText := WSTRING#'+literal(value)+', ValueType := '+str(catalog.enums['E_ConfigValueType']['TEXT'])+', ReadLevel := #Access.Policy.Required[0], Readable := #Access.CurrentLevel >= #Access.Policy.Required[0], Cursor := #Cursor, Page := #Page);']
        text+=function('FRK_EngineeringManifest',['Scope : String;','Access : "FRK_Access";'],['Cursor : "FRK_ConfigCursor";','Page : "ST_ConfigPage";'],[],body)
    return {'16b_ConditionEvents.scl':text},{TEMPLATE.relative_to(REPO).as_posix():hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()}
