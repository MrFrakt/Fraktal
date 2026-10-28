# S4b legacy Part-read diagnostic preparation — 2026-10-27

**A same-image diagnostic session is prepared and not authorized.** The
[parallel-reader attempt](AB_S4B_PARALLEL_READER_ATTEMPT_2026-10-27.md) completes
**25/41 cases**: 15 main, two Access and eight configuration/set-store. Its
**53 completed paired captures** independently replay with exact values/types
on 4,799–5,407 paths. The legacy Part reader then refuses the SFC adopted-fault
record: `part snapshot changed during every bounded read`. The original
three-attempt proof remains enforced. The full 41-case/87-pair gate is not met.

The four-connection Dart observer completes **1,288 entirely Good samples**,
zero Bad/Uncertain, four configuration page queries and targeted details. Age
median/p95/max is **295.514 /385.779 /493.517 ms**; maximum accepted row window
is **9,965 us** against the published 10,000 us interval. This partial workload
does not establish a controlled performance comparison with earlier runs.
Desktop, independent page comparison, idle/generic acquisition and final scan
are not reached. TASK monitoring records **8,994 us maximum /zero overlaps**
through 4,303 candidate observations. Genealogy, the five exact original
documents, **31/31 baseline cases**, policy, MANUAL/idle/logout and all final
checks/preflight are restored. That session's authorization is consumed.

## What changes, and what remains unknown

The failing Part acquisition did not record its before/body/after counters or
per-read timing. It does not establish contention, a counter defect or a PLC
publisher cause. The Part reader reads a whole legacy structure for each
before/body/after call and requires matching even revisions. This diagnostic
keeps that original function and all its requests, attempts, projection and
rejection rules unchanged.

A session-only context wraps its communication object to record **only** the
first two DINT schema/revision words, attempt/phase and per-read/call timing.
It forwards every request exactly once and rethrows the original refusal.
The trace is written after each Part-read call; no UID, Part payload or PIN
is retained. Existing output paths are refused. The original function is
restored when the context exits. Logging adds overhead; its timings include
trace work. **This session may reproduce the refusal.** It does not promise
acceptance or change any production PLC/HMI code.

The generic client retains four read-only connections pinned to one serial,
one outstanding request per socket, complete row leases, count barriers and
revision ordering. Fast **1/3 s** and slow **7.5/15 s** Good/expiry limits,
conservative complete-sample and leaf ages, **20 attempts /one-second** row
budget and proof windows remain unchanged. No extra PLC requests, retries,
write vectors, quality or acceptance rules are introduced by the tracer.

## Exact image and proposed scope

- Local Echo **601FC87B**, 1756-L81E **38.011**, **127.0.0.1 slot 0**.
- ACD: `30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`.
- Source: `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`.
- Same exact-image Capacity: **2,066,212 used /1,079,516 available /
  3,145,728 total Blocks (65%)**; physical fit is not covered.
- Runner: `C:/work/fraktal-ab-s4b-partdiag-20261027/session_01/qualification_session_v2.py`.

Fresh service/listener/identity/mode/fault/session/idle guards and backup;
guarded MANUAL normalization if needed; Program/download/Run; five-document
restore and the inherited **41 candidate cases**, with the four-connection
read-only observer and Part-read tracing. Read-only TASK monitoring at nominal
**100 ms** begins before download. Strict live desktop follows only if the
fixture passes. If ready, remaining configuration/detail, independent page
comparisons, idle equivalence, generic acquisition and final scan follow.
Candidate work stops at its first failure. Then pinned genealogy rollback,
the exact original host documents, five-document restore, **31 baseline cases**,
MANUAL cleanup and every final check/preflight. Target/fault/idle/session
guards remain active during rollback.

No added PLC write vectors, fault/TASK-counter clears, clock changes, power/
vendor-state operations or Echo hard kills. The original genealogy ACD
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084` is never opened;
rollback downloads its hash-checked copy. Credentials are never archived.

## Gates and provenance

- **Six new tracing tests pass**: exact request/argument/attempt and return
  preservation, nine-read refusal with identical exception, network failure,
  evidence overwrite refusal, payload exclusion and per-call phase numbering.
- All shipping HMI inputs and the **318-input** mirror remain unchanged from
  the parallel-reader package: **660 HMI tests /12 skipped**, analyzer, Windows
  debug build and enforced lockfile transfer by hashes, using Flutter
  **3.47.5 /Dart 3.13.4**. These gates are transferred, not rerun compiler claims.
- All **373 PLC/gate bindings** remain unchanged: **2,339 AB tests**, both
  v38 build/read-back/access/SDK gates, 15 byte-identical prior stage images
  and exact-image 65% Capacity transfer by hashes.
- Fresh SDK build has zero warnings/errors. **16 authorization refusals**,
  missing-approval parent/SDK, **eight workflow checks**, **six readiness
  checks** and both read-only helper refusals pass without controller access.
  Spec/contracts/strict consistency, **74 root tests** and whitespace pass.
- The only prepared fixture change is its Part-tracing context and new helper.
  All other write/rollback helpers are unchanged apart from session paths.
  Private Dart maps stay pinned. Prior evidence seals verify. No authorization,
  start, backup, deploy or Part-trace output exists in this new session.
  ACD/SDK binaries are hash-bound and excluded from the archive.

Next: run this diagnostic after fresh approval. Use actual counter/timing
records to decide any correction offline; complete acceptance only if every
unchanged gate passes. Then restore genealogy and all baseline/final checks.
S4b remains open. S5 gateway/Web/installer, S6 classified legacy migration/
retirement/persistence/events/capacity and S7 physical/CIP Security including
real I/O remain. Persistence medium, gateway write posture per station, physical
hardware and commit/push policy still require owner decisions. V2/Part III
remain inactive. Nothing is committed or pushed.

[AGENTS.md §3a](../../../AGENTS.md) requires “current explicit authorization
and an exact target check immediately before use.” The parallel-reader session
ended with verified rollback and its approval is consumed. This fresh diagnostic
session therefore needs current approval, despite the unchanged image and
unchanged write vectors.
