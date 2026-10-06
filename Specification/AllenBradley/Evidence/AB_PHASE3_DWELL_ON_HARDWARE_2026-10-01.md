# Fraktal/AB — the press dwell pauses on the bench (TC3's N220)

**Result:** releasing the two-hand inside the dwell now pauses the dwell on its
named condition, with no fault and no hold, and pressing again finishes only
the time that remained. **press38 was downloaded. §146 parity passed 22 of 22,
including the new dwell rows in ST, SFC and LD, and Phases 1, 2 and 3 passed
7/7, 6/6 and 8/8.**

**Date:** 2026-10-01 · **Repository revision:** `63e2195`
**Raw record:** [`AB_PHASE3_DWELL_ON_HARDWARE_2026-10-01.json`](AB_PHASE3_DWELL_ON_HARDWARE_2026-10-01.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press38.L5X`: `ContentHash 9BD371752899748A`, `ConfigRevision 10212209` |
| Declaration | the same hash, so the controller matches the repository |

## 1. What changed on the controller

TC3's N220 is a named wait, `twoHandHeldDuringPress`. AB's dwell used to read
the step clock, which counts a pause. A delay now keeps its own clock,
`Chart.DelayMs`. It is zeroed on entry and advanced only on scans its
conditions hold, in all three renditions. A plain delay, N170's settle, is
the same clock with nothing to wait for.

## 2. §146 parity: 22 of 22

| | ST | SFC | LD |
|---|---|---|---|
| Cycle completes, `OrderFail` 0, parked at N100 | 962.2 ms | 742.1 ms | 944.3 ms |
| HELD at N180 on 12001, self-resumed to 200 | ✓ | ✓ | ✓ |
| **Dwell released: paused at N220** | ✓ | ✓ | ✓ |
| `CondOk[0]` / `StallReason` while paused | 0 / 12011 | same | same |
| `Error` / `Held` while paused | 0 / 0 | same | same |
| `DelayMs` across the 1.5 s release | 0 → 0 | same | same |
| Dwell served once pressed again | 300 ms of 300 | same | same |
| The step's own duration (`LastMs[220]`) | 1810 ms | same | same |
| Aborted cycle stands down to step 0 | ✓ | ✓ | ✓ |

The parity walk releases as soon as the ram presses. In all three renditions
the release landed before the dwell had run, so these rows show a dwell paused
from its first scan. The step lasted 1810 ms and only 300 ms of it counted as
dwell.

## 3. Released part-way (`fraktal_ab_phase3_execute.py`, new row)

This row waits until some of the dwell has run, then releases. It is the
operator's case, and it is the one that shows the remainder.

| | Observed |
|---|---|
| Released at | `DelayMs` 10 of 300 |
| 1.5 s later | `DelayMs` still 10; step 220; `Error` 0, `Held` 0 |
| Published record | `CurrentStep/Conds[1]`: `project.condition.twoHandHeldDuringPress`, `Ok` false |
| Pressed again | resumed to 230 with `DelayMs` 300: 290 ms more, not 0 and not 300 |

The row ran from the working tree and is committed with this record. Phase 3's
first run on press38, without it, passed its other 7 rows.

## 4. What this does not show

- **The ram's force.** TC3 also withdraws the ram's valve during the release
  and restores it after. AB's cylinder simulates position, not a valve, so
  there is no output to withdraw.
- **A stall during a long release.** While paused, `DiagReason` stays 0 until
  the 30 s `StallTime`. TC3 arms its watchdog at the step's `ExpectedTime`
  (the dwell) instead. That difference is recorded in the parity audit and
  not addressed by this build.
