# S4b parallel read-only reader qualification — 2026-10-27

**Native acceptance: OPEN / not accepted. Genealogy is restored.**
The [sealed preparation](AB_S4B_PARALLEL_READER_PREPARATION_2026-10-27.md) was
approved: “Approve guarded S4b parallel-reader session”, question
`call_18bf5754fcb54411bfc34409e002243f:0`. The exact-session authorization is
consumed. No subsequent controller changes are authorized by this record.

## Target, scope and reader

- Echo **601FC87B**, 1756-L81E **v38.011**, **127.0.0.1 slot 0**.
- Prepared ACD `30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`.
- Generated source `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`.
- Same exact-image offline Capacity: **2,066,212 used /1,079,516 available /
  3,145,728 total Blocks (65%)**; not physical-controller fit evidence.
- **1075 bound inputs** verify. Only the SDK-saved
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

## Actual results

**The fixture stopped after 25/41 cases**: 15 main, two Access and eight
configuration/set-store cases. The SFC adopted-fault record then raised
`part snapshot changed during every bounded read` from the legacy Part reader.
All 53 completed paired captures independently replay with exact values/types;
this is partial proof and does not satisfy the 87-pair/full-fixture gate.
The unchanged original replay gate first refused incomplete fixture counts;
separate partial analysis retains that refusal and reports the actual subset.
The first partial-count analysis also refused an incorrect assumption that
Access/config checks had not run; the corrected analysis counts all 25 cases.

The original three-attempt Part proof remains enforced. The failed run did not
record its before/body/after counter values or per-read timings, so the failure
does not isolate contention, counter changes or a publisher defect. Desktop,
independent page comparison, idle/generic acquisition and final timing were
not reached. No complete S4b acceptance or controlled performance comparison
with earlier, longer workloads is inferred from the shorter observer run.

| Gate | Recorded outcome |
|---|---|
| Candidate fixture | 25 passed; group counts in summary |
| Independent raw-record replay | 53 paired captures; 4799–5407 paths |
| Concurrent Dart observer | 1288 samples; 1288 entirely Good, 0 with Uncertain, 0 with Bad |
| Observer completion | PASS |
| Complete reader/configuration/acquisition | OPEN / not accepted |
| Configuration | 4 pages; None exact oracle values/types |
| Idle equivalence | 0 paths; OPEN / not accepted |
| Generic acquisition | 0 values /0 modules |
| Strict live desktop | OPEN / not accepted; 0 modules /0 bus nodes /0 views |
| Scan acceptance | OPEN / not accepted |
| Genealogy rollback | **31/31 baseline**, five original documents, all final checks/preflight |

Sample ages (ms): `{"minimum": 246.167, "median": 295.514, "p95": 385.779, "maximum": 493.517}`.
RPC duration (us): `{"minimum": 255243, "median": 305202.5, "p95": 395054, "maximum": 501987}`.
Accepted row windows (us): `{"minimum": 4057, "median": 5831.5, "p95": 8470, "maximum": 9965}`.
Observer error: `None`.
Independent configuration comparison uses the post-fixture oracle and published
ReadServices. It does not compare Dart results to themselves. Payload-free
refusals are not counted as Good. Missing later stages are skipped, not inferred
successful from previous attempts. Runtime summary and stage exits record the
actual boundaries reached.

## Desktop and TASK evidence

Final candidate timing was not reached. The candidate trace contains 4303 valid observations; maximum recorded TASK value 8994 us, overlap count 0. First published probe sample 0, last 42898.
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
Candidate error: `CalledProcessError: Command '['C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-pool-20261027\\session_01\\run_logged.py', 'candidate_regressions', 'C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-pool-20261027\\session_01\\candidate_regressions_v2.py', '--execute-fixture', '--expect-serial', '601FC87B', '--credential-file', 'C:/work/fraktal_echo38_access_fixture.json', '--output', 'C:\\work\\fraktal-ab-s4b-pool-20261027\\session_01\\candidate_regressions.json']' returned non-zero exit status 1.`.

## Restoration, gates and remaining work

Rollback downloads a hash-checked copy of genealogy
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`,
restores the five exact original host documents, runs **31/31 baseline cases**,
restores policy, MANUAL/idle/logout, saved/live equality and every final check/
preflight. Baseline scan: `{"lastScanMedianUs": 99.0, "cumulativeMaxUs": 1166, "overlaps": 0}`. The original ACD
is never opened. No dumps, fault/TASK-counter clears, clock changes, power/
vendor-state operations or Echo hard kills occur.

The preparation binds **660 HMI tests passed /12 skipped**, analyzer, Windows
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
