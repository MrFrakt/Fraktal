from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,json,re,shutil
ROOT=Path('C:/Users/SoftIndVM/Fraktal');E=ROOT/'Specification/AllenBradley/Evidence';O=Path(__file__).parent
W=Path(json.loads((O/'native_preparation_location_01.json').read_bytes())['workspace'])
NAME='AB_S3J_CANONICAL_RETRY_PREPARATION_2026-10-25';OUT=E/NAME;assert not OUT.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_bytes())
for name in ('ab_suite_01','root_tests_01','ab_spec_01','ab_contracts_01','consistency_01','whitespace_01'):
 assert load(O/(name+'_exit.json'))['exitCode']==0,name
 for suffix in ('.log','_exit.json'):
  with (W/(name+suffix)).open('xb') as out:out.write((O/(name+suffix)).read_bytes())
assert 'Ran 2249 tests' in (O/'ab_suite_01.log').read_text() and 'Ran 74 tests' in (O/'root_tests_01.log').read_text()
for name in ('session_build_01','download_gate_dry_check_01','authorization_negative_01','guard_readonly_01','baseline_state_readonly_01'):
 assert load(W/(name+'_exit.json'))['exitCode']==0,name
assert not load(W/'authorization.json')['CurrentOwnerApproved']
for n in ('preflight.json','deploy_attempt.json','backup.sha256','echo_before_s3j.ACD','canonical_downloaded.L5X','genealogy_restored.L5X'):assert not (W/n).exists(),n
regen=load(O/'regeneration_verified_01.json');assert regen['passed'] and regen['byteIdentical']
pin=regen['acdSha256'];source=regen['sourceSha256']
for name in ('s3j_canonical.ACD','capacity_review.ACD'):assert sha(W/name).upper()==pin
assert sha(W/'s3j.L5X').upper()==sha(O/'s3j_regenerated_01.L5X').upper()==source
assert load(W/'canonical_prepared_compare.json')['Equivalent']
capacity=load(W/'capacity_review.json');assert capacity['Measured'] and capacity['VerifiedFit'] and capacity['CanonicalSha256']==pin
assert load(W/'relocation_verified_01.json')['controllerHelperLogicByteIdenticalAfterPathNormalization']
replay=load(O/'capture_replay_corrected_01.json');assert replay['passed'] and replay['captures']==replay['comparisonsPassed']==41
prior=load(E/'AB_S3J_CANONICAL_PREPARATION_2026-10-25/Preparation/source_bindings_01.json')
paths=set(prior['sha256']);paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'FraktalCore/PLC/Allen-Bradley/tools').glob('*.py'))
bindings={n:sha(ROOT/n) for n in sorted(paths)}
with (W/'source_bindings_01.json').open('x') as out:json.dump(dict(passed=True,sha256=bindings,preparedAcdSha256=pin,sourceSha256=source,sourceCount=len(bindings),head='f194c3a53'),out,indent=2)
seals=[];total=0;pat=re.compile(r'AB_S(0|1|2|3[A-Z]?)_(CANONICAL|SUPPLEMENTARY)_')
for p in sorted(E.glob('AB_*/manifest.json')):
 if not (pat.match(p.parent.name) or p.parent.name.startswith('AB_R1_R2_')):continue
 m=load(p)
 for a in m['artifacts']:
  b=(p.parent/a['path']).read_bytes();assert len(b)==a['bytes'] and hashlib.sha256(b).hexdigest()==a['sha256'].lower(),(p,a['path'])
  if a.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(b)).hexdigest()==a['expandedSha256'].lower()
 if m.get('reportSha256'):assert sha(E/m['report'])==m['reportSha256'].lower()
 seals.append(dict(name=p.parent.name,manifestSha256=sha(p),artifacts=len(m['artifacts'])));total+=len(m['artifacts'])
def copy(p,t):
 t.parent.mkdir(parents=True,exist_ok=True)
 with t.open('xb') as f:f.write(p.read_bytes())
def pack(p,t):
 t.parent.mkdir(parents=True,exist_ok=True)
 with p.open('rb') as a,t.open('xb') as b,gzip.GzipFile(filename='',mode='wb',fileobj=b,mtime=0) as z:shutil.copyfileobj(a,z)
def tree(base,label):
 for p in sorted(base.rglob('*')):
  if not p.is_file() or any(x in ('bin','obj','__pycache__') for x in p.relative_to(base).parts) or p.suffix.upper() in ('.ACD','.BAK','.EXE','.DLL','.PDB'):continue
  assert 'credential' not in p.name.lower()
  t=OUT/label/p.relative_to(base)
  if p.suffix.upper()=='.L5X':pack(p,Path(str(t)+'.gz'))
  else:copy(p,t)
tree(O,'Offline');tree(W,'Preparation')
for n,pin_sha in bindings.items():
 assert sha(ROOT/n)==pin_sha,n
 pack(ROOT/n,OUT/'Source'/(n+'.gz'))
# Reuse the immutable compiler/read-back/access/Capacity payload for unchanged
# PLC bytes; archive a small hash-bound transfer record, not another native run.
original=load(E/'AB_S3J_CANONICAL_PREPARATION_2026-10-25/manifest.json')
assert original['preparedAcdSha256']==pin and original['sourceSha256']==source
transfer=dict(passed=True,sourceAndAcdUnchanged=True,originalPreparation='AB_S3J_CANONICAL_PREPARATION_2026-10-25',manifestSha256=sha(E/'AB_S3J_CANONICAL_PREPARATION_2026-10-25/manifest.json'),compilerTargets=['EchoController v38','PhysicalController v38'],nativeCompilesRerun=False,readbackEquivalent=True,readbackBodies=60,readbackInitialValues=42043,capacity=original['capacity'],canonicalReaderUnchanged=bindings['FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_canonical_reader.py']==prior['sha256']['FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_canonical_reader.py'],priorCapturesBound=1245)
with (OUT/'gate_transfer.json').open('x') as f:json.dump(transfer,f,indent=2)
artifacts=[]
for p in sorted(OUT.rglob('*')):
 if p.is_file():
  a=dict(path=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size,sha256=sha(p))
  if p.name.endswith('.gz'):a['expandedSha256']=hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()
  artifacts.append(a)
sdk=W/'session/bin/Debug/net8.0/win-x86/S3jSession.exe'
m=dict(schema='fraktal.ab.s3j-canonical-retry-preparation',schemaVersion=1,date='2026-10-25',timeZone='America/Mexico_City',sealedUtc=datetime.now(timezone.utc).isoformat(),report=NAME+'.md',reportSha256=sha(E/(NAME+'.md')),status='offline-qualified-exact-image-awaits-current-confirmation',currentNativeSessionApproved=False,controllerOperations=0,readOnlyControllerChecks=True,nativeAccepted=False,preparedAcdSha256=pin,sourceSha256=source,sourceBindings=len(bindings),abTests=2249,rootTests=74,correctedCaptureReplays=41,priorCapturesBound=1245,capacity=original['capacity'],sessionExecutableSha256=sha(sdk),sessionAssemblySha256=sha(sdk.with_suffix('.dll')),sessionSourceSha256=sha(W/'session/Program.cs'),workspace=str(W),offlineWorkspace=str(O),writeScopeUnchanged=True,priorSeals=seals,priorArtifactCount=total,artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(a['bytes'] for a in artifacts),credentialFilesArchived=False,nativeAcdFilesArchived=False,committed=False,pushed=False)
with (OUT/'manifest.json').open('x') as f:json.dump(m,f,indent=2)
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),sourceBindings=len(bindings),priorRecords=len(seals),priorArtifacts=total,workspace=str(W))))
