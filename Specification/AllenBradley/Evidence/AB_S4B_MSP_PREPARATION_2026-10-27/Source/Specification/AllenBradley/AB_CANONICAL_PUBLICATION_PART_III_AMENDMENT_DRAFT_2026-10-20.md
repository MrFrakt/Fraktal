# Part III canonical publication amendment — approved target draft

2026-10-20. **Owner-approved target; not yet effective.** This is proposed replacement text for the named
clauses, based on [S0 evidence](Evidence/AB_S0_CANONICAL_TYPES_2026-10-20.md)
and [the V2 draft](AB_FROZEN_CONTRACTS_V2.json). Part III and frozen contracts
V1 remain authoritative for the shipping implementation. Approval settles the
target contract; it does not establish implementation or runtime conformance.
S1–S7 retain the implementation plan's gates.

Owner approval on 2026-10-20: “Approve drafts and proceed to S1”. This approves
the target contract and S1 work; additional controller changes require their
own current authorization. The archived S0 review drafts remain historical.

The owner-approved S3f and S3g finite corrections extend this target draft.
S3g binds the 64 consumed OEE values to exact Core REAL arithmetic, 101
numeric paths to the full UInt32 domain and 35 to Int16. Its separately
approved 224 dependent values follow those Core arithmetic/count semantics;
all 631 other S3g values/types stay exact. The [plan §1](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md)
links the enumerations. This records the approved target, without activating
Part III/V2 or establishing runtime acceptance.

## AB §3.13 — discoverable per-row/group coherence (S4 target extension)

Owner-approved on 2026-10-25: **“A — publish existing counter bindings
(Recommended)”**. The [S4 coherence review](AB_CANONICAL_PUBLICATION_S4_COHERENCE_REVIEW_2026-10-25.md)
defines V6.7's exact hash-covered `ReadCoherenceBindings` columns and validation.
It exposes the existing scan guard rather than adding a cyclic publication
owner. Every root/data-product prefix has a published revision symbol, protocol
and mutation interval. Clients derive none of them from station knowledge.

Coherence is per consumed row/group and tier. Equal even counters enclose each
bounded native acquisition, including its first counter request; the window
must be shorter than the published interval. A session establishes progress
before claiming fresh scanning data. Failed acquisition degrades quality and
does not retain mixed bytes as a Good value. No whole-document same-scan claim
or dependency on the migration observation frame is introduced.

The opt-in V6.7 image is implemented, compiled and qualified on Echo at S4a's
initial module Status/product-row scope; see the
[runtime evidence](Evidence/AB_S4A_COHERENCE_RUNTIME_2026-10-25.md).
S4b full desktop/tier and active-workload acceptance remain open. This extension
does not activate Part III/V2 or authorize another controller session.

## AB §3.10.2 — read-only configuration service (S4b target extension)

The owner selected option A in the
[S4b review](AB_CANONICAL_PUBLICATION_S4B_READONLY_CONFIG_REVIEW_2026-10-25.md).
V6.8 adds hash-covered `ReadServices` rows with `Kind`, `Version`, `RootSymbol`
and `CanonicalRoot`; counts/capacities are exact. Kind 1/version 1 refers to an
explicit data product, never a type-name or station-name convention.

That product publishes SchemaVersion, RootIdentity, Revision, definition and
value counts/capacities, Definitions and Values. Definitions extend the existing
configuration-entry metadata with DefinitionIndex and omit ValueText/Readable.
Each value row publishes DefinitionIndex, ModelOrdinal, ModelCode, ValueText,
Readable and Revision. Ordinal zero is live; occupied banks use positive
ordinals. Logical extents/count references are PLC-published and validated.

The existing configuration owner remains authoritative. Publication is derived
on change and applies the same formatting, access masking and revision. A read
level drop clears every unreadable ValueText buffer across its full width;
unused rows cannot retain plaintext. Unmasked caches stay private. Clients
reject incomplete references, duplicate rows, invalid banks, mixed revisions
and mismatched capacities. Configuration reads do not renew station liveness.
They yield between bounded worker requests, fetch consumed definitions and
selected-bank values, and perform no mailbox/provider write on unsecured CIP.

