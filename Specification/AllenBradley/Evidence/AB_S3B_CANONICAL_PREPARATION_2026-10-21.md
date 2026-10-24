# AB S3b diagnostics/timing — offline preparation, 2026-10-21

S3b passes its offline gates. **No S3b controller-changing operation has run
or is currently authorized.** Echo remains on restored genealogy. Runtime
equivalence, active-condition coverage, candidate/rollback regressions and
native scan measurements remain open. Shipping Part III/V1 remain
authoritative; the approved V2 target is inactive.

This follows accepted [S3a runtime](AB_S3A_CANONICAL_RUNTIME_2026-10-21.md).
See the [S3b notes](../AB_CANONICAL_PUBLICATION_S3B_NOTES_2026-10-21.md),
[independent inventory](../AB_CANONICAL_PUBLICATION_S3B_INVENTORY_2026-10-21.json)
and [payload hashes](AB_S3B_CANONICAL_PREPARATION_2026-10-21/manifest.json).
Evidence date is America/Mexico_City; timestamps cross UTC midnight.
Source commit is `a1163c7c7bec21988167bc971145b1366206e9ce` plus uncommitted
canonical work. No commit/push is authorized or performed. No ACD binary or
credential file is archived.

## Surface and ownership

The inventory was recorded before implementation from the sealed legacy
projection and S3a inventory: 94 prior paths, 42 added diagnostic paths and
168 timing paths, **304 total**. Six diagnostic fields apply to seven modules;
seven timing fields apply to eight rows on each of three commanded CMs. Only
the five approved D2 corrections remain permitted. There is no EM in this
fixture. Missing Core status/diagnostic and earlier Decision fields remain
explicit in the notes; no fabricated defaults or full-Core claim is made.

Versioned UDTs preserve S2/S3a layouts. One generated PLC resolver owns
reason/held-permit keys, electrical joins and calendar-to-LDT conversion.
Private input caches and completed-command counts bound repeated work.
`Since` is native LDT nanoseconds, logical DateTime including unset zero;
durations are DINT milliseconds. ISO UTC strings retain three to nine
fractional digits for strict equality with the oracle's millisecond spelling.
The discovery client imports no station declaration.

Multiple Service Packets batch small legacy UDTs; large records retain
fragmented reads. Complete values, including the first DINT, are validated
before decoding after the closing generation read. The equal-even whole-scan
proof, 100 attempts and five-second budget are unchanged. A read-only legacy
diagnostic returned eight complete UDTs in two wire reads (1.59 ms); this is
transport evidence, not S3b same-scan acceptance.

The inherited 31-row fixture adds read-only captures before existing held/fault
clears, with no extra stimuli/writes. Its prepared audit requires four active
decision pairs and held/fault coverage at rendition ordinals 0/1/2, each with
304 paths/types and same-scan proof. Observation failures are retained and
cannot block the parent's cleanup after failure.

## Exact artifacts and native gates

Work folder:
`C:/work/fraktal-ab-s3b-20261021/prepare_17bd9babe817422b977d82139bae95cb/`.

| Artifact | SHA-256 |
|---|---|
| `genealogy_s3b_final.L5X` | `72B9FAA0ECA228FEBAD8D19B5628A09DC06B87E739AAB3473C63E1E891CEF589` |
| `s3b_canonical.ACD` | `634A3A86B88E666CFFCA9F530AC1D279709078BCF3E2C7EC2727B4B134394EEF` |
| Echo native read-back | `7EF9F23A0AF4EF0B07D1983423D0D6CD335975A1C1DA16861BC396854341D185` |
| Physical native read-back | `FCC45F19CF19AA2A943713F895D3E9179455138A7894FE1B134C0CE6850B405D` |

Both v38 SDK targets build with 0-warning/0-error imports and clean Build/Save
As audits. They are offline targets, not physical deployments. Source, both
native exports and reopened prepared export pass R6 and all 26 canonical
type/member checks using the prior sealed top-level access allow-list.

Each read-back compares 84 UDTs, seven AOIs, 126 tags, one program/task,
45 executable bodies, the 21-step SFC graph, descriptions and **24,281 authored
initial values**, with no differences. Large Studio manifest exports omit
Decorated values; a strict schema-based L5K decoder now compares all 1,717
affected authored values, string lengths/padding and array extents. No values
were waived. Unsupported atoms fail closed.

