"""Optional retained event outbox; transport policy is a binding-owned extension."""
import json
from pathlib import Path
from fraktal_tia_binding import PRIVATE, READONLY, type_source
from fraktal_tia_alarms import expand

HERE=Path(__file__).resolve().parents[1]/'Framework/Core'
TEMPLATE=HERE/'event_delivery.scl.in'
POLICY=HERE/'event_delivery.json'

def fields(name, items, public=False):
    return type_source(name,[dict(member=n,native_type=t,accessible=public,initial='') for n,t in items])

def build(catalog):
    from fraktal_tia_generate import db
    sources={
        '02_FRK_DeliveryEntry.udt':fields('FRK_DeliveryEntry',[('Sequence','UDInt'),('Ev','"ST_AlarmEvent"'),('Checksum','DWord')]),
        '02_FRK_DeliveryAnchor.udt':fields('FRK_DeliveryAnchor',[('SchemaVersion','UInt'),('Scope','String[@NAME_WIDTH@]'),('StreamId','String[36]'),('Epoch','UDInt'),('Checksum','DWord')]),
        '02_FRK_DeliveryImage.udt':fields('FRK_DeliveryImage',[('SchemaVersion','UInt'),('Epoch','UDInt'),('Revision','UDInt'),('NextSequence','UDInt'),('Head','Int'),('Count','Int'),('Overflow','Bool'),('Dropped','UDInt'),('Checksum','DWord'),('Entries','Array[1..@DELIVERY_CAPACITY@] of "FRK_DeliveryEntry"')]),
        '02_FRK_DeliveryView.udt':fields('FRK_DeliveryView',[('SchemaVersion','UInt'),('Scope','String[@NAME_WIDTH@]'),('StreamId','String[36]'),('Epoch','UDInt'),('Capacity','Int'),('Pending','Int'),('Overflow','Bool'),('Dropped','UDInt'),('RestoreLost','Bool'),('AnchorValid','Bool'),('Token','String[160]'),('Checksum','UDInt'),('Ev','"ST_AlarmEvent"')],True),
        '02_FRK_DeliveryReceipt.udt':fields('FRK_DeliveryReceipt',[('SchemaVersion','UInt'),('TargetPath','String[@NAME_WIDTH@]'),('Token','String[160]'),('Checksum','UDInt'),('DiscardLost','Bool'),('Epoch','UDInt'),('StreamId','String[36]'),('Sequence','UDInt')],True),
        '02_FRK_DeliveryResponse.udt':fields('FRK_DeliveryResponse',[('SchemaVersion','UInt'),('AckSequence','UDInt'),('Accepted','Bool')],True),
    }
    sources['05_FRK_EventDeliveryStore.db']=db('FRK_EventDeliveryStore',[
        'Anchors'+PRIVATE+' : Array[1..@DELIVERY_COUNT@] of "FRK_DeliveryAnchor";',
        'Images'+PRIVATE+' : Array[1..@DELIVERY_COUNT@] of "FRK_DeliveryImage";',
        'Commissioned'+PRIVATE+' : Array[1..@DELIVERY_COUNT@] of Bool;']).replace('VAR\n','VAR RETAIN\n',1)
    sources['05_FRK_EventDeliveryRuntime.db']=db('FRK_EventDeliveryRuntime',[
        'Valid'+PRIVATE+' : Array[1..@DELIVERY_COUNT@] of Bool;',
        'AnchorValid'+PRIVATE+' : Array[1..@DELIVERY_COUNT@] of Bool;',
        'SeenReceipt'+PRIVATE+' : Array[1..@DELIVERY_ROOT_COUNT@] of UDInt;',
        'PublishedRevision'+PRIVATE+' : Array[1..@DELIVERY_COUNT@] of UDInt;'])
    sources['05_FRK_EventDeliveryView.db']=db('FRK_EventDeliveryView',[
        'Count'+READONLY+' : Int := @DELIVERY_COUNT@;',
        'Rows'+READONLY+' : Array[1..@DELIVERY_COUNT@] of "FRK_DeliveryView";'])
    sources['05_FRK_EventDeliveryReceipt.db']=db('FRK_EventDeliveryReceipt',[
        'Count'+READONLY+' : Int := @DELIVERY_ROOT_COUNT@;',
        'Roots'+READONLY+' : Array[1..@DELIVERY_ROOT_COUNT@] of String[@NAME_WIDTH@];',
        'Request : Array[1..@DELIVERY_ROOT_COUNT@] of "FRK_DeliveryReceipt";',
        'Response'+READONLY+' : Array[1..@DELIVERY_ROOT_COUNT@] of "FRK_DeliveryResponse";'])
    text=expand(TEMPLATE,catalog)
    header=[]
    for name,kind in [('Epoch','UDInt'),('Revision','UDInt'),('NextSequence','UDInt'),('Head','Int'),('Count','Int'),('Overflow','Bool'),('Dropped','UDInt')]:
        value='"FRK_EventDeliveryStore".Images[#Slot].'+name
        if kind=='Int':value='INT_TO_UDINT('+value+')'
        if kind=='Bool':value='BOOL_TO_UDINT('+value+')'
        header.append('    #Work := "FRK_CrcNumber"(Previous := #Work, Value := '+value+');')
    text=text.replace('@DELIVERY_HEADER_FIELDS@','\n'.join(header))
    policy=json.loads(POLICY.read_bytes())
    text=text.replace('@DELIVERY_MINIMUM@',str(catalog.enums['E_AccessLevel'][policy['minimum_access']]))
    for name,value in policy['request_kinds'].items():text=text.replace('@'+name+'@',str(value))
    for name,value in policy['restore_loss'].items():
        if name in ('severity','category','reset_class'):value=catalog.enums[{'severity':'E_Severity','category':'E_Category','reset_class':'E_ResetClass'}[name]][value]
        text=text.replace('@DELIVERY_LOST_'+name.upper()+'@',str(value))
    return sources,text,''
