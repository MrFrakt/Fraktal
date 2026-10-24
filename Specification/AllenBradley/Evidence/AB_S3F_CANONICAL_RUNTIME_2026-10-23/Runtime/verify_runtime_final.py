"""Closing S3f runtime audit. It grants no further controller permission."""
from pathlib import Path
import datetime,gzip,hashlib,json,re,statistics
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent
W=Path('C:/work/fraktal-ab-s3f-20261022/prepare_3816927132f14d4998876bc62e22f342')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
required=('backup_01','backup_log_audit_01','backup_access_01','preflight_before_download_01',
 'deploy_01','deploy_log_audit_01','deploy_readback_01','deploy_access_01','guard_candidate_01',
 'candidate_regressions_04','candidate_acceptance_02','manual_candidate_01','idle_equivalence_01',
 'generic_acquire_02','native_record_sizes_01','candidate_timing_01','capture_replay_01',
 'restore_genealogy_01','restore_log_audit_01','restore_readback_01','restore_access_01','guard_baseline_01',
 'baseline_regressions_01','manual_final_01','final_checks_01','preflight_final_01','inspect_final_01','baseline_timing_01',
 'fragment_tests_01','fixture_policy_tests_01','ab_suite_closing_01','root_tests_closing_01','spec_closing_01','contracts_closing_01','consistency_closing_01',
 'source_verification_01','prior_seals_closing_02')
for n in required:assert json.loads((R/(n+'_exit.json')).read_text())['exitCode']==0,n
fixture=json.loads((R/'candidate_regressions_04.json').read_text())
base=json.loads((R/'baseline_regressions_01.json').read_text())
for f in (fixture,base):assert len(f['rows'])==31 and all(r['passed'] for r in f['rows']) and f['restored'] and f['policyRestored'] and not f.get('error')
assert len(fixture['s3fAccessRows'])==2 and len(fixture['s3fConfigRows'])==8
accept=json.loads((R/'candidate_acceptance_02.json').read_text());assert accept['passed']
assert accept['requiredLevelsObserved']==[0,1] and accept['classReadLevelsObserved']==[0,1,4]
replay=json.loads((R/'capture_replay_01.json').read_text());assert replay['passed'] and replay['captures']==88
source=json.loads((R/'source_verification_01.json').read_text())
for n,pin in source['sha256'].items():assert sha(ROOT/n)==pin,n
assert source['currentBindings']==140 and source['generatedPlcSourceUnchanged']
for n,count in [('ab_suite_closing_01',2108),('root_tests_closing_01',74)]:
 m=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK',(R/(n+'.log')).read_text());assert m and int(m[1])==count,n
assert json.loads((R/'final_checks_01.json').read_text())['passed']
inspection=json.loads((R/'inspect_final_01.log').read_text());assert inspection['ControllerMode']==1 and not inspection['IsFaulted'] and inspection['KeySwitchPosition']==0
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')).upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
assert sha(W/'capacity_review.ACD').upper()=='A05695F15ED162B500D353528621CE0AB92D36E8240339DAAD001DA928E3EB66'
assert sha(W/'s3f_canonical.ACD').upper()=='D75642226EF16122E7C5EC0B9255C154B2A9340B9D0E8E644B138627247515F3'
actual=0;runs=[]
for p in sorted(R.glob('*regressions_*.json')):
 if p.name.endswith('_exit.json'):continue
 f=json.loads(p.read_text());rows=len(f.get('rows',[]))+len(f.get('s3fAccessRows',[]))+len(f.get('s3fConfigRows',[]))
 actual+=rows;runs.append(dict(file=p.name,recordedRows=rows,restored=f.get('restored'),error=f.get('error')))
assert actual==113,actual
timing={}
for name,prefix,last,mx,ov in [('candidate','FRK_Press_CanonicalTiming.','LastScanUs','MaxScanUs','OverlapCount'),('baseline','FRK_Press_HealthProbe.','TaskLastScanUs','TaskMaxScanUs','TaskOverlapCount')]:
 f=json.loads((R/(name+'_timing_01.json')).read_text())
 timing[name]=dict(medianUs=statistics.median(s['values'][prefix+last] for s in f['samples']),maximumUs=max(s['values'][prefix+mx] for s in f['samples']),overlaps=max(s['values'][prefix+ov] for s in f['samples']))
 assert timing[name]['overlaps']==0
size=json.loads((R/'native_record_sizes_01.json').read_text());assert size['passed'] and size['totalPayloadBytes']==133156
failures=[dict(label=p.name.removesuffix('_exit.json'),exitCode=json.loads(p.read_text())['exitCode']) for p in sorted(R.glob('*_exit.json')) if json.loads(p.read_text())['exitCode']!=0]
report=dict(passed=True,runtimeAcceptedAtRecordedScope=True,s3fStageComplete=False,
 openNativeGates=['retained restart and active-model revision vectors'],authorizationConsumed=True,
 requiredSuccessfulRuns=list(required),acceptedCandidateRows=41,acceptedBaselineRows=31,acceptedTotalRows=72,
 actualRecordedRows=actual,extraRecordedRows=actual-72,regressionRuns=runs,pairedCaptures=88,replay=replay['attempts'],
 expectedPagePaths={'0':2617,'1':2567,'empty':2217},nativePayloadBytes=133156,timing=timing,
 sourceBindings=140,changedPreparedSources=source['changedObserverBindings'],failedRunsRetained=failures,
 originalAcdSha256='A05695F15ED162B500D353528621CE0AB92D36E8240339DAAD001DA928E3EB66',
 sdkSavedAcdSha256=sha(W/'s3f_canonical.ACD').upper(),preparedPlcSourceUnchanged=True,finalGenealogyReady=True,
 capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (R/'runtime_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
with (R/'authorization_consumed.json').open('x') as f:json.dump(dict(consumed=True,authorizationSha256=sha(R/'authorization.json'),capturedUtc=report['capturedUtc'],scope='Completed exact S3f session; no further controller changes authorized'),f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('changedPreparedSources','requiredSuccessfulRuns')}))
