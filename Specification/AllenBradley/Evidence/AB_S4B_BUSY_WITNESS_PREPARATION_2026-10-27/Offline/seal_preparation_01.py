"""Freeze the apparatus-only retry over hash-identical shipping/PLC inputs."""
from pathlib import Path
import concurrent.futures
import datetime
import gzip
import hashlib
import json

R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;S=W.parent/'session_01'
OLD=Path('C:/work/fraktal-ab-s4b-array-tiers-20261027/session_01');A=OLD.parent/'offline_01'
E=R/'Specification/AllenBradley/Evidence'
P=E/'AB_S4B_TIER_QUEUE_PREPARATION_2026-10-27'
O=E/'AB_S4B_BUSY_WITNESS_PREPARATION_2026-10-27';REPORT=O.with_suffix('.md')
load=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not O.exists() and not REPORT.exists() and not (S/'source_bindings.json').exists()
assert sha(P/'manifest.json')=='6acef0cd97d1c7028cb9098928c3b70da0f5cff2b0748d041cf9f2f9b4eea1ca'
assert sha(E/'AB_S4B_TIER_QUEUE_ATTEMPT_2026-10-27/manifest.json')=='1226d3062c8e8727cca9834a9ed6e3bb96c834a0757589e06845e4b00b75015b'
for name in ('authorization.json','session_started.json','deploy_attempt.json','echo_before_s4b.ACD','desktop_live'):
    assert not (S/name).exists(),name
for label in ('prepare_session_01','busy_witness_tests_03','sdk_build_01','authorization_checks_02',
    'workflow_checks_01','readiness_checks_01','readonly_refusals_01','part_trace_tests_01',
    'update_status_01','spec_01','contracts_01','consistency_01','root_tests_01','whitespace_01'):
    assert load(W/(label+'_exit.json'))['exitCode']==0,label
assert load(W/'cli_refusal_01_exit.json')['exitCode']==255
assert b'Ran 14 tests' in (W/'busy_witness_tests_03.log').read_bytes()
assert b'Ran 6 tests' in (W/'part_trace_tests_01.log').read_bytes()
assert b'Ran 74 tests' in (W/'root_tests_01.log').read_bytes()
assert b'0 Warning(s)' in (W/'sdk_build_01.log').read_bytes()
assert b'0 Error(s)' in (W/'sdk_build_01.log').read_bytes()
previous=load(OLD/'runtime_summary_01.json')
assert previous['genealogyRestored'] and previous['baselineCases']==31 and previous['finalChecksPassed']
assert previous['authorizationConsumed'] and not previous['currentControllerChangesAuthorized']
assert previous['candidateCases']==0 and previous['observerSamples']==previous['allGoodSamples']==49
assert previous['pairedCapturesReplayed']==1 and not previous['nativeAccepted']
pin='30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5'
source_pin='60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E'
assert sha(S/'s4b_read_view.ACD').upper()==pin
assert sha(S/'s4b_read_view.L5X').upper()==source_pin
docs={R/'Specification/AllenBradley'/n for n in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
    'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md','AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md','AB_FROZEN_CONTRACTS_V2.json')}
files=set();changed=[];plc_count=0
for name,expected in load(OLD/'source_bindings.json')['sha256'].items():
    path=Path(name)
    if path.is_relative_to(OLD):
        path=S/path.relative_to(OLD)
        if not path.is_file():continue
    else:
        if sha(path).upper()!=expected.upper():
            assert path in docs,'unexpected shipping/input change: '+name
            changed.append(path)
        if 'FraktalCore/PLC/Allen-Bradley/tools/' in name:
            assert sha(path).upper()==expected.upper(),name
            plc_count+=1
    files.add(path)
assert set(changed)==docs and plc_count==373
mirror=load(A/'isolated_hmi_sources_01.json')
assert len(mirror['files'])==319
for row in mirror['files']:
    path,copy=Path(row['source']),Path(row['copy'])
    assert sha(path)==row['sha256'] and path.read_bytes()==copy.read_bytes()
    files.update((path,copy))
for path in S.rglob('*'):
    if path.is_file() and not any(part in ('obj','__pycache__') for part in path.parts):
        if path.suffix.lower() in ('.py','.cs','.csproj','.dart','.json','.dll','.exe','.l5x','.acd','.sha256'):
            files.add(path)
