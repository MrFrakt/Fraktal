# S3k command binding - owner choice before the request slice

Non-normative engineering review, 2026-10-25. The
[remaining-S3 semantic contract](AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md)
is already approved. Its 133 S3k frozen paths, Core argument types/widths,
24-slot reports, single dispatch owner and secret exclusion do not need to
be approved again. This review asks which physical write ABI should realize
the newly discoverable Core arguments. It authorizes no controller operation.

## Why the existing record cannot simply become the Core request

The current S9 profile writes one **89-DINT / 356-byte** Frame payload at a
500-byte connection, then Sequence separately. Its aggregate string budget
on this fixture is 312 bytes. Five decoded strings and four decoded DINT
arguments are private storage. The BoolValue DINT is overloaded for numeric
configuration values; it cannot become a native Core BOOL by annotation.
The new reader rejects that logical/native mismatch, correctly.

The current request also embeds staged ConfigSet and ConfigProvider inputs.
The generator's declared-size tally is **9,448 bytes** for the whole request,
including a 6,664-byte all-DINT provider input. This tally is not a newly
measured Template byte size. It nevertheless rules out assuming that the
whole existing record fits a 500-byte or 4,000-byte command write. Staged
services must remain separate from the bounded command payload.

Part III section 7.7 freezes the S9 physical Frame ingress and requires one
unfragmented payload write with the commit marker last. The approved S3k
review requires all ten Core request fields to be discoverable, with actual
Core types and command-only tiers, while retaining the staged services until
S6. A second independently acting request handler would violate both contracts.

## A - compact typed Core payload, one owner (recommended)

Add a versioned native command payload containing a schema header, a staged
sequence and the **nine Core arguments**, without the separately written
commit marker. The nine arguments retain Kind, TargetPath, NameValue,
TextValue, User, Secret, IntValue, BoolValue and DurationMs; their string
widths are 255/160/255/32/32, BoolValue is native BOOL and the duration keeps
UInt32 bits. No station-specific ordinal is supplied by the generic client.
The PLC resolves canonical module identities, configuration keys and model
codes through its own generated facts, then calls the existing access/release
owner. One dispatcher acts once.

The logical argument paths are discovered through the payload's actual
Symbol/Template and a versioned command-binding row, merged under the root's
HmiRequest schema. They are **command arguments, not cyclic values**. The
root's live HmiRequest.Sequence remains the separately written commit marker.
This uses the existing canonical fragment principle with an explicit schema/
command role; it does not fabricate live argument values or copy secrets
into a cyclic root.

Proposed discovery facts include root identity, protocol/schema ID, payload
symbol and argument-member path, commit symbol/path, acknowledgement source,
payload size/required connection budget, operation capability references,
read role, and secret classification. Every fact comes from the PLC; clients
do not load a station declaration, guess a symbol name or map application
ordinals. Actual field offsets/types/widths come from Templates.

The compact payload is expected to fit a 4,000-byte connection comfortably;
exact size and one-packet encoding are acceptance gates, not assumed native
measurements. A connection too small for the advertised payload plus protocol
overhead is refused for this profile. The legacy 500-byte Frame profile remains
available during migration. No payload may fragment silently.

The existing Frame/Sequence and staged-service symbols remain usable until
S6 through a temporary ingress adapter feeding that **same** owner. The adapter
does not have its own execution path. Owner-published response and sequence
facts stay consistent when either supported ingress is used alone. Simultaneous
commits are explicitly refused and acknowledged in their originating ingress;
neither is silently preferred, queued or replayed. The per-root serializer
still allows only one in-flight mutation. The detailed sequence/adapter state
table must be written and tested before its generated PLC code is qualified.

Arguments are staged in one connected write; the matching sequence is committed
last. The owner takes a bounded snapshot, validates schema/matching sequence
before interpretation, samples valid arguments privately and immediately wipes
transported secrets. Reconnect never replays a prior request. Native tests must
cover stale/mismatched sequences, competing ingress, invalid lengths/schema,
unknown targets, acknowledgement ordering and wipe paths.

Generic cyclic acquisition never reads the command payload. Schema discovery
needs only its Symbol/Template, not a sampled credential-bearing record.
Persisted captures reject unexpected argument-value records. The migration
frame samples safe sequence/response/owner facts only, not command payloads.
Explicit raw-frame/capture tests must prove exclusion of committed and
uncommitted secrets, including bytes beyond LEN. No visibility filter alone
counts as exclusion.

The cost is a new compact write profile, PLC-side Core argument resolution and
a temporary compatibility adapter. The benefit is that the generic client
serializes Core arguments directly, as the other bindings do; application
lookup and routing remain on the PLC.

## B - retain Frame as the only ingress

Keep the physical S9 payload unchanged and publish a versioned description of
its encoding, operation-specific slot transforms and all lookup tables needed
to route Core arguments to the old overloaded native slots. Core argument
discovery still uses genuine typed schema metadata and omits cyclic values.
For example, module paths become native ordinals and a numeric configuration
value moves into the old BoolValue DINT slot. Those transformations would be
interpreted by a generic binding encoder from PLC-published facts; no station
declaration is permitted.

This avoids a new command ingress and connection minimum. It retains the
312-byte aggregate string restriction on this fixture and adds a transport
mapping mechanism in both manifest and generic client. The overloaded private
slot must never be advertised as the Core native BOOL field. Staged service
discovery and secret exclusion remain mandatory. Choosing B does not permit
hard-coded per-station or per-kind application routing in the client.

## Work that does not depend on this choice

The versioned 24-reason owner and R4 dispatcher are implemented; their generated
code compiles and reads back equivalently on both v38 targets. R4 model tests
compare action/refusal and permit-report behavior against the released code.
The 133 read surfaces, exact reference, counter/wait semantics, report clearing,
Capacity/scan preparation and compatibility gates can proceed under the existing
semantic approval. S3k remains incomplete until command discovery/binding,
secret exclusion and the complete operation/service inventory are qualified.

Requested owner choice: **A**, the compact typed Core payload with one owner
and temporary legacy adapter, or **B**, the frozen Frame ingress with fully
published generic encoding/lookup metadata. This chooses the target write ABI;
it does not activate V2, authorize a download or enable a production station's
gateway writes. Current exact-image confirmation remains a later native gate.
