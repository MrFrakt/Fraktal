from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,json,shutil,re
ROOT=Path('C:/Users/SoftIndVM/Fraktal');E=ROOT/'Specification/AllenBradley/Evidence';O=Path(__file__).parent
W=Path(json.loads((O/'native_preparation_location_02.json').read_bytes())['workspace'])
NAME='AB_S3J_CANONICAL_PREPARATION_2026-10-25';OUT=E/NAME;assert not OUT.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for name in ('ab_suite_03','root_tests_06','ab_spec_06','ab_contracts_06','consistency_06','whitespace_06'):assert json.loads((O/(name+'_exit.json')).read_bytes())['exitCode']==0,name
for name in ('session_build_01','prepared_compare_01','download_gate_dry_check_01','authorization_negative_01'):assert json.loads((W/(name+'_exit.json')).read_bytes())['exitCode']==0,name
assert not json.loads((W/'authorization.json').read_bytes())['CurrentOwnerApproved']
identity=json.loads((O/'prepared_identity_02.json').read_bytes());pin=identity['acdSha256'];source=identity['sourceSha256']
for name in ('s3j_canonical.ACD','capacity_review.ACD'):assert sha(W/name).upper()==pin
assert sha(W/'s3j.L5X')==sha(O/'s3j_06.L5X')==source.lower()
assert json.loads((W/'canonical_prepared_compare.json').read_bytes())['Equivalent']
for name in ('Echo','Physical'):
 assert json.loads((O/('readback_'+name+'_04.log')).read_bytes())['Equivalent']
 assert json.loads((O/('access_'+name+'_04.json')).read_bytes())['passed']
 assert json.loads((O/('sdk_'+name+'_04.json')).read_bytes())['Clean']
assert json.loads((O/'prepared_sdk_audit_02.json').read_bytes())['Clean']
assert json.loads((O/'compatibility_01.json').read_bytes())['passed']
assert json.loads((O/'r1_r2_compatibility_01.json').read_bytes())['passed']
assert json.loads((O/'regeneration_01.json').read_bytes())['passed']
replay=json.loads((O/'capture_replay_01.json').read_bytes());assert replay['passed'] and replay['captures']==1245
capacity=json.loads((O/'capacity_auto_02.json').read_bytes());assert capacity['Measured'] and capacity['VerifiedFit'] and capacity['CanonicalSha256']==pin
# Carry prior closure, add the full current AB Python surface and normative
# fieldbus DUT/ceiling sources. Never enumerate any credential directory.
prior=json.loads((E/'AB_R1_R2_CANONICAL_PREPARATION_2026-10-24/Preparation/source_bindings_01.json').read_bytes())['sha256']
paths=set(prior);paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'FraktalCore/PLC/Allen-Bradley/tools').glob('*.py'))
paths.update('FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/'+p for p in ('DUTs/ST_FieldbusTopology.TcDUT','DUTs/ST_BusNode.TcDUT','DUTs/ST_IoChannel.TcDUT','DUTs/E_NodeState.TcDUT','Params/PL_Fraktal.TcGVL'))
paths.update('Specification/AllenBradley/'+p for p in ('AB_CANONICAL_PUBLICATION_S3J_WIRE_DRAFT_2026-10-24.md','AB_CANONICAL_PUBLICATION_S3J_CONTRACT_REVIEW_2026-10-24.md','AB_CANONICAL_PUBLICATION_S3J_INVENTORY_2026-10-24.json'))
bindings={name:sha(ROOT/name) for name in sorted(paths)}
with (W/'source_bindings_01.json').open('x') as f:json.dump(dict(passed=True,sha256=bindings,preparedAcdSha256=pin,sourceSha256=source,sourceCount=len(bindings),head='f194c3a53'),f,indent=2)
seals=[];total=0;pattern=re.compile(r'AB_S(0|1|2|3[A-Z]?)_(CANONICAL|SUPPLEMENTARY)_')
for p in sorted(E.glob('AB_*/manifest.json')):
 if not (pattern.match(p.parent.name) or p.parent.name.startswith('AB_R1_R2_')):continue
 m=json.loads(p.read_bytes())
 for a in m['artifacts']:
  raw=(p.parent/a['path']).read_bytes();assert len(raw)==a['bytes'] and hashlib.sha256(raw).hexdigest()==a['sha256'].lower(),(p,a['path'])
  if a.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==a['expandedSha256'].lower()
 if m.get('report') and m.get('reportSha256'):assert sha(E/m['report'])==m['reportSha256'].lower()
 seals.append(dict(name=p.parent.name,manifestSha256=sha(p),artifacts=len(m['artifacts'])));total+=len(m['artifacts'])
