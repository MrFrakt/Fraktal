"""Append-only failed-attempt and verified-rollback evidence; never copy credentials/ACDs."""
from pathlib import Path
import datetime,gzip,hashlib,json
R=Path('C:/Users/SoftIndVM/Fraktal');D=Path(__file__).parent;E=R/'Specification/AllenBradley/Evidence'
NAME='AB_S3K_CANONICAL_ATTEMPT_2026-10-25';OUT=E/NAME
assert not OUT.exists()
sha=lambda b:hashlib.sha256(b).hexdigest()
load=lambda p:json.loads(p.read_bytes())
def write(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def save(p,v):write(p,(json.dumps(v,indent=2,ensure_ascii=False)+'\n').encode())
assert load(D/'restore_verify_session_03.json')['passed']
assert len(load(D/'baseline_regressions_01.json')['rows'])==31
assert load(D/'final_checks_01.json')['passed']
assert load(D/'partial_pair_replay_02.json')['captures']==5
for label in ('ab_suite_request_cases_02','post_runtime_root_tests_01','post_runtime_spec_01','post_runtime_contracts_01',
              'post_runtime_consistency_01','post_runtime_whitespace_01','restore_log_audit_01','restore_access_01','preflight_final_01'):
 assert load(D/(label+'_exit.json'))['exitCode']==0,label
previous=E/'AB_S3K_COMMAND_BINDING_OFFLINE_2026-10-25/manifest.json';m=load(previous)
names={p['name'] for p in m['priorSeals']}|{previous.parent.name};seals=[];total=0
for name in sorted(names):
 p=E/name/'manifest.json';old=load(p)
 for a in old['artifacts']:
  b=(p.parent/a['path']).read_bytes();assert len(b)==a['bytes'] and sha(b)==a['sha256'].lower(),(name,a['path'])
  if a.get('expandedSha256'):assert sha(gzip.decompress(b))==a['expandedSha256'].lower()
 if old.get('reportSha256'):assert sha((E/old['report']).read_bytes())==old['reportSha256'].lower()
 seals.append(dict(name=name,manifestSha256=sha(p.read_bytes()),artifacts=len(old['artifacts'])));total+=len(old['artifacts'])
save(D/'prior_seals_runtime_01.json',dict(passed=True,records=len(seals),artifacts=total,rows=seals))
source=load(Path('C:/work/fraktal-ab-s3k-20261025/command_a_02/source_bindings_01.json'))['sha256']
paths={p for p in source if (R/p).exists()}
paths.update(p.relative_to(R).as_posix() for p in (R/'FraktalCore/PLC/Allen-Bradley/tools').glob('*.py'))
bindings={p:sha((R/p).read_bytes()) for p in sorted(paths)}
save(D/'runtime_source_bindings_01.json',dict(passed=True,sha256=bindings))
artifacts=[]
def archive(src,rel,compress=False):
 raw=src.read_bytes();b=gzip.compress(raw,mtime=0) if compress else raw;name=rel+('.gz' if compress else '')
 write(OUT/name,b);row=dict(path=name,bytes=len(b),sha256=sha(b))
 if compress:row['expandedSha256']=sha(raw)
 artifacts.append(row)
for p in sorted(D.rglob('*')):
 if not p.is_file() or any(part in ('bin','obj','__pycache__') for part in p.relative_to(D).parts):continue
 if p.suffix.lower() not in ('.py','.json','.gz','.log','.l5x','.cs','.csproj','.txt','.sha256'):continue
 assert not ('credential' in p.name.lower()),p
 archive(p,'Download/'+p.relative_to(D).as_posix(),p.suffix.lower()=='.l5x')
reproduction=Path('C:/work/fraktal-ab-s3k-20261025/compatibility_fix_01/reproduction_01.json')
archive(reproduction,'Diagnosis/reproduction_01.json')
for name in bindings:archive(R/name,'Source/'+name,True)
report=E/(NAME+'.md')
manifest=dict(schema='fraktal.ab.s3k-native-attempt',schemaVersion=1,date='2026-10-25',
 timeZone='America/Mexico_City',sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 report=report.name,reportSha256=sha(report.read_bytes()),status='candidate-document-restore-refused-genealogy-restored',
 nativeAccepted=False,candidateRows=0,accessCasesPassed=2,typedVectorsRun=False,pairedCapturesReplayed=5,
 ownerInstruction='please continue, run request cases **then restore genealogy**',authorizationConsumed=True,
 currentControllerChangesAuthorized=False,genealogyRestored=True,baselineChecks=31,finalChecksPassed=True,
 downloadedAcdSha256='5B62CAC28C8EB5A819850D49FC854123C0B0B00449E2E8663FAC08B96C3000F6',
 sourceSha256='426289A5E71CDEC1DBC5A4C5C7FBCDE4E706676B311362A12A91CFD36083EE78',
 sourceBindings=len(bindings),abTests=2287,rootTests=74,timing=load(D/'timing_summary_01.json'),
 priorSeals=seals,priorArtifacts=total,artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(a['bytes'] for a in artifacts),
 credentialFilesArchived=False,nativeAcdFilesArchived=False,committed=False,pushed=False)
save(OUT/'manifest.json',manifest)
for a in artifacts:
 b=(OUT/a['path']).read_bytes();assert sha(b)==a['sha256'] and len(b)==a['bytes']
 if a.get('expandedSha256'):assert sha(gzip.decompress(b))==a['expandedSha256']
result=dict(passed=True,manifest=str(OUT/'manifest.json'),manifestSha256=sha((OUT/'manifest.json').read_bytes()),
 artifactCount=len(artifacts),sourceBindings=len(bindings),priorSeals=len(seals),priorArtifacts=total,nativeAccepted=False,genealogyRestored=True)
save(D/'sealed_attempt_01.json',result);print(json.dumps(result))
