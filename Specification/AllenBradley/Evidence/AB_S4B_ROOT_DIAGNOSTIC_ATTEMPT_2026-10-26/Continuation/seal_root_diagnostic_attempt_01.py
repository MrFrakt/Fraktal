"""Seal native root-age diagnosis, the failed baseline and its completion."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json

R = Path('C:/Users/SoftIndVM/Fraktal')
W = Path(__file__).parent
D = W.parent / 'retry_root_diagnostic_01'
E = R / 'Specification/AllenBradley/Evidence'
OUT = E / 'AB_S4B_ROOT_DIAGNOSTIC_ATTEMPT_2026-10-26'
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
first_baseline = load(D / 'baseline_regressions.json')
baseline = load(D / 'baseline_regressions_retry_01.json')
final = load(D / 'final_checks_retry_01.json')
dart = json.loads(gzip.decompress((D / 'dart_qualification.json.gz').read_bytes()))
inspection = load(D / 'diagnostic_inspection_01.json')
assert not session['passed'] and session['rollbackError'] and not session['genealogyRestored']
assert len(first_baseline['rows']) == 22 and not first_baseline['restored']
assert first_baseline['error'] == 'ready mode 2 timed out: step=0, error=0'
assert len(baseline['rows']) == 31 and all(row['passed'] for row in baseline['rows'])
assert baseline['restored'] and baseline['policyRestored']
assert final['passed'] and all(final['checks'].values()) and all(final['savedDocumentsEqual'].values())
assert load(D / 'rollback_cleanup_01.json')['passed']
assert not dart['passed'] and not dart['samples'] and not dart['configurationPages']
rejected = inspection['rejectedSnapshots'][0]
assert rejected['rootFailure']['reasons'] == ['cyclic sample age reached 1000 ms']
assert rejected['sampleAgeMs'] == 2065.752 and rejected['responseProcessingMs'] == 2495.609
assert rejected['statusCounts'] == {'0': 976}
assert rejected['rootFailure']['rootSamples']['Press']['identityValue'] == 'Press'
assert not (D / 'candidate_regressions.json').exists() and not (D / 'dart_ready.json').exists()
stages = {p.name.removesuffix('_exit.json'): load(p)['exitCode'] for p in D.glob('*_exit.json')}
failed = {'qualification_run_01', 'candidate_regressions', 'dart_observer', 'baseline_regressions', 'final_state_after_failure_01'}
assert all(code == (1 if name in failed else 0) for name, code in stages.items()), stages
bindings = load(D / 'source_bindings.json')
changed = [name for name, pin in bindings['sha256'].items() if sha(Path(name)).upper() != pin.upper()]
assert changed == [(D / 's4b_read_view.ACD').as_posix()], changed
assert not session['dumpFiles']
original = Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')
assert sha(original).upper() == 'D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
summary = dict(passed=False, nativeAccepted=False, serial='601FC87B', candidateCases=0,
    reason=dart['error'], firstSnapshotFastAgeMs=rejected['sampleAgeMs'], firstSnapshotProcessingMs=rejected['responseProcessingMs'],
    goodValues=976, badValues=0, uncertainValues=0, rootIdentityCorrect=True, templateDiscoveryPassed=True,
    maximumAcceptedRowWindowUs=rejected['maximumAcceptedWindowUs'], originalBaselineCasesPassed=22,
    baselineRetryCasesPassed=31, originalBaselineFailure=first_baseline['error'],
    originalRunnerRollbackVerified=False, continuationGenealogyRestored=True, originalDocumentsRestored=5,
    continuationFinalChecksPassed=True, policyRestored=True, stageExits=stages,
    approvalQuestion='call_0c97c2f8c5c84620bbb108165c7177cd:0', authorizationConsumed=True,
    currentControllerChangesAuthorized=False, dumpFiles=[], faultClears=0, clockChanges=0, powerOperations=0, hardKills=0)
save(D / 'runtime_summary_01.json', summary)
save(D / 'owner_authorization_consumed_01.json', dict(authorizationConsumed=True,
    currentControllerChangesAuthorized=False, originalScopeCompletedWithBaselineRetry=True,
    approvalQuestion=summary['approvalQuestion'], ownerInstruction='Approve guarded S4b root diagnostic session',
    authorizationSha256=sha(D / 'authorization.json'), originalSessionResultSha256=sha(D / 'session_result.json'),
    finalChecksSha256=sha(D / 'final_checks_retry_01.json')))
report = '''# S4b root-sample diagnostic attempt — 2026-10-26

**The refusal is diagnosed: the first snapshot's oldest fast row was 2,065.752 ms
old, above the unchanged 1,000 ms acceptance limit. Genealogy restoration and
31/31 baseline checks are verified after one unchanged baseline retry.**
S4b qualification failed; native and desktop acceptance remain open.

The owner answered “Approve guarded S4b root diagnostic session” to
`call_0c97c2f8c5c84620bbb108165c7177cd:0`, authorizing the
[sealed preparation](AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26.md).
The original approval included rollback cleanup and the 31 baseline vectors.
The runner's first failure record is retained unchanged; its incomplete cleanup
was finished within that original scope, without another download or new write
vectors. That scope is now complete and the approval is consumed.

## Native finding

Fresh guards/backup, exact-image download/Run, SDK, L5X read-back and access
audits pass on Echo 601FC87B (1756-L81E v38.011, 127.0.0.1 slot 0).
ACD `7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF`;
source `C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F`;
offline Capacity remains 65% (2,066,100 /3,145,728 Blocks).

The corrected Template and manifest discovery pass. The retained rejected
snapshot has the correct Press root identity and **976 Good values, zero Bad
and zero Uncertain**. Snapshot processing took **2,495.609 ms**; the oldest
fast row, Press/Status, was **2,065.752 ms** old at delivery. That row's accepted
coherence window was 1,909 us; the largest returned window was 6,387 us, below
the declared 10,000 us period. This is an age failure after sequential
acquisition, not a missing root or an identity mismatch. These samples are not
accepted qualification samples. The initial 1,000 ms refusal is preserved.

Readiness was never set, **0/41 candidate cases** ran, and no configuration
pages were read. Candidate equivalence, generic acquisition, candidate scan
and desktop rendering were not reached.

## Rollback and failed baseline

Pinned genealogy was downloaded from a hash-checked copy; the original remains
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
The SDK and external-access audits and original five-document restoration pass.
The first baseline run passed **22 cases**, then SFC adopted-fault setup timed
out waiting for HOME readiness (`step=0, error=0`). Its finally path left
MANUAL/policy restoration incomplete, and the original runner correctly records
rollback verification as false. The initial final-state check also failed and
is preserved; that state was idle, logged out and scanning, with documents equal.

Residual cleanup restored only fixture policy gate 10 and MANUAL through the
already approved LOGIN/SET_ACCESS_LEVEL/SET_MODE/LOGOUT scope. Final checks and
preflight then pass. One unchanged repeat of the original 31 baseline cases
passed **31/31**, restored policy, and was followed by MANUAL normalization,
final checks, preflight equality and baseline timing. No readiness condition or
fixture assertion was weakened. The first baseline timeout's cause is not
established by this successful retry.

The final controller is Run, not faulted, scanning, MANUAL/idle, logged out,
not restoring, with the original policy and all five saved/live documents equal.
No dumps, fault clears, clock changes, power/vendor-state operations or Echo
hard kills. No further controller-changing session is authorized.

## Offline investigation and next step

An unchanged-source recorded-byte replay with an immediate fake transport took
1,697.892 ms for its first acquisition and 1,596.195 ms for its second:
1,986 requests, 596 groups across the two reads, and 976 sampled values. This
reproduces substantial client cost without network delay; it is a profiling
observation, not a native timing guarantee or proof of one specific hotspot.
Inspect repeated path/count lookups and scheduling, preserve exact values/types
and all coherence/freshness limits, then rerun offline gates before preparing
another approved native qualification. No production correction has been made
at this seal. The bound sources remain unchanged except the SDK-saved working
ACD. Preparation gates remain 2,336 AB /74 root /637 Flutter (12 skipped).

S4b desktop, S5-S7 and S3 physical I/O acceptance remain open. V2/Part III are
inactive. Nothing is committed or pushed; no credentials or ACD binaries are
archived.
'''
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
    artifacts.append(dict(path=relative, sha256=sha(target), bytes=len(raw),
                          **({'expandedSha256': expanded} if expanded else {})))
for path in sorted(D.rglob('*')):
    if not path.is_file() or any(part in ('bin', 'obj', '__pycache__') for part in path.relative_to(D).parts):
        continue
    if path.suffix.lower() not in ('.py', '.json', '.gz', '.log', '.txt', '.sha256', '.l5x', '.cs', '.csproj'):
        continue
    assert 'credential' not in path.name.lower()
    archive(path, 'Runtime/' + path.relative_to(D).as_posix())
for name in ('authorize_root_diagnostic_01.py', 'inspect_root_diagnostic_01.py',
             'finish_root_diagnostic_cleanup_01.py', 'retry_root_diagnostic_baseline_01.py',
             'seal_root_diagnostic_attempt_01.py', 'schedule_profile_before_01.json'):
    archive(W / name, 'Continuation/' + name)
archive(W.parent / 'hmi_verify_01/test/cip_schedule_profile_probe.dart', 'Continuation/cip_schedule_profile_probe.dart')
for name in ('authorize_root_diagnostic_01.log', 'authorize_root_diagnostic_01_exit.json',
             'schedule_profile_before_01.log', 'schedule_profile_before_01_exit.json'):
    archive(W.parent / 'session_01' / name, 'Continuation/' + name)
prep = E / 'AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26/manifest.json'
save(OUT / 'manifest.json', dict(schema='fraktal.ab.s4b-root-diagnostic-attempt', schemaVersion=1,
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(), report=REPORT.name, reportSha256=sha(REPORT),
    preparationManifestSha256=sha(prep), nativeAccepted=False, candidateCases=0,
    firstBaselineCasesPassed=22, baselineRetryCasesPassed=31, genealogyRestored=True, finalChecksPassed=True,
    authorizationConsumed=True, currentControllerChangesAuthorized=False, rootIdentityCorrect=True,
    rootSampleAgeMs=2065.752, snapshotProcessingMs=2495.609, goodValues=976,
    dumpFiles=0, faultClears=0, clockChanges=0, powerOperations=0, hardKills=0,
    credentialFilesArchived=False, acdBinariesArchived=False, committed=False, pushed=False, artifacts=artifacts))
for row in artifacts:
    assert sha(OUT / row['path']) == row['sha256']
save(W / 'sealed_root_diagnostic_attempt_01.json', dict(passed=True, nativeAccepted=False,
    genealogyRestored=True, baselineRetryCases=31, firstBaselineCases=22,
    artifacts=len(artifacts), manifestSha256=sha(OUT / 'manifest.json')))
print(json.dumps(dict(sealed=True, artifacts=len(artifacts), genealogyRestored=True, baselineRetryCases=31)))
