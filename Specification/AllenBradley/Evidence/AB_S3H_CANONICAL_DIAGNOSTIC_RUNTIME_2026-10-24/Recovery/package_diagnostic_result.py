"""Seal the recovery plus diagnostic attempt, including failures, without memory dumps."""
from pathlib import Path
import datetime,gzip,hashlib,json,re
R=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley';E=AB/'Evidence'
D=Path('C:/work/fraktal-ab-s3h-20261023/runtime_b1730f6ce242464a817b4d8eb4d38abb')
P=D.parent/'diagnostic_0b74f072e0d74c7c97531e07dec70898'
NAME='AB_S3H_CANONICAL_DIAGNOSTIC_RUNTIME_2026-10-24';DEST=E/NAME;REPORT=E/(NAME+'.md')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((R/'diagnostic_session_closure_01.json').read_text())
assert v['passed'] and not v['stageAccepted'] and v['candidateDownloadSucceeded'] and v['finalGenealogyReady']
for label in ('ab_diagnostic_closure_01','root_diagnostic_result_01','spec_diagnostic_result_01',
              'contracts_diagnostic_result_01','consistency_diagnostic_result_01','whitespace_diagnostic_result_01',
              'record_diagnostic_result_01','diagnostic_closure_01','end_readiness_01'):
    assert json.loads((R/(label+'_exit.json')).read_text())['exitCode']==0,label
assert 'Ran 2149 tests' in (R/'ab_diagnostic_closure_01.log').read_text()
assert 'Ran 74 tests' in (R/'root_diagnostic_result_01.log').read_text()
assert json.loads((R/'end_readiness_01.json').read_text())['passed']
assert json.loads((R/'recovery_download_01_exit.json').read_text())['exitCode']!=0
assert json.loads((D/'candidate_regressions_01_exit.json').read_text())['exitCode']==1
pins=json.loads((D/'initial_source_verification.json').read_text())
for name,h in pins['sha256'].items():assert sha(ROOT/name)==h,name
for name,h in pins['diagnosticBindings'].items():assert sha(P/name)==h,name
assert sha(P/'capacity_review.ACD').upper()==pins['preparedAcdSha256']

prior=[]
for path in sorted(E.glob('AB_*/manifest.json')):
    if not any(prefix in path.parent.name for prefix in ('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL',
            'AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL','AB_S3E_CANONICAL',
            'AB_S3F_CANONICAL','AB_S3G_CANONICAL','AB_S3H_CANONICAL')):continue
    m=json.loads(path.read_text())
    for item in m['artifacts']:
        p=path.parent/item['path'];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'].lower(),p
        if item.get('expandedSha256'):
            assert hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()==item['expandedSha256'].lower(),p
    if m.get('report'):assert sha(E/m['report'])==m['reportSha256'].lower()
    prior.append(dict(name=path.parent.name,artifacts=len(m['artifacts']),manifestSha256=sha(path)))
assert len(prior)==38 and sum(row['artifacts'] for row in prior)==8615
assert not DEST.exists();DEST.mkdir()
expanded={}
def copy(path,name):
    assert path.suffix.lower() not in ('.acd','.bak','.dmp','.dat','.bin','.sqlite','.dll','.exe','.pdb')
    assert 'credential' not in path.name.lower()
    raw=path.read_bytes()
    if path.suffix.lower()=='.l5x':
        name+='.gz';expanded[name]=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0)
    target=DEST/name;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(raw)

for folder,prefix in ((R,'Recovery'),(D,'Diagnostic')):
    for path in sorted(folder.rglob('*')):
        if not path.is_file() or any(part in ('bin','obj','__pycache__') for part in path.parts):continue
        if path.name.lower().endswith(('.acd','.bak','.dmp','.dat','.bin','.sqlite','.dll','.exe','.pdb')):continue
        if folder==R and path.name.startswith(('package_diagnostic_result_01','diagnostic_result_seal_')):continue
        assert 'credential' not in path.name.lower(),path
        copy(path,prefix+'/'+path.relative_to(folder).as_posix())
for name in ('authorization.json','canonical.sha256','canonical_prepared_compare.json','capacity_review.json',
             'native_summary_final.json','diagnostic_verification_01.json','diagnostic_seal_verification_01.json',
             'source_bindings_01.json','prepared_image_reference.json','backup.sha256'):
    copy(P/name,'Preparation/'+name)
for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md',
             'AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md','AB_FROZEN_CONTRACTS_V2.json'):
    copy(AB/name,'Target/'+name)
rows=[]
for path in sorted(DEST.rglob('*')):
    if not path.is_file():continue
    name=path.relative_to(DEST).as_posix();row=dict(path=name,bytes=path.stat().st_size,sha256=sha(path))
    if name in expanded:row['expandedSha256']=expanded[name]
    rows.append(row)
m=dict(schema='fraktal.ab.s3h-echo-recovery-diagnostic-runtime-evidence',schemaVersion=1,date='2026-10-24',
    timeZone='America/Mexico_City',sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    report=REPORT.name,reportSha256=sha(REPORT),status='echo-recovered-candidate-download-pass-coherence-fail-genealogy-restored',
    controllerRecovered=True,candidateDownloadSucceeded=True,stageAccepted=False,sessionApprovalConsumed=True,
    candidatePassedChecks=30,candidateFailedChecks=1,candidateChecksNotReached=10,recoveryBaselineChecks=31,rollbackBaselineChecks=31,
    recordedChecks=93,acceptedChecks=92,independentPartialReplays=64,diagnosticWindows=65,
    fullAbTests=2149,rootTests=74,recoveryAuthorizationTests=7,sourceBindings=159,diagnosticBindings=2,
    generatedPlcAndObserverSourcesUnchanged=True,capacityExactImageReused=True,
    nativeMemoryDumpsArchived=False,credentialFilesArchived=False,nativeAcdFilesArchived=False,
    vendorBinariesModified=False,hardKills=0,newNativeDumpsObserved=False,faultClears=0,clockChanges=0,
    finalGenealogyReady=True,priorSeals=prior,artifacts=rows,artifactCount=len(rows),totalBytes=sum(row['bytes'] for row in rows))
with (DEST/'manifest.json').open('x') as f:json.dump(m,f,indent=2)
for row in rows:assert sha(DEST/row['path'])==row['sha256']
result=dict(passed=True,artifactCount=len(rows),reportSha256=sha(REPORT),manifestSha256=sha(DEST/'manifest.json'),
    predecessorRecords=38,predecessorArtifacts=8615,currentRecords=39,currentArtifacts=8615+len(rows),
    candidateDownloadSucceeded=True,stageAccepted=False,finalGenealogyReady=True)
with (R/'diagnostic_result_seal_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
