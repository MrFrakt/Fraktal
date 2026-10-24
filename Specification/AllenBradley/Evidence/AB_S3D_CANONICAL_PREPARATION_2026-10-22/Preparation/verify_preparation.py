"""Offline exact-artifact S3d preparation audit, with runtime gates pending."""
from pathlib import Path
import datetime,hashlib,json,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_studio_capacity as capacity
required=('ab_suite_01','focused_04','root_tests_01','spec_gate_01','contracts_gate_01','consistency_gate_01','whitespace_gate_01','echo_readback_01','physical_readback_01','echo_audit_01','physical_audit_01','access_source_01','access_echo_01','access_physical_01','prepared_readback_01','prepared_audit_01','access_prepared_01','session_build_02','prepare_acd_01','capacity_auto_01','capacity_forecast_01','compatibility_verification_01','guard_readonly_01','preflight_01','final_checks_01','preflight_verify_01','inspect_readonly_01','prior_seals_01')
for name in required:assert json.loads((W/(name+'_exit.json')).read_text())['exitCode']==0,name
for name in ('authorization.json','deploy_attempt.json','backup.sha256','echo_before_s3d.ACD','canonical_downloaded.L5X','genealogy_restored.L5X'):assert not (W/name).exists(),name
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
pin=(W/'canonical.sha256').read_text().strip()
assert pin=='E5CA9AB3493AABF93E72A728EBDF5630E8056EEA2AC82254B38913B8C7CF7C9D'
assert sha(W/'s3d_canonical.ACD')==sha(W/'capacity_review.ACD')==pin
assert sha(W/'genealogy_s3d_01.L5X')=='03E0775EDD8A1A22D88D198D4D3CE2B7C19A2F2029A40E3C428CB838FC2EE962'
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD'))=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
cap=json.loads((W/'capacity_review.json').read_text());raw=(W/'capacity_auto_capture_01.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()==cap['CaptureSha256']
normalized=capacity.normalize(json.loads(raw.decode('utf-8-sig')),pin)
assert all(cap[k]==v for k,v in normalized.items())
prior=json.loads((W/'baseline_capacity.json').read_text())
assert sha(W/'baseline_capacity.json')==json.loads((W/'baseline_reference.json').read_text())['capacitySha256']
for suffix in ('Sha256','UsedStandardBlocks','AvailableBlocks','TotalBlocks'):
 assert cap['Baseline'+suffix]==prior['CanonicalSha256' if suffix=='Sha256' else suffix]
assert cap['DeltaUsedStandardBlocks']==182464
for label in ('echo','physical'):
 assert json.loads((W/(label+'_readback_01.log')).read_text())['Equivalent']
prepared=json.loads((W/'canonical_prepared_compare.json').read_text());assert prepared['Equivalent']
for label in ('source','echo','physical','prepared'):
 assert json.loads((W/('access_'+label+'_01.json')).read_text())['passed']
bindings=json.loads((W/'source_bindings_01.json').read_text())
for path,expected in bindings['sha256'].items():assert sha(ROOT/path).lower()==expected,path
assert len(bindings['sha256'])==70
for file in W.rglob('*.py'):
 if not any(p in ('bin','obj','__pycache__') for p in file.parts):compile(file.read_bytes(),str(file),'exec')
assert W.as_posix() in (W/'session/Program.cs').read_text()
assert 'Opening an ACD takes time' in (W/'session/Program.cs').read_text()
assert json.loads((W/'final_checks_01.json').read_text())['passed']
assert json.loads((W/'preflight.json').read_text())['mode']==1
assert json.loads((W/'preflight_verify_01_exit.json').read_text())['exitCode']==0
assert not json.loads((W/'authorization.template.json').read_text())['CurrentOwnerApproved']
forecast=json.loads((W/'capacity_forecast_01.json').read_text());error=forecast['estimatedUsedBlocks']-cap['UsedStandardBlocks']
report=dict(passed=True,offlineGatesPassed=True,controllerChanges=0,currentAuthorizationPending=True,runtimeAccepted=False,preflightRecorded=True,manualOrdinal=1,expectedPaths=2125,
 requiredSuccessfulRuns=list(required),preparedAcdSha256=pin,sourceSha256=sha(W/'genealogy_s3d_01.L5X'),sourceBindings=70,
 capacityBlocks=cap['UsedStandardBlocks'],availableBlocks=cap['AvailableBlocks'],totalBlocks=cap['TotalBlocks'],deltaBlocks=182464,
 forecastHoldout=dict(estimated=forecast['estimatedUsedBlocks'],measured=cap['UsedStandardBlocks'],errorBlocks=error,errorPercent=100*error/cap['UsedStandardBlocks'],planningBudget=forecast['planningBudgetBlocks'],measurementExcludedFromCalibration=True),
 predecessorRecords=json.loads((W/'prior_seals_verification_01.json').read_text())['records'],capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (W/'preparation_verification_01.json').open('x') as out:json.dump(report,out,indent=2)
print(json.dumps(report))
