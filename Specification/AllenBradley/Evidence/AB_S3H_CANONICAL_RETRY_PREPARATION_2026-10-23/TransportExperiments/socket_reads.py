"""One owner multiplexes four prewarmed sockets, one pending read per socket."""
import select
import struct
import time


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


def _response(frame,request,limit):
    if (len(frame)<50 or struct.unpack_from('<H',frame)[0]!=0x70 or frame[8:12]!=b'\0'*4 or frame[20:24]!=b'\0'*4
            or frame[24:28]!=b'\0'*4 or struct.unpack_from('<H',frame,30)[0]!=2
            or frame[32:36]!=b'\xa1\x00\x04\x00' or frame[40:42]!=b'\xb1\x00'
            or struct.unpack_from('<H',frame,42)[0]+44!=len(frame) or _key(frame)!=_key(request)):
        raise ValueError('connected read response identity/framing invalid')
    return frame[48],frame


def acquire(channels,plans):
    if not 2<=len(channels)<=4 or len(channels)!=len(plans) or len({id(c.conn.Socket) for c in channels})!=len(channels):
        raise ValueError('two to four distinct connected socket owners required')
    for c,plan in zip(channels,plans,strict=True):
        if not plan or not c.conn.SocketConnected or not c.conn._connected:raise ValueError('nonempty prewarmed read plans required')
        for item in plan:
            if item.get('kind') not in ('fragment','batch'):raise ValueError('prebuilt read packets required')
            _read(item['request'])
            if len(item['request'])>c.ConnectionSize:raise ValueError('read request exceeds negotiated size')
    states=[]
    def next_request(s):
        frame=s['comm'].conn._build_eip_header(s['plan'][s['index']]['request'])
        # Echo returns zero connected sender context. Send the same value;
        # every reply still has to match its exact session and sequence.
        s.update(tx=frame[:12]+b'\0'*8+frame[20:],sent=0,rx=bytearray(),total=None)
    try:
        for c,plan in zip(channels,plans,strict=True):
            sock=c.conn.Socket;s=dict(comm=c,sock=sock,timeout=sock.gettimeout(),plan=plan,index=0,replies=[])
            states.append(s);sock.setblocking(False);next_request(s)
        timeout=min(s['timeout'] if s['timeout'] is not None else 10.0 for s in states)
        deadline=time.monotonic()+timeout
        while any(s['index']<len(s['plan']) for s in states):
            active={s['sock']:s for s in states if s['index']<len(s['plan'])}
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('connected read socket deadline elapsed')
            waiting=[sock for sock,s in active.items() if s['sent']==len(s['tx'])]
            sending=[sock for sock,s in active.items() if s['sent']<len(s['tx'])]
            readable,writable,errors=select.select(waiting,sending,list(active),remaining)
            if errors:raise OSError('connected read socket failed')
            for sock in writable:
                s=active[sock]
                try:sent=sock.send(s['tx'][s['sent']:])
                except BlockingIOError:continue
                if sent<=0:raise OSError('connected read send ended early')
                s['sent']+=sent
            for sock in readable:
                s=active[sock]
                try:part=sock.recv(s['comm'].ConnectionSize+88)
                except BlockingIOError:continue
                if not part:raise OSError('connected read stream ended early')
                s['rx'].extend(part)
                if len(s['rx'])>s['comm'].ConnectionSize+88:raise ValueError('connected read buffer exceeds bound')
                if s['total'] is None and len(s['rx'])>=24:
                    length=struct.unpack_from('<H',s['rx'],2)[0]
                    if not 26<=length<=s['comm'].ConnectionSize+64:raise ValueError('connected read response size invalid')
                    s['total']=24+length
                if s['total'] is not None:
                    if len(s['rx'])>s['total']:raise ValueError('unexpected trailing connected data')
                    if len(s['rx'])==s['total']:
                        s['replies'].append(_response(bytes(s['rx']),s['tx'],s['comm'].ConnectionSize))
                        s['index']+=1
                        if s['index']<len(s['plan']):next_request(s)
        for s in states:s['sock'].settimeout(s['timeout'])
        return [s['replies'] for s in states]
    except Exception:
        for c in channels:
            c.conn.SocketConnected=False;c.conn._connected=False;c.conn._registered=False;c.conn.Socket.close()
        raise
