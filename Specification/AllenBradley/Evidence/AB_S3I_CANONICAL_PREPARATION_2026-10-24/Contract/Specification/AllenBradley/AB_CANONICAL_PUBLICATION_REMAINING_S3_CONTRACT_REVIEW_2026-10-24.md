# Remaining S3 contract review — 2026-10-24

**Owner-approved for dependent offline work on 2026-10-24**
(question `call_2e1575c86f2947c59925e347cd3d0109:0`). The exact reviewed bytes and approval
are preserved in [inventory evidence](Evidence/AB_S3I_CANONICAL_INVENTORY_2026-10-24.md).
No controller operation is authorized by this approval. This review follows
the owner's request to inventory the remaining 149 paths before implementing
them. Plan §1 currently permits only D2 and the approved S3f/S3g/S3h corrections.
The finite additions below need an explicit extension; the frozen 4,437-value
capture stays immutable. The [machine-readable inventory](AB_CANONICAL_PUBLICATION_REMAINING_S3_INVENTORY_2026-10-24.json) names
every old/new path, type, value consequence and owning source, with hashes.

S3h has subsequently passed 41 candidate / 31 baseline checks and 88 paired
captures on Echo through the migration-only observation frame. That newer
[runtime evidence](Evidence/AB_S3H_CANONICAL_OBSERVATION_FRAME_RUNTIME_2026-10-24.md)
governs this review. Earlier failed coherence runs remain historical evidence.

## 1. Census: 149 actual gaps, eight D2 endpoints

| Remaining group | Frozen paths | Implementation slice |
|---|---:|---|
| Mailbox / release report | 126 | S3k: 122 report fields, three acknowledgement fields, one request Sequence |
| Line / shift status | 16 | S3i: seven Line fields and nine root shift fields |
| Production | 5 | S3k: GoodCount, NokCount, ReworkCount, Starved, Blocked |
| Feature flags | 2 | S3k: CaptureEnabled and ExportCurrentConfig |
| Total | 149 | All are explicitly enumerated in the inventory |

Raw subtraction reports 157 because prior stage inventories already use the
approved canonical D2 coordinates while the frozen capture uses old coordinates.
Normalize the frozen keys once, then subtract: 4,437 − 4,288 = 149. The eight
apparent gaps below are already covered; there is no additional Access/Policy
gap, new array-bound exception or path dropped from acceptance.

| Frozen endpoint | Existing canonical endpoint |
|---|---|
| `Access/Policy/Required[12]` | `Access/Policy/Required[11]` |
| `ActiveSteps[1]/Elapsed` | `ActiveSteps[0]/Elapsed` |
| `ActiveSteps[1]/RowIdx` | `ActiveSteps[0]/RowIdx` |
| `ActiveSteps[1]/TimedOut` | `ActiveSteps[0]/TimedOut` |
| `ModePolicy[4]/Shield` | `ModePolicy[3]/Shield` |
| `ModePolicy[4]/Style` | `ModePolicy[3]/Style` |
| `SupportedModesPublished[4]` | `SupportedModesPublished[3]` |
| `SupportedRunStylesPublished[3]` | `SupportedRunStylesPublished[2]` |

## 2. Finite proposal for the 149 frozen paths

Publish Core member names/types through PLC templates and manifest metadata;
the generic reader contains no station mapping. Propose **122 path spelling
correspondences** and **13 type corrections**, all enumerated in the inventory.
Paths not explicitly corrected keep their exact value and logical type.

- The 120 release-reason fields move from
  `HmiResponse/Report/Reasons/Reasons[n]/<field>` to the native Core array
  spelling `HmiResponse/Report/Reasons[n]/<field>`, for n=1..24 and exactly
  Description, ReasonCode, SourcePath, Kind, Bypassable. The repeated container
  is TF6100's browse spelling; Core ST_ReleaseReport has one Reasons array.
  The shared HMI's `_indexedPrefix` already accepts both forms. This is an
  explicit V2 correspondence, not a general array-path rewrite or index change.
