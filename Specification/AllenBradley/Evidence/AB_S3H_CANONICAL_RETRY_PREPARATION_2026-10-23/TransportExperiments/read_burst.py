"""Bounded connected read packets; one socket owner and no write service.

Uses pylogix's existing connected-session frame builder. Complete TCP frames
are joined by session/context/sequence before returning the same (status, raw)
tuples as conn.send. UDT inspection/fragment reassembly remains with the caller.
"""
import struct

MAX_PENDING=16


def _read(request):
    if not isinstance(request,bytes) or len(request)<4:raise ValueError('complete read request required')
    service,words=request[:2];end=2+words*2
    if end>len(request) or words<1:raise ValueError('read path is incomplete')
    if service in (0x4c,0x52):
        tail=2 if service==0x4c else 6
        if request[2]!=0x91 or len(request)!=end+tail or struct.unpack_from('<H',request,end)[0]!=1:
            raise ValueError('one symbolic UDT read required')
        return
    if service!=0x0a or request[2:end]!=b'\x20\x02\x24\x01':raise ValueError('only symbolic reads and read-only MSPs allowed')
    body=request[end:]
    if len(body)<4:raise ValueError('MSP read table incomplete')
    count=struct.unpack_from('<H',body)[0]
    if not 1<=count<=64 or len(body)<2+2*count:raise ValueError('MSP read count invalid')
    offsets=list(struct.unpack_from('<'+'H'*count,body,2))
    if offsets[0]!=2+2*count or offsets!=sorted(set(offsets)) or offsets[-1]>=len(body):raise ValueError('MSP offsets invalid')
    for i,start in enumerate(offsets):
        child=body[start:offsets[i+1] if i+1<count else len(body)]
        if not child or child[0]!=0x4c:raise ValueError('MSP contains a non-read service')
        _read(child)


def _key(frame):return frame[4:8],frame[12:20],frame[44:46]


def _drop(conn):
    conn.SocketConnected=False;conn._connected=False;conn._registered=False
    conn.Socket.close()


def acquire(comm,items):
    requests=[]
    for item in items:
        if item.get('kind') not in ('fragment','batch'):raise ValueError('prebuilt read packets required')
        request=item['request'];_read(request)
        if len(request)>comm.ConnectionSize:raise ValueError('read request exceeds negotiated packet size')
        requests.append(request)
    if not requests:raise ValueError('nonempty read plan required')
    conn=comm.conn
    if not conn.SocketConnected or not conn._connected:raise ValueError('prewarmed connected read session required')
    result=[]
    try:
        for start in range(0,len(requests),MAX_PENDING):
            # Echo returns zero sender context on connected responses. Send
            # that same value explicitly; session and sequence bind every
            # pending request, including out-of-order replies.
            frames=[]
            for request in requests[start:start+MAX_PENDING]:
                frame=conn._build_eip_header(request)
                frames.append(frame[:12]+b'\0'*8+frame[20:])
            keys=[_key(f) for f in frames]
            if len(set(keys))!=len(keys):raise ValueError('ambiguous connected request identity')
            expected=set(keys);replies={};buffer=bytearray()
            conn.Socket.sendall(b''.join(frames))
            while len(replies)<len(keys):
                part=conn.Socket.recv(65536)
                if not part:raise ValueError('connected read stream ended early')
                buffer.extend(part)
                if len(buffer)>MAX_PENDING*(comm.ConnectionSize+88):raise ValueError('connected read buffer exceeds bound')
                while len(buffer)>=24:
                    length=struct.unpack_from('<H',buffer,2)[0]
                    if not 26<=length<=comm.ConnectionSize+64:raise ValueError('connected response size invalid')
                    total=24+length
                    if len(buffer)<total:break
                    frame=bytes(buffer[:total]);del buffer[:total]
                    if (struct.unpack_from('<H',frame)[0]!=0x70 or frame[8:12]!=b'\0'*4 or frame[20:24]!=b'\0'*4
                            or frame[24:28]!=b'\0'*4 or struct.unpack_from('<H',frame,30)[0]!=2
                            or frame[32:36]!=b'\xa1\x00\x04\x00' or frame[40:42]!=b'\xb1\x00'
                            or struct.unpack_from('<H',frame,42)[0]+44!=len(frame)):
                        raise ValueError('connected response framing invalid')
                    key=_key(frame)
                    if key not in expected or key in replies:
                        observed=tuple(v.hex() for v in key)
                        wanted=[tuple(v.hex() for v in k) for k in keys]
                        raise ValueError(f'unknown or duplicate connected response identity: {observed}; expected {wanted}')
                    replies[key]=(frame[48],frame)
            if buffer:raise ValueError('unexpected trailing connected data')
            result.extend(replies[k] for k in keys)
    except Exception:
        _drop(conn)
        raise
    return result
