"""Seal the lookup retry, successful PLC cases and failed Dart observation."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json
import statistics

R = Path('C:/Users/SoftIndVM/Fraktal')
W = Path(__file__).parent
D = W.parent / 'retry_lookup_01'
E = R / 'Specification/AllenBradley/Evidence'
OUT = E / 'AB_S4B_LOOKUP_RETRY_ATTEMPT_2026-10-26'
REPORT = OUT.with_suffix('.md')
load = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

assert not OUT.exists() and not REPORT.exists()
session = load(D / 'session_result.json')
cases = load(D / 'candidate_regressions.json')
baseline = load(D / 'baseline_regressions.json')
final = load(D / 'final_checks.json')
replay = load(D / 'paired_replay_01.json')
dart = json.loads(gzip.decompress((D / 'dart_qualification.json.gz').read_bytes()))
inspection = load(D / 'runtime_inspection_01.json')
assert not session['passed'] and session['genealogyRestored'] and session['rollbackError'] is None
assert session['authorizationConsumed'] and not session['dumpFiles']
for key, count in (('rows', 31), ('s4bAccessRows', 2), ('s4bConfigRows', 8)):
    assert len(cases[key]) == count and all(row['passed'] for row in cases[key])
assert cases['restored'] and cases['policyRestored'] and cases['s3fSetMediumEmpty']
assert len(baseline['rows']) == 31 and all(row['passed'] for row in baseline['rows'])
assert baseline['restored'] and baseline['policyRestored']
assert final['passed'] and all(final['checks'].values()) and all(final['savedDocumentsEqual'].values())
assert replay['passed'] and replay['pairs'] == 87 and replay['minimumPaths'] == 4799 and replay['maximumPaths'] == 5407
assert not dart['passed'] and len(dart['samples']) == 140 and not dart['configurationPages']
assert dart['error'] == 'FormatException: Fresh canonical root sample is unavailable: missing or different root identity: Press.'
rejected = next(s for s in dart['snapshots'] if s.get('qualificationRejectedRootSample'))
root = rejected['rootSampleFailure']['rootSamples']['Press']
assert root['identityValue'] is None
assert root['identityDataValue']['status'] == 0x40000000 and root['identityDataValue']['reason'] == 'coherence-unavailable'
assert rejected['sampleAgeMs'] < 1000
stages = {p.name.removesuffix('_exit.json'): load(p)['exitCode'] for p in D.glob('*_exit.json')}
failed = {'qualification_run_01', 'candidate_regressions', 'dart_observer'}
assert all(code == (1 if name in failed else 0) for name, code in stages.items()), stages
changed = [name for name, pin in load(D / 'source_bindings.json')['sha256'].items() if sha(Path(name)).upper() != pin.upper()]
assert changed == [(D / 's4b_read_view.ACD').as_posix()], changed
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')).upper() == 'D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
timing = [row['values'] for row in load(D / 'baseline_timing.json')['samples']]
summary = dict(passed=False, nativeAccepted=False, serial='601FC87B', candidateCases=41,
    candidateCasesPassed=True, candidateWritesRestored=True, pairedCapturesReplayed=87,
    minimumPairedPaths=4799, maximumPairedPaths=5407, observerPassed=False,
    observerError=dart['error'], observerSamples=140, configurationPages=0,
    sampleAgeMs=inspection['sampleAgeMs'], rpcUs=inspection['rpcUs'],
    maximumAcceptedRowWindowUs=inspection['maximumAcceptedRowWindowUs'], rootRefusal=root,
    exactFailedAttemptCountersRecorded=False, baselineCases=31, genealogyRestored=True,
    finalChecksPassed=True, originalDocumentsRestored=5, stageExits=stages,
    baselineScanMedianUs=statistics.median(row['FRK_Press_HealthProbe.TaskLastScanUs'] for row in timing),
    baselineScanCumulativeMaxUs=max(row['FRK_Press_HealthProbe.TaskMaxScanUs'] for row in timing),
    baselineOverlaps=max(row['FRK_Press_HealthProbe.TaskOverlapCount'] for row in timing),
    authorizationConsumed=True, currentControllerChangesAuthorized=False,
    dumpFiles=[], faultClears=0, clockChanges=0, powerOperations=0, hardKills=0)
save(D / 'runtime_summary_01.json', summary)
save(D / 'owner_authorization_consumed_01.json', dict(authorizationConsumed=True,
    currentControllerChangesAuthorized=False, approvalQuestion='call_2b13d9faea7945c9803fd0d2782b3c10:0',
    ownerInstruction='Approve guarded S4b lookup retry', authorizationSha256=sha(D / 'authorization.json'),
    sessionResultSha256=sha(D / 'session_result.json')))
report = '''# S4b lookup retry attempt — 2026-10-26

**All 41 candidate cases and 87 paired comparisons pass; Dart qualification
fails after 140 snapshots on a root-row coherence refusal. Genealogy and all
31 baseline/final checks are restored. Native S4b/desktop acceptance remain open.**

The owner answered “Approve guarded S4b lookup retry” to
`call_2b13d9faea7945c9803fd0d2782b3c10:0`, authorizing the
[sealed lookup retry](AB_S4B_LOOKUP_RETRY_PREPARATION_2026-10-26.md).
Its scope completed with verified rollback and the approval is consumed.

## Passed

- Fresh identity/service/listener, MANUAL/idle/logout/document guards, backup,
  SDK audits, download/Run, L5X read-back and external-access audits pass on
  Echo 601FC87B, 1756-L81E v38.011, 127.0.0.1 slot 0.
- Image `7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF`,
  source `C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F`.
  Offline Capacity is unchanged at 65% (2,066,100 /3,145,728 Blocks).
- Dart passed discovery and readiness. Its 140 completed snapshots had fast
  sample age median **621.756 ms**, p95 **656.818 ms**, maximum **745.063 ms**.
  RPC median/p95/max were 633.216 /668.344 /795.073 ms. The largest accepted
  returned row window was **8,455 us**, below the declared 10,000 us interval.
  There were no Bad values in the completed samples. Fifty-nine samples
  contained payload-free Uncertain rows; those rows are not counted as Good.
- **41/41 candidate cases**: 31 main, two Access and eight configuration/store.
  Changes and policy were restored; the isolated set store was left empty.
  **87/87 paired comparisons** replay independently from saved native record
  bytes to the same canonical values/types and stored oracle. Logical occupied
  counts yield **4,799–5,407 paths** across these captures. This includes the
  PLC-owned configuration view; it does not establish Dart page acceptance.
- Pinned genealogy downloaded from a hash-checked copy; the original remains
  `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
  Exact original five host documents, **31/31 baseline cases**, policy,
  MANUAL cleanup, final checks, preflight and baseline timing pass.
- Final state: Run, not faulted, scanning, MANUAL/idle, logged out, not restoring,
  original policy and all five saved/live documents equal. No dumps, fault
  clears, clock changes, power/vendor-state operations or Echo hard kills.

## Failed and skipped

At the next snapshot the root Status row was Uncertain with reason
`coherence-unavailable` and no payload. Its prior sampled identity was
1,230.022 ms old; no value was retained as Good. Other Good fast samples were
603.998 ms old. The observer stopped with “missing or different root identity:
Press”. This differs from the previous whole-acquisition age failure: the
lookup correction allowed 140 snapshots to meet the original 1,000 ms limit.

The guard exhausts at most three attempts within one second. The rejected
DataValue preserves the prior successful row's timing fields, not the failed
attempt trace. The record therefore cannot distinguish odd pre-counters,
changing counters or overlong windows for this particular refusal. Do not
claim an exact retry-phase cause from these data.

The observer stopped first; the separate inherited fixture completed its
approved cases/restoration before the wrapper collected the observer failure
and entered rollback. This is not a passing concurrent-observation result.
Dart all-bank configuration pages, detail reads, candidate idle equivalence,
generic acquisition and candidate native scan were not reached. Desktop
rendering/connection acceptance remains open.

## Next

Reproduce the bounded retry behavior with a publishing counter that completes
on a later scheduling turn, retain useful failed-attempt diagnostics, and fix
any demonstrated retry starvation without increasing attempt/deadline budgets
or accepting torn/stale payloads. The exact native attempt pattern remains
unrecorded; a later native retry must confirm the correction. Every bound
source remains unchanged at this seal except the SDK-saved deployment ACD.
Offline 2,336 AB /74 root /638 Flutter tests (12 skipped), Windows build,
analyzer, both v38 builds and 65% Capacity remain preparation results.

V2/Part III are inactive. S4b desktop, S5-S7 and S3 physical I/O proof remain.
Nothing is committed or pushed; credentials and ACD binaries are not archived.
'''
assert sum(row['uncertain'] > 0 for row in dart['samples']) == 59
with REPORT.open('x', encoding='utf-8') as stream:
    stream.write(report)
artifacts = []
def archive(source, relative):
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
    artifacts.append(dict(path=relative, bytes=len(raw), sha256=sha(target),
                          **({'expandedSha256': expanded} if expanded else {})))
for path in sorted(D.rglob('*')):
    if not path.is_file() or any(part in ('bin', 'obj', '__pycache__') for part in path.relative_to(D).parts):
        continue
    if path.suffix.lower() not in ('.py', '.json', '.gz', '.log', '.txt', '.sha256', '.l5x', '.cs', '.csproj'):
        continue
    assert 'credential' not in path.name.lower()
    archive(path, 'Runtime/' + path.relative_to(D).as_posix())
for name in ('authorize_lookup_retry_01.py', 'inspect_lookup_runtime_01.py', 'lookup_fixture_progress_01.py',
             'replay_lookup_pairs_01.py', 'seal_lookup_attempt_01.py'):
    archive(W / name, 'Continuation/' + name)
for name in ('authorize_lookup_retry_01.log', 'authorize_lookup_retry_01_exit.json'):
    archive(W.parent / 'session_01' / name, 'Continuation/' + name)
save(OUT / 'manifest.json', dict(schema='fraktal.ab.s4b-lookup-retry-attempt', schemaVersion=1,
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(), report=REPORT.name, reportSha256=sha(REPORT),
    preparationManifestSha256=sha(E / 'AB_S4B_LOOKUP_RETRY_PREPARATION_2026-10-26/manifest.json'),
    nativeAccepted=False, candidateCases=41, pairedCapturesReplayed=87, observerSamples=140,
    observerPassed=False, baselineCases=31, genealogyRestored=True, finalChecksPassed=True,
    authorizationConsumed=True, currentControllerChangesAuthorized=False, dumpFiles=0, faultClears=0,
    clockChanges=0, powerOperations=0, hardKills=0, credentialFilesArchived=False,
    acdBinariesArchived=False, committed=False, pushed=False, artifacts=artifacts))
for row in artifacts:
    assert sha(OUT / row['path']) == row['sha256']
save(W / 'sealed_lookup_attempt_01.json', dict(passed=True, nativeAccepted=False, genealogyRestored=True,
    candidateCases=41, baselineCases=31, pairs=87, observerSamples=140, artifacts=len(artifacts),
    manifestSha256=sha(OUT / 'manifest.json')))
print(json.dumps(dict(sealed=True, artifacts=len(artifacts), candidateCases=41, pairs=87,
    genealogyRestored=True, baselineCases=31, nativeAccepted=False)))
