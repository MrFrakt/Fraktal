# S4b legacy Part-read diagnostic qualification — 2026-10-27

**Native acceptance: OPEN / not accepted. Genealogy is restored.**
The [sealed preparation](AB_S4B_PART_READ_DIAGNOSTIC_PREPARATION_2026-10-27.md) was
approved: “Approve guarded S4b Part-read diagnostic session”, question
`call_438cc23f4aa04d9cbddadf9fd71508b4:0`. The exact-session authorization is
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

Diagnostic summary: `{"passed": true, "readOnly": true, "controllerAccess": false, "tracePresent": true, "calls": 218, "successfulCalls": 218, "failedCalls": 0, "attempts": 229, "equalEvenHeaderAttempts": 218, "failedCallRecords": [], "maxAttemptWindowUs": 10732, "medianAttemptWindowUs": 1594, "traceIncludesOverhead": true, "includesLiveAndHeldOracleReads": true, "causeIsolated": false, "interpretation": "Only recorded schema/revision equality/parity and timing are classified. No missing headers, payload integrity or host/publisher cause is inferred."}`.
Only actually recorded header equality/parity and timing are classified. Missing
headers, payload integrity, contention or a particular host/publisher cause are
not inferred. A successful diagnostic acquisition is not proof of why an earlier
unrecorded acquisition refused. Raw JSONL and the independent analysis are
archived. The preparation's six tracing tests preserve original call counts,
arguments, attempt budget, exact return/error and payload exclusion.

## Actual results

| Gate | Recorded outcome |
|---|---|
| Candidate fixture | 41 passed; group counts in summary |
| Independent raw-record replay | 87 paired captures; 4799–5407 paths |
| Concurrent Dart observer | 1991 samples; 1991 entirely Good, 0 with Uncertain, 0 with Bad |
| Observer completion | PASS |
| Complete reader/configuration/acquisition | OPEN / not accepted |
| Configuration | 4 pages; None exact oracle values/types |
| Idle equivalence | 0 paths; OPEN / not accepted |
| Generic acquisition | 0 values /0 modules |
| Strict live desktop | OPEN / not accepted; 0 modules /0 bus nodes /0 views |
| Scan acceptance | OPEN / not accepted |
| Genealogy rollback | **31/31 baseline**, five original documents, all final checks/preflight |

Sample ages (ms): `{"minimum": 250.505, "median": 311.621, "p95": 384.682, "maximum": 528.719}`.
RPC duration (us): `{"minimum": 260140, "median": 322457, "p95": 395944, "maximum": 541200}`.
Accepted row windows (us): `{"minimum": 3827, "median": 5686, "p95": 8416, "maximum": 9995}`.
Observer error: `None`.
Independent configuration comparison uses the post-fixture oracle and published
ReadServices. It does not compare Dart results to themselves. Payload-free
refusals are not counted as Good. Missing later stages are skipped, not inferred
successful from previous attempts. Runtime summary and stage exits record the
actual boundaries reached.

## Desktop and TASK evidence

Final candidate timing was not reached. The candidate trace contains 6918 valid observations; maximum recorded TASK value 9002 us, overlap count 0. First published probe sample 0, last 69224.
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
`{"passed": true, "readOnly": true, "controllerAccess": false, "observations": [{"sourceAgeUs": 906062, "rpcUs": 1221541, "transitUs": 313700, "receivedAgeUs": 1219762, "localProcessingUs": 13590, "effectiveAgeUs": 1233352, "fastGoodUs": 1000000, "responseProcessingMs": 908.841, "excessUs": 233352, "sourceAlreadyLate": false, "lateAtReceipt": true, "localProcessingCrossedBoundary": false}], "refusalReproduced": true, "interpretation": "Exact measured arithmetic, not an isolated code/host cause. Missing observations are not inferred."}`.
No missing timing is estimated. No timestamp is renewed to obtain LIVE.
Candidate error: `CalledProcessError: Command '['C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-partdiag-20261027\\session_01\\run_logged.py', 'desktop_readonly', 'C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-partdiag-20261027\\session_01\\desktop_readonly.py']' returned non-zero exit status 1.`.

## Restoration, gates and remaining work

Rollback downloads a hash-checked copy of genealogy
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`,
restores the five exact original host documents, runs **31/31 baseline cases**,
restores policy, MANUAL/idle/logout, saved/live equality and every final check/
preflight. Baseline scan: `{"lastScanMedianUs": 99.0, "cumulativeMaxUs": 1167, "overlaps": 0}`. The original ACD
is never opened. No dumps, fault/TASK-counter clears, clock changes, power/
vendor-state operations or Echo hard kills occur.

The preparation adds six session-only tracing tests and transfers unchanged
shipping inputs: **660 HMI tests passed /12 skipped**, analyzer, Windows
debug build and enforced lockfile, using Flutter **3.47.5 /Dart 3.13.4** and a
318-input identical source mirror. Six existing HMI source/test files changed
and two pool files were added relative to the startup diagnostic. All **373
PLC/gate bindings** remained unchanged: **2,339 AB tests**, both v38 builds/
read-backs/access/SDK audits, 15 byte-identical prior stage images and exact
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
