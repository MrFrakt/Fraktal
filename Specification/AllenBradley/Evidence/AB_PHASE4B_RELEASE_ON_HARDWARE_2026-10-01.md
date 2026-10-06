# Fraktal/AB — TC3's release reports on the bench (Phase 4b), and a reset that restarted the press

**Result:** press42 was downloaded. **The release reports pass: Phase 4 is 11
of 11, §146 parity 25 of 25, and Phases 2 and 3 are 6/6 and 8/8.** Phase 1
passed 6 of 7. Its failure is a defect older than this build, which the new
START gate exposed: **an operator reset restarted the press by itself.**
press43 fixes it.

**Date:** 2026-10-01 · **Repository revision:** `4dce1f3`
**Raw record:** [`AB_PHASE4B_RELEASE_ON_HARDWARE_2026-10-01.json`](AB_PHASE4B_RELEASE_ON_HARDWARE_2026-10-01.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press42.L5X`: `ContentHash B8A2BE7BB9D19ECB`, `ConfigRevision 12100286` |

## 1. The reports, read where the HMI reads them (`HmiResponse/Report`)

| Row | Observed |
|---|---|
| START without air | refused, `DiagnosticKey` = `project.condition.airPressureOk`; the answer's report: `airPressureOk`, 2002 (`PERMISSIVE_NOT_MET`), owner `Press`, kind INTERLOCK |
| Air back | RELEASE_START: `Released` true, no reasons; START accepted |
| MANUAL, aborted, no air | three reasons, in TC3's order: `std.release.manualHasNoAutoSequence` (MODE), `std.release.unitNotReady` (MODE), `project.condition.airPressureOk` (INTERLOCK) |
| Manual query: door close, slide outside | `project.interlock.doorCloseRequiresSlideInside`, 2003, owner `Press.Door`, INTERLOCK |
| Manual query: door open | released, no reasons |
| Action query: ALARM_RESET, nothing blocking | `std.release.noBlockingAlarm`, owner `Press`, OTHER |
| START while an alarm waits (Phase 1) | refused; the report lists `unitNotReady` and `std.release.manualReset` (ALARM); the refusal names the first |

Phase 4a's seven rows pass unchanged, and so do all three renditions' cycles:
every stroke ran, in 972-976 ms.

## 2. The defect: an operator reset restarted the press

Phase 1's next row, `start_accepted_after_the_reset`, failed. START after the
reset was refused as `unitNotReady`, because the press was already running.

- **The sequence.** START raises `RunRequest`, a level. A fault stops the
  chain (`Running := 0`) but leaves the level up. OPERATOR_RESET only raised
  `ResetRequest`. So in the scan it cleared the error, the run latch saw
  `RunRequest` high and set `Running` again. The chain restarted from its
  init step with no START.
- **Why it was not seen before.** The old START gate accepted a START while
  the Unit was running, which did nothing harmful and so hid the restart. The
  release report refuses it, because TC3 refuses START when the Unit is not
  ready, and that refusal is what exposed it.
- **What TC3 does.** TC3's OperatorReset releases its own run command
  (`_M_RecoverState`). AGENTS.md: one operator reset must leave the machine
  restartable, never restarted.

**Fix (press43):** OPERATOR_RESET lowers `RunRequest` with the reset.
`test_fraktal_ab_release.AResetDoesNotRestart` runs START, a fault, the reset
and a fresh START on the model. The old reset fails it, and the mutant is
killed. Phase 1's reset row now also requires `Running` 0 after the reset.
press43 carries the same contract and hash as press42 (one line of logic), so
the Phase 1 reset rows are what tell them apart.

## 3. Not shown here

The HMI release panel itself, in a browser. The paths it re-reads after an
acknowledgement are the ones read above, and the projection publishes all 24
of TC3's slots, which `test_fraktal_ab_release` checks.
