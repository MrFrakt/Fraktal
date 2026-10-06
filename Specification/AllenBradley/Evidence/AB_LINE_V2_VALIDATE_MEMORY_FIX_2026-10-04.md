# LineValidate memory correction — prepared press72

Client date: 2026-10-04, America/Bogota. Parent: `b2438e1`. Target:
192.168.100.89, serial 7036B510, 1769-L24ER-QB1B firmware 33.014.
This is offline correction evidence. Press70 remains the last owner-confirmed
completed-download fit baseline; press72 requires its own Verify/full download.
Earlier [preparation](AB_LINE_V2_PREPARED_2026-10-04.md) and
[ownership checks](AB_LINE_V2_OWNERSHIP_CHECK_2026-10-04.md) remain unchanged.

## Owner failure and current readback

The owner supplied:

```text
Error: Routine 'FRK_PressProgram - FRK_Press_LineValidate': Out of memory in the controller.
Complete - 1 error(s), 0 warning(s)
```

The exact compiler/download stage was not specified, and no completed press71
download is inferred. The first prior70 capture guard found a different native
manifest and refused before capturing configuration. A subsequent exact-serial,
read-only inspection found Line manifest `94E302F650BA1DB5` / `9757442`, valid
and untruncated. This is evidence of published tags, not a completed download,
running application or correct compiled code. The agent made no controller
writes, mode/fault/clock changes, downloads or gateway restarts.

Two independent current-profile captures agreed, with the same header before
and after. They preserve current records, Line configuration, ordinal 1 and
all four model banks/codes: M-100, M-200, M-050, M-101. Image SHA is
`4BD511A1CDF82C8ECEFDFCA5219B0EED162C228561668B15B3C532467F528076`,
equal to the prior prepared image. No credentials/session/class policy or
history were captured; no provider upgrade-retention claim is made.

## Correction and exact artifact

The old validator used four nested loops over row pairs, weekdays and adjacent
day offsets (336 inner candidates), plus two seven-arm day-bit CASEs. Duration
is bounded to at most 24 hours, so distinct rows can intersect only on the same
day or adjacent days. Press72 checks the six unordered row pairs instead:

- Intersect the weekday masks for same-day overlap.
- Rotate each seven-bit mask left for its next-day overlap, wrapping Sunday to
  Monday. Multiplication and conditional subtraction keep the result integral.
- Check both crossing directions with strict half-open end comparisons, so
  adjacent endpoints stay legal. Disabled rows/masks do not create intervals.

Offset/start/duration/mask range checks remain before overlap evaluation.
Whole-calendar writes/sets, permissions, revision/audit and scheduling/history
behavior are unchanged. Existing private scratch is reused; no data is added.

Exact replacement: **`C:/work/press72.L5X`**, SHA-256
`1288D13ABD42CC6729613F98BFA9E579E4BAB3A91E7F98FC2DAEA80423BA156A`.
Generation is deterministic. XML comparison finds only the `LineValidate`
routine changed from press71; all other routines, UDTs, tag initializers,
AOIs, tasks and I/O module declarations compare equal. The manifest stays
`94E302F650BA1DB5` / `9757442`, 70,520 bytes. Consequently that manifest alone
cannot distinguish the failed build from the corrected code; the owner's exact
file/full-download confirmation is required before native acceptance.

| Generation trend | Failed press71 | Prepared press72 | Change |
| --- | ---: | ---: | ---: |
| LineValidate ST source bytes | 3,434 | 2,630 | -804 (23.4%) |
| LineValidate terminators | 39 | 33 | -6 |
| LineValidate lines | 45 | 32 | -13 |
| Total ST source bytes | 305,399 | 304,595 | -804 |
| Total terminators | 4,789 | 4,783 | -6 |
| Total lines | 5,900 | 5,887 | -13 |
| Declared supported data bytes | 112,480 | 112,480 | 0 |
| RLL rungs | 20 | 20 | 0 |

Against completed press70, the prepared build remains +3,156 declared-data
bytes, +12,779 ST source bytes, +245 terminators and +318 lines. These are
generation trends, not compiled memory or proof of fit. The owner's four-user
ceiling and all capacities remain unchanged by this correction.

## Checks and next gate

**1,593 AB tests pass**, including 22 Line behavior tests; the root's 33 tool
tests pass and consistency reports zero errors/warnings. The new generated-ST
test compares 2,020 calendars with the independent interval-enumeration oracle:
all weekday pairs in all six row positions, same-day/full-day/overnight/exact
adjacency/reverse-crossing cases, plus 256 deterministic mixed-mask calendars.
Another test checks every invalid numeric bound before mask arithmetic.

**12/12 semantic mutants are killed by assertion**, without interpreter errors:
same-day and both overnight overlap omissions, false adjacency rejection, both
Sunday-wrap losses, invalid offset acceptance, weekend scheduling, unscheduled
state, snapshot/reset order, revision and complete-set validation. HMI source
hashes remain identical to the previously tested/deployed release: 495 passes,
seven expected environment skips, clean analyzer/release build. No rebuild or
redeployment was needed for this PLC-only correction.

The exact press72 SDK attempt again refused `No valid license` before project
conversion (exit 3762504530). It created no ACD, contacted no controller and
left the input hash unchanged. Owner Studio Verify/full download is the
remaining fit gate. After success, restart the existing gateway and refresh
Chrome; then establish restored native Line results and browser/retention
evidence before adding the next controller-storage feature.

The [JSON record](AB_LINE_V2_VALIDATE_MEMORY_FIX_2026-10-04.json) binds the
owner failure, inspection/captures, artifacts, size comparisons, source and
private-log hashes, mutation results and explicit pending native gates.
