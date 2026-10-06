# Fraktal/AB — TC3's machine state and rework count on the bench (Phase 5d)

**Result:** press47 was downloaded. **Phase 5 passed 17/17.** The press moved
through every machine state the bench can reach, each classified as TC3
classifies it. Nothing regressed: §146 parity 25/25, and Phases 1-4 7/7, 6/6,
8/8 and 11/11.

**Date:** 2026-10-01 · **Repository revision:** `1753925`
**Raw record:** [`AB_PHASE5D_MACHINE_STATE_ON_HARDWARE_2026-10-01.json`](AB_PHASE5D_MACHINE_STATE_ON_HARDWARE_2026-10-01.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press47.L5X`: `ContentHash FF92FDD44C16C06E`, `ConfigRevision 16749309` |
| Manifest | read back whole and coherent, 51,064 bytes in 140.4 ms, every row equal to the declaration |
| Gateway | `/healthz` ready, PLC ready |

## 1. The machine state, read where the HMI reads it (`Press/MachineState`)

| The press | Published |
|---|---|
| stopped and reset | IDLE |
| CHANGEOVER selected | CHANGEOVER |
| AUTO running | PRODUCING |
| after STOP | STOPPED |
| after the reset | IDLE |
| the slide stuck, the Unit in ERROR | DOWN |
| recovered | IDLE |

STARVED and BLOCKED do not occur here. No step of either binding's press is an
upstream or downstream wait. Both are tested on the model.

## 2. Rework count

`Press/ReworkCount` is 0, and so is the Unit's own counter on the controller.
The press declares no rework verdict, on either binding.

## 3. Everything else

| Gate | Result |
|---|---|
| Phase 5 run styles (10 rows) | all pass in ST, SFC and LD |
| Phase 5 OEE (5 rows) | all pass: RunMs 1,520 against 1,564 ms of wall time, P 0.625; the first sample landed 60.013 s after the reset |
| §146 parity | 25/25. ST 972.0 ms, SFC 977.3 ms, LD 971.3 ms; each runs 3/3 door, 3/3 ram and 2/2 slide strokes; OrderFail 0 |
| Phase 1 / 2 / 3 / 4 | 7/7 · 6/6 · 8/8 · 11/11 |

Every harness checked serial `7036B510` and the press fingerprint before
writing, and every disarm cleared. The harnesses ran with `python -B`, from a
cleared bytecode cache.
