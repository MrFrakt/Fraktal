from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,json,shutil,re
ROOT=Path('C:/Users/SoftIndVM/Fraktal');EV=ROOT/'Specification/AllenBradley/Evidence'
O=Path(__file__).parent;W=Path(json.loads((O/'native_preparation_location_01.json').read_bytes())['workspace'])
NAME='AB_R1_R2_CANONICAL_PREPARATION_2026-10-24';OUT=EV/NAME
assert not OUT.exists(),'append-only output exists'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for name in ('ab_suite_03','root_tests_04','ab_spec_04','ab_contracts_04','consistency_04','whitespace_04'):
 assert json.loads((W/(name+'_exit.json')).read_bytes())['exitCode']==0,name
for name in ('gate_dry_check_01','authorization_negative_01'):
 assert json.loads((W/(name+'.json')).read_bytes())['passed'] is True,name
assert json.loads((W/'authorization.json').read_bytes())['CurrentOwnerApproved'] is False
acd=(W/'canonical.sha256').read_text().strip();source=sha(W/'s3i_r1_r2.L5X')
for name in ('s3i_canonical.ACD','capacity_review.ACD','retention_control.ACD'):assert sha(W/name).upper()==acd
assert source.upper()=='C3E1FA7EEACB927B98AC0177E51D44A2E132BC1C1677ACC07583A46C02021333'
assert json.loads((W/'canonical_prepared_compare.json').read_bytes())['Equivalent'] is True
for name in ('sdk_echo_audit_02','sdk_physical_audit_02','prepare_sdk_audit_02'):assert json.loads((O/(name+'.json')).read_bytes())['Clean'] is True
for name in ('readback_Echo_01','readback_Physical_01'):assert json.loads((O/(name+'.log')).read_bytes())['Equivalent'] is True
for name in ('access_Echo_01','access_Physical_01'):assert json.loads((O/(name+'.json')).read_bytes())['passed'] is True
replay=json.loads((O/'capture_replay_04.json').read_bytes());assert replay['passed'] and replay['captures']==1147
assert json.loads((O/'compatibility_02.json').read_bytes())['passed'] is True
# Source closure extends the predecessor with all flat AB Python tools/tests,
# preserving normative inputs while never traversing credential stores.
prior=json.loads((EV/'AB_S3I_CANONICAL_LIFETIME_RETRY2_PREPARATION_2026-10-24/Preparation/source_bindings_01.json').read_bytes())['sha256']
paths=set(prior)
paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'FraktalCore/PLC/Allen-Bradley/tools').glob('*.py'))
paths.update('Specification/AllenBradley/'+name for name in (
 'AB_CANONICAL_MANIFEST_V64_CONTRACT_REVIEW_2026-10-24.md','AB_CAPACITY_BUDGET_AND_REDUCTION_PLAN_2026-10-24.md',
 'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md',
 'AB_FROZEN_CONTRACTS_V2.json'))
bindings={name:sha(ROOT/name) for name in sorted(paths)}
with (W/'source_bindings_01.json').open('x') as f:json.dump(dict(passed=True,sha256=bindings,preparedAcdSha256=acd,
 sourceSha256=source,head='f194c3a53',nativeAccepted=False,sourceCount=len(bindings)),f,indent=2)

def copy(path,target):
 target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists();shutil.copyfile(path,target)
def pack(path,target):
 target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists()
 with path.open('rb') as a,target.open('wb') as b,gzip.GzipFile(filename='',mode='wb',fileobj=b,mtime=0) as c:shutil.copyfileobj(a,c)
def archive_tree(base,label):
 for p in sorted(base.rglob('*')):
  rel=p.relative_to(base)
  if not p.is_file() or any(x in ('bin','obj','__pycache__') for x in rel.parts) or p.suffix.upper() in ('.ACD','.BAK','.EXE','.DLL','.PDB'):continue
  if p.suffix.upper()=='.L5X':pack(p,OUT/label/(rel.as_posix()+'.gz'))
  else:copy(p,OUT/label/rel)
archive_tree(O,'Offline');archive_tree(W,'Preparation')
for name,pin in bindings.items():
 assert sha(ROOT/name)==pin,name
 pack(ROOT/name,OUT/'Source'/(name+'.gz'))
artifacts=[]
for p in sorted(OUT.rglob('*')):
 if not p.is_file():continue
 row=dict(path=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size,sha256=sha(p))
 if p.name.endswith('.gz'):row['expandedSha256']=hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()
 artifacts.append(row)
assert not any('credential' in x['path'].lower() or x['path'].upper().endswith(('.ACD','.BAK')) for x in artifacts)
sdk=W/'session/bin/Debug/net8.0/win-x86/S3iLifetimeSession.exe'
predecessors=json.loads((O/'prior_seals_01.json').read_bytes())
manifest=dict(schema='fraktal.ab.r1-r2-canonical-preparation',schemaVersion=1,date='2026-10-24',timeZone='America/Mexico_City',
 sealedUtc=datetime.now(timezone.utc).isoformat(),report=NAME+'.md',reportSha256=sha(EV/(NAME+'.md')),
 status='offline-qualified-exact-image-awaits-current-confirmation',currentNativeSessionApproved=False,controllerOperations=0,
 readOnlyControllerChecks=True,stageAccepted=False,nativeAccepted=False,preparedAcdSha256=acd,sourceSha256=source,
 sourceBindings=len(bindings),sourceClosureSha256=sha(W/'source_bindings_01.json'),abTests=2227,rootTests=74,sealedCaptures=1147,
 typeAnnotations=137,pathExceptions=2,capacity=dict(used=1653432,available=1492296,total=3145728,displayedPercent=52),
 sessionExecutableSha256=sha(sdk),sessionAssemblySha256=sha(sdk.with_suffix('.dll')),sessionSourceSha256=sha(W/'session/Program.cs'),
 workspace=str(W),offlineWorkspace=str(O),priorSeals=predecessors['rows'],priorArtifactCount=predecessors['artifacts'],
 artifactCount=len(artifacts),artifacts=artifacts,totalBytes=sum(x['bytes'] for x in artifacts),
 credentialFilesArchived=False,nativeAcdFilesArchived=False,committed=False,pushed=False)
with (OUT/'manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2);f.write('\n')
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),sourceBindings=len(bindings),bytes=manifest['totalBytes'],predecessors=len(predecessors['rows']),manifest=str(OUT/'manifest.json'))))
