"""Verify the completed authorized S3g scope and every predecessor seal."""
from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent
P=R.parent/'prepare_feb76c7a0968442293ee0d20b812eb17';E=ROOT/'Specification/AllenBradley/Evidence'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
required=('guard_readonly_01','ensure_manual_01','preflight_verify_01','backup_01','backup_log_audit_01','backup_access_01',
    'preflight_before_download_01','deploy_01','deploy_log_audit_01','deploy_readback_01','deploy_access_01','guard_candidate_01',
    'candidate_regressions_01','manual_candidate_01','idle_equivalence_01','generic_acquire_01','candidate_timing_01',
    'restore_genealogy_01','restore_log_audit_01','restore_access_01','restore_readback_01','guard_baseline_01',
    'baseline_regressions_01','manual_final_01','final_checks_01','preflight_final_01','baseline_timing_01','session_01',
    'offline_audit_sources_01','candidate_coverage_01','capture_replay_01','native_record_sizes_01','native_measurements_01')
for label in required:assert json.loads((R/(label+'_exit.json')).read_text())['exitCode']==0,label
candidate=json.loads((R/'candidate_regressions_01.json').read_text());baseline=json.loads((R/'baseline_regressions_01.json').read_text())
for fixture in (candidate,baseline):
    assert len(fixture['rows'])==31 and all(row['passed'] for row in fixture['rows'])
    assert fixture['restored'] and fixture['policyRestored'] and not fixture.get('error')
assert len(candidate['s3gAccessRows'])==2 and len(candidate['s3gConfigRows'])==8
assert all(row['passed'] for key in ('s3gAccessRows','s3gConfigRows') for row in candidate[key])
native=json.loads((R/'native_boundary_replay_01.json').read_text());assert native['passed'] and native['oeeVectors']==9 and native['profilerHighBitVectors']==2
coverage=json.loads((R/'candidate_coverage_01.json').read_text());assert coverage['passed'] and coverage['plannedCandidateRows']==41
replay=json.loads((R/'capture_replay_01.json').read_text());assert replay['passed'] and replay['captures']==88 and replay['attempts']['maximum']<=100
timing=json.loads((R/'timing_summary_01.json').read_text());assert timing['passed']
for name in ('candidate','baseline'):assert timing['timing'][name]['samples']==20 and timing['timing'][name]['overlaps']==0
sizes=json.loads((R/'native_record_sizes_01.json').read_text());assert sizes['passed'] and sizes['totalPayloadBytes']==145084
assert [r['nativeTemplateBytes'] for r in sizes['records']]==[121160,7308,16616]
assert json.loads((R/'final_checks_01.json').read_text())['passed']
assert json.loads((R/'session_execution_01.json').read_text())['passed']
bindings=json.loads((R/'runtime_inputs_01.json').read_text());assert bindings['sourceBindings']==151
for name,pin in bindings['sha256'].items():assert sha(ROOT/name)==pin,name
with (R/'source_verification_01.json').open('x') as f:
    json.dump(dict(passed=True,sourceBindings=151,changedSources=[],generatedPlcSourceUnchanged=True,sha256=bindings['sha256']),f,indent=2)
assert sha(P/'s3g_native_candidate_01.L5X')==bindings['preparedSourceSha256']
assert sha(P/'capacity_review.ACD').upper()==bindings['preparedAcdSha256']
assert sha(P/'session/bin/Debug/net8.0/win-x86/S3gSession.exe')==bindings['sessionExecutableSha256']
assert sha(P/'echo_before_s3g.ACD').upper()==(P/'backup.sha256').read_text().strip()
for label in ('deploy_readback_01','restore_readback_01'):assert json.loads((R/(label+'.log')).read_text())['Equivalent']
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')).upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
seals=[]
for path in sorted(E.glob('AB_*/manifest.json')):
    if not any(n in path.parent.name for n in ('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL','AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL','AB_S3E_CANONICAL','AB_S3F_CANONICAL','AB_S3G_CANONICAL')):continue
    m=json.loads(path.read_text())
    for item in m['artifacts']:
        file=path.parent/item['path'];raw=file.read_bytes()
        assert len(raw)==item['bytes'] and sha(file)==item['sha256'].lower(),file
        if item.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==item['expandedSha256'].lower()
    if m.get('report'):assert sha(E/m['report'])==m['reportSha256'].lower()
    seals.append(dict(name=path.parent.name,artifacts=len(m['artifacts']),manifestSha256=sha(path)))
assert len(seals)==25 and sum(row['artifacts'] for row in seals)==5689
failures=[dict(label=p.name.removesuffix('_exit.json'),exitCode=json.loads(p.read_text())['exitCode'])
    for p in sorted(R.glob('*_exit.json')) if json.loads(p.read_text())['exitCode']!=0]
assert not failures,failures
report=dict(passed=True,s3gStageComplete=True,authorizationConsumed=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    acceptedCandidateRows=41,acceptedNativeVectorResults=11,acceptedBaselineRows=31,acceptedTotalChecks=83,actualRecordedChecks=83,
    pairedCaptures=88,attempts=replay['attempts'],expectedPagePaths=[3672,3622,3272],canonicalAddedPaths=1055,
    approvedNumericPaths=200,approvedDependentValuePaths=224,unchangedOtherAddedPaths=631,
    nativePayloadBytes=145084,nativeRecordBytes=[121160,7308,16616],timing=timing['timing'],
    sourceBindings=151,allPreparedSourcesUnchanged=True,abTests=2127,rootTests=74,
    testsSource='Identical prepared sources: full discovery/root suites in the preparation seal; no implementation changes during runtime',
    capacityBlocks=2407200,availableBlocks=738528,totalBlocks=3145728,deltaFromAcceptedS3fBlocks=108752,
    preparedAcdSha256=bindings['preparedAcdSha256'],sourceSha256=bindings['preparedSourceSha256'],
    sdkSavedAcdSha256=sha(P/'s3g_canonical.ACD').upper(),backupAcdSha256=sha(P/'echo_before_s3g.ACD').upper(),
    finalGenealogyReady=True,failedRunsRetained=failures,requiredSuccessfulRuns=list(required),
    priorSeals=seals,predecessorRecords=25,predecessorArtifacts=5689)
with (R/'runtime_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
with (R/'authorization_consumed.json').open('x') as f:json.dump(dict(consumed=True,authorizationSha256=sha(R/'authorization.json'),
    capturedUtc=report['capturedUtc'],scope='Completed exact S3g session; no further controller-changing operation authorized'),f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('priorSeals','requiredSuccessfulRuns')}))
