"""Derive acceptance from raw results after rollback, including semantic desktop proof."""
from pathlib import Path
import gzip
import hashlib
import importlib.util
import json
import statistics

R=Path('C:/Users/SoftIndVM/Fraktal')
W=Path(__file__).parent
S=W.parent/'session_01'
def load(path):
    p=Path(path)
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def optional(name):
    p=S/name
    return load(p) if p.is_file() else None
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,value):
    with (S/name).open('x',encoding='utf-8',newline='') as f:
        json.dump(value,f,indent=2,ensure_ascii=False)
        f.write('\n')

session=load(S/'session_result.json')
baseline=load(S/'baseline_regressions.json')
final=load(S/'final_checks.json')
assert session['genealogyRestored'] and session['authorizationConsumed'] and session['rollbackError'] is None
assert len(baseline['rows'])==31 and all(row['passed'] for row in baseline['rows'])
assert baseline['restored'] and baseline['policyRestored']
assert final['passed'] and all(final['checks'].values()) and all(final['savedDocumentsEqual'].values())
assert not session['dumpFiles'] and all(session[k]==0 for k in ('faultClears','clockChanges','powerOperations','hardKills'))
assert sha('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD').upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
b=load(S/'source_bindings.json')
changed=[name for name,pin in b['sha256'].items() if sha(name).upper()!=pin.upper()]
assert changed==[(S/'s4b_read_view.ACD').as_posix()],changed
cases=optional('candidate_regressions.json') or {}
case_counts={key:dict(expected=count,recorded=len(cases.get(key,[])),
    passed=sum(row.get('passed') is True for row in cases.get(key,[])))
    for key,count in (('rows',31),('s4bAccessRows',2),('s4bConfigRows',8))}
candidate_passed=all(row['expected']==row['recorded']==row['passed'] for row in case_counts.values()) \
    and all(cases.get(key) is True for key in ('restored','policyRestored','s3fSetMediumEmpty'))
dart=optional('dart_qualification.json.gz') or {}
samples=dart.get('samples',[])
inspection=optional('runtime_inspection_01.json') or {}
replay=optional('paired_replay_01.json') or {}
idle=optional('idle_equivalence.json.gz') or {}
generic=optional('generic_snapshot.json.gz') or {}
config=optional('configuration_page_comparison_01.json') or {}
trace=optional('task_trace_analysis_01.json') or {}
timing=optional('candidate_timing.json') or {}
timings=[row['values'] for row in timing.get('samples',[])]
prefix='FRK_Press_HealthProbe.'
def timing_summary(rows):
    if not rows:return None
    return dict(lastScanMedianUs=statistics.median(row[prefix+'TaskLastScanUs'] for row in rows),
        cumulativeMaxUs=max(row[prefix+'TaskMaxScanUs'] for row in rows),
        overlaps=max(row[prefix+'TaskOverlapCount'] for row in rows))
candidate_scan=timing_summary(timings)
baseline_scan=timing_summary([row['values'] for row in load(S/'baseline_timing.json')['samples']])
idle_passed=idle.get('passed') is True and idle.get('comparison',{}).get('equal') is True \
    and idle.get('comparison',{}).get('typeAcceptance') is True
idle_paths=len(idle.get('pair',{}).get('canonical',{}).get('values',{}))
generic_values=len(generic.get('values',{}))
generic_modules=generic.get('moduleCount',0)
all_readonly_checks=candidate_passed and dart.get('passed') is True and replay.get('passed') is True \
    and replay.get('pairs')==87 and idle_passed and idle_paths==5407 \
    and generic_values==5407 and generic_modules==7 and config.get('passed') is True \
    and config.get('scalarComparisons')==1100 and config.get('pages')==len(dart.get('configurationPages',[]))==4