assert (S/'login_busy_witness.py').read_bytes()==(W/'login_busy_witness.py').read_bytes()
for name in ('qualification_session_v2.py','desktop_readonly.py','task_monitor.py','session/Program.cs',
    'desktop_diagnostic_qualification_test.dart','part_read_diagnostics.py'):
    assert (S/name).read_text(encoding='utf-8')==(OLD/name).read_text(encoding='utf-8').replace(OLD.as_posix(),S.as_posix()),name
package=Path('C:/work/fraktal-ab-s4b-20261025/hmi_verify_01/.dart_tool/package_config.json')
assert load(package)['flutterVersion']=='3.47.5'
assert (package.parent.parent/'pubspec.lock').read_bytes()==(R/'FraktalCore/HMI/pubspec.lock').read_bytes()
assert not load(S/'authorization.template.json')['CurrentOwnerApproved']
assert load(S/'authorization.template.json')['SessionOnlyLoginBusyWitness'] is True
files.add(package);files.update(docs)
files.discard(R/'FraktalCore/HMI/.dart_tool/package_config.json')
names={row['name'] for row in load(P/'manifest.json')['priorSeals']}
names.update(('AB_S4B_TIER_QUEUE_PREPARATION_2026-10-27','AB_S4B_TIER_QUEUE_ATTEMPT_2026-10-27'))
assert len(names)==102
checks=[];seals=[]
for name in sorted(names):
    path=E/name/'manifest.json';manifest=load(path)
    if manifest.get('reportSha256'):assert sha(E/manifest['report'])==manifest['reportSha256'].lower(),name
    checks.extend((path.parent/row['path'],row) for row in manifest['artifacts'])
    seals.append(dict(name=name,manifestSha256=sha(path),artifacts=len(manifest['artifacts'])))
def verify(item):
    path,row=item;raw=path.read_bytes()
    assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'].lower(),path
    if row.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==row['expandedSha256'].lower(),path
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(verify,checks))
def save(path,value):
    with path.open('x',encoding='utf-8',newline='') as f:json.dump(value,f,indent=2,ensure_ascii=False);f.write('\n')
# All bound-input/gate/prior-seal checks pass before any immutable output exists.
save(S/'source_bindings.json',dict(schema='fraktal.ab.s4b-busy-witness-source-bindings',gatesPassed=True,
    currentOwnerApproved=False,canonicalSha256=pin,sourceSha256=source_pin,unchangedPlcBoundFiles=373,
    changedHmiFiles=[],addedHmiFiles=[],hmiMirrorInputs=319,sessionOnlyLoginBusyWitness=True,
    privatePinnedPackageMap=True,sha256={p.as_posix():sha(p).upper() for p in sorted(files)}))
with REPORT.open('x',encoding='utf-8',newline='') as f:f.write((W/'busy_preparation_report_01.md').read_text(encoding='utf-8'))
artifacts=[]
def archive(path,relative):
    assert 'credential' not in path.name.lower(),path
    raw=path.read_bytes();expanded=None
    if path.suffix.lower() in ('.log','.l5x'):
        expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);relative+='.gz'
    target=O/relative;target.parent.mkdir(parents=True,exist_ok=True)
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
    if path.is_file() and path.name!='seal_preparation_01.log' and path.suffix.lower() in ('.py','.json','.log','.md'):
        archive(path,'Offline/'+path.name)
save(O/'manifest.json',dict(schema='fraktal.ab.s4b-busy-witness-preparation',schemaVersion=1,
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
    canonicalSha256=pin,sourceSha256=source_pin,sourceBindingsSha256=sha(S/'source_bindings.json'),
    transferredPreparationManifestSha256=sha(P/'manifest.json'),abTests=2339,rootTests=74,
    flutterTests=665,flutterSkipped=12,busyWitnessTests=14,partTraceTests=6,
    unchangedPlcBoundFiles=373,changedShippingHmiFiles=0,sessionOnlyLoginBusyWitness=True,
    nativeSessionAuthorized=False,nativeAccepted=False,controllerChanges=0,priorSeals=seals,
    artifacts=artifacts,credentialFilesArchived=False,acdBinariesArchived=False,sdkBinariesArchived=False))
for row in artifacts:assert sha(O/row['path'])==row['sha256']
save(W/'sealed_preparation_01.json',dict(passed=True,manifestSha256=sha(O/'manifest.json'),artifacts=len(artifacts),
    sourceBindings=len(files),priorSeals=len(seals),unchangedPlcBoundFiles=373,changedShippingHmiFiles=0,
    nativeSessionAuthorized=False,controllerChanges=0))
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),sourceBindings=len(files),priorSeals=len(seals),
    changedShippingFiles=0,nativeSessionAuthorized=False,controllerChanges=0)))
