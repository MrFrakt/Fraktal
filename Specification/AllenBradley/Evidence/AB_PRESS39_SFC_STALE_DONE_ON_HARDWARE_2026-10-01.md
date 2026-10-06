# Fraktal/AB — press39 on the bench, and the SFC rendition that did not press

**Result:** press39 brought in TC3's N180 abandon, the two-hand policy and
per-step stall times. ST and LD pass every row. The SFC rendition failed the
new abandon row, and the cause is older than press39. **Since the SFC chart
was first generated, it has skipped a stroke whenever a module was still Done
from its previous command.** On every SFC cycle the door did not close at N180,
the ram did not press at N200 and the slide did not go out at N244. The parity
harness compared only which steps were entered, so it did not see this.
press40 fixes it.

**Date:** 2026-10-01 · **Repository revision:** `20eb47c`
**Raw record:** [`AB_PRESS39_SFC_STALE_DONE_ON_HARDWARE_2026-10-01.json`](AB_PRESS39_SFC_STALE_DONE_ON_HARDWARE_2026-10-01.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press39.L5X`: `ContentHash 57BE3FF0681AF466`, `ConfigRevision 5750335` |

## 1. What press39 shows on the controller

| Run | Result |
|---|---|
| §146 parity, as committed | 20 of 22; `release_abandons_the_close_sfc` and `abandon_matches_st_sfc` fail |
| §146 parity, with per-module command counts | 22 of 25; the same two, plus `commands_complete_sfc` |
| Phase 1 / 2 / 3 (ST) | 7/7, 6/6, 8/8 |

ST and LD, on the controller:

- **N180 abandon.** A release at the close is one `TWO_HAND_RELEASED`
  (12001) warning from the Unit itself, on N180's row, with no error. Then
  N185 and N190 run once each, and the chain rests at N100 with the start
  latch dropped. N200 is not entered.
- **The dwell.** Released, it is reported stalled after its expected time
  (`StepTimedOut` 1, `DiagReason` 2005). It then serves exactly 300 ms once
  pressed again. Phase 3's part-way release also passes, with `DiagReason`
  2005.

## 2. The SFC defect

In the abandon walk, SFC entered N180 once and went straight to N200,
reporting no warning. The door had not been released, so the close was never
commanded. The new command-count row shows the same in a plain cycle:

| One AUTO cycle | Door | PressRam | PartSlide | Cycle |
|---|---|---|---|---|
| ST | 3 run, 3 done | 3 / 3 | 2 / 2 | 967 ms |
| **SFC** | **2 / 2** | **2 / 2** | **1 / 1** | **756 ms** |
| LD | 3 / 3 | 3 / 3 | 2 / 2 | 940 ms |

**Cause.** A commanding step's SFC transition was `Done <> 0`, with no entry
guard. The SFC action also never dropped `Execute` when a command completed.
A module therefore stayed Done after its command, and the next SFC step that
commanded it found that Done true on its entry scan. The transition fired
before the module had seen a new command:

- the door, opened at N130, was still Done at N180;
- the ram, raised at N110, was still Done at N200;
- the slide, moved in at N150, was still Done at N244.

ST and LD read the module only after the entry scan, and drop `Execute` on
Done. They were never affected.

**Why it was not seen.** The parity harness compared entry counts per step,
and SFC entered every step exactly as ST did. The SFC cycle was always about
210 ms faster than ST and LD (743 vs 963 ms on press37). That is three skipped
strokes, and it was read as a property of the language.

## 3. The fix (press40)

- **Same transitions as ST and LD.** The SFC transitions of commanding steps
  read the module only after the entry scan.
- **Same action shape as ST.** The SFC action now has ST's step body: drop
  `Execute` on entry, command after that, and drop `Execute` again on Done.
  Completion marks and errors go in the same block.
- **The model now checks the plant.**
  `test_fraktal_ab_rendition_cycle` runs one AUTO cycle per rendition against
  the generated module layer and requires the same commands, completions,
  motions and step order as ST. All three renditions now take 97 scans
  (970 ms), which matches ST on the controller. A second test enters N110,
  N150, N180 and N200 with the module still Done, and requires every
  rendition to command it afresh. Each half of the fix, reverted on its own,
  fails these tests.
- **The controller check is the plant's too.** The parity harness now counts,
  module by module, the commands each rendition ran and completed in a cycle
  (`commands_complete_*`).

press40's ContentHash equals press39's. The hash covers the published
contract and not the logic, so the controller's hash cannot tell the two
apart. `commands_complete_sfc` can.
