from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,json,re,shutil
ROOT=Path('C:/Users/SoftIndVM/Fraktal');E=ROOT/'Specification/AllenBradley/Evidence';R=Path(__file__).parent
W=R.parent/'prepare_fb6598e2234d43f99f5ae75e718f9860'
NAME='AB_S3J_CANONICAL_ATTEMPT_2026-10-25';OUT=E/NAME
assert not OUT.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_bytes())
pins=load(R/'initial_source_verification.json')
for name,pin in pins['sha256'].items():assert sha(ROOT/name)==pin,name
session=load(R/'session_execution_01.json');start=load(R/'start_execution_01.json')
assert not session['passed'] and not start['passed'] and session['restoreError'] is None
assert [s['label'] for s in session['steps'] if s['exitCode']] == ['candidate_regressions_01']
assert len({s['label'] for s in session['steps']})==len(session['steps'])==16
candidate=load(R/'candidate_regressions_01.json')
assert candidate['error']=='condition equivalence failed' and candidate['policyRestored']
rows=candidate['rows']+candidate['s3jAccessRows']+candidate['s3jConfigRows'];assert len(rows)==19 and all(x['passed'] for x in rows)
base=load(R/'baseline_regressions_01.json');assert len(base['rows'])==31 and all(x['passed'] for x in base['rows'])
assert load(R/'final_checks_01.json')['passed']
for n in ('dumps_before_session_01','dumps_after_session_01'):assert load(R/(n+'.json'))['dumpFiles']==[]
replay=load(R/'replay_attempt_01.json');assert replay['passed'] and replay['captures']==41 and replay['comparisonsPassed']==40
assert load(R/'failure_diagnosis_01.json')['passed']
assert not (R/'io_vectors_01.json').exists() and not (R/'candidate_timing_01.json').exists()
a=load(R/'owner_session_approval.json');consumed=load(R/'owner_session_consumed.json')
assert a['approved'] and consumed['Consumed'] and not consumed['CurrentOwnerApproved']
assert not load(W/'authorization.json')['CurrentOwnerApproved']
ACD=pins['preparedAcdSha256'];assert load(W/'deploy_attempt.json')['CanonicalSha256']==ACD
assert sha(W/'capacity_review.ACD').upper()==ACD
assert sha(W/'s3j.L5X').upper()==pins['sourceSha256'].upper()
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')).upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
seals=[];total=0;pat=re.compile(r'AB_S(0|1|2|3[A-Z]?)_(CANONICAL|SUPPLEMENTARY)_')
for p in sorted(E.glob('AB_*/manifest.json')):
 if not (pat.match(p.parent.name) or p.parent.name.startswith('AB_R1_R2_')):continue
 m=load(p)
 for x in m['artifacts']:
  raw=(p.parent/x['path']).read_bytes();assert len(raw)==x['bytes'] and hashlib.sha256(raw).hexdigest()==x['sha256'].lower(),(p,x['path'])
  if x.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==x['expandedSha256'].lower()
 if m.get('report') and m.get('reportSha256'):assert sha(E/m['report'])==m['reportSha256'].lower()
 total+=len(m['artifacts']);seals.append(dict(name=p.parent.name,manifestSha256=sha(p),artifacts=len(m['artifacts'])))
def copy(p,target):
 target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as out:out.write(p.read_bytes())
def pack(p,target):
 target.parent.mkdir(parents=True,exist_ok=True)
 with p.open('rb') as inp,target.open('xb') as out,gzip.GzipFile(filename='',mode='wb',fileobj=out,mtime=0) as z:shutil.copyfileobj(inp,z)
for p in sorted(R.rglob('*')):
 if p.is_file() and '__pycache__' not in p.parts:
  assert p.suffix.upper() not in ('.ACD','.BAK') and 'credential' not in p.name.lower()
  copy(p,OUT/'Runtime'/p.relative_to(R))
for n in ('authorization.json','preflight.json','deploy_attempt.json','backup.sha256','canonical.sha256'):
 copy(W/n,OUT/'Session'/n)
for n in ('echo_before_s3j.L5X','canonical_downloaded.L5X','genealogy_restored.L5X'):
 pack(W/n,OUT/'Session'/(n+'.gz'))
for n in ('fraktal_ab_projection.py','fraktal_ab_s2_equivalence.py'):
 copy(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'/n,OUT/'OracleSources'/n)
artifacts=[]
for p in sorted(OUT.rglob('*')):
 if p.is_file():
  row=dict(path=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size,sha256=sha(p))
  if p.name.endswith('.gz'):row['expandedSha256']=hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()
  artifacts.append(row)
m=dict(schema='fraktal.ab.s3j-canonical-attempt',schemaVersion=1,date='2026-10-25',timeZone='America/Mexico_City',sealedUtc=datetime.now(timezone.utc).isoformat(),report=NAME+'.md',reportSha256=sha(E/(NAME+'.md')),status='candidate-oracle-mismatch-genealogy-restored',nativeAccepted=False,sessionApprovalConsumed=True,approvalQuestionItemId=a['questionItemId'],approvalAnswer=a['answer'],downloadedAcdSha256=ACD,sourceSha256=pins['sourceSha256'],backupSha256=(W/'backup.sha256').read_text().strip(),sourceBindings=len(pins['sha256']),completedCandidateCaseRows=19,pairedCaptures=41,equalCaptures=40,unequalCaptures=1,independentCaptureReplays=41,ioVectorWrites=0,candidateTimingMeasured=False,baselineChecks=31,finalChecksPassed=True,newDumps=False,faultClears=0,clockChanges=0,powerOperations=0,hardKills=0,priorSeals=seals,priorArtifactCount=total,artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(x['bytes'] for x in artifacts),credentialFilesArchived=False,nativeAcdFilesArchived=False,committed=False,pushed=False)
with (OUT/'manifest.json').open('x') as f:json.dump(m,f,indent=2)
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),priorRecords=len(seals),priorArtifacts=total,sourceBindings=len(pins['sha256']))))