The ACD was built/saved, reopened/rebuilt and exported equivalently before
pinning. Its deployment/review copies remain hash-unchanged. The helper builds
warning/error-clean with SDK 2.1.974 and absolute Python guard paths. It requires
current exact-artifact authorization, measured Capacity/baseline arithmetic,
fresh backup and preflight. Only a false authorization template exists; no
backup or deploy marker exists.

V6.1 metadata has 142 rows, hash
`247BC7B4F7F630613010AA81CB12D41F8BA6C7A77FEDEB4DEAB6A95AFE9ACFF3`,
revision 38255739. V5 remains `6DEC4C1DC2F7F78A`. These are generated
identities, not live S3b observations.

## Automatic Capacity

The owner requested an algorithm to avoid repeated screenshots. The
[method](../AB_CAPACITY_FORECAST_METHOD_2026-10-21.md) now supplies an advisory
forecast and an automatic Studio offline Capacity collector. The collector
opens only a unique hash-checked review copy, verifies Offline/process/file/
model identity, reads two stable Standard samples, cancels Properties and
closes its process. Normalization checks labels, controls/parentage,
arithmetic, displayed percentage, source hash preservation and closure.

Qualification reproduced all exact owner S3a values on its original pinned
review copy, then measured pinned S3b:

| Image | Used Standard | Available | Total | Displayed |
|---|---:|---:|---:|---:|
| S3a owner and automatic reference | 817,476 | 2,328,252 | 3,145,728 | 25% |
| S3b automatic measurement | 991,612 | 2,154,116 | 3,145,728 | 31% |

S3b adds **174,136 Blocks**. Blocks are not assumed bytes. This is Studio's
offline estimate, not online memory. Both source pins remain unchanged and
both review processes closed. Qualification is limited to this L81E/v38
English setup. This supplies the measured Capacity gate without another
screenshot; download/native scan gates remain open.

S3b was excluded from calibration: forecast 977,992 differs from measurement
991,612 by -13,620 (-1.3735%). Planning budget is 1,229,016. Neither holdout
establishes a guaranteed upper/error bound.

## Checks, retained failures and readiness

- Final AB suite: `Ran 2007 tests in 256.919s` / `OK`.
- Earlier AB suite before automatic-provider additions:
  `Ran 1996 tests in 259.587s` / `OK`.
- Root suite: `Ran 74 tests in 2.164s` / `OK`.
- Spec gate: `Fraktal/AB specification gate: clean.`
- Contracts gate: `Fraktal/AB frozen-contract gate: clean.`
- Strict consistency: `0 error(s), 0 warning(s)` across inventory,
  localization, parity and readsurface. CR-at-EOL whitespace check passes.
- Regenerated S2/S3a images retain accepted hashes; sealed pairs replay
  identical values/types, 46 and 94 paths respectively.
- Six fixtures: 53,969 compressed / 1,087,988 expanded bytes, within budget.
- All nine predecessor seals / 1,049 artifacts verify unchanged.

Retained failures: nonempty-seed refusal; overlong generated type name at
first native import; DINT-zero-to-LDT rejection at second native build; and
the initial final-source read-back's 1,717 L5K-only missing-value findings.
Corrected generated naming, typed LINT assignment and strict decoding resolved
these. Failed sources, raw logs and exit records remain in the payload.
The probe can exit zero with `BuildAccepted=false`; content/log audits,
not exit alone, establish native acceptance. UI exploration and qualified
collector receipts are preserved too.

Read-only guards/final checks pass: service/listener/identity, Run, not faulted,
Remote keyswitch, scanning, MANUAL/idle, logged out, not restoring, restored
policy and five saved documents equal live. Preflight was recorded once, then
verified. Immutable genealogy ACD remains
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
No S3b HMI changes: Flutter gates/SDK selection are not applicable. Physical
hardware/security, missing Core fields and later surfaces remain open.

## Next session

The runbook prepares fresh backup; Program/download/Run of pinned S3b; five-
document restore and 31 candidate regressions with read-only decision/held/
fault pairs; 304-path idle equivalence/native scan; hash-checked-copy genealogy
rollback; five-document restore and 31 baseline regressions; final checks.
AGENTS.md §3a requires current explicit authorization for this new session.
Completed S3a approval is historical. Fault clear is separate. No commit/push.
