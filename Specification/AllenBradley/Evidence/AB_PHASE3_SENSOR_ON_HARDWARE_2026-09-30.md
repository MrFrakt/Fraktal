# Fraktal/AB — the part-present sensor on the bench (Phase 3, item 1)

**Result:** the second library type, TC3's `FB_DigitalInputCM`, and the
per-type context it needed **compiled in Studio v33 and were downloaded. §146
parity re-passed 17 of 17, and Phases 1, 2 and 3 re-passed 7/7, 6/6 and 5/5**,
the last including a row for the sensor itself.

**Date:** 2026-09-30 · **Repository revision:** `7cf8970`
**Raw record:** [`AB_PHASE3_SENSOR_ON_HARDWARE_2026-09-30.json`](AB_PHASE3_SENSOR_ON_HARDWARE_2026-09-30.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press34.L5X`: `ContentHash F95302D66EC858DD`, manifest schema major 2 |
| Declaration | the same hash, so the controller matches the repository |

## 1. What the compiler accepted for the first time

- a second library AOI, `FRK_M_DigitalInput`, beside `FRK_M_Cylinder`;
- per-type context UDTs, `FRK_T_CylinderCtx` and `FRK_T_DigitalInputCtx`,
  where one `FRK_T_ModuleCtx` had served every module;
- the Unit AOI taking InOut contexts of two different types;
- a step condition on another module's context inside the Unit AOI
  (`CtxPartPresentSensor.OutImm_Value AND .OutImm_Quality`), in ST, SFC and LD.

## 2. §146 parity

| | ST | SFC | LD |
|---|---|---|---|
| Cycle completes, `OrderFail` 0 | 936.7 ms | 741.1 ms | 911.8 ms |
| HELD at step 180 → self-resumed | ✓ | ✓ | ✓ |
| Held reason | 12001 | same | same |

**17 of 17.** `OrderFail` 0 in every rendition matters here: the sensor is a
fifth module the Unit's ordering check now covers, and it ran before the Unit
on every scan.

N100 now waits on the sensor, not on the bare tag, so every parity cycle
started through it. The harness still writes the same part-present stimulus,
which now feeds the sensor.

## 3. The sensor itself (`fraktal_ab_phase3_execute.py`, row 0)

| Part stimulus | Sensor `OutImm_Value` / `OutImm_Quality` / `Error` |
|---|---|
| 0 | 0 / 1 / 0 |
| 1 | 1 / 1 / 0 |
| 0 | 0 / 1 / 0 |

It is published as `std.moduleType.digitalInput`, TC3's key, under
`project.module.partpresentsensor`, with no fault.

## 4. Not observed on hardware

- **A command to the sensor is refused.** Nothing on the declared write
  surface commands a module directly, and the mailbox does not address one.
  It is proved on the ST model (`test_fraktal_ab_digital_input`).
- **Bad quality.** The simulated source always vouches for its value, so a
  part at bad quality is not reachable on the bench. The model proves N100
  does not start on one.
