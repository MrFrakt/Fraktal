"""Generic, guarded provider-response transport; no station/declaration imports.

The caller owns the authorized mailbox transaction and medium I/O. This module
discovers its symbols and validates the exact negotiated native template before
writing the common V1 frame. It does not render configuration or decide access.
"""
import time
from fraktal_ab_canonical_reader import read_document,decode_record
from fraktal_ab_config_provider_wire import VERSION,SERVICE_KIND,layout,payload


def binding(capture):
    services=[s for s in capture['manifest'].get('services',[]) if s['Kind']==SERVICE_KIND]
    if len(services)!=1 or services[0]['Version']!=VERSION:raise ValueError('store-response service unavailable')
    service=services[0];templates={t['handle']:t for t in capture['templates']}
    symbols={s['name']:s for s in capture['symbols']}
    request=symbols.get(service['RequestSymbol']);answer=symbols.get(service['ResponseSymbol'])
    if not request or not answer:raise ValueError('store-response symbols unavailable')
    member=next((m for m in templates[request['handle']]['members'] if m['name']==service['RequestMember']),None)
    if not member or not member.get('struct') or member.get('array'):raise ValueError('store-response frame is not scalar structure')
    frame=templates[member['handle']]
    expected=dict(layout());actual={m['name']:m for m in frame['members']}
    if set(actual)!=set(expected):raise ValueError('store-response template differs from V1')
    for name,count in expected.items():
        m=actual[name]
        if m.get('struct') or m['atomic']!=0xC4 or m['info']!=count or bool(m.get('array'))!=bool(count):
            raise ValueError('store-response native field type/extent differs from V1')
    return service,answer


def write_plan(service,packet):
    expected=dict(layout())
    if set(packet)!=set(expected):raise ValueError('store-response payload fields differ from V1')
    prefix=service['RequestSymbol']+'.'+service['RequestMember']
    planned=[(prefix+'.Commit',0)]
    for name,count in expected.items():
        if name=='Commit':continue
        value=packet[name];items=value if count else [value]
        if count and (not isinstance(value,list) or len(value)!=count):raise ValueError('store-response array extent')
        if any(type(v) is not int or not -(1<<31)<=v<1<<31 for v in items):raise ValueError('store-response requires exact DINT values')
        if count:
            # Fixed upper bound fits a standard 500-byte connected request.
            for start in range(0,count,80):planned.append((f'{prefix}.{name}[{start}]',items[start:start+80]))
        else:planned.append((prefix+'.'+name,value))
    if type(packet['Commit']) is not int or not 1<=packet['Commit']<=2147483646:
        raise ValueError('store-response commit outside V1')
    return planned+[(prefix+'.Commit',packet['Commit'])]


def publish(comm,*,expect_serial,root,request_sequence,operation,headers=None,document=None,
            document_line=0,document_lines=0,reject_scope='',reject_key=''):
    document_state,capture=read_document(comm,expect_serial=expect_serial)
    service,answer=binding(capture)
    response=comm.Read(service['ResponseSymbol'])
    if response.Status!='Success' or not isinstance(response.Value,(bytes,bytearray)):
        raise ValueError('store-response acknowledgement read failed')
    prior=decode_record(bytes(response.Value),answer['handle'],capture['templates'])
    sequence=prior['AckSequence']+1
    if sequence>2147483646:sequence=1
    packet=payload(sequence=sequence,request_sequence=request_sequence&0xffffffff,
        login_sequence=document_state['values'][root+'/Access/LoginResultSequence'],
        build_revision=service['BuildRevision'],operation=operation,headers=headers,document=document,
        document_line=document_line,document_lines=document_lines,reject_scope=reject_scope,reject_key=reject_key)
    plan=write_plan(service,packet)
    # Read-only discovery can take time: repeat the exact pin immediately
    # before beginning the caller's one bounded, serialized write transaction.
    identity=comm.GetDeviceProperties()
    if identity.Status!='Success' or identity.Value is None or int(str(identity.Value.SerialNumber),0)!=int(expect_serial,16):
        raise ValueError('store-response exact serial guard failed')
    for target,value in plan:
        result=comm.Write(target,value)
        if result.Status!='Success':raise ValueError('store-response payload interrupted before commit')
    deadline=time.monotonic()+6
    while time.monotonic()<deadline:
        response=comm.Read(service['ResponseSymbol'])
        if response.Status=='Success' and isinstance(response.Value,(bytes,bytearray)):
            result=decode_record(bytes(response.Value),answer['handle'],capture['templates'])
            if result['AckSequence']==sequence:
                if not result['Accepted']:raise ValueError('controller refused store response')
                return dict(accepted=True,sequence=sequence,requestSequence=request_sequence&0xffffffff)
        time.sleep(.01)
    raise TimeoutError('store-response acknowledgement timed out; outcome unknown')
