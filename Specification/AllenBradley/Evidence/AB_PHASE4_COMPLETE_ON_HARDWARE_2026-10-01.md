# Fraktal/AB — Phase 4 complete on the bench: every gate passes on press43

**Result:** press43 was downloaded. **Phase 1 passed 7/7, Phase 2 6/6, Phase 3
8/8, Phase 4 11/11, and §146 parity 25/25.** Defect D8 is closed: an operator
reset no longer restarts the press.

**Date:** 2026-10-01 · **Repository revision:** `23c72f3`
**Raw record:** [`AB_PHASE4_COMPLETE_ON_HARDWARE_2026-10-01.json`](AB_PHASE4_COMPLETE_ON_HARDWARE_2026-10-01.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press43.L5X`: `ContentHash B8A2BE7BB9D19ECB` |
| How press43 is known | its hash equals press42's (one line of logic). Phase 1's reset rows passed here and failed on press42. |

## 1. D8, closed

After an adopted CYL_NOT_EXTENDED and its blocking alarm:

| | press42 | press43 |
|---|---|---|
| START before the reset | refused; report `unitNotReady`, `manualReset` | same |
| After OPERATOR_RESET | the event closed into the ring; **the press running again by itself** | the event closed into the ring; `Running` 0, nothing blocking, no diagnostic |
| START after the reset | refused, `unitNotReady` | **accepted** |

## 2. Everything else

| Gate | Result |
|---|---|
| §146 parity | 25/25. ST 970.4 ms, SFC 970.1 ms, LD 972.1 ms; each runs 3/3 door, 3/3 ram and 2/2 slide strokes; OrderFail 0 |
| Phase 2 (flow chart) | 6/6 |
| Phase 3 (modules, stall, dwell, air) | 8/8 |
| Phase 4 (manual commands, interlocks, release reports) | 11/11 |

Phase 4 of the parity audit, act-or-explain, is complete on hardware:

- TC3's manual commands and collision interlocks;
- the Start, Manual and Action release reports;
- Start gated by its own report;
- a reset that leaves the press restartable and not restarted.