desktop=optional('desktop_live/result.json')
desktop_failure=optional('desktop_live/failure.json')
semantic=optional('desktop_semantic_acceptance.json')
desktop_passed=False
desktop_error=None
if desktop is not None:
    spec=importlib.util.spec_from_file_location('cold_semantic_coverage',S/'desktop_coverage.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        module.validate_coverage(desktop,load(S/'desktop_expected_inventory.json'),require_live=True)
        assert semantic and semantic['passed'] and semantic['live']
        desktop_passed=True
    except (AssertionError,ValueError) as error:
        desktop_error=str(error)
elif desktop_failure:
    desktop_error=desktop_failure.get('error')
epochs=trace.get('epochs',[])
candidate_epoch=epochs[-1] if len(epochs)>=2 else None
scan_passed=bool(candidate_scan and candidate_epoch and candidate_scan['overlaps']==0 \
    and candidate_scan['cumulativeMaxUs']<10000 and candidate_epoch['maxOverlapCount']==0 \
    and candidate_epoch['maxTaskScanUs']<10000)
stages={p.name.removesuffix('_exit.json'):load(p)['exitCode'] for p in S.glob('*_exit.json')}
accepted=session['passed'] and all_readonly_checks and desktop_passed and scan_passed \
    and all(value==0 for value in stages.values())
summary=dict(nativeAccepted=bool(accepted),nativeReaderPassed=bool(all_readonly_checks),
    activeWorkloadReaderPassed=bool(candidate_passed and dart.get('passed') is True and replay.get('passed') is True),
    scanReviewPassed=scan_passed,scanCauseConfirmed=False,desktopAccepted=desktop_passed,
    serial='601FC87B',canonicalSha256=b['canonicalSha256'],sourceSha256=b['sourceSha256'],
    candidateCases=sum(row['passed'] for row in case_counts.values()),caseGroups=case_counts,
    candidateCasesRestored=cases.get('restored'),candidatePolicyRestored=cases.get('policyRestored'),
    pairedCapturesReplayed=replay.get('pairs',0),pairedMinimumPaths=replay.get('minimumPaths'),
    pairedMaximumPaths=replay.get('maximumPaths'),observerSamples=len(samples),
    observerPassed=dart.get('passed'),observerError=dart.get('error'),
    allGoodSamples=sum(row['bad']==0 and row['uncertain']==0 for row in samples),
    samplesWithUncertainRows=sum(row['uncertain']>0 for row in samples),
    samplesWithBadRows=sum(row['bad']>0 for row in samples),
    sampleAgeMs=inspection.get('sampleAgeMs'),rpcUs=inspection.get('rpcUs'),
    maximumAcceptedRowWindowUs=inspection.get('maximumAcceptedRowWindowUs'),
    configurationPages=len(dart.get('configurationPages',[])),
    configurationScalarComparisons=config.get('scalarComparisons'),
    idlePaths=idle_paths,idlePassed=bool(idle_passed),genericValues=generic_values,genericModules=generic_modules,
    candidateScan=candidate_scan,candidateTraceEpoch=candidate_epoch,taskTrace=trace,
    desktopCoverage=dict(accepted=desktop_passed,modules=len((desktop or desktop_failure or {}).get('modules',[])),
        views=len((desktop or desktop_failure or {}).get('shots',[])),
        fieldbusNodes=len((desktop or {}).get('fieldbusNodes',[])),error=desktop_error,
        link=(desktop_failure or {}).get('link'),
        localWriteRefusals=(desktop or desktop_failure or {}).get('refusedActions'),
        fixtureClientWriteCalls=(desktop or {}).get('fixtureClientWriteCalls'),
        nativeWireWriteCountMeasured=False),
    genealogyRestored=True,baselineCases=31,originalDocumentsRestored=5,finalChecksPassed=True,
    baselineScan=baseline_scan,sourceBindingsVerified=len(b['sha256']),sdkSavedWorkingAcdOnly=True,
    stageExits=stages,sessionCandidateError=session['candidateError'],authorizationConsumed=True,
    currentControllerChangesAuthorized=False,dumpFiles=[],faultClears=0,taskCounterClears=0,
    clockChanges=0,powerOperations=0,hardKills=0)
desktop_log=S/'desktop_readonly.log'
if desktop_log.is_file() and b'Complete station sample is late or expired.' in desktop_log.read_bytes():
    summary['desktopCoverage']['primaryError']='Complete station sample is late or expired.'
    summary['desktopCoverage']['primaryBoundary']='OpcUaRepository initial complete-sample freshness check'
    summary['desktopCoverage']['helperSecondaryError']=desktop_error if desktop_error and 'Null check operator' in desktop_error else None
summary['desktopFreshnessDiagnostics']=optional('desktop_freshness_analysis_01.json')
summary['parallelReader']=dict(connections=4,serialPinned=True,outstandingPerSocket=1,guardedRowLease=True,proofAndFreshnessRulesUnchanged=True)
summary['partReadDiagnostics']=optional('part_read_analysis_01.json')
summary['cipPhaseTiming']=optional('cip_timing_analysis_01.json')
save('runtime_summary_01.json',summary)
save('owner_authorization_consumed_01.json',dict(authorizationConsumed=True,
    currentControllerChangesAuthorized=False,approvalQuestion='call_65010f20595041d78cea54b482b0f09f:0',
    ownerInstruction='Approve guarded S4b desktop timing session',
    authorizationSha256=sha(S/'authorization.json'),sessionResultSha256=sha(S/'session_result.json')))
print(json.dumps({key:summary[key] for key in ('nativeAccepted','nativeReaderPassed','activeWorkloadReaderPassed',
    'scanReviewPassed','desktopAccepted','candidateCases','pairedCapturesReplayed','observerSamples',
    'candidateScan','desktopCoverage','genealogyRestored','baselineCases')}))
