from datetime import datetime,timezone
from pathlib import Path
import gzip,hashlib,json,re,shutil
ROOT=Path('C:/Users/SoftIndVM/Fraktal');E=ROOT/'Specification/AllenBradley/Evidence';R=Path(__file__).parent
W=R.parent/'prepare_d93d8292dbb4425d9eba04ba75cd110c';NAME='AB_S3J_CANONICAL_RUNTIME_2026-10-25';OUT=E/NAME
assert not OUT.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_bytes())
pins=load(R/'initial_source_verification.json');verified=load(R/'source_verification_before_documents_01.json')
assert verified['passed'] and verified['sourceBindings']==len(pins['sha256'])==368
updates=load(R/'documentation_updates_01.json');allowed={'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','Specification/AllenBradley/AB_FROZEN_CONTRACTS_V2.json'}
assert set(updates)==allowed
for n,h in pins['sha256'].items():
 if n in updates:assert updates[n]['beforeSha256']==h and updates[n]['afterSha256']==sha(ROOT/n),n
 else:assert sha(ROOT/n)==h,n
start=load(R/'start_execution_01.json');session=load(R/'session_execution_01.json')
assert start['passed'] and session['passed'] and all(x['exitCode']==0 for x in session['steps'])
assert len({x['label'] for x in session['steps']})==len(session['steps'])==21
c=load(R/'candidate_regressions_01.json');rows=c['rows']+c['s3jAccessRows']+c['s3jConfigRows']
assert len(rows)==41 and all(x['passed'] for x in rows) and c['restored'] and c['policyRestored'] and c['s3fSetMediumEmpty']
pairs=[x for k,v in c.items() if k.endswith('Pairs') for x in v];assert len(pairs)==87 and all(x['passed'] for x in pairs)
io=load(R/'io_vectors_01.json');assert io['passed'] and io['sourceRestored'] and len(io['rows'])==9 and all(x['passed'] for x in io['rows'])
assert len(io['s3jIoPairs'])==10 and all(x['passed'] for x in io['s3jIoPairs']) and io['s3jIoPairs'][-1]['phase']=='source_restored'
base=load(R/'baseline_regressions_01.json');assert len(base['rows'])==31 and all(x['passed'] for x in base['rows'])
assert load(R/'final_checks_01.json')['passed']
for n in ('dumps_before_session_01','dumps_after_session_01'):assert load(R/(n+'.json'))['dumpFiles']==[]
replay=load(R/'replay_01.json');assert replay['passed'] and replay['captures']==98
scan=load(R/'measurements_summary_01.json');assert scan['passed'] and scan['timing']['candidate']['overlaps']==0
for n in ('post_root_tests_01','post_ab_spec_01','post_ab_contracts_01','post_consistency_01','post_whitespace_01'):assert load(R/(n+'_exit.json'))['exitCode']==0,n
a=load(R/'owner_session_approval.json');consumed=load(R/'owner_session_consumed.json')
assert a['approved'] and consumed['Consumed'] and not consumed['CurrentOwnerApproved'] and not load(W/'authorization.json')['CurrentOwnerApproved']
ACD=pins['preparedAcdSha256'];assert load(W/'deploy_attempt.json')['CanonicalSha256']==ACD==sha(W/'capacity_review.ACD').upper()
assert sha(W/'s3j.L5X').upper()==pins['sourceSha256'].upper()
seals=[];total=0;pat=re.compile(r'AB_S(0|1|2|3[A-Z]?)_(CANONICAL|SUPPLEMENTARY)_')
for p in sorted(E.glob('AB_*/manifest.json')):
 if not (pat.match(p.parent.name) or p.parent.name.startswith('AB_R1_R2_')):continue
 m=load(p)
 for x in m['artifacts']:
  b=(p.parent/x['path']).read_bytes();assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['sha256'].lower(),(p,x['path'])
  if x.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(b)).hexdigest()==x['expandedSha256'].lower()
 if m.get('reportSha256'):assert sha(E/m['report'])==m['reportSha256'].lower()
 seals.append(dict(name=p.parent.name,manifestSha256=sha(p),artifacts=len(m['artifacts'])));total+=len(m['artifacts'])
def copy(p,t):
 t.parent.mkdir(parents=True,exist_ok=True)
 with t.open('xb') as f:f.write(p.read_bytes())
def pack(p,t):
 t.parent.mkdir(parents=True,exist_ok=True)
 with p.open('rb') as a,t.open('xb') as b,gzip.GzipFile(filename='',mode='wb',fileobj=b,mtime=0) as z:shutil.copyfileobj(a,z)
for p in sorted(R.rglob('*')):
 if p.is_file() and '__pycache__' not in p.parts:
  assert p.suffix.upper() not in ('.ACD','.BAK') and 'credential' not in p.name.lower()
  copy(p,OUT/'Runtime'/p.relative_to(R))
for n in ('authorization.json','preflight.json','deploy_attempt.json','backup.sha256','canonical.sha256'):copy(W/n,OUT/'Session'/n)
for n in ('echo_before_s3j.L5X','canonical_downloaded.L5X','genealogy_restored.L5X'):pack(W/n,OUT/'Session'/(n+'.gz'))
for n in updates:copy(ROOT/n,OUT/'Documentation'/n)
artifacts=[]
for p in sorted(OUT.rglob('*')):
 if p.is_file():
  v=dict(path=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size,sha256=sha(p))
  if p.name.endswith('.gz'):v['expandedSha256']=hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()
  artifacts.append(v)
m=dict(schema='fraktal.ab.s3j-canonical-runtime',schemaVersion=1,date='2026-10-25',timeZone='America/Mexico_City',sealedUtc=datetime.now(timezone.utc).isoformat(),report=NAME+'.md',reportSha256=sha(E/(NAME+'.md')),status='native-accepted-genealogy-restored',nativeAccepted=True,acceptedScope='Local Echo 601FC87B sampled-word genealogy fixture through migration frame',sessionApprovalConsumed=True,approvalQuestionItemId=a['questionItemId'],approvalAnswer=a['answer'],downloadedAcdSha256=ACD,sourceSha256=pins['sourceSha256'],backupSha256=(W/'backup.sha256').read_text().strip(),sourceBindings=len(pins['sha256']),allBoundSourcesUnchangedDuringNativeSession=True,postSessionDocumentationUpdates=updates,abTestsBound=2249,rootTests=74,candidateChecks=41,candidatePairedCaptures=87,ioVectorCases=9,ioSourceWritesIncludingRestoration=80,ioPairs=10,baselineChecks=31,pairedCapturesReplayed=98,proofAttempts={k:replay['attempts'][k] for k in ('minimum','maximum')},measurements=scan,capacity=dict(used=1743080,available=1402648,total=3145728,displayedPercent=55),newDumps=False,failedOrRepeatedControllerStages=0,faultClears=0,clockChanges=0,powerOperations=0,hardKills=0,priorSeals=seals,priorArtifactCount=total,artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(x['bytes'] for x in artifacts),credentialFilesArchived=False,nativeAcdFilesArchived=False,committed=False,pushed=False)
with (OUT/'manifest.json').open('x') as f:json.dump(m,f,indent=2)
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),sourceBindings=len(pins['sha256']),priorRecords=len(seals),priorArtifacts=total)))
