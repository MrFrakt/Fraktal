"""Offline verification of prepared S3c artifacts and explicit pending gates."""
from pathlib import Path
import datetime,hashlib,json,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_sdk_log_gate as sdk
import fraktal_ab_studio_capacity as capacity_provider
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
required=('ab_suite_01','root_tests_01','spec_gate_02','contracts_gate_02','consistency_gate_02','whitespace_gate_01','echo_readback_04','physical_readback_05','echo_audit_04','physical_audit_05','prepared_readback_01','prepared_audit_01','access_source_01','access_echo_01','access_physical_01','access_prepared_01','session_build_03','prepare_acd_02','capacity_candidate_auto_01','compatibility_verification_01','prior_seals_01','guard_readonly_01','baseline_state_01')
for name in required:assert json.loads((W/(name+'_exit.json')).read_text())['exitCode']==0,name
for name in ('authorization.json','deploy_attempt.json','backup.sha256','echo_before_s3c.ACD','preflight.json'):assert not (W/name).exists(),name
pin=(W/'canonical.sha256').read_text().strip()
assert sha(W/'s3c_canonical.ACD')==sha(W/'capacity_review.ACD')==pin
assert sha(W/'genealogy_s3c_04.L5X')=='E58BB88F9E63BE9144AF90C4032714F9B44B167CA02E2B2A64C933788F4E70A2'
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD'))=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
capacity=json.loads((W/'capacity_review.json').read_text());raw=(W/'capacity_candidate_auto_capture_01.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()==capacity['CaptureSha256']
normalized=capacity_provider.normalize(json.loads(raw.decode('utf-8-sig')),pin)
assert all(capacity[k]==v for k,v in normalized.items())
baseline=json.loads((W/'baseline_capacity.json').read_text());reference=json.loads((W/'baseline_reference.json').read_text())
assert sha(W/'baseline_capacity.json')==reference['capacitySha256']
for suffix in ('Sha256','UsedStandardBlocks','AvailableBlocks','TotalBlocks'):
 source='CanonicalSha256' if suffix=='Sha256' else suffix
 assert capacity['Baseline'+suffix]==baseline[source]
assert capacity['DeltaUsedStandardBlocks']==115940
for name in ('native_echo_04','native_physical_05','prepare_acd_02'):
 audit=sdk.audit_log((W/(name+'.log')).read_text(),('Build','Save As'),True);assert audit['Clean'],audit
binding=json.loads((W/'source_bindings_01.json').read_text())
for file,pin_value in binding['sha256'].items():assert sha(ROOT/file).lower()==pin_value,file
for file in W.rglob('*.py'):
 if not any(part in ('bin','obj','__pycache__') for part in file.parts):compile(file.read_bytes(),str(file),'exec')
program=(W/'session/Program.cs').read_text();assert W.as_posix() in program and 'prepare_17bd9' not in program
assert "unit['Mode']!=app.manual_mode" in (W/'scripts/preflight.py').read_text()
assert "unit['Mode'] == app.manual_mode" in (W/'final_checks.py').read_text()
state=json.loads((W/'readiness_checks_01.json').read_text());assert state['manualNormalizationPending'] and not state['passed']
assert {k for k,v in state['checks'].items() if not v}=={'manual'}
assert json.loads((W/'preflight_readonly_refusal_01_exit.json').read_text())['exitCode']==1
assert 'not MANUAL and idle' in (W/'preflight_readonly_refusal_01.log').read_text()
assert not json.loads((W/'authorization.template.json').read_text())['CurrentOwnerApproved']
forecast=json.loads((W/'capacity_forecast_01.json').read_text());error=forecast['estimatedUsedBlocks']-capacity['UsedStandardBlocks']
report=dict(passed=True,offlineGatesPassed=True,controllerChanges=0,currentAuthorizationPending=True,
 manualNormalizationPending=True,preflightRecorded=False,runtimeAccepted=False,requiredSuccessfulRuns=list(required),
 preparedAcdSha256=sha(W/'s3c_canonical.ACD'),sourceSha256=sha(W/'genealogy_s3c_04.L5X'),expectedPaths=647,
 sourceBindings=len(binding['sha256']),capacityBlocks=capacity['UsedStandardBlocks'],deltaBlocks=115940,
 forecastHoldout=dict(estimated=forecast['estimatedUsedBlocks'],measured=capacity['UsedStandardBlocks'],errorBlocks=error,errorPercent=100*error/capacity['UsedStandardBlocks'],planningBudget=forecast['planningBudgetBlocks'],measurementExcludedFromCalibration=True),
 priorSeals=json.loads((W/'prior_seals_verification_01.json').read_text())['records'],
 capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (W/'preparation_verification_01.json').open('x') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report))
