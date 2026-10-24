"""Read-only audit of the completed authorized S3c session."""
from pathlib import Path
import datetime,gzip,hashlib,json,statistics,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent;W=Path('C:/work/fraktal-ab-s3c-20261022/prepare_147ef60398974c44abf7b2959b2d813f')
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_capacity_estimate as capacity
required=('guard_initial_01','manual_initial_01','preflight_01','backup_01','backup_audit_01','backup_access_02','preflight_verify_01','deploy_01','deploy_audit_01','deploy_readback_01','deploy_access_01','guard_candidate_01','candidate_regressions_01','candidate_acceptance_01','manual_candidate_01','idle_equivalence_01','generic_capture_01','candidate_scan_01','restore_01','restore_audit_01','restore_readback_01','restore_access_01','guard_restored_01','baseline_regressions_01','manual_final_01','final_checks_01','preflight_final_verify_01','baseline_scan_01','inspect_final_01','capture_replay_01','prior_seals_01')
for name in required:assert json.loads((R/(name+'_exit.json')).read_text())['exitCode']==0,name
candidate=json.loads((R/'candidate_regressions_01.json').read_text());baseline=json.loads((R/'baseline_regressions_01.json').read_text())
for result in (candidate,baseline):
 assert not result.get('error') and len(result['rows'])==31 and all(row['passed'] for row in result['rows'])
 assert result['restored'] and result['policyRestored']
acceptance=json.loads((R/'candidate_acceptance_01.json').read_text())
assert acceptance['passed'] and acceptance['sequencePairs']==21 and acceptance['decisionPairs']==4 and acceptance['conditionPairs']==14
replay=json.loads((R/'capture_replay_01.json').read_text());assert replay['passed'] and replay['pairedCaptures']==40 and replay['genericPaths']==647
assert replay['attempts']['maximum']==6
assert json.loads((R/'backup_access_01_exit.json').read_text())['exitCode']==1
initialAccess=json.loads((R/'backup_access_01.json').read_text())
assert len(initialAccess['Findings'])==4 and all('declared public but not present' in finding for finding in initialAccess['Findings'])
for name in ('backup_access_02','restore_access_01'):
 result=json.loads((R/(name+'.json')).read_text());assert result['Conforms'] and result['ExactReferenceTagAccessEqual'] and result['TagsAudited']==109
assert json.loads((R/'deploy_access_01.json').read_text())['passed']
assert json.loads((R/'deploy_readback_01.log').read_text())['Equivalent']
assert json.loads((R/'restore_readback_01.log').read_text())['Equivalent']
final=json.loads((R/'final_checks_01.json').read_text());assert final['passed'] and all(final['checks'].values())
inspection=json.loads((R/'inspect_final_01.log').read_text());assert inspection['ControllerMode']==1 and not inspection['IsFaulted'] and inspection['KeySwitchPosition']==0 and inspection['SerialNumber']==0x601FC87B
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD'))=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
assert sha(W/'echo_before_s3c.ACD')==(W/'backup.sha256').read_text().strip()
assert (W/'canonical.sha256').read_text().strip()=='A255918860C3062D8F0DF3FA4E70373EF84372DDB3214E050AF23A08A0C2286C'
assert sha(W/'s3c_canonical.ACD')=='CE52EB2EA19C764561DF511D70BEEA1092B99BE8CD9BBC2970D269ACE3A3EA9B'
assert sha(W/'genealogy_s3c_04.L5X')=='E58BB88F9E63BE9144AF90C4032714F9B44B167CA02E2B2A64C933788F4E70A2'
bindings=json.loads((W/'source_bindings_01.json').read_text())
for name,pin in bindings['sha256'].items():assert sha(ROOT/name).lower()==pin,name
normalizations=[]
for name in ('manual_initial_01','manual_candidate_01','manual_final_01'):
 result=json.loads((R/(name+'.json')).read_text())
 assert result['passed'] and result['beforeMode']==0 and result['afterMode']==1 and result['currentLevel']==0
 normalizations.append(name)
def timing(name,prefix):
 result=json.loads((R/name).read_text());rows=[row['values'] for row in result['samples']];last=[row[prefix+'LastScanUs'] for row in rows]
 assert len(rows)==20 and all(row[prefix+'OverlapCount']==0 for row in rows)
 return dict(samples=len(rows),unit='microseconds',medianLast=statistics.median(last),minimumLast=min(last),maximumLast=max(last),cumulativeMax=max(row[prefix+'MaxScanUs'] for row in rows),overlaps=0)
samples=capacity.load_observations(ROOT/'Specification/AllenBradley/AB_CAPACITY_OBSERVATIONS_2026-10-21.json')
assert len(samples)==5 and samples[-1]['label']=='S3c' and samples[-1]['used']==1107552
report=dict(passed=True,sessionComplete=True,scope='647-path S3c genealogy subset on local Echo 601FC87B',runtimeAccepted=True,
 candidateRows=31,baselineRows=31,totalRegressionRows=62,extraRegressionRows=0,decisionPairs=4,conditionPairs=14,sequencePairs=21,pairedCapturesIncludingIdle=40,
 sameScanAttempts=replay['attempts'],manualNormalizations=normalizations,additionalMailboxCommands=9,perTagWriteCallCountMeasured=False,
 originalCandidatePin=(W/'canonical.sha256').read_text().strip(),sdkSavedCandidateSha256=sha(W/'s3c_canonical.ACD'),backupSha256=sha(W/'echo_before_s3c.ACD'),
 originalGenealogyUnchanged=True,finalChecks=final['checks'],finalNative=inspection,
 candidateTiming=timing('candidate_scan_01.json','FRK_Press_CanonicalTiming.'),baselineTiming=timing('baseline_scan_01.json','FRK_Press_HealthProbe.Task'),
 sourceFilesUnchanged=len(bindings['sha256']),abSuiteReusedFromExactUnchangedPreparation=dict(tests=2052,seconds=271.430,passed=True),
 capacitySamples=len(samples),failedWorkAudits=['backup_access_01'],requiredSuccessfulRuns=list(required),faultClears=0,clockChanges=0,commits=0,pushes=0,
 completedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (R/'runtime_verification_01.json').open('x') as out:json.dump(report,out,indent=2)
print(json.dumps(report))
