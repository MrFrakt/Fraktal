# S4b read-only body-packet preparation — 2026-10-27

**Prepared offline; not authorized or natively accepted.** The generic Dart
reader combines fitting count/body reads in a bounded Multiple Service Packet
(MSP), between separately completed counter requests. It preserves the PLC
image, contract values/types, row proof, freshness limits and fixture writes.

## Completed row-refill session

The [sealed attempt](AB_S4B_REFILL_ATTEMPT_2026-10-27.md) passes **41/41 cases**,
**87/87 independent exact raw-record replays** (4,799–5,407 paths), the separate
short login-busy witness and **3,144 entirely Good Dart samples**, zero
Uncertain/Bad. Four configuration queries and targeted details complete. All
218 Part calls succeed in 222 attempts. Observer age median/p95/max is
265.8085/337.691/523.733 ms; maximum accepted row window 9,995 us.

Strict desktop initially reaches LIVE with seven modules, then refuses
`after-overview`: source age 996,563 us, RPC 1,610,859 us, server bracket
1,183.292 ms, transit 428,567 us, received age 1,425,130 us, local 3,015 us,
effective age **1,428,145 us** against **1,000,000 us** fast Good. Worker
acquisition is 1,125,722 us and queue 50,819 us; frontend validation is 2 us.
These measured intervals do not isolate a host/network/PLC cause. Zero views
are accepted. Independent configuration/idle/generic acquisition/final timing
are skipped. TASK maximum 9,003 us/zero overlaps is observational, not final
scan acceptance. Genealogy, five original documents, **31/31 baseline** and
all final/preflight checks pass. The completed authorization is consumed.

## Read-only timing controls

The [sealed controls](AB_S4B_HOST_TIMING_2026-10-27.md) run on the restored
genealogy baseline. Scalar request medians are 0.891 ms in Dart CLI, 1.120 ms
in Flutter without widgets and 1.2765 ms under simulator UI load. Flutter
maximum requests are 13.073/16.290 ms, exceeding the 10 ms proof window.
They do not establish the cause of the earlier refusal.

Python and Dart each validate 20 native MSPs/60 reads. One Dart packet spans
a sample-counter change: no packet atomicity is claimed. These controls make
no tag writes, mode/download/clear/clock/power changes. The baseline sample
counter is not the canonical seqlock. They are packet-support evidence, not
canonical row or desktop acceptance.

## Generic read correction and proof

The existing native-read layout owns path/count/type/handle/extent facts for
both readers. A fitting row with at least two count/body reads can use one
MSP. The pre-counter request completes first; body reads then execute in the
packet; the post-counter request completes afterwards. Count sources remain
inside that bracket. No order among embedded body reads is assumed. A golden
test executes them in reverse and verifies the same values/types and external
counter boundaries. No counter is folded into the packet. An earlier
counter-folding prototype is retained as an abandoned experiment and excluded
from the proposed runtime package: a vendor execution-order guarantee was not
established.

