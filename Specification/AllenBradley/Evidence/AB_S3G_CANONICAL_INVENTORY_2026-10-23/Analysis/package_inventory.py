from pathlib import Path
import datetime,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');G=Path(__file__).parent;AB=ROOT/'Specification/AllenBradley';E=AB/'Evidence'
NAME='AB_S3G_CANONICAL_INVENTORY_2026-10-23';D=E/NAME;REPORT=E/(NAME+'.md');sha=lambda raw:hashlib.sha256(raw).hexdigest()
v=json.loads((G/'validation_01.json').read_text());assert v['passed'] and not v['acceptanceRulesChanged']
for n in ('inventory_02','validation_01','spec_gate_01','contracts_gate_01','consistency_gate_01','root_tests_01','whitespace_gate_01'):
 assert json.loads((G/(n+'_exit.json')).read_text())['exitCode']==0,n
sources=dict(v['currentAbSources']);sources.update({p:row['sha256'] for p,row in v['sourceBindings'].items()})
for p,pin in sources.items():assert sha((ROOT/p).read_bytes())==pin,p
assert not D.exists();D.mkdir()
def put(name,raw):
 p=D/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw)
for p in sorted(G.rglob('*')):
 if not p.is_file() or '__pycache__' in p.parts or p.name.startswith(('package_01','seal_verification_')):continue
 assert '.acd' not in p.name.lower() and 'credential' not in p.name.lower()
 put('Analysis/'+p.relative_to(G).as_posix(),p.read_bytes())
for p in sources:put('Source/'+p,(ROOT/p).read_bytes())
for name in ('AB_CANONICAL_PUBLICATION_S3G_INVENTORY_2026-10-23.json','AB_CANONICAL_PUBLICATION_S3G_CONTRACT_REVIEW_2026-10-23.md','AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','AB_FROZEN_CONTRACTS_V2.json','AB_CAPACITY_OBSERVATIONS_2026-10-21.json'):put('Target/'+name,(AB/name).read_bytes())
artifacts=[]
for p in sorted(D.rglob('*')):
 if p.is_file():raw=p.read_bytes();artifacts.append(dict(path=p.relative_to(D).as_posix(),bytes=len(raw),sha256=sha(raw)))
m=dict(schema='fraktal.ab.s3g-inventory-evidence',schemaVersion=1,date='2026-10-23',timeZone='America/Mexico_City',sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),status='owner-review-required',controllerAccess=False,controllerWrites=0,productionSourceChanges=False,acceptanceRulesChanged=False,legacyPathsAdded=1055,cumulativeLegacyPaths=4010,proposedTypeCorrections=200,proposedTypeCounts={'Double->Float':64,'Int32->UInt32':101,'Int32->Int16':35},priorSeals=v['priorSeals'],currentAbSourceBindings=143,abTestsReused=2114,abTestEvidence='AB_S3F_CANONICAL_REVISION_RUNTIME_2026-10-23.md',rootTests=74,nativeBuildApplicable=False,nativeAcdFilesArchived=False,credentialFilesArchived=False,artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(a['bytes'] for a in artifacts))
put('manifest.json',json.dumps(m,indent=2).encode())
for a in artifacts:
 raw=(D/a['path']).read_bytes();assert len(raw)==a['bytes'] and sha(raw)==a['sha256']
assert sha(REPORT.read_bytes())==m['reportSha256']
result=dict(passed=True,artifacts=len(artifacts),bytes=m['totalBytes'],reportSha256=m['reportSha256'],manifestSha256=sha((D/'manifest.json').read_bytes()),predecessorRecords=22,predecessorArtifacts=4849,ownerDecisionPending=True,controllerChanges=0,acceptanceRulesChanged=False)
with (G/'seal_verification_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
