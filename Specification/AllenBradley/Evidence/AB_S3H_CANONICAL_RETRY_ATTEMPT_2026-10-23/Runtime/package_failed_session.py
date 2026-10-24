from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent;P=R.parent/'retry_9d1da9a04d564b03bc2b176f5b17ea42'
AB=ROOT/'Specification/AllenBradley';E=AB/'Evidence';NAME='AB_S3H_CANONICAL_RETRY_ATTEMPT_2026-10-23';D=E/NAME;REPORT=E/(NAME+'.md')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
v=json.loads((R/'failed_session_closure_01.json').read_text());assert not v['stageAccepted'] and v['finalGenealogyReady']
assert json.loads((R/'restore_readback_01.log').read_text())['Equivalent']
for label in ('root_closure_01','spec_closure_01','contracts_closure_01','consistency_closure_01','failed_session_closure_01','finalize_failed_documents_01'):
    assert json.loads((R/(label+'_exit.json')).read_text())['exitCode']==0,label
sources=json.loads((R/'source_verification_failed_01.json').read_text())['sha256']
for name,pin in sources.items():assert sha((ROOT/name).read_bytes())==pin,name
prior=[]
for path in sorted(E.glob('AB_*/manifest.json')):
    if not any(n in path.parent.name for n in ('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL','AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL','AB_S3E_CANONICAL','AB_S3F_CANONICAL','AB_S3G_CANONICAL','AB_S3H_CANONICAL')):continue
    m=json.loads(path.read_text())
    for item in m['artifacts']:
        raw=(path.parent/item['path']).read_bytes();assert len(raw)==item['bytes'] and sha(raw)==item['sha256'].lower()
        if item.get('expandedSha256'):assert sha(gzip.decompress(raw))==item['expandedSha256'].lower()
    if m.get('report'):assert sha((E/m['report']).read_bytes())==m['reportSha256'].lower()
    prior.append(dict(name=path.parent.name,artifacts=len(m['artifacts']),manifestSha256=sha(path.read_bytes())))
assert len(prior)==30 and sum(r['artifacts'] for r in prior)==7199
assert not D.exists();D.mkdir()
def put(name,raw):
    p=D/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(raw)
def copy(path,name):
    raw=path.read_bytes()
    if path.suffix.lower()=='.l5x':name+='.gz';raw=gzip.compress(raw,mtime=0)
    put(name,raw)
for path in sorted(R.rglob('*')):
    if not path.is_file() or any(p in ('bin','obj','__pycache__') for p in path.parts):continue
    if path.name.startswith(('package_failed_01','failed_seal_verification_')) or path.suffix.lower()=='.acd' or 'credential' in path.name.lower():continue
    copy(path,'Runtime/'+path.relative_to(R).as_posix())
for name in ('authorization.json','deploy_attempt.json','backup.sha256','canonical.sha256','capacity_review.json',
    'echo_before_s3h.L5X','canonical_downloaded.L5X','genealogy_restored.L5X','session/Program.cs'):
    copy(P/name,'Session/'+name)
for name in sources:copy(ROOT/name,'Source/'+name)
for name in ('AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md','AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
    'AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','AB_FROZEN_CONTRACTS_V2.json'):
    copy(AB/name,'Target/'+name)
artifacts=[]
for path in sorted(D.rglob('*')):
    if not path.is_file():continue
    raw=path.read_bytes();row=dict(path=path.relative_to(D).as_posix(),bytes=len(raw),sha256=sha(raw))
    if path.name.lower().endswith('.l5x.gz'):row['expandedSha256']=sha(gzip.decompress(raw))
    artifacts.append(row)
m=dict(schema='fraktal.ab.s3h-canonical-retry-attempt-evidence',schemaVersion=1,date='2026-10-23',timeZone='America/Mexico_City',
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),
    status='coherence-gate-failed-genealogy-restored',stageAccepted=False,authorizationConsumed=True,
    passingPairs=3,failedPairs=1,baselineRegressions=31,finalGenealogyReady=True,
    sourceBindings=159,abTests=2148,rootTests=74,preparedAcdSha256=v['preparedAcdSha256'],
    sourceSha256=v['sourceSha256'],nativeRecordBytes=[133744,7308,16616],nativePayloadBytes=157668,
    priorSeals=prior,credentialFilesArchived=False,nativeAcdFilesArchived=False,artifactCount=len(artifacts),
    totalBytes=sum(a['bytes'] for a in artifacts),artifacts=artifacts)
put('manifest.json',json.dumps(m,indent=2).encode())
for row in artifacts:
    raw=(D/row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
assert sha(REPORT.read_bytes())==m['reportSha256']
result=dict(passed=True,sealedFailedAttempt=True,stageAccepted=False,genealogyRestored=True,
    artifactCount=len(artifacts),bytes=m['totalBytes'],reportSha256=m['reportSha256'],manifestSha256=sha((D/'manifest.json').read_bytes()),
    currentRecords=31,currentArtifacts=7199+len(artifacts),predecessorRecords=30,predecessorArtifacts=7199)
with (R/'failed_seal_verification_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
