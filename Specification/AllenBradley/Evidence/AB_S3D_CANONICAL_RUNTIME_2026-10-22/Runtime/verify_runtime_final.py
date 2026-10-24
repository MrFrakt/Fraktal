from pathlib import Path
import datetime,hashlib,json,re,statistics,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent
W=Path('C:/work/fraktal-ab-s3d-20261022/prepare_f1995b2579fe4f7a9d15d02dd8ed53e9')
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_capacity_estimate as capacity
required=('initialize_02','guard_initial_01','manual_initial_01','preflight_initial_01','backup_01','backup_audit_01','backup_access_01','preflight_predeploy_01','deploy_01','deploy_audit_01','deploy_readback_01','deploy_access_01','guard_candidate_01','guard_candidate_02','guard_candidate_03','candidate_regressions_03','candidate_acceptance_03','manual_candidate_01','idle_equivalence_01','generic_capture_01','native_record_sizes_01','candidate_scan_01','restore_01','restore_audit_01','restore_readback_01','restore_access_01','guard_restored_01','baseline_regressions_01','manual_final_01','guard_final_01','final_checks_01','preflight_final_verify_01','baseline_scan_01','inspect_final_01','capture_replay_01','capture_replay_02','prior_seals_01','source_audit_01','read_window_tests_03','ab_suite_01','root_tests_01','spec_gate_01','contracts_gate_01','consistency_gate_01','whitespace_gate_01','update_target_01')
for name in required:assert json.loads((R/(name+'_exit.json')).read_text())['exitCode']==0,name
closing=('guard_close_01','final_checks_close_01','preflight_close_verify_01','inspect_close_01')
for name in closing:assert json.loads((R/(name+'_exit.json')).read_text())['exitCode']==0,name
failures={p.name.removesuffix('_exit.json') for p in R.glob('*_exit.json') if json.loads(p.read_text())['exitCode']!=0}
assert failures=={'initialize_01','candidate_regressions_01','candidate_acceptance_01','candidate_regressions_02','candidate_acceptance_02'},failures
fixtures=[json.loads((R/name).read_text()) for name in ('candidate_regressions_01.json','candidate_regressions_02.json','candidate_regressions_03.json','baseline_regressions_01.json')]
assert [len(f['rows']) for f in fixtures]==[8,26,31,31]
for f in fixtures:
 assert all(row['passed'] for row in f['rows']) and f['restored'] and f['policyRestored']
for f in fixtures[:2]:assert f['error']=='condition equivalence failed'
for f in fixtures[2:]:assert not f.get('error')
acceptance=json.loads((R/'candidate_acceptance_03.json').read_text())
assert acceptance['passed'] and (acceptance['decisionPairs'],acceptance['conditionPairs'],acceptance['sequencePairs'],acceptance['resetPairs'])==(4,14,21,8)
assert acceptance['activeStatesObserved']==[0,1] and acceptance['ringWrapObserved'] and acceptance['closedDurationMaximum']==1360
replay=json.loads((R/'capture_replay_02.json').read_text())
assert replay['passed'] and replay['pairedCaptures']==48 and replay['genericPaths']==2125 and replay['attempts']['maximum']==8
sizes=json.loads((R/'native_record_sizes_01.json').read_text())
assert sizes['passed'] and [row['rawPayloadBytes'] for row in sizes['records']]==[77304,7308,16616]
for name in ('backup_access_01','restore_access_01'):
 d=json.loads((R/(name+'.json')).read_text());assert d['Conforms'] and d['ExactReferenceTagAccessEqual'] and d['TagsAudited']==109
