"""Read only minidump metadata/exception/module streams; never copy memory."""
from pathlib import Path
import datetime,hashlib,json,struct
R=Path(__file__).parent
path=Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root/sd/RockwellAutomation/601FC87B/Faults/FaultDump.dmp')
with path.open('rb') as f:
 size=path.stat().st_size
 def read(offset,length):
  assert 0<=offset<=size and 0<=length<=1048576 and offset+length<=size
  f.seek(offset);raw=f.read(length);assert len(raw)==length;return raw
 header=read(0,32);signature,version,count,directory,checksum,stamp,flags=struct.unpack('<4sIIIIIQ',header)
 assert signature==b'MDMP' and 0<count<=128
 entries=[dict(streamType=t,bytes=n,rva=o) for t,n,o in struct.iter_unpack('<III',read(directory,12*count))]
 streams={r['streamType']:r for r in entries}
 exception=None;modules=[];architecture=None
 if 6 in streams:
  s=streams[6];raw=read(s['rva'],s['bytes']);assert len(raw)>=168
  thread=struct.unpack_from('<I',raw)[0];code,exception_flags=struct.unpack_from('<II',raw,8)
  record,address=struct.unpack_from('<QQ',raw,16);parameters=struct.unpack_from('<I',raw,32)[0];assert parameters<=15
  exception=dict(threadId=thread,code=f'0x{code:08X}',flags=exception_flags,address=f'0x{address:X}',
   parameterValues=[f'0x{x:X}' for x in struct.unpack_from('<'+'Q'*parameters,raw,40)],
   exceptionStreamSha256=hashlib.sha256(raw).hexdigest())
 if 7 in streams:architecture=struct.unpack_from('<H',read(streams[7]['rva'],2))[0]
 if 4 in streams:
  s=streams[4];raw=read(s['rva'],s['bytes']);n=struct.unpack_from('<I',raw)[0];assert n<=4096 and len(raw)>=4+108*n
  for i in range(n):
   offset=4+108*i;base,image_size,check,when,name_rva=struct.unpack_from('<QIIII',raw,offset)
   length=struct.unpack('<I',read(name_rva,4))[0];assert length<=8192 and length%2==0
   name=read(name_rva+4,length).decode('utf-16le')
   if exception and base<=address<base+image_size:
    exception.update(module=name,moduleBase=f'0x{base:X}',moduleOffset=f'0x{address-base:X}')
   modules.append(dict(name=name,base=f'0x{base:X}',bytes=image_size))
report=dict(readOnly=True,controllerChanges=0,dumpArchived=False,memoryStreamsRead=False,
 dumpPath=str(path),dumpBytes=size,dumpModifiedUtc=datetime.datetime.fromtimestamp(path.stat().st_mtime,datetime.timezone.utc).isoformat(),
 headerFlags=f'0x{flags:X}',systemProcessorArchitecture=architecture,streams=entries,exception=exception,modules=modules)
with (R/'emulator_dump_metadata_01.json').open('x') as out:json.dump(report,out,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('modules','streams')},indent=2))
