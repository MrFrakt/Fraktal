"""Seal the same-image four-connection reader after all gates; no controller access."""
from pathlib import Path
import concurrent.futures
import datetime
import gzip
import hashlib
import json

R=Path('C:/Users/SoftIndVM/Fraktal')
W=Path(__file__).parent
S=W.parent/'session_01'
OLD=Path('C:/work/fraktal-ab-s4b-startup-20261027/session_01')
G=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01')
E=R/'Specification/AllenBradley/Evidence'
P=E/'AB_S4B_STARTUP_DIAGNOSTIC_PREPARATION_2026-10-27'
O=E/'AB_S4B_PARALLEL_READER_PREPARATION_2026-10-27'
REPORT=O.with_suffix('.md')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_bytes())
assert not O.exists() and not REPORT.exists() and not (S/'source_bindings.json').exists()
for name in ('authorization.json','session_started.json','deploy_attempt.json','echo_before_s4b.ACD','desktop_live'):
    assert not (S/name).exists(),name
labels=('verify_prepared_session_02','pool_tests_06','pool_pub_01','pool_flutter_02',
    'pool_analyze_02','pool_windows_02','record_mirror_03','pool_sdk_build_01',
    'pool_authorization_checks_01','pool_workflow_checks_01','pool_readiness_checks_01',
    'pool_readonly_refusals_01','update_status_01','pool_spec_01','pool_contracts_01',
    'pool_consistency_01','pool_root_tests_01','pool_whitespace_01')
for label in labels:assert load(W/(label+'_exit.json'))['exitCode']==0,label
for label in ('pool_tests_04','pool_tests_05'):
    assert load(W/(label+'_exit.json'))['exitCode']==1,label
assert load(W/'cli_refusal_01_exit.json')['exitCode']==255
assert b'660 ~12: All tests passed!' in (W/'pool_flutter_02.log').read_bytes()
assert b'No issues found!' in (W/'pool_analyze_02.log').read_bytes()
assert b'Ran 74 tests' in (W/'pool_root_tests_01.log').read_bytes()
assert b'Ran 2339 tests' in (G/'ab_suite_01.log').read_bytes()
prior_result=load(OLD/'session_result.json')
assert prior_result['genealogyRestored'] and prior_result['authorizationConsumed'] and prior_result['rollbackError'] is None
assert load(OLD/'final_checks.json')['passed']
assert load(OLD/'runtime_summary_01.json')['observerSamples']==906
pin='30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5'
source_pin='60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E'
assert sha(S/'s4b_read_view.ACD').upper()==pin==sha(G/'canonical_cold_01.ACD').upper()
assert sha(S/'s4b_read_view.L5X').upper()==source_pin
capacity=load(G/'capacity_auto_01.json')
assert capacity['CanonicalSha256']==pin and capacity['VerifiedFit'] and capacity['SourceUnchanged']
mirror=load(W/'isolated_hmi_sources_03.json')
assert len(mirror['files'])==318 and len(mirror['changed'])==6 and len(mirror['added'])==2
allowed={R/'FraktalCore/HMI'/p for p in ('packages/fraktal_opcua_client/lib/src/cip_read_plan.dart',
    'packages/fraktal_opcua_client/lib/src/cip_transport.dart',
    'packages/fraktal_opcua_client/lib/src/cip_session_client.dart',
    'packages/fraktal_opcua_client/lib/src/cip_read_coherence.dart',
    'test/cip_read_coherence_test.dart','test/cip_transport_test.dart')}
allowed.update(R/'Specification/AllenBradley'/p for p in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
    'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md','AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md',
    'AB_FROZEN_CONTRACTS_V2.json'))
