# Fraktal/AB — Phase 2 on the bench: the §3.13 flow chart

**Result:** Phase 2 of the AB/TC3 parity plan
([`Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md`](../../Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md))
**compiled in Studio v33, was downloaded, re-passed §146 parity 17 of 17, and
passed 6 of 6 checks of the flow chart on the controller.**

**Date:** 2026-09-30 · **Repository revision:** `5cdb574`
**Raw record:** [`AB_PHASE2_ON_HARDWARE_2026-09-30.json`](AB_PHASE2_ON_HARDWARE_2026-09-30.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press31.L5X`: `ContentHash 57824B57B4D694D5`, manifest schema major 2 |
| Declaration | the same hash, so the controller matches the repository |

## 1. The compile gate

The owner imported press31 in Studio 5000 v33 on the licensed desktop and
downloaded it; the bench SDK probe still has no licence. New to this build is
a **nested branch inside a ladder leg**: each LD step rung now discovers its
row in `[NEQ(RowEpochOf[i],RowEpoch) … ,MOV(0,WarnReason[i])]` inside the
entry-marking leg. The compiler accepted it.

## 2. §146 parity, re-run because Phase 2 changed every step's entry

| | ST | SFC | LD |
|---|---|---|---|
| Cycle completes, `OrderFail` 0 | 938.2 ms | 724.4 ms | 918.8 ms |
| HELD at step 180 → self-resumed | ✓ | ✓ | ✓ |
| Held reason / severity | 6130 / LOW | same | same |
| Abort stands down to step 0, Running 0, Error 0 | 3.8 ms | 3.0 ms | 2.9 ms |

**17 of 17.** Mailbox sequence seed 0: the download reset the mailbox.

**The cycles are about 400 ms shorter than on press30, and that is correct.**
The download also reset the running model to the default, M-100, whose dwell
plus settle (300 + 200) is 400 ms shorter than M-200's (600 + 300), which the
press30 runs used. The same arithmetic is recorded in the Phase 0 evidence.

## 3. The flow chart, on the controller

`fraktal_ab_phase2_execute.py`, through the declared write surface only. The
expected order is not written in the script: it is walked from the declaration,
following `on_advance` from the chain's first step, which is the path a
fault-free cycle takes.

| Row | Observed |
|---|---|
| Rows in first-entry order | a fresh AUTO session after one cycle: `0, 100, 110, 130, 150, 170, 180, 200, 220, 230, 240, 242, 244, 999` on the controller (`RowOf`), as published (`SequenceSteps[i]/StepNo`), and from the declaration: identical, 14 rows |
| A row keeps its duration, the cursor its step | N170's `LastDuration` 200 ms against a declared settle of 200 ms; parked at N100, `ActiveSteps[1]/RowIdx` 2 = N100's row |
| A second cycle adds no rows | `RowCount` 14 before and after, same order |
| A mode change starts a new chart | MANUAL: `RowEpoch` 3 → 4, `RowCount` 0, `SequenceStepCount` 0 published |
| A report marks its row | the ram failing at N200: `WarnReason` 6102, `WarnSource` 1 (`PressRam`); N200 is row 8, `WarningActive` true, one annotation on row 8 with `project.reason.device_fault` and `Press.PressRam`; no row is an error |
| The next visit starts clean | N200 passed without a fault: `WarnReason` 0, `WarningActive` false, no annotation |

N170's duration shows why the record has to be the controller's: the settle
lasted 200 ms, about a fifth of a second, which a client polling at a few Hz
would see on at most one read, and often none.

## 4. Not claimed

- **`ErrorActive` is never set.** TC3 marks a row only for a §6.9(d) raise.
  An awaited child adopted by rollup is not marked there either, and the AB step
  vocabulary has no raise step yet.
- **No parallel legs.** The AB declaration has no §6.12 branches, so only
  `ActiveSteps[1]` is published.
