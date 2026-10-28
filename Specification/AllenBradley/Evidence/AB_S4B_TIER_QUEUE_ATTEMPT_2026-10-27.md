# S4b tier/queue qualification — 2026-10-27

**Native acceptance: OPEN / not accepted. Genealogy is restored.**
The [sealed preparation](AB_S4B_TIER_QUEUE_PREPARATION_2026-10-27.md) was
approved: “Approve guarded S4b tier/queue retry”, question
`call_a6801bdef7184d1c95927b1b41c26fde:0`. The exact-session authorization is
consumed. No subsequent controller changes are authorized by this record.

## Target, scope and reader

- Echo **601FC87B**, 1756-L81E **v38.011**, **127.0.0.1 slot 0**.
- Prepared ACD `30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`.
- Generated source `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`.
- Same exact-image offline Capacity: **2,066,212 used /1,079,516 available /
  3,145,728 total Blocks (65%)**; not physical-controller fit evidence.
- **1078 bound inputs** verify. Only the SDK-saved
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

Diagnostic summary: `{"passed": true, "readOnly": true, "controllerAccess": false, "tracePresent": true, "calls": 4, "successfulCalls": 4, "failedCalls": 0, "attempts": 4, "equalEvenHeaderAttempts": 4, "failedCallRecords": [], "maxAttemptWindowUs": 2853, "medianAttemptWindowUs": 2139.0, "traceIncludesOverhead": true, "includesLiveAndHeldOracleReads": true, "causeIsolated": false, "interpretation": "Only recorded schema/revision equality/parity and timing are classified. No missing headers, payload integrity or host/publisher cause is inferred."}`.
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
and validation from later local work. The response-processing clock now starts at worker message receipt, so it
includes the serialized worker queue within the existing server-processing
bracket. The source/leaf age boundaries and frontend arithmetic are unchanged.
Primitive-array scheduling now uses the manifest-published logical leaf set
and its consumed members: excluded arrays are skipped and all-slow consumed
arrays follow the slow tier. Explicit targeted reads retain their original
proof. Snapshot values/types, row proofs, retries, deadlines, Good/expiry limits
and write policy remain unchanged.

The archived capture replay reduces reads from **990 to 810** and guarded groups
from **297 to 237**, removing **60** excluded profiler-array reads. All **976**
consumed values/types remain exactly equal to the pre-change replay and the
independent oracle. Those are replay counts, not native latency measurements.

Recorded stream/phase summary:
`{"observer": {"snapshots": 49, "deliveries": 49, "phases": {"queueUs": {"count": 49, "minimum": 5, "median": 8, "p95": 19, "maximum": 26}, "manifestBeforeUs": {"count": 49, "minimum": 1026, "median": 1575, "p95": 2421, "maximum": 3603}, "progressProofUs": {"count": 49, "minimum": 0, "median": 1, "p95": 2, "maximum": 11179}, "acquireUs": {"count": 49, "minimum": 215434, "median": 274647, "p95": 413025, "maximum": 445050}, "manifestAfterUs": {"count": 49, "minimum": 696, "median": 1019, "p95": 1324, "maximum": 1367}, "projectionUs": {"count": 49, "minimum": 1182, "median": 1645, "p95": 2855, "maximum": 4999}, "ageSelectionUs": {"count": 49, "minimum": 68, "median": 229, "p95": 535, "maximum": 572}, "pathExpansionUs": {"count": 49, "minimum": 6090, "median": 8042, "p95": 10770, "maximum": 12538}, "assemblyUs": {"count": 49, "minimum": 111, "median": 197, "p95": 706, "maximum": 1616}, "sendUs": {"count": 49, "minimum": 268, "median": 575, "p95": 1536, "maximum": 1644}}}, "desktop": {"snapshots": 0, "deliveries": 0, "phases": {"queueUs": null, "manifestBeforeUs": null, "progressProofUs": null, "acquireUs": null, "manifestAfterUs": null, "projectionUs": null, "ageSelectionUs": null, "pathExpansionUs": null, "assemblyUs": null, "sendUs": null}}}`.
Only measured intervals are summarized. They include instrumentation and
scheduling. Missing phase rows are not inferred successful, and a particular
host, network or PLC cause is not inferred from these aggregates. Slowest and
first snapshot rows are retained in `cip_timing_analysis_01.json`; the complete
observer/desktop stdout retains every recorded phase row.

## First failure and skipped stages

The candidate stops before any completed regression row at
`bounded login must be observed busy`. The accepted full comparison is exact
on **5,199 paths** and independently replays from raw reads. Both canonical and
legacy Access values show `LoginBusy=false`, `LoginFailed=true`,
`LoginResultSequence=1`, `CurrentLevel=0`: it sampled completed refusal rather
than the required transient busy state. It does not prove a missing PLC busy
publication. Request-to-capture duration was not measured, so the precise
timing cause is not claimed. `login_capture_analysis_01.json` preserves the
counter proof and safe flags. No credential/PIN is included.

