# S6 host-service inventory and implementation boundary

Non-normative WP6.4 inventory, 2026-11-02. O4 already approves the service shape
and O5 selects host FileMedium. This records the current owners and preservation
requirements before WP6.5; it requests no further approval. No new wire type,
generator output, adapter process or controller operation is implemented here.
WP6.2 and the final WP6.3 replay still precede dependent implementation/collapse.

## Existing service owners

Paths below are relative to `FraktalCore/PLC/Allen-Bradley/tools/`.

| Service | Current owners and endpoints | Dependency to remove |
|---|---|---|
| ConfigSets | `fraktal_ab_sets.py` owns transaction validation, JSON-lines format and FileStore; `fraktal_ab_set_broker.py` stages `HmiRequest.ConfigSet`, then commits through the Frame command owner and reads ConfigSetState | `gen.editable_values(app)` maps `(scope,key)` into ordinals on the host; names, layouts, revision and authorization depend on the application |
| ConfigProvider | `fraktal_ab_config_provider.py` publishes V6 Services rows and owns validated catalog/document/rejection responses; `fraktal_ab_config_provider_wire.py` owns the common V1 layout; `fraktal_ab_config_provider_client.py` already discovers its endpoint and Template | Transport is already declaration-free, but the response producer is the declaration-bound set broker and the staged request remains nested in the legacy HmiRequest |
| LiveDocuments | `fraktal_ab_live.py` owns FileMedium, confirmed index, restore planning and Keeper; `fraktal_ab_medium.py` chooses deployment storage | `Capture`, key/catalog enumeration, editable records and restore permissions are reconstructed through the application, legacy contexts and projection |
| HostEvents | `fraktal_ab_host_events.py` owns ring validation, coherent read, event conversion, Cursor and sink delivery | Schema/capacity/kinds come from the application; raw acquisition uses `read_layout`; decoding imports projection helpers and declaration-specific resources/genealogy |

`fraktal_ab_live.py`, provider client/wire modules and their test/helper consumers
are part of this migration even though the first-match census gives only four
Python modules the AD label. A role label does not permit leaving their imports
or behavior behind. The inventory's 106 direct legacy references remains a
different measure from complete service ownership.

## Behavior to preserve

ConfigSet V1 has four stored sets, at most 64 records, 480-character bounded
JSON lines, 80-character set names, a 5,000 ms pending window and 16 audit rows.
These limits live in `fraktal_ab_sets.py`; clients derive negotiated bounds from
the new descriptor rather than copying these values. The header fields are
`set,root,schema,configRev,kind,model,records,created,clock`; each record contains
`scope,key,rev,kind,type,value`. Duplicate JSON members, invalid/non-finite JSON,
wrong shapes, range/width violations and incomplete documents refuse. The
frozen set-document text rules remain ASCII; the provider's response text is a
separate, bounded UTF-8 wire contract. Do not conflate their validators.

The broker's existing operation set is the eight kinds enumerated by
`sets.SET_KINDS`. Loads remain validate-before-apply, not sequences of individual
WRITE_CONFIG commands. Current model-load restrictions, model creation rules,
scope/key/revision/type checks, store-full behavior, import/export cursors,
interrupt handling and persistence receipts survive the transport change.

Provider V1 carries catalog, document and rejection flags independently. Its
15 bounded text fields occupy 1,616 byte values: four sets of 80/80/64-byte
identity fields, a 480-byte document and 80/160-byte rejection scope/key. It
checks request/build/login identity, operation, flags, lengths and UTF-8 before
publishing any replacement. Its existing serial domain differs from the typed
command's uint32 cursor; do not silently reinterpret that historical V1 frame.
The new versioned host-service ingress uses the typed command state table as O4
requires, while old endpoints remain intact until WP6.6.

FileStore remains at `%LOCALAPPDATA%/Fraktal/ConfigSets/<serial>-<root>`, with
the existing `FRAKTAL_AB_CONFIG_SET_DIR` deployment override. FileMedium adds its
`live/` directory, hashed JSON-lines document names and `index.json` schema 1.
The root's station/line/model keys and model catalog ordering come from PLC
metadata. Atomic replacement, confirmed-generation index, schema/revision and
content checks stay. An unreadable medium is retryable; a confirmed missing or
damaged document is explicit loss. Neither case permits capturing fresh-image
defaults over saved documents while restoring. Model/line loads precede the
station load, which stamps completion and the StoreResult. Existing authorization
still gates all restoring writes; the adapter gains no login or write bypass.

