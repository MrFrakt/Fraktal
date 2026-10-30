# S4b observer policy and harness corrections — 2026-10-29

**Offline corrections pass. Native S4b remains open; Echo stays on genealogy.**

The [native attempt](AB_S4B_Q_ATTEMPT_2026-10-29.md) passed all 41 candidate
cases and 87 paired replays but refused 56 expired Status leaves in the
concurrent observer. Its rollback passed. This record keeps that failure intact
and qualifies the dependent offline corrections.

`qualify_cip_canonical.dart` now uses the approved optional CIP configuration
heartbeat and the same authoritative field classifier as the desktop. It selects
exactly the 230 O8 leaves before manifest replacements, keeps live identity,
active alarms, counters and Access fast, and applies slow/excluded sets atomically.
There are no declarations or station-specific mappings in the tool. A regression
replays the sealed refused native snapshot and preserves all 56 expiry records;
the 20-attempt, one-second acquisition deadline and fast 1/3-second Good/expiry
limits remain unchanged. The plan E3 row now explicitly names both existing
tier limits (fast Good 1 second, slow Good 7.5 seconds), as required by approved O8.
No acceptance limit is increased by this correction.

The changed observer passes a fresh, separate **100-sample loopback rehearsal**:
zero Bad samples, all four configuration pages, zero writes/refused services and
graceful peer shutdown. The peer uses the immutable raw controller capture and
unchanged latency distribution at scale 1, on an ephemeral loopback port. This
is synthetic observer proof, not native acceptance.

The orchestration correction catches a writer/observer failure after the fixture
has stopped and cleaned up, rechecks the healthy exact target and executes all
five independent read-only stages in plan order. Eight failure/success scenarios
exercise the actual parent with mocked process/controller calls and prove
rollback. The writer still stops at its first failure. Controller fault/dump
guards continue to stop further changes.

The CPU sampler handles transient wildcard-process counter errors, records invalid
or missing samples, and retains valid host and emulator samples. Readiness needs
a valid host sample; ten consecutive missing host samples still fail. Injected
churn retains three host, three emulator and three invalid samples plus the error
count. A live read-only sampler probe records three host/emulator samples and
exits cleanly. No system or controller counter is cleared.

An adaptive-packing experiment was tested and **reverted**. Binding-wide and
row-local variants did not pass three consecutive desktop rehearsals; profiles
01, 02 and 04 fail, while profile 03 passes all 31 views at 419,924 µs maximum
mapped age. All sources, tests and failed results are retained. The intermediate
744/746-pass suites describe those experimental sources. Their results are not
used to authorize a native image or claim final-source acceptance.

The restored desktop has **all 27 input hashes identical** to the sealed
[O8 qualification](AB_S4B_O8_CONFIGURATION_HEARTBEAT_2026-10-28.md). Independent
verification checks that record's artifacts, its three consecutive 31-view
profile passes (392,880 / 484,124 / 453,639 µs), debug comparison and every current
input. Those unchanged-source proofs transfer. The only additional changed HMI
files are the observer tool and its test; neither is imported by the desktop
graph. Their new behavior is qualified separately above. No experimental packing
logic remains in the product.

Final-source gates: **743 HMI tests passed, 12 skipped**, clean analyzer, locked
dependencies, Windows profile build, 74 root tests and specification/contract/
strict consistency gates. Flutter 3.47.5 / Dart 3.13.4 at
`C:/work/fraktal-toolchains/flutter-3.47.5`. All 373 PLC/gate hashes remain
unchanged, transferring the 2,339 AB tests, both v38 builds/read-backs and exact
candidate Capacity (65%); no PLC compilation was rerun for this observer change.

Workspace: `C:/work/fraktal-ab-s4b-observer-20261029/offline_01`. The append-only
payload includes failed intermediate runs and the reverted experiment, final
sources, sampler/workflow tests and the explicit desktop-proof transfer. It
excludes credentials, binaries and ACD/BAK. No controller changes occur here.
Next is fresh exact-source preparation and S4b-Q under standing O3, collecting
all read-only outcomes before genealogy rollback. Native improvement is unproven.
S5/S6 and deferred physical S7 remain; no commit/push or S4b exit is claimed.
