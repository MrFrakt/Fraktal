"""Close the failed diagnostic session at its measured acceptance boundary."""
from pathlib import Path
import datetime,gzip,hashlib,json,statistics,xml.etree.ElementTree as ET
R=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal')
D=Path('C:/work/fraktal-ab-s3h-20261023/runtime_b1730f6ce242464a817b4d8eb4d38abb')
P=D.parent/'diagnostic_0b74f072e0d74c7c97531e07dec70898'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for directory,labels in (
    (R,('recovery_download_02','recovery_log_audit_01','recovery_readback_01','recovery_access_01',
        'recovery_baseline_01','recovery_manual_01','recovery_final_checks_01','recovery_preflight_01',
        'reverse_engineering_review_01')),
    (D,('guard_initial_02','manual_initial_02','preflight_initial_02','backup_02','backup_log_audit_02',
        'backup_access_02','preflight_before_download_01','deploy_01','deploy_log_audit_01','deploy_readback_01',
        'deploy_access_01','guard_candidate_01','restore_genealogy_01','restore_log_audit_01','restore_access_01',
        'restore_readback_01','guard_baseline_01','baseline_regressions_01','manual_final_01','final_checks_01',
        'preflight_final_01','baseline_timing_01','diagnostic_partial_replay_01','diagnostic_analysis_02')),
):
    for label in labels:assert json.loads((directory/(label+'_exit.json')).read_text())['exitCode']==0,label
candidate=json.loads((D/'candidate_regressions_01.json').read_text())
baseline=json.loads((D/'baseline_regressions_01.json').read_text())
recovered=json.loads((R/'recovery_baseline_01.json').read_text())
for fixture in (baseline,recovered):
    assert len(fixture['rows'])==31 and all(row['passed'] for row in fixture['rows'])
    assert fixture['restored'] and fixture['policyRestored'] and not fixture.get('error')
assert candidate['restored'] and candidate['policyRestored'] and candidate['error']=='sequence equivalence failed'
assert len(candidate['rows'])==21 and sum(row.get('passed') is True for row in candidate['rows'])==20
assert len(candidate['s3hAccessRows'])==2 and len(candidate['s3hConfigRows'])==8
assert all(row['passed'] for key in ('s3hAccessRows','s3hConfigRows') for row in candidate[key])
assert json.loads((D/'diagnostic_partial_replay_01.json').read_text())['captures']==64
session=json.loads((D/'session_execution_01.json').read_text())
assert not session['passed'] and session['restoreError'] is None
analysis=json.loads((D/'diagnostic_analysis_02.json').read_text())
assert analysis['acceptedComparisons']==64
assert analysis['failedFixtureCapture']['language']=='SFC' and analysis['failedFixtureCapture']['case']=='abort'
assert analysis['failure']['generationDeltas']==[[1,5],[2,11]]
pins=json.loads((D/'initial_source_verification.json').read_text())
for name,h in pins['sha256'].items():assert sha(ROOT/name)==h,name
for name,h in pins['diagnosticBindings'].items():assert sha(P/name)==h,name
assert sha(P/'capacity_review.ACD').upper()==pins['preparedAcdSha256']
assert sha(P/'s3h_candidate_03.L5X')==pins['sourceSha256']
assert sha(P/'session/bin/Debug/net8.0/win-x86/S3hSession.exe')==pins['sessionExecutableSha256']
assert sha(P/'echo_before_s3h.ACD').upper()==(P/'backup.sha256').read_text().strip()
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')).upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
for path in (R/'recovery_readback_01.log',D/'deploy_readback_01.log',D/'restore_readback_01.log'):
    assert json.loads(path.read_text())['Equivalent']
periodic=ET.parse(P/'s3h_candidate_03.L5X').find('./Controller/Tasks/Task')
assert periodic is not None and periodic.get('Type')=='PERIODIC' and periodic.get('Rate')=='10'
accepted=[item for key,items in candidate.items() if key.endswith('Pairs') for item in items if item['passed']]
first=json.loads(gzip.decompress(Path(accepted[0]['output']).read_bytes()))['pair']['capture']
templates={item['handle']:item for item in first['templates']};symbols={item['name']:item for item in first['symbols']}
sizes=[]
for record in first['records']:
    size=len(bytes.fromhex(record['rawHex']));assert size==templates[symbols[record['tag']]['handle']]['byteSize']
    sizes.append(dict(tag=record['tag'],nativeTemplateBytes=size))
