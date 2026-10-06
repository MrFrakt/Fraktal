# Phase 6 - press69 compiler refusal and corrective press70

Date: 2026-10-04. [Machine-readable record](AB_PHASE6_SUBSCRIPT_FIX_2026-10-04.json).
This supersedes the prepared-artifact claim in the
[model/catalog export record](AB_PHASE6_MODEL_CATALOG_EXPORT_2026-10-04.md),
which remains unchanged history. This is offline correction evidence, not native
compile, download or model-creation acceptance.

## Failure and correction

The owner reports Studio v33 Verify refused press69 with eight errors, zero
warnings at lines 580, 583, 588 and 591. ReadLevel and WriteLevel use the same
invalid nested index:

```text
FRK_Press_DataLevels.WriteLevel[(FRK_Press_SetStaged.Ordinal[FRK_Press_SetIndex]) - 1]
Invalid array subscript specifier
```

The shared generator `fraktal_ab_data_access.check_value` now samples the already
validated dynamic ordinal minus one into `DataWork.Index`, then indexes the
level table with that scalar. The outer set/model loop owns different scratch.
The resolver has completed before this check; no additional tag, UDT member,
unrolled check or external write permission is introduced. Static ordinal checks
are unchanged. Set staging bounds/type/schema/range checks, all-or-none commit,
read/write direction, effective levels and denial audit remain enforced.

The correction covers both set load/export branches, current export and both
model-source permission directions. Five dynamic lookups gain one statement
each. Regeneration audits every emitted ST line for nested subscripts and
confirms identical native data layouts/tag byte sizes against refused press69.
The public contract hash stays unchanged because this is a logic-only fix.

## Artifact and fit

Owner replacement: **C:/work/press70.L5X**, SHA-256
`A8CE4B44DA9F09BEE1DCDA1AAC2886F70954C9FA896562D4F3F14D510B9BCF04`.
Seed SHA-256 `0E596EC140BB4FA24B089942A6AE3825ABC7B0898E06AB0D2298252FA5475E7A`.
Manifest 66C4A00ABDB4FCC3 / revision 6735008, major 4 / binding 2,
68,472 bytes; Fields 565/640, Localization 570/640. Four users remain the ceiling.

| Trend | press70 total | Delta against successful press68 | Delta against refused press69 |
| --- | --- | --- | --- |
| Declared tag data | 109,324 bytes | +2,700 | 0 |
| ST source | 291,816 bytes | +5,135 | +50 |
| ST statement terminators | 4,538 | +59 | +5 |
| ST lines | 5,569 | +54 | +5 |
| RLL rungs | 20 | 0 | 0 |

Only the HMI mailbox routine changes versus press69. These are source/data
trends, not compiled fit: AOI storage, native instruction size, object metadata
and controller reserves are excluded. Fit requires owner Studio Verify and a
completed link/download. Press68 remains the successful memory baseline.

An exact-serial read-only capture at 2026-10-04T20:39:15Z confirms serial
7036B510 and loaded manifest 7A9B9A8B59EEFD16. The current commissioned image
still has air-pressure minimum 400; its records, three model banks and selected
ordinal seed press70. The earlier owner observation of 451 remains history.
Image SHA-256 `9E418F02DDD930F80C0E51975D4BAB4693603A80FF3C5C1D73F109CE4FE98D30`.
No private credential read, PIN provisioning, controller write, mode change,
clock write, gateway restart or HMI rebuild was performed for this correction.
Configuration seeding does not establish credential-provider upgrade retention.

## Verification

- Focused platform/data/model/set suites: 87 tests pass.
- Full AB discovery with a fresh cache prefix and `-B`: 1,563 tests pass.
- New platform regression covers press and new-station template; it rejects
  nested array indices while retaining measured scalar arithmetic subscripts.
- Executed permission regression tests the first, interior and last registered
  value for read/write, allowed/denied and corrupt levels; verifies stale scratch
  replacement, unchanged loop counter and correct rejection sequence/ordinal/level.
- Four in-memory mutations are killed by assertions, with no harness errors:
  original refused index shape (1 failure), wrong index (12), swapped read/write
  direction (18), removed dynamic authorization (18). Both baselines pass and
  the original function is restored after each run. No source-file mutant persists.
- Repository consistency: zero errors/warnings; all 33 root tests pass.
  Native Verify/download acceptance remains pending.

## Owner step and continuation

Import press70, Verify Controller, complete download, restart the existing
gateway and hard-refresh Chrome. The owner's "done" authorizes only the named
guarded verification harnesses on serial 7036B510. Distinguish press70 from
press69 by file/source SHA; their contract hashes match. Never bypass hash checks
or start a write-enabled gateway to avoid the deployment boundary.

Current export, model creation and Changeover entry scope still owe native and
browser acceptance. Model creation needs an owner-selected retained code/source,
not a disposable test entry. Full port work then follows the
[completion plan](../AB_PORT_COMPLETION_PLAN_2026-10-04.md), starting with Part
traceability. The owner's added weekday/12-hour weekend shift requirement is
queued in the line-data stage; it is not implemented by press70. Control power
remains deliberately excluded. Other absent hardware/profile claims stay explicit.
