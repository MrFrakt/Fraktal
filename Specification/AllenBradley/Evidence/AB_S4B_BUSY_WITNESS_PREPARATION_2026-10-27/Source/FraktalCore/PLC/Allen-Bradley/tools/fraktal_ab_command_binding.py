"""V6.6 command metadata: schema discovery never samples argument values.

This module is client-side protocol code. It imports no station declaration or
generator. Native offsets, StringFamily widths and BOOL storage come from the
controller Templates; the PLC supplies every endpoint and connection bound.
"""
import re
import struct
from dataclasses import dataclass,field

VERSION = 1
ROLE = 'CommandOnly'
FIELD = frozenset(('Version','RootSymbol','PayloadSymbol','ArgumentsMember',
                   'CommitSymbol','ResponseSymbol','StatusSymbol','ConnectionBytes','MaximumPayloadBytes','ReadRole',
                   'CapabilitiesSymbol','CapabilitiesCount','KeysSymbol','KeysCount'))
TEXT_FIELDS = frozenset(('RootSymbol','PayloadSymbol','ArgumentsMember','CommitSymbol','ResponseSymbol','StatusSymbol','ReadRole',
                         'CapabilitiesSymbol','KeysSymbol'))
ARGUMENTS = ('Kind','TargetPath','NameValue','TextValue','User','Secret','IntValue','BoolValue','DurationMs')
WIDTHS = dict(TargetPath=255,NameValue=160,TextValue=255,User=32,Secret=32)
IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,39}\Z')
HEADER = ('SchemaVersion','ManifestRevision','StagedSequence')
OPERATION_FIELD=frozenset(('Kind','Supported','RequiresSetStage','RefusalKey'))


def operations(rows):
    if not isinstance(rows,list) or len(rows)!=39:
        raise ValueError('Core V1 command operation inventory must contain all 39 kinds')
    for kind,row in enumerate(rows):
        if not isinstance(row,dict) or set(row)!=OPERATION_FIELD or type(row['Kind']) is not int or row['Kind']!=kind \
                or type(row['Supported']) is not bool or type(row['RequiresSetStage']) is not bool \
                or not isinstance(row['RefusalKey'],str) or len(row['RefusalKey'].encode())>255 \
                or bool(row['RefusalKey'])==row['Supported'] or (row['RequiresSetStage'] and not row['Supported']):
            raise ValueError('invalid, duplicate or incomplete command operation descriptor')
    return rows


def bindings(rows):
    if not isinstance(rows,list) or not 1<=len(rows)<=1024:
        raise ValueError('invalid command binding table')
    roots=set();endpoints=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)!=FIELD:
            raise ValueError('invalid command binding descriptor')
        if any(type(row[k]) is not int for k in FIELD-TEXT_FIELDS) \
                or row['Version']!=VERSION or row['ReadRole']!=ROLE \
                or not 500<=row['ConnectionBytes']<=4000 \
                or not 1<=row['MaximumPayloadBytes']<=row['ConnectionBytes']-256:
            raise ValueError('unsupported command profile or connection bound')
        if type(row['CapabilitiesCount']) is not int or not 0<=row['CapabilitiesCount']<=100000 \
                or type(row['KeysCount']) is not int or not 1<=row['KeysCount']<=100000:
            raise ValueError('invalid command side-table bounds')
        names=TEXT_FIELDS-{'ReadRole'}-({'CapabilitiesSymbol'} if not row['CapabilitiesCount'] else set())
        if any(not isinstance(row[k],str) or not IDENTIFIER.fullmatch(row[k]) for k in names) \
                or (not row['CapabilitiesCount'] and row['CapabilitiesSymbol']!=''):
            raise ValueError('invalid command endpoint/member identifier')
        symbols=[row[k] for k in ('PayloadSymbol','CommitSymbol','ResponseSymbol')]
        if row['RootSymbol'] in roots or len(set(symbols))!=3 or set(symbols)&endpoints or row['RootSymbol'] in symbols:
            raise ValueError('duplicate command root or endpoint')
        roots.add(row['RootSymbol']);endpoints.update(symbols)
    return rows


