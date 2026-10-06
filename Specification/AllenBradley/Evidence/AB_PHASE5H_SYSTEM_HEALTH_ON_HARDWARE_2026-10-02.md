# Fraktal/AB — TC3's system-health publisher on the bench (Phase 5h)

**Result:** press52 was downloaded. **Phase 5 passed 25/25**, and the raised
55,160-byte manifest read back whole. One Phase 3 row failed on its first run,
because its harness assumed the fault was the only open event. The controller
was right, the harness was corrected, and the row passes. Nothing regressed:
S3 6/6, §146 parity 25/25, and Phases 1-4 7/7, 6/6, 8/8 and 11/11.

**Date:** 2026-10-02 · **Repository revision:** `75c288c`, and the Phase 3 harness fix
**Raw record:** [`AB_PHASE5H_SYSTEM_HEALTH_ON_HARDWARE_2026-10-02.json`](AB_PHASE5H_SYSTEM_HEALTH_ON_HARDWARE_2026-10-02.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press52.L5X`: `ContentHash 4FD8961CE0AA3E17`, `ConfigRevision 5232790` |
| Manifest | **55,160 bytes**, read back whole and coherent in 147.4 ms. Localization's 32,768 bytes took 38.7 ms in one request. This confirms the 56 KiB budget the way every raise is confirmed |
| Gateway | `/healthz` ready, PLC ready, before and after every harness |

## 1. The health facet, read where the HMI reads it (`Press/SystemHealth`)

| | Published |
|---|---|
| Present, TaskAvailable | true, true |
| TaskCycleUs, TaskJitterUs | **10,167 µs**, **167 µs**, against the 10 ms period |
| TaskOverrun | false |
| Healthy | **false**, by construction: CPU and memory cannot be read |
| ControllerAvailable, IpcAvailable, FieldbusAvailable, DcAvailable | all false, with zero values: never presented as healthy |
| TimeQuality | available, not synchronized, no source (no PTP), offset 0 |

## 2. The one condition this controller always has

The active list holds exactly one health event: **21
`CONTROLLER_METRICS_UNAVAILABLE`**, LOW, AUTO_RESET, sourced to the Unit.
`Blocking` is 0. Starts went on being accepted through every phase's rows, and
no overrun or jitter event was open.

## 3. The Phase 3 row, and its harness

`a_stuck_slide_times_out_and_names_its_sensor` read `AlarmLog/Active[1]` as the
stuck slide's event. Until §8.12, the fault was the only event that could be
open. Now the standing health event, raised at the first scan after the
download, holds slot 1.

The run's own record shows the controller was right:
- the Unit was faulted with **10101** (`CYL_NOT_EXTENDED`), naming
  `_101B301A` at `Local:1:I.0`;
- the row merely inspected the wrong slot.

The harness now reads the fault's own slot, `FaultEvt`, as the Phase 1 harness
already did. On the re-run the event is 10101 `_101B301A` from
`Press.PartSlide`, and Phase 3 is 8/8.

## 4. Everything else

| Gate | Result |
|---|---|
| Phase 5: run styles, OEE, machine state, rework, profile, command timing, degradation, state flags (23 rows) | all pass |
| S3, read-only | 6/6 |
| §146 parity | 25/25. ST 966.7 ms, SFC 971.1 ms, LD 970.1 ms; each runs 3/3 door, 3/3 ram and 2/2 slide strokes; OrderFail 0 |
| Phase 1 / 2 / 3 / 4 | 7/7 · 6/6 · 8/8 (after the harness fix) · 11/11 |

Every writing harness checked serial `7036B510` and the press fingerprint before
writing, and every disarm cleared.
