"""Read-only exact-artifact closing audit for S3f offline preparation."""
from pathlib import Path
import datetime,hashlib,json,re,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_studio_capacity as capacity
required=('ab_suite_02','focused_final_01','publication_fixture_tests_02','root_tests_01',
 'spec_gate_02','contracts_gate_02','consistency_gate_02','whitespace_gate_01',
 'echo_readback_06','physical_readback_06','echo_audit_01','physical_audit_01',
 'access_source_01','access_echo_01','access_physical_01','prepared_readback_01','prepared_audit_01','access_prepared_01',
 'session_sources_01','session_build_01','prepare_acd_01','pin_acd_01','capacity_auto_01','capacity_forecast_01','capacity_binding_01',
 'compatibility_verification_01','runtime_audit_preparation_01','source_binding_01',
 'guard_readonly_01','inspect_readonly_01','preflight_01','preflight_verify_01','final_checks_02','baseline_timing_preparation_01','prior_seals_01')
for name in required:assert json.loads((W/(name+'_exit.json')).read_text())['exitCode']==0,name
for name in ('authorization.json','deploy_attempt.json','backup.sha256','echo_before_s3f.ACD','canonical_downloaded.L5X','genealogy_restored.L5X'):assert not (W/name).exists(),name
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
pin=(W/'canonical.sha256').read_text().strip()
assert pin=='A05695F15ED162B500D353528621CE0AB92D36E8240339DAAD001DA928E3EB66'
assert sha(W/'s3f_canonical.ACD')==sha(W/'capacity_review.ACD')==pin
assert sha(W/'genealogy_s3f_05.L5X')==sha(W/'generation_recheck.L5X')=='7BBAD050BFD82D3C76DD84E82644AC1AAE5A772125CC02AAC7DD93FE1F621C28'
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD'))=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
for name in ('echo_readback_06','physical_readback_06','prepared_readback_01'):
 comparison=json.loads((W/(name+'.log')).read_text())
 assert comparison['Equivalent'] and comparison['ExecutableBodies']==52 and comparison['AuthoredInitialValues']==37556
assert json.loads((W/'canonical_prepared_compare.json').read_text())['Equivalent']
for label in ('source','echo','physical','prepared'):assert json.loads((W/('access_'+label+'_01.json')).read_text())['passed']
cap=json.loads((W/'capacity_review.json').read_text());raw=(W/'capacity_auto_capture_01.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()==cap['CaptureSha256']
assert all(cap[k]==v for k,v in capacity.normalize(json.loads(raw.decode('utf-8-sig')),pin).items())
prior=json.loads((W/'baseline_capacity.json').read_text())
assert sha(W/'baseline_capacity.json')==json.loads((W/'baseline_reference.json').read_text())['capacitySha256']
for key in ('Sha256','UsedStandardBlocks','AvailableBlocks','TotalBlocks'):assert cap['Baseline'+key]==prior['CanonicalSha256' if key=='Sha256' else key]
assert cap['DeltaUsedStandardBlocks']==729560 and cap['UsedStandardBlocks']==2298412
bindings=json.loads((W/'source_bindings_01.json').read_text())
for name,expected in bindings['sha256'].items():assert sha(ROOT/name).lower()==expected,name
assert len(bindings['sha256'])==138 and bindings['localPythonImportsClosed']
for p in W.rglob('*.py'):
 if not any(part in ('bin','obj','__pycache__') for part in p.parts):compile(p.read_bytes(),str(p),'exec')
source=(W/'session/Program.cs').read_text();assert W.as_posix() in source and 'Opening an ACD takes time' in source
approval=json.loads((W/'authorization.template.json').read_text())
for key in ('CurrentOwnerApproved','ManualNormalizationAuthorized','AccessVectorsAuthorized','ConfigurationVectorsAuthorized','FaultClearAuthorized'):assert approval[key] is False
for key in ('AccessVectorsAuthorized','ConfigurationVectorsAuthorized'):assert key in source
assert json.loads((W/'contract_approval.json').read_text())['controllerChangesAuthorized'] is False
assert json.loads((W/'final_checks_02.json').read_text())['passed']
assert json.loads((W/'preflight.json').read_text())['mode']==1
for label,count in [('ab_suite_02',2104),('root_tests_01',74),('focused_final_01',43)]:
 text=(W/(label+'.log')).read_text();m=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK',text)
 assert m and int(m[1])==count,label
failed=[]
for p in sorted(W.glob('*_exit.json')):
 result=json.loads(p.read_text())
 if result['exitCode']!=0:failed.append(dict(label=p.name.removesuffix('_exit.json'),exitCode=result['exitCode']))
forecast=json.loads((W/'capacity_forecast_01.json').read_text());error=forecast['estimatedUsedBlocks']-cap['UsedStandardBlocks']
seals=json.loads((W/'prior_seals_verification_01.json').read_text());assert seals['records']==18 and seals['artifacts']==3207
report=dict(passed=True,offlineGatesPassed=True,runtimeAccepted=False,currentAuthorizationPending=True,controllerChanges=0,
 requiredSuccessfulRuns=list(required),failedRunsRetained=failed,preparedAcdSha256=pin,sourceSha256=sha(W/'genealogy_s3f_05.L5X'),sourceBindings=138,
 expectedPagePaths={'0':2617,'1':2567,'empty':2217},nativeExecutableBodies=52,nativeInitialValues=37556,
 plannedInheritedCandidateRows=31,plannedAccessRows=2,plannedConfigurationRows=8,plannedBaselineRows=31,plannedTotalRows=72,
 capacityBlocks=cap['UsedStandardBlocks'],availableBlocks=cap['AvailableBlocks'],totalBlocks=cap['TotalBlocks'],deltaBlocks=729560,
 forecastHoldout=dict(estimated=forecast['estimatedUsedBlocks'],measured=cap['UsedStandardBlocks'],errorBlocks=error,errorPercent=100*error/cap['UsedStandardBlocks'],planningBudget=forecast['planningBudgetBlocks'],planningFits=forecast['planningFits'],measurementExcludedFromCalibration=True),
 predecessorRecords=18,predecessorArtifacts=3207,preflightRecorded=True,manualOrdinal=1,
 openNativeGates=['page/provider equivalence, live revisions/timestamps, same-scan reads, sizes, scan, rollback/regressions',
 'retained restart and active-model revision vectors remain outside this prepared fixture'],
 capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (W/'preparation_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report))