- `Line/OwnerId` becomes `Line/Owner`, and `Line/LastUpdatedAt` becomes
  `Line/LastUpdate`, matching ST_LineStatus. Do not publish duplicate aliases.
  `Line/AppliedRevision` remains the existing AB/HMI status extension: it is
  distinct from the current Line Revision when a calendar change is pending.
- The three new DateTime fields use D7: native LDT, exact UTC instant, canonical
  UTC spelling, zero for unset. This explicitly permits ShiftStartedAt's
  `+00:00` spelling to become canonical `Z`, and ShiftEndsAt's null to become
  zero. Line LastUpdate retains its existing populated instant. Never invent
  synchronization quality or round through floating point.

| Frozen path | Legacy type | Proposed logical type |
|---|---|---|
| `CurrentShift` | Int32 | Int16 |
| `GoodCount` | Int32 | UInt32 |
| `HmiRequest/Sequence` | Int32 | UInt32 |
| `HmiResponse/AckSequence` | Int32 | UInt32 |
| `HmiResponse/Report/Count` | Int32 | Int16 |
| `Line/LastUpdatedAt` | String | DateTime |
| `Line/Revision` | Int32 | UInt32 |
| `NokCount` | Int32 | UInt32 |
| `ReworkCount` | Int32 | UInt32 |
| `ShiftEndsAt` | Null | DateTime |
| `ShiftHistoryCount` | Int32 | Int16 |
| `ShiftProductionTarget` | Int32 | UInt32 |
| `ShiftStartedAt` | String | DateTime |

UInt32 is the exact 32-bit bit pattern, as already qualified in S3g; it is not
a float conversion. This proposal does not silently expand the existing
mailbox sequence producer's range or change its change-marker handshake.
The Line revision and target owners retain their validation domains. Starved
and Blocked remain derived by the existing owning state/sequence semantics;
feature flags come from declared capabilities. No client accumulates counters,
evaluates release predicates or learns the station declaration.

## 3. Required cases absent from the frozen snapshot

The 149-key census is a coverage count, not a complete runtime schema. Approve
the following finite related surfaces as part of this contract:

**Line status.** Add ST_LineStatus.TimeSynchronized (BOOL) and SourceError
(DINT). TimeSynchronized belongs to the stored LastUpdate and must be sampled
by its owner at commit, never taken from the current clock when the client
reads. Unknown historical quality stays false. The declared valid local owner
has SourceError=0; this does not claim an implemented mirror/provider. Preserve
released backing types; any added owner stamp/quality storage is versioned.
Core LineId is STRING(40), Owner STRING(80); canonical V2 generation rejects
over-width identity rather than truncating. The legacy validator currently
permits 80 for both, so the 40-byte LineId constraint is an explicit target-
profile change, not an in-place change to a released legacy profile.

**Shift history.** The frozen snapshot contains zero rows. Publish occupied
newest-first `ShiftHistory[1..ShiftHistoryCount]`, capacity eight, using the 21
members of Core ST_ShiftRecordV3. The inventory enumerates all 168 possible
paths, including the eight additional SchemaVersion fields (UINT=3). Of the
160 existing legacy row fields, 112 have finite type corrections at maximum
occupancy: 56 UInt32, eight Int16, 32 Float32 and sixteen DateTime. The 32
unchanged-type validity flags are explicitly allowed to follow Core arithmetic
at unsigned/wrap boundaries. Preserve closing snapshots, manual-reset flags,
latched production targets, history ordering and overflow behavior. Reuse
Core Float32 operation order and UInt32 bucket wrap through the existing
owning algorithms; the independent oracle reads legacy owners, never actual
canonical values. This allowance is limited to the eight enumerated rows.

**Full command discovery.** Besides the frozen HmiRequest/Sequence, discover
the other nine ST_HmiRequest members: Kind, TargetPath, NameValue, TextValue,
User, Secret, IntValue, BoolValue and DurationMs, at Core-declared widths and
logical types. These are command argument paths, not cyclic value streams.
The PLC publishes their effective access/tier metadata. Sequence is committed
last; AckSequence is published after the complete response. One mailbox owner
dispatches a request once. Retain existing validation, login, access, route
and audit rules; an alias/bridge cannot introduce a second dispatch owner.

