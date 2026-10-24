# S3a canonical array views: V6.1 candidate, 2026-10-21

The owner selected preservation of the oracle's logical path set using
PLC-published extents and live count references. This implements that choice
without changing the five D2 corrections or adding station knowledge to a
client. Part III/V1 remain the shipping contract. S3a runtime acceptance is
pending; this document describes the generated candidate.

V6.0 remains readable, and regenerating the accepted S2 source is byte-identical.
V6.1 keeps the V6 header shape, magic and major, sets SchemaMinor=1 and
PublicationStage=3, and appends two StringFamily(255) members to each Fields
row: CountPath and Indices. The writer/reader authority is
`fraktal_ab_canonical_manifest.py`. Hash input includes the actual minor,
stage, all ordered rows and their new members. No live value is hashed into
the schema token.

| Row member | Meaning |
|---|---|
| LowerBound | Canonical index = selected physical index + LowerBound |
| ElementCount | Maximum logical prefix within reserved physical storage; positive for arrays |
| CountPath | Empty, or a same-root canonical path to a published integer scalar giving the current prefix length |
| Indices | Empty for the default prefix, or a JSON array of selected physical indices; [] explicitly selects none |

CountPath and Indices cannot both select a view. Indices must be strictly
increasing, unique integers in [0, ElementCount). CountPath names a scalar
through named structures, with no array/wildcard traversal; it cannot target
a BOOL, float, string, structure or array. Each acquired value is range-checked
against [0, ElementCount]. A zero live count publishes no elements. A normal
array's physical template extent must cover ElementCount; BOOL arrays must
provide enough packed storage. V6.0 keeps its original exact-extent rules.

All annotations are checked against the template schema before applying the
view. An empty array cannot hide an absent field, invalid logical type or bad
reference. String lengths, UTF-8, physical layout and unused native storage
remain subject to strict raw decoding. No view is inferred from a Count suffix,
a member name, a declaration file or observed values.

The genealogy candidate uses these views:

| Array | Physical allocation | Published view |
|---|---|---|
| ModePolicy | Core MODE_COUNT entries | Declared mode indices [0,1,2,3], lower bound 0 |
| SupportedModesPublished | Native packed BOOL storage | Same declared mode indices, maximum Core MODE_COUNT |
| SupportedRunStylesPublished | Native packed BOOL storage | Three Core run-style entries, lower bound 0 |
| Decision.Options | Core MAX_OPTIONS slots | Maximum declared decision option count (two), lower bound 1 |
| AvailableModels | Eight model slots | Prefix referenced by Press/AvailableModelCount, lower bound 1 |
| CM Catalog | Declared command count | All declared entries, lower bound 1 |

Sparse/non-contiguous mode ordinals are also carried explicitly. The client
does not renumber them. Core capacities are read by the engineering generator
from the Core parameter declarations; the runtime reader imports no generator,
Core source file, station declaration or Python projection.

The candidate has 94 logical paths with the current three models. Creating
another model adds its one ModelCode path through the live count reference,
without changing the physical template or metadata hash. The append-only
catalog provider owns immutable model codes/ordinals; publication refreshes
when its Count changes. Decision text refreshes when the owning DecisionId
changes. Dynamic state/default/count mirrors remain cyclic. These caches and
indices are private controller tags outside whole-read canonical records.

The paired gate chooses all expected paths independently from the legacy
projection/declaration, using the paired live model catalog count. It still
requires an equal-even generation around the entire scan and the unchanged
strict path/type/value comparison. The 31-row candidate fixture adds read-only
pairs before its existing decision answers, preserving the original commands,
simulation stimuli, cleanup and regression row count.

Decision.Timeout/SourcePath remain an explicit full-Core gap, as recorded in
the S3a notes. They are not fabricated or silently excluded from a claim of
complete Core conformance. This stage claims the explicit migration subset.
