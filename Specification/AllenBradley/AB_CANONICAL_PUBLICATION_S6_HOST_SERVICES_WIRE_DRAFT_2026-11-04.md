# S6 host services - V6.11 engineering draft

Non-normative WP6.4 draft, 2026-11-04. O4 (plan §6.3) approves the shape: one
`HostServiceBindings` row per root and service, bounded chunks addressed by
scope and key, and the typed ingress's commit/acknowledge rules. No further
approval gates WP6.5 or the host-service part of WP6.6. This draft fixes the
native fields and state transitions the
[inventory](AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_REVIEW_2026-11-02.md)
left open. It is not a download authorization, and V2 stays inactive. No V6.11
image has been built or downloaded; the generator emits one only under the
`canonical_host_services` opt-in, which no accepted declaration sets.

## Why the flow inverts

Today the Python gateway intercepts a set command before the controller sees
it. It does the host I/O, stages `HmiRequest.ConfigSet` under its in-process
mailbox lock, and only then writes the operator's request. WP6.6 removes both
that staging and the Python gateway, so no host process sees a command first.
In V6.11 the operator's typed command reaches the PLC directly. The PLC opens
a **job** and asks the host for exactly the I/O it needs. The host is a
declaration-free document server. It reads and writes files by name and
renders or parses JSON lines. It never maps a key to an ordinal or decides a
verdict.

## Endpoints

Each root with a mutating service has one shared host ingress. ConfigSets,
ConfigProvider and LiveDocuments rows name the same four endpoints. PLC-owned
job identity therefore covers every host writer together; no process-local lock
is needed for correctness.

| Endpoint | Access | Content |
|---|---|---|
| `RequestSymbol` | Read/Write | Envelope plus one chunk (`ChunkMember`, normally `Body`) |
| `CommitSymbol` | Read/Write | DINT commit, written last |
| `ReplySymbol` | Read Only | Acknowledgement, the published job and its snapshot |
| *(private)* sample and work | None | CPS copy of the request; state table and reply buffer |

HostEvents has no writable state. Its row names only the canonical ring.

## Manifest V6.11

V6.11 is additive over V6.10. It keeps every V6.10 table and appends
`HostServiceBindingsCount`, `HostServiceBindingsCapacity` and
`HostServiceBindings` (1-1024 rows, count = capacity). The table enters the
content hash. A V6.10 record normalizes byte-for-byte as before.

| Field | Type | Rule |
|---|---|---|
| `RootSymbol` | STRING40 | A root that has a CommandBindings row |
| `Service` | DINT | 1 ConfigSets, 2 ConfigProvider, 3 LiveDocuments, 4 HostEvents; one row per root and service |
| `Version` | DINT | 1 |
| `RequestSymbol`, `ChunkMember`, `CommitSymbol`, `ReplySymbol` | STRING40 | Mutating: identifiers, distinct, shared by the root's mutating rows, never another root's. HostEvents: empty |
| `MaximumChunkBytes` | DINT | Mutating: 1 to `ConnectionBytes` - 256; the request's native size must fit. HostEvents: 0 |
| `ConnectionBytes` | DINT | Mutating: 500-4000, the minimum the client must open. HostEvents: 0 |
| `CanonicalRoot` | STRING255 | HostEvents: exactly `<root>/HostEvents`. Others: empty |
| `AccessGate` | DINT | The gate a *host-opened* job needs: LiveDocuments the set gate (11); -1 for services whose jobs only an authorized operator command opens |

`ConnectionBytes` is the one addition to the O4 field list. It follows
the existing rule that the PLC publishes every endpoint and connection bound.
A root advertises only the services it serves. ConfigSets and ConfigProvider
appear with `config_sets`, LiveDocuments with a live-document medium and
HostEvents with a ring. A PLC-memory-only project (O5) has no mutating row.

**HostEvents coherence.** The ring is read through the S1 row reader. Its
`<root>/HostEvents` prefix gets its own V6.10 owner-read row (protocol 2,
whole scope, its own revision symbol), so it never borrows another owner's
window. The validator now accepts a whole-scope owner row for a ring that its
HostEvents row names. A ring without one refuses.

## Request layout