This additive target has an independent oracle for the new path family. It
does not relax the existing frozen-path comparison. The opt-in image is
compiled/read-back and measures 65% offline Capacity; native S4b qualification
and desktop acceptance remain pending. The first S4b attempt stopped in Template
discovery before candidate writes and rolled back with 31/31 baseline checks;
the parser correction then passed discovery in the approved retry. That retry
refused its first root sample before candidate writes and again restored
genealogy with 31/31 baseline/final checks. The following diagnostic session
retained the rejected snapshot: correct identity and 976 Good values, but oldest
fast-row age 2,065.752 ms. It completed rollback after a retained 22-check baseline
failure, residual cleanup and one unchanged 31/31 retry. The offline client
lookup correction preserves all reads and production guards; native S4b remains
open. See the [diagnostic attempt](Evidence/AB_S4B_ROOT_DIAGNOSTIC_ATTEMPT_2026-10-26.md)
and [lookup retry preparation](Evidence/AB_S4B_LOOKUP_RETRY_PREPARATION_2026-10-26.md).
V2/Part III remain inactive; no new session is authorized by the contract choice.

The lookup retry then passed 41 candidate cases and 87 raw-read replays.
Dart met the original freshness limit for 140 snapshots, then stopped on a
payload-free Uncertain root Status row. Genealogy and 31 baseline/final checks
were restored. The [sealed attempt](Evidence/AB_S4B_LOOKUP_RETRY_ATTEMPT_2026-10-26.md)
claims no native S4b or desktop acceptance. A bounded pacing correction and
failed-attempt metadata are [prepared offline](Evidence/AB_S4B_COHERENCE_RETRY_PREPARATION_2026-10-26.md),
with the same attempt/deadline/quality rules and strict root qualification.

The paced attempt then passed 41 cases/87 replays and reached 587 non-Bad
cyclic rows before one Bad value. The strict observer stopped; genealogy and
31 baseline/final checks were restored. The [sealed run](Evidence/AB_S4B_COHERENCE_RETRY_ATTEMPT_2026-10-26.md)
records the missing Bad-branch snapshot explicitly. A verified slow-expiry
implementation mismatch (10 seconds versus the published 15) is corrected
offline using one unchanged profile for aging and its envelope. Rejected Bad
snapshots are now retained. See the [freshness preparation](Evidence/AB_S4B_FRESHNESS_RETRY_PREPARATION_2026-10-26.md).
No publication contract or advertised budget is changed; native/desktop
acceptance remains open and V2/Part III remain inactive.

The [freshness run](Evidence/AB_S4B_FRESHNESS_RETRY_ATTEMPT_2026-10-26.md)
then passed 41 cases/87 replays and 884 completed cyclic samples without Bad
values, before a root-coherence refusal. Its recorded three attempts ended
after 6,237 us within one publication phase. Genealogy and all 31 baseline
and final checks are restored. The [prepared reader correction](Evidence/AB_S4B_READER_RETRY_PREPARATION_2026-10-26.md)
allows the desktop plan 20 attempts instead of three, retaining its one-second
deadline and every per-row proof/freshness condition. Source age starts before
accepted pre-counter I/O; the processing bracket ends before age calculation.
These are client policy/bookkeeping changes, not a publication ABI amendment
or acceptance claim. Native pages, detail, acquisition/scan and desktop
acceptance remain open; no new controller session is authorized here.

The [bounded reader run](Evidence/AB_S4B_READER_RUNTIME_2026-10-26.md)
passes 41 cases/87 replays, 902 entirely Good cyclic samples, four configuration
pages (1,100 exact oracle scalar/type comparisons), targeted details and
5,407-path idle/generic acquisition. Genealogy and all 31 baseline/final checks
are restored. This is functional native proof, with desktop and scan review
still open: cumulative native maximum 10,033 us and one overlap on a 10 ms
task, already present at the earliest paired capture. The cause is unproven;
no limit is widened or counter cleared. V2/Part III remain inactive.

The [desktop/scan diagnostic run](Evidence/AB_S4B_DESKTOP_SCAN_RUNTIME_2026-10-26.md)
repeats functional proof with 41 cases/87 replays and 895 entirely Good Dart
samples. It first observes the one overlap between probe observations 1 and
17, before the observer/desktop; scalar polling does not identify the exact
scan or cause. The desktop helper's success is rejected: its native result
contains zero modules and two screenshots, including a stale/empty overview.
Genealogy, the original documents and 31 baseline/final checks are restored.

