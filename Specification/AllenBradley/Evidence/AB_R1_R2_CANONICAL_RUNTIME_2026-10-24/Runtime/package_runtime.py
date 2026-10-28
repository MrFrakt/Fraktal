from datetime import datetime,timezone
from pathlib import Path
import gzip,hashlib,json,re,shutil
R=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');E=ROOT/'Specification/AllenBradley/Evidence'
W=Path('C:/work/fraktal-ab-r1-r2-20261024/prepare_8f74e954758141dd81821a0c1316c2ef')
NAME='AB_R1_R2_CANONICAL_RUNTIME_2026-10-24';OUT=E/NAME;assert not OUT.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
pins=json.loads((R/'initial_source_verification.json').read_bytes())
for name,pin in pins['sha256'].items():assert sha(ROOT/name)==pin,name
start=json.loads((R/'start_execution_01.json').read_bytes());session=json.loads((R/'session_execution_01.json').read_bytes())
assert start['passed'] and session['passed'] and all(x['exitCode']==0 for x in session['steps'])
assert len({x['label'] for x in session['steps']})==len(session['steps'])==25
candidate=json.loads((R/'candidate_regressions_01.json').read_bytes());rows=candidate['rows']+[x for k,v in candidate.items() if k.endswith('Rows') for x in v]
assert len(rows)==41 and all(x['passed'] for x in rows)
assert candidate['s3iNativeChecks']['passed'] and candidate['s3iNativeChecks']['cases']==8
calendar=json.loads((R/'calendar_01.json').read_bytes());assert calendar['passed'] and len(calendar['rows'])==7 and 0<calendar['calendarWriteCount']<=64 and calendar['configurationRestored']
retained=json.loads((W/'retained_cycle.json').read_bytes());assert retained['Passed'] and not retained['DownloadPerformed'] and retained['SourceAcdUnchanged']
retention=json.loads((R/'retention_01.json').read_bytes());assert retention['passed'] and retention['nativeFirstScanChecks']['cases']==8
assert all(x['passed'] for x in json.loads((R/'baseline_regressions_01.json').read_bytes())['rows'])
assert len(json.loads((R/'baseline_regressions_01.json').read_bytes())['rows'])==31
assert json.loads((R/'final_checks_01.json').read_bytes())['passed']
for name in ('dumps_before_session_01','dumps_after_session_01'):assert json.loads((R/(name+'.json')).read_bytes())['dumpFiles']==[]
replay=json.loads((R/'replay_01.json').read_bytes());assert replay['passed'] and replay['captures']==97
scan=json.loads((R/'candidate_timing_summary_01.json').read_bytes());assert scan['passed'] and scan['samples']==20 and scan['overlaps']==0 and scan['cumulativeMaxScanUs']<scan['periodUs']==10000
approval=json.loads((R/'owner_session_approval.json').read_bytes());consumed=json.loads((R/'owner_session_consumed.json').read_bytes())
assert approval['CurrentOwnerApproved'] and not consumed['CurrentOwnerApproved'] and consumed['Consumed']
assert not json.loads((W/'authorization.json').read_bytes())['CurrentOwnerApproved']
ACD=pins['preparedAcdSha256'];assert json.loads((W/'deploy_attempt.json').read_bytes())['CanonicalSha256']==ACD
assert sha(W/'capacity_review.ACD').upper()==ACD==sha(W/'retention_control.ACD').upper()
assert sha(W/'s3i_r1_r2.L5X')==sha(W/'s3i_bench_05.L5X')==pins['sourceSha256']
seals=[];total=0;pat=re.compile(r'AB_S(0|1|2|3[A-Z]?)_(CANONICAL|SUPPLEMENTARY)_')
for p in sorted(E.glob('AB_*/manifest.json')):
 if not (pat.match(p.parent.name) or p.parent.name.startswith('AB_R1_R2_')):continue
 m=json.loads(p.read_bytes())
 for a in m['artifacts']:
  raw=(p.parent/a['path']).read_bytes();assert len(raw)==a['bytes'] and hashlib.sha256(raw).hexdigest()==a['sha256'].lower(),(p,a['path'])
  if a.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==a['expandedSha256'].lower()
 if m.get('report') and m.get('reportSha256'):assert sha(E/m['report'])==m['reportSha256'].lower()
 total+=len(m['artifacts']);seals.append(dict(name=p.parent.name,manifestSha256=sha(p),artifacts=len(m['artifacts'])))
