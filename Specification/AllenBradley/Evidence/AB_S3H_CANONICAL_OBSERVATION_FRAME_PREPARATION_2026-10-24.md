# S3h observation-frame preparation — 2026-10-24

**Offline gates pass for a new S3h image whose PLC latches the oracle's paired
records. No download, mode change or tag write has run. Native acceptance and
the authorization for it are pending.** Target remains local Echo `601FC87B`,
1756-L81E v38.011, 127.0.0.1 slot 0.

## Why the acquisition changed

Part III §3.13 binds every coherence-guarded snapshot: *"Any data set guarded
by a coherence token **shall** have a mutation interval longer than its guarded
read window, or it **shall** be double-buffered on the PLC side. Retry is not a
substitute for either."* The S3h pair broke that rule. Its 133,744-byte
canonical root plus 30 legacy owner records (32 reads) changed every 10 ms scan.
The [diagnostic run](AB_S3H_CANONICAL_DIAGNOSTIC_RUNTIME_2026-10-24.md) measured
8,690 / 10,649 / 15,871 µs opening-to-closing windows against an even gap of
about 8.9 ms. Larger packets, eight sockets and immediate send had already
been excluded. The owner asked for an evaluation against the Core §1.1
objectives and a decision. The PLC-side frame was chosen under six
conditions, all implemented here.

| Condition | Implementation |
|---|---|
| Migration images only | `canonical_observation_period_ms`, default 0. It is valid only at S3h (stage 10); the S3h candidate sets 50 ms. It is removed with the legacy contexts at S6 |
| One list | `fraktal_ab_canonical_observation.legacy_sources` names each record through its owning generator helper. The frame Template member names are the tag names, and the oracle refuses any read outside the frame or any member it did not read |
| Surface | Two Read Only tags, `FRK_Press_ObservationGeneration` and `FRK_Press_ObservationFrame`. No top-level `Status`, no manifest row, no write |
| Timing | Latched when `ScanCount MOD 5 = 0`, after the canonical section's final even mark. The read starts on a fresh frame edge, so a read of at most 16 ms fits a frame that holds for about 48 ms |
| Proof unchanged | `stable_scan_pair` runs unmodified (100 polls, five seconds, fresh start), applied to the frame generation. Added checks only reject: source generation at or after the live generation at the capture request, an even completed scan, and a fragment revision equal to the cached definitions |
| Fidelity and gates | Same-type `CPS(…,1)` per record, element by element for the model array. Executed-ST tests check copy, period, independence and generation recovery. Every gate below was rerun for the new image |

Comparisons, value/type rules, approved corrections, task period, poll budget,
four sockets and one outstanding read per socket are unchanged. The odd mark
is derived (`g - (g MOD 2) + 1`), so an interrupted copy is never followed by
a frame that reads as complete without a whole copy in between. Negative or
exhausted generations restart at 1/2.

## Results

| Gate | Exact outcome |
|---|---|
| Focused observation tests | 9 pass: emission gating, validation, Template/access/root/manifest shape, executed latch and recovery, reader layout refusals, proof ordering, stale/odd/revision refusals |
| AB discovery suite | 2,158 pass in 260.822 s (2,149 earlier + 9) |
| Root suites / spec / contracts / strict consistency | 74 pass / pass / pass / 0 errors, 0 warnings |
| Recorded read set | Frame legacy sources equal the oracle reads in all 64 accepted native pairs of the diagnostic run |
| Frame off | Regeneration reproduces the earlier S3h source `E83B9A2C…567315` byte for byte |
| Prior stages | Eight accepted stage images and their sealed generic snapshot replays exact |
| Candidate source | `BF456BCA68745C39D0903D0DE96B9B8AD4EC9DC502E809F38DA82599D2EFB1F2`; +3,758 ST bytes, +45 terminators |
| v38 EchoController / PhysicalController | Import 0 warnings / 0 errors; build accepted; strict read-back equivalent (55 bodies, 40,885 initial values, 21 SFC steps) |
| Effective access | Both targets and the prepared read-back pass: 144 tags, 91 canonical types, frame members exact, no `Status`. The first prepared run printed to the console only; `prepared_access_02` repeats it with a log |
| Prepared ACD | Offline-only helper: import/build/save, reopen/build/save, read-back equivalent. SHA-256 `E07C419651A2C6A785D150CAA0BB1894A57CB4453036A0CC2EF2FA8413649745` |
| Automatic Studio Capacity | 2,680,132 used / 465,596 available / 3,145,728 total Blocks (85%), two samples, review process closed |
| Capacity delta | +178,412 Blocks over the C6 image (2,501,720) |
| Native S3h acceptance | Not run; needs current authorization |

The generator's declared-data total moves only +4 bytes because it does not
size structure tags; Capacity is the measurement. The frame grows with the
canonical root in later stages, so Capacity is the gate to watch. Scan time is
not measured offline: every fifth scan carries one about 172 KB copy, and the
candidate's 20-sample TASK gate measures it.

## What is not claimed

No native S3h equivalence, TASK timing, rollback or acceptance. The frame does
not address the S4/S5 generic client. Core does not ask for whole-tier
coherence (Part III §3.13 specifies coherence per row), so that client needs
per-row tokens or single-request rows and must not reuse this frame. Copy
fidelity rests on same-type `CPS`, the executed-ST tests and the live generic
read that remains in the stage exit.

## Proposed native session

Same shape as every S3h attempt:

1. Guarded MANUAL normalization when needed, then fresh preflight and backup.
2. Program/download/Run of exactly `E07C4196…649745`, then five-document
   restore.
3. The inherited 41 candidate checks. Paired captures read the frame; there are
   no new write vectors.
4. Final generic/idle acquisition, sizes and the 20-sample TASK gate.
5. Hash-checked genealogy rollback, five-document restore and 31 baseline
   regressions.
6. MANUAL cleanup and final checks.

Fault clears, clock changes, hard kills, commit and push remain excluded. The
guarded backup/download/restore helper is built for that session and bound to
this ACD. The preparation helper here contains no communications path. The
[authorization template](AB_S3H_CANONICAL_OBSERVATION_FRAME_PREPARATION_2026-10-24/Preparation/authorization.template.json)
is false. AGENTS.md §3a requires current explicit approval for this exact
image.

Sources: 162 bindings (155 unchanged, four changed, three added). Work folder:
`C:/work/fraktal-ab-s3h-20261024/frame_b7a501a104b448438e1e3566840fa12f`.
Append-only payload: [manifest](AB_S3H_CANONICAL_OBSERVATION_FRAME_PREPARATION_2026-10-24/manifest.json).
No ACD binary or credential is archived. V2 remains inactive; no commit or push.
