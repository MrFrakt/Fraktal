"""Seal V6.10 implementation/rehearsal proof without a native acceptance claim."""
from pathlib import Path
import datetime,gzip,hashlib,json
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
O=R/'Specification/AllenBradley/Evidence/AB_S4B_OWNER_REVISION_OFFLINE_2026-10-29'
report=O.with_suffix('.md');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_bytes())
assert not O.exists() and report.is_file()
labels=['ab_suite_02','full_hmi_03','locked_dependencies_02','analyze_02','windows_profile_02',
 'root_03','ab_spec_03','ab_contracts_03','consistency_03','whitespace_02',
 'compile_01','audit_offline_01','prepare_capacity_01','final_generate_01',
 'owner_publisher_tests_01','owner_fixture_python_01','consumed_scope_tests_01',
 'count_walk_comparison_01','observer_peer_02','final_guard_01','final_preflight_01']
for label in labels:assert load(W/(label+'_exit.json'))['exitCode']==0,label
assert b'Ran 2354 tests' in (W/'ab_suite_02.log').read_bytes()
assert b'+759 ~12: All tests passed!' in (W/'full_hmi_03.log').read_bytes()
profiles=load(W/'three_profiles_01.json');assert profiles['passed'] and profiles['sameFinalSource']
for p,pin in profiles['sourceSha256'].items():assert sha(H/p)==pin,p
assert not load(W/'debug_01/result.json')['passed']
assert load(W/'debug_01/desktop/failure.json')['link']=='stale'
observer=load(W/'observer_peer_qualification_01.json')
assert observer['passed'] and observer['samples']==100 and observer['badSamples']==observer['peerWrites']==0
assert load(W/'configuration_peer_comparison_01.json')['scalarComparisons']==1100
capacity=load(W/'capacity_auto_01.json');assert capacity['VerifiedFit'] and capacity['DisplayedUsagePercent']==66
assert load(W/'opt_out_identity_01.json')['passed'] and load(W/'final_emitter_identity_01.json')['passed']
O.mkdir();artifacts=[]
def copy(p,name):
 raw=p.read_bytes();expanded=None
 if p.suffix=='.log':expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);name+='.gz'
 target=O/name;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(raw)
 artifacts.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
     **({'expandedSha256':expanded} if expanded else {})))
for p in sorted(W.rglob('*')):
 if not p.is_file() or p.suffix.lower() not in {'.py','.ps1','.json','.jsonl','.log','.gz','.dart','.png','.csv','.sha256','.md'}:continue
 if any(s in p.parts for s in ['__pycache__','bin','obj','.dart_tool','build']):continue
 if p.name in ['seal_offline_owner_02.log','seal_offline_owner_02_exit.json']:continue
 assert not any(s in p.name.lower() for s in ['credential','password'])
 copy(p,'Work/'+p.relative_to(W).as_posix())
paths=list((R/'FraktalCore/PLC/Allen-Bradley/tools').glob('*.py'))
for tree in ['lib','packages/fraktal_opcua_client/lib','test','integration_test','test_driver','tool']:
 paths+=list((H/tree).rglob('*.dart'))
paths += [H/p for p in ['pubspec.yaml','pubspec.lock','test/fixtures/cip_owner_apparatus_v610.json.gz',
    'test/fixtures/cip_owner_manifest_v610.json.gz']]
paths += [R/'tools'/p for p in ['check_ab_spec.py','check_ab_contracts.py','check_consistency.py',
    'test_check_ab_spec.py','test_check_ab_contracts.py','test_check_consistency.py']]
paths += [R/'Specification/AllenBradley'/p for p in ['AB_FROZEN_CONTRACTS_V2.json',
    'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_STATUS_LOG_2026-10-27.md',
    'AB_CANONICAL_PUBLICATION_S4B_OWNER_REVISION_REVIEW_2026-10-29.md',
    'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md']]
bound={}
for p in sorted(set(paths)):
 relative=p.relative_to(R).as_posix();bound[relative]=sha(p);copy(p,'Current/'+relative)
value=dict(report=dict(path=report.name,sha256=sha(report)),createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 sourceSha256=bound,artifactCount=len(artifacts),artifacts=artifacts,
 offlineGatesPassed=True,desktopPrerequisitePassed=True,observerPeerPassed=True,
 abTests=2354,hmiPassed=759,hmiSkipped=12,rootTests=74,
 nativeAccepted=False,nativeAcceptanceClaim=False,controllerChanges=0,
 credentialFilesArchived=False,binaryOrAcdArchived=False)
with (O/'artifact_manifest.json').open('x') as f:json.dump(value,f,indent=2)
for a in artifacts:
 p=O/a['path'];assert sha(p)==a['sha256']
 if 'expandedSha256' in a:assert hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()==a['expandedSha256']
print(json.dumps(dict(sealed=str(O),artifactCount=len(artifacts),sourceFiles=len(bound),manifestSha256=sha(O/'artifact_manifest.json'))))
