# S4b desktop phase-timing qualification — 2026-10-27

**Native acceptance: OPEN / not accepted. Genealogy is restored.**
The [sealed preparation](AB_S4B_DESKTOP_TIMING_PREPARATION_2026-10-27.md) was
approved: “Approve guarded S4b desktop timing session”, question
`call_65010f20595041d78cea54b482b0f09f:0`. The exact-session authorization is
consumed. No subsequent controller changes are authorized by this record.

## Target, scope and reader

- Echo **601FC87B**, 1756-L81E **v38.011**, **127.0.0.1 slot 0**.
- Prepared ACD `30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`.
- Generated source `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`.
- Same exact-image offline Capacity: **2,066,212 used /1,079,516 available /
  3,145,728 total Blocks (65%)**; not physical-controller fit evidence.
- **1076 bound inputs** verify. Only the SDK-saved
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

Diagnostic summary: `{"passed": true, "readOnly": true, "controllerAccess": false, "tracePresent": true, "calls": 218, "successfulCalls": 218, "failedCalls": 0, "attempts": 223, "equalEvenHeaderAttempts": 218, "failedCallRecords": [], "maxAttemptWindowUs": 10430, "medianAttemptWindowUs": 1548, "traceIncludesOverhead": true, "includesLiveAndHeldOracleReads": true, "causeIsolated": false, "interpretation": "Only recorded schema/revision equality/parity and timing are classified. No missing headers, payload integrity or host/publisher cause is inferred."}`.
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
`{"observer": {"snapshots": 2035, "deliveries": 2035, "phases": {"queueUs": {"count": 2035, "minimum": 2, "median": 5, "p95": 11, "maximum": 104}, "manifestBeforeUs": {"count": 2035, "minimum": 578, "median": 1104, "p95": 1635, "maximum": 12126}, "progressProofUs": {"count": 2035, "minimum": 0, "median": 1, "p95": 1, "maximum": 7585}, "acquireUs": {"count": 2035, "minimum": 237314, "median": 308870, "p95": 373272, "maximum": 1580933}, "manifestAfterUs": {"count": 2035, "minimum": 546, "median": 934, "p95": 1170, "maximum": 17033}, "projectionUs": {"count": 2035, "minimum": 1100, "median": 1405, "p95": 2074, "maximum": 7002}, "ageSelectionUs": {"count": 2035, "minimum": 32, "median": 160, "p95": 397, "maximum": 3338}, "pathExpansionUs": {"count": 2035, "minimum": 5367, "median": 6493, "p95": 7921, "maximum": 32768}, "assemblyUs": {"count": 2035, "minimum": 103, "median": 167, "p95": 318, "maximum": 1667}, "sendUs": {"count": 2035, "minimum": 202, "median": 404, "p95": 868, "maximum": 3520}}}, "desktop": {"snapshots": 2, "deliveries": 2, "phases": {"queueUs": {"count": 2, "minimum": 8, "median": 25456.0, "p95": 50904, "maximum": 50904}, "manifestBeforeUs": {"count": 2, "minimum": 2245, "median": 2283.5, "p95": 2322, "maximum": 2322}, "progressProofUs": {"count": 2, "minimum": 9, "median": 10114.5, "p95": 20220, "maximum": 20220}, "acquireUs": {"count": 2, "minimum": 505457, "median": 689506.5, "p95": 873556, "maximum": 873556}, "manifestAfterUs": {"count": 2, "minimum": 1199, "median": 2240.0, "p95": 3281, "maximum": 3281}, "projectionUs": {"count": 2, "minimum": 4118, "median": 7526.0, "p95": 10934, "maximum": 10934}, "ageSelectionUs": {"count": 2, "minimum": 270, "median": 769.0, "p95": 1268, "maximum": 1268}, "pathExpansionUs": {"count": 2, "minimum": 18689, "median": 19985.5, "p95": 21282, "maximum": 21282}, "assemblyUs": {"count": 2, "minimum": 1157, "median": 2281.0, "p95": 3405, "maximum": 3405}, "sendUs": {"count": 2, "minimum": 327, "median": 747.0, "p95": 1167, "maximum": 1167}}}}`.
Only measured intervals are summarized. They include instrumentation and
scheduling. Missing phase rows are not inferred successful, and a particular
host, network or PLC cause is not inferred from these aggregates. Slowest and
first snapshot rows are retained in `cip_timing_analysis_01.json`; the complete
observer/desktop stdout retains every recorded phase row.