The [new offline preparation](Evidence/AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26.md)
withholds the uninitialized read-only view on the cold first Run scan, clears
all value buffers and starts normal formatting next scan. Retained initialized
first scans still mask access immediately. No wire type, tags or initializer
change. The strict desktop qualification now requires LIVE, complete nonempty
coverage at every capture, with parent semantic validation and refresh/forest
diagnostics. These corrections pass 2,339 AB tests, both v38 builds/read-backs,
65% Capacity and the standalone desktop positive/stale-refusal checks. No
native timing improvement or live desktop acceptance is claimed. This image
requires fresh exact-image authorization; V2/Part III remain inactive.

The [2026-10-27 cold-image attempt](Evidence/AB_S4B_COLD_DESKTOP_ATTEMPT_2026-10-27.md)
passes 41 cases/87 replays and records zero TASK overlaps with a 9,002 us
maximum through the candidate fixture. The Dart observer refuses a root Status
at 1,035.46 ms after 68 Good samples; its payload stays withheld. Desktop and
later acquisition/final timing are skipped, and genealogy/31 baseline/final
checks are restored. The same-image [offline retry](Evidence/AB_S4B_STATUS_ORDER_PREPARATION_2026-10-27.md)
schedules discovered module Status groups at the end of cyclic walks, retaining
all reads, values/types, targeted semantics, row proofs and freshness limits.
The regression, 648 HMI tests (12 skipped), analyzer, Windows and lockfile gates
pass. No native improvement is claimed before a new authorized qualification.
V2/Part III remain inactive.

The [Status-order qualification](Evidence/AB_S4B_STATUS_ORDER_ATTEMPT_2026-10-27.md) remains open at the recorded
read-only desktop Echo scope: 41 cases /87
replays /910 Dart samples, 0 live desktop views,
0 generic values. Reader remains open, desktop
remains open, scan remains open. Genealogy,
the original documents and 31 baseline/final checks are restored. The correction
changes only cyclic group order; wire reads, values/types, row proofs and freshness
limits remain unchanged. V2/Part III remain inactive pending later gates; this
evidence grants no physical, retained-power or CIP Security acceptance.

The [startup diagnostic](Evidence/AB_S4B_STARTUP_DIAGNOSTIC_ATTEMPT_2026-10-27.md) completes 41 cases/87 replays and 906
entirely Good observer samples, but the initial desktop complete sample is
refused at 1,003.130 ms: 982.641 ms source +16.992 ms transit +3.497 ms local
processing. Zero live views are accepted. The preserved primary exception
has no secondary null assertion. TASK trace maximum is 8,937 us /zero overlaps;
remaining acquisition/final timing are skipped. Genealogy, the exact original
documents and 31 baseline/final checks are restored.

The [parallel-reader attempt](Evidence/AB_S4B_PARALLEL_READER_ATTEMPT_2026-10-27.md) adds a bounded pool of four
serial-pinned read-only connections, keeping a full row proof on one connection
and at most one request outstanding per socket. Count barriers and revision
ordering protect out-of-order replies. It records 1,288 entirely Good samples,
295.514 ms median /493.517 ms maximum age and 25/41 fixture cases, with 53 exact
raw-record replays. The legacy Part reader refuses its three bounded reads at
the SFC adopted-fault record; desktop/full acquisition/final timing are not
reached. TASK trace maximum is 8,994 us /zero overlaps. Genealogy, original
documents and 31 baseline/final checks are restored. Full S4b acceptance is open.

The [Part-read diagnostic](Evidence/AB_S4B_PART_READ_DIAGNOSTIC_ATTEMPT_2026-10-27.md) completes 41 cases/87 exact replays
and 1,991 entirely Good observer samples. All 218 traced Part calls succeed;
the earlier exhausted refusal is not reproduced or explained. Desktop reaches
LIVE with all seven modules, then fails the overview freshness gate at
1,233.352 ms. Zero views are accepted; full acquisition/final timing are skipped.
TASK trace maximum is 9,002 us /zero overlaps. Genealogy, original documents
and all 31 baseline/final checks are restored.

The [refill attempt](Evidence/AB_S4B_REFILL_ATTEMPT_2026-10-27.md) passes 41 cases/87 exact replays, the busy
witness and 3,144 entirely Good samples. Desktop initially LIVE then STALE at
1,428.145 ms; later acquisition/final timing skipped. TASK maximum 9,003 us /
zero overlaps. Genealogy/31 baseline/final checks pass; approval consumed.
S4b remains open. The [read-only diagnostic](Evidence/AB_S4B_HOST_TIMING_2026-10-27.md) establishes MSP support,
not atomicity or canonical acceptance. The [prepared client](Evidence/AB_S4B_MSP_PREPARATION_2026-10-27.md) batches
only body/count reads between separately completed counter requests, retaining
all value/type/proof/freshness/read-only rules and the original fallback.
685 HMI/12 skips, 73 focused, analyzer/Windows/locked dependencies and 74 root
tests pass. Native qualification needs new approval. No PLC/source/layout or
Capacity change; V2/Part III remain inactive.

