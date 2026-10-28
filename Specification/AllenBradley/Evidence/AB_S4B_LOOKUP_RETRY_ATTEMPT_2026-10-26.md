# S4b lookup retry attempt — 2026-10-26

**All 41 candidate cases and 87 paired comparisons pass; Dart qualification
fails after 140 snapshots on a root-row coherence refusal. Genealogy and all
31 baseline/final checks are restored. Native S4b/desktop acceptance remain open.**

The owner answered “Approve guarded S4b lookup retry” to
`call_2b13d9faea7945c9803fd0d2782b3c10:0`, authorizing the
[sealed lookup retry](AB_S4B_LOOKUP_RETRY_PREPARATION_2026-10-26.md).
Its scope completed with verified rollback and the approval is consumed.

## Passed

- Fresh identity/service/listener, MANUAL/idle/logout/document guards, backup,
  SDK audits, download/Run, L5X read-back and external-access audits pass on
  Echo 601FC87B, 1756-L81E v38.011, 127.0.0.1 slot 0.
- Image `7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF`,
  source `C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F`.
  Offline Capacity is unchanged at 65% (2,066,100 /3,145,728 Blocks).
- Dart passed discovery and readiness. Its 140 completed snapshots had fast
  sample age median **621.756 ms**, p95 **656.818 ms**, maximum **745.063 ms**.
  RPC median/p95/max were 633.216 /668.344 /795.073 ms. The largest accepted
  returned row window was **8,455 us**, below the declared 10,000 us interval.
  There were no Bad values in the completed samples. Fifty-nine samples
  contained payload-free Uncertain rows; those rows are not counted as Good.
- **41/41 candidate cases**: 31 main, two Access and eight configuration/store.
  Changes and policy were restored; the isolated set store was left empty.
  **87/87 paired comparisons** replay independently from saved native record
  bytes to the same canonical values/types and stored oracle. Logical occupied
  counts yield **4,799–5,407 paths** across these captures. This includes the
  PLC-owned configuration view; it does not establish Dart page acceptance.
- Pinned genealogy downloaded from a hash-checked copy; the original remains
  `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
  Exact original five host documents, **31/31 baseline cases**, policy,
  MANUAL cleanup, final checks, preflight and baseline timing pass.
- Final state: Run, not faulted, scanning, MANUAL/idle, logged out, not restoring,
  original policy and all five saved/live documents equal. No dumps, fault
  clears, clock changes, power/vendor-state operations or Echo hard kills.

## Failed and skipped

At the next snapshot the root Status row was Uncertain with reason
`coherence-unavailable` and no payload. Its prior sampled identity was
1,230.022 ms old; no value was retained as Good. Other Good fast samples were
603.998 ms old. The observer stopped with “missing or different root identity:
Press”. This differs from the previous whole-acquisition age failure: the
lookup correction allowed 140 snapshots to meet the original 1,000 ms limit.

The guard exhausts at most three attempts within one second. The rejected
DataValue preserves the prior successful row's timing fields, not the failed
attempt trace. The record therefore cannot distinguish odd pre-counters,
changing counters or overlong windows for this particular refusal. Do not
claim an exact retry-phase cause from these data.

The observer stopped first; the separate inherited fixture completed its
approved cases/restoration before the wrapper collected the observer failure
and entered rollback. This is not a passing concurrent-observation result.
Dart all-bank configuration pages, detail reads, candidate idle equivalence,
generic acquisition and candidate native scan were not reached. Desktop
rendering/connection acceptance remains open.

## Next

Reproduce the bounded retry behavior with a publishing counter that completes
on a later scheduling turn, retain useful failed-attempt diagnostics, and fix
any demonstrated retry starvation without increasing attempt/deadline budgets
or accepting torn/stale payloads. The exact native attempt pattern remains
unrecorded; a later native retry must confirm the correction. Every bound
source remains unchanged at this seal except the SDK-saved deployment ACD.
Offline 2,336 AB /74 root /638 Flutter tests (12 skipped), Windows build,
analyzer, both v38 builds and 65% Capacity remain preparation results.

V2/Part III are inactive. S4b desktop, S5-S7 and S3 physical I/O proof remain.
Nothing is committed or pushed; credentials and ACD binaries are not archived.
