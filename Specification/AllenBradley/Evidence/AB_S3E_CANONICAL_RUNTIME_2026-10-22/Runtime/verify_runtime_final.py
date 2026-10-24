from pathlib import Path
import datetime,gzip,hashlib,json,re,statistics,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent
W=Path('C:/work/fraktal-ab-s3e-20261022/prepare_768bb43d842d4b008ab1dfb322741aea')
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_capacity_estimate as capacity
required=('initialize_01','guard_initial_01','manual_initial_01','preflight_initial_01','backup_01','backup_audit_01','backup_access_01','preflight_predeploy_01','deploy_01','deploy_audit_01','deploy_readback_01','deploy_access_01','guard_candidate_01','candidate_regressions_01','candidate_acceptance_02','fixture_tests_02','manual_candidate_01','idle_equivalence_01','generic_capture_01','native_record_sizes_01','candidate_scan_01','restore_01','restore_audit_01','restore_readback_01','restore_access_01','guard_restored_01','baseline_regressions_01','manual_final_01','guard_final_01','final_checks_01','preflight_final_verify_01','baseline_scan_01','inspect_final_01','capture_replay_01','prior_seals_01','source_verification_01','capacity_catalog_01','root_tests_01','spec_gate_01','contracts_gate_01','consistency_gate_01','whitespace_gate_01')
for name in required:assert json.loads((R/(name+'_exit.json')).read_text())['exitCode']==0,name
failed={p.name.removesuffix('_exit.json') for p in R.glob('*_exit.json') if json.loads(p.read_text())['exitCode']!=0}
assert failed=={'candidate_acceptance_01','candidate_regressions_02'},failed
candidate=json.loads((R/'candidate_regressions_01.json').read_text())
partial=json.loads((R/'candidate_regressions_02.json').read_text())
baseline=json.loads((R/'baseline_regressions_01.json').read_text())
for d,count in ((candidate,31),(partial,1),(baseline,31)):
 assert len(d['rows'])==count and all(x['passed'] for x in d['rows']) and d['restored'] and d['policyRestored']
for d in (candidate,baseline):assert not d.get('error')
assert partial['error']=='existing manual policy change must be observed at its commit'
for d in (candidate,partial):assert len(d['s3eAccessRows'])==2 and all(x['passed'] for x in d['s3eAccessRows'])
assert json.loads((R/'candidate_acceptance_01.json').read_text())['error']=='manual policy transition missing'
for p in R.glob('candidate_regressions_02_*.json.gz'):
 d=json.loads(gzip.decompress(p.read_bytes()));assert d['passed'] and d['comparison']['equal'] and d['comparison']['comparedPaths']==2154
acceptance=json.loads((R/'candidate_acceptance_02.json').read_text())
assert acceptance['passed'] and acceptance['manualPolicyPath']=='Press/Access/Policy/Required[2]'
assert (acceptance['decisionPairs'],acceptance['conditionPairs'],acceptance['sequencePairs'],acceptance['resetPairs'],acceptance['accessPairs'],acceptance['accessRows'])==(4,14,21,8,6,2)
assert acceptance['requiredLevelsObserved']==acceptance['classReadLevelsObserved']==[0,1]
assert acceptance['activeStatesObserved']==[0,1] and acceptance['ringWrapObserved']
replay=json.loads((R/'capture_replay_01.json').read_text())
assert replay['passed'] and replay['pairedCaptures']==54 and replay['genericPaths']==2154 and replay['attempts']['maximum']==41
sizes=json.loads((R/'native_record_sizes_01.json').read_text())
assert sizes['passed'] and [row['rawPayloadBytes'] for row in sizes['records']]==[77856,7308,16616]
for name in ('backup_access_01','restore_access_01'):
 d=json.loads((R/(name+'.json')).read_text());assert d['Conforms'] and d['ExactReferenceTagAccessEqual'] and d['TagsAudited']==109