Secret is ephemeral and is cleared by the mailbox owner after sampling. It
must never enter generic snapshots, observation-frame evidence, logs or saved
documents. Extending the migration frame to a root containing command inputs
therefore requires an explicit, tested secret-exclusion/redaction policy before
the frame becomes readable; a whole-root copy is not sufficient. Existing
binding-specific set/provider transfers must remain discoverable and validated
until relocated at S6; adding the ten Core fields is not permission to drop
those operations. Their separate capability inventory remains an S3k gate.

**Complete reports.** Keep all 24 Core reason slots, clearing unused rows;
do not replace the frozen 24-slot surface with occupied-only publication.
The existing private legacy owner holds eight reasons, despite projecting 24
slots. Canonical V2 must use a versioned owner capable of all 24, derived from
Core MAX_RELEASE_REASONS, with saturation/completeness checks. Do not edit a
released V1 layout in place or silently discard the ninth failure. Description
and SourcePath keep their Core STRING(255) widths; text/key resolution and
module identity come from PLC-owned metadata. The pure release query and the
action continue to consume the same predicate/result.

## 4. Gates and implementation order

After approval, implement one slice at a time: S3i Line/shift, S3j fieldbus as
its own data product, S3k mailbox/reports and the seven remaining Unit fields.
The frozen genealogy has zero fieldbus paths, so closing its 149 gaps does not
accept S3j. Each slice retains full value/type checks plus the finite approved
correspondences. No broad coercion, ignored prefix, tolerance, capacity cut or
validation bypass is proposed.

The S3 exit also requires the actual press declaration in ST, SFC and ladder,
with its own declared surface, compilation/read-back, exact Capacity, native
regressions and generic equivalence. Genealogy exercising three renditions
does not transfer that acceptance to another declaration. Qualify populated
and wrapped shift history, reports with >8 and up to 24 failures, accepted/
refused mailbox requests, stale acknowledgements, parameter-before-Sequence
ordering, secret wipe/exclusion and exact saved-document restoration. New
native sessions still need their own exact-image/current authorization.

Measured S3h Capacity is 2,680,132 used / 465,596 available / 3,145,728 Blocks
(85%). The held-out forecast's planning budget exceeds the total; it is a
warning, not a measured failure for an unbuilt image. The 24 reason rows alone
need at least 12,456 payload bytes before LEN/alignment, headers, owner/frame
copies and compiled mapping logic. That lower bound is not a fit estimate.
Derive widths/bounds once, share emitted algorithms, cache event-owned data
and measure every exact candidate with the automatic Studio provider. If fit
fails, address structural duplication or explicitly revise migration order;
do not cut fields, truncate strings or weaken acceptance. The observation
frame grows with its sampled records and must be included until S6 removes it.

S4's shipping client follows Part III §3.13 **per-row/group coherence**, read
tiers and quality/freshness. It discovers coherence/access facts from the PLC,
buffers or rejects a group when required, and has no station declaration or
dependency on the migration frame. A whole-document same-scan HMI read is not
a requirement. The frame remains an acceptance instrument and is removed with
legacy contexts at S6. D9 remains: direct CIP is read-only without commissioned
CIP Security; gateway commanding requires the existing authenticated write gate.

S5–S7, persistence-medium selection after its probe, per-station gateway write
posture, physical hardware/security commissioning and push policy remain open.
This proposal neither activates V2 nor changes any deployment write setting.

## Owner decision requested

Approve this finite target contract and dependent **offline** work: the 149
enumerated frozen paths, 122 path spellings, 13 frozen type corrections, the
eleven additional static Core command/status paths, bounded 21-field/eight-row
shift schema with its enumerated arithmetic effects, Core widths and complete
24-reason versioned owner. The inventory is the exact allow-list proposal.
Implementation starts only after that decision; controller changes remain
behind separate image, Capacity, guard and current-authorization gates.
