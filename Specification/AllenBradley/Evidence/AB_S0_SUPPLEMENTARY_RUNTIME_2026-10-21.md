# S0 supplementary runtime and genealogy restoration — 2026-10-21

Append-only, non-normative evidence. The authorized supplementary session is
complete on local Echo **601FC87B**. Size/fragmentation, browse-name root,
effective parent/member access and precise LREAL vectors pass at this scope.
Genealogy is restored with **31/31 regressions** and passing final checks.
This supersedes the preparation snapshot's pending authorization/Capacity
state; the [sealed preparation](AB_S0_SUPPLEMENTARY_PREPARATION_2026-10-21.md)
remains unchanged. Shipping V1 remains active; S2–S7 are separate gates.

Payload and hashes:
[manifest.json](AB_S0_SUPPLEMENTARY_RUNTIME_2026-10-21/manifest.json).
No credential file or native ACD is archived. The owner's screenshot is
transcribed from this conversation, rather than represented as a locally
captured image.

## Authorization, Capacity and guards

The owner answered **“Approve this guarded session”** to the explicit request
for fresh backup; Program/download/Run of ACD A468BA12…B88A25; read-only
measurement; four fixed DINT access-test attempts under FRK_S0S_AccessRO/RW
with restoration; genealogy rollback; five-document restore and 31-regression
tag writes. No fault clear, physical operation, additional image deployment,
commit or push was authorized or performed.

The owner answered “usage 69%” and then supplied the Studio Capacity screenshot
for the separately prepared capacity_review.ACD. Its displayed values are:

| Studio label | Value |
|---|---:|
| Usage | 69% |
| Capacity unit | Blocks |
| Available | 955,812 |
| Used Standard | 2,189,916 |
| Total | 3,145,728 |

Available + used equals total. The exact-artifact fit gate records these
actual units and checks positive total, nonnegative used/available and exact
accounting, together with owner approval and the prepared ACD hash. The
session helper was adapted from its proposed byte-field form, rebuilt with
zero warnings/errors, and its before/after sources are retained. No block-to-
byte conversion or separate I/O metric is inferred. File size and declared
UDT size are not substituted for Studio Capacity.

The service was Running; the 127.0.0.1:44818 listener belonged to
EmulateControlLogix5580. CIP identity matched Emulate 5580 Controller,
product 288, firmware 38.11 (UI 38.011), serial 601FC87B, slot 0. Echo API
inspection reported Run, not faulted, keyswitch Remote. The preflight matched
its once-recorded genealogy state: manifest 6DEC4C1DC2F7F78A, revision 7203916,
MANUAL/idle, CurrentLevel 0, original policy and all five documents equal live.
Identity/fault/keyswitch checks ran immediately before controller mutations.
No login guard was weakened and no fault clear was needed.

## Artifact binding and deployment

Work folder:
`C:/work/fraktal-ab-s0-supplementary-20261020/prepare_da41a9b11aad4d10938044fdcdcb4005/`.
Runtime folder:
`C:/work/fraktal-ab-s0-supplementary-20261021/runtime_44309c2828a4421d8d1320512f68f12a/`.
Source commit a1163c7c7bec21988167bc971145b1366206e9ce plus the uncommitted
canonical-publication work. Unrelated owner changes were left alone.

- Generated combined source SHA-256:
  `796A56D6CEA3191A34967B3AD7A26351620D634D02D27E3CA488912ABAAB0669`.
- Prepared deployment ACD pin:
  `A468BA121687AF6C1502B04936EE4A347B7525A4430809E58B972A2BF5B88A25`.
- Fresh uploaded backup SHA-256:
  `4E47EA8E4BF727B7E42A41EB5149BFBEC9273B434ABB934F736BD87BC56BBAE8`.
- SDK saves after deployment changed the opened probe ACD to:
  `FCCFE0B831A6D13B9B54830F8F4F8F66D419C7F189622D8507BE55A38DE1705F`.
  The prepared pin was not rewritten. This completed session cannot be reused.

Backup, probe download and genealogy rollback exited 0 and passed clean SDK
audits, with zero SDK error events. Backup requires Save As in the audit:
the SDK names upload “Open Project From Controller”. Deploy/restore audits
require Download, Change Controller Mode and Save As. Both returned Run.
Probe read-back is equivalent: 10 UDTs, 13 controller tags, one program/task,
one executable body and three authored scalar initial values. The downloaded
fixture access audit also conforms; its two writable inert fixture tags are
explicit evidence inputs, not production mailboxes.

## Size, fragmentation, naming and precision

Template attribute 5 reports 4,096 / 65,536 / **2,097,152 bytes** for the three
size records. Every byte, including three separated sentinels and all zeros,
matches at both connection settings. A root named **Press**, with top-level
Status and Status.Name = Press, is discovered and decoded at 56 bytes.

Final capture measurement_03 records:

| Connection setting | Record bytes | Stream packets | Elapsed ms |
|---:|---:|---:|---:|
| 500 | 4,096 | 10 | 3.274 |
| 500 | 65,536 | 136 | 45.901 |
| 500 | 2,097,152 | 4,299 | 2,247.293 |
| 4,000 | 4,096 | 3 | 1.529 |
| 4,000 | 65,536 | 18 | 7.353 |
| 4,000 | 2,097,152 | 527 | 294.624 |