assert json.loads((R/'deploy_access_01.json').read_text())['passed']
for name in ('deploy_readback_01','restore_readback_01'):assert json.loads((R/(name+'.log')).read_text())['Equivalent']
for name in ('backup_audit_01','deploy_audit_01','restore_audit_01'):assert json.loads((R/(name+'.log')).read_text())['Clean']
final=json.loads((R/'final_checks_01.json').read_text());assert final['passed'] and all(final['checks'].values())
inspection=json.loads((R/'inspect_final_01.log').read_text());assert inspection['ControllerMode']==1 and not inspection['IsFaulted'] and inspection['KeySwitchPosition']==0 and inspection['SerialNumber']==0x601FC87B
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD'))=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
assert sha(W/'echo_before_s3e.ACD')==(W/'backup.sha256').read_text().strip()=='C3B31F147AEDDAB795C0A7550E57DE1C899A2FE4ED032FEFEF8A4776291925B8'
assert (W/'canonical.sha256').read_text().strip()=='95E85B507387A548553688C1B5CCF52D7D99B35751C68F1B02DE92AC2A1B240B'
assert sha(W/'s3e_canonical.ACD')=='8D6A476193C421CE7ADDE6933EFAC3C4C7F501E7A1EECC79E64D86EB9CEDB2EC'
assert sha(W/'genealogy_s3e_01.L5X')=='3BFFCEADB98EC7B7B7AA05550202CC187C736A8C2B22C75B7B7D158BE4F5AD87'
bindings=json.loads((W/'source_bindings_01.json').read_text())
for name,pin in bindings['sha256'].items():assert sha(ROOT/name).lower()==pin,name
assert len(bindings['sha256'])==76
normalizations=[]
for name in ('manual_initial_01','manual_candidate_01','manual_final_01'):
 d=json.loads((R/(name+'.json')).read_text());assert d['passed'] and d['afterMode']==1 and d['currentLevel']==0
 if d['beforeMode']!=1:normalizations.append(name)
assert len(normalizations)==2
def timing(name,prefix):
 rows=[s['values'] for s in json.loads((R/name).read_text())['samples']];last=[row[prefix+'LastScanUs'] for row in rows]
 assert len(rows)==20 and all(row[prefix+'OverlapCount']==0 for row in rows)
 return dict(samples=20,unit='microseconds',medianLast=statistics.median(last),minimumLast=min(last),maximumLast=max(last),cumulativeMax=max(row[prefix+'MaxScanUs'] for row in rows),overlaps=0)
def suite(path,expected):
 m=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK(?:\s|$)',path.read_text());assert m and int(m[1])==expected,str(path)
 return dict(tests=int(m[1]),seconds=float(m[2]),passed=True)
samples=capacity.load_observations(ROOT/'Specification/AllenBradley/AB_CAPACITY_OBSERVATIONS_2026-10-21.json')
assert len(samples)==7 and samples[-1]['label']=='S3e' and samples[-1]['used']==1568852
prior=json.loads((R/'prior_seals_verification_01.json').read_text());assert prior['records']==16 and prior['artifacts']==2854
report=dict(passed=True,sessionComplete=True,runtimeAccepted=True,scope='2154-path S3e genealogy subset on local Echo 601FC87B',
 candidateInheritedRows=31,candidateAdditionalAccessRows=2,baselineRows=31,acceptedRegressionRows=64,partialRepeatInheritedRows=1,partialRepeatAccessRows=2,totalRecordedRegressionRows=67,extraRecordedRegressionRows=3,
 decisionCaptures=4,conditionCaptures=14,sequenceCaptures=21,resetCaptures=8,resetBeforeAfterPairs=4,accessCaptures=6,pairedCapturesIncludingIdle=54,
 sameScanAttempts=replay['attempts'],readOnlyAcquisitionConnections=2,metadataCoherence='V6.2 equal manifest revision',manualPolicyPath=acceptance['manualPolicyPath'],requiredLevelsObserved=[0,1],classReadLevelsObserved=[0,1],activeStatesObserved=[0,1],waitResetObserved=False,ringWrapObserved=True,closedDurationMaximumMs=acceptance['closedDurationMaximum'],
 manualNormalizations=normalizations,fixedAccessVectorExecutions=2,knownAdditionalMailboxCommands=12,perTagWriteCallCountMeasured=False,
 originalCandidatePin=(W/'canonical.sha256').read_text().strip(),sdkSavedCandidateSha256=sha(W/'s3e_canonical.ACD'),backupSha256=sha(W/'echo_before_s3e.ACD'),originalGenealogyUnchanged=True,finalChecks=final['checks'],finalNative=inspection,
 nativeRecords=sizes['records'],totalNativePayloadBytes=sizes['totalPayloadBytes'],candidateTiming=timing('candidate_scan_01.json','FRK_Press_CanonicalTiming.'),baselineTiming=timing('baseline_scan_01.json','FRK_Press_HealthProbe.Task'),
 unchangedPreparedRootSources=76,temporaryReadOnlyEditsRestored=True,postSessionAuditCorrectedToOwnerGate=True,plcSourcesUnchanged=True,abSuiteReusedFromExactUnchangedPreparation=suite(W/'ab_suite_01.log',2078),rootSuite=suite(R/'root_tests_01.log',74),finalFixtureTests=suite(R/'fixture_tests_02.log',15),capacitySamples=7,
 failedRuns=sorted(failed),requiredSuccessfulRuns=list(required),faultClears=0,clockChanges=0,commits=0,pushes=0,completedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (R/'runtime_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report))
