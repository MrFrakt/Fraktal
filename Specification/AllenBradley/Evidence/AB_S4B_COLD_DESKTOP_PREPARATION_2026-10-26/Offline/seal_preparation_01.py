"""Seal the concrete unapproved cold-start/desktop package; never touch Echo."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json

R = Path('C:/Users/SoftIndVM/Fraktal')
W = Path(__file__).parent
S = W.parent / 'session_01'
OLDW = Path('C:/work/fraktal-ab-s4b-20261025/offline_01')
OLD = OLDW.parent / 'desktop_scan_continue_01'
G = OLDW.parent / 'session_01'
E = R / 'Specification/AllenBradley/Evidence'
NAME = 'AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26'
OUT = E / NAME
REPORT = OUT.with_suffix('.md')
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
load = lambda path: json.loads(Path(path).read_bytes())
pin = load(W / 'prepared_pins_01.json')['acdSha256']
source_pin = load(W / 'prepared_pins_01.json')['sourceSha256']

def save(path, value):
    with path.open('x', encoding='utf-8', newline='') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')

assert not OUT.exists() and not REPORT.exists()
assert not (S / 'source_bindings.json').exists()
for name in ('authorization.json','session_started.json','deploy_attempt.json','echo_before_s4b.ACD',
             'task_monitor_ready.json','desktop_live'):
    assert not (S / name).exists(), name
required = ('ab_suite_01','compile_01','generate_01','build_EchoController_01',
    'readback_EchoController_01','build_PhysicalController_01','readback_PhysicalController_01',
    'prepare_acd_01','prepared_compare_01','prepare_capacity_01','capacity_01',
    'desktop_positive_02','desktop_coverage_tests_01','desktop_analyze_01','prepare_session_01',
    'session_sdk_build_01','session_authorization_checks_02','sdk_gate_echo_01','sdk_gate_physical_01',
    'layout_comparison_01','access_echo_01','access_physical_01','compatibility_02',
    'session_workflow_checks_01','session_readiness_checks_01','readonly_refusals_01',
    'update_status_01','spec_01','contracts_01','consistency_01','root_tests_01','whitespace_01')
for label in required:
    assert load(W / (label + '_exit.json'))['exitCode'] == 0, label
for label, code in (('desktop_stale_rejected_01',1),('desktop_positive_01',1),
    ('compatibility_01',1),('session_authorization_checks_01',1),('cli_refusal_01',255)):
    assert load(W / (label + '_exit.json'))['exitCode'] == code, label
assert b'Ran 2339 tests' in (W / 'ab_suite_01.log').read_bytes()
assert b'Ran 74 tests' in (W / 'root_tests_01.log').read_bytes()
assert '647 ~12: All tests passed!' in (G / 'reader_flutter_01.log').read_text(encoding='utf-8')
assert 'No issues found!' in (G / 'reader_analyze_01.log').read_text(encoding='utf-8')
assert load(OLD / 'final_checks.json')['passed']
old_result = load(OLD / 'session_result.json')
assert old_result['genealogyRestored'] and old_result['authorizationConsumed'] and old_result['rollbackError'] is None
assert not load(OLD / 'runtime_summary_01.json')['nativeAccepted']
assert sha(S / 's4b_read_view.ACD').upper() == pin
assert sha(S / 's4b_read_view.L5X').upper() == source_pin
assert sha(W / 'canonical_cold_01.ACD').upper() == pin
capacity = load(W / 'capacity_auto_01.json')
assert capacity['CanonicalSha256'] == pin and capacity['VerifiedFit'] and capacity['SourceUnchanged']
assert capacity['ReviewProcessClosed'] and capacity['UsedStandardBlocks'] == 2066212
assert load(W / 'cold_layout_comparison_01.json')['manifestAndInitializersIdentical']
assert load(W / 'compatibility_retry_01/accepted_images_01.json')['images'] == 15
positive = load(W.parent / 'desktop_diagnostic_fixture_02/result.json')
assert positive['passed'] and positive['coverageValidated'] and not positive['live'] and len(positive['shots']) == 31
negative = load(W.parent / 'desktop_diagnostic_fixture_03/failure.json')
assert not negative['desktopLiveAccepted'] and not negative['modules']
assert not (W.parent / 'desktop_diagnostic_fixture_03/result.json').exists()
assert (S / 'desktop_diagnostic_qualification_test.dart').read_bytes() == (W / 'desktop_diagnostic_qualification_test.dart').read_bytes()
mirror = load(OLDW / 'isolated_hmi_sources_07.json')
assert len(mirror['files']) == 316
files = set()
allowed = {R / 'FraktalCore/PLC/Allen-Bradley/tools' / name for name in (
    'fraktal_ab_config_read_view.py','test_fraktal_ab_config_read_view.py')}
allowed.update(R / 'Specification/AllenBradley' / name for name in (
    'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md',
    'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md','AB_FROZEN_CONTRACTS_V2.json'))
changed = []
unchanged_plc = 0
unchanged_hmi = 0
for name, expected in load(OLD / 'source_bindings.json')['sha256'].items():
    path = Path(name)
    if path.is_relative_to(OLD):
        path = S / path.relative_to(OLD)
        if not path.is_file():
            continue
    else:
        if sha(path).upper() != expected.upper():
            assert path in allowed, 'unexpected bound source change: ' + name
            changed.append(path.as_posix())
        elif 'FraktalCore/PLC/Allen-Bradley/tools/' in name:
            unchanged_plc += 1
        if '/FraktalCore/HMI/lib/' in name or '/FraktalCore/HMI/packages/' in name:
            assert sha(path).upper() == expected.upper(), name
            unchanged_hmi += 1
    files.add(path)
assert unchanged_plc == 371
assert len([p for p in changed if '/PLC/Allen-Bradley/tools/' in p]) == 2
for row in mirror['files']:
    original, copy = Path(row['source']), Path(row['copy'])
    assert original.read_bytes() == copy.read_bytes() and sha(original) == row['sha256']
    files.update((original, copy))
package = OLDW.parent / 'hmi_verify_01/.dart_tool/package_config.json'
assert load(package)['flutterVersion'] == '3.47.5'
assert (package.parent.parent / 'pubspec.lock').read_bytes() == (R / 'FraktalCore/HMI/pubspec.lock').read_bytes()
helper_copy = package.parent.parent / 'tool/desktop_cold_qualification_test.dart'
assert helper_copy.read_bytes() == (S / 'desktop_diagnostic_qualification_test.dart').read_bytes()
files.update((package, helper_copy))
for path in S.rglob('*'):
    if path.is_file() and '__pycache__' not in path.parts and not any(part in ('obj',) for part in path.parts):
        if path.suffix.lower() in ('.py','.cs','.csproj','.dart','.json','.dll','.exe','.l5x','.acd','.sha256'):
            files.add(path)
files.update(allowed)
files.discard(R / 'FraktalCore/HMI/.dart_tool/package_config.json')
previous = E / 'AB_S4B_DESKTOP_SCAN_CONTINUATION_2026-10-26/manifest.json'
names = {row['name'] for row in load(previous)['priorSeals']}
names.update(('AB_S4B_DESKTOP_SCAN_CONTINUATION_2026-10-26','AB_S4B_DESKTOP_SCAN_RUNTIME_2026-10-26'))
seals = []
for name in sorted(names):
    manifest_path = E / name / 'manifest.json'
    manifest = load(manifest_path)
    if manifest.get('reportSha256'):
        assert sha(E / manifest['report']) == manifest['reportSha256'].lower(), name
    for row in manifest['artifacts']:
        path = manifest_path.parent / row['path']
        assert sha(path) == row['sha256'].lower() and path.stat().st_size == row['bytes'], str(path)
        if row.get('expandedSha256'):
            assert hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest() == row['expandedSha256'].lower()
    seals.append(dict(name=name,manifestSha256=sha(manifest_path),artifacts=len(manifest['artifacts'])))
assert len(seals) == 88
bindings = dict(schema='fraktal.ab.s4b-cold-desktop-source-bindings',gatesPassed=True,
    currentOwnerApproved=False,canonicalSha256=pin,sourceSha256=source_pin,
    unchangedPlcBoundFiles=unchanged_plc,changedPlcBoundFiles=2,
    unchangedHmiProductionFiles=unchanged_hmi,hmiMirrorInputs=len(mirror['files']),
    privatePinnedPackageMap=True,sha256={path.as_posix():sha(path).upper() for path in sorted(files)})

# All preconditions above are read-only. Append-only output starts here.
save(S / 'source_bindings.json', bindings)
with REPORT.open('x',encoding='utf-8',newline='') as stream:
    stream.write((W / 'cold_preparation_report_01.md').read_text(encoding='utf-8'))
artifacts = []
archived = set()
def archive(path, relative):
    assert 'credential' not in path.name.lower(), path
    assert relative not in archived, relative
    archived.add(relative)
    raw = path.read_bytes()
    expanded = None
    if path.suffix.lower() in ('.log','.l5x','.jsonl'):
        expanded = hashlib.sha256(raw).hexdigest()
        raw = gzip.compress(raw,mtime=0)
        relative += '.gz'
    target = OUT / relative
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
    artifacts.append(dict(path=relative,source=path.as_posix(),bytes=len(raw),sha256=sha(target),
        **(dict(expandedSha256=expanded) if expanded else {})))

for path in sorted(files):
    if path.suffix.lower() in ('.acd','.exe','.dll'):
        continue
    if path.is_relative_to(S):
        relative = 'Preparation/' + path.relative_to(S).as_posix()
    elif path.is_relative_to(R):
        relative = 'Source/' + path.relative_to(R).as_posix()
    else:
        continue
    archive(path,relative)
archive(S / 'source_bindings.json','Preparation/source_bindings.json')
for path in sorted(W.iterdir()):
    if path.is_file() and path.suffix.lower() in ('.py','.dart','.json','.log','.l5x','.md'):
        archive(path,'Offline/'+path.name)
for path in sorted((W / 'compatibility_retry_01').iterdir()):
    if path.is_file():
        archive(path,'Compatibility/'+path.name)
for name in ('desktop_diagnostic_fixture_01','desktop_diagnostic_fixture_02','desktop_diagnostic_fixture_03'):
    folder = W.parent / name
    if folder.exists():
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                archive(path,'Desktop/'+name+'/'+path.relative_to(folder).as_posix())
for name in ('cold_start_before_01','cold_start_after_01'):
    for suffix in ('.log','_exit.json'):
        archive(OLD / (name+suffix),'ColdTests/'+name+suffix)
for name in ('reader_flutter_01','reader_analyze_01'):
    for suffix in ('.log','_exit.json'):
        archive(G / (name+suffix),'RetainedHmiGates/'+name+suffix)
archive(OLDW / 'isolated_hmi_sources_07.json','RetainedHmiGates/isolated_hmi_sources_07.json')
save(OUT / 'manifest.json',dict(schema='fraktal.ab.s4b-cold-desktop-preparation',schemaVersion=1,
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
    canonicalSha256=pin,sourceSha256=source_pin,sourceBindingsSha256=sha(S / 'source_bindings.json'),
    nativeSessionAuthorized=False,nativeAccepted=False,controllerChanges=0,abTests=2339,rootTests=74,
    flutterTests=647,flutterSkipped=12,unchangedPlcBoundFiles=unchanged_plc,changedPlcBoundFiles=2,
    unchangedHmiProductionFiles=unchanged_hmi,hmiMirrorInputs=316,priorSeals=seals,artifacts=artifacts,
    credentialFilesArchived=False,acdBinariesArchived=False,sdkBinariesArchived=False))
for row in artifacts:
    assert sha(OUT / row['path']) == row['sha256']
save(W / 'sealed_preparation_01.json',dict(passed=True,manifestSha256=sha(OUT / 'manifest.json'),
    artifacts=len(artifacts),sourceBindings=len(files),priorSeals=len(seals),
    unchangedPlcBoundFiles=unchanged_plc,changedPlcBoundFiles=2,nativeSessionAuthorized=False,controllerChanges=0))
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),sourceBindings=len(files),priorSeals=len(seals),
    nativeSessionAuthorized=False,controllerChanges=0)))
