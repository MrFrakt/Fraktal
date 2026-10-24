# S3f configuration publication: contract correction proposal

Status: **proposed, awaiting owner decision**. This does not amend the accepted
V2 target, change an acceptance rule, or authorize a controller operation.
S3e's accepted image and immutable evidence remain unchanged.

## Decision requested

Approve a versioned S3f oracle correction for configuration publication:

1. Use the owning Core numeric and timestamp types at the **110 enumerated
   existing paths** in the [inventory](AB_CANONICAL_PUBLICATION_S3F_INVENTORY_2026-10-22.json).
   Preserve every represented value; forbid truncation, tolerance, Boolean
   coercion, or a general numeric equivalence exception. The typed expectation
   must be explicit at each affected path.
2. Serve a bounded configuration window through `QUERY_CONFIG`, using the
   reference window of **16 entries**. The genealogy's 30 editable entries
   require pages of **16 and 14**, with the same ordered entries and metadata.
   Compare each window against an independent reference pager and separately
   prove that their ordered union contains all 30 entries exactly once.
3. Add the **12 Core fields missing from the frozen oracle**: page Revision and
   PageIndex; persistence LastSetName and LastSetRecords; Used and SetSchema on
   each of the four set headers. Their values need independent owner/oracle
   coverage. They are additions, not permission to omit any existing content.
4. Make configuration revision and timestamps PLC-owned. A revision must change
   on the relevant configuration/model/access-view change and restart; page
   Revision must equal the revision of the data it serves. Capture the date and
   time of an operation together, then publish native LDT Unix nanoseconds.
   Do not reinterpret a time-of-day number as an epoch. Zero remains unset.
5. Publish non-empty saved-set listings, export lines, and rejection detail
   from a **validated provider response held in the PLC**. Keep file I/O behind
   the existing medium seam until S6's medium decision. The provider response
   uses a versioned, bounded transaction through the existing `HmiRequest`
   surface, under the existing session/access gates; it does not make public
   records writable or allow a generic client to rebuild station data.

These are explicit configuration-contract corrections beyond the original five
D2 bound corrections. The D2 list itself does not change. Approval would permit
implementation and an explicit revision of the plan's acceptance clause; it
would **not** approve a download, tag writes, or a new runtime session.

## Why the current rules conflict

The plan's definition of done says:

> The only exceptions are the five D2 array-bound corrections, listed one by one.

The supplied handover repeats this constraint. At S3f it conflicts with Core
type and bounded-page requirements; simply copying the current Python result
would retain the defects below. This proposal records the conflict rather than
changing the comparison gate or treating frozen zero/empty values as proof.

The independent inventory adds **801 legacy paths** to S3e's 2,154, for
**2,955 legacy paths**. Of the 801, **750** are 30 entries with 25 fields each.
The remaining **51** are the page counters/revision, durability, four set
headers, and set-document/status fields. These are census numbers for the
existing oracle, not a promised path count for the proposed page window.

| Existing path group | Legacy inferred type | Owning Core type | Paths |
|---|---|---|---:|
| Entry Minimum / Maximum | Int32 | LREAL / Double | 60 |
| Entry WriteRevision; Status/ConfigRev; set ConfigRev; WindowMs | Int32 | UDINT / UInt32 | 36 |
| Page counters; set count/document counters/record counts | Int32 | INT / Int16 | 9 |
| PendingSince; set CreatedAt | Int32, including zero placeholders | DT bound to LDT / DateTime | 5 |

Every affected path and its frozen value is listed individually. Enums remain
DINT under approved D5; no blanket narrowing of fields is proposed.

### Page shape and ownership

`fraktal_ab_projection.config_page` currently assembles all 30 entries and
unconditionally returns PageCount=1. The controller's `QUERY_CONFIG` branch
only acknowledges; it builds no page. The gateway switches model pages in
connection state and overlays a Python-computed page. Therefore the current
answer is not a PLC-owned query result.

Core §3.10.2 says that paging shall not require a full manifest buffer in the
PLC. `PL_Fraktal.MAX_CONFIG_PAGE = 16` is the **reference implementation's
constant**, not a normative rule that every binding must use 16. Sixteen is
the proposed matching reference choice. A generated buffer sized to all current
editable values would miss the bounded-window property as stations grow.

### Revision and time

`fraktal_ab_projection._config_revision` hashes a build revision and ordered
entry values/effective levels/readability, then keeps 31 bits. The frozen
genealogy value is **1,376,612,482**, reproduced exactly by the inventory.
It has no boot identity, so a restart with unchanged values produces the same
token. Core §3.10.2 requires a revision change after restart as well.

`fraktal_ab_sets.dispatch_logic` assigns PendingSince from
`FRK_<root>_NowTime`, an **HHMMSSmmm** number. For example, 123456000 occurs on
both October 21 and October 22 at 12:34:56 UTC, but these are different absolute
timestamps. An LDT assignment cannot repair the missing date. Set document
CreatedAt is separately assembled by the host broker as Unix seconds. Both need
an explicit conversion at their owning boundary; their frozen zero values
establish neither nonzero units nor timestamp correctness.

### Saved sets and document responses

`fraktal_ab_sets.empty_values` gives the ordinary projection an empty list and
empty document/rejection fields. `fraktal_ab_set_broker.process` reads the host
store and returns connection overlays for LIST/export/rejection. A pure-function
counterexample in the inventory produces count 0 from the base projection and
count 1 from a synthetic non-empty broker list, with no store/controller I/O.
Publishing only the empty defaults would not complete S3f.

This creates an earlier dependency on part of the S6 adapter migration and S3k
mailbox work. Move only the configuration provider transaction/description
needed here into S3f; retain the later full transport/mailbox and storage
retirement gates. Version its binding and keep prior generated images unchanged.

## Implementation and acceptance after approval

- Preserve the frozen 4,437-path capture and all earlier seals byte-for-byte.
  Add a separately versioned S3f expected contract; never rewrite history.
- Keep the generic Symbol/Template reader free of station imports. It decodes
  native members plus PLC-published types/extents/bindings. Query/page scheduling
  remains generic protocol work; it does not reconstruct capabilities or labels.
- Generate page text, effective levels, bounds, model selection, revision and
  timestamp conversion in owning PLC services. Reuse existing formatting/hash
  primitives where suitable; keep independent private work state and bounded work.
- For every authorized query, compare the complete expected window, values and
  types in one verified scan. Compare all 30 logical entries across a revision-
  coherent page walk; reject duplicates, omissions, stale revisions and mixing
  models. Test empty, partial, out-of-range, hidden-value and model-bank cases.
- Exercise non-empty list/save/delete/import/export and named rejection detail
  through the provider transaction, including interrupted/stale/malformed
  responses and exact restoration of files, documents and policy. No extra public
  write surface, credential publication, or direct unsecured commanding.
- Resolve D9's read-only direct path explicitly: `QUERY_CONFIG` writes a mailbox
  even though its operation is observational. No direct Echo write exception is
  implied. The read-only desktop must consume an approved read-only data route
  or obtain pages through the secured gateway; its behavior is an S4 gate.
- Run the full AB and cross-tree gates, both v38 build/read-backs, access audit,
  automatic measured Capacity and advisory forecast. Prepare and pin the ACD,
  backup/rollback helpers and fixed runtime vectors before requesting a new
  guarded controller session. Measure native sizes and scan at runtime.

## Current boundary

Only read-only source/capture analysis and this review have been performed for
S3f. **No S3f PLC code, image, download or acceptance result exists yet.**
The original five-D2-only gate remains active pending the owner's decision.
