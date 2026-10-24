from pathlib import Path
import datetime,gzip,hashlib,json,statistics
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent
W=Path('C:/work/fraktal-ab-s3f-revision-20261023/prepare_c66f76a368304f6981b436dbf651e009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
required=('opening_02','guard_01','manual_before_01','preflight_01','backup_01','backup_log_audit_01','backup_access_01','preflight_before_download_01','deploy_01','deploy_log_audit_01','deploy_readback_01','deploy_access_01','guard_candidate_01','guard_retry_01','guard_retry_02','cleanup_after_observer_02','candidate_regressions_05','manual_candidate_01','restart_01','restart_log_audit_01','candidate_acceptance_01','idle_equivalence_01','generic_acquire_01','native_record_sizes_01','candidate_timing_01','capture_replay_01','restore_genealogy_01','restore_log_audit_01','restore_readback_01','restore_access_01','guard_baseline_01','baseline_regressions_02','manual_final_01','final_checks_01','preflight_final_01','inspect_final_01','baseline_timing_01','source_verification_02','observer_tests_01','observer_window_tests_01','ab_suite_closing_01','root_tests_closing_01')
required+=('cleanup_after_observer_03','normalize_query_01','guard_retry_03','fixture_order_tests_01')
for n in required:assert json.loads((R/(n+'_exit.json')).read_text())['exitCode']==0,n
fixture=json.loads((R/'candidate_regressions_05.json').read_text());base=json.loads((R/'baseline_regressions_02.json').read_text())
for f in (fixture,base):assert len(f['rows'])==31 and all(r['passed'] for r in f['rows']) and f['restored'] and f['policyRestored'] and not f.get('error')
assert len(fixture['s3fAccessRows'])==2 and len(fixture['s3fConfigRows'])==8 and len(fixture['s3fRevisionRows'])==1
accept=json.loads((R/'candidate_acceptance_01.json').read_text());assert accept['passed'] and accept['totalCandidateChecks']==43
inherited=json.loads((R/'base_acceptance_01.json').read_text());assert inherited['passed'] and inherited['configurationPairs']==39
replay=json.loads((R/'capture_replay_01.json').read_text());assert replay['passed'] and replay['captures']==93
source=json.loads((R/'source_verification_02.json').read_text());assert source['sourceBindings']==143 and source['generatedPlcSourceUnchanged']
for n,pin in source['sha256'].items():assert sha(ROOT/n)==pin,n
assert json.loads((R/'final_checks_01.json').read_text())['passed']
inspection=json.loads((R/'inspect_final_01.log').read_text());assert inspection['ControllerMode']==1 and not inspection['IsFaulted'] and inspection['KeySwitchPosition']==0
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')).upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
pin='BD030AEB01D58469D452D877A9CFF2868B79DE45055A3795D1D1479BB2771183';assert sha(W/'capacity_review.ACD').upper()==pin
assert sha(W/'s3f_canonical.ACD').upper()==(W/'deployed.sha256').read_text().strip()
actual=1;runs=[]
for p in sorted(R.glob('*regressions_*.json')):
 if p.name.endswith('_exit.json'):continue
 f=json.loads(p.read_text());rows=sum(len(f.get(k,[])) for k in ('rows','s3fAccessRows','s3fConfigRows','s3fRevisionRows'))
 actual+=rows;runs.append(dict(file=p.name,recordedRows=rows,restored=f.get('restored'),error=f.get('error')))
assert actual==125,actual
timing={}
for name,prefix,last,mx,ov in [('candidate','FRK_Press_CanonicalTiming.','LastScanUs','MaxScanUs','OverlapCount'),('baseline','FRK_Press_HealthProbe.','TaskLastScanUs','TaskMaxScanUs','TaskOverlapCount')]:
 f=json.loads((R/(name+'_timing_01.json')).read_text());timing[name]=dict(medianUs=statistics.median(s['values'][prefix+last] for s in f['samples']),maximumUs=max(s['values'][prefix+mx] for s in f['samples']),overlaps=max(s['values'][prefix+ov] for s in f['samples']))
 assert timing[name]['overlaps']==0
size=json.loads((R/'native_record_sizes_01.json').read_text());assert size['passed'] and size['totalPayloadBytes']==133156
failures=[dict(label='opening_01',exitCode=1,controllerAccess=False)]+[dict(label=p.name.removesuffix('_exit.json'),exitCode=json.loads(p.read_text())['exitCode']) for p in sorted(R.glob('*_exit.json')) if json.loads(p.read_text())['exitCode']!=0]
import re
for label,count in (('ab_suite_closing_01',2114),('root_tests_closing_01',74)):
 match=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK',(R/(label+'.log')).read_text());assert match and int(match[1])==count,label
report=dict(passed=True,s3fStageComplete=True,authorizationConsumed=True,requiredSuccessfulRuns=list(required),acceptedCandidateRows=42,acceptedRetainedRestartRows=1,acceptedBaselineRows=31,acceptedTotalRows=74,actualRecordedRows=actual,extraRecordedRows=actual-74,regressionRuns=runs,pairedCaptures=93,replay=replay['attempts'],expectedPagePaths={'0':2617,'1':2567,'empty':2217},nativePayloadBytes=133156,timing=timing,sourceBindings=143,abTests=2114,rootTests=74,testsSource='current full discovery and root suites',failedRunsRetained=failures,preparedAcdSha256=pin,sdkSavedAcdSha256=sha(W/'s3f_canonical.ACD').upper(),retainedRestart=accept,observerChanges=source['observerChanges'],finalGenealogyReady=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (R/'runtime_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
with (R/'authorization_consumed.json').open('x') as f:json.dump(dict(consumed=True,authorizationSha256=sha(R/'authorization.json'),capturedUtc=report['capturedUtc'],scope='Completed exact S3f revision session; no further controller changes authorized'),f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='requiredSuccessfulRuns'}))
