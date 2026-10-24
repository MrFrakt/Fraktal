# S3h observation-frame runtime — 2026-10-24

**S3h exit passes on Echo. Genealogy is restored.** The owner approved this
session in chat on 2026-10-24 (“yes i approve”), naming Echo `601FC87B` and ACD
`E07C419651A2C6A785D150CAA0BB1894A57CB4453036A0CC2EF2FA8413649745`. The
approved scope was backup, download, the 41 candidate checks reading the frame,
rollback to genealogy and the 31 baseline checks, excluding fault clears and
clock changes. Every stage ran once, in order, and exited 0. There are no
failed or extra runs in this session.

| Result | Measured scope |
|---|---|
| Guard / dumps before | Exact identity 0x601fc87b, 38.11, Emulate 5580; not faulted; Remote; listener owned by the emulator. No dump files |
| MANUAL normalization (initial) | Already MANUAL=1; no write |
| Preflight / backup | Fresh preflight; upload `80114688…13C65F`; SDK log clean; tag access equals the sealed genealogy reference |
| Candidate download / SDK audit / read-back / access | Pass / pass / equivalent (55 bodies, 40,885 values) / pass |
| Candidate checks | **41 / 41 pass**: 31 base rows, 2 Access rows, 8 configuration rows |
| Paired captures | 87 fixture pairs plus idle equivalence; every one through the frame, equal at 3,342–3,950 typed paths with 0 differences |
| Coherence proof | Unchanged `stable_scan_pair`; accepted in 2–29 of 100 polls; the accepted frame's source scan was 1–6 scans after its capture request |
| Independent replay | All 88 pairs re-decode from native bytes, re-derive legacy inputs and reference projection, and every record slice equals the frame bytes |
| Generic acquisition | 3,950 values, 7 modules, not truncated, read only |
| Native records | Root / definitions / alarm metadata 133,744 / 7,308 / 16,616 bytes; frame 172,088 bytes in 44 fragments |
| Candidate TASK (20 samples) | LastScan median 872 µs (872–924); cumulative max 8,402 µs; zero overlaps |
| Rollback | Hash-checked genealogy copy downloaded; SDK log clean; tag access equals the sealed reference |
| Baseline regressions | **31 / 31 pass** |
| Final state | MANUAL normalized after the candidate and after the baseline, each with the existing LOGIN, SET_MODE(1) and LOGOUT mailbox frames. Final checks: scanning, MANUAL, idle, logged out, not restoring, five saved/live documents equal, policy restored. Preflight equal |
| Baseline TASK (20 samples) | LastScan median 99 µs; cumulative max 1,167 µs; zero overlaps |
| Dumps after / fault clears / clock changes / hard kills | None / 0 / 0 / 0 |

The candidate cumulative maximum, 8,402 µs, equals the reading recorded after
the C6 image's failed capture. So the observed maximum is not attributable to
the frame copy. The copy's own cost is not isolated: 20 LastScan samples at
50 ms intervals ranged 872–924 µs. Every scan stayed below the 10 ms period,
with zero overlaps.

The held-out Capacity forecast from the nine prior observations estimated
2,720,877 Blocks against 2,680,132 measured (+40,745, +1.5203%). Its planning
budget, 3,435,201, exceeds the 3,145,728 total, so the next stage's forecast
already warns. Measured Capacity remains the gate.

## Scope

This accepts S3h at the genealogy/Echo scope: the 36 approved type
corrections and 242 exact added paths, read through the Part III §3.13
PLC-latched frame. Physical controller, CIP Security, the press declaration,
the 149 remaining inventory paths, S4–S7 and V2 activation remain separate.
The frame is a migration instrument; it is removed with the legacy contexts at
S6 and is not a shipping surface. This session's approval is consumed; any
further controller change needs new current approval.

Workspace: `C:/work/fraktal-ab-s3h-20261024/frame_b7a501a104b448438e1e3566840fa12f`.
Runtime: `C:/work/fraktal-ab-s3h-20261024/runtime_f3cd2b95b75845c99ab24b3f81f91c0f`.
Append-only payload: [manifest](AB_S3H_CANONICAL_OBSERVATION_FRAME_RUNTIME_2026-10-24/manifest.json).
It also holds the two packaging runs that failed before the preparation seal
(hash-case convention, missing log). No ACD binary or credential is archived.
No commit or push.