The [Rockwell data-access manual](https://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm020_-en-p.pdf)
documents MSP service 0x0A to Message Router class 2/instance 1. The client
allows only bounded symbolic Read Tag Fragmented (0x52) subrequests, at most
64, within both request and reply connection budgets. Nested packets, writes
and Connection Manager wrappers refuse. Paths/data are copied before checking
and queuing; later caller mutation cannot change the checked request. Reply
counts, offsets, services, types, structure handles and extents are checked.
Malformed responses refuse and poison the socket.

Large rows and data-dependent variable-length primitive arrays keep the
original fragmented reader. Unsupported or valid partial replies discard the
packet and fall back within the **same attempt, elapsed window and deadline**.
Count shrink still withdraws ineligible rows. The equal-even/elapsed-window
proof, **20 attempts/one second**, source ages, fast Good/expiry **1/3 s**,
slow **7.5/15 s**, whole-row leases, four-connection bound, row refill and
count/Status barriers remain. Direct desktop CIP is read-only. No station
declaration or observation frame is used by the client.

## Verification

- **685 HMI tests pass/12 intentional skips**, including 16 batch tests and
  a queued-input mutation test in the existing pool module. Golden values/
  types, reversed-body execution, partial/unsupported fallback, malformed
  refusal, torn counters, elapsed-window rejection and count shrink pass.
- **73 trace-enabled focused tests pass**. Analyzer, Windows debug build and
  `pub get --enforce-lockfile` pass with Flutter **3.47.5/Dart 3.13.4** at
  `C:/work/fraktal-toolchains/flutter-3.47.5`. The **320-input mirror** matches
  all shipping inputs; four existing HMI source/test files change and one
  test module is added relative to the completed refill preparation.
- Recorded-wire replay uses **@PACKETS@ packets** for **@READS@ logical reads**
  across **237 groups**, versus 810 packets previously. All **976 consumed
  values/types** match the independent oracle and prior replay. This is a
  model packet count, not native full-tree latency evidence.
- Fourteen unchanged busy-witness tests and six Part tracing tests pass.
  Fresh SDK build has zero warnings/errors. Sixteen authorization refusals,
  missing-approval parent/SDK, eight workflow, six readiness and two read-only
  helper refusals pass; CLI argument refusal occurs before I/O.
- Spec/contracts/strict consistency/whitespace and **74 root tests pass**.
- **373 PLC/gate bindings** are unchanged: **2,339 AB tests**, both v38 builds/
  read-back/access/SDK gates and exact-image Capacity transfer by hashes.
  Capacity is **2,066,212 used/1,079,516 available/3,145,728 total Blocks (65%)**.
  This is not physical-controller fit evidence.

Failed offline runs and the abandoned prototype remain archived separately
from the final body-only implementation. No acceptance limit is relaxed.
The final full-suite/analyzer/build/focused outputs have suffix `_02`;
`isolated_hmi_sources_02.json` binds the final source, not the prototype.

## Exact proposed qualification

- Local Echo **601FC87B**, **1756-L81E v38.011**, **127.0.0.1 slot 0**.
- Prepared ACD
  `30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`.
- Generated source
  `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`.
- Fresh service/listener/identity/mode/fault/idle/session guards and backup;
  guarded MANUAL normalization if needed; Program/download/Run.
- Five-document restore and the inherited 41 candidate cases with the proven
  busy witness and retained full comparisons. Concurrent corrected four-
  connection read-only Dart observation, existing Part/phase traces and
  read-only TASK monitoring nominally every 100 ms from before download.
- Strict LIVE/nonempty desktop qualification: seven modules, three bus nodes,
  31 views with original quality/age and semantic checks. Remaining independent
  four-page/1,100-value comparison, 5,407-path idle equivalence, 5,407-value/
  seven-module acquisition and final scan if ready. Stop candidate work at its
  first failure.
- Pinned genealogy rollback, five exact original documents, 31 baseline cases,
  MANUAL/idle/logout, saved/live equality and final checks/preflight.

No new PLC write vectors. Fault/TASK-counter clears, clock changes, power/
vendor-state operations and Echo hard kills remain excluded. Preparation
authorizes no controller change. [AGENTS.md §3a](../../../AGENTS.md) requires
“current explicit authorization and an exact target check immediately before
use.” The prior approved session completed with verified rollback.

## Remaining plan

S4b strict desktop/full configuration/acquisition/final scan acceptance remains
open. Next come S5 Dart gateway/Web/installer, S6 legacy retirement/persistence/
events/capacity, and S7 physical/CIP Security including real I/O. Persistence
medium, gateway write posture per station, hardware and commit/push policy
remain owner decisions. V2/Part III remain inactive. Nothing is committed or
pushed. Evidence is append-only; credentials, ACD and SDK binaries are excluded
from archived payloads and remain hash-bound where required.
