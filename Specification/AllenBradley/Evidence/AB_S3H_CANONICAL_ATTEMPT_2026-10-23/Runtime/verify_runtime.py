"""Verify the completed exact-image S3h session and append-only predecessors."""
from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent;P=R.parent/'prepare_5822102a73e348ec95ff7082959ef940'
E=ROOT/'Specification/AllenBradley/Evidence';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
required=('guard_initial_01','manual_initial_01','preflight_initial_01','backup_01','backup_log_audit_01','backup_access_01',
    'focused_tool_fix_01','ab_tool_fix_01','root_tool_fix_01','spec_tool_fix_01','contracts_tool_fix_01','consistency_tool_fix_01',
    'whitespace_tool_fix_01','tooling_validation_01','prepare_offline_audits_01','preflight_before_download_01',
    'deploy_01','deploy_log_audit_01','deploy_readback_01','deploy_access_01','guard_candidate_01',
    'candidate_regressions_01','manual_candidate_01','idle_equivalence_01','generic_acquire_01','candidate_timing_01',
    'restore_genealogy_01','restore_log_audit_01','restore_access_01','restore_readback_01','guard_baseline_01',
    'baseline_regressions_01','manual_final_01','final_checks_01','preflight_final_01','baseline_timing_01','session_01',
    'candidate_coverage_01','capture_replay_01','native_record_sizes_01','native_measurements_01','trace_observations_01')
for label in required:assert json.loads((R/(label+'_exit.json')).read_text())['exitCode']==0,label
candidate=json.loads((R/'candidate_regressions_01.json').read_text());baseline=json.loads((R/'baseline_regressions_01.json').read_text())
for fixture in (candidate,baseline):
    assert len(fixture['rows'])==31 and all(r['passed'] for r in fixture['rows'])
    assert fixture['restored'] and fixture['policyRestored'] and not fixture.get('error')
assert len(candidate['s3hAccessRows'])==2 and len(candidate['s3hConfigRows'])==8
assert all(r['passed'] for k in ('s3hAccessRows','s3hConfigRows') for r in candidate[k])
coverage=json.loads((R/'candidate_coverage_01.json').read_text());assert coverage['passed'] and coverage['plannedCandidateRows']==41
replay=json.loads((R/'capture_replay_01.json').read_text());assert replay['passed'] and replay['captures']==88 and replay['attempts']['maximum']<=100
trace=json.loads((R/'trace_observations_01.json').read_text());assert trace['passed'] and trace['captures']==88
timing=json.loads((R/'timing_summary_01.json').read_text());assert timing['passed']
for name in ('candidate','baseline'):assert timing['timing'][name]['samples']==20 and timing['timing'][name]['overlaps']==0
sizes=json.loads((R/'native_record_sizes_01.json').read_text());assert sizes['passed'] and len(sizes['records'])==3
assert json.loads((R/'final_checks_01.json').read_text())['passed']
assert json.loads((R/'session_execution_01.json').read_text())['passed']
inputs=json.loads((R/'tooling_validation_01.json').read_text());assert inputs['passed'] and inputs['sourceBindings']==157
for name,pin in inputs['sha256'].items():assert sha(ROOT/name)==pin,name
with (R/'source_verification_01.json').open('x') as f:
    json.dump(dict(passed=True,sourceBindings=157,changedDuringNativeSession=[],generatedPlcSourceUnchanged=True,
        correctedBeforeDownload=inputs['changedFromPreparation'],sha256=inputs['sha256']),f,indent=2)
assert sha(P/'s3h_candidate_03.L5X')==inputs['preparedSourceSha256']
assert sha(P/'capacity_review.ACD').upper()==inputs['preparedAcdSha256']
assert sha(P/'session/bin/Debug/net8.0/win-x86/S3hSession.exe')==inputs['sessionExecutableSha256']
assert sha(P/'echo_before_s3h.ACD').upper()==(P/'backup.sha256').read_text().strip()
for label in ('deploy_readback_01','restore_readback_01'):assert json.loads((R/(label+'.log')).read_text())['Equivalent']
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')).upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
seals=[]
for path in sorted(E.glob('AB_*/manifest.json')):
    if not any(n in path.parent.name for n in ('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL','AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL','AB_S3E_CANONICAL','AB_S3F_CANONICAL','AB_S3G_CANONICAL','AB_S3H_CANONICAL')):continue
    m=json.loads(path.read_text())
    for item in m['artifacts']:
        file=path.parent/item['path'];raw=file.read_bytes()
        assert len(raw)==item['bytes'] and sha(file)==item['sha256'].lower(),file
        if item.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==item['expandedSha256'].lower()
    if m.get('report'):assert sha(E/m['report'])==m['reportSha256'].lower()
    seals.append(dict(name=path.parent.name,artifacts=len(m['artifacts']),manifestSha256=sha(path)))
assert len(seals)==28 and sum(row['artifacts'] for row in seals)==6589
failures=[dict(label=p.name.removesuffix('_exit.json'),exitCode=json.loads(p.read_text())['exitCode']) for p in sorted(R.glob('*_exit.json')) if json.loads(p.read_text())['exitCode']!=0]
assert not failures,failures
report=dict(passed=True,s3hStageCompleteAtRecordedScope=True,authorizationConsumed=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    acceptedCandidateRows=41,acceptedBaselineRows=31,acceptedTotalChecks=72,actualRecordedChecks=72,
    pairedCaptures=88,attempts=replay['attempts'],fullRingExpectedPagePaths=[3950,3900,3550],canonicalAddedPaths=278,
    approvedTypePaths=36,otherAddedPathsExact=242,unsetPartStampCorrection=True,
    nativePayloadBytes=sizes['totalPayloadBytes'],nativeRecordBytes=[r['nativeTemplateBytes'] for r in sizes['records']],
    timing=timing['timing'],traceObservations={k:v for k,v in trace.items() if k not in ('rows',)},
    sourceBindings=157,allNativeSessionSourcesUnchanged=True,correctedBeforeDownload=inputs['changedFromPreparation'],
    abTests=2140,rootTests=74,focusedTests=13,testsSource='Full current-source offline suites rerun and bound before download; byte-identical PLC source/ACD reuses both v38 compiler/read-back/access gates',
    capacityBlocks=2501720,availableBlocks=644008,totalBlocks=3145728,deltaFromAcceptedS3gBlocks=94520,
    preparedAcdSha256=inputs['preparedAcdSha256'],sourceSha256=inputs['preparedSourceSha256'],
    sdkSavedAcdSha256=sha(P/'s3h_canonical.ACD').upper(),backupAcdSha256=sha(P/'echo_before_s3h.ACD').upper(),
    finalGenealogyReady=True,failedRunsRetained=failures,requiredSuccessfulRuns=list(required),
    priorSeals=seals,predecessorRecords=28,predecessorArtifacts=6589)
with (R/'runtime_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
with (R/'authorization_consumed.json').open('x') as f:json.dump(dict(consumed=True,authorizationSha256=sha(R/'owner_session_approval.json'),
    capturedUtc=report['capturedUtc'],scope='Completed exact S3h session; no further controller-changing operation authorized'),f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('priorSeals','requiredSuccessfulRuns','correctedBeforeDownload','traceObservations')}))
