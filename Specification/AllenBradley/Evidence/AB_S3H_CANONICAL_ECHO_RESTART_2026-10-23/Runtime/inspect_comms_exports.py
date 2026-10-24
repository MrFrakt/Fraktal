"""Use the installed DLL's public PE export table for stack context only."""
from pathlib import Path
import bisect,hashlib,json,struct
R=Path(__file__).parent;stack=json.loads((R/'emulator_stack_01.json').read_text())
path=Path(stack['frames'][0]['module']);raw=path.read_bytes()
pe=struct.unpack_from('<I',raw,0x3c)[0];assert raw[pe:pe+4]==b'PE\0\0'
count=struct.unpack_from('<H',raw,pe+6)[0];optional=pe+24;opt_bytes=struct.unpack_from('<H',raw,pe+20)[0]
assert struct.unpack_from('<H',raw,optional)[0]==0x10b
sections=[]
for i in range(count):
 o=optional+opt_bytes+40*i;vsize,va,rsize,rptr=struct.unpack_from('<IIII',raw,o+8);flags=struct.unpack_from('<I',raw,o+36)[0]
 sections.append((va,max(vsize,rsize),rptr,flags))
def offset(rva):
 for va,size,pointer,flags in sections:
  if va<=rva<va+size:return pointer+rva-va
 raise ValueError('RVA outside PE sections')
def string(rva):
 o=offset(rva);end=raw.find(b'\0',o,o+4096);assert end>=0
 return raw[o:end].decode('ascii')
export_rva,export_size=struct.unpack_from('<II',raw,optional+96);exports=[]
if export_rva:
 e=offset(export_rva);functions,names,fa,na,oa=struct.unpack_from('<IIIII',raw,e+20)
 assert names<=functions<=1000000
 for i in range(names):
  nrva=struct.unpack_from('<I',raw,offset(na)+4*i)[0];ordinal=struct.unpack_from('<H',raw,offset(oa)+2*i)[0]
  rva=struct.unpack_from('<I',raw,offset(fa)+4*ordinal)[0]
  if export_rva<=rva<export_rva+export_size:continue
  if not any(va<=rva<va+size and flags&0x20000000 for va,size,pointer,flags in sections):continue
  exports.append((rva,string(nrva)))
exports.sort();addresses=[r for r,n in exports];rows=[]
for frame in stack['frames']:
 if frame.get('module')!=str(path):continue
 target=int(frame['offset'],16);i=bisect.bisect_right(addresses,target)-1
 row=dict(moduleOffset=frame['offset'])
 if i>=0:row.update(nearestPrecedingExport=exports[i][1],exportRva=f'0x{exports[i][0]:X}',distance=target-exports[i][0])
 rows.append(row)
report=dict(readOnly=True,dllPath=str(path),dllSha256=hashlib.sha256(raw).hexdigest(),namedExecutableExports=len(exports),
 note='Public export proximity is context only; it does not identify an internal function without private symbols',rows=rows)
with (R/'comms_exports_context_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report,indent=2))
