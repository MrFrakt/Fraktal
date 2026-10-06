# Press76 five shifts and production targets — offline preparation

Recorded 2026-10-05T14:42:53.601897+00:00. **Offline checks pass; native fit is pending.**
Press75 remains loaded on 1769-L24ER-QB1B fw33.014, serial 7036B510. No controller
writes/download, mode change, clock set or gateway restart were performed.

Prepared file: `C:/work/press76.L5X`, SHA-256
`806BB78A1D8B6A932AA826373C0F59F2C2D9848E6F6AA2004A11D2D5EF876C35`. Manifest `026DC8F584CA2D70` /
159176, 68,048 bytes;
Fields 626/640, Localization 678/688, WriteCapabilities 30/32, no truncation.
Two generations from the same pinned seed/commissioning image are byte-identical.
All retained released type layouts compare equal; expanded Line/work/history and
derived value arrays use new V3 type names, never larger V2 reinterpretations.
AOIs, task/module setup and existing access initializers remain identical.

Five weekly slots support three Monday–Friday eight-hour rows and two
Saturday–Sunday twelve-hour rows, without enabling that example automatically.
Every row remains independently configurable. Whole-calendar validation checks
all ten unordered row pairs; 3,196 calendars match the independent interval oracle.
Existing half-open boundaries, Sunday wrap, unscheduled counts, deferred calendar
application, clock quality, manual-reset marking and eight-record history remain.
Targets are good-part counts, 0 unconfigured, 0..2147483647, with PIECE units.
ENGINEER-or-higher effective policy applies to edits and complete 21-field Line sets.
The PLC latches a target at interval start and snapshots it at closure before reset;
later calendar/target edits do not rewrite open or closed targets. HMI current
progress and historical attainment use existing good counts, allow above 100%,
exclude NOK/rework and avoid division for absent/zero goals. Targets are reporting
data and do not command production.

The fresh guarded capture read the complete configuration/catalog twice with
identical results and unchanged serial/manifest guards. It preserves four model
banks and M-101; the explicit V2 commissioning migration preserves all old rows
and current records, adds an unused fifth row and zero targets, then validates
the complete image. Credentials/session/history are not commissioning data.
Unchanged access initializers are not a claim of migrating edited live accounts
across a full download; owner account/retention acceptance remains separate.

Compared with loaded press75, declared data grows 2,756 bytes, ST source 9,535
bytes, 153 terminators and 187 lines; RLL remains 20 rungs. These are source/data
trends, not compiled memory. The prior online baseline has 27,864 free data/logic
bytes. Require owner Capacity Estimate of both divided areas, Verify and completed
link/download before claiming fit or growing memory further.

Verification: 1,615 AB tests pass; 531 HMI tests pass with 7 deployment-gated skips;
Flutter analysis clean; release JavaScript Web build passes; consistency 0/0.
Generated-ST tests cover all five schedule boundaries, atomic sets, negative target
refusal, effective permission refusal, current target edits waiting for the boundary,
old-target closure and immutable history. Shared HMI tests cover row 5/12 weekdays,
legacy missing fields, independent current/history goals, overachievement and zero.
The initial full AB run found the fixture's stale expected V2 array schema; corrected
to the declared V3 contract and rerun fully. No native compiler result is claimed:
Studio import/Verify/download are the owner's licensed-desktop gate.

Published Web HMI main SHA-256 `ED95380639100592B4BD56E892225CB5A4145638555F95544EB3F3A147C25624`. TLS host validation and
authenticated HTTPS requests returned byte-identical main/bootstrap/index assets
at 200. The client remains compatible with loaded press75's absent target fields.
Restart the existing gateway after matching press76 download, then hard-refresh
Chrome to expose five-slot configuration. Native/browser/physical retention still
need their own acceptance; no PLC motion or time changes were made for this record.

Structured record: [AB_PRESS76_SHIFT_TARGETS_OFFLINE_2026-10-05.json](AB_PRESS76_SHIFT_TARGETS_OFFLINE_2026-10-05.json)
SHA-256 `218C2D230D23FDB198689A7B31368A94F57FD5E3A1AD028A2321C9F6785775D5`.
