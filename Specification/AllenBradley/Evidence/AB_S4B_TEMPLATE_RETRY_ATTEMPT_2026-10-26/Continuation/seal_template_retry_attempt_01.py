"""Preserve the approved Template retry and its baseline rollback."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json
import statistics

R = Path('C:/Users/SoftIndVM/Fraktal')
W = Path(__file__).parent
D = W.parent / 'retry_template_01'
E = R / 'Specification/AllenBradley/Evidence'
OUT = E / 'AB_S4B_TEMPLATE_RETRY_ATTEMPT_2026-10-26'
REPORT = OUT.with_suffix('.md')
load = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')

assert not OUT.exists() and not REPORT.exists()
session = load(D / 'session_result.json')
baseline = load(D / 'baseline_regressions.json')
final = load(D / 'final_checks.json')
dart = json.loads(gzip.decompress((D / 'dart_qualification.json.gz').read_bytes()))
assert session['passed'] is False and session['genealogyRestored'] and session['rollbackError'] is None
assert session['authorizationConsumed'] and not session['dumpFiles']
assert len(baseline['rows']) == 31 and all(row['passed'] for row in baseline['rows'])
assert final['passed'] and all(final['checks'].values()) and all(final['savedDocumentsEqual'].values())
assert not (D / 'candidate_regressions.json').exists() and not (D / 'dart_ready.json').exists()
assert dart['passed'] is False and not dart['samples'] and not dart['configurationPages']
assert dart['error'] == 'FormatException: Fresh canonical root sample is unavailable.'
stages = {p.name.removesuffix('_exit.json'): load(p)['exitCode'] for p in D.glob('*_exit.json')}
assert stages['qualification_run_01'] == stages['candidate_regressions'] == stages['dart_observer'] == 1
assert all(code == 0 for name, code in stages.items()
           if name not in ('qualification_run_01', 'candidate_regressions', 'dart_observer'))
bindings = load(D / 'source_bindings.json')
changed = [path for path, pin in bindings['sha256'].items() if sha(Path(path)).upper() != pin.upper()]
assert changed == [(D / 's4b_read_view.ACD').as_posix()], changed
original = Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')
assert sha(original).upper() == 'D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
timing = load(D / 'baseline_timing.json')
samples = [row['values'] for row in timing['samples']]
summary = dict(passed=False, reason=dart['error'], serial='601FC87B',
    templateDiscoveryPassed=True, candidateWritesStarted=False, candidateCases=0,
    baselineCases=31, genealogyRestored=True, finalChecksPassed=True, originalDocumentsRestored=5,
    stageExits=stages, changedBoundFiles=changed,
    changedAcdReason='SDK Save in the approved deployment; exported L5X read-back and access audit pass',
    observerElapsedMs=dart['elapsedMs'],
    rootFailureDetailCaptured=False,
    baselineScanMedianUs=statistics.median(row['FRK_Press_HealthProbe.TaskLastScanUs'] for row in samples),
    baselineScanCumulativeMaxUs=max(row['FRK_Press_HealthProbe.TaskMaxScanUs'] for row in samples),
    overlaps=max(row['FRK_Press_HealthProbe.TaskOverlapCount'] for row in samples),
    authorizationConsumed=True, currentControllerChangesAuthorized=False,
    dumpFiles=[], faultClears=0, clockChanges=0, powerOperations=0, hardKills=0)
save(D / 'runtime_summary_01.json', summary)
save(D / 'owner_authorization_consumed_01.json', dict(serial='601FC87B',
    approvalQuestion='call_378e7db52cb749e49ad59c696606376a:0',
    ownerInstruction='Approve guarded S4b Template retry', authorizationSha256=sha(D / 'authorization.json'),
    sessionResultSha256=sha(D / 'session_result.json'), authorizationConsumed=True,
    currentControllerChangesAuthorized=False))
report = '''# S4b Template retry attempt — 2026-10-26

**Template discovery passed; qualification failed at the first root-sample
check, before candidate writes. Genealogy rollback is verified.** S4b native,
row-coherence, active-workload, performance and desktop acceptance remain open.

The owner answered “Approve guarded S4b Template retry” to
`call_378e7db52cb749e49ad59c696606376a:0`, authorizing the
[sealed retry](AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26.md).
This exact-image session completed with rollback; its approval is consumed.

## Passed

- Fresh service/listener, serial and identity checks: local Echo 601FC87B,
  1756-L81E v38.011, 127.0.0.1 slot 0; Run/Remote, not faulted. Initial
  MANUAL/idle, logged out and five saved/live document equality pass.
- Fresh preflight, backup, Save As audit and baseline access audit pass.
- ACD `7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF`
  downloaded and returned to Run. Source
  `C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F`.
  SDK log, exported L5X read-back and external-access audits pass. The SDK
  changed its working ACD through Save; the pinned original remains intact.
- Corrected Dart Template discovery and manifest/publication discovery reached
  the first snapshot. The previous unterminated-name failure did not recur.
- Pinned genealogy was restored from a hash-checked copy; its original remains
  `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
  Restore SDK/access audits, exact original host-document restoration,
  **31/31 baseline regressions**, MANUAL cleanup, final checks and preflight pass.
- Final state: Run, not faulted, scanning, MANUAL/idle, logged out, not restoring,
  policy restored, five saved/live documents equal. No dumps, fault clears,
  clock changes, power/vendor-state operations or Echo hard kills.

## Failed and skipped

The observer reported **`FormatException: Fresh canonical root sample is
unavailable.`** at the first snapshot, before its readiness marker and before
any candidate fixture writes. The qualification condition checks root presence,
root Status/Name and sample age together. It did not preserve that refused
snapshot, so this record cannot distinguish the specific failing condition or
claim an exact cause. The guard was retained and the runner rolled back.

There are zero complete qualification samples, zero configuration pages and
**0/41 candidate cases**. Candidate all-path equivalence, generic acquisition,
native candidate scan and desktop rendering were not reached. The separate
approved rollback normalization and baseline writes ran as recorded.

All 743 runtime source bindings remain unchanged except the SDK-saved working
ACD. Offline 2,336 AB /74 root /635 Flutter tests (12 skipped), both v38 builds,
Windows build and exact-image **65% Capacity** remain preparation results.

## Next

Preserve the rejected snapshot and root quality/age/reason diagnostics in the
read-only qualification tool, and reproduce any scheduling/quality issue with
recorded bytes and a controlled clock before changing production logic. The
current error is insufficient to justify changing freshness, coherence or retry
limits. A fresh controller-changing session needs current authorization under
AGENTS.md §3a. S4-S7 and S3 physical I/O proof remain open. V2/Part III stay
inactive. Nothing is committed or pushed; no credentials or ACD binaries are
archived.
'''
with REPORT.open('x', encoding='utf-8', newline='') as stream:
    stream.write(report)
artifacts = []
for source in sorted(D.rglob('*')):
    if not source.is_file() or any(part in ('bin', 'obj', '__pycache__') for part in source.relative_to(D).parts):
        continue
    if source.suffix.lower() not in ('.py', '.json', '.gz', '.log', '.txt', '.sha256', '.l5x', '.cs', '.csproj'):
        continue
    assert 'credential' not in source.name.lower()
    relative = 'Runtime/' + source.relative_to(D).as_posix()
    raw = source.read_bytes()
    expanded = None
    if source.suffix.lower() in ('.log', '.l5x'):
        expanded = hashlib.sha256(raw).hexdigest()
        raw = gzip.compress(raw, mtime=0)
        relative += '.gz'
    target = OUT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
    artifacts.append(dict(path=relative, sha256=sha(target), bytes=len(raw),
                          **({'expandedSha256': expanded} if expanded else {})))
for source in (W / 'authorize_template_retry_01.py', W / 'seal_template_retry_attempt_01.py',
               W.parent / 'session_01/authorize_template_retry_01.log',
               W.parent / 'session_01/authorize_template_retry_01_exit.json'):
    target = OUT / 'Continuation' / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(source.read_bytes())
    artifacts.append(dict(path=target.relative_to(OUT).as_posix(), sha256=sha(target), bytes=target.stat().st_size))
prep = E / 'AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26/manifest.json'
save(OUT / 'manifest.json', dict(schema='fraktal.ab.s4b-template-retry-attempt', schemaVersion=1, date='2026-10-26',
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(), report=REPORT.name, reportSha256=sha(REPORT),
    nativeAccepted=False, authorizationConsumed=True, currentControllerChangesAuthorized=False,
    approvalQuestion='call_378e7db52cb749e49ad59c696606376a:0', preparationManifestSha256=sha(prep),
    preparedAcdSha256=load(D / 'authorization.json')['CanonicalSha256'], sourceSha256=load(D / 'authorization.json')['SourceSha256'],
    templateDiscoveryPassed=True, candidateCases=0, baselineCases=31, genealogyRestored=True,
    originalHostDocumentsRestored=5, finalChecksPassed=True, dumpFiles=0, faultClears=0, clockChanges=0,
    powerOperations=0, hardKills=0, credentialFilesArchived=False, nativeAcdFilesArchived=False,
    committed=False, pushed=False, artifacts=artifacts))
for row in artifacts:
    assert sha(OUT / row['path']) == row['sha256']
    if row.get('expandedSha256'):
        assert hashlib.sha256(gzip.decompress((OUT / row['path']).read_bytes())).hexdigest() == row['expandedSha256']
save(W / 'sealed_template_retry_attempt_01.json', dict(passed=True, nativeAccepted=False, genealogyRestored=True,
    baselineCases=31, artifacts=len(artifacts), manifestSha256=sha(OUT / 'manifest.json'), authorizationConsumed=True))
print(json.dumps(dict(sealed=True, artifacts=len(artifacts), genealogyRestored=True, baselineCases=31, nativeAccepted=False)))