allowed_copies={Path(row['copy']) for row in mirror['files'] if Path(row['source']) in allowed}
package=Path('C:/work/fraktal-ab-s4b-20261025/hmi_verify_01/.dart_tool/package_config.json')
assert load(package)['flutterVersion']=='3.47.5'
assert (package.parent.parent/'pubspec.lock').read_bytes()==(R/'FraktalCore/HMI/pubspec.lock').read_bytes()
files=set()
changed=[]
unchanged_plc=0
for name,pin_before in load(OLD/'source_bindings.json')['sha256'].items():
    path=Path(name)
    if path.is_relative_to(OLD):
        path=S/path.relative_to(OLD)
        if not path.is_file():continue
    else:
        if sha(path).upper()!=pin_before.upper():
            assert path in allowed or path in allowed_copies or path==package,'unexpected bound change: '+name
            changed.append(path.as_posix())
        if 'FraktalCore/PLC/Allen-Bradley/tools/' in name:
            assert sha(path).upper()==pin_before.upper(),name
            unchanged_plc+=1
    files.add(path)
assert unchanged_plc==373
assert sum('/FraktalCore/HMI/' in name for name in changed)==6
for row in mirror['files']:
    source,copy=Path(row['source']),Path(row['copy'])
    assert source.read_bytes()==copy.read_bytes() and sha(source)==row['sha256']
    files.update((source,copy))
for path in S.rglob('*'):
    if path.is_file() and not any(p in ('obj','__pycache__') for p in path.parts):
        if path.suffix.lower() in ('.py','.cs','.csproj','.dart','.json','.dll','.exe','.l5x','.acd','.sha256'):
            files.add(path)
files.update(allowed)
files.add(package)
helper=package.parent.parent/'tool/desktop_startup_diagnostic_test.dart'
assert helper.read_bytes()==(S/'desktop_diagnostic_qualification_test.dart').read_bytes()
files.add(helper)
# Strict UI helper and fixtures are unchanged; retain the exact earlier proofs.
U=OLD.parent/'offline_01'
positive=load(U.parent/'desktop_diagnostic_fixture_01/result.json')
assert positive['passed'] and positive['coverageValidated'] and len(positive['shots'])==31 and not positive['live']
startup=load(U.parent/'desktop_diagnostic_fixture_02/failure.json')
assert startup['error']=='FormatException: Injected startup fixture refusal' and not startup['desktopLiveAccepted']
assert b'Null check operator' not in (U/'desktop_startup_refused_01.log').read_bytes()
assert load(U.parent/'desktop_diagnostic_fixture_03/failure.json')['link']=='stale'
assert (S/'desktop_diagnostic_qualification_test.dart').read_bytes()==(OLD/'desktop_diagnostic_qualification_test.dart').read_bytes()
assert load(W/'verified_prepared_session_02.json')['preparedInputsVerified']

files.discard(R/'FraktalCore/HMI/.dart_tool/package_config.json')
names={row['name'] for row in load(P/'manifest.json')['priorSeals']}
names.update(('AB_S4B_STARTUP_DIAGNOSTIC_PREPARATION_2026-10-27','AB_S4B_STARTUP_DIAGNOSTIC_ATTEMPT_2026-10-27'))
assert len(names)==94
seals=[]
checks=[]
for name in sorted(names):
    p=E/name/'manifest.json'
    m=load(p)
    if m.get('reportSha256'):assert sha(E/m['report'])==m['reportSha256'].lower(),name
    for row in m['artifacts']:checks.append((p.parent/row['path'],row))
    seals.append(dict(name=name,manifestSha256=sha(p),artifacts=len(m['artifacts'])))
def check_artifact(item):
    path,row=item
    assert sha(path)==row['sha256'].lower() and path.stat().st_size==row['bytes'],str(path)
    if row.get('expandedSha256'):
        assert hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest()==row['expandedSha256'].lower(),str(path)
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    list(pool.map(check_artifact,checks))
def save(path,value):
    with path.open('x',encoding='utf-8',newline='') as f:
        json.dump(value,f,indent=2,ensure_ascii=False)
        f.write('\n')
