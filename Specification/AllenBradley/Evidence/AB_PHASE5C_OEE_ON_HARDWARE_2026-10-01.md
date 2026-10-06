# Fraktal/AB — TC3's OEE on the bench (Phase 5c)

**Result:** press46 was downloaded. **Phase 5 passed 15/15**, including the five
new OEE rows. Nothing regressed: §146 parity 25/25, and Phases 1-4 7/7, 6/6, 8/8
and 11/11.

**Date:** 2026-10-01 · **Repository revision:** `7e73e23`
**Raw record:** [`AB_PHASE5C_OEE_ON_HARDWARE_2026-10-01.json`](AB_PHASE5C_OEE_ON_HARDWARE_2026-10-01.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press46.L5X`: `ContentHash C6F4216F214A6BA5`, `ConfigRevision 13038625` |
| Manifest | read back whole and coherent, 51,064 bytes in 121.8 ms, every row equal to the declaration |
| Gateway | `/healthz` ready, PLC ready |

## 1. OEE, timed against the wall clock

The formula is the projection's and is tested offline. These rows check what
only the controller can show: that its buckets measure time.

| Row | Observed |
|---|---|
| `RESET_OEE` | accepted; epoch 1 → 2; run 0, down 0, trend head 0; nothing valid (no run, no parts since) |
| Run time is the time the press runs | one cycle and a wait at N100: **RunMs 1,520** against 1,571 ms of wall time from START to STOP (the wall time includes two acknowledgements); down 0. A 1.0, Q 1.0, P = 950 x 1 / 1,520 = **0.625**, OEE 0.625 |
| Down time is the time it is faulted | the slide stuck, the Unit in ERROR: across two card reads a second apart, **DownMs grew 1,340, RunMs and IdleMs by 0**. The extra ~340 ms is the second read's own time. A = run / (run + down) = 0.596 |
| A sample a minute after the reset | **Head 1 at 60.005 s** after the reset. Slot 1: epoch 2, run 2,240 ms, down 1,670 ms, 1 good part, ideal 950 ms. The card shows it valid at **0.2430**, which is A 0.5729 x P 0.4241 x Q 1.0 from the slot's own numbers |
| A reset retires the trend and keeps the counts | head 0, sample 1 no longer valid; **GoodCount 7 before and after** (counts reset only on their own logged action, Core §8.11.2) |

Run time includes HOME: the 2,240 ms in the sample is the cycle's 1,520 plus
the HOME run before the fault row. HOME is BUSY, and TC3 counts it the same way.

## 2. Run styles and regression

| Gate | Result |
|---|---|
| Phase 5 run styles (10 rows) | all pass in ST, SFC and LD |
| §146 parity | 25/25. ST 971.4 ms, SFC 973.5 ms, LD 973.0 ms; each runs 3/3 door, 3/3 ram and 2/2 slide strokes; OrderFail 0 |
| Phase 1 / 2 / 3 / 4 | 7/7 · 6/6 · 8/8 · 11/11 |

Every harness checked serial `7036B510` and the press fingerprint before
writing, and every disarm cleared.

## 3. Not shown here

- **The HMI's OEE card in a browser.** The paths it reads (`Oee/*`,
  `OeeTrendHead`, `OeeTrend[i]/Oee`, `OeeTrend[i]/OeeValid`) are the ones read
  above, and the consistency gate holds the projection to them.
- **A ring that wraps.** That takes an hour; the wrap is tested on the model.
- **The access gate and audit on `RESET_OEE`**, which wait for Phase 6.