HostEvents has schema versions 1–5, capacity 1–64 when enabled, 31-bit monotonic
sequences and an explicit publisher epoch. Schemas retain their producer-specific
Part/resource/text/genealogy semantics. Equal before/body/after metadata, an even
DataRevision and validated complete row intervals remain required. The canonical
ring is read-only, on demand under Core §11.6; its adapter must not create an
operator command or mutate the ring to acknowledge local delivery. Cursor state
is per station/source/sink, locked and atomically persisted only after the sink
accepts. Delivery remains at least once with the same idempotency keys; epoch
changes and overwritten intervals remain explicit loss records. No malformed
row may be dropped to manufacture continuity.

V6.10's long owner window covers module headers and the configuration view,
not the HostEvents ring. The new service must explicitly publish the ring or
snapshot coherence mechanism it uses. An even DataRevision alone does not grant
the protocol-2 one-second window or prove scan progress; do not borrow that
permission from another owner.

## Approved shape to implement

The next unused additive manifest minor is **V6.11** after accepted V6.10. Retain
the existing owner bindings; do not extend or downgrade a released physical
header silently. `HostServiceBindings` describes enabled root/service pairs for
ConfigSets, ConfigProvider, LiveDocuments and HostEvents, including version,
endpoint roles, request/commit/reply symbols where applicable, native chunk
record, maximum chunk bytes and access gate. Do not advertise an unused service
or invent writable HostEvents state. Native field order, service-specific
read-only endpoint representation and complete chunk state vectors are still
engineering work before emission; this inventory is not an emitted ABI.

Bounded chunks are addressed by scope/key. The PLC resolves its own ordinals
and owns validation and final application. Every mutating chunk/receipt follows
the typed ingress's serial arithmetic, payload/commit agreement, commit-last,
acknowledgement, collision refusal and no replay semantics. Ambiguous outcomes
are not automatically retried. Separate gateway and host processes cannot rely
on the old Python gateway's in-process mailbox lock for correctness; PLC-owned
transaction identity and collision handling must cover them together.

One `fraktal_ab_host_adapter.py` process per controller instance discovers these
bindings through the canonical reader. It imports no declaration, generator,
station or projection. The optional `instances/<name>/host_adapter.args` is
supervised beside that instance's gateway by the tray. Existing `gateway.args`
folder discovery remains the only instance index. The generic Dart gateway
stays binding-neutral. A PLC-memory-only project runs no adapter, publishes no
ConfigPersist durability claim and produces no standing persistence alarm.

## V6.11 layouts (2026-11-04)

The [wire draft](AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_WIRE_DRAFT_2026-11-04.md)
fixes the native fields and the state table. Each root has one shared host
ingress for its mutating services. It has a request record of envelope plus
one chunk of up to eight key-addressed records, a DINT commit, and a
CPS-published reply. The reply carries the acknowledgement, the PLC-owned job
and its snapshot. An operator command opens set jobs; a host opens
LiveDocuments jobs under the set gate. HostEvents is a read-only canonical
ring with its own owner-read revision. The client binding, the generic ingress
state table, V6.11 manifest normalization, S1 acceptance and the Dart decoder
are implemented offline. Service routines, emission and the adapter remain.
See the [offline evidence](Evidence/AB_S6_HOST_SERVICE_LAYOUT_OFFLINE_2026-11-04.md)
(manifest SHA-256 `2454C42CA081DD619C2A9E319D203D27950AFC4A581792EE10317B52516FB1B2`).
Its gates ran on CRLF bytes written by the edit scripts. The
[LF restoration](Evidence/AB_S6_SOURCE_LF_NORMALIZATION_2026-11-04.md) proves
that only line endings changed and reruns every suite on the LF sources
(manifest SHA-256 `64E8B94D241A161028490B775EB6526FE6A13AE6860DE3D4AD0A362D8BDE7B90`).