def copy(source,target):
 target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists();shutil.copyfile(source,target)
def pack(source,target):
 target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists()
 with source.open('rb') as a,target.open('wb') as b,gzip.GzipFile(filename='',mode='wb',fileobj=b,mtime=0) as c:shutil.copyfileobj(a,c)
for p in sorted(R.rglob('*')):
 if not p.is_file() or '__pycache__' in p.parts:continue
 assert p.suffix.upper() not in ('.ACD','.BAK')
 copy(p,OUT/'Runtime'/p.relative_to(R))
for name in ('authorization.json','preflight.json','deploy_attempt.json','backup.sha256','retained_cycle.json','canonical.sha256'):
 copy(W/name,OUT/'Session'/name)
for name in ('echo_before_s3i.L5X','canonical_downloaded.L5X','genealogy_restored.L5X'):
 pack(W/name,OUT/'Session'/(name+'.gz'))
artifacts=[]
for p in sorted(OUT.rglob('*')):
 if not p.is_file():continue
 row=dict(path=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size,sha256=sha(p))
 if p.name.endswith('.gz'):row['expandedSha256']=hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()
 artifacts.append(row)
assert not any(x['path'].upper().endswith(('.ACD','.BAK')) or 'credential' in x['path'].lower() for x in artifacts)
manifest=dict(schema='fraktal.ab.r1-r2-canonical-runtime',schemaVersion=1,date='2026-10-24',timeZone='America/Mexico_City',sealedUtc=datetime.now(timezone.utc).isoformat(),
 report=NAME+'.md',reportSha256=sha(E/(NAME+'.md')),status='native-accepted-genealogy-restored',acceptedScope='Local Echo 601FC87B genealogy fixture through migration frame',
 r1NativeAccepted=True,r2NativeAccepted=True,sessionApprovalConsumed=True,approvalQuestionId=approval['ApprovalQuestionId'],approvalAnswer=approval['ApprovalAnswer'],
 downloadedAcdSha256=ACD,sourceSha256=pins['sourceSha256'],backupSha256=(W/'backup.sha256').read_text().strip(),
 sourceBindings=len(pins['sha256']),candidateChecks=41,baselineChecks=31,nativeFirstScanVectors=8,nativeFirstScanExecutions=2,
 calendarRows=len(calendar['rows']),calendarCommits=calendar['calendarWriteCount'],retainedProgramRunCycles=1,downloadInCycle=False,pairedCapturesReplayed=97,
 proofAttempts=dict(minimum=replay['attempts']['minimum'],maximum=replay['attempts']['maximum']),candidateTiming=scan,
 measuredCapacity=dict(used=1653432,available=1492296,total=3145728,displayedPercent=52),idlePaths=4010,modules=7,
 abTestsBound=2227,rootTestsBound=74,allBoundSourcesUnchanged=True,failedOrRepeatedControllerStages=0,newDumps=False,faultClears=0,clockChanges=0,powerOperations=0,hardKills=0,
 preparationManifestSha256=approval['PreparationManifestSha256'],priorSeals=seals,priorArtifactCount=total,
 artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(x['bytes'] for x in artifacts),credentialFilesArchived=False,nativeAcdFilesArchived=False,committed=False,pushed=False)
with (OUT/'manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2);f.write('\n')
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),bytes=manifest['totalBytes'],priorRecords=len(seals),priorArtifacts=total,sourceBindings=len(pins['sha256']))))
