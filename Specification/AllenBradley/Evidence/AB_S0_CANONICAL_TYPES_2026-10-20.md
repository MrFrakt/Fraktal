# S0 canonical type measurement and genealogy restoration — 2026-10-20

Append-only, non-normative evidence. **The first S0 runtime measurement and
restoration are complete.** D6/D7 are selected in the design note; frozen V2
and the Part III amendment are drafts awaiting owner approval. S1 has not
started. Supplementary size/naming/access, full-precision LREAL initializer,
Capacity/native scan and later-stage acceptance gates remain open.

Payload and hashes:
[`AB_S0_CANONICAL_TYPES_2026-10-20/manifest.json`](AB_S0_CANONICAL_TYPES_2026-10-20/manifest.json).
Earlier preparation and failed stimulus regression are preserved in
[the preparation evidence](AB_S0_CANONICAL_PROBE_PREPARATION_2026-10-20.md).
No credential file or native ACD is archived.

## Authorization, target and preflight

The owner's current reply, **"logix echo back online , go on"**, followed the
explicit request covering backup, Program/Run changes, one corrected probe
download/read-only measurement, genealogy restoration and the five-document
restore/31-regression harness writes. It covers this session and this local
Echo only; a second probe download, fault clear, physical operation, commit
and push were not authorized or performed.

Source commit `a1163c7c7bec21988167bc971145b1366206e9ce`, plus the uncommitted
canonical-publication work. This continuation repaired only the S0 reader and
its tests, and prepared the evidence/design/plan/handover/contract drafts.
The owner's existing unrelated edits and prior HMI CIP edit were left alone.

The service was Running. Port 44818 on 127.0.0.1 belonged to
EmulateControlLogix5580. The CIP identity matched Emulate 5580 Controller,
product 288, firmware 38.11 (38.011), serial 601FC87B, slot 0. Echo inspection
reported not faulted and the SDK reported Run/Remote. The Unit was MANUAL and
idle, CurrentLevel 0, with manifest 6DEC4C1DC2F7F78A. All five saved documents
matched live configuration. Preflight was recorded once and verified again
before backup and deployment. No fault clear was needed.

Prepared work directory:
`C:/work/fraktal-ab-s0-20261020/readiness_20edac489b6c46e2b6229c76d400e9e7/`.
Runtime logs/scripts:
`C:/work/fraktal-ab-s0-20261020/runtime_6cf8bfb1e68e4002b5c3738feb9bf486/`.

## Backup and probe deployment

Backup upload completed with a clean SDK audit requiring Save As (the upload
itself is named Open Project From Controller). Backup ACD SHA-256:
`7E6C1326361738A3A5D4EB5A6437C44AF20A9B85808373016824E68059939B57`.

Corrected probe source SHA-256:
`F3CB9D6CA3BCAC1A7912B1B6721F46F4EC30D2FB2054BE61EA64CE8669A1D1ED`.
Prepared ACD pin:
`0D0F05980B2EE5E2F2CF25656327755D66DE171263C86067869E1E3E35AFEA85`.
The SDK guarded Program → Download → Run, with exact identity checks before
each mutation. The download and full read-back succeeded; there were no SDK
error events. The generated source and downloaded export are equivalent.

SDK saves changed the opened ACD's hash to
`65C0BD588EC177366E8B128AD7B0CCCEC1C77B09A2F8C6CF0F9224DAC73E992B`.
The original prepared pin was not rewritten. Do not reuse that deployment
session or overwrite its existing outputs for another download.

The access audit passes on both the generated source and downloaded export:
two declared public controller tags, Read Only, no command or write surface.
All authored probe members are Read Only. This is a disposable memory-only
probe with output updates disabled, no I/O and no mailbox.

## Measured types and values

The record is **1,240 bytes**; its scan count advances. Discovery ultimately
recovered eight templates, including every string width and the child record.
The following values come from captured raw bytes and independent member reads:

| Native type | Template code | Native storage/unit | Assigned/observed value |
| --- | --- | --- | --- |
| TIME | 0xD7 | 64-bit µs | T#1s500ms → 1,500,000 |
| TIME32 | 0xD6 | 32-bit µs | T32#1s500ms → 1,500,000 |
| LTIME | 0xDF | 64-bit ns | LT#1s500ms → 1,500,000,000 |
| DT | 0xC0 | 64-bit µs | LINT 1,792,413,296,123,456 → 1,792,413,296,123 |
| LDT | 0xCC | 64-bit ns | LINT 1,792,413,296,123,456,789 → the same integer |

