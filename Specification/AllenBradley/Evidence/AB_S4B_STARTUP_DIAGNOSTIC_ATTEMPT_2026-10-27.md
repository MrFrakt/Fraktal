# S4b desktop startup diagnostic qualification — 2026-10-27

**Native acceptance: OPEN / not accepted. Genealogy is restored.**
The owner approved the [sealed startup diagnostic package](AB_S4B_STARTUP_DIAGNOSTIC_PREPARATION_2026-10-27.md):
“Approve guarded S4b startup diagnostic session”, question
`call_7d2226c74b974b268cf6aa63ab8aaae6:0`. Its approval is now consumed.

## Target, image and bindings

- Local Echo **601FC87B**, 1756-L81E **v38.011**, 127.0.0.1 slot 0.
- ACD `30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`.
- Generated PLC source `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`.
- Exact-image offline Capacity: **2,066,212 used /1,079,516 available /
  3,145,728 total Blocks (65%)**.
- **1071 source/gate/image bindings** matched before
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
| Concurrent Dart observer | PASS; 906 samples |
| Quality | 906 entirely Good; 0 with Uncertain; 0 with Bad |
| Full reader/configuration/acquisition scope | OPEN / not accepted |
| Read-only configuration | 4 pages /None exact oracle scalar/type comparisons |
| Idle equivalence | 0 paths; OPEN / not accepted |
| Generic acquisition | 0 values /0 modules |
| Strict live desktop | OPEN / not accepted; 0 modules /0 bus nodes /0 views |
| Startup/workload/desktop/final scan | OPEN / not accepted |
| Genealogy rollback | **31/31 baseline**, original documents, all final checks and preflight passed |

Sample ages (ms): `{"minimum": 623.08, "median": 691.696, "p95": 776.049, "maximum": 898.383}`. Accepted row windows (us):
`{"minimum": 2824, "median": 3232.5, "p95": 4636, "maximum": 8908}`. The observer retains any refused snapshot and checks
strict root identity and the existing one-second fast Good boundary. A global
Good-sample aggregate does not authorize an older root or another late row.
Configuration pages are compared against the independent post-fixture oracle.
No torn row, missing identity or late payload is promoted to Good.

Observer error, if any: `None`.
Parent failure, if any: `CalledProcessError: Command '['C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-startup-20261027\\session_01\\run_logged.py', 'desktop_readonly', 'C:\\Python314\\python.exe', 'C:\\work\\fraktal-ab-s4b-startup-20261027\\session_01\\desktop_readonly.py']' returned non-zero exit status 1.`.
The bounded writer fixture joins the observer at completion; a failed observer
does not establish concurrent acceptance merely because fixture cases finish.
Later stages skipped after failure are not inferred successful from prior runs.
Full stage exits and raw records are retained.

## Measured refusal timing

The only shipping-code addition is a refusal diagnostic. Accepted source ages,
freshness limits, row proofs, retries and write policy are unchanged. The helper
retains the primary startup exception/stack before using app state.

Repository timing analysis: `{"passed": true, "readOnly": true, "controllerAccess": false, "observations": [{"sourceAgeUs": 982641, "rpcUs": 1026951, "transitUs": 16992, "receivedAgeUs": 999633, "localProcessingUs": 3497, "effectiveAgeUs": 1003130, "fastGoodUs": 1000000, "responseProcessingMs": 1010.959, "excessUs": 3130, "sourceAlreadyLate": false, "lateAtReceipt": false, "localProcessingCrossedBoundary": true}], "refusalReproduced": true, "interpretation": "Exact measured arithmetic, not an isolated code/host cause. Missing observations are not inferred."}`.
The numeric reconciliation uses source + transit = received age, then received
age + local processing = effective age. It checks the server-processing
subtraction and the unchanged Good boundary. A source already over its limit,
a crossing at receipt and a crossing during local processing are distinguished
only when measured fields support that conclusion. Missing observations are
not inferred. This arithmetic does not isolate a code routine or host cause.
The [transport contract](../../OPCUA_TRANSPORT.md) requires conservative complete
acquisition age; no timestamp is renewed to obtain a LIVE result.

## TASK and desktop evidence

Final candidate timing was not reached. The candidate trace contains 6733 valid observations; maximum recorded TASK value 8937 us, overlap count 0. First published probe sample 0, last 67369.
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

Desktop detail: `{"accepted": false, "modules": 0, "views": 0, "fieldbusNodes": 0, "error": "FormatException: Complete station sample is late or expired.", "link": null, "localWriteRefusals": 0, "fixtureClientWriteCalls": null, "nativeWireWriteCountMeasured": false, "primaryError": "Complete station sample is late or expired.", "primaryBoundary": "OpcUaRepository initial complete-sample freshness check", "helperSecondaryError": "FormatException: Complete station sample is late or expired."}`.

## Restoration, gates and remaining work

The runner downloads a hash-checked copy of genealogy
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`,
restores the five exact original host documents, runs 31 baseline cases,
restores policy, normalizes MANUAL/idle/logout and passes final checks/preflight.
Baseline timing: `{"lastScanMedianUs": 99.0, "cumulativeMaxUs": 1167, "overlaps": 0}`. The original genealogy
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
