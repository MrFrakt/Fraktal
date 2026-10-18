import ctypes as c,os,time,json,struct
from pathlib import Path
w=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Press_Bench_20261017'
os.add_dll_directory('C:/Windows/System32/Npcap')
p=c.CDLL('C:/Windows/System32/Npcap/wpcap.dll')
p.pcap_open_live.argtypes=[c.c_char_p,c.c_int,c.c_int,c.c_int,c.c_char_p];p.pcap_open_live.restype=c.c_void_p
p.pcap_geterr.argtypes=[c.c_void_p];p.pcap_geterr.restype=c.c_char_p
p.pcap_compile.argtypes=[c.c_void_p,c.c_void_p,c.c_char_p,c.c_int,c.c_uint]
p.pcap_setfilter.argtypes=[c.c_void_p,c.c_void_p]
p.pcap_setnonblock.argtypes=[c.c_void_p,c.c_int,c.c_char_p]
p.pcap_next_ex.argtypes=[c.c_void_p,c.POINTER(c.c_void_p),c.POINTER(c.c_void_p)]
p.pcap_close.argtypes=[c.c_void_p]
err=c.create_string_buffer(256)
h=p.pcap_open_live(b'\\Device\\NPF_{AA4AF3A8-6D64-4895-A244-B46D27718E24}',128,0,100,err)
if not h: raise SystemExit(err.value.decode())
try:
    prog=c.create_string_buffer(32)
    filt=b'(arp and (host 192.168.0.20 or host 192.168.0.10)) or (tcp and host 192.168.0.10 and (port 24001 or port 24002))'
    if p.pcap_compile(h,prog,filt,1,0xffffffff) or p.pcap_setfilter(h,prog):raise RuntimeError(p.pcap_geterr(h))
    if p.pcap_setnonblock(h,1,err):raise RuntimeError(err.value)
    end=time.monotonic()+15;count=0
    with (w/'transport_capture01.pcap').open('xb') as f:
        f.write(struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,128,1))
        while time.monotonic()<end and count<300:
            header=c.c_void_p();data=c.c_void_p();result=p.pcap_next_ex(h,c.byref(header),c.byref(data))
            if result==0:time.sleep(.01);continue
            if result<0:raise RuntimeError(p.pcap_geterr(h))
            raw=c.string_at(header,16);sec,usec,cap,total=struct.unpack('<IIII',raw)
            packet=c.string_at(data,cap);f.write(raw+packet);count+=1
    print(json.dumps(dict(event='capture',packets=count,seconds=15,path=str(w/'transport_capture01.pcap'))))
finally:p.pcap_close(h)
