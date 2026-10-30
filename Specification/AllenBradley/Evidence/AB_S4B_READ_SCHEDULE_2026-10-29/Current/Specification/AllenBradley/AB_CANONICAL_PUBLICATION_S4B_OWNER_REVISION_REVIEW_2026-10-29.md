# S4b owner-revision contract review — 2026-10-29

**Proposed; owner decision pending. No dependent PLC implementation or download.**

The current reader still cannot pass three consecutive desktop rehearsals. The
[investigation record](Evidence/AB_S4B_READ_SCHEDULE_2026-10-29.md) retains the
successful runs and every failed experiment. The prior native session passed
desktop E7, but failed E3/E4; neither that result nor these peer failures proves
that scan-bound reads can never work on Echo. S4b remains open.

The [original coherence review](AB_CANONICAL_PUBLICATION_S4_COHERENCE_REVIEW_2026-10-25.md)
explicitly leaves Alternative B available when bounded scan-counter reads cannot
satisfy freshness. The owner selected A. Plan §3 also says: “No freshness limit,
proof window, attempt budget, tier rule, coherence rule, access policy or read-only
rule changes to make a gate pass.” **This proposal requires an explicit amendment
for a new, stronger publication protocol; it does not reinterpret protocol 1.**

## Proposed scope

Keep the canonical tree, scalar types, logical bounds, manifest discovery, typed
command ABI and all read tiers unchanged. Publish an additive owner-version
binding for these data:

- The five discovery-header members `Status/Name`, `ModuleType`, `State`,
  `ConfigRev` and `TypeKey` on every discovered module. The present genealogy
  inventory has seven modules and therefore 35 selected paths. Counts and paths
  come from the generated module tree, never a station list in a client.
- The existing read-only configuration view named by each `ReadServices` row.
  Its definitions, values, counts, model routing and permission masking retain
  their current owner/rebuild semantics and exact page projection.

All other fields keep their current scan-bound protocol. This narrow scope is
not a claim that it will settle E3; all E1–E9 must still pass together.

## Versioned wire shape

Reserve **V6.10** for an additive, hash-covered `OwnerReadBindings` table. V6.9
is already reserved/approved for S6 host services; its approved shape carries
forward without a later schema downgrade. Physical string families reuse the
existing binding path/symbol capacities; counts/capacities are generated exactly.

| Member | Meaning |
|---|---|
| `CanonicalPrefix` | Exact module `Status` prefix or declared read-service root |
| `MembersJson` | Relative selected members; empty array means the whole declared read-service view |
| `RevisionSymbol` | Published read-only DINT owner seqlock |
| `ProgressSymbol` | Separately published existing scan-generation DINT |
| `Protocol` | New ordinal 2; owner-versioned, immutable between revisions |
| `MinimumUpdateIntervalUs` | Lower bound between owner update transactions, derived from the task period |
| `MaximumProofWindowUs` | 1,000,000, bounded by the existing acquisition deadline and the counter's wrap bound |

An owner binding overrides the old binding only for its explicitly selected
leaves. Duplicate owner selections, conflicting owners, missing/invalid symbols,
unknown protocol, uncovered fields, inconsistent periods or a mixed-owner read
group refuse. The planner partitions selections by their published owner; it
does not infer a counter name. Protocol-1 interpretation remains unchanged.

## Publisher and reader obligations

1. The owner opens its seqlock before **any** write to a protected member and
   closes it afterwards. It changes the revision only when the selected row
   changes. Static identity is initialized under that owner; `State` and
   `ConfigRev` changes use the same transaction. Identical cyclic assignments
   cannot bypass the ownership proof. The generator verifies the full writer
   set; project code adds no required calls.
2. The configuration-view owner brackets every rebuild, including session/
   policy masking and any count, routing or bank change. A header revision alone
   cannot certify a view whose value rows changed outside that transaction.
3. Stable revisions are nonnegative even DINT values; updates use odd values,
   then the next even value with the existing 31-bit wrap. Every transaction
   changes the token. A declared minimum update interval plus the token space
   proves that the token cannot wrap back within the maximum proof window.
4. A read accepts only equal even owner revisions around its complete body,
   within the published protocol-2 window **and the original one-second total
   acquisition budget**. At a 10 ms minimum update interval, the 2^30 distinct
   stable tokens cannot wrap in one second. Protocol 1 still requires its
   original strict 10 ms window; it does not gain this new permission.
5. Owner-version stability does not prove that the PLC is scanning. The reader
   independently proves the published `ProgressSymbol` advances. Frozen progress,
   invalid metadata or a stopped publisher cannot remain Good merely because
   an unchanged owner revision is even.
6. Source age starts before I/O. The existing 20-attempt maximum, one-second
   deadline, fast 1/3-second Good/expiry, slow 7.5/15-second Good/expiry, O8
   heartbeat, payload-free Uncertain rows and desktop write refusal remain.
   A coherent result that arrives too late still fails freshness.

This changes which PLC publication guarantee justifies a proof window. It is
not an accepted client retry/window adjustment against the old image.

## Work authorized by approval, and its gates

Approval covers the V6.10 draft/frozen-contract amendment, generated owner logic,
generic decoder/planner/progress support and offline tests. It does not declare
fit, scan improvement, native acceptance or stage exit.

Before a guarded Echo session: prove writer coverage and no-ABA bounds; test
mid-read mutation, odd/invalid/wrapped revisions, frozen scan progress, source-age
preservation, conflicting selections and unsupported versions; retain exact
goldens; pass full AB/HMI/root gates and both v38 builds/read-backs; measure exact
Studio Capacity; pass three final-source profile rehearsals and debug comparison.
No feature or validation is cut for fit. Native E1–E9, including all four config
pages and rollback, remain mandatory. O3 already governs guarded Echo use.

**Decision requested:** approve this owner-versioned publication contract and
dependent offline work, or retain A and continue investigation without a new
PLC publication contract. No approval has been recorded for this proposal.