## AB §1, §2.1 and §4.1 — reference profile

The reference profile is a CIP Security-capable CompactLogix 5380 or
ControlLogix 5580 at firmware v37 or above. Each different family/revision
requires the applicable compiler, type-map, transport and runtime qualification.
The development bench is FactoryTalk Logix Echo emulating a 1756-L81E at
38.011; simulation evidence is identified as such and grants no physical fit,
retention, I/O or CIP Security acceptance.

The 1769-L24ER-QB1B/v33 is retired as a reference target. Its dated evidence
and V1 contract remain history at their recorded scope. A future constrained
profile uses this same canonical architecture and declares its reductions;
it does not introduce a station-specific projection architecture.

## AB §3.8 — type map V2

The PLC publishes the logical Core contract itself. Type bindings are defined
by frozen contracts V2; the manifest supplies logical information absent from
the controller's native type system. A client never infers logical type or
array bounds from a member's name or a station declaration.

- BOOL members are native. A reader honors template offsets and bit metadata.
  Native BOOL arrays may be described as DWORD storage; the manifest supplies
  their logical Boolean type, lower bound and element count. Only that logical
  extent enters the canonical snapshot.
- SINT, INT, DINT, REAL, LINT and LREAL are native. Core enum ordinals remain
  generated DINT constants. Int64 transport uses exact integers/decimal
  strings and never passes through a float. Generation preserves the declared
  floating-point precision; an untyped REAL literal widened into LREAL is not
  a conforming full-precision initializer. Supplementary S0 qualifies the ST
  `L` suffix and typed Decorated LREAL initial data on Echo v38: pi and
  1.0000000000000002 are preserved exactly.
- **D6: Core TIME binds to DINT milliseconds**, with the manifest logical type
  DURATION and wire ordinal 3. Its signed 32-bit range and millisecond units
  match Core directly. Native TIME32 has microsecond units and insufficient
  range for this contract; native TIME has 64-bit microseconds. Neither is
  substituted for the published DINT representation. An internal native time
  value is converted and range-checked by its owning provider before publication.
- **D7: Core timestamps bind to native LDT**, 64-bit Unix nanoseconds, mapped
  to UTC DateTime; zero retains Core's unset meaning. Snapshot encoding is an
  ISO UTC string with three to nine fractional digits, or numeric zero for
  unset. Retain at least three digits to match the existing millisecond
  spelling; retain additional digits when required for exact nanoseconds.
  Conversion from a microsecond clock is owned once by its provider. A LINT
  supplied to the time-type assignment is a nanosecond value: S0 measured a
  microsecond LINT assigned to DT being divided by 1,000, while nanoseconds
  assigned to LDT were preserved exactly.
- Strings retain the owning Core/application byte capacities. A StringFamily
  is recognized from its LEN DINT / DATA SINT[n] template shape. LEN counts
  UTF-8 bytes. Generation rejects an over-width literal; acquisition rejects
  invalid length or encoding rather than truncating it.

Canonical array indices equal the declared Core indices. Logix physical
storage starts at zero; the manifest supplies logical lower bound and element
count. Packed Boolean bits are expanded before that bound is applied.
The five V1 corrections are exactly ActiveSteps, ModePolicy,
SupportedModesPublished, SupportedRunStylesPublished and Access.Policy.Required,
all changing from lower bound 1 to 0. Other arrays keep their Core bounds.

The owner selected preservation of the oracle's logical path set on 2026-10-21.
Reserved physical slots do not automatically become published logical entries.
The V6.1 candidate carries explicit selected indices and same-root live count
references in its PLC-resident manifest; these are range/type checked against
the native template and the acquired record. Empty views still validate their
full annotation schema. See the [S3a wire draft](AB_CANONICAL_PUBLICATION_S3A_WIRE_DRAFT_2026-10-21.md).
This adds no station declaration or name-based inference to the client and
does not expand the five permitted D2 differences.

The native units and LINT conversion rule agree with Rockwell's
[time and date type documentation](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/37-01/contents-ditamap/instruction-set/time-and-date-data-types.html).
The D6/D7 selections above are binding decisions from the measurements, not a
claim that Rockwell prescribes those Fraktal representations.