# Append-only outputs begin after every input/gate/seal precondition passes.
save(S/'source_bindings.json',dict(schema='fraktal.ab.s4b-parallel-reader-source-bindings',gatesPassed=True,
    currentOwnerApproved=False,canonicalSha256=pin,sourceSha256=source_pin,unchangedPlcBoundFiles=373,
    changedHmiFiles=mirror['changed'],addedHmiFiles=mirror['added'],hmiMirrorInputs=318,privatePinnedPackageMap=True,
    sha256={p.as_posix():sha(p).upper() for p in sorted(files)}))
with REPORT.open('x',encoding='utf-8',newline='') as f:f.write((W/'parallel_preparation_report_01.md').read_text(encoding='utf-8'))
artifacts=[]
def archive(path,relative):
    assert 'credential' not in path.name.lower()
    raw=path.read_bytes()
    expanded=None
    if path.suffix.lower() in ('.log','.l5x'):
        expanded=hashlib.sha256(raw).hexdigest()
        raw=gzip.compress(raw,mtime=0)
        relative+='.gz'
    target=O/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(raw)
    artifacts.append(dict(path=relative,source=path.as_posix(),bytes=len(raw),sha256=sha(target),
        **(dict(expandedSha256=expanded) if expanded else {})))
for path in sorted(files):
    if path.suffix.lower() in ('.acd','.dll','.exe'):continue
    if path.is_relative_to(S):relative='Preparation/'+path.relative_to(S).as_posix()
    elif path.is_relative_to(R):relative='Source/'+path.relative_to(R).as_posix()
    else:continue
    archive(path,relative)
archive(S/'source_bindings.json','Preparation/source_bindings.json')
for path in sorted(W.iterdir()):
    if path.is_file() and path.suffix.lower() in ('.py','.dart','.json','.log','.md'):
        archive(path,'Offline/'+path.name)
for folder in sorted(U.parent.glob('desktop_diagnostic_fixture_*')):
    for path in sorted(folder.rglob('*')):
        if path.is_file():archive(path,'RetainedDesktop/'+folder.name+'/'+path.relative_to(folder).as_posix())
for label in ('desktop_positive_01','desktop_startup_refused_01','desktop_stale_refused_01'):
    for suffix in ('.log','_exit.json'):archive(U/(label+suffix),'RetainedDesktop/'+label+suffix)
for name in ('ab_suite_01','build_EchoController_01','readback_EchoController_01',
    'build_PhysicalController_01','readback_PhysicalController_01','access_echo_01','access_physical_01',
    'sdk_gate_echo_01','sdk_gate_physical_01','capacity_01','prepared_compare_01'):
    for suffix in ('.log','_exit.json'):archive(G/(name+suffix),'RetainedPlcGates/'+name+suffix)
for name in ('capacity_auto_01.json','prepared_pins_01.json','cold_layout_comparison_01.json'):
    archive(G/name,'RetainedPlcGates/'+name)
save(O/'manifest.json',dict(schema='fraktal.ab.s4b-parallel-reader-preparation',schemaVersion=1,
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
    canonicalSha256=pin,sourceSha256=source_pin,sourceBindingsSha256=sha(S/'source_bindings.json'),
    abTests=2339,rootTests=74,flutterTests=660,flutterSkipped=12,unchangedPlcBoundFiles=373,changedHmiFiles=6,addedHmiFiles=2,readConnections=4,
    nativeSessionAuthorized=False,nativeAccepted=False,controllerChanges=0,priorSeals=seals,artifacts=artifacts,
    credentialFilesArchived=False,acdBinariesArchived=False,sdkBinariesArchived=False))
for row in artifacts:assert sha(O/row['path'])==row['sha256']
save(W/'sealed_preparation_01.json',dict(passed=True,manifestSha256=sha(O/'manifest.json'),
    artifacts=len(artifacts),sourceBindings=len(files),priorSeals=len(seals),unchangedPlcBoundFiles=373,
    nativeSessionAuthorized=False,controllerChanges=0))
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),sourceBindings=len(files),priorSeals=len(seals),
    nativeSessionAuthorized=False,controllerChanges=0)))
