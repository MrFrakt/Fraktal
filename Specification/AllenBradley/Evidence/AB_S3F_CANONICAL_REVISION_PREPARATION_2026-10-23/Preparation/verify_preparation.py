"""Final offline gates for the S3f retained-revision follow-up."""
from pathlib import Path
import datetime,gzip,hashlib,json,re,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_studio_capacity as capacity
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
required=('generation_01','revision_model_01','revision_fixture_tests_01','restart_check_tests_01','ab_suite_01','root_tests_01',
 'native_echo_01','native_physical_01','echo_readback_01','physical_readback_01','echo_audit_01','physical_audit_01',
 'access_source_01','access_echo_01','access_physical_01','session_sources_01','session_build_01','prepare_acd_01',
 'prepared_readback_01','prepared_audit_01','access_prepared_01','capacity_auto_01','source_delta_02','close_inputs_01',
 'compatibility_01','guard_readonly_01','preflight_01','final_checks_01')
for n in required:assert json.loads((W/(n+'_exit.json')).read_text())['exitCode']==0,n
for n in ('authorization.json','deploy_attempt.json','backup.sha256','deployed.sha256','restart_before.json','restart_after.json'):assert not (W/n).exists(),n
pin=(W/'canonical.sha256').read_text().strip()
assert pin=='BD030AEB01D58469D452D877A9CFF2868B79DE45055A3795D1D1479BB2771183'
assert sha(W/'s3f_canonical.ACD')==sha(W/'capacity_review.ACD')==pin
assert sha(W/'genealogy_s3f_revision_01.L5X')==sha(W/'generation_recheck.L5X')=='B71E30ABBE8221AAA39A0DF8EEB934897FE0A4B0711047EFDC7D653A20AE7CF3'
for n in ('echo_readback_01','physical_readback_01','prepared_readback_01'):
 d=json.loads((W/(n+'.log')).read_text());assert d['Equivalent'] and d['ExecutableBodies']==52 and d['AuthoredInitialValues']==37556
for n in ('source','echo','physical','prepared'):assert json.loads((W/('access_'+n+'_01.json')).read_text())['passed']
cap=json.loads((W/'capacity_review.json').read_text());capture=W/'capacity_auto_capture_01.json'
assert sha(capture).lower()==cap['CaptureSha256']
assert all(cap[k]==v for k,v in capacity.normalize(json.loads(capture.read_text(encoding='utf-8-sig')),pin).items())
assert cap['UsedStandardBlocks']==2298448 and cap['DeltaUsedStandardBlocks']==36
prior=json.loads((W/'baseline_capacity.json').read_text());assert sha(W/'baseline_capacity.json')==json.loads((W/'baseline_reference.json').read_text())['capacitySha256']
for k in ('Sha256','UsedStandardBlocks','AvailableBlocks','TotalBlocks'):assert cap['Baseline'+k]==prior['CanonicalSha256' if k=='Sha256' else k]
bindings=json.loads((W/'source_bindings_01.json').read_text());assert len(bindings['sha256'])==142
for n,pin_source in bindings['sha256'].items():assert sha(ROOT/n).lower()==pin_source,n
for n,count in [('ab_suite_01',2111),('root_tests_01',74)]:
 m=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK',(W/(n+'.log')).read_text());assert m and int(m[1])==count
template=json.loads((W/'authorization.template.json').read_text())
for k in ('CurrentOwnerApproved','ManualNormalizationAuthorized','AccessVectorsAuthorized','ConfigurationVectorsAuthorized','RevisionVectorsAuthorized','RetainedRestartAuthorized','FaultClearAuthorized','ClockSetAuthorized'):assert template[k] is False
source=(W/'session/Program.cs').read_text()
for value in ('RevisionVectorsAuthorized','RetainedRestartAuthorized','restart-canonical','NoDownload=true','restart_checks.py'):assert value in source
assert json.loads((W/'final_checks_01.json').read_text())['passed']
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD'))=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
for p in W.rglob('*.py'):
 if not any(v in ('bin','obj','__pycache__') for v in p.parts):compile(p.read_bytes(),str(p),'exec')
base=ROOT/'Specification/AllenBradley/Evidence';seals=[]
for p in sorted(base.glob('AB_*/manifest.json')):
 if not any(v in p.parent.name for v in ('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL','AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL','AB_S3E_CANONICAL','AB_S3F_CANONICAL')):continue
 m=json.loads(p.read_text())
 for a in m['artifacts']:
  raw=(p.parent/a['path']).read_bytes();assert len(raw)==a['bytes'] and hashlib.sha256(raw).hexdigest()==a['sha256'].lower()
  if a.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==a['expandedSha256'].lower()
 if m.get('report'):assert sha(base/m['report']).lower()==m['reportSha256'].lower()
 seals.append(dict(name=p.parent.name,artifacts=len(m['artifacts']),manifestSha256=sha(p).lower()))
assert len(seals)==20 and sum(s['artifacts'] for s in seals)==4032
failed=[dict(label=p.name.removesuffix('_exit.json'),exitCode=json.loads(p.read_text())['exitCode']) for p in sorted(W.glob('*_exit.json')) if json.loads(p.read_text())['exitCode']!=0]
report=dict(passed=True,offlineGatesPassed=True,runtimeAccepted=False,controllerChanges=0,currentAuthorizationPending=True,
 requiredSuccessfulRuns=list(required),preparedAcdSha256=pin,sourceSha256=sha(W/'genealogy_s3f_revision_01.L5X'),
 sourceBindings=142,expectedChangedPlcBodies=1,addedStLines=1,publicLayoutAndInitialsUnchanged=True,
 capacityBlocks=2298448,availableBlocks=847280,totalBlocks=3145728,deltaCapacityBlocks=36,
 plannedCandidateRows=42,plannedRetainedRestartRows=1,plannedBaselineRows=31,plannedTotalRows=74,
 failedRunsRetained=failed,priorSeals=seals,predecessorRecords=20,predecessorArtifacts=4032,
 capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (W/'preparation_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('priorSeals','requiredSuccessfulRuns')}))
