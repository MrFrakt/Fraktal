"""Read x86 frame-chain control addresses only; never export dump memory."""
from pathlib import Path
import json,struct
R=Path(__file__).parent;m=json.loads((R/'emulator_dump_metadata_01.json').read_text())
path=Path(m['dumpPath']);streams={s['streamType']:s for s in m['streams']}
assert m['systemProcessorArchitecture']==0
with path.open('rb') as f:
 def read(offset,length):
  assert 0<=offset and 0<=length<=1048576 and offset+length<=path.stat().st_size
  f.seek(offset);raw=f.read(length);assert len(raw)==length;return raw
 e=streams[6];raw=read(e['rva'],e['bytes']);thread=struct.unpack_from('<I',raw)[0]
 context_size,context_rva=struct.unpack_from('<II',raw,160);context=read(context_rva,context_size)
 assert len(context)>=204
 ebp,eip=struct.unpack_from('<II',context,180);esp=struct.unpack_from('<I',context,196)[0]
 s=streams[3];threads=read(s['rva'],s['bytes']);n=struct.unpack_from('<I',threads)[0]
 stack_start=stack_end=None
 for i in range(n):
  row=4+48*i
  if struct.unpack_from('<I',threads,row)[0]==thread:
   stack_start=struct.unpack_from('<Q',threads,row+24)[0]&0xffffffff
   stack_bytes=struct.unpack_from('<I',threads,row+32)[0];stack_end=stack_start+stack_bytes
   break
 assert stack_start is not None and stack_start<=esp<stack_end
 memory=[]
 if 9 in streams:
  s=streams[9];raw=read(s['rva'],s['bytes']);count,offset=struct.unpack_from('<QQ',raw)
  assert count<=65536 and len(raw)>=16+16*count
  for i in range(count):
   base,length=struct.unpack_from('<QQ',raw,16+16*i)
   memory.append((base&0xffffffff,length,offset));offset+=length
 elif 5 in streams:
  s=streams[5];raw=read(s['rva'],s['bytes']);count=struct.unpack_from('<I',raw)[0]
  for i in range(count):
   base,length,offset=struct.unpack_from('<QII',raw,4+16*i);memory.append((base&0xffffffff,length,offset))
 else:raise ValueError('no address map for frame-chain reads')
 def control_words(address):
  if not stack_start<=address<=stack_end-8:raise ValueError('frame outside recorded fault-thread stack')
  for base,length,offset in memory:
   if base<=address and address+8<=base+length:return struct.unpack('<II',read(offset+address-base,8))
  raise ValueError('frame address absent from dump map')
 def frame(address):
  row=dict(address=f'0x{address:08X}')
  for mod in m['modules']:
   base=int(mod['base'],16)&0xffffffff
   if base<=address<base+mod['bytes']:
    row.update(module=mod['name'],offset=f'0x{address-base:X}');break
  return row
 frames=[frame(eip)];cursor=ebp;reason='frame limit'
 for _ in range(64):
  try:next_frame,return_address=control_words(cursor)
  except ValueError as error:reason=str(error);break
  if not return_address:reason='zero return address';break
  frames.append(frame(return_address))
  if next_frame<=cursor:reason='nonincreasing frame chain';break
  cursor=next_frame
report=dict(readOnly=True,controllerChanges=0,dumpArchived=False,onlyFrameChainControlAddressesRead=True,
 threadId=thread,stackStart=f'0x{stack_start:X}',stackEnd=f'0x{stack_end:X}',frames=frames,stopReason=reason,
 qualification='x86 EBP-chain walk without private vendor symbols; optimizer/frame omission may truncate the chain')
with (R/'emulator_stack_01.json').open('x') as out:json.dump(report,out,indent=2)
print(json.dumps(report,indent=2))
