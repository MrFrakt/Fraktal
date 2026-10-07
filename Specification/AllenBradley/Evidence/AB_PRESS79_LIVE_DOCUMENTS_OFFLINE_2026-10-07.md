# AB press79 — declared medium and live documents (offline)

Recorded 2026-10-07 from the
[missing-features handover](../AB_MISSING_FEATURES_HANDOVER_2026-10-06.md), items
1b and 1c. The owner chose, on 2026-10-07, to keep live configuration as gateway
documents re-applied after a download instead of seeding each image ("Yes,
design and build it"). This record covers offline implementation and one
read-only bench read only. **No controller write, download, mode change or power
cycle was performed, and no native fit, Verify or retention result is claimed.**
Historical evidence is unchanged.

## Loaded artifact, read-only

`fraktal_ab_manifest_read.py 192.168.100.89 --expect-serial 7036B510`
(serial `7036B510`, `1769-L24ER-QB1B/A`, revision 33.14) read a coherent manifest
equal to the source declaration then committed: `026DC8F584CA2D70 / 159176`,
68,048 bytes in 135 ms. That is the calendar V3 contract shared by press76,
press77 and press78; press75's `94E302F650BA1DB5` is no longer loaded. Press77
never completed a download, so the loaded image is press76 or press78. The
contract hash cannot distinguish them and **the exact artifact remains an owner
statement to record**, together with press78's Studio Capacity Estimate.

A fresh capture (`C:/work/press79_source_capture_01.py`) read the loaded image
twice under the same serial and manifest guards, with no controller write and no
credential: both reads are identical and equal the press78 capture
(`modelCodes` M-100, M-200, M-050, M-101; active ordinal 1; all four banks,
station and V3 line values).

## What changed

- **The project picks the medium (1b).** `decl.ConfigMedium(store, live_documents)`
  beside `config_sets`; `store` is Core `E_ConfigStore` (pinned to the TwinCAT DUT
  by test) and is what `ConfigPersist.StoreKind` publishes. `FILE_JSON` is the only
  implementation; `EXTERNAL` is refused until a server, schema and credentials owner
  are named. The gateway opens the declared store through
  `fraktal_ab_medium.SetStore`; `FileStore` behaviour and its folder are unchanged,
  and its atomic replacement is now one shared routine.
- **Live documents (1c), on the press, off in the template.** The design is in
  Part III AB §3.8b. In short: the first scan leaves a not-intact station image at
  version zero, which is the derived restoring state; Start names
  `std.release.configRestoring`; `WRITE_CONFIG`/`CAPTURE_CONFIG` are refused with
  that key and SAVE is refused; model documents load into their bank only while
  restoring, the active one reaching ParCfg through the changeover's own
  `CommitModel` copy; the station load answers the restore, carrying the active
  model and `StoreResult` 2 for a loss (`RestoreLost`), and stamps the image. The
  gateway keeps `Press.station`, `Press.line` and `Press.model<n>` in
  `…\ConfigSets\7036B510-Press\live\` from the reads the projection already makes,
  and restores only from a write-enabled gateway under a controller session the
  set gate permits. A medium that cannot answer is retried and never concluded.
- **Sets saved before live documents still load.** The restore text moves the
  published revision (159176 → 15071508); the five accepted revisions are
  press78's four plus press79's own. The owner's stored `M-101` set (8035226)
  stays accepted.

## Generated artifact

`C:/work/press79.L5X`, SHA-256
`3074710A088D56F8EC83056B02F76294ECB3044561934DDF0D95E3C383EBB134`, generated
twice byte-identically from `seed_v33.L5X` and the fresh capture
(`press79_source_config_01.json`, `5D044C0A…C65D`). Manifest
`E5F914E06055CD3B / 15071508`. Data types, AOIs, tasks, modules and the tag set
equal press78; only the manifest header/localization initializers change
(Localization 679 of 688 rows, capacity unchanged).

| Generated measure | press79 | Delta from press78 |
| --- | ---: | ---: |
| ST source bytes | 335560 | +3132 |
| ST statement terminators | 4088 | +28 |
| ST lines | 6514 | +54 |
| Declared data bytes | 110268 | 0 |
| RLL rungs | 20 | 0 |

`ReleaseStart` +527 bytes / +7 statements, `ConfigWrite` +165 / +2, `ConfigSets`
+2438 / +19. `HmiMailbox`, `AlarmShelfRequest`, `ConfigRecordAudit` and
`ScanModules` differ only by renumbered localization keys (equal with numbers
masked); `ScanConfigRestore`'s one changed line is the station stamp `3` → `0`.
These are generated trends, not compiled memory. Press78's margin is unmeasured,
so press79 needs the owner's Capacity Estimate before Verify and download.

## Validation

- Full AB suite by discovery: **1664 tests pass** (`press79_ab_tests_03.log`),
  including 39 new tests in `test_fraktal_ab_live.py` that execute the emitted ST,
  the medium, the keeper, the restore plan, an end-to-end restore of a downloaded
  controller through the guarded writer, and the gateway's write gate and
  sequence guard.
- 19 semantic mutants on a mirrored scratch copy run with `-B`, each killed
  (`press79_mutations_03.json`).
- Rendition gate on press79: ST/LD/SFC equal the declared graph.
- `tools/check_ab_contracts.py` clean; `tools/check_consistency.py --strict`
  0 errors, 0 warnings; its 33 tests pass.
- `tools/check_ab_spec.py` reports 3 errors (R4-R6 expected OPEN; S16 registered;
  S15 expected OPEN). The same 3 errors occur on the unmodified Part III at
  `3d77e7a`: the gate predates those spec changes and was not altered here.
- Press78 still regenerates byte-identically (`6063EE0B…`) from the same source
  with live documents off.

## Failed attempt, retained

The first press79 generation (`rejected_platform_limit_press79.L5X`,
`1D1C3C61…BCCC`) accepted eight set revisions, a chain of seven `AND`s; the
platform-limits test refused it, because Studio v33 compiles at most five
identical operators per expression (press35/press36). It was never offered for
Verify. The accepted revisions now cover only builds that existed. Two
intermediate full-suite runs are kept as `press79_ab_tests_superseded_01.log`
(1 failure: a model test still built its historical identity from the live
press) and `press79_ab_tests_02.log`; the test now names the pre-live identity.

## Owner gates still open

1. State which artifact is loaded (press76 or press78) and record press78's Studio
   Capacity Estimate; then press79's Estimate and Verify before any download.
2. The first press79 download is seeded (no documents exist yet). After it, start
   the write-enabled gateway from this commit: it captures the documents; check
   `/healthz` `liveDocuments.state = kept`.
3. Download acceptance of the restore: download an unseeded later image (or the
   same build regenerated without a seed), log in with a set-gate level, and
   compare station, line, every bank, `M-101` and the active model with the
   capture; `restored` in health, Start released, no loss.
4. The retention check plan (power cycle) for values, accounts, sets, models and
   the line calendar, each recorded separately; host power loss separately.
5. Chrome: the Start reason and the durability banner while restoring.

Until press79 is downloaded the repository is ahead of the controller: a gateway
started from this commit refuses the loaded `026DC8F584CA2D70` build by design.
Run a gateway needed before then from a worktree at `3d77e7a`.

Machine record: [AB_PRESS79_LIVE_DOCUMENTS_OFFLINE_2026-10-07.json](AB_PRESS79_LIVE_DOCUMENTS_OFFLINE_2026-10-07.json).
