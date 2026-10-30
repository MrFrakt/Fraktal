# S4b-Q preparation — 2026-10-29

The approved O8 source is ready for native qualification on Echo `601FC87B`,
`127.0.0.1` slot 0, 1756-L81E v38.011. This record claims preparation only.
Standing owner authorization O3 applies; the approval template remains false
when this preparation is sealed. Fault/TASK-counter clears, clock changes,
power operations, vendor-state edits and Echo hard kills are excluded.

The candidate is unchanged: ACD
`30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`,
L5X `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`.
Fresh working copies came from the untouched cold-start preparation. Read-back
against its SDK export is equivalent. Capacity remains 2,066,212 used /
1,079,516 available / 3,145,728 Blocks (65%). The 2,339 AB tests, both v38
build/read-back gates and Capacity transfer through 373 unchanged PLC inputs.
They were not rerun for this client-only change.

[O8 offline qualification](AB_S4B_O8_CONFIGURATION_HEARTBEAT_2026-10-28.md)
sealed 740 HMI tests passed, 12 skipped; locked dependencies, clean analyzer,
Windows profile build, all 74 root tests and specification/contract/strict
consistency gates passed. Three consecutive profile rehearsals covered all
31 views, with maximum mapped ages 392,880 / 484,124 / 453,639 µs. The required
debug comparison refused LIVE after the overview. No shipping source changed
after those runs. Flutter 3.47.5 / Dart 3.13.4 was used.

The native profile executable was built in advance for the real CIP endpoint,
with tracing enabled and rehearsal disabled. Its 16 files are hash-bound;
no compiler runs during desktop timing. Helper build: zero warnings/errors.
Five helper tests cover authorization refusal, failure isolation/order,
independent configuration joins and cumulative TASK rejection. A separate
workflow test injects eight failure/success scenarios through the actual
orchestrator and verifies genealogy rollback in each. A local sampler probe
records host CPU and the actual EmulateControlLogix process without controller
access. Missing authorization refuses Python and SDK entry points before I/O.

The session starts with service/listener/identity/fault/keyswitch/session guards,
dump check, MANUAL normalization, fresh preflight and backup. After guarded
download/Run it runs the inherited 41 cases with concurrent read-only Dart
observation, then independently replays all 87 raw-read pairs. Read-only
stages follow the plan order: four configuration pages (1,100 scalar values
and types) against a fresh Python oracle, idle equivalence (5,407 paths),
generic acquisition (5,407 values/seven modules), strict LIVE profile desktop
(31 views), and 20 native timing samples. Each read-only stage records an
outcome even when an earlier read-only stage fails.

TASK polling starts before download. An append-only host marker after download
and before Run scopes candidate cumulative TASK evidence; no counter is cleared.
The final 20 samples extend scan evidence beyond desktop completion. The gate
requires cumulative maximum below 10,000 µs and zero overlaps. Overall host
and relevant process CPU are collected separately at one-second intervals.

The finally path restores a hash-checked copy of pinned genealogy
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`,
the five exact original host documents, 31 baseline cases, MANUAL/idle/logout,
final checks, preflight verification and baseline timing. The original ACD is
never opened. Fault/dump guards still stop further controller changes.

Workspace: `C:/work/fraktal-ab-s4b-q-20261028/session_01` (prepared October 28,
finalized October 29). The payload contains whitelisted helpers, proof logs,
input hashes and gate records. It excludes credentials, binaries and ACD/BAK.
All native E1–E9 outcomes remain open until the run finishes and is sealed.
Nothing is committed or pushed.
