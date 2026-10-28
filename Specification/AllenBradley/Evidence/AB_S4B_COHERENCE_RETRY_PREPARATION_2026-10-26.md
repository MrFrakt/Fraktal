# S4b paced coherence retry preparation — 2026-10-26

**A bounded pacing correction and failed-attempt diagnostics are ready offline;
the new controller session is not authorized.** The [lookup attempt](AB_S4B_LOOKUP_RETRY_ATTEMPT_2026-10-26.md)
passed 41 candidate cases and 87 independent paired replays, but its Dart
observer stopped after 140 fresh snapshots on an Uncertain root Status row.
Genealogy, the original documents, 31 baseline and all final checks are restored.
S4b native/desktop acceptance remain open; the previous approval is consumed.

## Exact image and scope

- Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0.
- Prepared ACD `7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF`.
- Generated source `C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F`.
- Offline Capacity **2,066,100 used /1,079,628 available /3,145,728 total
  Blocks (65%)**. PLC source/image, both v38 builds/read-backs and access
  audits are unchanged.
- Runner: `C:/work/fraktal-ab-s4b-20261025/retry_coherence_01/qualification_session_v2.py`.

The scope remains fresh guards/backup; guarded MANUAL normalization;
Program/download/Run; read-only Dart readiness before five-document restore
and the inherited 41 candidate cases; concurrent read-only observation,
all-bank configuration/detail reads, equivalence/acquisition/scan; then pinned
genealogy rollback, exact original host documents, 31 baseline cases, MANUAL
cleanup, final checks and preflight. The wrapper rejects a failed observer;
the separate fixed fixture retains its own restoration path. No new mailbox
vectors, controller fault clears, clock changes, power/vendor-state operations
or Echo hard kills. The strict root readiness/qualification checks are unchanged.

## Correction and evidence limits

The lookup fix produced 140 native snapshots with age median 621.756 ms,
maximum 745.063 ms and no Bad values. At the next snapshot the root Status
row was payload-free Uncertain (`coherence-unavailable`), so qualification
failed. Its failed attempt counters were not captured; odd pre-counters,
changing tokens and excessive windows cannot be distinguished in that record.

A deterministic offline publisher that completes on a later event-loop turn
reproduces exhausted rapid retries. That regression fails on the sealed code
and passes with bounded pacing. After an odd pre-counter the client waits at
most **1 ms**, capped by the manifest's mutation interval, inside the existing
total deadline. It then uses the same guarded read rule. It does not wait after
its final allowed attempt. **Three attempts and the one-second deadline remain
unchanged**, as do equal-even tokens, window shorter than mutation period,
progress, identity, type, freshness and read-only rules. No stale/torn bytes
are accepted, no timestamp is renewed on refusal, and an unavailable root
still fails qualification. This fixes a reproduced retry weakness; a native
retry must establish its effect on the recorded Echo workload.

For previously sampled rows that become Uncertain, DataValue diagnostics now
include the actual failed attempt count, total acquisition time and a bounded
counter/window trace. Metadata preserves prior accepted sample ages and omits
the payload. At most one trace row per attempt is retained; successful payloads
still require the original proof. Three new tests cover later-turn completion,
failed counter traces and timeout during the new wait. Existing planner tests
also prove payload absence, metadata delivery and unchanged ages.

## Gates

The **316 active HMI inputs** match the isolated verification
copy. Pinned **Flutter 3.47.5 /Dart 3.13.4**: **641 passed, 12 skipped**,
analyzer, enforced lockfile and rebuilt Windows debug binary pass. The original
IDE-generated package map is untouched; the runner has a frozen private map.
No dependencies or lockfile change. **373 unchanged PLC/gate files**
preserve the 2,336-test AB result; all 74 root tests, AB spec/contracts, strict
consistency and whitespace gates pass again. The SDK helper builds with zero
warnings/errors; all 16 authorization refusal cases and missing-approval CLI/
SDK checks pass without controller access.

No authorization, session marker, backup or deployment attempt exists here.
**78 prior seals /22993 artifacts** verify unchanged, including every
failed run and the raw native comparisons. Credentials and ACD binaries are
excluded. V2/Part III remain inactive; S4b desktop, S5-S7 and S3 physical I/O
acceptance remain open. Nothing is committed or pushed.

[AGENTS.md §3a](../../../AGENTS.md) requires “current explicit authorization
and an exact target check immediately before use.” The previous approved
scope completed with verified rollback; this fresh session needs approval.
