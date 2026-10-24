# S2 canonical wire candidate — 2026-10-21

Non-normative implementation candidate for the approved V2 target. Shipping
Part III/V1 remain active. The [plan](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md)
requires live equivalence, Capacity and scan measurements before S2 exit.
Those S2 gates now pass at the recorded Echo scope; see
[runtime evidence](Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21.md).
This draft records the implemented layout, rather than freezing an unmeasured
future capacity. The shared writer/reader rules live in
`fraktal_ab_canonical_manifest.py`.

## Migration and discovery

`Application.canonical_publication_stage = 2` selects this explicit migration
image. Zero preserves legacy generation. The disposable
`fraktal_ab_genealogy_canonical_demo` derives the existing genealogy declaration
and changes only that selector. The legacy manifest remains available to the
projection oracle with its existing hash, 6DEC4C1DC2F7F78A. It is temporary
migration storage, removed at S6 with the old contexts.

The new canonical record is one controller tag named exactly Press. It has
Status and children named after their local instance names. A generic client
discovers module roots by a top-level structured Status member; it does not
need an application name, declaration, projection or engineering file.
Every module identity is checked against its canonical browse path.

The V6 manifest is a separate controller record, found by header shape and
magic, not its application-specific symbol name. Neither its UDT nor its tag
name is a discovery convention. Duplicate matching manifests, missing records,
unsupported versions/stages, invalid flags, corrupt rows and hash/revision
mismatches fail closed. The reader loads and validates it before and after
canonical acquisition. Configuration coherence does not assert scan atomicity.

## Physical header and Fields row

| Header member | Native type / meaning |
|---|---|
| Magic | DINT, 0x46524B36 |
| SchemaMajor / SchemaMinor | DINT, 6 / 0 |
| PublicationStage | DINT, 2 for this gated slice |
| Valid / Truncated | BOOL; only true / false qualifies |
| ContentHash | StringFamily(80), 64 uppercase SHA-256 hex digits |
| ConfigRevision | DINT, derived from the hash prefix, equality token |
| LegacyContentHash | StringFamily(80), binds the migration oracle image |
| FieldsCount / FieldsCapacity | DINT; exact allocation, no unused rows in V6.0 |
| Fields | Array of the row below, with that exact extent |

| Fields member | Native type / meaning |
|---|---|
| CanonicalPath | StringFamily(255), slash path; ancestor arrays may use [*] |
| LogicalType | StringFamily(16): empty for native, or BOOL / ENUM / DURATION / TIMESTAMP / BITSTRING32 |
| EffectiveAccess | StringFamily(16): Read Only / Read/Write |
| LowerBound | DINT, declared logical array lower bound; zero for a scalar |
| ElementCount | DINT, logical array count; zero for a scalar |

String capacities count UTF-8 bytes. Structured members use NullType radix;
StringFamily DATA uses ASCII radix for native hex encoding. Every row is
derived from the same member declarations as the UDT. Array cardinality is
logical, never guessed from physical DWORD storage. None is not a public leaf
permission: private storage stays outside records read whole.

ContentHash covers the ordered canonical Fields rows, schema/stage and the
legacy content hash, serialized by the shared wire module. ConfigRevision is
`int(ContentHash[:7], 16) or 1`; it is compared for equality, not ordering, as in
the existing manifest protocol. No monotonic ordering is implied.

## First slice and access

The genealogy candidate publishes exactly **46 paths** across one Unit and
six CMs: Status.Name, DisplayNameKey, optional TypeKey, ModuleType, State and
FaultActive; plus root ModeActivePublished, RunStyle, CurrentStep.StepNo and
Model.ModelCode. This is the S2 subset, not the complete Status/diagnostic or
HMI surface. Diagnostics and the other surfaces follow in S3.

Status uses the Core identity/key capacities (80/160 bytes), native BOOL and
DINT enum carriers. ModelCode preserves the application's existing 80-byte
model-catalog declaration; it never silently narrows an accepted model code.
Core §3.1b requires a string model identity; the application's declared bound
is authoritative for this existing catalog. Static identity is initialized
in the PLC. Cyclic state and model selection are copied/derived after the
owning services, with no client derivation. Shared leaf/status types avoid one
type per instance. Existing native model validation remains in force.

All added canonical data tags and members are Read Only. The one publication
scratch index is None. HmiRequest has not yet migrated; the existing fixture
mailbox and simulated inputs retain their earlier scopes. Direct canonical
acquisition exposes no write path. Later mailbox publication must use S0's
measured Read/Write ancestor / Read Only sibling rule.

## Same-state and performance gates

A separate read-only generation tag brackets the **entire PLC scan**: odd
before any owning service, even after canonical publication. A bounded
read-only fixture samples that generation around all canonical and legacy
reads and accepts only the same completed even generation. It closes the
read window before decoding. Counter rollover is bounded in PLC logic.
If no window qualifies, equivalence fails; matching configuration hashes
cannot replace this proof.

The acceptance harness chooses its expected S2 paths from an explicit stage
contract, independently of the discovered paths, then calls the unmodified
strict path/type/value comparison. A missing published field cannot shrink
the comparison silently. Declaration knowledge exists on the test-oracle
side only. Generic acquisition and wire decoding import no station code.

The standalone read-only CanonicalTiming record carries native TASK
LastScanTime, MaxScanTime and OverlapCount plus an advancing scan sample.
Capacity compares owner Studio values from the hash-bound baseline and
candidate copies in the same displayed units. Both performance deltas and
the live 46-path gate pass in the linked runtime record. This acceptance is
limited to S2; later surfaces and shipping V2 activation remain open.
