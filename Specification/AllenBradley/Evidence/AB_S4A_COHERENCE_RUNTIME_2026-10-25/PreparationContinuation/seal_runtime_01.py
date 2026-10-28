"""Append-only S4a acceptance seal; prior records and credentials are untouched."""
from pathlib import Path
import datetime,gzip,hashlib,json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;D=W.parent/'session_01'
E=R/'Specification/AllenBradley/Evidence';NAME='AB_S4A_COHERENCE_RUNTIME_2026-10-25'
OUT=E/NAME;REPORT=E/(NAME+'.md')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
load=lambda path:json.loads(path.read_bytes())
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,ensure_ascii=False);stream.write('\n')

assert not OUT.exists()
session=load(D/'session_result.json');summary=load(D/'runtime_summary_01.json')
assert session['passed'] and summary['passed'] and session['authorizationConsumed']
for label in ('session_execution_01','summarize_runtime_01','native_source_verify_01','post_runtime_root_tests_01',
              'post_runtime_spec_01','post_runtime_contracts_01','post_runtime_consistency_01','post_runtime_whitespace_01'):
    assert load(D/(label+'_exit.json'))['exitCode']==0,label
assert load(D/'native_source_verified_01.json')['unchangedBoundFiles']==431
save(D/'owner_authorization_consumed_01.json',dict(serial='601FC87B',
    approvalQuestion='call_0aa6207bba714a73bb1e80ee242d1981:0',
    ownerInstruction='Approve guarded S4a qualification',authorizationConsumed=True,
    authorizationSha256=sha((D/'authorization.json').read_bytes()),
    currentControllerChangesAuthorized=False,sessionResultSha256=sha((D/'session_result.json').read_bytes()),
    completedUtc=session['utc']))

prepared=E/'AB_S4A_COHERENCE_PREPARATION_2026-10-25/manifest.json'
names={row['name'] for row in load(prepared)['priorSeals']}|{prepared.parent.name}
seals=[];total=0
for index,name in enumerate(sorted(names),1):
    path=E/name/'manifest.json';held=load(path)
    for row in held['artifacts']:
        raw=(path.parent/row['path']).read_bytes()
        assert sha(raw)==row['sha256'].lower() and len(raw)==row['bytes'],(name,row['path'])
        if row.get('expandedSha256'):assert sha(gzip.decompress(raw))==row['expandedSha256'].lower()
    if held.get('reportSha256'):assert sha((E/held['report']).read_bytes())==held['reportSha256'].lower()
    seals.append(dict(name=name,manifestSha256=sha(path.read_bytes()),artifacts=len(held['artifacts'])))
    total+=len(held['artifacts'])
    if index%20==0:print(json.dumps(dict(priorSealsChecked=index,total=len(names))),flush=True)
save(D/'prior_seals_runtime_01.json',dict(passed=True,records=len(seals),artifacts=total,rows=seals))

artifacts=[]
def archive(source,relative,compress=False):
    raw=source.read_bytes();data=gzip.compress(raw,mtime=0) if compress else raw
    name=relative+('.gz' if compress else '')
    path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write(data)
    row=dict(path=name,bytes=len(data),sha256=sha(data))
    if compress:row['expandedSha256']=sha(raw)
    artifacts.append(row)

for source in sorted(D.rglob('*')):
    if not source.is_file() or any(p in ('bin','obj','__pycache__') for p in source.relative_to(D).parts):continue
    if source.suffix.lower() not in ('.py','.json','.gz','.log','.txt','.sha256','.l5x','.cs','.csproj'):continue
    assert 'credential' not in source.name.lower()
    archive(source,'Runtime/'+source.relative_to(D).as_posix(),source.suffix.lower() in ('.log','.l5x'))
for name in ('authorize_session_01.py','summarize_runtime_01.py','verify_native_sources_01.py','write_runtime_report_01.py',
             'seal_runtime_01.py','authorize_session_01.log','authorize_session_01_exit.json'):
    archive(W/name,'PreparationContinuation/'+name,name.endswith('.log'))
for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_S4_COHERENCE_REVIEW_2026-10-25.md',
             'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md','AB_FROZEN_CONTRACTS_V2.json'):
    archive(R/'Specification/AllenBradley'/name,'CurrentDocs/'+name)

manifest=dict(schema='fraktal.ab.s4a-coherence-runtime',schemaVersion=1,date='2026-10-25',
    timeZone='America/Mexico_City',sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),nativeAccepted=True,
    nativeScope=summary['proofScope'],shippingClientAccepted=False,physicalAccepted=False,
    ownerInstruction='Approve guarded S4a qualification',approvalQuestion='call_0aa6207bba714a73bb1e80ee242d1981:0',
    authorizationConsumed=True,currentControllerChangesAuthorized=False,
    preparedAcdSha256='07C54E8DCE8D70A1EC487684B65F3596922D615448881AA05470304821CC2FF3',
    sourceSha256='20F27F80CF9D0AEFEFA72EB64848927AE6076CF05CB544073575A55728825996',
    rollbackOriginalSha256='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084',
    sourcePreparationManifestSha256=sha(prepared.read_bytes()),
    candidateChecks=31,baselineChecks=31,idleValueTypePaths=4428,genericValues=4428,genericModules=7,
    qualifiedGroups=8,qualityCounts=summary['qualityCounts'],acceptedWindowUs=summary['acceptedWindowUs'],
    coherentRowsReplayed=798,canonicalCapturesReplayed=2,
    measuredOfflineCapacityBlocks=dict(used=1904400,available=1241328,total=3145728,displayedPercent=60),
    candidateTiming=summary['candidateTiming'],baselineTiming=summary['baselineTiming'],
    genealogyRestored=True,originalHostDocumentsRestored=5,finalChecksPassed=True,
    faultClears=0,clockChanges=0,powerOperations=0,hardKills=0,dumpFiles=0,
    abTests=2320,rootTests=74,flutterPassed=608,flutterSkipped=12,
    priorSeals=seals,priorArtifacts=total,artifacts=artifacts,artifactCount=len(artifacts),
    credentialFilesArchived=False,nativeAcdFilesArchived=False,committed=False,pushed=False)
save(OUT/'manifest.json',manifest)
for row in artifacts:
    raw=(OUT/row['path']).read_bytes()
    assert sha(raw)==row['sha256'] and len(raw)==row['bytes']
    if row.get('expandedSha256'):assert sha(gzip.decompress(raw))==row['expandedSha256']
assert sha(REPORT.read_bytes())==manifest['reportSha256']
result=dict(passed=True,manifest=str(OUT/'manifest.json'),manifestSha256=sha((OUT/'manifest.json').read_bytes()),
    artifacts=len(artifacts),priorSeals=len(seals),priorArtifacts=total,authorizationConsumed=True,
    genealogyRestored=True,currentControllerChangesAuthorized=False)
save(D/'sealed_runtime_01.json',result)
print(json.dumps(result),flush=True)
