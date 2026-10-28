# S4b Status-order qualification — 2026-10-27

**Native acceptance: OPEN / not accepted. Genealogy is restored.**
The owner approved the [sealed Status-order package](AB_S4B_STATUS_ORDER_PREPARATION_2026-10-27.md):
“Approve guarded S4b Status-order retry”, question
`call_e167e16df752449e8bbb27e2ef44e6b7:0`. Its approval is now consumed.

## Target, image and bindings

- Local Echo **601FC87B**, 1756-L81E **v38.011**, 127.0.0.1 slot 0.
- ACD `30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`.
- Generated PLC source `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`.
- Exact-image offline Capacity: **2,066,212 used /1,079,516 available /
  3,145,728 total Blocks (65%)**.
- **1070 source/gate/image bindings** matched before
  execution. Post-run verification permits only the SDK-saved working ACD to
  differ. The original prepared image and pinned genealogy ACD remain unchanged.

The generic client schedules discovered module Status groups near the end of
full cyclic walks, including leaf modules already fitting one guarded group.
The prepared comparison proves identical wire-read multisets and projected
values/types. Targeted reads, tiers, source ages, row proofs and all freshness,
attempt and deadline limits are unchanged. Late rows still withhold payload.
The migration observation frame is used only by the independent Python oracle;
the shipping desktop client discovers and reads canonical rows directly.

## Actual outcome

| Gate | Recorded result |
|---|---|
| Fixture | 41 passed cases |
| Independent replay from raw controller bytes | 87 pairs |
| Concurrent Dart observer | PASS; 910 samples |
| Quality | 902 entirely Good; 8 with Uncertain; 0 with Bad |
| Full reader/configuration/acquisition scope | OPEN / not accepted |
| Read-only configuration | 4 pages /None exact oracle scalar/type comparisons |
| Idle equivalence | 0 paths; OPEN / not accepted |
| Generic acquisition | 0 values /0 modules |
| Strict live desktop | OPEN / not accepted; 0 modules /0 bus nodes /0 views |
| Startup/workload/desktop/final scan | OPEN / not accepted |
| Genealogy rollback | **31/31 baseline**, original documents, all final checks and preflight passed |

Sample ages (ms): `{"minimum": 697.465, "median": 828.5365, "p95": 935.218, "maximum": 999.542}`. Accepted row windows (us):
`{"minimum": 3088, "median": 3756.0, "p95": 5494, "maximum": 9737}`. The observer retains any refused snapshot and checks
strict root identity and the existing one-second fast Good boundary. A global
Good-sample aggregate does not authorize an older root or another late row.
Configuration pages are compared against the independent post-fixture oracle.
No torn row, missing identity or late payload is promoted to Good.

Observer error, if any: `None`.
Parent failure, if any: `CalledProcessError: Command '['C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-status-20261027\\session_01\\run_logged.py', 'desktop_readonly', 'C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-status-20261027\\session_01\\desktop_readonly.py']' returned non-zero exit status 1.`.
The bounded writer fixture joins the observer at completion; a failed observer
does not establish concurrent acceptance merely because fixture cases finish.
Later stages skipped after failure are not inferred successful from prior runs.
Full stage exits and raw records are retained.

## TASK and desktop evidence

Final candidate timing was not reached. The candidate trace contains 8099 valid observations; maximum recorded TASK value 8994 us, overlap count 0. First published probe sample 0, last 81055.
The fixed read-only TASK monitor starts before download, polls at nominal
100 ms and stops before rollback. Download read errors are retained. Separate
scalar reads and polling bound observations; they do not isolate an exact
offending scan, routine or host cause. No TASK counter is cleared. The PLC's
cold first-scan view deferral remains the identical previously qualified image.
Retained-mode/power/physical acceptance is not established here.

Desktop uses the real production factory/repository/UI and genuine source
quality/age. The helper requires LIVE, complete nonempty module coverage,
selected tabs and 31 views before success. The parent independently checks
semantic coverage. Screenshots, native test stdout/stderr, refresh and forest
diagnostics, and any failure record remain archived. Captured-fixture
substitutions are disabled in live mode. Local start/login calls must be refused
by the read-only repository; this does not create a native packet-write counter.

Desktop detail: `{"accepted": false, "modules": 0, "views": 0, "fieldbusNodes": 0, "error": "Null check operator used on a null value", "link": null, "localWriteRefusals": 0, "fixtureClientWriteCalls": null, "nativeWireWriteCountMeasured": false, "primaryError": "Complete station sample is late or expired.", "primaryBoundary": "OpcUaRepository initial complete-sample freshness check", "helperSecondaryError": "Null check operator used on a null value"}`.

## Restoration, gates and remaining work

The runner downloads a hash-checked copy of genealogy
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`,
restores the five exact original host documents, runs 31 baseline cases,
restores policy, normalizes MANUAL/idle/logout and passes final checks/preflight.
Baseline timing: `{"lastScanMedianUs": 99.0, "cumulativeMaxUs": 1166, "overlaps": 0}`. The original genealogy
ACD is never opened. No dumps, fault/TASK-counter clears, clock changes,
power/vendor-state operations or Echo hard kills occur.

Preparation binds **648 HMI tests passed /12 skipped**, pinned Flutter
3.47.5 /Dart 3.13.4, analyzer, Windows debug build and enforced lockfile.
All 12 read-plan tests and the independent traffic/value comparison pass.
The identical PLC source/image preserves **2,339 AB tests**, both v38
build/read-back/access/SDK gates, 15 prior byte-identical images and 65%
Capacity. Root spec/contracts/strict consistency and 74 tests pass.
Credentials and ACD/SDK binaries are excluded from the archive; binary inputs
are hash-bound. No shipping source changes during runtime.

S4 is accepted only at the actual scope recorded above. Remaining stages are
S5 Dart gateway/Web/installer, S6 classified legacy-reader migration/retirement,
persistence/event ownership and capacity work, and S7 physical/CIP Security,
including real I/O. V2/Part III stay inactive until their remaining gates.
Nothing is committed or pushed. No later controller session is authorized.
