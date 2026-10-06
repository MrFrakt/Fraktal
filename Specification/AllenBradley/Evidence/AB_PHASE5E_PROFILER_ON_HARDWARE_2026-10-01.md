# Fraktal/AB — TC3's cycle-time profile on the bench (Phase 5e)

**Result:** press48 was downloaded. **Phase 5 passed 19/19.** The bench profiled
a START's first cycle exactly as the model profiles it in every rendition.
Nothing regressed: §146 parity 25/25, and Phases 1-4 7/7, 6/6, 8/8 and 11/11.

**Date:** 2026-10-01 · **Repository revision:** `3770131`
**Raw record:** [`AB_PHASE5E_PROFILER_ON_HARDWARE_2026-10-01.json`](AB_PHASE5E_PROFILER_ON_HARDWARE_2026-10-01.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press48.L5X`: `ContentHash E526206F016FC47C`, `ConfigRevision 15017504` |
| Manifest | read back whole and coherent, 51,064 bytes in 148.9 ms, every row equal to the declaration |
| Gateway | `/healthz` ready, PLC ready |

## 1. One cycle, read where the HMI reads it (`Press/Profiler`)

| | Observed |
|---|---|
| Waterfall | `0, 100, 110, 130, 150, 170, 180, 200, 220, 230, 240, 242, 244, 999`: the init step, the operator's start, the happy path and the finish step, in order. This is the sequence the model produces from a START in ST, SFC and LD |
| N170 transfer settle | expected **200 ms** (the recipe's `TransferSettleMs`), took **210 ms** |
| N220 press dwell | expected **300 ms** (`PressDwellMs`), took **310 ms** |
| Total | **1,010 ms**, the sum of its steps and `LastCycleTime` alike |
| Work / wait | **970 / 40 ms**. The 40 ms is N100, the only wait (`WAIT_OPERATOR`): the two-hand press |
| Trend | the newest `History` entry is cycle 8, 1,010 ms, split `[970, 0, 0, 40, 0]` by `E_TimeClass` |
| Statistics | N110's count went from 11 to 12: the cycle counted it once |

A delay is seen to finish one scan after its time, which is why 200 ms reads
210, and why the stall watchdog gives an expected time one scan of grace.
Every duration is a whole number of 10 ms task periods.

Cycle 8 is the eighth completed since the download. The earlier Phase 5 rows
ran seven, and every one was counted.

## 2. A cycle stopped part-way

STOP at N150, then the reset: `LastCycleNo`, `LastCycleTime` and the trend
head are unchanged (8, 1,010 ms, 8), and the cycle is closed, not left open.
TC3's `CycleAbandon`, applied to a stop inside a cycle.

## 3. Everything else

| Gate | Result |
|---|---|
| Phase 5: run styles, OEE, machine state, rework (17 rows) | all pass |
| §146 parity | 25/25. ST 945.2 ms, SFC 971.8 ms, LD 968.5 ms; each runs 3/3 door, 3/3 ram and 2/2 slide strokes; OrderFail 0 |
| Phase 1 / 2 / 3 / 4 | 7/7 · 6/6 · 8/8 · 11/11 |

Every harness checked serial `7036B510` and the press fingerprint before
writing, and every disarm cleared.

## 4. Not shown here

- **The HMI's cycle view in a browser.** It reads the paths read above.
- **The waterfall in SFC and LD on the bench.** The profiled cycle ran in ST.
  The observer reads only the entry record, which parity shows each rendition
  writes alike, and the model gives an identical waterfall for all three.
- **A trend that wraps, or a cycle past 32 steps.** Both are tested on the
  model.
