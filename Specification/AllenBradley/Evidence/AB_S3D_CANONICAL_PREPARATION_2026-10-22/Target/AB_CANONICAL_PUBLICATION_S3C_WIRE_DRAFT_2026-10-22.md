# S3c canonical record bindings: V6.2 candidate

V6.2 extends V6.1 without changing its field rows or the accepted V6.0/V6.1
images. The implementation authority is fraktal_ab_canonical_manifest.py;
Part III/V1 remain the shipping contract. See the
[S3c notes](AB_CANONICAL_PUBLICATION_S3C_NOTES_2026-10-22.md) for scope.

SchemaMinor = 2 adds these header members:

| Member | Meaning |
|---|---|
| FragmentRevision | Nonnegative DINT generation for cached definition data |
| BindingsCount | Number of binding rows |
| BindingsCapacity | Allocated binding row count |
| Bindings | Inline rows with SourceSymbol and TargetRoot, both StringFamily(80) |

Count and capacity must equal the exact bounded allocation (1..1024).
Symbols are valid controller identifiers of at most 80 characters. Sources
are unique and cannot equal their target. Schema content hashing includes
all ordered binding rows in V6.2, alongside the existing header/Fields facts.
FragmentRevision is live data and is excluded from that hash. V6.0/V6.1
reject injected binding members and retain their original hash inputs.

Roots are still found by their top-level Status member. A binding names a
separate scalar UDT Symbol and a discovered target root. The reader decodes
the source through its native Template and joins its member paths under the
target root. It validates that all required records were acquired exactly
once, and rejects absent symbols/targets, arrays at the binding source,
duplicate sources, root aliases and unbound records. Fragment trees cannot
contain Status or introduce module identities. The source is metadata/data,
not an additional module or a client-side station declaration.

Joins must have disjoint scalar leaves. Structured containers may overlap
only with matching array rank and physical extent; leaf collisions fail.
Each contributed leaf uses its native schema and the same manifest
annotations as the root. Logical array views and bounds are validated even
when empty. A live CountPath must address a native integer scalar in the
target root, not in a cached fragment.

Coherence tokens contain content hash, configuration revision and, for
V6.2, FragmentRevision. Readers compare before/after manifest states around
acquisition and invalidate cached definition values on a revision change.
The writer advances the revision once per changed batch, with bounded wrap.
This does not establish same-scan atomicity across tags: the runtime
equivalence gate still requires the PLC's whole-scan generation proof.

S3c binds FRK_Press_SequenceDefinitions to Press. Both records contribute
SequenceSteps[1..21]: the root carries four history leaves per row; the
separate record carries seven definition leaves. The manifest publishes the
binding and all type/bound/access facts. The generic client contains no Press
name, sequence-text lookup, recipe rule or station import. Later bindings can
use the same validated mechanism; they require their own staged gates.

S3d preparation uses a second binding, FRK_Press_AlarmMetadata to Press.
Its AlarmLog.Meta contributes disjoint fields alongside the root's live
AlarmLog. MetaCount stays in the native root, as required for CountPath.
No V6.2 field/header change or client modification is needed. The root still
contains active/ring data; binding values remain cached definition metadata.
See the [S3d notes](AB_CANONICAL_PUBLICATION_S3D_NOTES_2026-10-22.md).
