# Fraktal/AB — the raised manifest read back from the bench (Phase 5b)

**Result:** press45 was downloaded. **Its 51,064-byte manifest read back whole
and coherently in 141.8 ms**, 11 requests with no fallback, and every
published row equals the declaration. The gateway, now checking table
capacities, projects it. Nothing regressed: §146 parity 25/25, and Phases 1-5
7/7, 6/6, 8/8, 11/11 and 10/10.

**Date:** 2026-10-01 · **Repository revision:** `259c867`
**Raw record:** [`AB_PHASE5B_MANIFEST_CAPACITY_ON_HARDWARE_2026-10-01.json`](AB_PHASE5B_MANIFEST_CAPACITY_ON_HARDWARE_2026-10-01.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press45.L5X`: `ContentHash F1200055EB9C8388`, `ConfigRevision 15802368` |
| How press45 is known | its hash equals press44's, because the hash excludes table capacity. The header publishes `FieldsCapacity` 512 and `LocalizationCapacity` 448, and 51,064 bytes were read |

## 1. The read, before and after

Both read by `fraktal_ab_manifest_read.py`, the same reader the gateway uses,
each table as one whole-tag request.

| | press44 | press45 |
|---|---:|---:|
| Manifest bytes | 40,824 | **51,064** |
| Fields (rows / capacity) | 356 / 384 | 356 / **512** |
| Localization (rows / capacity) | 332 / 352 | 332 / **448** |
| Fields read | 12,288 B in 18.3 ms | 16,384 B in 22.2 ms |
| Localization read | 22,528 B in 26.4 ms | 28,672 B in 34.2 ms |
| All tables | 88.8 ms | 101.0 ms |
| Header + tables + coherence recheck | 130.2 ms | **141.8 ms** |
| Requests / coherent | 11 / yes | 11 / yes |

The 10,240 added bytes cost 12.2 ms of table time, about 1.2 ms per KB. The
other seven tables are each a ~6 ms request floor, as S7 saw, so the 53,248-byte
budget reads in roughly 144 ms. That cost is paid on connect and on a revision
change only. This manifest is a build constant, and the live-tier header poll
(38 ms here) does not grow with it.

## 2. What this settles

- **The binding's manifest limit is now 53,248 bytes** (`MANIFEST_BUDGET_BYTES`),
  in place of S7's 43,728. The raise was S7's cost-curve calculation, as Part
  III prescribes, and the size actually built has now been read back from this
  controller.
- **A build sized differently is refused by name.** press45 shares press44's
  hash, so the hash alone would have let a gateway built from this
  declaration read 512 rows out of press44's 384-row tag and project anyway.
  The header's published capacities now decide. The refusal is tested offline
  (the gateway was restarted after the download, so it was not seen live).

## 3. Regression

| Gate | Result |
|---|---|
| §146 parity | 25/25. ST 979.1 ms, SFC 968.3 ms, LD 971.3 ms; each runs 3/3 door, 3/3 ram and 2/2 slide strokes; OrderFail 0 |
| Phase 1 / 2 / 3 / 4 | 7/7 · 6/6 · 8/8 · 11/11 |
| Phase 5 (run styles) | 10/10. Single-stepped cycles `[0, 1 x 8]` in 4.56-4.57 s in each rendition |

Every harness checked serial `7036B510` and the press fingerprint before
writing, and every disarm cleared.
