"""Archive the actual desktop timing outcome after verified genealogy rollback."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json

R=Path('C:/Users/SoftIndVM/Fraktal')
W=Path(__file__).parent
S=W.parent/'session_01'
E=R/'Specification/AllenBradley/Evidence'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_bytes())
q=load(S/'runtime_summary_01.json')
assert q['genealogyRestored'] and q['baselineCases']==31 and q['finalChecksPassed']
assert q['authorizationConsumed'] and not q['currentControllerChangesAuthorized']
assert load(S/'authorization.json')['ApprovalQuestion']=='call_65010f20595041d78cea54b482b0f09f:0'
assert all(q[key]==0 for key in ('faultClears','taskCounterClears','clockChanges','powerOperations','hardKills'))
assert not q['dumpFiles']
stamp=datetime.datetime.now().astimezone().strftime('%Y-%m-%d')
kind='RUNTIME' if q['nativeAccepted'] else 'ATTEMPT'
name=f'AB_S4B_DESKTOP_TIMING_{kind}_{stamp}'
OUT=E/name
REPORT=OUT.with_suffix('.md')
assert not OUT.exists() and not REPORT.exists()
prep=E/'AB_S4B_DESKTOP_TIMING_PREPARATION_2026-10-27/manifest.json'
assert sha(prep)=='fed4a614842da063744c56dfa37c9bf029f84b716ba08265faa18f3a6ab4c03f'
def save(path,value):
    with path.open('x',encoding='utf-8',newline='') as f:
        json.dump(value,f,indent=2,ensure_ascii=False)
        f.write('\n')
def flag(value):return 'PASS' if value else 'OPEN / not accepted'
scan=q['candidateScan']
coverage=q['desktopCoverage']
age=q.get('sampleAgeMs')
window=q.get('maximumAcceptedRowWindowUs')
scan_text=(f"Median **{scan['lastScanMedianUs']:g} us**, cumulative maximum **{scan['cumulativeMaxUs']} us**, "
    f"**{scan['overlaps']} overlaps** on the 10,000 us task.") if scan else 'Final candidate timing was not reached.'
first=q.get('candidateTraceEpoch')
trace_text=(f"The candidate trace contains {first['rows']} valid observations; maximum recorded TASK value "
    f"{first['maxTaskScanUs']} us, overlap count {first['maxOverlapCount']}. "
    f"First published probe sample {first['first']['values']['Samples']}, last {first['last']['values']['Samples']}.") if first else 'No complete candidate trace epoch is available.'
report=f'''# S4b desktop phase-timing qualification — {stamp}

**Native acceptance: {flag(q['nativeAccepted'])}. Genealogy is restored.**
The [sealed preparation](AB_S4B_DESKTOP_TIMING_PREPARATION_2026-10-27.md) was
approved: “Approve guarded S4b desktop timing session”, question
`call_65010f20595041d78cea54b482b0f09f:0`. The exact-session authorization is
consumed. No subsequent controller changes are authorized by this record.

## Target, scope and reader

- Echo **601FC87B**, 1756-L81E **v38.011**, **127.0.0.1 slot 0**.
- Prepared ACD `{q['canonicalSha256']}`.
- Generated source `{q['sourceSha256']}`.
- Same exact-image offline Capacity: **2,066,212 used /1,079,516 available /
  3,145,728 total Blocks (65%)**; not physical-controller fit evidence.
- **{q['sourceBindingsVerified']} bound inputs** verify. Only the SDK-saved
  working ACD differs after execution; the original prepared image and pinned
  genealogy ACD remain unchanged.

The production generic client opens four read-only CIP connections, all pinned
to the first verified controller serial. A complete row retains one connection
through pre-counter, dependency counts, body/fragments and post-counter, with
one request outstanding per socket. Full walks use bounded cohorts of four and
count barriers; targeted reads stay serial. Publication revisions order count
and progress observations; older parallel replies cannot renew progress.
Conflicting same-revision counts, counter restart or transport failure abort
the pool and require rediscovery. All source/leaf ages, complete-sample age,
fast 1/3-second and slow 7.5/15-second Good/expiry limits, 20-attempt/one-second
row budget, proof windows and read-only policy remain unchanged.

The approved writer scope is the inherited 41 cases with exact restoration.
No new PLC write vectors are introduced by the reader. TASK monitoring starts
before download. Strict live desktop and remaining comparisons/acquisition/
timing follow the fixture only if preceding stages pass. Candidate work stops
at its first failure; rollback retains fault/identity/idle/session guards.

## Session-only Part-read diagnostic

The original legacy Part reader, its requests, three-attempt default, projection
and even-revision acceptance rule are unchanged. The session wraps its Read
calls only to retain schema/revision words, before/body/after phase, attempt and
timing. No Part payload/UID or PIN is recorded. It forwards requests exactly
once and preserves the original return value or refusal. The original function
is restored on context exit. Trace work adds overhead; recorded timings include
that work. No new PLC reads/writes, retry or acceptance rule is introduced.

Diagnostic summary: `{json.dumps({k:v for k,v in (q.get('partReadDiagnostics') or {}).items() if k!='rows'},ensure_ascii=False)}`.
Only actually recorded header equality/parity and timing are classified. Missing
headers, payload integrity, contention or a particular host/publisher cause are
not inferred. A successful diagnostic acquisition is not proof of why an earlier
unrecorded acquisition refused. Raw JSONL and the independent analysis are
archived. The preparation's six tracing tests preserve original call counts,
arguments, attempt budget, exact return/error and payload exclusion.

## Worker and frontend timing evidence

Qualification launchers enable `fraktal.cip.trace=true`; normal builds keep
worker tracing disabled. Completed snapshots record worker queue, manifest/
progress checks, acquisition, projection, age selection, path expansion,
assembly/trace preparation and SendPort delivery. The eight slowest guarded
groups retain paths, quality, attempts and elapsed times, without PLC values.
The existing frontend rejection log separates snapshot wait, service decoding
and validation from later local work. The original response age bracket and
age arithmetic remain in their original positions. No reads, snapshot values,
proofs, retries, deadlines, freshness limits or write policy change.

Recorded stream/phase summary:
`{json.dumps({name:{'snapshots':data['snapshots'],'deliveries':data['deliveries'],'phases':data['phases']} for name,data in (q.get('cipPhaseTiming') or {}).get('streams',{}).items()},ensure_ascii=False)}`.
Only measured intervals are summarized. They include instrumentation and
scheduling. Missing phase rows are not inferred successful, and a particular
host, network or PLC cause is not inferred from these aggregates. Slowest and
first snapshot rows are retained in `cip_timing_analysis_01.json`; the complete
observer/desktop stdout retains every recorded phase row.

## Actual results

| Gate | Recorded outcome |
|---|---|
| Candidate fixture | {q['candidateCases']} passed; group counts in summary |
| Independent raw-record replay | {q['pairedCapturesReplayed']} paired captures; {q['pairedMinimumPaths']}–{q['pairedMaximumPaths']} paths |
| Concurrent Dart observer | {q['observerSamples']} samples; {q['allGoodSamples']} entirely Good, {q['samplesWithUncertainRows']} with Uncertain, {q['samplesWithBadRows']} with Bad |
| Observer completion | {flag(q['observerPassed'])} |
| Complete reader/configuration/acquisition | {flag(q['nativeReaderPassed'])} |
| Configuration | {q['configurationPages']} pages; {q['configurationScalarComparisons']} exact oracle values/types |
| Idle equivalence | {q['idlePaths']} paths; {flag(q['idlePassed'])} |
| Generic acquisition | {q['genericValues']} values /{q['genericModules']} modules |
| Strict live desktop | {flag(q['desktopAccepted'])}; {coverage['modules']} modules /{coverage['fieldbusNodes']} bus nodes /{coverage['views']} views |
| Scan acceptance | {flag(q['scanReviewPassed'])} |
| Genealogy rollback | **31/31 baseline**, five original documents, all final checks/preflight |

Sample ages (ms): `{json.dumps(age)}`.
RPC duration (us): `{json.dumps(q.get('rpcUs'))}`.
Accepted row windows (us): `{json.dumps(window)}`.
Observer error: `{q['observerError']}`.
Independent configuration comparison uses the post-fixture oracle and published
ReadServices. It does not compare Dart results to themselves. Payload-free
refusals are not counted as Good. Missing later stages are skipped, not inferred
successful from previous attempts. Runtime summary and stage exits record the
actual boundaries reached.

## Desktop and TASK evidence

{scan_text} {trace_text}
TASK scalars are polled read-only at nominal 100 ms; download read errors remain
in the trace. Polling and separately read scalars do not isolate an exact scan,
routine or host cause. No TASK counters are cleared.

Desktop uses the production factory/repository/UI and genuine source quality/
age, requires LIVE/nonempty/full semantic coverage at every capture, and has
independent parent validation of seven modules, three bus nodes and 31 views.
Refresh logs, forest transitions, stdout/stderr, screenshots and any refused
result are retained. Captured-fixture substitutions are disabled in live mode.
Desktop detail: `{json.dumps(coverage,ensure_ascii=False)}`.
Measured complete-sample refusal components, when present:
`{json.dumps(q.get('desktopFreshnessDiagnostics'),ensure_ascii=False)}`.
No missing timing is estimated. No timestamp is renewed to obtain LIVE.
Candidate error: `{q['sessionCandidateError']}`.

## Restoration, gates and remaining work

Rollback downloads a hash-checked copy of genealogy
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`,
restores the five exact original host documents, runs **31/31 baseline cases**,
restores policy, MANUAL/idle/logout, saved/live equality and every final check/
preflight. Baseline scan: `{json.dumps(q['baselineScan'])}`. The original ACD
is never opened. No dumps, fault/TASK-counter clears, clock changes, power/
vendor-state operations or Echo hard kills occur.

The preparation binds **660 HMI tests passed /12 skipped**, 40 trace-enabled
focused tests, analyzer, Windows build and enforced lockfile, using Flutter
**3.47.5 /Dart 3.13.4** and the identical 318-input mirror. Three existing HMI
source/test files add diagnostics. Six unchanged session-only Part trace tests
pass. All **373 PLC/gate bindings** remain unchanged: **2,339 AB tests**, both
v38 build/read-back/access/SDK gates, 15 byte-identical prior images and exact
65% Capacity transfer by hashes. **74 root tests** and spec/contracts/strict
consistency/whitespace pass. Runtime execution changes no shipping source.
The prepared SDK and negative authorization/workflow/readiness gates are
recorded in the preparation. Credentials and ACD/SDK binaries are excluded
from this archive; their approved inputs are hash-bound.

S4 acceptance is limited to the results above. S5 gateway/Web/installer, S6
classified legacy migration/retirement/persistence/events/capacity and S7
physical/CIP Security including real I/O remain. Persistence, per-station
gateway write posture, physical hardware and commit/push policy still require
owner decisions. V2/Part III remain inactive. Nothing is committed or pushed.
'''

with REPORT.open('x',encoding='utf-8',newline='') as f:f.write(report)
artifacts=[]
def archive(path,relative):
    assert 'credential' not in path.name.lower(),str(path)
    raw=path.read_bytes()
    expanded=None
    if path.suffix.lower() in ('.log','.l5x','.jsonl'):
        expanded=hashlib.sha256(raw).hexdigest()
        raw=gzip.compress(raw,mtime=0)
        relative+='.gz'
    target=OUT/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(raw)
    artifacts.append(dict(path=relative,bytes=len(raw),sha256=sha(target),
        **(dict(expandedSha256=expanded) if expanded else {})))
for path in sorted(S.rglob('*')):
    if not path.is_file() or any(part in ('bin','obj','__pycache__') for part in path.relative_to(S).parts):continue
    if path.suffix.lower() not in ('.py','.json','.gz','.log','.txt','.sha256','.l5x','.cs','.csproj','.dart','.png','.jsonl'):continue
    archive(path,'Runtime/'+path.relative_to(S).as_posix())
for name in ('authorize_timing_session_01.py','prepare_runtime_analysis_01.py','inspect_cold_runtime_01.py',
    'replay_pairs_01.py','compare_cold_config_pages_01.py','analyze_cold_task_trace_01.py',
    'peek_runtime_progress_01.py','summarize_runtime_01.py','seal_runtime_01.py',
    'prepare_runtime_seal_01.py','parse_startup_timing_01.py','analyze_cip_timing_01.py','analyze_part_reads_01.py','part_read_diagnostics.py','test_part_read_diagnostics.py',
    'authorize_timing_session_01.log','authorize_timing_session_01_exit.json','echo_guard_approved_01.log',
    'echo_guard_approved_01_exit.json'):
    archive(W/name,'Analysis/'+name)
save(OUT/'manifest.json',dict(schema='fraktal.ab.s4b-desktop-timing-runtime',schemaVersion=1,
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
    preparationManifestSha256=sha(prep),nativeAccepted=q['nativeAccepted'],nativeReaderPassed=q['nativeReaderPassed'],
    desktopAccepted=q['desktopAccepted'],scanReviewPassed=q['scanReviewPassed'],candidateCases=q['candidateCases'],
    pairedCapturesReplayed=q['pairedCapturesReplayed'],observerSamples=q['observerSamples'],baselineCases=31,
    genealogyRestored=True,finalChecksPassed=True,authorizationConsumed=True,currentControllerChangesAuthorized=False,
    credentialFilesArchived=False,acdBinariesArchived=False,sdkBinariesArchived=False,artifacts=artifacts,
    committed=False,pushed=False))
for row in artifacts:assert sha(OUT/row['path'])==row['sha256']
save(W/'sealed_runtime_01.json',dict(passed=True,report=REPORT.as_posix(),manifestSha256=sha(OUT/'manifest.json'),
    artifacts=len(artifacts),nativeAccepted=q['nativeAccepted'],nativeReaderPassed=q['nativeReaderPassed'],
    desktopAccepted=q['desktopAccepted'],scanReviewPassed=q['scanReviewPassed'],genealogyRestored=True))
print(json.dumps(dict(sealed=True,report=REPORT.name,artifacts=len(artifacts),nativeAccepted=q['nativeAccepted'],
    desktopAccepted=q['desktopAccepted'],scanReviewPassed=q['scanReviewPassed'],genealogyRestored=True)))
