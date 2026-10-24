# S3f configuration publication wire V6.3

Non-normative implementation draft for the owner-approved S3f correction.
V2 remains inactive. This describes the prepared candidate, not runtime acceptance.

The V6.2 header and record bindings remain. V6.3 appends ServicesCount,
ServicesCapacity and Services. Each service has Kind, Version, BuildRevision,
RequestSymbol, RequestMember and ResponseSymbol. The service rows participate in
ContentHash. Unknown versions, malformed descriptors and unsupported logical
types fail discovery. Older stage images and hashes are unchanged.

| Kind | Version | Purpose | Request member | Response |
|---|---:|---|---|---|
| 1 | 1 | Validated medium-provider result | ConfigProvider | SchemaVersion, AckSequence, Accepted, ErrorCode, RequestSequence |
| 2 | 1 | Existing QUERY_CONFIG command | Frame | SchemaVersion, AckSequence, Accepted, PageIndex, ModelIndex, Revision |

Symbol names come from the PLC manifest. Kind 2 uses the existing mailbox
command vocabulary and commit rule. These descriptors add no anonymous write
authority: D9 still applies to a direct desktop connection. A read-only direct
client's route for requesting pages is an open S4 integration gate; the authorized
bench apparatus and write-enabled gateway are distinct deployment contexts.

The root page holds 16 entries physically. Its Entries annotation has lower
bound 1 and CountPath to the live EntryCount. The deterministic genealogy walk
returns 16/14 entries at page indices 0/1, and zero at page 2. Page/model range
validation precedes selection. Only the requested window's metadata and values
are rendered. Private caches contain numeric source values/effective levels,
not a second full manifest/page buffer. Hidden values publish empty ValueText.

Core INT counters use native INT. Minimum/Maximum use LREAL; revisions and
WindowMs use DINT annotated BITSTRING32, decoded as UInt32. SetSchema is a
DINT annotated UINT16 with a checked 0..65535 domain, decoded as UInt16.
PendingSince/CreatedAt use LDT Unix nanoseconds, with zero unset. All other
corrections are explicitly enumerated in the approved inventory. Numeric
comparison stays exact, including LREAL bits during native read-back.

The PLC owns the live revision token. It seeds from controller wall-clock
microseconds and increments on numeric configuration/model-bank/catalog/
active-model/effective access-view changes. Tokens are opaque positive words;
their arithmetic/hash is not a client contract. Page Revision equals root
Status.ConfigRev. Query acknowledgement provides an independent native owner
read for the oracle. Model tests cover restart and date separation; native
restart and same-scan behavior remain runtime gates.

The provider frame is appended to the existing native HmiRequest. Its complete
V1 field/extents source is `fraktal_ab_config_provider_wire.layout()`.
Scalars and arrays are DINT. Up to four set headers and 1,616 UTF-8 bytes use
explicit lengths/offsets; those include four 80-byte names, 80-byte roots and
64-byte model codes, a 480-byte document, 80-byte reject scope and 160-byte key.
Header CreatedSeconds and ConfigRevision preserve full unsigned 32-bit words.
The generic client discovers the native Template and requires the exact V1
shape before planning any write. It has no declaration/generator/projection
imports. Writes are bounded to 80 DINTs per chunk: Commit=0, complete arguments,
then a separate positive Commit. No replay follows an interrupted transaction.

PLC validation snapshots the frame, then checks schema/build, a forward commit,
the owning native set request and acknowledgement, operation, login epoch,
session/access authority, counts, widths, header domains/duplicates and strict
UTF-8. No invalid byte sequence is repaired. Validation succeeds before any
catalog/document/rejection field is published. Refused attempts receive an
acknowledgement and burn their sequence. The catalogue flag changes the complete
four-slot listing and clears unused slots; document/rejection flags govern those
fields independently. LIST publishes an empty document as the legacy adapter
does; exporting a line preserves the latest listing. The store remains behind
the existing file-medium seam pending S6. No public canonical record becomes
writable, and no private staging/work tag is published.

Native compilation/read-back can validate layout and executable preservation.
Only the forthcoming authorized runtime can establish live access/refusal,
page/provider equivalence, scan cost and rollback acceptance.