Envelope, all DINT: `SchemaVersion` (1), `ManifestRevision` (the manifest's
ConfigRevision), `StagedSequence` (equals the commit), `Service`,
`JobSequence` (0 opens a host job), `Operation` (Core kind),
`Argument`, `Chunk`, `Final` (0/1), `Status`.

The chunk is one fixed record, `R` = 8 records per chunk:

| Members | Type | Use by chunk `Kind` |
|---|---|---|
| `Kind` | DINT | 0 none, 1 header, 2 records, 3 catalog entry, 4 text |
| `Count`, `Total` | DINT | Records in this chunk / in the document; catalog index / count; line index / count (0-64) |
| `Scope` | STRING80 | Header: root identity. Records: the records' scope. Catalog: root identity |
| `Name` | STRING80 | Header or catalog: set name. Text: rejection scope |
| `Model` | STRING64 | Header or catalog: model code |
| `SetSchema`, `ConfigRev`, `RecordKind`, `CreatedSeconds`, `Synchronized` | DINT | Header or catalog fields |
| `Keys[R]` | STRING160 | Records: write keys. Text: `Keys[0]` is the rejection key |
| `Revisions[R]`, `RecordKinds[R]`, `ValueTypes[R]`, `Values[R]` | DINT | Records: `rev`, `kind`, `type` and the parsed value |
| `Line` | STRING480 | Text: one document line |

Records carry write **keys**, not ordinals. The PLC resolves each key through
its own route table, as the typed ingress does, and stages the ordinal into the
unchanged `SetStaged` record. `dispatch_logic`'s validation then runs as it
does today, so behavior stays written once. The host translates value syntax,
for example `TRUE`/`FALSE`, or `ValueTypes` -1 for non-integer text, exactly as
`set_broker.staging` does now. Syntax is translated, never authorized. With
synthetic packing the request is 2,232 bytes, against a 3,744-byte bound.
The native size is a build gate.

## Reply layout

DINT: `SchemaVersion`, `Serial`, `AckSequence`, `Accepted`, `ErrorCode`,
`JobSequence`, `JobService`, `JobOperation`, `JobPhase`, `NextChunk`,
`JobInt`, `JobBool`, `Restoring`, `SessionPermits`. Text: `JobName`
(STRING80), `JobText` (STRING255). `Snapshot`: `Kind`, `Count`,
`ModelOrdinal`, `Date`, `Clock`, `Synchronized`, `Revision` and
`Values[N]`, with N the editable-value count.

The PLC builds the reply in its work record and publishes it with **one CPS
per scan in which it changed**. A single Read Tag (the reply fits one
connected reply) then sees the whole old or the whole new reply. `Serial` is
the accepted position a writer advances from. `AckSequence` names the last
*consumed* commit, which can be a refused stale one.

`Snapshot` replaces the host's direct reads of the private set state. It
carries exactly the values the job's document contains, which is the exposure
`ConfigSetState.Snapshot` has today; there is no new exposure class. The host
renders it declaration-free from published facts:
- `WriteCapabilities` rows give each ordinal's write key, kind and type;
- the localization table gives the key text;
- `<root>/AvailableModels` gives model codes.

`JobText` is filled only for IMPORT_CONFIG_SET pieces and wiped when the job
closes.

## State table (implemented: `fraktal_ab_host_services.ingress`/`finish`)

Each scan, in the host-service owner, before the typed command ingress:

1. **Arm.** Only a download (`Armed` = 0) seeds `Serial` and `LastSeen` from
   the commit. A later first scan abandons the active job, but still consumes
   a changed commit. A write made in program mode is therefore refused
   visibly, never swallowed. A writer that advances from `Serial` can never
   repeat the value the PLC last saw.
