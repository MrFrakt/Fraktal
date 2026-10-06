# Fraktal/AB — the air-pressure monitor on the bench (Phase 3, item 3)

**Result:** the fourth library type, TC3's `FB_AirPressureMonitorCM`, with air
as each cylinder's interlock (TC3's `SetAreaSafe`), **compiled in Studio v33 at
the second attempt and was downloaded. §146 parity re-passed 17 of 17, and
Phases 1, 2 and 3 re-passed 7/7, 6/6 and 7/7.** The last includes air lost
under a moving cylinder.

**Date:** 2026-10-01 · **Repository revision:** `8f5bbac`
**Raw record:** [`AB_PHASE3_AIR_ON_HARDWARE_2026-10-01.json`](AB_PHASE3_AIR_ON_HARDWARE_2026-10-01.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press37.L5X`: `ContentHash 3819172B1682B27F`, manifest schema major 2 |
| Declaration | the same hash, so the controller matches the repository |

## 1. The first build did not compile, and why that is recorded here

press36 carried the same contract and the same hash. Studio v33 rejected it:

```
Error: Line 139: Too many 'OR' operators in expression with enough parentheses.
```

Line 139 of `FRK_PressMain` was the stall watchdog's test of whether anything
was held: one `OR` per module, and the air monitor made six. press35 had
compiled the same line with five. The generator now writes that test as one
`IF` per holder into an unpublished flag (`FRK_Press_AnyHeld`), and
`test_fraktal_ab_platform_limits` holds every generated ST line to five
operators of one kind, for this application and for one with twelve more
modules. press37 is that build. Its hash equals press36's because the flag
is not part of the published contract. Since press36 never compiled, the hash
on the controller can only be press37's.

## 2. §146 parity

| | ST | SFC | LD |
|---|---|---|---|
| Cycle completes, `OrderFail` 0, parked at N100 | 963.9 ms | 743.6 ms | 941.3 ms |
| HELD at step 180 → self-resumed | ✓ | ✓ | ✓ |
| Held reason | 12001 | same | same |

**17 of 17**, with seven modules, the air monitor running before the
cylinders on every scan.

## 3. Air lost under a moving cylinder (`fraktal_ab_phase3_execute.py`)

Air was withdrawn during N170's declared 200 ms settle. That way the door's
close at N180 starts without air, and the test does not race a four-scan
stroke.

| | Observed |
|---|---|
| The monitor | `PressureOk` 0, `LowPressure` 1, `OperatingPressure` 0 |
| The door, 0.8 s later (past its 500 ms timeout) | `Held` 1 on `2003` `INTERLOCK_DROPPED`, `Error` 0, position 0 |
| The press | step 180, `DiagReason` 2003 (the held child rolled up), `Error` 0, not timed out |
| Air back | the door finished its close; the chain resumed to step 200 |

TC3's rule, observed on AB: a cylinder cannot move without air, losing it
mid-stroke is a hold with nothing to reset, and it resumes by itself.

Phase 3's other rows re-passed: the sensor, the stuck slide naming
`_101B301A`, the held ram, the 30 s stall, and a press before the part not
starting the stroke.

## 4. Not observed on hardware

- **The switch conflict.** The bench's one air stimulus drives both switches
  consistently, so both-on cannot occur. Its qualification over
  `ConflictTime`, its fault naming both switches, and its latch until an
  operator reset are proved on the ST model (`test_fraktal_ab_air_pressure`).
- **Editing `ConflictTime` from the HMI.** It is published as a write
  capability under `airPressure.conflictTime`; no write was made in this run.