## AB §3.10 — canonical exposure and self-description

Each deployed root is one controller-scope tag named exactly as its local
browse name. Its record declares the standard Status contract; children are
records named exactly as their local instance/schematic names. Status.Name
carries the qualified Fraktal identity. Infrastructure, private state and
reference aliases do not create additional roots.

Discovery uses the controller's Symbol object (0x6B), Template object (0x6C)
and validated PLC-resident manifest. A module is recognized through its Status
contract, as on TC3 and TIA. The structure flag and complete 12-bit template
handle govern references; a handle's low byte matching an atomic code does not
make the referenced record an atomic type.

The new physical manifest major is 6. It describes canonical paths and carries
logical types, logical array bounds/extents, and effective member access
where native Template metadata is insufficient. These facts are derived from
the same owning declarations as the UDTs and their access settings. Physical word count cannot replace logical Boolean
element count. Static metadata is cached by the validated manifest content hash
and configuration revision; existing coherence, invalid-manifest and
incompatible-major refusals remain.

The S3c V6.2 candidate adds explicit bindings from separate scalar data
records to discovered roots, with disjoint native leaves and matching array
containers. Step definitions can be cached outside cyclic whole-root reads;
FragmentRevision invalidates their values independently of the schema hash.
History remains PLC-owned. See the [V6.2 draft](AB_CANONICAL_PUBLICATION_S3C_WIRE_DRAFT_2026-10-22.md).
This is a staged implementation proposal; shipping activation is still gated.

Published data is effectively Read Only, HmiRequest alone is effectively
Read/Write, and private storage has access None. The generated access audit
proves the effective leaf policy. A writable mailbox requires Read/Write on
its ancestors; other public branches are Read Only. Private None members are
kept outside records that a client reads whole. Supplementary S0 measured that
a Read Only parent denies its Read/Write child, and a None member blocks the
whole record read. The captured Template metadata does not distinguish member
permissions, so the manifest publishes them; a client does not infer them from
pylogix access properties or a station declaration. These findings and the
2 MiB fragmented-read qualification are recorded in
[supplementary evidence](Evidence/AB_S0_SUPPLEMENTARY_RUNTIME_2026-10-21.md).

The client decodes the PLC-owned contract. There is no runtime station
declaration, client-owned derivation, hard-coded station tree, or station HMI
screen. During S2–S3, old contexts coexist only for migration/equivalence; S6
removes them after all harnesses and adapters have moved.

## AB §11.1 — desktop and gateway topology (D9)

One generic CipSessionClient in fraktal_opcua_client emits
fraktal.opcua.snapshot.v1. The desktop selects it through cip://. The Dart
gateway uses the same client for Web clients, as it does for ADS and S7 Web API.
The PLC's canonical tree and manifest are the sole runtime description.

Direct writes require a commissioned CIP Security session proved on capable
hardware. Without it, direct CIP is explicitly read-only in the HMI. Echo
implements no CIP Security, so direct desktop acceptance on Echo is read-only.

Commands on the Echo/isolated gateway path use the existing authenticated
wss:// gateway posture, recorded per-deployment write choice, root scope and
PLC mailbox gates. Browser clients do not open raw CIP sockets. Existing
§11.2.1 authenticated-principal, least-privilege and no-anonymous-write rules
remain in force for a write-enabled production deployment.

Every mailbox transaction is serialized. All argument writes must succeed
before a separate Sequence commit. Success requires the matching PLC
acknowledgement and acceptance; timeouts and reconnects never replay a request.
CIP sample receipt time is recorded without inventing device source time or
clock synchronization.

## Approval and implementation boundary

The owner approved this target draft on 2026-10-20; it is not yet effective.
Supplementary S0 size/fragmentation, root-name, effective access and precise
LREAL vectors now pass at their recorded Echo scope. Per-surface Capacity,
native scan and S2-S6 implementation/equivalence, plus S7 physical/security
acceptance, remain open. The 2 MiB UDT qualification is not a global array-tag
size limit or a frozen application/manifest capacity.

## Approved S3f correction (offline implementation, 2026-10-23)

The owner approved the explicit configuration correction in
`call_eead11c567404709986d61b2907a3d61:0`. See its
[enumerated review](AB_CANONICAL_PUBLICATION_S3F_CONTRACT_REVIEW_2026-10-22.md)
and [V6.3 wire draft](AB_CANONICAL_PUBLICATION_S3F_WIRE_DRAFT_2026-10-23.md).
The target now includes bounded PLC-owned pages, the 110 corrected Core types,
12 missing Core fields, PLC-owned revision/absolute time and a validated
PLC-held medium-provider response. This amends the oracle only at that explicit
scope; the five D2 array-bound changes remain the entire bound-change list.

