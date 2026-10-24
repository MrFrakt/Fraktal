"""Offline inventory from the frozen oracle and owning Core declarations."""
from pathlib import Path
import collections,datetime,gzip,hashlib,json,re,struct,sys,xml.etree.ElementTree as ET
ROOT=Path('C:/Users/SoftIndVM/Fraktal');G=Path(__file__).parent
CORE=ROOT/'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core';TOOLS=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0,str(TOOLS))
import fraktal_ab_genealogy_s3f_demo as demo
import fraktal_ab_generate as gen
app=demo.application();assert app.canonical_publication_stage==8
sha=lambda raw:hashlib.sha256(raw).hexdigest()
capture_path=TOOLS/'fixtures/canonical/genealogy_projection_01.json.gz';raw=gzip.decompress(capture_path.read_bytes());capture=json.loads(raw)
previous_path=ROOT/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S3F_INVENTORY_2026-10-22.json'
previous=json.loads(previous_path.read_text());prior=set(previous['paths'])
assert previous['cumulativeLegacyPaths']==2955
decls={};used=set()
for path in [*CORE.joinpath('DUTs').glob('*.TcDUT'),CORE/'BaseClasses/FB_CycleProfiler.TcPOU',CORE/'BaseClasses/FB_UnitBase.TcPOU']:
 root=ET.parse(path).getroot();node=root.find('DUT')
 if node is None:node=root.find('POU')
 if node is None:continue
 declaration=node.findtext('Declaration');text=re.sub(r'//[^\n]*','',declaration)
 members={m[1]:m[2].strip() for m in re.finditer(r'\b(\w+)\s*:\s*(ARRAY\s*\[[^\]]+\]\s*OF\s+\w+|\w+(?:\([^)]*\))?)\s*(?::=[^;]*)?;',text,re.I)}
 decls[node.get('Name')]=(members,path)
roots={'Oee':'ST_Oee','OeeTrend':'ST_OeeSample','OeeTrendHead':'INT','Profiler':'FB_CycleProfiler','SystemHealth':'ST_SystemHealthStatus'}
for name in ('Oee','OeeTrendHead','Profiler'):assert decls['FB_UnitBase'][0][name]==roots[name]
params_path=CORE/'Params/PL_Fraktal.TcGVL';params=params_path.read_text(encoding='utf-8')
for name,native in (('MAX_PROFILE_STEPS',gen.PROFILE_STEPS),('MAX_CYCLE_HISTORY',gen.CYCLE_HISTORY),('MAX_OEE_SAMPLES',gen.OEE_SAMPLES)):
 assert int(re.search(r'\b'+name+r'\s*:\s*INT\s*:=\s*(\d+)',params)[1])==native
primitive={'BOOL':'Boolean','SINT':'Int8','INT':'Int16','DINT':'Int32','UDINT':'UInt32','UINT':'UInt16','LINT':'Int64','REAL':'Float','LREAL':'Double','TIME':'Int32','DT':'DateTime','LDT':'DateTime'}
def core_type(path):
 parts=path.split('/')[1:];name=re.sub(r'\[.*','',parts[0]);kind=roots[name];owners=[]
 for part in parts[1:]:
  member=re.sub(r'\[.*','',part);members,source=decls[kind];used.add(source);owners.append(source.relative_to(ROOT).as_posix())
  assert member in members,(path,kind,member)
  kind=members[member]
  if kind.startswith('ARRAY'):kind=re.search(r'OF\s+(\w+)',kind)[1]
 if kind.startswith('STRING'):result='String'
 elif kind.startswith('E_'):result='Int32'
 else:result=primitive[kind]
 return kind,result,list(dict.fromkeys(owners))
def legacy_type(v):return 'Boolean' if type(v) is bool else 'String' if type(v) is str else 'Double' if type(v) is float else 'Int32' if type(v) is int else 'UNSUPPORTED'
paths={};counts=collections.Counter();changes=collections.Counter()
for path,value in sorted(capture['values'].items()):
 segment=path.split('/')[1];surface=re.sub(r'\[.*','',segment)
 if surface not in roots:continue
 assert path not in prior,path
 kind,target,owners=core_type(path);old=legacy_type(value)
 paths[path]=dict(value=value,legacyType=old,coreDeclarationType=kind,proposedCoreType=target,ownerSources=owners,ownerApprovalRequired=old!=target)
 counts[surface]+=1
 if old!=target:changes[old+'->'+target]+=1
assert counts['Profiler']==900 and counts['OeeTrend']==120
assert counts==dict(Oee=11,OeeTrend=120,OeeTrendHead=1,Profiler=900,SystemHealth=23),counts
assert sum(changes.values())==200 and dict(changes)=={'Int32->UInt32':101,'Double->Float':64,'Int32->Int16':35},changes
sources={capture_path,previous_path,params_path,CORE/'DUTs/ST_Oee.TcDUT',CORE/'DUTs/ST_OeeSample.TcDUT',CORE/'DUTs/ST_SystemHealthStatus.TcDUT',CORE/'BaseClasses/FB_CycleProfiler.TcPOU',CORE/'BaseClasses/FB_UnitBase.TcPOU',TOOLS/'fraktal_ab_projection.py',TOOLS/'fraktal_ab_generate.py',*used}
result=dict(schema='fraktal.ab.s3g-surface-inventory',schemaVersion=1,status='owner-review-required',date='2026-10-23',capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),controllerAccess=False,controllerWrites=0,productionSourceChanges=False,priorLegacyPaths=2955,addedLegacyPaths=len(paths),cumulativeLegacyPaths=2955+len(paths),surfaceCounts=dict(counts),proposedTypeChanges=sum(changes.values()),proposedTypeChangeCounts=dict(changes),approvedAllowListChanged=False,sourceProjectionExpandedSha256=sha(raw),paths=paths,sourceBindings={p.relative_to(ROOT).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(sources)},float32Counterexample=dict(pythonDouble=1/3,coreFloat32=struct.unpack('<f',struct.pack('<f',1/3))[0]),unsignedBucketCounterexample=dict(milliseconds=4294967296,legacy=4294967296,coreUInt32=0),notes=['Core numeric corrections need an explicit extension of the current finite S3f allow-list before implementation.','Only the frozen logical path set is inventoried; no additional unconsumed Core fields are proposed here.','OEE/profiler ownership stays event-driven; this script does not change the oracle, PLC, generic reader, or provider.'])
with (G/'inventory_02.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ('paths','sourceBindings')}))
