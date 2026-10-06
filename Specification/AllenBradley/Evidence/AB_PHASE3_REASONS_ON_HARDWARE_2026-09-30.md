# Fraktal/AB — TC3's reasons, the stall watchdog and hold rollup, on the bench

**Result:** the first step of Phase 3 of the AB/TC3 parity plan
([`Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md`](../../Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md))
**compiled in Studio v33 and was downloaded. §146 parity re-passed 17 of 17,
Phase 1 and Phase 2 re-passed 7 of 7 and 6 of 6, and the new behaviour passed
4 of 4 on the controller.** The sensor a timeout names, which the Phase 1
record could only prove on the model, is now observed on hardware.

**Date:** 2026-09-30 · **Repository revision:** `8eccd46`, plus the harness
`home()` helper recorded in §4
**Raw record:** [`AB_PHASE3_REASONS_ON_HARDWARE_2026-09-30.json`](AB_PHASE3_REASONS_ON_HARDWARE_2026-09-30.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press33.L5X`: `ContentHash C1A5A2B177022CDD`, manifest schema major 2 |
| Declaration | the same hash, so the controller matches the repository |

## 1. §146 parity

| | ST | SFC | LD |
|---|---|---|---|
| Cycle completes, `OrderFail` 0 | 960.7 ms | 722.2 ms | 920.4 ms |
| HELD at step 180 → self-resumed | ✓ | ✓ | ✓ |
| Held reason / severity | **12001** / LOW | same | same |
| Abort stands down to step 0, Running 0, Error 0 | 2.9 ms | 3.3 ms | 3.1 ms |

**17 of 17.** The hold is now reported as 12001, TC3's
`PRESS_TWO_HAND_RELEASED`, where press31 reported 6130.

## 2. Phase 1 and Phase 2, re-run

Phase 1: **7 of 7.** Phase 2: **6 of 6.** The Phase 1 adopted-fault row now
injects a stuck slide rather than an immediate fault, and it shows what press30
could not:

| | Observed |
|---|---|
| Reason | `10101` `CYL_NOT_EXTENDED`, severity 1 (MED, the registry's) |
| The Unit's diagnostic | `std.reason.10101`, `IoTag _101B301A`, `IoAddress Local:1:I.0` |
| The alarm | `SourceModuleId` 4 = `Press.PartSlide`, `IoRoles` 2 (extendedFb), `IoTag _101B301A` |
| START while it waits | refused, `alarm_blocks_start` |

`_101B301A` is the feeder-*retracted* switch. That is the slide's logical
extended end, per `CX2030_PRESS_IO_MAPPING.md` and TC3's `FB_PressIoCatalog`.

## 3. TC3's reasons, watchdog and rollup (`fraktal_ab_phase3_execute.py`)

| Row | Observed |
|---|---|
| A stuck slide times out and names its sensor | 574 ms from START to the adopted fault. That is the declared 500 ms timeout plus the steps before N150: nothing faulted early. `10101`, `_101B301A`, the slide still at position 0 |
| A held child rolls up | the ram held at N110. The Unit's own diagnostic is `2003` `INTERLOCK_DROPPED` (`std.reason.2003`), `Error` 0, `StallMs` 0, not timed out. On press31 the Unit said nothing |
| A step that waits past StallTime is stalled | N100 waiting for a part, not timed out while it waits (`CurrentStepTimedOut` false), then at `StallMs` 30000 `StepTimedOut` 1, the Unit saying `2005` `STEP_STALLED`, `Error` 0 |
| The stall clears when the step moves | the part arrives: step 110, `StepTimedOut` 0, `STEP_STALLED` gone |

Before this build, `CurrentStepTimedOut` was true for all 30 of those seconds
and for every other wait.

## 4. One harness correction, and why it was needed

The first Phase 1 run on press33 failed its adopted-fault row. The slide never
faulted, because it was **already extended** when the row began. The parity
pass's abort rows stop a cycle wherever it is, and a cylinder already at its
target completes at once, stuck or not. That is physically right, and press30's
immediate fault had hidden the assumption.

The harness now runs the declared HOME chain first (`px.home()`: ram up, door
open, slide out) before either stuck-slide row, as a TC3 station would start
from home. No declaration or controller change was involved. The failing run
is in the raw record's history only as this note. The committed record is the
re-run.
