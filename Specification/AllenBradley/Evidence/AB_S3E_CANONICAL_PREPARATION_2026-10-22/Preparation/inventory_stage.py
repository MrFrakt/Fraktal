from pathlib import Path
import datetime,gzip,hashlib,json,re
ROOT=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;B=ROOT/'Specification/AllenBradley'
p=ROOT/'FraktalCore/PLC/Allen-Bradley/tools/fixtures/canonical/genealogy_projection_01.json.gz'
raw=p.read_bytes();expanded=gzip.decompress(raw);frozen=json.loads(expanded)
previous=B/'AB_CANONICAL_PUBLICATION_S3D_INVENTORY_2026-10-22.json';prior=json.loads(previous.read_text())
paths=dict(prior['paths']);added=[]
for path,value in frozen['values'].items():
 if not path.startswith('Press/Access/'):continue
 target=re.sub(r'/Required\[(\d+)\]',lambda m:'/Required['+str(int(m[1])-1)+']',path)
 assert target not in paths
 logical='Boolean' if type(value) is bool else 'String' if isinstance(value,str) else 'Int32'
 paths[target]=dict(projectionPath=path,value=value,type=logical);added.append(target)
assert len(added)==29 and len(paths)==2154
result=dict(schema='fraktal.ab.s3e-surface-inventory',schemaVersion=1,date='2026-10-22',capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceProjection=p.relative_to(ROOT).as_posix(),sourceCompressedSha256=hashlib.sha256(raw).hexdigest(),sourceExpandedSha256=hashlib.sha256(expanded).hexdigest(),priorS3dInventorySha256=hashlib.sha256(previous.read_bytes()).hexdigest(),previousPaths=2125,addedPaths=29,expectedPaths=2154,auditAddsPaths=0,auditOverrides='Description/SourcePath of occupied MESSAGE slots in the existing 64-entry AlarmLog/Ring, never a second ring',fixtureEquipmentModules=0,paths=paths,addedPathList=sorted(added))
for target in (W/'inventory.json',B/'AB_CANONICAL_PUBLICATION_S3E_INVENTORY_2026-10-22.json'):
 with target.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ('paths','addedPathList')}))
