# AB canonical publication — supplementary S0 preparation

2026-10-21, following S1. **Prepared offline; not downloaded or authorized.**
No controller-changing operation, commit or push occurred. V2 target approval
remains the owner's 2026-10-20 approval; the stale “approval is pending” sentence
at the amendment's end is corrected. Earlier sealed snapshots remain unchanged.

## Concrete artifact and scope

Work folder:
`C:/work/fraktal-ab-s0-supplementary-20261020/prepare_da41a9b11aad4d10938044fdcdcb4005/`.
Its `RUNBOOK.md` describes the guarded sequence and all remaining gates.

- Generated combined L5X SHA-256:
  `796A56D6CEA3191A34967B3AD7A26351620D634D02D27E3CA488912ABAAB0669`.
- Prepared `s0_probe.ACD` SHA-256:
  `A468BA121687AF6C1502B04936EE4A347B7525A4430809E58B972A2BF5B88A25`.
- `capacity_review.ACD` initially matches that hash. The owner reviews this
  copy in Studio, preserving the pinned deployment ACD. No owner Capacity
  Estimate or fit approval has yet been supplied. ACD disk size is not memory.
- New session executable: `session/bin/Debug/net8.0/win-x86/S0Session.exe`.
  Offline preparation/build/read-back passes. Download requires new current
  owner authorization and a Capacity record bound to the prepared ACD hash.

Generated from unchanged L81E/v38 seed SHA-256
`FA96516C9E8D7F45874A825003756363C71DE528EDEDC0BD2766C19C1711C0C7`.
All L5X, including diagnostic cases, is generated through the existing empty-
seed builder. No generated file was hand-edited. The periodic 10 ms task has
output updates disabled, no physical I/O commands and no application consumer
of the access-test values.

The combined image publishes a controller tag `Press` with top-level `Status`
and exact browse-name identity, LREAL vectors, separate 4 KiB / 64 KiB / 2 MiB
size records, task scan telemetry and an access contrast matrix. The matrix
separates private-member and RO-parent/RW-child questions from the public root.
It has no canonical V6 manifest and is not a production canonical image.

## Tools and bounded runtime proposal

`fraktal_ab_s0_supplementary_probe.py` generates six cases: ST precision,
typed initialization, below-limit-with-extra-member, exact limit, above limit,
and combined image. StringFamily emission reuses the first S0 generator.

`fraktal_ab_s0_supplementary_measure.py` is read-only and pinned to local Echo
`601FC87B`, product 288, firmware `38.11`, plus a unique probe identity marker.
It captures Symbol/Template/type sizes, access metadata and read outcomes,
LREAL values, and actual Read Tag / Read Tag Fragmented packet offsets at
500/4000-byte connection settings. It checks the entire size-record byte image,
not just endpoints. Partial acquisitions and failures are retained in new output.

`fraktal_ab_s0_supplementary_access.py` requires explicit execution and that
same guard immediately before every write. It permits only the four fixed
`Readback`/`HmiRequest` DINT leaves under `FRK_S0S_AccessRO` and
`FRK_S0S_AccessRW`; no arbitrary host/tag/value option exists. Four stimulus
writes and at most four restorations are proposed. Changed values are restored
in `finally`, including lost-response uncertainty. Tests cover both possible
RO-parent/RW-child outcomes, denial, restoration and wrong-image refusal.
No live access vector has been executed.

The existing access auditor passes with the two RW matrix tags explicitly
classified as disposable fixture stimuli, all other public tags RO, and the
private tag None. This is not production R6 acceptance or a mailbox deployment.

## Offline findings and exact gates