SetSchema's Core UINT is carried by a native DINT with logical UINT16 and
checked 0..65535 range. The generic reader returns UInt16. Revisions retain
the full UInt32 bit pattern, counters are native INT, bounds are LREAL and
timestamps LDT. V6.3 hashes versioned service descriptors alongside the existing
fields/bindings. Provider responses use the existing mailbox/session/access
gates, bounded UTF-8 and commit-last staging; no private tag is exposed.

Both native compiler/read-back/access gates and exact-image automatic Capacity
pass for the prepared S3f candidate. Runtime equivalence, native revision/
timestamp/provider behavior, scan/rollback and later stages remain open.
Neither this approval nor QUERY_CONFIG creates a direct-write exception to D9.

## Approved S3g and S3h finite corrections (2026-10-23)

The target includes the [200 S3g Core numeric corrections](AB_CANONICAL_PUBLICATION_S3G_CONTRACT_REVIEW_2026-10-23.md)
and [224 dependent values](AB_CANONICAL_PUBLICATION_S3G_DEPENDENT_VALUES_REVIEW_2026-10-23.md),
including exact Float32 OEE arithmetic and full UInt32 counter visibility.
S3g native acceptance passes at its recorded genealogy/Echo scope; this is
not physical/security acceptance or V2 activation.

The owner approved the [36 S3h type corrections](AB_CANONICAL_PUBLICATION_S3H_CONTRACT_REVIEW_2026-10-23.md):
sixteen UInt32 event sequences, three native INT ring counters and seventeen
LDT timestamps. Unset Part Stamp becomes canonical zero. The other 242 added
paths retain exact types and values. Existing AB genealogy/delivery metadata,
append/epoch/carrier/measurement/tower ownership and consumed bounds remain.
The event ring uses its PLC-published count for occupied physical slots;
measurement scaling occurs in LREAL before publication. Nameplate facts are
initialized by the PLC declaration. S3h offline gates pass; native session,
scan and rollback remain open. These finite lists add no general coercion,
tolerance, ignored path or direct-write exception to D9.

## Approved V6.4 type-scoped manifest (offline, 2026-10-24)

The owner approved [R1's finite wire change](AB_CANONICAL_MANIFEST_V64_CONTRACT_REVIEW_2026-10-24.md).
With the declaration opt-in `canonical_type_manifest`, SchemaMinor=4 replaces
Fields with TypeAnnotations and PathExceptions. TypeAnnotations names the
owning Template type and member, logical type, logical bound/count, sibling
CountMember and effective access; empty type/access means the native mapping
and Read Only. The sparse exception table names explicit index selections.
Bindings/services retain their meanings. ContentHash includes both new tables;
ConfigRevision derives from it. A zero-count table omits its physical array.

The generic reader resolves every type fact through the discovered Template
name/member, then applies the path exceptions. Every physical array needs an
extent, including arrays below empty views. Counts refer to an integer sibling
in the assembled logical tree, including bound metadata records. Missing,
ambiguous or conflicting facts fail closed. Unsupported per-instance facts
and non-sibling count exceptions are refused by generation.

V6.0?6.3 readers/captures and released images remain supported. Canonical
paths, values, logical types, selections and occupied counts are unchanged;
only the configuration identity changes. This is an inactive V2 draft,
not native acceptance or a direct-write exception to D9.

## Approved S3j fieldbus product (offline, 2026-10-24)

The [approved S3j review](AB_CANONICAL_PUBLICATION_S3J_CONTRACT_REVIEW_2026-10-24.md)
adds a separate PLC-owned ST_FieldbusTopology product. Its
[V6.5 wire draft](AB_CANONICAL_PUBLICATION_S3J_WIRE_DRAFT_2026-10-24.md)
retains V6.4 type annotations and adds the DataProducts binding table.
Identity is on demand, state per row/group; clients infer no station facts.
Declared counts stay inside Core's ceilings, with process-word child nodes
for the reviewed over-bound catalog. Node and channel counts/indices are INT,
AnalogValue REAL, flags BOOL and strings at Core widths. Missing sampled words
fail closed. A mapping error is visible. Force capability remains absent
without a registered OUTPUT_FORCING gate. This inactive draft does not grant
controller writes or physical/security acceptance.