def copy(p,t):
 t.parent.mkdir(parents=True,exist_ok=True);assert not t.exists();shutil.copyfile(p,t)
def pack(p,t):
 t.parent.mkdir(parents=True,exist_ok=True);assert not t.exists()
 with p.open('rb') as a,t.open('wb') as b,gzip.GzipFile(filename='',mode='wb',fileobj=b,mtime=0) as z:shutil.copyfileobj(a,z)
def tree(base,label):
 for p in sorted(base.rglob('*')):
  if not p.is_file() or any(x in ('bin','obj','__pycache__') for x in p.relative_to(base).parts) or p.suffix.upper() in ('.ACD','.BAK','.EXE','.DLL','.PDB'):continue
  t=OUT/label/p.relative_to(base)
  if p.suffix.upper()=='.L5X':pack(p,Path(str(t)+'.gz'))
  else:copy(p,t)
tree(O,'Offline');tree(W,'Preparation')
for name,pin_sha in bindings.items():
 assert sha(ROOT/name)==pin_sha,name
 pack(ROOT/name,OUT/'Source'/(name+'.gz'))
artifacts=[]
for p in sorted(OUT.rglob('*')):
 if not p.is_file():continue
 a=dict(path=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size,sha256=sha(p))
 if p.name.endswith('.gz'):a['expandedSha256']=hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()
 artifacts.append(a)
assert not any(a['path'].upper().endswith(('.ACD','.BAK')) or 'credential' in a['path'].lower() for a in artifacts)
sdk=W/'session/bin/Debug/net8.0/win-x86/S3jSession.exe'
manifest=dict(schema='fraktal.ab.s3j-canonical-preparation',schemaVersion=1,date='2026-10-25',timeZone='America/Mexico_City',sealedUtc=datetime.now(timezone.utc).isoformat(),
 report=NAME+'.md',reportSha256=sha(E/(NAME+'.md')),status='offline-qualified-exact-image-awaits-current-confirmation',currentNativeSessionApproved=False,controllerOperations=0,readOnlyControllerChecks=True,
 stageAccepted=False,nativeAccepted=False,preparedAcdSha256=identity['acdSha256'],sourceSha256=source,sourceBindings=len(bindings),abTests=2248,rootTests=74,sealedCapturesReplayed=1245,
 nodeCount=3,channels=20,fieldbusPaths=327,typeAnnotations=142,manifestMinor=5,
 capacity={k:capacity[k] for k in ('UsedStandardBlocks','AvailableBlocks','TotalBlocks','DisplayedUsagePercent')},
 sessionExecutableSha256=sha(sdk),sessionAssemblySha256=sha(sdk.with_suffix('.dll')),sessionSourceSha256=sha(W/'session/Program.cs'),
 workspace=str(W),offlineWorkspace=str(O),priorSeals=seals,priorArtifactCount=total,artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(a['bytes'] for a in artifacts),
 credentialFilesArchived=False,nativeAcdFilesArchived=False,committed=False,pushed=False)
with (OUT/'manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2);f.write('\n')
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),sourceBindings=len(bindings),priorRecords=len(seals),priorArtifacts=total,bytes=manifest['totalBytes'])))
