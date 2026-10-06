# Fraktal/AB — command timing and the degradation watch on the bench (Phase 5f), and a reader defect

**Result:** press49 was downloaded. Its manifest read back exact, but **the
gateway refused the station**. Its reader shifted the cylinder context past
the first array members 5f added: defect D9, in the gateway and harness reader,
not the controller. Fixed in the reader (`582aded`) with no new download. On
the fixed reader **Phase 5 passed 21/21**, §146 parity 25/25, and Phases 1-4
7/7, 6/6, 8/8 and 11/11. The gateway itself needs a restart onto the fix.

**Date:** 2026-10-01 · **Controller logic:** `ee50c04` · **Reader and harnesses:** `582aded`
**Raw record:** [`AB_PHASE5F_COMMAND_TIMING_ON_HARDWARE_2026-10-01.json`](AB_PHASE5F_COMMAND_TIMING_ON_HARDWARE_2026-10-01.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press49.L5X`: `ContentHash E54508813767DDD1`, `ConfigRevision 15025416` |
| Manifest | read back whole and coherent, 51,064 bytes in 145.1 ms, every row equal to the declaration |
| Gateway | `/healthz` **degraded, PLC not ready**, until restarted on `582aded` |

## 1. D9: the reader, not the controller

- **What happened.** The gateway's `/healthz` read degraded. Running the
  projection directly against the controller (read-only) raised `TypeError`
  in `command_timing`, because the cylinder's `TimCount` came back as one
  integer.
- **The cause.** `read_unit` and `read_module` unpacked a context by member
  NAME, one DINT per name. Until 5f no module context had an array, so that
  was never wrong. The cylinder's first arrays (`TimCount[8]` and the rest of
  the timing columns) shifted every member after them, `AreaSafe`, `Permit`
  and the end sensors among them.
- **Why nothing was published wrong.** The projection failed on the first
  shifted value, and the gateway refused the station. That is §3.10's
  fail-closed rule doing its job.
- **Why no test caught it.** Every offline fixture built a context as Python
  values. None packed one the way Logix lays it out and read it back through
  the real reader.
- **The fix.** Both now read through `read_layout`, the dimension-aware
  reader the chart, alarm log, OEE and profiler already used.
  `test_fraktal_ab_readers` packs every structure the projection reads as
  Logix does and reads it back; it fails four ways on the old reader. What is
  still read flat (the configuration records, the durability record, the
  model values) is held to scalar-only by test.

After the fix the projection reads press49 cleanly: 3,679 values, the door's
timing rows in place.

## 2. Command timing (§8.11.4(a))

Manual commands in MANUAL, read from each module's own timing columns:

| Command | Counted | Last |
|---|---|---|
| PartSlide EXTEND | once | **40 ms**: four 25-unit scans |
| PartSlide RETRACT | once | **40 ms** |
| Door RETRACT, the door already open | once | **10 ms**: accepted and done in one scan |

The last row is the command TC3 never times: it leaves no BUSY edge between
two of TC3's cycles.

The slide's published row (`Press/PartSlide/Timing/Rows[1]`) reads `extend`,
14 runs, last 40, minimum 40, maximum 500, average 107. The 500 ms maximum is
the jammed-slide timeout of the OEE down-time row, timed like any other
command.

## 3. The degradation watch (§8.11.4(d))

The running model's `BaselineWorkMs` was written from 950 down to 300 through
`WRITE_CONFIG`, then two AUTO cycles were run:

| | Observed |
|---|---|
| First cycle | WORK **970 ms**, past 300 + 20 % = 360: `DegradedCount` 1 → 2, and **one** ring entry: **2007** `CYCLE_TIME_DEGRADED`, LOW, AUTO_RESET, source `Press` |
| Second cycle | still degraded, the same excursion: count stays 2, no new entry |
| Baseline | written back to **950**, and read back as 950 |

The count was already 1 before this row. The Phase 5 SINGLE_STEP cycles had
tripped it: their 0.4 s pauses for each Step fall inside WORK steps, so a paced
cycle reads as a slow one. TC3 classes paced time the same way. It is recorded
as a finding for both bindings, not changed here.

## 4. Everything else

| Gate | Result |
|---|---|
| Phase 5: run styles, OEE, machine state, rework, profile (19 earlier rows) | all pass |
| §146 parity | 25/25. ST 969.5 ms, SFC 971.6 ms, LD 972.7 ms; each runs 3/3 door, 3/3 ram and 2/2 slide strokes; OrderFail 0 |
| Phase 1 / 2 / 3 / 4 | 7/7 · 6/6 · 8/8 · 11/11 |

Every harness checked serial `7036B510` and the press fingerprint before
writing, and every disarm cleared.