## Actual results

| Gate | Recorded outcome |
|---|---|
| Candidate fixture | 41 passed; group counts in summary |
| Independent raw-record replay | 87 paired captures; 4799–5407 paths |
| Concurrent Dart observer | 2035 samples; 2033 entirely Good, 2 with Uncertain, 0 with Bad |
| Observer completion | PASS |
| Complete reader/configuration/acquisition | OPEN / not accepted |
| Configuration | 4 pages; None exact oracle values/types |
| Idle equivalence | 0 paths; OPEN / not accepted |
| Generic acquisition | 0 values /0 modules |
| Strict live desktop | OPEN / not accepted; 0 modules /0 bus nodes /0 views |
| Scan acceptance | OPEN / not accepted |
| Genealogy rollback | **31/31 baseline**, five original documents, all final checks/preflight |

Sample ages (ms): `{"minimum": 238.259, "median": 309.58, "p95": 373.504, "maximum": 997.151}`.
RPC duration (us): `{"minimum": 249499, "median": 320331, "p95": 384484, "maximum": 1593921}`.
Accepted row windows (us): `{"minimum": 3157, "median": 5644, "p95": 8040, "maximum": 9959}`.
Observer error: `None`.
Independent configuration comparison uses the post-fixture oracle and published
ReadServices. It does not compare Dart results to themselves. Payload-free
refusals are not counted as Good. Missing later stages are skipped, not inferred
successful from previous attempts. Runtime summary and stage exits record the
actual boundaries reached.

## Desktop and TASK evidence

Final candidate timing was not reached. The candidate trace contains 7011 valid observations; maximum recorded TASK value 8937 us, overlap count 0. First published probe sample 0, last 70277.
TASK scalars are polled read-only at nominal 100 ms; download read errors remain
in the trace. Polling and separately read scalars do not isolate an exact scan,
routine or host cause. No TASK counters are cleared.

Desktop uses the production factory/repository/UI and genuine source quality/
age, requires LIVE/nonempty/full semantic coverage at every capture, and has
independent parent validation of seven modules, three bus nodes and 31 views.
Refresh logs, forest transitions, stdout/stderr, screenshots and any refused
result are retained. Captured-fixture substitutions are disabled in live mode.
Desktop detail: `{"accepted": false, "modules": 0, "views": 0, "fieldbusNodes": 0, "error": "Expected: LinkState:<LinkState.live>\n  Actual: LinkState:<LinkState.stale>\nafter-overview\n", "link": "stale", "localWriteRefusals": 2, "fixtureClientWriteCalls": null, "nativeWireWriteCountMeasured": false}`.
Measured complete-sample refusal components, when present:
`{"passed": true, "readOnly": true, "controllerAccess": false, "observations": [{"sourceAgeUs": 874812, "rpcUs": 1170250, "transitUs": 292080, "receivedAgeUs": 1166892, "localProcessingUs": 2391, "effectiveAgeUs": 1169283, "fastGoodUs": 1000000, "snapshotAwaitUs": 1170224, "serviceDecodeUs": 6, "validationUs": 1, "responseProcessingMs": 879.17, "excessUs": 169283, "sourceAlreadyLate": false, "lateAtReceipt": true, "localProcessingCrossedBoundary": false}], "refusalReproduced": true, "interpretation": "Exact measured arithmetic, not an isolated code/host cause. Missing observations are not inferred."}`.
No missing timing is estimated. No timestamp is renewed to obtain LIVE.
Candidate error: `CalledProcessError: Command '['C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-timing-20261027\\session_01\\run_logged.py', 'desktop_readonly', 'C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-timing-20261027\\session_01\\desktop_readonly.py']' returned non-zero exit status 1.`.

## Restoration, gates and remaining work

Rollback downloads a hash-checked copy of genealogy
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`,
restores the five exact original host documents, runs **31/31 baseline cases**,
restores policy, MANUAL/idle/logout, saved/live equality and every final check/
preflight. Baseline scan: `{"lastScanMedianUs": 99.0, "cumulativeMaxUs": 1166, "overlaps": 0}`. The original ACD
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
