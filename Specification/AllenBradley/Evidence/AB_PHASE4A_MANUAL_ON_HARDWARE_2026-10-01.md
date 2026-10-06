# Fraktal/AB — TC3's manual commands and collision interlocks on the bench (Phase 4a)

**Result:** press41 was downloaded. **Phase 4a passed 7 of 7 on the controller.
§146 parity passed 25 of 25, and Phases 1, 2 and 3 passed 7/7, 6/6 and 8/8,
with the new interlocks active in every rendition.**

**Date:** 2026-10-01 · **Repository revision:** `80d2dcd`
**Raw record:** [`AB_PHASE4A_MANUAL_ON_HARDWARE_2026-10-01.json`](AB_PHASE4A_MANUAL_ON_HARDWARE_2026-10-01.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press41.L5X`: `ContentHash 9C54A2F97E1ACFC9`, `ConfigRevision 10245282` |

## 1. Phase 4a (`fraktal_ab_phase4_execute.py`)

| Row | Observed |
|---|---|
| START in MANUAL | refused, `std.release.manualHasNoAutoSequence`; not running |
| Catalogue | each cylinder: `1 std.command.extend`, `2 std.command.retract`; the sensor: 0 entries |
| Door close, slide outside | accepted, then HELD on 2003, described `project.interlock.doorCloseRequiresSlideInside`; 0.8 s later still at 0, no error, no timeout |
| Second command to the held door | refused, `module_busy`; OPERATOR_RESET released the held command (Execute 0, ManualCmd 0) |
| Slide out under a closed door | the door closed by manual command over the slide inside; the slide's way out HELD, described `project.interlock.slideOutsideRequiresDoorOpen`; opening the door let it finish, no error |
| Ram press, guard open | HELD, described `project.interlock.pressRequiresGuardClosed`; with air lost as well, `project.interlock.pressRequiresAirPressure` - TC3's first-out order |
| Refusals | the sensor as target: `target_not_addressable`; command 3: `command_not_in_catalog`; any command in AUTO: `std.release.manualModeRequired` |

## 2. With the interlocks in force

| One AUTO cycle | Door | PressRam | PartSlide | Cycle | OrderFail |
|---|---|---|---|---|---|
| ST | 3 / 3 | 3 / 3 | 2 / 2 | 965.1 ms | 0 |
| SFC | 3 / 3 | 3 / 3 | 2 / 2 | 971.7 ms | 0 |
| LD | 3 / 3 | 3 / 3 | 2 / 2 | 969.0 ms | 0 |

The abandon, dwell and abort walks pass in every rendition. The dwell walk now
releases once N220 has begun, because a release during the N200 stroke holds
the ram on its two-hand permit, as TC3's does. Phases 1-3 pass unchanged,
including air lost under the door's close.

## 3. Not shown here

- The HMI's own manual panel. The gateway resolves an HMI `TargetPath` with
  the same function this harness calls (`mailbox.manual_target`), which is
  unit-tested. No browser session was part of this run.
- The control-power condition of TC3's ram permit (no power group on this
  bench), manual audit events, and a Unit naming a held child by its
  interlock text. These are recorded in the parity audit.
