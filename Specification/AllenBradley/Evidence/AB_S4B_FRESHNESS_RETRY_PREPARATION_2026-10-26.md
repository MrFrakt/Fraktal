# S4b freshness-profile retry preparation — 2026-10-26

**The profile conformance correction is prepared offline; the new session is
not authorized.** The [paced attempt](AB_S4B_COHERENCE_RETRY_ATTEMPT_2026-10-26.md)
passed 41 cases and 87 raw-read replays, but stopped at one Bad value after
587 preceding non-Bad rows. Genealogy, original documents and all 31 baseline/
final checks are restored. S4b native/desktop acceptance remain open.

## Exact image and preserved operation scope

- Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0.
- ACD `7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF`.
- Source `C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F`.
- Capacity **2,066,100 used /1,079,628 available /3,145,728 total Blocks
  (65%)**. PLC source/image, both v38 builds/read-backs and access audits
  remain unchanged.
- Runner: `C:/work/fraktal-ab-s4b-20261025/retry_freshness_01/qualification_session_v2.py`.

The scope remains fresh guards/backup; guarded MANUAL normalization;
Program/download/Run; read-only Dart readiness; five-document restore and
41 inherited candidate cases with concurrent read-only observation; all-bank
configuration/detail reads, equivalence/acquisition/scan; then pinned genealogy
rollback, exact original host documents, 31 baseline cases, MANUAL cleanup,
final checks and preflight. The fixed fixture keeps its restoration path if
the observer stops. No new write vectors, fault clears, clock changes,
power/vendor-state operations or Echo hard kills. A Bad value or unavailable
root still fails qualification; no refusal is counted as a Good sample.

## Verified mismatch and correction

The prior observer reported one Bad value but its Bad branch did not retain
the full rejected map. The preceding retained snapshots identify
ShiftHistoryTruncated as a pending Uncertain slow row at age 7,708.869 ms.
The exact final Bad path is therefore inferential. The supplementary read-only
capture ended as rollback stopped the publisher and did not reproduce that leaf.

Independently, the frozen source proves a mismatch: slow expiry was implemented
as twice the five-second heartbeat (**10 seconds**) while the session declared
**15 seconds**. Clock-controlled tests fail on the frozen implementation at
11 seconds, at the Good boundaries and for retained excluded-group tiers.
They pass after the correction.

One authoritative profile now drives both planner and envelope, with every
previously declared value unchanged: poll 250 ms, fast Good/expiry 1,000/3,000 ms,
slow heartbeat 5,000 ms and Good/expiry 7,500/15,000 ms. Good cutoffs remove
payloads; expiry is enforced at the exact boundary. Existing non-Good quality
is never promoted and cached sample ages never renew without a successful
read. Retained excluded groups use the slow profile, as OPCUA_TRANSPORT
specifies. Types, paths, request selection, equal-even proof/window, strict
root checks, three-attempt/one-second guard and bounded odd-counter pacing
remain unchanged. No advertised budget is increased.

The qualification tool now retains the entire rejected Bad snapshot and all
affected paths/metadata before stopping. The existing root-failure capture is
unchanged. Four new tests cover slow expiry, both Good cutoffs, excluded-group
retention and Bad diagnostics. Existing clock, torn/frozen publisher, timeout,
payload absence, stale shell and command-refusal tests remain intact.

## Gates and sealed inputs

All **316 active HMI inputs** match the isolated copy.
Pinned **Flutter 3.47.5 /Dart 3.13.4**: enforced lockfile, rebuilt Windows debug,
analyzer and **645 passed /12 skipped**. No dependency or lockfile change;
the private runtime package map is frozen independently of the IDE's generated
map. **373 unchanged PLC/gate file bindings** preserve the 2,336-test
AB result. All 74 root tests, spec/contracts, strict consistency and whitespace
gates pass again. The fresh SDK builds with zero warnings/errors; 16 negative
authorization cases and missing-approval CLI/SDK checks pass without I/O.

No current authorization, backup, session marker or deployment attempt exists
in this fresh workspace. **80 prior seals /23972 artifacts** verify
unchanged. Failed runs remain, including the earlier sealing substitution guard
and the intentionally failing pre-correction tests. Credentials and ACD binaries
are excluded. V2/Part III remain inactive. S4b native/desktop, S5-S7 and S3
physical I/O acceptance remain open. Nothing is committed or pushed.

[AGENTS.md §3a](../../../AGENTS.md) requires “current explicit authorization
and an exact target check immediately before use.” The previous approved scope
completed with verified rollback; a fresh download/session needs approval.
