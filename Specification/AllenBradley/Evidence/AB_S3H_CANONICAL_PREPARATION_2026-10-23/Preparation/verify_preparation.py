"""Close the exact S3h offline gate; never infer controller authorization."""
from pathlib import Path
import datetime,hashlib,json,re,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0,str(T));import fraktal_ab_studio_capacity as capacity
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
required=('generation_03','focused_04','frozen_01','native_echo_03','native_physical_03',
    'echo_readback_03','physical_readback_03','echo_access_03','physical_access_03',
    'session_preparation_01','helper_build_01','prepare_acd_01','finish_preparation_01',
    'prepared_readback_01','prepared_access_01','capacity_auto_01','capacity_forecast_01',
    'current_guard_01','current_preflight_01','current_final_checks_01','close_sources_01',
    'compatibility_01','predecessor_seals_01','ab_suite_02','root_tests_02','ab_spec_02',
    'ab_contracts_02','consistency_02','whitespace_01','failed_analysis_01','finalize_documents_01')
for label in required:assert json.loads((P/(label+'_exit.json')).read_text())['exitCode']==0,label
times={}
for label,count in (('ab_suite_02',2138),('root_tests_02',74),('focused_04',11)):
    text=(P/(label+'.log')).read_text();found=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK',text)
    assert found and int(found[1])==count;times[label]=float(found[2])
pin=(P/'canonical.sha256').read_text().strip()
assert pin=='C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC'
assert sha(P/'s3h_canonical.ACD').upper()==sha(P/'capacity_review.ACD').upper()==pin
source=sha(P/'s3h_candidate_03.L5X');assert source==sha(P/'s3h_regenerated_01.L5X')=='e83b9a2cd9593718026528ccdbd83a1ead6c8a52948fc6616006daffb0567315'
for label in ('echo_readback_03','physical_readback_03','prepared_readback_01'):
    row=json.loads((P/(label+'.log')).read_text());assert row['Equivalent'] and row['ExecutableBodies']==55 and row['AuthoredInitialValues']==40885
for label in ('echo_access_03','physical_access_03','prepared_access_01'):assert json.loads((P/(label+'.json')).read_text())['passed']
cap=json.loads((P/'capacity_review.json').read_text());capture=P/'capacity_capture_01.json'
assert sha(capture)==cap['CaptureSha256']
assert all(cap[k]==v for k,v in capacity.normalize(json.loads(capture.read_text(encoding='utf-8-sig')),pin).items())
assert (cap['UsedStandardBlocks'],cap['AvailableBlocks'],cap['TotalBlocks'],cap['DeltaUsedStandardBlocks'])==(2501720,644008,3145728,94520)
baseline=json.loads((P/'baseline_capacity.json').read_text())
assert sha(P/'baseline_capacity.json').upper()==json.loads((P/'baseline_reference.json').read_text())['capacitySha256']
for key in ('Sha256','UsedStandardBlocks','AvailableBlocks','TotalBlocks'):assert cap['Baseline'+key]==baseline['CanonicalSha256' if key=='Sha256' else key]
bindings=json.loads((P/'source_bindings_01.json').read_text());assert len(bindings['sha256'])==157
for name,value in bindings['sha256'].items():assert sha(ROOT/name)==value,name
raw=(T/'fraktal_ab_generate.py').read_bytes();assert raw.count(b'\n')==raw.count(b'\r\n')
for name in ('authorization.json','deploy_attempt.json','backup.sha256','canonical_downloaded.L5X','genealogy_restored.L5X'):assert not (P/name).exists(),name
template=json.loads((P/'authorization.template.json').read_text())
for key in ('CurrentOwnerApproved','ManualNormalizationAuthorized','AccessVectorsAuthorized','ConfigurationVectorsAuthorized','FaultClearAuthorized','ClockSetAuthorized'):assert template[key] is False
assert template['CanonicalSha256']==pin and template['Serial']=='601FC87B' and template['NoAddedDirectTraceabilityWrites']
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')).upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
assert json.loads((P/'current_final_checks_01.json').read_text())['passed']
assert json.loads((P/'preflight.json').read_text())['manifest']=='6DEC4C1DC2F7F78A'
assert json.loads((P/'compatibility_verification_01.json').read_text())['passed']
assert len(json.loads((P/'compatibility_verification_01.json').read_text())['priorStages'])==8
v2=json.loads((ROOT/'Specification/AllenBradley/AB_FROZEN_CONTRACTS_V2.json').read_text());m=v2['approvedTraceabilityCorrection']
assert not v2['active'] and m['typeCorrections']==36 and m['unchangedAddedPaths']==242 and not m['runtimeAccepted'] and not m['controllerChangesAuthorized']
seals=json.loads((P/'predecessor_seals_01.json').read_text());assert seals['passed'] and seals['predecessorRecords']==27 and seals['predecessorArtifacts']==6251
failures=[dict(label=p.name.removesuffix('_exit.json'),exitCode=json.loads(p.read_text())['exitCode']) for p in sorted(P.glob('*_exit.json')) if json.loads(p.read_text())['exitCode']!=0]
assert {r['label'] for r in failures}=={'focused_01','native_echo_01','native_echo_02','ab_suite_01'}
report=dict(passed=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),offlineGatesPassed=True,
    currentAuthorizationPending=True,controllerChanges=0,controllerAccess='read-only baseline checks',runtimeAccepted=False,
    sourceSha256=source,preparedAcdSha256=pin,canonicalAddedPaths=278,approvedTypePaths=36,otherAddedPathsExact=242,
    unsetPartStampCorrection=True,expectedFullRingCanonicalPagePaths=[3950,3900,3550],
    cumulativeLegacyInventory=4288,totalLegacyInventory=4437,remainingLegacyInventory=149,
    abTests=2138,abSeconds=times['ab_suite_02'],rootTests=74,rootSeconds=times['root_tests_02'],focusedTests=11,
    sourceBindings=157,capacityBlocks=2501720,availableBlocks=644008,totalBlocks=3145728,deltaFromAcceptedS3gBlocks=94520,
    scanMeasured=False,plannedCandidateRows=41,plannedBaselineRows=31,plannedTotalChecks=72,
    sha256=bindings['sha256'],changedExistingSources=bindings['changedExistingSources'],addedSources=bindings['addedSources'],
    failedRunsRetained=failures,requiredSuccessfulRuns=list(required),priorSeals=seals['priorSeals'],predecessorRecords=27,predecessorArtifacts=6251)
with (P/'preparation_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('sha256','priorSeals','changedExistingSources','addedSources','requiredSuccessfulRuns')}))
