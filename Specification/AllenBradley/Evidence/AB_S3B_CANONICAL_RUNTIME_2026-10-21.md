# AB S3b diagnostics/timing — runtime acceptance, 2026-10-21

**S3b passes at its explicit 304-path subset.** The owner approved the exact
guarded session for local Echo `601FC87B`, ACD `634A3A86...4394EEF`.
Candidate and restored-genealogy regressions pass **31/31 each**. All 304 paths
and types match the legacy oracle under unchanged equal-even entire-scan
proof, including four active decisions, ten held and four Unit first-out
fault pairs across ST/SFC/LD. Genealogy and all five documents are restored;
final readiness passes. S3c is next. Shipping V2 remains inactive.

See [preparation](AB_S3B_CANONICAL_PREPARATION_2026-10-21.md),
[surface notes](../AB_CANONICAL_PUBLICATION_S3B_NOTES_2026-10-21.md),
[independent inventory](../AB_CANONICAL_PUBLICATION_S3B_INVENTORY_2026-10-21.json)
and [payload hashes](AB_S3B_CANONICAL_RUNTIME_2026-10-21/manifest.json).
Evidence date uses America/Mexico_City; UTC timestamps fall on October 22.
Source is `a1163c7c7bec21988167bc971145b1366206e9ce` plus uncommitted canonical
work. No commit/push is authorized or performed. No ACD or credential file
is archived.

## Target, authorization and exact artifacts

Local FactoryTalk Logix Echo, `127.0.0.1` slot 0, emulated L81E/v38.011,
product code 288, serial `601FC87B`, controller GUID
`91dec7d6-8ac3-45c9-ab2e-0d039c7006fd`. Fresh service, listener-process,
identity, Run/not-faulted/Remote keyswitch, MANUAL/idle, logout, policy and
saved/live-document checks passed before backup. Preflight was recorded in
preparation once and verified throughout this session.

The owner's current reply was “Approve this guarded S3b session”. The saved
authorization identifies the exact candidate and requested backup, mode/
download/Run, existing fixture writes, measurements, rollback and final checks.
No controller fault clear, clock set or other target was authorized or used.
The completed authorization does not authorize a future image.

| Artifact | SHA-256 |
|---|---|
| Generated S3b source | `72B9FAA0ECA228FEBAD8D19B5628A09DC06B87E739AAB3473C63E1E891CEF589` |
| Original prepared/deployed ACD pin | `634A3A86B88E666CFFCA9F530AC1D279709078BCF3E2C7EC2727B4B134394EEF` |
| ACD after SDK download/saves | `B308A9E4DE98B5E7557CDA84F55A6C57281DA161100B22D3A5F3AC7EA2079835` |
| Fresh backup ACD | `F899F066CD3E53909F2DF9B1B9A2036E9A91C7739606157E4E7F39AB924310F9` |
| Immutable genealogy original | `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084` |
| Genealogy copy after SDK restore/saves | `88DF7432B4248F64F5482B742E5A7AA6EEBDA91134F9ABBE5D8B3BB6D54862DF` |

The SDK changes the ACD it opens/saves. Original pins were preserved; the
immutable genealogy original was never opened. Restore used a fresh
hash-checked copy. Hidden detached processes preserved each SDK operation
through completion. Backup upload/Save/Save As, both downloads/mode changes,
exports and audits pass. Fresh backup inventory matches genealogy. Candidate
and restored exports compare fully equivalently; candidate R6/top-level and
all 26 canonical type/member access checks pass.

Preparation's two v38 native compiler/read-back gates remain bound to the
unchanged generated source. Only the fixture observer and its tests changed
during runtime; no regenerated PLC source or second candidate download was
needed. There were two downloads total and four explicit Program/Run changes.

## Retained failures and corrections

| Candidate run | Completed regression rows | Result |
|---|---:|---|
| 01 | 8 | First held pair exhausted the 100-attempt same-scan gate; cleanup passed |
| 02 | 31 | Behavioral rows, four decisions and ten held pairs pass; coverage audit correctly rejects absent fault pairs |
| 03 | 31 | Accepted: all required coverage, values/types and cleanup pass |
| Restored genealogy | 31 | Accepted baseline and restoration pass |

All **101 actual rows** remain in evidence: 62 accepted and 39 extra candidate
rows. Neither failed acquisition nor incomplete coverage is relabeled a pass.

Run 01 exposed connection ownership: mailbox commands set the fixture's
connection size to 500 for framed writes. Reusing it for the 12,008-byte root
makes paired acquisition span scans. An independent read-only observer now
uses 4,000 bytes; writer framing remains 500. Native instrumentation on the
same image returned the complete nine-UDT paired plan in about 3.5 ms.
Every accepted pair records independent connections with these exact sizes.
The reader retains strict protocol checks and the original 100 attempts /
five-second budget. No scan freezing, tolerance or discarded path was added.

