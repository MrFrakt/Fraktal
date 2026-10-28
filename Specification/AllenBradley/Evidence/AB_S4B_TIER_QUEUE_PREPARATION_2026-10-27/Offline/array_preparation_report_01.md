# S4b logical array tiers and worker queue correction — 2026-10-27

**Two implementation corrections pass offline gates. Native acceptance remains
open; this retry is not authorized.** The [timing attempt](AB_S4B_DESKTOP_TIMING_ATTEMPT_2026-10-27.md)
passes **41/41 candidate cases, 87/87 exact independent replays and 2,035 observer
samples**: **2,033 entirely Good, two with payload-free Uncertain rows, zero Bad**.
Observer age median/p95/max is **309.58 /373.504 /997.151 ms**; maximum accepted
row window is **9,959 us**. Four configuration page queries and targeted details
complete. All 218 Part calls succeed in 223 attempts. Desktop reaches LIVE with
seven modules, then fails `after-overview`; zero views are accepted. Remaining
independent page comparison, idle/generic acquisition and final scan are skipped.
TASK trace maximum is **8,937 us /zero overlaps**. Genealogy, five original
documents, **31/31 baseline**, policy, MANUAL/idle/logout and all final/preflight
checks are restored. That session's authorization is consumed.

The rejected desktop sample measures source **874,812 us**, RPC **1,170,250 us**,
server processing **879.170 ms**, transit **292,080 us**, received age **1,166,892
us**, local processing **2,391 us**, effective age **1,169,283 us** against
**1,000,000 us**. Phase tracing records acquisition **873,556 us**, worker queue
**50,904 us**, projection **10,934 us**, path expansion **18,689 us**, send
**1,167 us**, and frontend validation **1 us**. These intervals include scheduling
and instrumentation; they do not isolate a network/host/PLC cause.

## Corrections and proof

The trace contains profiler `ByClass` reads whose logical leaves are excluded.
The planner classified a primitive array by its unindexed base, while tier
requests name its logical elements. It therefore read fully excluded arrays
and treated arrays with all-slow leaves as fast. Excluded siblings could also
keep an otherwise slow group fast.

The planner now expands logical leaves using **PLC-published bounds, extent
and indices**, then bases scheduling on consumed leaves. Fully excluded groups
perform no cyclic read; all-consumed-slow groups follow the existing heartbeat.
A fast consumer keeps its native group fast. Explicit targeted reads still
bypass exclusion under the original row proof. Discovery, logical extents,
values/types, native decode and projection remain unchanged. No station facts
or declaration are added to the client.

Five regression cases cover closed profiler histories, excluded arrays, slow
heartbeat, slow consumers with excluded siblings, fast promotion and explicit
targeted reads. **Four fail before the fix and pass after**; targeted-read
preservation passes both. Earlier fixture import/alignment and working-directory
failures are retained with corrected runs. A recorded-wire replay using the
same tier classifier reduces **990→810 reads**, **297→237 guarded groups**, and
**60→0 hidden ByClass reads**, preserving all **976 consumed values and types**
against the independent Python oracle and the pre-change replay. This is about
18% fewer wire reads in that replay, not a native latency or acceptance claim.

The server processing bracket previously began after the worker's serialized
queue. It now starts at request receipt and ends at the original age boundary,
including queue time as the [transport envelope](../../OPCUA_TRANSPORT.md)
requires for server wait/read. The existing receiver test checks queue+read
accounting and still rejects an underreported bracket. Source timestamps and
leaf/complete ages are not renewed. Fast **1/3 s**, slow **7.5/15 s** Good/expiry
limits, **20 attempts /one-second** row budget, proof windows and read-only policy
remain unchanged. Existing optional diagnostic traces remain enabled only in
qualification launchers. **Native improvement remains unproven.**

## Exact image and proposed scope

- Echo **601FC87B**, 1756-L81E **v38.011**, **127.0.0.1 slot 0**.
- ACD: `30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`.
- Source: `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`.
- Same Capacity: **2,066,212 used /1,079,516 available /3,145,728 total Blocks
  (65%)**. Physical-controller fit is not covered.
- Runner: `C:/work/fraktal-ab-s4b-array-tiers-20261027/session_01/qualification_session_v2.py`.

Fresh service/listener/identity/mode/fault/session/idle guards and backup;
guarded MANUAL normalization if needed; Program/download/Run; five-document
restore and the same **41 candidate cases** with the corrected four-connection
serial-pinned read-only observer, one outstanding request per socket, original
Part tracing and phase timing. Read-only TASK monitoring at nominal **100 ms**
starts before download. Strict LIVE/nonempty/full desktop coverage follows;
remaining configuration/detail/oracle comparisons, idle equivalence, generic
acquisition and final scan follow only if ready. Candidate work stops at its
first failure. Then pinned genealogy rollback, exact original host documents,
five-document restore, **31 baseline cases**, MANUAL cleanup and all final
checks/preflight. Rollback retains target/fault/idle/session guards.

No added PLC write vectors, fault/TASK-counter clears, clock changes, power/
vendor-state operations or Echo hard kills. The original genealogy ACD
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084` is never opened;
rollback downloads its hash-checked copy. Credentials are never archived.

## Gates and provenance

- **665 HMI tests pass /12 skipped**, including the five new regressions;
  **53 trace-enabled focused tests**, analyzer, Windows debug build and enforced
  lockfile pass with Flutter **3.47.5 /Dart 3.13.4**. The **319-input** isolated
  mirror matches: three existing source/test files change and one is added.
- All **373 PLC/gate bindings** remain unchanged: **2,339 AB tests**, both v38
  build/read-back/access/SDK gates, 15 byte-identical prior images and exact-image
  Capacity transfer by hashes. No PLC source or generated image changes.
- Fresh SDK builds with zero warnings/errors. Six retained Part-trace tests,
  16 authorization refusals, missing-approval parent/SDK, eight workflow, six
  readiness and both read-only helper refusals pass without controller access.
  Spec/contracts/strict consistency, **74 root tests** and whitespace pass.
- Prior evidence seals and bound inputs verify. Private Dart maps stay pinned.
  No authorization/start/backup/deploy/desktop/Part-trace output exists in the
  fresh session. ACD/SDK binaries are hash-bound and excluded from archives.

Next: qualify these corrections on Echo after fresh approval, then restore
genealogy and all baseline checks. S4b desktop/full acquisition/final scan remain
open. S5 gateway/Web/installer, S6 classified legacy migration/retirement/
persistence/events/capacity and S7 physical/CIP Security including real I/O remain.
Persistence medium, gateway write posture per station, physical hardware and
commit/push policy remain owner decisions. V2/Part III inactive; nothing committed.

[AGENTS.md §3a](../../../AGENTS.md) requires “current explicit authorization
and an exact target check immediately before use.” The completed timing session
ended with verified rollback and its approval is consumed. This fresh retry
needs current approval for the corrected reader and the unchanged image/write scope.
