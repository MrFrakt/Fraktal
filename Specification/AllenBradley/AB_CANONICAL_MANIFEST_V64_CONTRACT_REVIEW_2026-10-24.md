# Canonical manifest V6.4 — type-scoped annotations (contract review draft)

**Owner-approved for offline implementation behind a declaration opt-in on 2026-10-24** (chat reply “all of them approved”). Implemented offline behind `canonical_type_manifest`; native acceptance keeps its own authorization. This is capacity plan R1
([plan](AB_CAPACITY_BUDGET_AND_REDUCTION_PLAN_2026-10-24.md)). It changes the
PLC manifest's wire layout, so it needs approval like every other contract
step. Published canonical paths, values and types do not change, and the
generic reader's snapshot must come out identical.

## 1. Why

V6.3 describes the canonical tree with one `Fields` row per instance path
pattern. Each row is `CanonicalPath`, `LogicalType`, `EffectiveAccess`,
`LowerBound`, `ElementCount`, `CountPath` and `Indices`, three of them
`STRING(255)`, about 828 bytes per row. Measured on the S3i declaration:

| Fact | Value |
|---|---:|
| Rows | 467 |
| Manifest data | about 386 KB (14% of the S3i image) |
| Rows carrying anything the Template does not already say | 181 |
| Distinct (structure type, member) pairs among those 181 | 136 |
| Pairs whose instances disagree | 0 |
| Count paths that name a sibling member | 6 of 6 |
| Rows with non-default access | 0 |
| Rows with an explicit index list | 2 (`ModePolicy`, `SupportedModesPublished`) |
| Manifest bytes added by one more cylinder module | 21,200 (its published state is 2,480) |

The design already says the manifest "supplies only what Logix types cannot
say themselves". Today it states each such fact once per instance and repeats
the defaults. That is a duplication O9 forbids, and a cost that grows with
instance count, against O4.

## 2. Proposal

Add V6.4 (`SchemaMinor = 4`). It replaces `Fields` with two bounded tables.

- **`TypeAnnotations`**: one row per (structure type, member) that needs a
  fact. Columns are `TypeName` and `MemberName` (both `STRING(40)`, the Logix
  identifier limit), `LogicalType` (`STRING(16)`), `LowerBound`,
  `ElementCount`, `CountMember` (`STRING(40)`, the sibling member holding the
  live count) and `EffectiveAccess` (`STRING(16)`). Empty means the default:
  the logical type follows the native atomic type, and access is Read Only.
  Every instance of the type inherits the row.
- **`PathExceptions`**: a sparse table for the facts a type cannot carry.
  Today these are the two explicit index lists, plus any count that is not a
  sibling or any per-instance difference. Columns are `CanonicalPath`
  (`STRING(255)`) and `Indices` (`STRING(255)`). Generation refuses an image
  whose instances disagree on a type-scoped fact unless an exception row
  states it.

Bindings, services, `FragmentRevision`, `ContentHash` semantics and
`ConfigRevision` are unchanged; `ContentHash` covers the new tables.

**Estimated size.** 136 rows × about 204 bytes is roughly 28 KB, plus two
exception rows: about 358 KB saved on S3i. A module of an existing type adds
no manifest rows; a new module type adds its own members once.

**Reader.** The Python reference reader and the S4 Dart client keep reading
V6.0–6.3 exactly as today. For V6.4 they resolve each decoded member's
annotation by (Template name, member name), then apply `PathExceptions`.
The rule "every physical array requires a logical extent" is unchanged. It is
now satisfied per type.

## 3. Acceptance

1. **Identical snapshot.** For every stage declaration, the generic reader's
   snapshot from a V6.4 image must equal the snapshot from the same image in
   V6.3. That is every path, logical type, value, extent and count.
2. **Old captures still decode.** Every sealed native capture (V6.0–6.3)
   still decodes unchanged.
3. **Image gates.** The usual exact-image v38 build/read-back, effective
   access, measured Capacity, and a native session under its own approval.
4. **Released images untouched.** V6.4 is opt-in per declaration, like R2,
   so accepted images keep their bytes.
5. **Documents.** Part III and the V2 frozen contract drafts gain the V6.4
   tables at S6, when V2 is finalized. The amendment draft records them now.

## 4. Risks

- **The Dart client implements the same lookup.** It is specified once here,
  and the golden replays cover both minors.
- **Type names become part of the contract.** Renaming a canonical type
  becomes visible to clients. Canonical types are already versioned by name
  (`…S3hV63`), so this adds no new rule.

## Owner decision requested

Approve the V6.4 type-scoped manifest as a finite contract change, and
offline implementation behind a declaration opt-in. Native acceptance keeps
its own authorization.

## Offline implementation ? 2026-10-24

The implementation emits **137 type annotations and two path exceptions** for
S3i. The review's 136-pair estimate deduplicated the logical `SequenceSteps`
path before counting types: its live root and definition fragment have separate
owning UDTs. Both need the annotation. No published path is added.

Empty tables have Count=Capacity=0 and omit the physical array, since Logix
has no zero-length UDT array. Nonempty tables allocate exactly their row count.
V6.4 always states the binding/service counts and FragmentRevision; stages
without those products use zero counts/revision. Every row is hash-covered.
A sibling count may be supplied by a bound fragment at the same logical parent;
the reader validates disjoint leaves and matching containers before lookup.
The two-column PathExceptions format represents index selections only. A
non-sibling count or conflicting type fact is refused; encoding such exceptions
would require an explicit wire amendment.

Both v38 targets compile and read back equivalently; effective access passes.
The combined R1+R2 S3i bench measures **1,653,432 used / 1,492,296 available /
3,145,728 total Blocks** (52% displayed). R1 frees 360,600 Blocks beyond R2,
and together they free 1,110,080 versus accepted S3i. All ten accepted images
stay byte-identical with both opt-ins off. Every sealed V6.0?6.3 capture
replays and has an identical snapshot with type-scoped metadata. The native
session remains unaccepted and needs exact-image current owner confirmation.

## Native acceptance ? 2026-10-24

The owner confirmed the exact combined R1/R2 image and the guarded session
passed at the genealogy/Echo scope: 41 candidate cases, calendar lifetime,
retained Program/Run, 4,010-path equivalence and all 97 independent native
replays. Genealogy is restored; authorization is consumed. Read
[runtime evidence](Evidence/AB_R1_R2_CANONICAL_RUNTIME_2026-10-24.md).
This supersedes the earlier pending-session status. V2 remains inactive;
Dart, press and physical/security acceptance remain separate gates.