The observer completes **49 entirely Good samples** and four configuration
queries. These short-run results do not establish full workload acceptance.
Strict desktop, independent configuration comparison, idle equivalence,
generic full acquisition and final candidate timing are **skipped**. The
read-only TASK trace is retained as an observation, not full scan acceptance.
The next offline step is a small same-scan canonical/legacy busy witness
immediately after acknowledgement, before the full comparison. The existing
full comparison, negative-login refusal and remaining fixture checks must stay.

## Actual results

| Gate | Recorded outcome |
|---|---|
| Candidate fixture | 0 passed; group counts in summary |
| Independent raw-record replay | 1 paired captures; 5199–5199 paths |
| Concurrent Dart observer | 49 samples; 49 entirely Good, 0 with Uncertain, 0 with Bad |
| Observer completion | PASS |
| Complete reader/configuration/acquisition | OPEN / not accepted |
| Configuration | 4 pages; None exact oracle values/types |
| Idle equivalence | 0 paths; OPEN / not accepted |
| Generic acquisition | 0 values /0 modules |
| Strict live desktop | OPEN / not accepted; 0 modules /0 bus nodes /0 views |
| Scan acceptance | OPEN / not accepted |
| Genealogy rollback | **31/31 baseline**, five original documents, all final checks/preflight |

Sample ages (ms): `{"minimum": 216.154, "median": 275.568, "p95": 413.967, "maximum": 438.839}`.
RPC duration (us): `{"minimum": 228394, "median": 291023, "p95": 428088, "maximum": 486153}`.
Accepted row windows (us): `{"minimum": 4282, "median": 5693, "p95": 8747, "maximum": 9109}`.
Observer error: `None`.
Independent configuration comparison uses the post-fixture oracle and published
ReadServices. It does not compare Dart results to themselves. Payload-free
refusals are not counted as Good. Missing later stages are skipped, not inferred
successful from previous attempts. Runtime summary and stage exits record the
actual boundaries reached.

## Desktop and TASK evidence

Final candidate timing was not reached. The candidate trace contains 505 valid observations; maximum recorded TASK value 7752 us, overlap count 0. First published probe sample 0, last 4390.
TASK scalars are polled read-only at nominal 100 ms; download read errors remain
in the trace. Polling and separately read scalars do not isolate an exact scan,
routine or host cause. No TASK counters are cleared.

Desktop uses the production factory/repository/UI and genuine source quality/
age, requires LIVE/nonempty/full semantic coverage at every capture, and has
independent parent validation of seven modules, three bus nodes and 31 views.
Refresh logs, forest transitions, stdout/stderr, screenshots and any refused
result are retained. Captured-fixture substitutions are disabled in live mode.
Desktop detail: `{"accepted": false, "modules": 0, "views": 0, "fieldbusNodes": 0, "error": null, "link": null, "localWriteRefusals": null, "fixtureClientWriteCalls": null, "nativeWireWriteCountMeasured": false}`.
Measured complete-sample refusal components, when present:
`{"passed": true, "readOnly": true, "controllerAccess": false, "observations": [], "refusalReproduced": false, "interpretation": "Exact measured arithmetic, not an isolated code/host cause. Missing observations are not inferred."}`.
No missing timing is estimated. No timestamp is renewed to obtain LIVE.
Candidate error: `CalledProcessError: Command '['C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-array-tiers-20261027\\session_01\\run_logged.py', 'candidate_regressions', 'C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-array-tiers-20261027\\session_01\\candidate_regressions_v2.py', '--execute-fixture', '--expect-serial', '601FC87B', '--credential-file', 'C:/work/fraktal_echo38_access_fixture.json', '--output', 'C:\\work\\fraktal-ab-s4b-array-tiers-20261027\\session_01\\candidate_regressions.json']' returned non-zero exit status 1.`.

## Restoration, gates and remaining work

Rollback downloads a hash-checked copy of genealogy
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`,
restores the five exact original host documents, runs **31/31 baseline cases**,
restores policy, MANUAL/idle/logout, saved/live equality and every final check/
preflight. Baseline scan: `{"lastScanMedianUs": 99.0, "cumulativeMaxUs": 1166, "overlaps": 0}`. The original ACD
is never opened. No dumps, fault/TASK-counter clears, clock changes, power/
vendor-state operations or Echo hard kills occur.

The preparation binds **665 HMI tests passed /12 skipped**, 53 trace-enabled
focused tests, analyzer, Windows build and enforced lockfile, using Flutter
**3.47.5 /Dart 3.13.4** and the identical 319-input mirror. Three existing HMI
source/test files change and one new array-tier test file is added. The five
new array cases pass; the archived old implementation fails four of them.
The freshness counterexample covers queue-plus-read processing without changing
source timestamps or quality limits. Six unchanged session-only Part trace tests
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
