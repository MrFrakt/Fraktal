# Fraktal/AB S3 — what the controller says about its own health and timing

**Spike:** S3, "GSV and module objects supply health and timing"
(Part III AB §8.11, §8.12, §10)

**Result: PARTIAL PASS.**
- **Task timing, time quality and controller faults are settled.** Every GSV
  attribute the probe reads exists on this controller, Studio's import being
  the arbiter, and all of them answer plausibly and steadily, idle and under
  the full harness load.
- **Module connection state is not measured yet.** The MODULE object's
  attributes are INT-typed and were left out of this DINT-only probe.

**Date:** 2026-10-01 · **Repository revision:** `d26a323`
**Raw record:** [`AB_S3_HEALTH_AND_TIMING_2026-10-01.json`](AB_S3_HEALTH_AND_TIMING_2026-10-01.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press51.L5X`: `ContentHash 2429AD8014904A38`, carrying the read-only `FRK_Press_HealthProbe` |
| Harness | `fraktal_ab_s3_execute.py`: **read-only**, wrote nothing, issued no command |

## 1. What was read, and how

The probe is AB's version of TC3's `FB_TcSystemHealthProbe` input, and it runs
every scan of the 10 ms task:

| Source | Attributes |
|---|---|
| `GSV(TASK, FRK_PressTask, …)` | `LastScanTime`, `MaxScanTime`, `OverlapCount` |
| `GSV(TimeSynchronize, , …)` | `IsSynchronized`, `PTPEnable` |
| `GSV(FaultLog, , …)` | `MajorFaultBits`, `MinorFaultBits` |
| `WallClockTime` (already proven, S1) | the task's real period between scans, and its jitter against the declared 10 ms, as one-second windows |

## 2. What the controller answered

| | Idle (6 s) | After the full harness load (3 s) |
|---|---|---|
| Probe rate | **100.0 scans/s** (594 in 5.94 s) | 6/6 rows again |
| Execution per scan (`LastScanTime`) | 545-882 µs, median 584 µs | |
| `MaxScanTime` | 1,021 µs | **1,190 µs**: 12 % of the period at its worst |
| Real period, per 1 s window | shortest 9,805-9,846 µs, longest 10,154-10,198 µs | |
| Largest jitter per window | **159-198 µs** | 190 µs |
| `OverlapCount` | 0 | 0 |
| `IsSynchronized` / `PTPEnable` | 0 / 0, as S1 and S9 recorded | |
| `MajorFaultBits` / `MinorFaultBits` | 0 / 0 | minor 0 |

The full harness load is parity 25/25 and Phases 1-5 at 7/7, 6/6, 8/8, 11/11
and 23/23, with faults, aborts and every rendition. None of it moved the task
near its period: there was no overrun.

## 3. The declared subset this settles (Part III AB §8.11, §8.12)

| Core §8.12 group | On this controller |
|---|---|
| Task: cycle, jitter, overrun | **Available.** The real period and jitter come from the wall clock between scans. Overrun is `OverlapCount` moving, with `LastScanTime` and `MaxScanTime` for headroom |
| Controller: CPU load, free memory | **No GSV source.** Published unavailable; TC3's own press does the same outside simulation |
| IPC: temperature, fan, storage | **Not applicable**: no IPC. Unavailable |
| Fieldbus: master, lost frames, slave errors | Local I/O, not a fieldbus. Unavailable until module connection state is measured |
| Distributed clock | **Not applicable**. Unavailable |
| Time quality | **Available**: `IsSynchronized` and `PTPEnable`. This bench runs unsynchronized, by design |
| Controller faults | **Available**: `FaultLog` major and minor bits |

## 4. Still owed

- **Module connection state**, for §10.5.1 and the fieldbus group. It needs the
  MODULE object (`EntryStatus`, `FaultCode`), whose INT attributes need an
  INT-typed destination this binding has not used yet.
- **Whether the publisher's thresholds raise and clear** their events. That is
  the §8.12 build itself, and it is built on this subset.
