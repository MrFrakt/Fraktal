# Line calendar V2 — prepared press71

Client date: 2026-10-04, America/Bogota. Baseline commit: `733a0df`.
This records offline implementation and served-client deployment, not native
Line acceptance. The owner-confirmed loaded baseline remains press70 on
192.168.100.89, serial 7036B510, 1769-L24ER-QB1B firmware 33.014.

## Exact artifact and commissioned image

Prepared full-controller file: `C:/work/press71.L5X`.
SHA-256: `381F1878F60CDFF79FBD3948ED622E1047319054A14F09CD65A21117EB96B140`.
Manifest major 4 / binding 2, content `94E302F650BA1DB5`, revision `9757442`.
Fields 616/640, Localization 652/672, WriteCapabilities 22/64;
estimated manifest 70,520 bytes, without truncation.

Two independent read-only, exact-serial captures of press70 agreed before
generation, with unchanged manifest `66C4A00ABDB4FCC3` / `6735008`. The image
preserves current records, running ordinal 1 and all four commissioned banks:
M-100, M-200, M-050, M-101. It adds only the declared empty Line defaults.
Capture SHA: `D8CC4ACF5BEB57754A3536EA309E04C1F65076FFEB3FB6B8D76A9343B7723F5E`.
Final image SHA: `4BD511A1CDF82C8ECEFDFCA5219B0EED162C228561668B15B3C532467F528076`.
No credentials, session, class policy or history were captured. Configuration
seeding is not evidence of credential or other provider upgrade retention.

## Implemented behavior

- Opt-in composition-owned Line data, separate from the module forest; Press
  selects one owner. Four rows have start, duration and Monday–Sunday mask.
  Saturday/Sunday 08:00 plus 720 minutes supports weekend-only 12-hour shifts.
- Complete range/type/weekly-overlap validation on the PLC before ordinary
  calendar writes or complete 13-field set loads. Effective permissions remain
  enforced. An accepted transaction increments the revision once.
- Current scheduled or unscheduled interval, deferred calendar changes and
  eight immutable controller-owned closed records. Counts and raw OEE buckets
  are snapshotted before reset; the trend survives closure. Manual resets and
  clock discontinuities carry quality flags. No clock is set by this code.
- Native integer epoch-minute/subminute timestamps; projection derives OEE
  factors from the frozen native snapshot. The HMI displays history and weekday
  checkboxes with existing permission, preset sizing and spacing behavior.
- Exact additive set-revision bridges preserve prior station/model ordinals;
  foreign or incomplete payloads still refuse. Expanded derived arrays use
  DataLevelsV2/ConfigSetStateV2 rather than reinterpreting their V1 layouts.

Mirror/source transport, shared multi-root ownership and external history-sink
delivery remain unbound. This single-root bench does not establish those claims.

## Memory and checks

Against completed press70, declared data increases 3,156 bytes to 112,480;
ST source increases 13,583 bytes to 305,399, with 251 more terminators and
331 more lines. RLL remains 20 rungs, byte-identical. The mailbox grows only
622 source bytes; the common permission refresh shrinks 4,426 bytes. Four
new bounded Line routines own validation, search, closure and calendar apply.
These are generation trends, not a compiled memory measurement.

Retained UDT layouts are byte-identical; the two larger derived arrays have
new V2 types/schema 2. Generation was deterministic. The first layout check
found V1 expansion, and the first implementation had excessive code growth;
both failed/pre-optimization artifacts remain in the private work directory.

The preparation JSON records 1,590 AB tests, 19 Line behavior tests, 33 root
tool tests, consistency with zero errors/warnings, 495 HMI passes with seven
expected environment skips, clean analyzer and successful release build.
Six semantic mutants were killed by assertions. A first snapshot mutation
survived; the full-count assertion was strengthened, then all six were killed.
The final record-name ownership repair and expanded regression count are
recorded separately in the [superseding ownership check](AB_LINE_V2_OWNERSHIP_CHECK_2026-10-04.md);
the prepared JSON is preserved unchanged.

The installed Rockwell offline probe failed before opening/exporting the
project with `OperationFailedException: No valid license`, exit 3762504530.
It created no ACD, contacted no controller and left the L5X hash unchanged.
Owner Studio Verify and completed full download are therefore still required.

## Served client and remaining gates

The release assets were deployed to the existing HMI web root with a private
backup. HTTPS at `press.localhost` returns all three checked assets with exact
bytes and host-validated TLS. `main.dart.js` SHA:
`5BB7FE3856360D44619B1987B898F00B6B764F1F72D44576EA07051FD53D45A5`.
The gateway was not restarted and no controller writes/downloads were performed.

Next: owner Studio Verify/full download of the exact press71 file, then the
existing gateway restart and Chrome Ctrl+Shift+R. Only after exact serial/build
readback establish native Line write/set/permission/boundary/history results,
restoration, browser acceptance and physical retention. Do not advance another
controller storage feature before the fit gate passes. The remaining port
stages stay in the [completion plan](../AB_PORT_COMPLETION_PLAN_2026-10-04.md).

Machine-readable preparation record:
[AB_LINE_V2_PREPARED_2026-10-04.json](AB_LINE_V2_PREPARED_2026-10-04.json).