2. **Serial.** A commit different from `LastSeen` is new. It is accepted only
   if strictly ahead of `Serial` by less than half the uint32 circle (the
   typed ingress's 16-bit-half arithmetic). Otherwise it is `STALE_SERIAL`
   and its payload is never sampled. Rewriting the identical value is not a
   new commit at all.
3. **Sample.** `CPS(Request, Sample)`. A chunk *claims* the job when its
   `JobSequence` equals the active one. Checks, first failure wins:
   - `SchemaVersion` → `INVALID`;
   - `StagedSequence` or the re-read commit differs from the seen commit
     (a torn or second writer) → `COLLIDED`;
   - `ManifestRevision` → `STALE_REVISION`;
   - field bounds, and every text and key extent, so no service loop can
     index past `DATA` → `INVALID`;
   - `JobSequence` 0 while a job is active → `BUSY`;
   - unknown `JobSequence` → `NO_JOB`;
   - a claimed chunk with the wrong `Service`, `Operation` or `Chunk` →
     `ORDER`.

   Otherwise the chunk is accepted for the service routine.
4. **Service.** It validates the body. It then opens a job (host request),
   stages and advances, completes, or sets `INVALID`, `ACCESS` or
   `NOT_RESTORING`.
5. **Finish.** **Any refused chunk that claimed the job abandons it.** No
   stream is ever half-applied, and a host never resumes one. The PLC publishes
   `Serial`, `AckSequence`, `Accepted` and `ErrorCode`. The job window runs and
   times out to `TIMED_OUT`, clearing `JobName`/`JobText` over their full
   widths. `Outcome` (completed, abandoned, timed out) lasts exactly the scan
   that set it; the owning service reacts in that scan.

`ErrorCode`: 1 INVALID, 2 COLLIDED, 3 STALE_SERIAL, 4 STALE_REVISION, 5 NO_JOB,
6 ORDER, 7 ACCESS, 8 BUSY, 9 NOT_RESTORING. `Status` (the host's answer):
1 OK, 2 FAILED (a durable write or delete failed), 3 REFUSED (cannot serve:
not found, store full, invalid document), 4 LOST (a confirmed live document is
missing or damaged), 5 UNAVAILABLE (medium unreadable; retry, conclude nothing).

There is no retry inside the protocol. An ambiguous outcome (no reply) is
never resent: the job times out, and the operator command is refused.

## Jobs per service

Phases (`JobPhase`): 1 FETCH, 2 STORE, 3 PRESENT, 4 SNAPSHOT, 5 RESTORE. Only
an operator command opens ConfigSets/ConfigProvider jobs. A host opens
LiveDocuments jobs under `AccessGate`.

| Operation | FETCH (service 1, before validation) | PLC transaction | STORE (1, after acknowledgement) | PRESENT (2, before acknowledgement) |
|---|---|---|---|---|
| LIST_CONFIG_SETS | - | gate only | - | catalog entries |
| SAVE_CONFIG_SET | status (store full refuses) | snapshot | host saves `Snapshot`; receipt | - |
| LOAD_CONFIG_SET | header + records | validate + apply | - | - |
| DELETE_CONFIG_SET | status (must exist) | gate | host deletes; receipt | - |
| EXPORT_CONFIG_SET | header + records + the `JobInt` line | validate | - | - |
| EXPORT_CURRENT_CONFIG | - | snapshot, when the command arrives | - | header line rendered from `Snapshot` |
| IMPORT_CONFIG_SET | piece in `JobText`; the host answers its set name and, on commit, the record count | structure, as today | on commit: host saves; receipt | - |
| CREATE_MODEL (`JobBool`) | header + records of the source set | create | - | - |

The controller renders the rejection scope and key itself, from its route
table and the texts it captured while staging, so no rejection needs a PRESENT
phase. The export line travels in the FETCH, as a text chunk after the records,
and is published only if the transaction accepts the document.

FETCH and PRESENT run before the operator's acknowledgement, under a 1,500 ms
window. The HMI's command acknowledgement budget is 2 s. A missed window refuses the command
with `project.mailbox.refused.host_service_unavailable`. STORE keeps
today's asynchronous `ConfigPersist` semantics. The acknowledgement precedes it,
`Pending` lasts until the receipt or the existing 5,000 ms window, and a
missed receipt is `Failed`. While a job is active, a further set command is
refused as busy, as an ingress collision, never queued. This is the one visible
change: the Python broker serialized such commands behind its lock instead.

**LiveDocuments** (implemented: `fraktal_ab_host_sets`). A host opens these
jobs itself, with `JobSequence` 0 and `Service` 3. The reply publishes
`Restoring` (the station image is unstamped) and `SessionPermits` (the set
gate's own predicate for the logged-in session) whenever either changes. Any
host-opened job is refused `BUSY` while an operator command is parked or any
job is active.

- *Keep.* `Operation` 38 (export current), chunk 0 of `Kind` 0, `Final` 0.
  `RecordKind` names the document: 1 station, 2 line, or 0 model with `Count`
  its catalog index. Refusals:
  - `BUSY` while restoring, so defaults are never captured over documents;
  - `INVALID` for a document the station does not have.

  The SNAPSHOT job (5,000 ms window) publishes the document's values in
  `Snapshot`, with its model ordinal (the active model for the station, the
  index for a model), the time and the revision. The host writes the medium
  and closes with chunk 1, of `Kind` 0 with `Final`. Status `OK` clears the
  keep failure; any other status sets it, and `ConfigPersist.Failed`
  publishes it until a keep succeeds, as the Python keeper's overlay did. An
  operator's set command abandons a keep job, and the host keeps it later.
- *Restore.* `Operation` LOAD or CREATE_MODEL, opened by the header chunk.
  - Its `Name` is `_live`.
  - `Argument` is the bank of a model document, or the active model of the
    station document. A creation takes its code from `Model`.
  - `Status` is `OK`, or `LOST` on the station document when any document
    was lost.

  The job is refused:
  - `NOT_RESTORING` unless the controller restores;
  - `ACCESS` unless the set gate permits the session.

  Records follow as for a FETCH. A complete document resumes as a **silent
  owner pass**. The access check and the unchanged set transaction run, under
  sequence 0, and the audit records that 0. The operator's sequence,
  acknowledgement and answer do not move. The job then turns to its STORE
  phase with the verdict: `JobBool` accepted, `JobInt` the diagnostic key.
  The host closes it with a `Kind` 0 `Final` chunk. An abandoned or late job
  runs no pass at all.

  The adapter keeps `live.restore`'s order and verdicts (WP6.5):
  - models first, the station last;
  - an unreadable medium means retry;
  - a refused station answer means still restoring;
  - a denied session stops the attempt without concluding anything.

Two differences from the Python keeper:
- A restore transaction no longer appears as a mailbox command with its own
  acknowledgement. It is audited with sequence 0.
- The controller publishes a loss as `RestoreLost` with `LostPath` naming the
  root. It does not publish the lost document's key, which the keeper used to
  overlay; the adapter reports that in its own health.

**HostEvents.** Read-only, as in the coherence note above. The adapter
keeps its cursor, durability, idempotency keys and loss records. It never
acknowledges by writing the ring.

## Parking an operator command (implemented: `fraktal_ab_host_sets`)

The mailbox owner gates a set command exactly as before, the access check
included. If it needs host data, the owner **parks** it and opens the FETCH
job. A parked command writes no answer:
- the response's previous `Accepted` and `DiagnosticKey` are put back;
- `OwnerAck`, `ResponseRevision` and the typed reply do not move.

The controller keeps the command's `Kind`, `IntValue`, `BoolValue`,
`DurationMs`, `User` and set name privately. Any other command that arrives
meanwhile is served normally, and cannot change those arguments.

When the FETCH completes, the command resumes in a scan with no new typed
command, and yields to one that arrives in the same scan. The owner runs again
on the restored arguments: the access check once more, then the unchanged set
transaction (`sets.dispatch_logic`, staged from the controller's own
`HostSetStaged`). The command is refused with
`project.mailbox.refused.host_service_unavailable` if:
- its job was abandoned or timed out;
- the controller passed a first scan;
- it could only run after `PARK_MS` (1,800 ms) from arrival.

So it never runs after the HMI's 2 s budget has given up on it. A second set
command while a command is parked or any job is active is refused with
`project.mailbox.refused.host_service_busy`.

A command that cannot need the host never parks: a malformed name or user, or
a creation without a source set. It runs at once, so the transaction refuses
and audits it as it always did. A name outside ASCII stages as no name, as the
broker staged it.

FETCH chunks, as the controller checks them:
- The header is chunk 0 and only chunk 0. The stored set must answer the name
  asked for, byte for byte, or the transaction refuses it. A creation's source
  must be a model set (kind 0).
- Records chunks follow in order, 1-8 records each, never past the header's
  total. Each chunk names one scope. A scope other than this root resolves
  every record to no ordinal. A key is resolved through the typed ingress's
  route table (purpose 2) and the root through purpose 4. The first unresolved
  record's scope and key are kept for the rejection text.
- An export's line is one text chunk after the records, with `Count` the line
  index and `Total` the record total.
- `Final` is accepted only on a complete document. A host that cannot serve
  sends one `Kind` 0 chunk with `Final` and a non-OK `Status`; the transaction
  then refuses the command as invalid and audits it.
- Any other chunk is `INVALID`, and abandons the job.

Rejection text, before the acknowledgement:
- a record the controller resolved: the root and that ordinal's key text;
- an unresolved one: the scope and key it carried;
- otherwise, as the broker chose: the header root, then the model code, then
  the set name.

STORE is one `Kind` 0 chunk with `Final`. `OK` stores `StoreResult` 1; any
other status stores 2. `StoreAck` takes the pending sequence, and
`ConfigPersist` consumes the receipt and keeps its 5,000 ms window unchanged.
The STORE job publishes the snapshot the transaction took: kind, count, model,
time and the configuration revision.

**List.** A PRESENT job on ConfigProvider. Each catalog entry is one chunk,
in this order: `Kind` 3, chunk index the entry index, `Total` the entry count
(1-4), `Count` the set's record count, and `CreatedSeconds` as unsigned
seconds. An empty store answers one `Kind` 0 chunk. The controller refuses as
`INVALID`, and abandons the job, for any entry:
- out of range: schema, record kind or synchronized flag;
- with an empty name or root;
- whose text is not ASCII. Catalog text is the set documents' own frozen
  ASCII, not the provider V1 frame's UTF-8;
- that repeats a name.

It buffers the entries privately, and publishes the whole catalog with an
accepted answer in one scan. A reader never sees part of one. An unreadable
store answers non-OK, and the list transaction refuses and audits it, as the
broker's invalid staging did.

**Current export.** The transaction runs when the command arrives, taking and
auditing the snapshot as before. Only an accepted one parks, with a PRESENT job
that publishes the snapshot. The host renders the header line from published
facts alone, and answers one `Kind` 4 chunk: `Count` 0 and `Total` the
snapshot's record count. The resumed command is accepted and publishes that
line. A rendering the host cannot make, or one with the wrong total, is
refused as unavailable. The later lines come from ordinary EXPORT commands,
which the host serves from the document it rendered, as the broker's session
did.

**Import.** Each piece parks a FETCH job, carrying the piece in `JobText`
(wiped with the job), the more flag in `JobInt` and the commit in `JobBool`.
The host keeps the parse and answers one `Kind` 1 chunk:
- `Name` is the set name so far, or the broker's placeholder `(import)` before
  a header line completes;
- on commit, `Total` is the document's record count.

A piece the host cannot parse answers the same chunk with a non-OK status, and
the transaction refuses and audits it by that name. The transaction checks
the import's structure, as it did. An accepted commit opens the STORE job, and
the host saves the document it holds.

The legacy staged `ConfigSet` member and the provider V1 endpoints are still
emitted. Nothing on the set path reads them, and WP6.6 removes them.

One visible side effect: the owner's data-access rejection fields (`Reject*`)
are reset on the park scan, as on every owner pass. They belong to the
previous answer, which a client has already read.

## Implemented in this checkpoint

- `fraktal_ab_host_service_binding.py` (client, declaration-free):
  - table validation;
  - Template schema negotiation (records per chunk, snapshot extent);
  - `encode`/`write_plan`: one 0x4D request write plus a separate DINT
    commit, with Template offsets and attribute-1 structure handle, and no
    retry;
  - `next_sequence`/`outcome`.
- `fraktal_ab_host_services.py` (engineering): types, rows, tags, the generic
  `ingress`/`finish` ST and the job helpers.
- Manifest V6.11 normalization and hashing, and S1 snapshot acceptance with
  schema negotiation. The owner-read rule now admits host rings.
- The Dart `CipManifest` accepts V6.11 with the same table, ring-owner and hash
  rules. It decodes a Python-normalized golden with the identical content hash,
  and refuses each invalid table by its named rule. The HMI itself never uses
  the host-service rows.

Second checkpoint, the same day:

- The `canonical_host_services` declaration opt-in. It requires the V6.10
  owner-revision profile, a set store or a ring, and the access gate for sets.
  It emits the V6.11 header type, the `HostServiceBindings` table, the ingress
  tags and the ring's own owner row and revision. Every other declaration's
  output is unchanged.
- The ConfigSets service (`fraktal_ab_host_sets.py`) for LOAD, EXPORT,
  CREATE_MODEL, SAVE and DELETE: parking, FETCH staging, resume, rejection
  text, export line and STORE receipt, as above. It hooks the typed ingress,
  the owner's acknowledgement, `sets.cyclic` and `sets.dispatch_logic` only
  under the opt-in.
- `fraktal_ab_st_bench.py`: the emitted tags and ST routines, run in the
  executed-ST model. `test_fraktal_ab_host_sets.py` drives operator commands
  and host chunks through the generated typed-ingress, mailbox and
  configuration-restore routines in main-routine order, from a first scan.
  It does not run `ScanCanonical`: its LINT arithmetic is outside the model,
  so the test runs that routine's response cyclic instead.

Third checkpoint, the same day: LIST, EXPORT_CURRENT and IMPORT, as above, so
all eight set operations travel over V6.11. The interim refusal key is
deleted.

Fourth checkpoint, the same day: the LiveDocuments keep and restore jobs, as
above, so the opt-in now accepts the press as declared, live documents
included. `test_fraktal_ab_host_live.py` runs them on that station from a
downloaded, restoring image.

Fifth checkpoint, the same day: the WP6.5 host adapter's PLC-facing half.
- `fraktal_ab_host_adapter.py` holds `RootService`, which answers every
  ConfigSets and ConfigProvider job and runs the LiveDocuments keep and
  restore. It renders documents from published facts alone:
  - the typed command binding's capability and key tables;
  - the root's model catalog;
  - the legacy content hash, which supplies the documents' configuration
    revision.
- `fraktal_ab_host_cip.py` is its pylogix port. It discovers through the S1
  read, which now also takes the V6.11 commit symbols and request structure
  handles. Each chunk is encoded once against the Templates validated at
  discovery, with no full re-validation per chunk. The port awaits each
  acknowledgement for a bounded time and never resends.
- The declaration-free host parts moved out of the engineering modules, which
  re-export them:
  - the set documents and `FileStore` to `fraktal_ab_set_documents`;
  - `FileMedium` to `fraktal_ab_live_medium`;
  - the event cursor to `fraktal_ab_host_cursor`.

  A fresh-process test proves the adapter imports neither the declaration nor
  the generator.

Sixth checkpoint, the same day: the owner chose to port the adapter to Dart,
so it ships and is supervised like the gateway. The Python adapter and its
port are retired; the Dart one is the only one.
- `package:fraktal_opcua_client/cip_host_service.dart`: the protocol and the
  controller port. It negotiates the layout from the Templates, encodes the
  request and commit, decodes the reply, discovers through the manifest, and
  reads facts from the published tables.
- `package:fraktal_gateway/host_adapter.dart`: `RootService`, the set-document
  format with `FileStore` and `Session`, and `FileMedium`. They read and write
  the Python store's and medium's files byte for byte.
- `bin/fraktal_host_adapter.dart` is the executable, packaged beside the
  gateway. The tray starts it from an instance's optional `host_adapter.args`
  and restarts it on its own backoff, without touching the gateway's state.
- `fraktal_ab_host_bench_server.py` serves the emitted controller code over
  stdio to the Dart tests, and renders the engineering documents they compare
  with.

## Open before emission (WP6.5/WP6.6)

- The adapter's HostEvents delivery over the canonical ring.
- The S1 snapshot's V6.11 path is exercised natively: a full V6.11 capture
  exists ([session 03](Evidence/AB_S6_HOST_SESSION_03_RUNTIME_2026-11-04.md)),
  and the canonical ring in it equals the legacy ring's projection.
- Then the WP6.6 removal of the legacy staged and provider endpoints, both v38
  builds, exact-image Capacity and scan, and S6-Q. The 2 s budget, the
  one-packet reply, the CPS reply atomicity, the native request size and the
  added scan cost of parking are native claims, unproven offline.
