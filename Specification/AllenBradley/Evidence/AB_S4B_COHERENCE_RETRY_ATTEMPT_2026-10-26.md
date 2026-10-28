# S4b paced coherence retry attempt — 2026-10-26

**All 41 candidate cases and 87 raw-read replays pass; the observer stops at
one Bad value after 587 preceding non-Bad samples. Genealogy and all 31
baseline/final checks are restored. Native S4b/desktop acceptance remain open.**

The owner answered “Approve guarded S4b paced coherence retry” to
`call_6af11f6634e14bc29c3a346b410be129:0`, authorizing the
[sealed preparation](AB_S4B_COHERENCE_RETRY_PREPARATION_2026-10-26.md).
Its original scope completed with verified rollback and approval is consumed.

## Passed

- Fresh service/listener/identity, MANUAL/idle/logout/document guards, backup,
  audits, download/Run, L5X read-back and external-access checks pass on
  Echo 601FC87B, 1756-L81E v38.011, 127.0.0.1 slot 0.
- ACD `7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF`,
  source `C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F`;
  measured offline Capacity remains 65% (2,066,100 /3,145,728 Blocks).
- Dart passed readiness and did not repeat the earlier missing-Good-root
  refusal. Its report contains 588 rows, including the final failed row.
  Reported fast age median/p95/max is 680.2575 /773.025 /931.960 ms; RPC
  median/p95/max is 691.9845 /785.968 /950.127 ms. Maximum returned accepted
  row window is 8,141 us, below the 10,000 us interval. There are 546 rows
  with no Bad or Uncertain values, 41 with payload-free Uncertain values,
  and the final row with one Bad value. These are not 588 accepted samples.
- **41/41 candidate checks**: 31 main, two Access, eight configuration/store.
  Changes and policy were restored; the isolated store was left empty.
  **87/87 paired comparisons** independently replay from raw controller
  bytes to the same values/types and stored oracle across 4,799-5,407
  logical occupied paths. This includes the PLC view, not Dart page acceptance.
- Pinned genealogy downloaded from a checked copy; its original remains
  `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
  Original five host documents, **31/31 baseline checks**, policy, MANUAL
  cleanup, final checks, preflight equality and baseline timing pass.
- Final state: Run, not faulted, scanning, MANUAL/idle, logged out, not restoring,
  original policy and five saved/live documents equal. No dumps, fault clears,
  clock changes, power/vendor-state operations or Echo hard kills.

## Failed and diagnostic limits

After 413,644 ms the observer reported “Bad value in cyclic qualification”.
Its final row has one Bad value and no Uncertain values. Unlike a root refusal,
this branch did not retain its failed full snapshot, so the exact Bad path and
metadata are not recorded. Retained snapshots identify **ShiftHistoryTruncated**
as the pending Uncertain slow row immediately before the failure. Its last
captured age is 7,708.869 ms. Its recorded failed attempts show a changed
counter followed by two odd pre-counters; no payload was accepted. The final
counts/ages are consistent with this row expiring, but the missing last map
prevents an unqualified claim of exact Bad-path identity.

Code inspection establishes an independent mismatch: `CipReadPlan.snapshot`
expires slow data at `slowIntervalUs * 2` = **10,000 ms**, while the same
session publishes **slowExpiryMs=15,000**. It also does not apply its advertised
Good cutoffs itself; the repository ages the data later. Correcting the
planner to its already declared profile is required, without increasing that
profile or renewing cached sample times. The exact failure map must be saved
before another test so future branches do not lose their diagnostic evidence.

An additional read-only pinned-publication diagnostic ran during the original
approved session after the observer stopped. It made zero writes and captured
33 samples without a Bad leaf before rollback stopped the publisher. It ended
with “No Good cyclic CIP sample”. That interruption is retained as a failed
diagnostic run, not acceptance or evidence of the original Bad leaf.

The inherited fixture completed its approved cases/restoration before the
wrapper collected the observer failure and rolled back. Dart all-bank pages,
detail reads, candidate idle equivalence, generic acquisition and candidate
native scan were not reached; desktop acceptance remains open. All sources
remain unchanged at this seal except the SDK-saved working ACD. Preparation
results remain 2,336 AB /74 root /641 Flutter (12 skipped), Windows/analyzer,
both v38 builds/read-backs and 65% Capacity.

V2/Part III are inactive. S4b desktop, S5-S7 and S3 physical I/O proof remain.
Nothing is committed or pushed; no credentials or ACD binaries are archived.