assert json.loads((R/'deploy_access_01.json').read_text())['passed']
for name in ('deploy_readback_01','restore_readback_01'):assert json.loads((R/(name+'.log')).read_text())['Equivalent']
for name in ('backup_audit_01','deploy_audit_01','restore_audit_01'):assert json.loads((R/(name+'.log')).read_text())['Clean']
final=json.loads((R/'final_checks_01.json').read_text());assert final['passed'] and all(final['checks'].values())
inspection=json.loads((R/'inspect_final_01.log').read_text());assert inspection['ControllerMode']==1 and not inspection['IsFaulted'] and inspection['KeySwitchPosition']==0 and inspection['SerialNumber']==0x601FC87B
assert json.loads((R/'inspect_close_01.log').read_text())==inspection
closingChecks=json.loads((R/'final_checks_close_01.json').read_text());assert closingChecks['passed'] and all(closingChecks['checks'].values())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD'))=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
assert sha(W/'echo_before_s3d.ACD')==(W/'backup.sha256').read_text().strip()=='A16E4A88721408894E29B28042DDAA42E31F1D2994429EF1337214DF0F8E326F'
assert (W/'canonical.sha256').read_text().strip()=='E5CA9AB3493AABF93E72A728EBDF5630E8056EEA2AC82254B38913B8C7CF7C9D'
assert sha(W/'s3d_canonical.ACD')=='8FBACD120BEB46891D34C8730ADB368081DC7F14D009421D10A24140154E8E01'
assert sha(W/'genealogy_s3d_01.L5X')=='03E0775EDD8A1A22D88D198D4D3CE2B7C19A2F2029A40E3C428CB838FC2EE962'
bindings=json.loads((R/'source_bindings_runtime_01.json').read_text())
for name,pin in bindings['sha256'].items():assert sha(ROOT/name).lower()==pin,name
normalizations=[]
for name in ('manual_initial_01','manual_candidate_01','manual_final_01'):
 d=json.loads((R/(name+'.json')).read_text());assert d['passed'] and d['afterMode']==1 and d['currentLevel']==0
 if d['beforeMode']!=1:normalizations.append(name)
assert len(normalizations)==2
def timing(name,prefix):
 d=json.loads((R/name).read_text());rows=[s['values'] for s in d['samples']];last=[row[prefix+'LastScanUs'] for row in rows]
 assert len(rows)==20 and all(row[prefix+'OverlapCount']==0 for row in rows)
 return dict(samples=20,unit='microseconds',medianLast=statistics.median(last),minimumLast=min(last),maximumLast=max(last),cumulativeMax=max(row[prefix+'MaxScanUs'] for row in rows),overlaps=0)
def suite(name,expected):
 text=(R/name).read_text();match=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK(?:\s|$)',text)
 assert match and int(match[1])==expected,name
 return dict(tests=int(match[1]),seconds=float(match[2]),passed=True)
samples=capacity.load_observations(ROOT/'Specification/AllenBradley/AB_CAPACITY_OBSERVATIONS_2026-10-21.json')
assert len(samples)==6 and samples[-1]['label']=='S3d' and samples[-1]['used']==1290016
report=dict(passed=True,sessionComplete=True,scope='2125-path S3d genealogy subset on local Echo 601FC87B',runtimeAccepted=True,
 candidateRows=31,baselineRows=31,totalRecordedRegressionRows=96,extraRecordedRegressionRows=34,failedFixtureRowCounts=[8,26],decisionCaptures=4,conditionCaptures=14,sequenceCaptures=21,resetCaptures=8,resetBeforeAfterPairs=4,pairedCapturesIncludingIdle=48,
 sameScanAttempts=replay['attempts'],readOnlyAcquisitionConnections=2,metadataCoherence='V6.2 equal manifest revision',activeStatesObserved=acceptance['activeStatesObserved'],waitResetObserved=False,ringWrapObserved=True,closedDurationMaximumMs=1360,
 manualNormalizations=normalizations,additionalMailboxCommands=6,perTagWriteCallCountMeasured=False,originalCandidatePin=(W/'canonical.sha256').read_text().strip(),sdkSavedCandidateSha256=sha(W/'s3d_canonical.ACD'),backupSha256=sha(W/'echo_before_s3d.ACD'),
 originalGenealogyUnchanged=True,finalChecks=final['checks'],finalNative=inspection,nativeRecords=sizes['records'],totalNativePayloadBytes=sizes['totalPayloadBytes'],
 candidateTiming=timing('candidate_scan_01.json','FRK_Press_CanonicalTiming.'),baselineTiming=timing('baseline_scan_01.json','FRK_Press_HealthProbe.Task'),
 unchangedPreparedSourceFiles=68,changedReadOnlyHarnessFiles=2,plcSourcesUnchanged=True,abSuite=suite('ab_suite_01.log',2066),rootSuite=suite('root_tests_01.log',74),
 capacitySamples=6,failedRuns=sorted(failures),requiredSuccessfulRuns=list(required)+list(closing),closingChecks=closingChecks['checks'],faultClears=0,clockChanges=0,commits=0,pushes=0,completedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (R/'runtime_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report))
