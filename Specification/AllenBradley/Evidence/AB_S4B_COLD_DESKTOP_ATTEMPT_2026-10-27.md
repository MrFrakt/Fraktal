# S4b cold-start and strict desktop qualification — 2026-10-27

**Native acceptance: OPEN / not accepted. Genealogy is restored.**
The [sealed preparation](AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26.md) was
approved by the owner: “Approve guarded S4b cold-start/desktop session”,
question `call_297cd0f6497b4493909e0f524643c7c9:0`. This exact-image approval
is consumed. No later controller changes are authorized by this record.

## Target and immutable image

- Local Echo **601FC87B**, 1756-L81E **v38.011**, 127.0.0.1 slot 0.
- Prepared ACD `30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`.
- Generated source `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`.
- Studio offline Capacity: **2,066,212 used /1,079,516 available /3,145,728
  total Blocks (65%)**. Native physical-controller fit is not covered.
- All **1071 source/gate/image bindings** matched before
  execution. Post-run verification permits only the SDK-saved working ACD
  to differ; original prepared image and genealogy rollback pin stay unchanged.

## Actual results

| Gate | Recorded outcome |
|---|---|
| Candidate fixture | 41 successful cases; groups in `runtime_summary_01.json` |
| Independent raw-record replay | 87 paired captures |
| Concurrent Dart observer | 68 samples; 68 entirely Good, 0 with Uncertain, 0 with Bad |
| Observer completion | OPEN / not accepted |
| Full reader/configuration/acquisition scope | OPEN / not accepted |
| Read-only configuration | 0 pages; None exact oracle scalar/type comparisons |
| Idle equivalence | 0 paths; OPEN / not accepted |
| Generic acquisition | 0 values /0 modules |
| Strict live desktop | OPEN / not accepted; 0 modules /0 fieldbus nodes /0 views |
| Startup/workload scan | OPEN / not accepted |
| Genealogy baseline | **31/31**, original five documents and all final/preflight checks passed |

Sample age statistics (ms): `{"minimum": 691.246, "median": 788.9124999999999, "p95": 876.098, "maximum": 961.11}`. Maximum accepted per-row
window statistics (us): `{"minimum": 3157, "median": 3842.0, "p95": 5484, "maximum": 5857}`. Payload-free refusals are not
counted as Good; strict root identity/freshness and the 20-attempt/one-second
policy remain unchanged. Read-only configuration pages are compared to the
independent post-fixture oracle, not to their own Dart values.

## Startup and desktop scope

Final candidate timing was not reached. The candidate trace contains 7659 valid observations; maximum recorded TASK value 9002 us, overlap count 0. First published probe sample 0, last 76682.
The monitor reads fixed TASK scalars at nominal 100 ms from before download
through candidate timing and stops before rollback. Temporary download read
errors remain in the raw trace. Separately read scalars and polling bound the
observations; they do not identify an exact offending scan or routine/host cause.
No counters are cleared. This image defers only cold first-scan view formatting
behind invalid publication/full-buffer clearing; retained access masking stays
immediate. Native evidence covers this approved local Echo workload only.

Desktop acceptance uses the production factory/repository/UI with genuine
source quality/age. The helper requires LIVE, a nonempty complete module forest,
correct tab selection, seven modules, three bus nodes and 31 views before it
can succeed. The parent independently validates semantic coverage. Refresh logs,
forest transitions, screenshots, test stdout/stderr and any failure record are
retained. Captured-fixture substitutions are disabled in live mode.

Desktop detail: `{"accepted": false, "modules": 0, "views": 0, "fieldbusNodes": 0, "error": null, "link": null, "localWriteRefusals": null, "fixtureClientWriteCalls": null, "nativeWireWriteCountMeasured": false}`.
Candidate error, if any: `CalledProcessError: Command '['C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-cold-20261026\\session_01\\run_logged.py', 'candidate_regressions', 'C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-cold-20261026\\session_01\\candidate_regressions_v2.py', '--execute-fixture', '--expect-serial', '601FC87B', '--credential-file', 'C:/work/fraktal_echo38_access_fixture.json', '--output', 'C:\\work\\fraktal-ab-s4b-cold-20261026\\session_01\\candidate_regressions.json']' returned non-zero exit status 1.`. Missing later stages
are skipped after the first failure, never inferred successful from older runs.
The complete stage exits and raw result are archived.

## Rollback, gates and next work

The runner downloaded a hash-checked copy of genealogy
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`,
restored the five exact original host documents, ran 31/31 baseline cases,
restored policy, normalized MANUAL/idle/logout and passed final checks and
preflight. Baseline scan: `{"lastScanMedianUs": 99.0, "cumulativeMaxUs": 1167, "overlaps": 0}`. The original
genealogy ACD was not opened. No dumps, fault/TASK-counter clears, clock
changes, power/vendor-state operations or Echo hard kills occurred.

The preparation binds **2,339 AB tests, 74 root tests, both v38 builds and
read-backs, access/SDK audits, 15 byte-identical prior images and 65% Capacity**.
Shipping HMI code/dependencies are unchanged: pinned Flutter 3.47.5 /Dart
3.13.4, **647 passed /12 skipped**, analyzer/Windows/enforced-lockfile proof
remains bound. The standalone desktop helper has its own analyzer, 31-view
positive rendering replay, expected stale/empty refusal and six coverage tests.
Runtime execution changes no shipping source. Credentials and ACD/SDK binaries
are excluded from this archive; their approved binary inputs are hash-bound.

S5 gateway/Web/installer, S6 classified legacy-reader migration/retirement,
persistence/events and capacity reductions, and S7 physical/CIP Security
including real I/O remain. S4 acceptance is limited to the actual outcome above.
V2/Part III remain inactive target drafts. Nothing is committed or pushed.