Counts exclude pylogix's preliminary type read but include the actual initial
Read Tag request. For these large records it returns status 6 with no value
bytes; Read Tag Fragmented (0x52) starts at offset zero. Each subsequent
fragment carries bytes, offsets are contiguous and the last status is 0.
This is an observed read time, not a latency guarantee or atomic snapshot proof.

The [offline preparation](AB_S0_SUPPLEMENTARY_PREPARATION_2026-10-21.md)
accepts a 2 MiB UDT on both v38 compiler targets and rejects the controlled
2 MiB + 4-byte UDT at import. The measured largest structure/tag is 2 MiB;
no global array-tag limit, physical fit or larger-tag claim follows.

Both ST L-suffixed values and typed Decorated scalar initial data preserve
**3.141592653589793** and **1.0000000000000002** exactly. The untyped ST control
still reads 3.1415927410125732, preserving the earlier REAL-rounding finding.
These qualify the precise initializer forms on this Echo/compiler baseline.

The inert 10 ms periodic task reports LastScanTime 9 us, MaxScanTime **10 us**,
OverlapCount **0** in both final acquisition samples; Scan advances from 19480
to 19715. These are native TASK measurements for this probe, not genealogy or
canonical-surface scan deltas.

## Effective access and discovery

All four authorized stimulus attempts used the fixed marker 324508639 from
original zero. Results:

| Parent | Member setting | Leaf | Write result |
|---|---|---|---|
| Read Only | Read Only | AccessRO.Readback | Privilege violation |
| Read Only | Read/Write | AccessRO.HmiRequest | Privilege violation |
| Read/Write | Read Only | AccessRW.Readback | Privilege violation |
| Read/Write | Read/Write | AccessRW.HmiRequest | Success; exact marker read back |

The successful leaf was restored to zero with one restoration write. All four
original values were verified: four stimulus attempts, one restoration write,
no whole-record write attempted. A structure with a None member rejects whole
reads (Privilege violation), while its public leaves read successfully and
its None leaf returns Path segment error. A None controller tag is absent
from Symbol browse and its explicit reads fail.

Get Attribute Single (0x0E) on Symbol attributes 2/8/10 returns unsupported
service (8). This did not establish attribute unavailability. Additional
Get Attribute List (0x03) and Get Instance Attribute List (0x55) reads succeed.
Attribute 10 is one byte: **2 for top-level RO, 0 for top-level RW** in these
controlled cases on this Echo. Attribute 2 identifies the common template;
attribute 8 is all-zero dimensions for these scalar records. Raw requests
and responses are retained; no Micro800 access semantics are assumed.

Raw Template definitions contain the same member-scope pair 45 41 for all
DINT members in the mixed-access records, including the None member.
pylogix consequently reports AccessRight 1 for each. This metadata does not
distinguish their effective permissions and is not an authorization oracle.

The measured implementation rule is therefore: every ancestor of a writable
HmiRequest must permit Read/Write; other public branches are Read Only.
Private None storage stays outside canonical records read whole. The V6
manifest publishes effective member access absent from native metadata,
derived from the same owning declarations as generated access settings.
No client gains station knowledge. The design, plan and inactive target
drafts record this correction to the previously unqualified physical encoding.
Rockwell documents whole-record restrictions and member addressing in
[1756-PM020, pp. 39 and 47](https://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm020_-en-p.pdf);
the specific attribute-10/member-byte observations above are measured findings.

## Preserved failed run, restoration and gates

measurement_01 exited 1: its verifier incorrectly rejected the header-only
partial Read Tag response as an empty data fragment. The captured root already
contained exact precise LREAL values. The repair permits only that initial
status-6 negotiation before a nonempty 0x52 stream from byte zero; it still
rejects empty fragments, gaps, overlaps and incorrect terminal status.
measurement_02 passes; measurement_03 adds the raw Template definitions and
the two list-service observations and also passes. All three outputs/logs,
before/after reader sources and regression tests are retained. No additional
download or repeated access stimulus was required for these reader changes.

Rollback opened only a fresh hash-checked copy of genealogy_current.ACD.
The immutable original remains
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
Restore read-back matches all 42 executable bodies and 21,926 authored initial
values. The authorized harness restores five live documents and passes
**31/31 rows**, including the three AUTO renditions and 21 genealogy rows.
It reports restored true, wasRestoring true, restoring false and original
policy restored. Final read-only checks pass: Run, not faulted, Remote,
advancing scans 18912 → 18938, MANUAL/idle, logged out, not restoring, original
policy and five saved documents equal live. Original preflight verify-only
also passes after restoration.

Final validation:

- AB discovery suite: `Ran 1932 tests in 253.190s` / `OK`.
- Root suites: `Ran 74 tests in 1.919s` / `OK`.
- Specification and active frozen-V1 contract gates: clean.
- Strict consistency: zero errors/warnings; git diff --check clean.
- C# session build: zero warnings/errors; focused supplement suite: 11 tests.
- Both v38 compiler/read-back gates bind the unchanged combined source hash
  in the sealed preparation; these are offline targets, not two controllers.
- SDK audits, downloaded access audit, both read-backs and restoration pass.

The full suite retains existing unclosed-socket ResourceWarnings in
fraktal_ab_manifest.py (lines 395/566); these do not fail its assertions.
No HMI code changed, so Flutter gates were inapplicable and no SDK was selected.
Separate I/O Capacity bytes, physical/security/retention acceptance and later
canonical-surface Capacity/scan/equivalence remain unmeasured. No full port
completion or shipping-V2 activation is claimed. S1's oracle exit already
passed; S2 is next, with its own prepared image and controller-operation gates.
