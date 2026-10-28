# S3k engineering notes - mailbox, reports and remaining Unit fields

Non-normative working notes, 2026-10-25. The semantic contract is already
owner-approved in the [remaining-S3 review](AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md).
This stage is in progress. No S3k controller operation is authorized.
S3j's accepted genealogy baseline remains loaded. No commit or push.

## Inventory

The approved inventory's own stage labels select exactly **133 frozen paths**:
126 mailbox/report, five production fields and two Features flags. Of the 126,
122 describe the complete 24-slot release report, three the response and one
the request Sequence. Nine additional Core request arguments are discovery
surface, not cyclic process values. There are 39 Core operation ordinals,
including NONE=0. Supported/refused operations remain declaration-dependent.

Work: `C:/work/fraktal-ab-s3k-20261025/inventory_01/inventory_04.json`.
It derives the exact paths, existing types, approved correspondences, widths,
operation IDs and selected native profile. Earlier local inventory-script
failures are retained in that work directory. No PLC source or controller
changed during that census.

The accepted bench's native Frame is 89 DINT words (356 bytes), with 312 bytes
available for its five string arguments, within a 500-byte connected write.
Its four scalar slots are Kind, IntValue, BoolValue and DurationMs. These are
an existing transport ABI; BoolValue is also an overloaded private DINT slot
for configuration writes. It cannot be relabelled as a Core BOOL member.
The Core argument schema has STRING(255/160/255/32/32), native BOOL BoolValue,
and UInt32 duration/sequence semantics. Native decoded private storage and
Core argument discovery are distinct roles.

## Engineering direction

Retain the frozen Frame ABI, bounded single payload write and final Sequence
commit. Do not add a second dispatch owner or a second scalar-write ingress.
The proposed canonical HmiRequest includes the exact typed Core argument
schema plus declared binding-specific Frame/set/provider extensions. Only
Frame, Sequence and validated staged services are transport write endpoints;
Core argument schema members are command-only discovery, never cyclic values.
The argument binding must explicitly state the transport endpoint, logical
type, native encoding/slot/width, limits and any PLC-published lookup facts.
The generic client must not infer a station's module/config/model ordinals.
These details require a versioned wire draft and tests before qualification.

The existing physical request symbol should become an alias of the canonical
request, so old fixed-vector writers and the generic binding share the same
commit marker and owner. The owner's decoded DINT storage remains private and
outside whole-read canonical records. Core BoolValue is genuinely BOOL; a
cast annotation on the old overloaded DINT is forbidden. Native alias/import/
read-back/access and request ordering must be proven, not assumed.

The manifest must distinguish command-argument/transport records from live
values. Generic snapshots omit command-only values. Secret and transported
credential bytes must be removed before any readable observation frame or
persisted generic raw capture exists, including uncommitted payloads and
bytes beyond string LEN. A whole-root CPS followed only by a client-side
display filter is insufficient. Raw packet proof uses the PLC-redacted frame;
generic acquisition needs its own schema-driven pre-persistence redaction.

ConfigSet and ConfigProvider extensions stay discoverable and validated until
S6 gives them their replacement owners. Full operation/service inventory is
an exit gate. The direct client remains read-only without commissioned CIP
Security; gateway writes retain the authenticated per-root write gate.

## Reports and R4

The new private report owner is versioned V2, with capacity derived from Core
MAX_RELEASE_REASONS=24. The released owner remains eight entries in earlier
profiles. All append/open/close/copy emitters receive the selected declaration.
The new owner keeps an Overflow flag, refuses an invalid index without array
access and never turns an incomplete report into Released. The publisher must
clear unused Core rows and reject incomplete/corrupt reports. Generation must
check reachable report completeness against the ceiling; do not discard a
ninth or twenty-fifth failure silently.

R4 replaces repeated module CASE routing with generated module/command tables
and one bounded dispatcher. The module catalog owns accepted command ordinals
and identities. Cache the exact pre-dispatch Busy/permit facts once; queue
accepted manual intent and apply it in the existing generated module scan
path, preserving the original same-scan Execute drop and ManualCmd behavior.
Do not add a per-project call. Permit absence remains the existing HELD/device
behavior; a release query must not silently introduce a stricter action gate.
Per-instance tag wiring remains generated; behavior belongs to the dispatcher.

## Current implementation and gates

The V2 report owner and declaration propagation are implemented offline.
Eighty focused tests pass, including 9th/24th reasons, saturation, invalid
indices and reopening after overflow. S3j regenerates byte-identically at
`2F0B2CE73C2ECB69B1DD7F32BB1AE1D66550811A0EF49C1D65E9AE2C7A753EEA`.
A generated inert owner probe is being compiled/read back on both v38 targets;
this is not a native acceptance image. Work is under
`C:/work/fraktal-ab-s3k-20261025/owner_01/`.

Still required: canonical report/response/production/Features publication;
wire metadata, request alias/owner integration and secret exclusion; R4;
independent reference and synthetic boundary tests; all earlier image/capture
compatibility; full AB/root/spec/consistency gates; exact full-image native
build/read-back/access and measured Capacity; then a separately authorized
native session with all inherited regressions, >8/up-to-24 reports,
accepted/refused and stale/ordered requests, secret wipe/redaction, exact
restoration, equivalence and scan. S3 is not complete until the press's
ST/SFC/LD and real-module identity/offline gates also pass.
