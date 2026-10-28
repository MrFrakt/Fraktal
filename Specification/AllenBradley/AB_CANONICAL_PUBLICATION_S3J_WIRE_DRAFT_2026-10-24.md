# S3j V6.5 data products and fieldbus wire draft

Non-normative implementation detail of the owner-approved
[S3j decisions D-1 to D-6](AB_CANONICAL_PUBLICATION_S3J_CONTRACT_REVIEW_2026-10-24.md).
Offline work only. V2 remains inactive; a native session needs current
authorization for its exact image and write vectors.

## Manifest and discovery

SchemaMajor remains 6; SchemaMinor is 5 for stage 12. V6.4's
TypeAnnotations, PathExceptions, bindings and services retain their semantics.
The new DataProductsCount/DataProductsCapacity describe an exactly allocated
DataProducts array. Zero counts omit the array. Each row contains:

| Member | Physical type | Meaning |
|---|---|---|
| SourceSymbol | STRING(40) | Controller-scope structured Symbol to read |
| CoreType | STRING(40) | Descriptive Core type, e.g. ST_FieldbusTopology |
| CanonicalRoot | STRING(255) | Independent logical root, e.g. PressFieldbus/Topology |

ContentHash covers these rows alongside the V6.4 tables; ConfigRevision is
derived as before. Source symbols must be unique and structured scalars.
Logical roots must not overlap another product or a discovered module root.
Unknown CoreType names do not select client code: the discovered Template and
type annotations still determine every field. Missing samples, bad extents,
bad counts or conflicting bindings fail closed. Readers keep V6.0-V6.4 support.

Fieldbus identity is initialized by the PLC. Its physical product symbol is
versioned with a 64-bit fingerprint of the initialized identity, so an identity
change also changes the manifest binding/hash and invalidates on-demand caches.
No client infers this symbol name. Identity is not duplicated in a second table.

## Layout and bounds

The public product follows Core ST_FieldbusTopology, ST_BusNode and
ST_IoChannel. NodeCount, ParentIdx and ChannelCount are native INT. State, Dir
and Kind are DINT enums; AnalogValue is REAL; flags are native BOOL. Strings
retain Core byte widths. Over-width UTF-8 identities are rejected.

The reviewed press catalog produces three nodes: Discrete_IO (parent, zero
channels), Discrete_IO.I (12 inputs), Discrete_IO.O (eight outputs). ParentIdx
is one for both children. All channel Name, Path, ModulePath and Address values
are preserved. The exact locator spelling is Local:1:I.0, not a raw Data-tag
operand. Node and channel ordinals in canonical paths are one-based.

Logix requires a homogeneous Nodes array. Its Channels stride is therefore the
largest declared word group (12 here), while each node's ChannelCount publishes
only its own 0/12/8 occupied rows. The reader never exposes unused slots.
Nodes and channels remain below the Core ceilings 64/16. This publishes 327
logical paths from the reviewed 311-path legacy product: the additional 16 are
the two word nodes' metadata, not additional channel aliases.

## Ownership, quality and forcing

IoModule.sample_tag binds a PLC-owned sampled-word record. Its InputWord,
OutputWord, FaultWord and three validity flags belong to the HAL producer.
An absent producer is unavailable. Missing one direction does not discard a
good sample for the other direction, but the module/node stays OFFLINE until
all three samples exist. All fault bits set mean inhibited/OFFLINE; a partial
fault means FAULT; a complete fault-free sample means OPERATIONAL. Each channel
needs its own direction and the fault word for good Quality. FaultActive names
its own bit. Output words are the controller image, not electrical feedback.

The generated owner checks mapping counts, parent references, identity lengths,
directions, kinds and duplicate channel Name/Path at activation. It hashes each
identity once and compares bytes on matching hashes; a hash collision cannot
hide a duplicate. Invalid lengths are rejected before byte access. Invalid
mapping publishes MappingValid=false and a localized MappingDiagnostic;
channel Quality is false. This check is not repeated on every scan because
the public identity is immutable during the activation.

There is no registered OUTPUT_FORCING gate in this AB profile. Forceable stays
false; the controller force owner withdraws held state and its existing
mailbox route refuses requests. Idle MANUAL alone does not grant that gate.
ForcesEnabled, ForceBool and ForceAnalog are not published. Enabling a proper
registered/annunciated commissioning gate is separate work, not a client switch.

## Acceptance fixture and read tiers

The genealogy variant labels TypeId as "Fixture: sampled controller words".
It configures no I/O module and writes no physical I/O operand. Its explicit
disposable source record is writable only in this fixture image. The ordinary
genealogy simulation and its 41-case apparatus are retained.

The separately armed word tool permits exactly eight DINT leaves of
FRK_Press_SimIo: nine fixed vectors plus complete original-word restoration
(80 writes). It checks the local Echo identity, expected manifest, MANUAL/idle
and logout state. Its cases cover operational, partial fault, inhibited,
offline, input-only, output-only, unknown fault quality, signed words and an
ineffective unregistered gate claim. Every observation uses an independent
4,000-byte reader. No motion stimulus, config, real I/O address, clock or fault
clear belongs to this added write surface.

The migration frame adds the product and the independent sampled-word source.
It is still an acceptance instrument. S4 must read identity on demand and
state per row/group under Part III 3.13; the shipping client must not depend on
a whole-document frame. Physical HAL sampling/electrical behavior remains S7;
the press identity/offline vehicle remains at S3 final.
