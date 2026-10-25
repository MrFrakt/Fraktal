# Canonical manifest V6.4 — type-scoped annotations (contract review draft)

**Owner-approved for offline implementation behind a declaration opt-in on 2026-10-24** (chat reply “all of them approved”). Not yet implemented; native acceptance keeps its own authorization. This is capacity plan R1
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
