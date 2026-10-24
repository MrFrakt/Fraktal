# AB S3d AlarmLog/StateFlags — offline preparation, 2026-10-22

**S3d passes its offline gates at 2,125 explicit paths.** Both v38 targets
compile/read back cleanly, 2,062 AB tests pass, and automatic Studio Capacity
passes at 41%. No S3d controller-changing operation is authorized or performed.
Same-scan equivalence, lifecycle/reset/flag coverage, candidate/rollback
regressions, native record sizes and scan remain pending current approval.
Echo remains on restored genealogy, actual MANUAL=1/idle and logged out.

See [scope notes](../AB_CANONICAL_PUBLICATION_S3D_NOTES_2026-10-22.md),
[independent inventory](../AB_CANONICAL_PUBLICATION_S3D_INVENTORY_2026-10-22.json),
[V6.2 bindings](../AB_CANONICAL_PUBLICATION_S3C_WIRE_DRAFT_2026-10-22.md) and
[payload hashes](AB_S3D_CANONICAL_PREPARATION_2026-10-22/manifest.json).
Date follows the client's America/Mexico_City date. Source commit is
`a1163c7c7bec21988167bc971145b1366206e9ce` plus uncommitted work. Shipping
Part III/V1 remain authoritative; approved V2 remains inactive. No commit/push.
No ACD binary or credential contents are archived.

## Surface, ownership and explicit gaps

Before implementation, the frozen projection and S3c inventory established
**1,478 added paths**: 1,469 AlarmLog paths and nine flag paths, for 2,125 total.
The plan's previous 1,469 figure counted AlarmLog alone and is corrected.
All 16 active slots, 64 ring slots, 31 metadata rows and two flags retain their
logical extents and one-based bounds. Only the approved D2 differences in the
earlier subset remain permitted. No discovered output selects its own oracle.

The existing PLC alarm owner alone appends/closes/resets. Publication mirrors
its complete slots, RingHead and Blocking; it changes no lifecycle, shelving,
release or reset predicate. Existing unconditional flag evaluation owns values
and change times. The root carries active/ring data and flags. A second V6.2
binding carries static rationalization metadata; MetaCount remains in the
native root. The generic discovery reader is unchanged and imports no station.

Changed-input caches bound repeated text/I/O/calendar work. S3d emits one
shared calendar routine for diagnostics, event timestamps and flags, retaining
reason-zero event times. Core widths are preserved: 255-byte descriptions,
paths and rationalization text, 80-byte I/O strings, 120-byte flag keys.
Timestamps are LDT nanoseconds; durations are DINT milliseconds. Invalid
calendar/range values invalidate publication. Private caches remain outside
public whole-read records.

Core event Category, ResetAt and ShelvedUntil have no oracle paths or stored
columns and remain gaps. Time-quality fields retain the legacy false values;
flag Stale remains false because its owner runs unconditionally. Earlier Core
gaps remain explicit. The fixture has no EM/concurrent branch; this preparation
claims no full-Core, HMI, physical-controller or security acceptance.

## Exact artifacts and native gates

Work folder:
`C:/work/fraktal-ab-s3d-20261022/prepare_f1995b2579fe4f7a9d15d02dd8ed53e9/`.

| Artifact | SHA-256 |
|---|---|
| genealogy_s3d_01.L5X | 03E0775EDD8A1A22D88D198D4D3CE2B7C19A2F2029A40E3C428CB838FC2EE962 |
| s3d_canonical.ACD | E5CA9AB3493AABF93E72A728EBDF5630E8056EEA2AC82254B38913B8C7CF7C9D |
| Echo native read-back | C1773347BD40D155EC16AC790FD8B031B7C327B5284F25E6279B9793DDD9F36D |
| Physical native read-back | 4029EF3AF45F58DFA9A0F67B66BAE201EAA1FE98B236B4D8B7383CEDA53B2DA7 |

Both offline v38 targets pass clean import/Build/Save As audits. Each strict
comparison covers 104 UDTs, seven AOIs, 132 tags, one program/task, 46 executable
bodies, the 21-step SFC graph, 352 descriptions and all **29,346 authored
initial values**, without differences. The prepared ACD was reopened/rebuilt/
exported equivalently before pinning. Source/native/prepared access audits
cover all 132 top-level tags and 46 canonical types, including both metadata
bindings. No private None member is placed in a public whole-read record.

