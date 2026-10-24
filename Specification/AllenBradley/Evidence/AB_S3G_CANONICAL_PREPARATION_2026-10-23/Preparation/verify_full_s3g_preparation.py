"""Close all offline S3g gates and verify every append-only predecessor seal."""
from pathlib import Path
import datetime,gzip,hashlib,json,re,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;E=ROOT/'Specification/AllenBradley/Evidence'
T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
import fraktal_ab_studio_capacity as capacity
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
required=('metrics_schema_05','metrics_behavior_02','full_generation_01','full_native_echo_01','full_echo_readback_01','full_echo_access_01',
    'native_checks_generation_01','bench_native_echo_01','bench_native_physical_01','bench_echo_readback_01','bench_physical_readback_01',
    'bench_echo_access_01','bench_physical_access_01','full_ab_06','root_checks_05','ab_spec_06','ab_contracts_06','strict_consistency_06',
    'session_sources_01','session_build_01','prepare_acd_01','finish_preparation_01','prepared_readback_01','prepared_access_01',
    'full_capacity_auto_01','close_sources_01','full_compatibility_01','current_guard_readonly_01','current_preflight_01','current_final_checks_01',
    'finalize_notes_01','whitespace_gate_02')
for label in required:assert json.loads((P/(label+'_exit.json')).read_text())['exitCode']==0,label
for label,count in (('full_ab_06',2127),('root_checks_05',74),('metrics_behavior_02',9),('metrics_schema_05',4)):
    text=(P/(label+'.log')).read_text();found=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK',text)
    assert found and int(found[1])==count,(label,text[-200:])
pin=(P/'canonical.sha256').read_text().strip()
assert pin=='CCE00F97A6868F823881A5A9316067834FE2B411F9F98DACE891A71C1B4A6331'
assert sha(P/'s3g_canonical.ACD').upper()==sha(P/'capacity_review.ACD').upper()==pin
assert sha(P/'s3g_native_candidate_01.L5X')==sha(P/'s3g_native_regeneration_01.L5X')=='50e0f8977d975a14c5cd6f86a42ae56b8d4f995cd6a2aa52e071c252104dae91'
for label in ('bench_echo_readback_01','bench_physical_readback_01','prepared_readback_01'):
    r=json.loads((P/(label+'.log')).read_text());assert r['Equivalent'] and r['ExecutableBodies']==55 and r['AuthoredInitialValues']==39835
for label in ('bench_echo_access_01','bench_physical_access_01','prepared_access_01'):
    assert json.loads((P/(label+'.json')).read_text())['passed']
cap=json.loads((P/'capacity_review.json').read_text());capture=P/'full_capacity_capture_01.json'
assert sha(capture)==cap['CaptureSha256']
assert all(cap[k]==v for k,v in capacity.normalize(json.loads(capture.read_text(encoding='utf-8-sig')),pin).items())
assert (cap['UsedStandardBlocks'],cap['AvailableBlocks'],cap['TotalBlocks'],cap['DeltaUsedStandardBlocks'])==(2407200,738528,3145728,108752)
baseline=json.loads((P/'baseline_capacity.json').read_text())
assert sha(P/'baseline_capacity.json').upper()==json.loads((P/'baseline_reference.json').read_text())['capacitySha256']
for key in ('Sha256','UsedStandardBlocks','AvailableBlocks','TotalBlocks'):
    assert cap['Baseline'+key]==baseline['CanonicalSha256' if key=='Sha256' else key]
bindings=json.loads((P/'full_source_bindings_01.json').read_text());assert len(bindings['sha256'])==151
for name,pin_source in bindings['sha256'].items():assert sha(ROOT/name)==pin_source,name
for name in ('authorization.json','deploy_attempt.json','backup.sha256','deployed.sha256','canonical_downloaded.L5X','genealogy_restored.L5X'):
    assert not (P/name).exists(),name
template=json.loads((P/'authorization.template.json').read_text())
for key in ('CurrentOwnerApproved','ManualNormalizationAuthorized','AccessVectorsAuthorized','ConfigurationVectorsAuthorized','NativeMetricsVectorsAuthorized','FaultClearAuthorized','ClockSetAuthorized'):
    assert template[key] is False
assert template['CanonicalSha256']==pin and template['Serial']=='601FC87B'
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')).upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
assert json.loads((P/'current_final_checks_01.json').read_text())['passed']
assert json.loads((P/'preflight.json').read_text())['manifest']=='6DEC4C1DC2F7F78A'
compat=json.loads((P/'full_compatibility_verification_01.json').read_text());assert compat['passed'] and len(compat['priorStages'])==7
v2=json.loads((ROOT/'Specification/AllenBradley/AB_FROZEN_CONTRACTS_V2.json').read_text())
m=v2['approvedMetricsCorrection'];assert not v2['active'] and m['dependentValuesApproved'] and m['totalAffectedPaths']==424 and not m['runtimeAccepted'] and not m['controllerChangesAuthorized']
assert set(m['dependentValueInventory'])==set(json.loads((P/'boundary_implications_02.json').read_text())['paths'])
seals=[]
for path in sorted(E.glob('AB_*/manifest.json')):
    if not any(n in path.parent.name for n in ('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL','AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL','AB_S3E_CANONICAL','AB_S3F_CANONICAL','AB_S3G_CANONICAL')):continue
    record=json.loads(path.read_text())
    for item in record['artifacts']:
        artifact=path.parent/item['path'];raw=artifact.read_bytes()
        assert len(raw)==item['bytes'] and sha(artifact)==item['sha256'].lower(),artifact
        if item.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==item['expandedSha256'].lower()
    if record.get('report'):assert sha(E/record['report'])==record['reportSha256'].lower()
    seals.append(dict(name=path.parent.name,artifacts=len(record['artifacts']),manifestSha256=sha(path)))
assert len(seals)==24 and sum(s['artifacts'] for s in seals)==5287
failures=[dict(label=path.name.removesuffix('_exit.json'),exitCode=json.loads(path.read_text())['exitCode']) for path in sorted(P.glob('*_exit.json')) if json.loads(path.read_text())['exitCode']!=0]
report=dict(passed=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),offlineGatesPassed=True,
    currentAuthorizationPending=True,controllerChanges=0,controllerAccess='read-only baseline checks',runtimeAccepted=False,
    sourceSha256=sha(P/'s3g_native_candidate_01.L5X'),preparedAcdSha256=pin,canonicalAddedPaths=1055,
    expectedCanonicalPagePaths=[3672,3622,3272],approvedNumericPaths=200,approvedDependentValuePaths=224,
    unchangedAdditionalPaths=631,abTests=2127,abSeconds=291.415,rootTests=74,rootSeconds=4.523,focusedTests=13,
    sourceBindings=151,capacityBlocks=2407200,availableBlocks=738528,totalBlocks=3145728,deltaFromAcceptedS3fBlocks=108752,
    nativeChecksPrepared=dict(oee=9,profilerHighBits=2,fixedCellsSavedRestored=6),
    plannedCandidateRows=41,plannedNativeVectorResults=11,plannedBaselineRows=31,plannedTotalChecks=83,
    sha256=bindings['sha256'],changedExistingSources=bindings['changedExistingSources'],addedSources=bindings['addedSources'],
    failedRunsRetained=failures,requiredSuccessfulRuns=list(required),priorSeals=seals,predecessorRecords=24,predecessorArtifacts=5287)
with (P/'full_preparation_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('sha256','priorSeals','changedExistingSources','addedSources','requiredSuccessfulRuns')}))
