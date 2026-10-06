# Fraktal/AB — press40 on the bench: the AUTO chain at parity with TC3

**Result:** press40 was downloaded. **§146 parity passed 25 of 25, and Phases
1, 2 and 3 passed 7/7, 6/6 and 8/8.** The SFC rendition now commands the plant
as ST and LD do (defect D7), and TC3's N180 abandon, two-hand policy and
per-step stall time pass in all three languages.

**Date:** 2026-10-01 · **Repository revision:** `67b6705`
**Raw record:** [`AB_PRESS40_ON_HARDWARE_2026-10-01.json`](AB_PRESS40_ON_HARDWARE_2026-10-01.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press40.L5X`: `ContentHash 57BE3FF0681AF466`, `ConfigRevision 5750335` |
| How press40 is known to be loaded | its hash equals press39's, since the hash covers the contract and not the logic. `commands_complete_sfc` passes here and failed on press39. |

## 1. One AUTO cycle per rendition

| | Door | PressRam | PartSlide | Cycle | OrderFail | Parked |
|---|---|---|---|---|---|---|
| ST | 3 run, 3 done | 3 / 3 | 2 / 2 | 966.6 ms | 0 | N100 |
| SFC | 3 / 3 | 3 / 3 | 2 / 2 | 976.5 ms | 0 | N100 |
| LD | 3 / 3 | 3 / 3 | 2 / 2 | 973.6 ms | 0 | N100 |

On press39 SFC ran 2, 2 and 1 and took 756 ms. The cycle now takes the time
the model predicts for all three, 97 scans. The step-entry traces still match
ST exactly.

## 2. TC3's N180: a release at the door close

In every rendition:

- one `TWO_HAND_RELEASED` (12001) warning, from the Unit itself, marked on
  N180's row;
- no error;
- N180, N185 and N190 entered once each, N200 not entered;
- resting at N100 with the start latch dropped.

## 3. TC3's N220 and the expected-time watchdog

In every rendition, a release while the ram presses pauses the dwell at
`DelayMs` 0 for 1.5 s. The step is reported stalled (`StepTimedOut` 1,
`DiagReason` 2005) because it has outrun its expected time. Once pressed
again it serves exactly 300 ms. The step lasted 1810 ms in ST and LD and
1830 ms in SFC.

## 4. Phases 1-3 (ST)

7/7, 6/6, 8/8. This includes Phase 3's part-way dwell release (paused,
stalled, then the remaining dwell served) and air lost under the door's
close (held, resumed).