def schema(row, symbols, objects, sizes, member_table, is_string):
    """Validate a command-only Template and return its argument handle.

    No byte record or decoder is accepted here. Commands and the separately
    readable reply are deliberately outside cyclic records.
    """
    def structured(name):
        symbol=symbols.get(name)
        if not symbol or symbol.get('arrayRank',0) or symbol.get('handle') not in objects:
            raise ValueError('command structured Symbol unavailable: '+name)
        handle=symbol['handle']
        if is_string(member_table(objects[handle])) is not None:
            raise ValueError('command endpoint must be structured')
        return handle,{m['name']:m for m in member_table(objects[handle])}
    def layout(handle,stack=()):
        if handle in stack or len(stack)>64:raise ValueError('command Template cycle/depth exceeds budget')
        intervals=[]
        for m in member_table(objects[handle]):
            if m['name'].startswith('ZZZZZZZZZZ'):continue
            if m['array']:raise ValueError('command record contains an unexpected array')
            start=m['offset']
            if m['struct']:
                child=m['handle']
                if child not in objects:raise ValueError('command child Template unavailable')
                width=is_string(member_table(objects[child]))
                if width is None:layout(child,(*stack,handle))
                else:
                    parts={r['name']:r for r in member_table(objects[child])}
                    if parts['LEN']['offset']+4>sizes[child] or parts['DATA']['offset']+width>sizes[child]:
                        raise ValueError('command StringFamily exceeds its Template')
                end=start+sizes[child]
            elif m['atomic']==0xc1:
                start+=m['info']//8;end=start+1
            elif m['atomic']==0xc4:end=start+4
            else:raise ValueError('unexpected command native field')
            if start<0 or end>sizes[handle] or any(start<b and a<end for a,b in intervals):
                raise ValueError('command fields overlap or exceed their Template')
            intervals.append((start,end))
    handle,outer=structured(row['PayloadSymbol'])
    if set(outer)!={*HEADER,row['ArgumentsMember']} or sizes[handle]>row['MaximumPayloadBytes']:
        raise ValueError('command payload layout or size bound differs')
    layout(handle)
    for name in HEADER:
        m=outer[name]
        if m['struct'] or m['array'] or m['atomic']!=0xC4:
            raise ValueError('command envelope requires three DINT fields')
    args=outer[row['ArgumentsMember']]
    if not args['struct'] or args['array'] or args['handle'] not in objects:
        raise ValueError('command arguments must be a structured scalar')
    members={m['name']:m for m in member_table(objects[args['handle']]) if not m['name'].startswith('ZZZZZZZZZZ')}
    if set(members)!=set(ARGUMENTS):raise ValueError('Core command argument set differs')
    for name,m in members.items():
        if m['array']:raise ValueError('command argument is an array')
        if name in WIDTHS:
            string=is_string(member_table(objects[m['handle']])) if m['struct'] and m['handle'] in objects else None
            if string!=WIDTHS[name]:raise ValueError('Core command string width differs: '+name)
        elif m['struct'] or m['atomic']!=(0xC1 if name=='BoolValue' else 0xC4):
            raise ValueError('Core command native scalar type differs: '+name)
    commit=symbols.get(row['CommitSymbol'])
    # Atomic Symbols are retained by discovery even though they have no Template.
    if not commit or commit.get('arrayRank',0) or commit.get('atomic')!=0xC4:
        raise ValueError('command commit must be a DINT scalar Symbol')
    unused,status=structured(row['StatusSymbol'])
    seed=status.get('CoreSerial')
    if not seed or seed['struct'] or seed['array'] or seed['atomic']!=0xC4:
        raise ValueError('command status lacks its DINT sequence seed')
    response_handle,unused=structured(row['ResponseSymbol'])
    unused,root=structured(row['RootSymbol'])
    response=root.get('HmiResponse')
    if not response or not response['struct'] or response['array'] or response['handle']!=response_handle:
        raise ValueError('command reply differs from the root Core response')
    for name,count,required in [('KeysSymbol',row['KeysCount'],('NumericKey','PortableKey')),
                               ('CapabilitiesSymbol',row['CapabilitiesCount'],('CapabilityIndex','WriteKeyKey','ConfigKind'))]:
        if not count:continue
        symbol=symbols.get(row[name])
        if not symbol or symbol.get('arrayRank')!=1 or symbol.get('handle') not in objects:
            raise ValueError('command side-table Symbol unavailable')
        members={m['name']:m for m in member_table(objects[symbol['handle']])}
        if not set(required)<=set(members):raise ValueError('command side-table shape differs')
    return args['handle']


