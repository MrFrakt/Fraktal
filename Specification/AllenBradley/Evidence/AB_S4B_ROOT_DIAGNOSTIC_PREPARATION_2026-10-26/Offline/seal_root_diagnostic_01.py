"""Seal a fresh unapproved S4b session with root-refusal evidence capture."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json

R = Path('C:/Users/SoftIndVM/Fraktal')
W = Path(__file__).parent
L = W.parent / 'session_01'
OLD = W.parent / 'retry_template_01'
D = W.parent / 'retry_root_diagnostic_01'
E = R / 'Specification/AllenBradley/Evidence'
OUT = E / 'AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26'
REPORT = OUT.with_suffix('.md')
load = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')

assert not OUT.exists() and not REPORT.exists()
for name in ('authorization.json', 'session_started.json', 'deploy_attempt.json', 'echo_before_s4b.ACD'):
    assert not (D / name).exists(), name
labels = ('seal_template_retry_attempt_01', 'prepare_root_diagnostic_01',
          'root_diagnostic_sdk_build_01', 'root_diagnostic_authorization_checks_01',
          'refresh_diagnostic_hmi_01', 'diagnostic_flutter_01', 'diagnostic_analyze_01',
          'root_diagnostic_status_01', 'root_diagnostic_spec_01', 'root_diagnostic_contracts_01',
          'root_diagnostic_consistency_01', 'root_diagnostic_tests_01', 'root_diagnostic_whitespace_01')
for label in labels:
    assert load(L / (label + '_exit.json'))['exitCode'] == 0, label
assert '637 ~12: All tests passed!' in (L / 'diagnostic_flutter_01.log').read_text(encoding='utf-8')
assert 'No issues found!' in (L / 'diagnostic_analyze_01.log').read_text(encoding='utf-8')
result = load(OLD / 'session_result.json')
assert result['genealogyRestored'] and result['authorizationConsumed'] and result['rollbackError'] is None
assert load(OLD / 'final_checks.json')['passed']
pin = '7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF'
source_pin = 'C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F'
assert sha(D / 's4b_read_view.ACD').upper() == pin
assert sha(D / 's4b_read_view.L5X').upper() == source_pin
files = set()
unchanged_plc = 0
unchanged_hmi_production = 0
for name, expected in load(OLD / 'source_bindings.json')['sha256'].items():
    path = Path(name)
    if 'FraktalCore/PLC/Allen-Bradley/tools/' in name:
        assert sha(path).upper() == expected.upper(), name
        unchanged_plc += 1
    if '/FraktalCore/HMI/lib/' in name or '/FraktalCore/HMI/packages/' in name:
        assert sha(path).upper() == expected.upper(), name
        unchanged_hmi_production += 1
    if path.is_relative_to(OLD):
        path = D / path.relative_to(OLD)
        if not path.is_file():
            continue
    files.add(path)
mirror = load(W / 'isolated_hmi_sources_03.json')
for row in mirror['files']:
    assert Path(row['source']).read_bytes() == Path(row['copy']).read_bytes()
    assert sha(Path(row['source'])) == row['sha256']
    files.add(Path(row['source']))
assert load(W.parent / 'hmi_verify_01/.dart_tool/package_config.json')['flutterVersion'] == '3.47.5'
assert (W.parent / 'hmi_verify_01/pubspec.lock').read_bytes() == (R / 'FraktalCore/HMI/pubspec.lock').read_bytes()
files.update((D / 'session/bin/Debug/net8.0/win-x86').glob('*.dll'))
files.update((D / 'session/bin/Debug/net8.0/win-x86').glob('*.json'))
files.add(D / 'session/bin/Debug/net8.0/win-x86/S4bSession.exe')
for folder, pattern in ((D, '*.py'), (D / 'scripts', '*.py'), (D / 'session', '*.cs'), (D / 'session', '*.csproj')):
    files.update(folder.glob(pattern))
files.update(D / name for name in ('s4b_read_view.ACD', 's4b_read_view.L5X', 'authorization.template.json',
    'dart_package_config.json', 'canonical.sha256', 'genealogy.sha256', 'capacity_review.json', 'canonical_prepared_compare.json'))
files.discard(R / 'FraktalCore/HMI/.dart_tool/package_config.json')
save(D / 'source_bindings.json', dict(schema='fraktal.ab.s4b-root-diagnostic-source-bindings',
    gatesPassed=True, currentOwnerApproved=False, canonicalSha256=pin, sourceSha256=source_pin,
    unchangedPlcBoundFiles=unchanged_plc, unchangedHmiProductionFiles=unchanged_hmi_production,
    privatePinnedPackageMap=True, sha256={p.as_posix(): sha(p).upper() for p in sorted(files)}))
previous_prep = E / 'AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26/manifest.json'
names = {row['name'] for row in load(previous_prep)['priorSeals']}
names.update(('AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26', 'AB_S4B_TEMPLATE_RETRY_ATTEMPT_2026-10-26'))
seals = []
total = 0
for name in sorted(names):
    path = E / name / 'manifest.json'
    manifest = load(path)
    if manifest.get('reportSha256'):
        assert sha(E / manifest['report']) == manifest['reportSha256'].lower()
    for row in manifest['artifacts']:
        artifact = path.parent / row['path']
        assert sha(artifact) == row['sha256'].lower() and artifact.stat().st_size == row['bytes']
        if row.get('expandedSha256'):
            assert hashlib.sha256(gzip.decompress(artifact.read_bytes())).hexdigest() == row['expandedSha256'].lower()
    seals.append(dict(name=name, manifestSha256=sha(path), artifacts=len(manifest['artifacts'])))
    total += len(manifest['artifacts'])
report = f'''# S4b root-sample diagnostic preparation — 2026-10-26

**A fresh unchanged-image diagnostic session is prepared and is not authorized.**
The [Template retry](AB_S4B_TEMPLATE_RETRY_ATTEMPT_2026-10-26.md) passed discovery
but failed its first root-sample check before candidate writes. Genealogy,
the original five documents and 31/31 baseline/final checks are restored.
The previous approval is consumed. Native S4b and desktop acceptance remain open.

## Image and scope

- Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0.
- Prepared ACD `{pin}`.
- Source `{source_pin}`.
- Exact-image offline Capacity **2,066,100 used /1,079,628 available /
  3,145,728 total Blocks (65%)**. Both v38 builds/read-backs and access audits
  transfer through unchanged source/image hashes.
- Runner: `C:/work/fraktal-ab-s4b-20261025/retry_root_diagnostic_01/qualification_session_v2.py`.

The operation scope is unchanged: fresh guards/backup; guarded MANUAL
normalization if needed; Program/download/Run; the first read-only Dart
snapshot must pass before five-document restore and the 41 inherited candidate
cases start. Concurrent read-only observation, all-bank configuration/detail
reads, equivalence/acquisition/scan follow; then pinned genealogy rollback,
exact original host documents, 31 baseline cases, MANUAL cleanup and final
checks/preflight. Candidate work stops at the first failure. Fault clears,
clock changes, power/vendor-state operations and Echo hard kills are excluded.

This session may stop at the same root refusal. Its purpose is to preserve
the actual condition before choosing a production correction; no acceptance
or corrected scheduling result is promised.

## Diagnostic change and its limits

Only the read-only qualification tool and its tests changed. The tool retains
the refused snapshot in the failure report before throwing. Its record names
missing roots, root identity mismatch/absence and age reaching 1,000 ms
separately, and includes root identity/state DataValue quality, age and reason.
It sets no readiness marker and counts no successful sample on refusal. The
snapshot already excludes command-only secret/text payloads; credentials are
never read by this tool or copied into evidence.

Two tests check refused first-snapshot retention, the quality/reason record,
wrong/missing root identity, missing roots and the unchanged exact age boundary.
No PLC code, publication contract, production client, row guard, freshness,
timeout or retry limit changed. The last observer ran for 2,745 ms including
discovery; its rejected snapshot was not saved, so that elapsed time alone
does not establish the cause.

## Gates and bindings

The identical isolated HMI copy contains **{len(mirror['files'])} source inputs**.
Pinned Flutter **3.47.5 /Dart 3.13.4** full suite passes **637 tests, 12 skipped**;
analyzer passes. The lockfile and dependencies are unchanged from the enforced
lockfile gate. The previous Windows debug build transfers through unchanged
production files; only the standalone qualification tool and tests changed.
**{unchanged_plc} PLC/gate bindings** preserve the 2,336-test AB result; all
74 root tests and spec/contracts/strict consistency gates pass again.

The fresh SDK helper builds with zero warnings/errors. Sixteen negative
authorization cases and missing-approval CLI/SDK refusals pass without
controller access. No approval file, session marker, backup or deployment
attempt exists here. The package map is frozen privately and does not depend
on the IDE's shared generated map. **{len(seals)} prior seals /{total} artifacts**
verify unchanged. Credentials and ACD binaries are excluded from this archive.

[AGENTS.md §3a](../../../AGENTS.md) requires “current explicit authorization
and an exact target check immediately before use.” The previous session ended
with verified rollback; a new download/session needs current approval.
V2/Part III remain inactive. S4b desktop, S5-S7 and S3 physical I/O acceptance
remain open. Nothing is committed or pushed.
'''
with REPORT.open('x', encoding='utf-8', newline='') as stream:
    stream.write(report)
artifacts = []
def archive(path, relative):
    raw = path.read_bytes()
    expanded = None
    if path.suffix.lower() in ('.log', '.l5x'):
        expanded = hashlib.sha256(raw).hexdigest()
        raw = gzip.compress(raw, mtime=0)
        relative += '.gz'
    target = OUT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
    artifacts.append(dict(path=relative, source=path.as_posix(), bytes=len(raw), sha256=sha(target),
                          **({'expandedSha256': expanded} if expanded else {})))
for path in sorted(files):
    if path.suffix.lower() in ('.acd', '.exe', '.dll'):
        continue
    if path.is_relative_to(D):
        relative = 'Preparation/' + path.relative_to(D).as_posix()
    elif path.is_relative_to(R):
        relative = 'Source/' + path.relative_to(R).as_posix()
    else:
        continue
    assert 'credential' not in path.name.lower()
    archive(path, relative)
archive(D / 'source_bindings.json', 'Preparation/source_bindings.json')
for label in labels:
    for suffix in ('.log', '_exit.json'):
        archive(L / (label + suffix), 'Offline/' + label + suffix)
for path in (W / 'prepare_root_diagnostic_01.py', W / 'root_diagnostic_authorization_checks.py',
             W / 'refresh_diagnostic_hmi_01.py', W / 'isolated_hmi_sources_03.json',
             W / 'root_diagnostic_authorization_checks_01.json', W / 'seal_root_diagnostic_01.py',
             W / 'update_root_diagnostic_status_01.py'):
    archive(path, 'Offline/' + path.name)
for name in ('missing_approval_cli_root_diagnostic_01.log', 'missing_approval_sdk_root_diagnostic_01.log'):
    archive(W / name, 'Offline/' + name)
save(OUT / 'manifest.json', dict(schema='fraktal.ab.s4b-root-diagnostic-preparation', schemaVersion=1,
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(), report=REPORT.name, reportSha256=sha(REPORT),
    canonicalSha256=pin, sourceSha256=source_pin, sourceBindingsSha256=sha(D / 'source_bindings.json'),
    nativeSessionAuthorized=False, nativeAccepted=False, abTests=2336, unchangedPlcBoundFiles=unchanged_plc,
    unchangedHmiProductionFiles=unchanged_hmi_production, rootTests=74, flutterTests=637, flutterSkipped=12,
    priorSeals=seals, artifacts=artifacts, credentialFilesArchived=False, acdBinariesArchived=False, controllerChanges=0))
for row in artifacts:
    assert sha(OUT / row['path']) == row['sha256']
save(W / 'sealed_root_diagnostic_01.json', dict(passed=True, manifestSha256=sha(OUT / 'manifest.json'),
    artifacts=len(artifacts), sourceBindings=len(files), priorSeals=len(seals), unchangedPlcBoundFiles=unchanged_plc,
    nativeSessionAuthorized=False, controllerChanges=0))
print(json.dumps(dict(sealed=True, artifacts=len(artifacts), sourceBindings=len(files),
    priorSeals=len(seals), nativeSessionAuthorized=False, controllerChanges=0)))