Generated V6.2 has 225 Fields, hash
`3A243F28997A2D53EDFACA45CE489CB1BF13D2AEC53A8B88AD58F7FC053BAB43`,
revision 60965874 and two bindings. V5 stays `6DEC4C1DC2F7F78A`. These are
generated identities, not live S3d observations. The SDK helper builds with
zero warnings/errors, binds both compiler results to the source, and requires
current approval, exact pin, measured Capacity, backup and preflight. It
rechecks preflight after opening the candidate ACD, before controller changes;
rollback remains available after an interrupted authorized attempt.

## Capacity and readiness

The qualified hidden Studio driver measured two stable offline samples and
closed its review process. Normalization verifies exact model/file identity,
source/review hashes, controls, arithmetic and closure. No screenshot request.

| Image | Used Standard | Available | Total | Displayed |
|---|---:|---:|---:|---:|
| Sealed S3c baseline | 1,107,552 | 2,038,176 | 3,145,728 | 35% |
| S3d automatic measurement | 1,290,016 | 1,855,712 | 3,145,728 | 41% |

Growth is **182,464 Blocks**. Blocks are not assumed bytes; this is Studio's
offline estimate, not online memory. The held-out five-sample forecast is
1,287,360, error -2,656 (about -0.206%), with planning budget 1,550,445. S3d
is excluded from calibration. No error bound is claimed; measurement and
completed download/scan gates remain independent.

Fresh read-only guards, preflight, final checks and native inspect pass:
service/listener/identity, Run, not faulted, Remote, scanning, MANUAL=1/idle,
logged out, not restoring, restored policy and five saved documents equal
live. Preflight is recorded once, then verified; never overwrite it. The
immutable genealogy original remains
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
No authorization.json, backup or deploy marker exists; only a false template.

## Tests, retained failures and pending runtime

- AB discovery: `Ran 2062 tests in 267.800s` / `OK`.
- Root suite: `Ran 74 tests in 1.942s` / `OK`.
- Focused alarms/fixtures/sequence/status/bindings: 36 pass (2.140 s), included
  in the full suite.
- Spec and frozen-contract gates: clean.
- Strict consistency: `0 error(s), 0 warning(s)` across inventory,
  localization, parity and readsurface; CR-at-EOL whitespace gate passes.
- S2/S3a/S3b/S3c regenerations retain all four accepted hashes. Sealed captures
  replay identical snapshots at 46/94/304/647 paths.
- All thirteen predecessor canonical seals / 2,042 artifacts verify unchanged.
- Final preparation audit binds 70 source files, exact artifacts and readiness.

Retained failures: the first model run applied its default DINT arithmetic
to the shared native LINT conversion, producing three timestamp failures.
The corrected harness uses S3b's 64-bit model and checks DINT intermediates;
native compilation independently validates the code. A focused test launch
from the repository root lacked the flat tools import path and failed import;
the corrected launch passes. Logs, exit records and the earlier model remain
in the payload. No failure or authored value was waived. HMI/Flutter gates
do not apply because no HMI source changes were made.

The proposed exact session is: guarded MANUAL normalization when needed;
fresh backup; Program/download/Run of this pin; five-document restore and
31 candidate regressions with read-only decision/held/fault/sequence and
before/after blocking-reset captures; 2,125-path idle equivalence, generic
capture/native record sizes and scan; hash-checked-copy genealogy rollback;
five-document restore and 31 baseline regressions; MANUAL cleanup and final
checks. The existing fixture owns every command/stimulus. Reset observations
add no reset command and skip themselves during failure cleanup. The prepared
audit requires rendition/reset/flag coverage, active/closed events/duration
and all earlier sequence gates. WAIT_RESET and ring-wrap observations are
recorded separately from offline model coverage. The larger same-scan read
plan is unproven; S0's 2 MiB qualification does not establish that budget.

AGENTS.md §3a requires current explicit authorization for this new session.
Completed S3c approval is historical. Fault clear and clock changes remain
outside scope. Later surfaces and shipping activation remain open.
