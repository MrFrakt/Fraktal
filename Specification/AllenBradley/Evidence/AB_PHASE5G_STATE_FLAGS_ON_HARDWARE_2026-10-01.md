# Fraktal/AB — TC3's derived state flags on the bench (Phase 5g)

**Result:** press50 was downloaded and the gateway restarted onto the D9
reader fix. **The gateway is ready, and Phase 5 passed 23/23.** Nothing
regressed: §146 parity 25/25, and Phases 1-4 7/7, 6/6, 8/8 and 11/11.

**Date:** 2026-10-01 · **Repository revision:** `53dcfe4`
**Raw record:** [`AB_PHASE5G_STATE_FLAGS_ON_HARDWARE_2026-10-01.json`](AB_PHASE5G_STATE_FLAGS_ON_HARDWARE_2026-10-01.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press50.L5X`: `ContentHash 1C7043DB55AC904B`, `ConfigRevision 1863747` |
| Manifest | read back whole and coherent, 51,064 bytes in 149.3 ms, every row equal to the declaration |
| Gateway | `/healthz` **ready, PLC ready**, before and after every harness. D9 is closed on the bench too |

## 1. At load position, never latched (`Press/StateFlags[1]`)

| The press, in MANUAL | Value | Since |
|---|---|---|
| home | **true** | 23:07:23.603 |
| the slide sent in by a manual command | **false** | 23:07:25.253 |
| the slide sent out again | **true** | 23:07:25.603 |

The flag cleared the moment the slide left its position, with no sequence
running to clear anything. That is the case TC3 made `Homed` a derived flag
for. Each change carries a later controller-clock stamp, and `Stale` stayed
false throughout.

## 2. Ready for a two-hand start (`Press/StateFlags[2]`)

The two-hand armed, air on, and the part sensor stepped through present,
absent, present: the flag read **true, false, true**.

## 3. Everything else

| Gate | Result |
|---|---|
| Phase 5: run styles, OEE, machine state, rework, profile, command timing, degradation (21 rows) | all pass |
| §146 parity | 25/25. ST 976.0 ms, SFC 974.5 ms, LD 975.0 ms; each runs 3/3 door, 3/3 ram and 2/2 slide strokes; OrderFail 0 |
| Phase 1 / 2 / 3 / 4 | 7/7 · 6/6 · 8/8 · 11/11 |

Every harness checked serial `7036B510` and the press fingerprint before
writing, and every disarm cleared.
