# Fraktal/AB Phase 6 item 0 — manifest room on hardware

**Result:** press53's enlarged manifest reads back whole, coherent and equal
to the declaration. Every regression harness passes. Phase 6 item 0 is complete.

**Date:** 2026-10-01, America/Bogota. The verification ran from
2026-10-02 01:12:16 to 01:15:37 UTC. **Source revision:** `1357a4f`.
The owner replied `done` after the requested Studio 5000 v33 import, Verify,
download and gateway restart. Studio verification is owner-reported;
the controller readback and runtime results below were measured here.

The [raw JSON record](AB_PHASE6_ROOM_ON_HARDWARE_2026-10-01.json) contains
every harness result, its serial guard and cleanup, gateway health checks,
and the offline gate summary. This follows the append-only
[offline build record](AB_PHASE6_ROOM_BUILD_2026-10-01.md).

## Build and manifest readback

| Property | Observed |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510`, `192.168.100.89` |
| Build | `C:\work\press53.L5X` |
| File SHA-256 | `7E35230B1C07E0837B15E5A6BB83ED6DDB5FCE5DB15920AB5866D8CBB541A0EC` |
| ContentHash / ConfigRevision | `4FD8961CE0AA3E17` / `5232790` |
| Fields | 485 / 768 rows; 24,576 bytes in 30.552 ms |
| Localization | 460 / 768 rows; 49,152 bytes in 54.996 ms |
| Full manifest | **79,736 bytes in 177.236 ms**, including header and coherence recheck; 11 requests |
| Valid / Truncated | 1 / 0 |
| Comparison | Every table's rows match the committed declaration; no findings |
| Gateway | `/healthz` reports `ready`, `plcReady: true`, before S3 and parity and after every writing harness |

Both enlarged tables were read through the whole-tag path, one request each.
The capacities have therefore been measured on the controller, independently
of the unchanged contract hash. The 96 KiB budget remains a generation limit;
this run measures the current 79,736-byte build, not the whole budget or the
station template.

## Runtime and regression verification

| Harness | Result |
|---|---|
| S3 health and timing, read-only | 6/6 |
| Press ST/SFC/LD parity | 25/25 |
| Phase 1 | 7/7 |
| Phase 2 | 6/6 |
| Phase 3 | 8/8 |
| Phase 4 | 11/11 |
| Phase 5 | 25/25 |

Parity proves the plant's command counts in each rendition: door 3 run / 3
done, ram 3 / 3, slide 2 / 2, with `OrderFail: 0` and no error. Its completed
cycles took 974.551 ms (ST), 971.852 ms (SFC) and 969.155 ms (LD).

S3 sampled 489 scans over 4.891 seconds. Execution time was 578–869 µs,
median 617.5 µs; the controller's maximum scan was 1,084 µs against a
10,000 µs period. The sampled windows span 9,783–10,186 µs with maximum
jitter 217 µs. Overlap count and major/minor fault bits were zero.

Phase 5 restored `BaselineWorkMs` to its original 950 and left the press
stopped in CONTINUOUS. The system-health facet remained evaluated:
`TaskCycleUs: 9994`, `TaskJitterUs: 6`, no overrun. `Healthy: false` is
expected because CPU and memory have no available GSV source. The only
standing health event was 21 `CONTROLLER_METRICS_UNAVAILABLE`, LOW,
AUTO_RESET, with no blocking event. The clock was available but unsynchronized.

The owner's `done` authorized these named verification harnesses' tag writes
on serial `7036B510`. Each writing harness checked that serial and the press
fingerprint before writing. All ten fixture inputs were reported cleared by
every disarm. No harness failed or required a rerun.

## Offline gates and claim

- AB tool suite: **1292 tests**, exit 0.
- `tools/check_consistency.py`: **0 errors, 0 warnings**, exit 0.
- `tools.test_check_consistency`: **32 tests**, exit 0.

The gates used the gateway venv with `-B`, `PYTHONDONTWRITEBYTECODE=1` and
a fresh `PYTHONPYCACHEPREFIX`. The preceding build record contains the
pressure tests, 9/9 killed mutations and XML comparison proving that only
the manifest header and the two enlarged array tags changed from press52.

The posture remains the v33 legacy zone-and-conduit bench, write-enabled by
the recorded owner decision. Phase 6 will widen the operations available
through that surface to sets, login and shelving; this capacity item adds
none of those routes. **The write-enabled claim remains owed until S9 passes.**
The next item is `CAPTURE_CONFIG` together with D5's read-only configuration
query in both gateways, under the handover's next `go on` / `done` loop.