Run 02 exposed fault lifetime: adoption drops child Execute and clears the
child's local diagnostic before the existing fault-stimulus clear. The Unit
owns the latched first-out. Run 03 observes that published Unit diagnostic at
the same pre-clear point, with nonzero reason/onset and active FaultActive.
`module` metadata names the stimulus being cleared; `diagnosticPath` names
the owning diagnostic. All four fault captures have ErrorID/DiagReason 10101,
ErrorSource 3, and include all three rendition ordinals.

These observer corrections add no simulation input, command, model creation
or regression row. The parent fixture owns all writes and cleanup. An
observation error prevents normal release but cannot prevent cleanup after
the parent records the failure. Tests cover connection isolation/closure,
wrong-target refusal, first-out ownership and failure cleanup.

The original restoration SDK audit reported the candidate hash alongside a
clean restore log. Its superseding v2 audit checks the actual restore-copy
path/hash from the completion event. Both outputs and audit script versions
remain recorded; the immutable original hash is separately verified.

## Values, types and scope

Idle equivalence and all 18 accepted active pairs compare 304 paths and 304
logical types exactly. Accepted pairs close in one or two attempts. Only the
five D2 corrections are permitted; no unused physical slot becomes an extra
path. Generic initial/final captures discover seven modules and 304 values
through Symbol/Template objects and the 142-row V6.1 manifest, without a station
declaration in the client. Metadata hash/revision are
`247BC7B4F7F630613010AA81CB12D41F8BA6C7A77FEDEB4DEAB6A95AFE9ACFF3` /
38255739; the migration oracle remains V5 `6DEC4C1DC2F7F78A`.

Diagnostic text remains a portable key. Electrical joins and timestamp
conversion are PLC-owned. Native LDT Since and DINT-millisecond timing values
match the Python projection, including logical DateTime for unset zero.
Active onset values reflect the PLC's existing unsynchronized 1998 clock; this
session did not set the clock or claim host-time accuracy. Exact conversion
and value fidelity are the acceptance results.

The fixture has one Unit/six CMs and no EM. The named missing Core status/
diagnostic and Decision fields, physical hardware/CIP Security, later S3
surfaces and shipping activation remain open. This is subset acceptance.

## Capacity and native scan observations

Qualified automatic Studio Capacity from preparation binds the original
candidate pin: **991,612 used / 2,154,116 available / 3,145,728 total Blocks**,
displayed 31%, **+174,136 Blocks over S3a**. The collector exactly reproduced
the owner's S3a reference before measuring S3b, using offline disposable copies
with preserved source hashes and closed review processes. No new screenshot
was required. Blocks are not assumed bytes or online memory.

The advisory holdout forecast was 977,992 blocks, -13,620 (-1.3735%); planning
budget 1,229,016. The sealed three-sample calibration preserves that validation.
The current observations add qualified S3b as sample 4 for future forecasts;
its zero-growth replay binds the measured baseline. Forecasts remain advisory.

| Image / native 20-sample observation | LastScanTime median (range), us | Cumulative MaxScanTime, us | Overlaps |
|---|---:|---:|---:|
| Genealogy before S3b | 99 | 1,167 | 0 |
| Prior S3a accepted image | 110 (110–111) | 1,178 | 0 |
| S3b after accepted run | 123 (122–123) | 1,190 | 0 |
| Restored genealogy after 31 rows | 99 | 1,167 | 0 |

Source is PLC GSV TASK LastScanTime/MaxScanTime; the two candidate publication
and HealthProbe samples agree. Observed delta over S3a is +13 us median and
+12 us cumulative maximum. Workloads differ: S3b includes retained failed/
retried fixtures and additional diagnostic captures. These observations do
not isolate publication cost. Samples were taken before the host test suite.

## Final checks and validation

- Full AB suite: `Ran 2011 tests in 256.800s` / `OK`.
- Observer/acquisition focused suite: `Ran 20 tests in 0.041s` / `OK`.
- Root suite: `Ran 74 tests in 1.857s` / `OK`.
- Specification and frozen-contract gates are clean; strict consistency and
  CR-at-EOL whitespace checks pass.
- Ten predecessor seals / 1,281 artifacts verify unchanged.
- Both 31-row accepted runs report restored configuration/policy and no error.
- Read-only final checks pass: Run, not faulted, Remote keyswitch, scanning,
  MANUAL/idle, logged out, not restoring, original policy restored, all five
  saved station/line/model documents equal live.
- Immutable genealogy original remains hash-unchanged. Controller fault
  clears 0; clock sets 0. No HMI implementation changed, so Flutter gates and
  SDK selection are not applicable.

Work:
`C:/work/fraktal-ab-s3b-20261021/prepare_17bd9babe817422b977d82139bae95cb/`.
Runtime:
`C:/work/fraktal-ab-s3b-20261021/runtime_117b9f6518b446aaab28d7845da5a488/`.
Do not rerun the completed session or repin its SDK-modified image. S3c uses
its own preparation, Capacity/scan/equivalence gates and current controller
authorization.