## V6.11 set service (2026-11-04)

The generator emits V6.11 under the `canonical_host_services` opt-in. The
ConfigSets service carries load, export, model creation, save and delete
through PLC-owned jobs, as the wire draft's "Parking an operator command"
section records. The behavior preserved above still holds, and the set
transaction itself is unchanged:
- model-load restrictions, creation rules and range/kind/revision checks;
- the audit of every refused and accepted transaction;
- the ConfigPersist window and the store-full refusal;
- the broker's rejection text.

At that first checkpoint the import cursor, the catalog and the current export
were refused by name. See the [offline evidence](Evidence/AB_S6_HOST_SET_SERVICE_OFFLINE_2026-11-04.md)
(manifest SHA-256 `279EED7252D89657FE9775A1321F9D9DFE8AE7A6F63F4DA35C034E8B11C9175D`).
Its tests run the emitted routines over the emitted tag initializers, and 19
mutations of the emitted text are each killed.

A second checkpoint the same day carries those three as well, so all eight
set operations travel over V6.11:
- the catalog is published whole, with the list's answer;
- the current export's header line is rendered by the host from the
  published snapshot;
- an import's pieces are parsed by the host, which names the set as the
  broker did.

See the [offline evidence](Evidence/AB_S6_HOST_SET_OPERATIONS_OFFLINE_2026-11-04.md)
(manifest SHA-256 `1F290E6BE03EAEE2368DF47E256B021909824911906BC34D9826E42019B98129`).
Its first gate run failed on one surviving mutant, a test weakness that is
recorded and fixed; the second run kills all 27 mutants.

A third checkpoint carries the live-document keep and restore, so the opt-in
accepts the press as declared. The behavior preserved above still holds:
- defaults are never captured while restoring;
- the station load comes last and carries the loss;
- the adapter gains no login, since `SessionPermits` is the controller's own
  set-gate verdict and the owner re-checks it in the restore's silent pass.

A restore no longer shows as a mailbox command; it is audited under sequence
0. See the [offline evidence](Evidence/AB_S6_HOST_LIVE_DOCUMENTS_OFFLINE_2026-11-04.md)
(manifest SHA-256 `D328C10CCD016C8104F4334FAA8B3359DEA0EF8DC1E6FEA98CE48C5521C09438`):
11 live tests from a downloaded, restoring image, and 13 live mutants each
killed.

## WP6.5 host adapter (2026-11-04)

`fraktal_ab_host_adapter.py` (with its pylogix port `fraktal_ab_host_cip.py`)
is the one process per controller instance named above. It holds:
- `FileStore` at the same folder and override;
- `FileMedium`, keeping documents on change and restoring them in
  `live.restore`'s order with its verdicts;
- the import session and the export cache, per root.

It imports no declaration, generator, station or projection; a fresh-process
test asserts that. Each chunk is written through the versioned host-service
endpoint, and an unanswered one is never resent. See the
[offline evidence](Evidence/AB_S6_HOST_ADAPTER_OFFLINE_2026-11-04.md)
(manifest SHA-256 `FDC2600E9575D5DE86028BC05F0155D8B3DBFB792EF04F09D299298A71934D6E`).

HostEvents delivery and the tray are still open. The cursor's rules moved
unchanged into `fraktal_ab_host_cursor`. Reading the canonical ring into the
same batch needs equivalence proof on a native capture. The tray starts
packaged executables only, so how the Python adapter is distributed must be
decided first.

## Implementation gates still open

Before WP6.5/WP6.6, enumerate the native descriptor/chunk fields and complete
state transitions from the owners above, then test stale/wrapped/colliding
commits, truncated/reordered/interrupted chunks, changed build/login/permissions,
unknown keys, invalid documents and durable-store failure. Preserve all current
store/live-document/cursor verdicts, including restart and loss cases. Test the
fresh-process adapter import graph and installer/tray lifecycle. Then require
both v38 build/readback/access gates, exact-image Capacity and scan, unchanged
Core schema/value acceptance and S6-Q's guarded native sessions. No persistence,
event-durability or new host-service acceptance is claimed by this inventory.
