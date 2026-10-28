# S3k typed Core command binding - V6.6 engineering draft

Owner choice recorded 2026-10-25: **A - typed Core payload (Recommended)**,
question `call_f17f50e248404825813327f8477a84f4:0`. This selects the write ABI
and authorizes dependent offline work. It is not a download authorization.
The [approved review](AB_CANONICAL_PUBLICATION_S3K_COMMAND_BINDING_REVIEW_2026-10-25.md)
and the remaining-S3 semantic approval stay authoritative. V2 is inactive.

## Endpoints and discovery

V6.6 adds a hashed CommandBindings table. Each row publishes Version=1,
RootSymbol, PayloadSymbol, ArgumentsMember, CommitSymbol, ResponseSymbol,
ConnectionBytes, MaximumPayloadBytes and ReadRole=CommandOnly. The payload
Template owns three DINT envelope fields (SchemaVersion, ManifestRevision,
StagedSequence) and a structured Arguments member containing the nine exact
Core arguments. CommitSymbol is a separately writable DINT scalar. The payload
contains no final commit marker. A client writes it once, unfragmented, then
writes the matching sequence to CommitSymbol. Sequence and duration retain
UInt32 bits. BoolValue is native BOOL; strings retain Core byte capacities.

The profile advertises a 4,000-byte connection and a 1,024-byte maximum native
payload. The actual byte size, offsets and string/BOOL encoding come from
Templates and must fit both bounds. Actual native size and one-packet encoding
are qualification gates. Payload/header mismatch is refused; nothing truncates.
ManifestRevision binds the canonical manifest's ConfigRevision. Core argument
IntValue still carries live capability revision where Core requires it.

Schema discovery merges the argument Template under Root/HmiRequest, with a
command-only role. It does not read any payload bytes. Cyclic acquisition and
persisted captures reject command payload records, staged service input records
and unexpected records, even if their string LEN is zero. Payload Secret and
TextValue (which can carry a login preimage) are wiped across their full widths
after a committed snapshot, including malformed/colliding requests. Private
samples are wiped before acknowledgement. Uncommitted payload bytes never enter
the observation frame or a persisted generic capture. Reads remain disabled
for those records; security still depends on the commissioned transport policy.

The legacy Frame/Sequence and staged ConfigSet/ConfigProvider endpoints remain
discoverable during migration. The existing native handler remains the single
mutation owner; there is no second command CASE or alternate permission path.
The adapter translates Core identities/keys into that owner's private slots
on the PLC. Native Frame writers keep their released encoding and endpoint.

## Commit and acknowledgement state table

The preparer snapshots both commit scalars before selecting an ingress. Last
seen values are retained independently. First scan baselines the currently
visible commits and executes neither, preventing replay across Program/Run or
download. Clients submit only after discovery/connection is live. Typed commits
use UInt32 serial arithmetic: a forward difference in 1..2^31-1 is new;
duplicate, backward and half-range tokens do not execute. A refused newly seen
token is consumed, so late payload writes cannot make it execute later.

| New legacy commit | New typed commit | Result |
|---|---|---|
| No | No | No dispatch, no acknowledgement change |
| Yes | No | Snapshot/validate legacy Frame; call the one owner once; legacy ACK last |
| No | Yes | Snapshot/validate typed envelope/arguments; PLC resolution; call the one owner once; typed reply ACK last |
| Yes | Yes | Consume both tokens, refuse both, wipe both transports/samples; no action, queue or replay |

Every malformed or stale typed commit receives a refused typed reply. A late
payload without a fresh commit has no effect. The canonical root response is
the latest processed owner result. On a simultaneous refusal its presentation
uses the typed token; both transports receive their own token, Accepted=false
and the same refusal. This presentation rule never selects an action. The
typed reply is a separate read-only Core response record and remains stable
when only the legacy ingress changes. The legacy native ACK remains specific
to legacy commits. One per-root serializer still permits only one mutation in
flight. Reconnect discards in-flight work and never resubmits it.

## Gates still required

Implementation and executed state/route/boundary tests; exact operation/service
inventory; genuine native access and Template/one-packet proof; secret exclusion
for committed, malformed, uncommitted and beyond-LEN bytes; every earlier image
and capture replay; full AB/root/spec/consistency gates; both v38 targets and
strict read-back; exact-image Capacity; then separately authorized native
regressions, original-value restoration, equivalence and scan measurement.
This draft makes no native acceptance or write-enabled deployment claim.
