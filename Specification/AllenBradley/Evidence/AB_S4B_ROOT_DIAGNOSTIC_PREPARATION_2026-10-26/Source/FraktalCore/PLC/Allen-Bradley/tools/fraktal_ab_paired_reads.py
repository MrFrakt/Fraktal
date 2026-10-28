"""Read-only UDT batches for the migration oracle's bounded scan window.

Warm whole-tag reads supply exact response sizes. Large records retain the
native fragmented reader; small records share CIP Multiple Service Packets.
All response inspection happens after the generation proof closes.
"""
import struct
from types import SimpleNamespace


def plan(comm,tags,sizes):
    limit=comm.ConnectionSize
    if type(limit) is not int or limit<500:raise ValueError('invalid paired connection size')
    if len(set(tags))!=len(tags) or not tags:raise ValueError('unique paired tags required')
    result=[];group=[];sent=received=64
    def flush():
        nonlocal group,sent,received
        if group:
            services=[item[1] for item in group]
            offset=2+2*len(group)
            offsets=[]
            for service in services:
                offsets.append(offset);offset+=len(service)
            request=(comm._build_multi_service_header()+struct.pack('<H',len(group))+
                     struct.pack('<'+'H'*len(offsets),*offsets)+b''.join(services))
            result.append(dict(kind='batch',tags=[item[0] for item in group],request=request))
        group=[];sent=received=64
    for tag in tags:
        size=sizes[tag]
        if type(size) is not int or size<=0:raise ValueError('positive warm UDT size required')
        if size+80>limit:
            flush();result.append(dict(kind='single',tags=[tag]));continue
        service=comm._add_read_service(comm._build_ioi(tag,0xa0),1)
        if sent+len(service)+2>limit or received+size+10>limit:flush()
        if len(service)+66>limit:raise ValueError('paired tag path exceeds request budget')
        group.append((tag,service));sent+=len(service)+2;received+=size+10
    flush()
    return result


def acquire(comm,read_plan):
    return [comm.Read(item['tags'][0]) if item['kind']=='single' else comm.conn.send(item['request'])
            for item in read_plan]


def decode_batch(reply,tags,sizes):
    status,raw=reply
    if status!=0 or not isinstance(raw,bytes) or len(raw)<52:
        raise ValueError('paired multi-service reply unavailable')
    # pylogix's connected transport returns the complete encapsulation frame;
    # its single-service CIP header begins at 46, with MSP data at byte 50.
    if raw[46:50]!=b'\x8a\x00\x00\x00':raise ValueError('paired multi-service header rejected')
    data=raw[50:]
    count=struct.unpack_from('<H',data)[0]
    if count!=len(tags) or len(data)<2+2*count:raise ValueError('paired multi-service count differs')
    offsets=list(struct.unpack_from('<'+'H'*count,data,2))
    if not offsets or offsets[0]!=2+2*count or offsets!=sorted(set(offsets)) or offsets[-1]>=len(data):
        raise ValueError('invalid paired multi-service offsets')
    result={}
    for index,tag in enumerate(tags):
        segment=data[offsets[index]:(offsets[index+1] if index+1<count else len(data))]
        if len(segment)<8 or segment[:4]!=b'\xcc\x00\x00\x00' or segment[4:6]!=b'\xa0\x02':
            raise ValueError('paired UDT read failed or has unexpected type')
        value=segment[8:]
        if len(value)!=sizes[tag]:raise ValueError('paired UDT byte size differs from warmed read')
        # Preserve the first DINT. The vendor multi-read parser treats custom
        # UDTs like strings and skips it; these are raw structure payloads.
        result[tag]=SimpleNamespace(Status='Success',Value=value)
    return result


def decode(read_plan,replies,sizes):
    if len(replies)!=len(read_plan):raise ValueError('paired reply plan differs')
    result={}
    for item,reply in zip(read_plan,replies,strict=True):
        if item['kind']=='fragment':
            continue
        if item['kind']=='single':
            tag=item['tags'][0]
            if reply.Status!='Success' or not isinstance(reply.Value,(bytes,bytearray)) or len(reply.Value)!=sizes[tag]:
                raise ValueError('paired fragmented UDT read failed or changed size')
            result[tag]=reply
        else:result.update(decode_batch(reply,item['tags'],sizes))
    fragments=[(item,reply) for item,reply in zip(read_plan,replies,strict=True) if item['kind']=='fragment']
    if fragments:
        from fraktal_ab_paired_fragments import decode as decode_fragments
        decoded=decode_fragments([i for i,r in fragments],[r for i,r in fragments],sizes)
        if result.keys()&decoded.keys():raise ValueError('whole and fragmented tag plans overlap')
        result.update(decoded)
    return result
