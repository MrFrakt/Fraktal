# S4b bounded row-refill preparation — 2026-10-27

**Prepared offline; not authorized or natively accepted.** The generic reader
now refills a completed row slot immediately, retaining four active rows,
whole-row socket leases and every existing acceptance limit. PLC image,
publication contract and all fixture writes remain unchanged.

## Completed busy-witness session

The [sealed attempt](AB_S4B_BUSY_WITNESS_ATTEMPT_2026-10-27.md) passes **41/41
candidate cases** and **87/87 independent exact raw-record replays**, with
4,799–5,407 paths. The separate one-path busy witness proves canonical/legacy
busy values true at entire-scan generation **4,934** in six polls. It is never
counted as a full pair. All 218 Part reads succeed in 225 attempts.

The Dart observer completes **2,805 entirely Good samples**, zero Uncertain or
Bad, four configuration queries and targeted details. Age median/p95/max is
279.061/347.923/520.648 ms; accepted row window maximum 9,998 us.

Strict desktop initially reaches LIVE with seven modules, then refuses
`after-overview`: source age 995,517 us, RPC 1,377,140 us, server bracket
1,066.586 ms, transit 311,554 us, received age 1,307,071 us, local 3,489 us,
effective age **1,310,560 us** against **1,000,000 us** fast Good. The late
sample records worker acquisition 1,011,964 us, queue 50,754 us, projection
6,260 us, path expansion 18,757 us and send 927 us; frontend validation 2 us.
These intervals include instrumentation/scheduling and do not isolate a
network/host/PLC cause. Zero desktop views are accepted. Independent
configuration/idle/generic acquisition/final timing are skipped. TASK maximum
8,994 us /zero overlaps over the recorded epoch is not final scan acceptance.
Genealogy, five original documents, 31/31 baseline and all final/preflight
checks pass. The session approval is consumed; all earlier failures remain.

## Bounded scheduling correction

The old planner waits for all four rows in a batch before starting the next
batch. A delayed row can therefore leave completed sibling slots idle while
independent rows are ready. A deterministic test holds one of eight published
scalar rows, lets its three siblings finish and checks whether a fifth starts.
The old implementation fails with exactly four started; the correction starts
the next ready row while the first is still held.

`CipReadPlan.acquire` now has **at most four active rows and one slot waiter**.
Completion makes a slot available without waiting for unrelated siblings.
Array-count dependencies and the final Status phase still drain the complete
active window before proceeding. A failure stops further dispatch once
observed; all started rows finish before the acquisition returns the original
error. No started row outlives a refused walk or its connection owner.
Invalid concurrency refuses before any read. Targeted reads remain serial.

The pool still has four serial-pinned connections and one outstanding request
per socket. Each entire row retains one connection through counters,
dependencies, body/fragments and the closing counter. Native read/decoding,
logical path/value/type contracts, count revision ordering, source timestamps,
age boundaries, fast Good/expiry **1/3 s**, slow **7.5/15 s**, and desktop
**20 attempts/one second** remain unchanged. The planner still publishes only
proved rows; errors/late values never acquire a Good payload. No observation
frame is used by the generic client. No PLC/write/security change occurs.

This is an offline scheduling correction, **not a native latency claim**.

## Verification

- **668 HMI tests pass /12 intentional skips**, including three new cases:
  immediate refill, failure draining and invalid concurrency. Existing golden
  values/types, serial-targeted reads, torn/frozen/restarted counters, count
  contradictions, lease ownership and socket bounds retain their gates.
- **56 trace-enabled focused tests pass**, analyzer reports no issues, Windows
  debug build and `pub get --enforce-lockfile` pass. Flutter **3.47.5 /Dart
  3.13.4**, `C:/work/fraktal-toolchains/flutter-3.47.5`. The **319-input mirror**
  matches; only the planner and pool-test file change, with no added HMI file.
- Recorded-wire replay retains **810 reads /237 groups /zero hidden ByClass
  reads**, with all **976 consumed values/types** equal to the independent
  oracle and the prior tier/queue replay. This is not native timing evidence.
- The native-proven short busy witness is unchanged: **14 tests pass**. Six
  unchanged Part tracing tests pass. Fresh SDK build has zero warnings/errors;
  16 authorization refusals, missing-approval parent/SDK, eight workflow, six
  readiness and two read-only helper refusals pass. CLI argument refusal occurs
  before I/O. No offline gate connects to Echo.
- Spec/contracts/strict consistency/whitespace and **74 root tests pass**.
- All **373 PLC/gate bindings** are unchanged: **2,339 AB tests**, both v38
  build/read-back/access/SDK gates and exact-image Capacity transfer by hashes.
  Capacity **2,066,212 used /1,079,516 available /3,145,728 total Blocks (65%)**;
  not physical-controller fit evidence.

Failed offline runs remain archived. The first counterexample fixture omitted
the case where the selected row parent equals its publication root; after that
fixture correction the old planner fails the intended refill assertion. The
first new failure test waited for three completions even though dispatch had
already stopped after two; correcting its wait preserves the stricter failure
rule. The first sealer materializer stops at a substitution-count assertion
before creating outputs; its corrected run passes. None weakens acceptance.

## Exact proposed retry

- Local Echo **601FC87B**, **1756-L81E v38.011**, **127.0.0.1 slot 0**.
- Prepared ACD
  `30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`.
- Generated source
  `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`.
- Fresh service/listener/identity/mode/fault/idle/session guards and backup;
  guarded MANUAL normalization if needed; Program/download/Run.
- Five-document restore and the same 41 candidate cases with the unchanged
  short busy witness, retaining all 87 full comparisons. Concurrent corrected
  four-connection read-only Dart observation and existing Part/phase tracing;
  read-only TASK monitoring at nominal 100 ms from before download.
- Strict LIVE/nonempty desktop qualification: seven modules, three bus nodes,
  31 views, with real source quality/age and independent semantic validation.
  Remaining independent four-page/1,100-value comparison, 5,407-path idle
  equivalence, 5,407-value/seven-module acquisition and final scan if ready.
  Stop candidate work at its first failure.
- Pinned genealogy rollback, five exact original documents, 31 baseline cases,
  MANUAL/idle/logout, saved/live equality and all final/preflight checks.

Fault/TASK-counter clears, clock changes, power/vendor-state operations and Echo
hard kills remain excluded. The preparation authorizes no controller change.
[AGENTS.md §3a](../../../AGENTS.md) requires current explicit authorization;
the prior approved session completed with verified rollback.

## Remaining plan

S4b desktop/full configuration/acquisition/final scan acceptance is open.
Then S5 generic Dart gateway/Web/installer, S6 classified legacy retirement,
persistence/events/capacity, and S7 physical/CIP Security including real I/O.
Persistence medium, gateway write posture per station, hardware and commit/push
policy remain owner decisions. V2/Part III remain inactive. Nothing is committed
or pushed. Evidence is append-only and excludes credentials/ACD/SDK binaries.
