"""Seal the review-only inventory without changing any accepted source/rule."""
from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');G=Path(__file__).parent;AB=ROOT/'Specification/AllenBradley';E=AB/'Evidence'
NAME='AB_S3H_CANONICAL_INVENTORY_2026-10-23';D=E/NAME;REPORT=E/(NAME+'.md');sha=lambda raw:hashlib.sha256(raw).hexdigest()
v=json.loads((G/'validation_01.json').read_text());assert v['passed'] and v['paths']==278 and v['typeCorrectionsProposed']==36 and not v['acceptanceRulesChanged']
for label in ('inventory_02','validation_01','record_notes_01','spec_gate_01','contracts_gate_01','consistency_gate_01','whitespace_gate_01'):
    assert json.loads((G/(label+'_exit.json')).read_text())['exitCode']==0,label
for name,pin in v['currentAbSources'].items():assert sha((ROOT/name).read_bytes())==pin,name
for name,bound in v['sourceBindings'].items():assert sha((ROOT/name).read_bytes())==bound['sha256'],name
assert not D.exists();D.mkdir()
def put(name,raw):
    path=D/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as file:file.write(raw)
for path in sorted(G.rglob('*')):
    if not path.is_file() or '__pycache__' in path.parts:continue
    if path.name.startswith(('package_01','seal_verification_')):continue
    assert path.suffix.lower()!='.acd' and 'credential' not in path.name.lower()
    put('Analysis/'+path.relative_to(G).as_posix(),path.read_bytes())
for name in v['currentAbSources']:put('Source/'+name,(ROOT/name).read_bytes())
for name in v['sourceBindings']:
    if name not in v['currentAbSources']:put('Reference/'+name,(ROOT/name).read_bytes())
for name in ('AB_CANONICAL_PUBLICATION_S3H_INVENTORY_2026-10-23.json','AB_CANONICAL_PUBLICATION_S3H_CONTRACT_REVIEW_2026-10-23.md',
    'AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md','AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
    'AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','AB_FROZEN_CONTRACTS_V2.json','AB_CAPACITY_OBSERVATIONS_2026-10-21.json'):
    put('Target/'+name,(AB/name).read_bytes())
artifacts=[]
for path in sorted(D.rglob('*')):
    if not path.is_file():continue
    raw=path.read_bytes();artifacts.append(dict(path=path.relative_to(D).as_posix(),bytes=len(raw),sha256=sha(raw)))
m=dict(schema='fraktal.ab.s3h-inventory-evidence',schemaVersion=1,date='2026-10-23',timeZone='America/Mexico_City',
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),
    status='inventory-complete-owner-contract-decision-pending',controllerAccess=False,controllerWrites=0,
    productionSourceChanges=False,acceptanceRulesChanged=False,addedLegacyPaths=278,cumulativeLegacyPaths=4288,remainingLegacyPaths=149,
    proposedTypeChanges=36,otherAddedPathsExact=242,unsetTimestampPaths=1,currentAbSourceBindings=151,
    implementationPrepared=False,runtimeAccepted=False,ownerDecisionPending=True,failedRunsRetained=[dict(label='inventory_01',exitCode=1)],
    priorSeals=v['priorSeals'],nativeAcdFilesArchived=False,credentialFilesArchived=False,
    artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(row['bytes'] for row in artifacts))
put('manifest.json',json.dumps(m,indent=2).encode())
for row in artifacts:
    raw=(D/row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
assert sha(REPORT.read_bytes())==m['reportSha256']
result=dict(passed=True,artifacts=len(artifacts),bytes=m['totalBytes'],reportSha256=m['reportSha256'],manifestSha256=sha((D/'manifest.json').read_bytes()),
    predecessorRecords=26,predecessorArtifacts=6059,currentRecords=27,currentArtifacts=6059+len(artifacts),ownerDecisionPending=True)
with (G/'seal_verification_01.json').open('x') as file:json.dump(result,file,indent=2)
print(json.dumps(result))