@dataclass(frozen=True)
class WritePlan:
    """Transient write bytes must not appear in logs, repr or capture files."""
    payload_symbol:str
    commit_symbol:str
    payload_bytes:int
    payload_request:bytes=field(repr=False)
    commit_request:bytes=field(repr=False)


def _path(name):
    if not isinstance(name,str) or not IDENTIFIER.fullmatch(name):raise ValueError('invalid command Symbol')
    raw=name.encode('ascii')
    return bytes((0x91,len(raw)))+raw+(b'\0' if len(raw)%2 else b'')


def write_plan(capture,descriptor,arguments,sequence,*,connection_bytes):
    """Encode one 0x4D structure write and the separate final DINT commit.

    Pure protocol code: no network write and no station-specific transforms.
    Attribute 1 supplies the structure CRC; an instance ID is not a CRC.
    All padding and unused string bytes start at zero.
    """
    from fraktal_ab_canonical_reader import snapshot,template_objects,member_table,is_string
    snapshot(capture)  # validates manifest, Templates, roles and absence of input records
    bindings([descriptor])
    if descriptor not in capture['manifest']['commandBindings']:raise ValueError('unnegotiated command binding')
    if type(connection_bytes) is not int or connection_bytes<descriptor['ConnectionBytes']:
        raise ValueError('command connection is below the PLC-published minimum')
    if not isinstance(arguments,dict) or set(arguments)!=set(ARGUMENTS):raise ValueError('complete Core argument set required')
    if type(sequence) is not int or not 0<=sequence<=0xffffffff:raise ValueError('sequence is not UInt32')
    objects,sizes=template_objects(capture['templates']);symbols={s['name']:s for s in capture['symbols']}
    args_handle=schema(descriptor,symbols,objects,sizes,member_table,is_string)
    handle=symbols[descriptor['PayloadSymbol']]['handle']
    template=next(t for t in capture['templates'] if t['handle']==handle)
    crc=template.get('structureHandle')
    if type(crc) is not int or not 0<=crc<=0xffff:raise ValueError('Template attribute 1 structure handle unavailable')
    members={m['name']:m for m in member_table(objects[handle])}
    data=bytearray(sizes[handle])
    for name,value in [('SchemaVersion',VERSION),('ManifestRevision',capture['manifest']['configRevision']),('StagedSequence',sequence)]:
        struct.pack_into('<I',data,members[name]['offset'],value&0xffffffff)
    base=members[descriptor['ArgumentsMember']]['offset']
    for row in member_table(objects[args_handle]):
        name=row['name']
        if name.startswith('ZZZZZZZZZZ'):continue
        value=arguments[name];at=base+row['offset']
        if name in WIDTHS:
            if not isinstance(value,str):raise ValueError('command text requires a string')
            raw=value.encode('utf-8')
            if len(raw)>WIDTHS[name] or b'\0' in raw:raise ValueError('command text exceeds native width or contains NUL')
            string={m['name']:m for m in member_table(objects[row['handle']])}
            struct.pack_into('<i',data,at+string['LEN']['offset'],len(raw))
            start=at+string['DATA']['offset'];data[start:start+len(raw)]=raw
        elif name=='BoolValue':
            if type(value) is not bool:raise ValueError('Core BoolValue requires BOOL')
            if value:data[at+row['info']//8]|=1<<(row['info']%8)
        else:
            lower,upper=(0,0xffffffff) if name=='DurationMs' else (-(1<<31),(1<<31)-1)
            if type(value) is not int or not lower<=value<=upper:raise ValueError('command scalar is out of its Core range')
            struct.pack_into('<I',data,at,value&0xffffffff)
    path=_path(descriptor['PayloadSymbol'])
    payload=bytes((0x4d,len(path)//2))+path+struct.pack('<HHH',0x02a0,crc,1)+data
    path=_path(descriptor['CommitSymbol'])
    commit=bytes((0x4d,len(path)//2))+path+struct.pack('<HHI',0xc4,1,sequence)
    # A conservative connected-message allowance, including CPF and sequence.
    if len(payload)+110>connection_bytes or len(commit)+110>connection_bytes:
        raise ValueError('command does not fit one connected Write Tag request')
    return WritePlan(descriptor['PayloadSymbol'],descriptor['CommitSymbol'],len(data),payload,commit)