assert [row['nativeTemplateBytes'] for row in sizes]==[133744,7308,16616]
samples=json.loads((D/'baseline_timing_01.json').read_text())['samples'];prefix='FRK_Press_HealthProbe.'
timing=dict(samples=len(samples),medianUs=statistics.median(row['values'][prefix+'TaskLastScanUs'] for row in samples),
    minimumUs=min(row['values'][prefix+'TaskLastScanUs'] for row in samples),
    maximumLastUs=max(row['values'][prefix+'TaskLastScanUs'] for row in samples),
    cumulativeMaximumUs=max(row['values'][prefix+'TaskMaxScanUs'] for row in samples),
    overlaps=max(row['values'][prefix+'TaskOverlapCount'] for row in samples))
assert len(samples)==20 and timing['overlaps']==0
controller=Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root')
dumps=[dict(path=path.relative_to(controller).as_posix(),bytes=path.stat().st_size,
            modifiedUtc=datetime.datetime.fromtimestamp(path.stat().st_mtime,datetime.timezone.utc).isoformat())
       for path in sorted(controller.rglob('*.dmp'))]
before=json.loads((R/'dumps_before_candidate_01.json').read_text())['dumpFiles']
assert dumps==before==[]
assert json.loads((D/'final_checks_01.json').read_text())['passed']
report=dict(passed=True,stageAccepted=False,controllerRecovered=True,candidateDownloadSucceeded=True,
    candidateFixtureAccepted=False,sessionStoppedAtCoherenceGate=True,
    candidateRecordedBaseRows=21,candidatePassedBaseRows=20,candidateAccessRows=2,candidateConfigRows=8,
    candidatePassedChecks=30,candidateFailedChecks=1,candidateChecksNotReached=10,
    recoveryBaselineChecks=31,rollbackBaselineChecks=31,acceptedChecksThisContinuation=92,recordedChecksThisContinuation=93,
    passingPairs=64,independentPartialReplays=64,failedPairs=1,failedCapture=analysis['failedFixtureCapture'],
    failedWindow=analysis['failure'],noObservedValueOrTypeMismatchInAcceptedPairs=True,
    nativeTaskPeriodMs=10,nativeRecordBytes=sizes,totalNativeRecordBytes=sum(row['nativeTemplateBytes'] for row in sizes),
    postFailureTaskSampleQualification=analysis['qualification'],baselineTiming=timing,
    capacityUsedBlocks=2501720,capacityAvailableBlocks=644008,capacityTotalBlocks=3145728,
    capacityReusedExactPreparedImage=True,sourceBindings=159,diagnosticBindings=2,
    allNativeSessionSourcesUnchanged=True,originalGenealogyAcdNeverOpened=True,
    preparedAcdSha256=pins['preparedAcdSha256'],sdkSavedAcdSha256=sha(P/'s3h_canonical.ACD').upper(),
    backupAcdSha256=sha(P/'echo_before_s3h.ACD').upper(),baselineReady=True,
    finalGenealogyReady=True,newNativeDumpsObserved=False,powerStateOperations=0,hardKills=0,faultClears=0,clockChanges=0,
    sessionApprovalConsumed=True,sessionApprovalQuestion='call_b76d12f2f038411386f83c339fcd94e0:0',
    ownerCurrentRetryInstruction='retry download on echo',
    missingGates=['All 41 candidate checks','Complete 88-pair/rendition trace acceptance','Final candidate idle/generic acquisition','Final 20-sample candidate timing'],
    capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (R/'diagnostic_session_closure_01.json').open('x') as out:json.dump(report,out,indent=2)
with (R/'authorization_consumed_01.json').open('x') as out:
    json.dump(dict(consumed=True,approvalQuestion=report['sessionApprovalQuestion'],capturedUtc=report['capturedUtc'],
                   reason='Guarded recovery, candidate diagnostic and verified genealogy rollback completed; candidate stopped at unchanged coherence gate.'),out,indent=2)
with (R/'dumps_after_session_01.json').open('x') as out:
    json.dump(dict(capturedUtc=report['capturedUtc'],readOnly=True,dumpFiles=dumps,newDumpsObserved=False),out,indent=2)
print(json.dumps({key:report[key] for key in ('passed','controllerRecovered','candidateDownloadSucceeded','stageAccepted',
    'candidatePassedChecks','candidateFailedChecks','candidateChecksNotReached','passingPairs','recoveryBaselineChecks',
    'rollbackBaselineChecks','totalNativeRecordBytes','baselineTiming','finalGenealogyReady','newNativeDumpsObserved')}))
