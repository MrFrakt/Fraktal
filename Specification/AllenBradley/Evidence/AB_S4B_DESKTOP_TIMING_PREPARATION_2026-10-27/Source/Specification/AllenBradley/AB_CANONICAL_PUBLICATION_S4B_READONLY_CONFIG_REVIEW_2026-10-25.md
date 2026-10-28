# S4b read-only configuration discovery — contract review

Non-normative review, 2026-10-25. **Option A owner-approved; implementation and
acceptance gates remain open.** This
records a gap between D9's direct read-only posture and the existing shared HMI
configuration loader. No PLC code, download or controller write implements this
proposal. Unaffected S4b transport, manifest, decoder and snapshot work continues.

## Measured/code finding

The accepted S4a capture has **30 editable definitions, three model banks, two
configuration pages, and 16 entries in page 0**. Its SHA-256 is
`097F34474B972BD8D5B67441276DFA209E7F10365D27404A95FB3F2AE18B86C8`;
the source is `AB_S4A_COHERENCE_RUNTIME_2026-10-25/Runtime/generic_capture.json.gz`.
`readonly_config_inventory_01.json` records the read-only offline inventory.

The canonical tree exposes the current `HmiResponse/ConfigPage` window, not all
configuration rows/banks. `OpcUaRepository._queryConfigPage` calls `_request`
with `QUERY_CONFIG`, page in IntValue and model in DurationMs. The PLC's
`canonical_config.query` snapshots those selectors and commits the chosen page.
V6.7's Kind-2 service explicitly names the legacy Frame ingress. New typed
ingress still requires a payload and commit write. The R2 descriptor and full
value cache are External Access None and absent from the captured Symbol list.
Write-capability/key tables are metadata, not the missing live values.

[D9](AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md) permits direct CIP writes
only with commissioned CIP Security; Echo has none. Calling a query read-only
does not make its mailbox writes reads. Reading private contexts or guessing
symbols would also violate the canonical-publication architecture. Therefore
the direct client cannot hydrate every configuration page/model from V6.7
without changing either publication or the declared acceptance boundary.

## Recommended A — add a versioned read-only configuration view

Preserve D9, existing page/command behavior, all current Core values/types and
all S3 corrections. Add an opt-in **V6.8** read-service descriptor and a
controller-owned read-only data product. No client projection from private
contexts, formatting of private values, credential fallback or write exception.

The exact additional hash-covered manifest table is `ReadServices`, with exact
count/capacity and these columns:

| Column | Type / meaning |
|---|---|
| Kind | DINT, ordinal 1 = configuration read view |
| Version | DINT, 1 |
| RootSymbol | STRING(40), an existing discovered root Unit |
| CanonicalRoot | STRING(255), a declared data-product prefix |

No duplicated source symbol: resolve CanonicalRoot through existing DataProducts.
There is one Kind-1 view per root that owns this configuration protocol; reject
duplicates, unknown kinds/versions, unresolved roots/products and missing views.
CoreType remains descriptive rather than a dispatch key. The view is covered by
an existing V6.7 counter binding and participates in content hash/revision.

Proposed product family: `<Root>Configuration/ReadView`. This is an explicit
new AB read-service surface, not a change to the frozen legacy path census.
The field family, independent oracle and equality gate are added explicitly;
the existing 4,428-path comparison remains exact. Wire declarations choose the
actual published names; no client derives them from `<Root>`.

| View member | Native / logical contract |
|---|---|
| SchemaVersion | DINT / UInt16, fixed 1 |
| RootIdentity | STRING(80), owning qualified Unit identity |
| Revision | DINT / UInt32, existing configuration owner's page revision |
| DefinitionCount, DefinitionCapacity | DINT, exact configured descriptor allocation |
| Definitions | zero-based array of the definition record below |
| ValueCount, ValueCapacity | DINT, occupied count and declared allocation; no spare logical rows |
| Values | zero-based array, live extent ValueCount |

Each definition is the existing S3f Core configuration entry **without
ValueText and Readable**, plus `DefinitionIndex : DINT` (zero-based). All other
field types/widths/meanings are inherited from that single authoritative schema:
Scope, Item, WriteKey, WriteRevision, ConfigKind, ValueType, Writable,
RequiresReady, HasMinimum, HasMaximum, Minimum, Maximum, Unit, LabelKey,
EnumDomain, UnitCode, EnumLabelKey, ClassId, ReadLevel, WriteLevel, ModelScoped,
CaptureSource and CanCapture. No independent second field/type list is authored.

| Value-row member | Native / logical contract |
|---|---|
| DefinitionIndex | DINT, reference to Definitions |
| ModelOrdinal | DINT; 0 = active/live, positive = published model-bank position |
| ModelCode | STRING(64); empty for live row, exact bank identity otherwise |
| ValueText | STRING(255), rendered by the existing PLC formatter |
| Readable | BOOL, current PLC-owned data-class read permission |
| Revision | DINT / UInt32, owning configuration revision |

Publish one live row per definition and one bank row per model-scoped definition
per occupied model bank. Shared values are not repeated for every bank. The PLC
publishes all references/counts; invalid/duplicate references, unknown banks,
overflow and revision mismatches refuse. Published rows are coherent under the
same bounded odd/even protocol. Demand reads fetch only consumed definitions
and selected-model values; unused model capacity is not streamed.

The existing R2 configuration owner/cache remains authoritative. Reuse its
descriptor facts, numerical formatter, revision and access decisions. The
exposure is derived from that owner; do not introduce another setter, store or
business rule. Raw/unmasked cache storage stays private. An unreadable row has
empty ValueText, including immediately after access drops; no stale plaintext
survives under a new permission. Metadata and value freshness/revisions remain
separate from station liveness. Publication should refresh on owning changes;
Capacity, initialization and worst change-scan cost are measured, not assumed.

The generic read client uses this versioned service to return the same
configuration-entry semantics the repository currently hydrates through pages,
without any mailbox or provider write. Shared UI mapping may reuse the existing
ConfigManifestEntry/overlay path. This is binding protocol code, independent of
station declarations. It does not enable edits, login, release queries, model
creation or any other command on unsecured direct CIP.

Gates before acceptance: exact schemas/oracle/goldens; existing AB/HMI/root
suites; both v38 builds/read-backs/access; exact-image Capacity; approved native
session checking all definitions and model banks, access masking and revision
changes, existing regressions, bounded read/scan measurements and genealogy
rollback. A new image and write/mode vectors require separate current approval.

## Alternative B — leave complete configuration browsing pending

Keep V6.7 and strict D9. Display the currently published page accurately, mark
the remaining pages/model views unavailable, and avoid automatic query writes or
endless hydration retries. Transport/snapshot work can proceed, but full S4
configuration/desktop acceptance remains open until a gateway or commissioned
CIP Security session can perform the existing queries. This changes the stage
completion boundary; it is not full S4 acceptance or removal of the feature.

The request is to choose A (contract and dependent offline work) or B (explicit
pending configuration boundary). Neither choice authorizes a controller change,
activates V2, changes a gateway's write posture or grants commit/push permission.

Owner reply to `call_519504369cbc4895aca3f61ae5696848:0`:
**“A — publish a read-only configuration view (Recommended)”**. The V6.8 view,
explicit additional path family and dependent offline work are approved. No
download, mode/tag write or other controller change is authorized by that choice.
