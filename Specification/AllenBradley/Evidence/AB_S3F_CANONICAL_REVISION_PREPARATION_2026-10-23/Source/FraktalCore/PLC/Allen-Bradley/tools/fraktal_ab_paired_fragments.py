"""Bounded raw UDT fragment packets for the migration observer's scan proof.

Only the warm-up probe is decoded before the proof. During acquisition each
connection sends its prebuilt packets; inspection/reassembly follows the
closing generation sample. Byte ranges must be complete and non-overlapping.
"""
import struct
from types import SimpleNamespace


def request(comm,tag,offset):
    path=comm._build_ioi(tag,0xa0)
    return struct.pack('<BB',0x52,len(path)//2)+path+struct.pack('<HI',1,offset)


def unpack(reply):
    status,raw=reply
    if status not in (0,6) or not isinstance(raw,bytes) or len(raw)<54:
        raise ValueError('fragment response unavailable')
    if raw[46:50]!=bytes((0xd2,0,status,0)) or raw[50:52]!=b'\xa0\x02':
        raise ValueError('fragment response header/type differs')
    return status,raw[50:54],raw[54:]


def packets(comm,tag,size):
    status,kind,raw=unpack(comm.conn.send(request(comm,tag,0)))
    chunk=len(raw)
    if not chunk or chunk>size or status!=(0 if chunk==size else 6):
        raise ValueError('fragment warm-up size/status differs')
    return [dict(kind='fragment',tags=[tag],offset=offset,length=min(chunk,size-offset),
                 total=size,nativeTypeHex=kind.hex(),request=request(comm,tag,offset))
            for offset in range(0,size,chunk)]


def partition(comm,tags,sizes):
    import fraktal_ab_paired_reads as batching
    large=[t for t in tags if sizes[t]+80>comm.ConnectionSize]
    small=[t for t in tags if t not in large]
    items=[p for t in large for p in packets(comm,t,sizes[t])]
    if small:items.extend(batching.plan(comm,small,sizes))
    # Every item is one bounded wire request, including MSPs. Balance packet
    # counts, rather than assigning a whole large record to one connection.
    return items[::2],items[1::2]


def decode(items,replies,sizes):
    if len(items)!=len(replies):raise ValueError('fragment reply plan differs')
    parts={}
    for item,reply in zip(items,replies,strict=True):
        tag=item['tags'][0];status,kind,raw=unpack(reply)
        if (len(raw)!=item['length'] or kind.hex()!=item['nativeTypeHex'] or item['total']!=sizes[tag]
                or status!=(0 if item['offset']+len(raw)==item['total'] else 6)):
            raise ValueError('fragment byte count/type/status differs from plan')
        parts.setdefault(tag,[]).append((item['offset'],raw))
    result={}
    for tag,rows in parts.items():
        position=0;payload=[]
        for offset,raw in sorted(rows):
            if offset!=position:raise ValueError('fragment range has a gap or overlap')
            position+=len(raw);payload.append(raw)
        if position!=sizes[tag]:raise ValueError('fragment range does not cover full UDT')
        result[tag]=SimpleNamespace(Status='Success',Value=b''.join(payload))
    return result