| Check | Result |
|---|---|
| AB suite by tool-directory discovery | `Ran 1930 tests in 257.829s` / `OK` |
| Added supplementary tests | 9, all included in the full suite |
| Root spec/contracts/consistency tests | `Ran 74 tests in 1.832s` / `OK` |
| Spec / active V1 frozen-contract gates | clean |
| Strict consistency | 0 errors, 0 warnings |
| v38 EchoController | five positive cases build and equivalent read-back; oversize rejected |
| v38 PhysicalController | five positive cases build and equivalent read-back; oversize rejected |
| Positive native SDK audits | zero import warnings/errors; required operations present |
| Prepared ACD, reopened/rebuilt/exported | clean SDK audit, equivalent read-back, hash pinned |
| New .NET session | build succeeded, 0 warnings / 0 errors |
| `git diff --check` | exit 0, empty output |

The below-limit case (2,093,060 bytes) validates the extra DINT member itself;
the exact 2,097,152-byte UDT passes, while the otherwise matching UDT with that
extra DINT (2,097,156 bytes) is rejected during XML import on both targets.
The SDK reports `XMLSrv_E_IMPORT_ABORTED_NO_CHANGES`; attributing this rejection
to the size boundary is an inference from the controlled passing cases and
Rockwell's documented [2 MiB UDT limit](https://literature.rockwellautomation.com/idc/groups/literature/documents/rm/1756-rm094_-en-p.pdf).
It is not an absolute array-tag limit or runtime acceptance.

The precise ST forms `3.141592653589793L` and `1.0000000000000002L` compile,
and typed Decorated LREAL initializers preserve their values in read-back.
Rockwell documents the [LREAL immediate-value suffix](https://www.rockwellautomation.com/en-in/docs/studio-5000-logix-designer/37-01/contents-ditamap/instruction-set/immediate-values.html).
Full native-byte precision is still a runtime gate; the original untyped
literal's REAL-rounding finding remains valid.

Initial imports failed because the new StringFamily helper emitted DATA with
Decimal radix. Field-name/type discriminators isolated this: Name/DINT and the
existing ASCII StringFamily passed, while the Decimal StringFamily failed.
The corrected generator reuses the qualified ASCII form. All failed sources,
logs and isolation controls are retained; masked syntax cases are not treated
as conclusions about LREAL literal syntax. No failure was discarded or hidden.
The full suite also retains the existing unclosed-socket ResourceWarning from
`fraktal_ab_manifest.py:395`, observed in S0/S1; a green suite is not described
as warning-free. Expected negative-control SDK errors are separate from positive
build/audit acceptance.

## Current target and pending runtime gate

Fresh read-only service/listener/identity/fault/keyswitch guard passes: Echo is
Run, not faulted, Remote; the listener is `EmulateControlLogix5580`. A new
preflight was recorded once: genealogy manifest `6DEC4C1DC2F7F78A`, MANUAL/idle,
logged out, all five saved documents equal live, unchanged policy. It must not
be overwritten. Later verify-only checks compare against it and refuse changes
or an active HMI session.

The new SDK session requires a matching current authorization and Capacity
record before deployment. Every mode/download step rechecks target identity.
Rollback creates a fresh copy of immutable genealogy ACD SHA-256
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`,
checks the copy hash, and never opens the original in the SDK. A recorded
deployment attempt keeps rollback available after an interrupted download.
Existing exports cannot be overwritten. Fault clear remains separately gated.

After authorization and owner Capacity fit: new backup, Program/download/Run,
read-only measurement, bounded access vector/restoration, genealogy rollback,
five-document restore and 31 regressions, then final read-only state checks.
Runtime fragmentation, access, LREAL precision, task timing and exact-artifact
Capacity remain unmeasured. No HMI code changed; Flutter gates were not invoked.
S2–S7 and physical/CIP Security acceptance remain open.

The [payload manifest](AB_S0_SUPPLEMENTARY_PREPARATION_2026-10-21/manifest.json)
binds source/target snapshots, all diagnostic/native logs and generated L5X,
prepared read-back and hashes, session source, runbook and fresh preflight.
Large read-backs are losslessly compressed with original hashes. No ACD binaries
or credentials are archived. Earlier evidence and unrelated edits are untouched.