The DT result is a **conversion finding**, not an acquisition failure. Both
raw LINT stimulus members equal their intended integers, confirming the earlier
stimulus repair. Rockwell's documented LINT-as-LDT conversion rule explains the
DT scaling. The preserved LDT value represents
2026-10-19T12:34:56.123456789Z. TIME32's physical slot has four padding bytes
before the next 8-byte member; the reader's unknown-type byte span is eight
bytes, not evidence of 64-bit TIME32 storage. Native widths and units agree
with [Rockwell's time/date type documentation](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/37-01/contents-ditamap/instruction-set/time-and-date-data-types.html).

Other measured details:

- B0–B9 have byte offsets 0–9 and bit information zero in this probe. A client
  cannot assume one universal scalar BOOL packing scheme.
- The declared BOOL[32] appears as DWORD[1], code 0x20D3. Its set bits are
  0, 5 and 31. Native word storage remains a word array in the generic decoder;
  the probe oracle compares the declared Boolean vector. Canonical publication
  needs logical type, lower bound **and element count** from the manifest.
- StringFamily widths 2, 80, 160, 255 and 480, plus standard STRING, decode by
  LEN/DATA shape. Aé is the UTF-8 byte sequence 41 C3 A9 with LEN 3. The long
  width cases preserve their end bytes. The three child records decode at an
  8-byte stride, with the selected child flags/values correct.
- LINT 0x0102030405060708 reads as exact integer 72623859790382856, above the
  range where a float can preserve every integer. LREAL is code 0xCB and
  occupies eight bytes, but the untyped decimal initializer produced
  **3.1415927410125732**, the REAL-rounded value, instead of
  3.141592653589793. Full-precision LREAL initialization is not qualified.

## Reader repairs and preserved failed checks

The first measurement raised an exception before writing a report. pylogix
omitted a referenced string template: handle 0x2D1's low byte matches atomic
BYTE. The repaired discovery follows the structure bit and full 12-bit handle,
explicitly acquires missing templates and retains earlier cache entries. It
also repairs the misleading cached member type name. No station/type name is
hard-coded to work around this collision.

The Boolean comparison now recognizes this probe's declared Boolean vector
against its native DWORD storage. The decoder itself does not reinterpret every
DWORD array as Boolean. New tests cover both behavior and the handle collision.

The second live report contains **47 comparisons, 46 equal and one DT finding**;
its exit 1 and allEqual false are retained. Review of the raw LREAL bytes then
found that the original REAL tolerance had hidden the precision loss above.
The comparison now requires an exact LREAL value. Offline replay of the same
captured bytes gives **45 equal and two explicit findings**, DT conversion and
LREAL literal precision. It requires no additional download or controller read.
Both raw captures and all reports remain intact.

Two session-helper errors are also retained: the first download log audit used
the wrong capitalization for Change Controller Mode (the SDK operation itself
exited 0); a new audit with the exact operation name is clean. The first final
check script omitted Names' required in_aoi keyword; a separate corrected
read-only script/report passes. Neither error triggered another download,
fault clear or controller repair.

## Genealogy restoration and acceptance

Restoration opened only a hash-checked copy of the original genealogy ACD.
The original remains unchanged at
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
The restore download returned Run with a clean SDK audit. Full read-back matches
all **42 executable bodies and 21,926 authored initial values**.

The authorized genealogy harness restored all five live documents through the
existing controller set validator, then passed **31/31 regressions** across
ST/SFC/LD, including 21 genealogy rows. Configuration reported wasRestoring true
and restoring false afterwards; no losses or rewritten documents were reported.
Inputs, policy, mode and session were restored.

Final read-only checks pass: Run, not faulted, scanning (13405 → 13430 in the
sample window), MANUAL, idle, logged out, not restoring, original policy, and
all five saved documents equal live. Preflight verify-only also passes against
the original pre-download record.

After the offline gates, a fresh handover check at 22:40:33 America/Mexico_City
again reports Run/not faulted and all seven restoration checks passing; the
scan sample is 98960 → 98985. The original 13405 → 13430 sample above and both
inspection/report generations are retained.

## Decisions, validation and remaining gates

D6 selects **DINT milliseconds**, manifest logical type DURATION, wire ordinal
3: exact Core width/units without native TIME's wider storage and conversion.
D7 selects **native LDT nanoseconds**: the measured timestamp vector is exact
and matches the TIA representation. These are recorded in the design note and
the inactive [V2 draft](../AB_FROZEN_CONTRACTS_V2.json), with the proposed
[Part III amendment](../AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md).

Final gates:

- AB suite: `Ran 1901 tests in 252.435s` / `OK`.
- Root spec/contract/consistency tests: `Ran 74 tests in 1.779s` / `OK`.
- AB specification and frozen-contract V1 gates: clean.
- Strict consistency: zero errors and zero warnings.
- Both v38 offline build targets: exit 0, clean import/build logs and full
  equivalent read-back. These are compiler targets, not two deployed controllers.
- Probe source/downloaded access audits: conform, empty write surface.

No HMI code changed in this continuation, so Flutter validation was not run.
Native TASK scan time and owner Capacity Estimate were not collected; payload
size and an advancing scan counter are not substitutes. No new canonical
surface has been implemented or qualified.

The first probe does not establish a maximum structure/tag size, fragmented-read
behavior, a root named Press, effective parent/member access combinations or
whether raw Symbol/Template access metadata suffices. pylogix's null Symbol
AccessRight property is not proof that the controller lacks that metadata.
Those cases, and a full-precision LREAL initializer, require a separately
prepared/gated probe and current download authorization. Physical/security and
retention acceptance remain separate. Owner V2 approval gates S1; this record
does not claim S0's supplementary questions or the overall port complete.
