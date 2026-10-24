# S3g Core numeric contract review

**Owner approved on 2026-10-23:** “Approve S3g corrections and offline work”
(`call_98e771c35eec48548b860bd7ad211932:0`). S3f is complete on Echo; this proposal covers S3g
contract and offline work. No S3g PLC image or native session is prepared.
The finite 200-path amendment is approved for offline implementation; no
controller-changing operation is authorized.

The [plan §1](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md) permits the five D2
bound corrections and the enumerated S3f configuration corrections. S3g adds
1,055 frozen legacy paths, of which **200 have different Core numeric types**.
Implementing those differences therefore needs an explicit contract amendment.
The [machine-readable inventory](AB_CANONICAL_PUBLICATION_S3G_INVENTORY_2026-10-23.json)
enumerates every path, frozen value, old type, proposed type and owning Core source.

| Surface | Added legacy paths |
|---|---:|
| Oee | 11 |
| OeeTrend and OeeTrendHead | 121 |
| Profiler | 900 |
| SystemHealth | 23 |
| Total | 1,055 |

The cumulative legacy path set becomes 4,010. With the approved S3f bounded
configuration windows, the prospective canonical page totals are 3,672 / 3,622 /
3,272 for page 0 / page 1 / an empty page. These are inventory counts, not runtime
acceptance. Profile/trend bounds match Core and the existing AB declaration;
no additional bound correction is proposed.

## Proposed finite amendment

| Exact inventory paths | Legacy type | Core type | Owner |
|---:|---|---|---|
| 64 | Double | Float (IEEE 754 binary32) | Four Oee factors and 60 OeeTrend[].Oee values; ST_Oee / ST_OeeSample |
| 101 | Int32 | UInt32 | Three Oee millisecond buckets; 61 profiler cycle numbers; 32 step execution counts; five system-health metrics |
| 35 | Int32 | Int16 | 32 waterfall StepNo values, LastCycle.NSteps, HistoryHead and OeeTrendHead |

Approve **only these 200 enumerated paths** to use their owning Core types.
All other paths retain exact values and types. The 855 other added S3g paths,
all accepted earlier surfaces, the five D2 bounds and the S3f page contract stay
under their existing acceptance rules. Unconsumed Core fields are outside this
proposal; the logical path set remains the oracle's consumed surface.

This has two explicit value consequences:

- OEE uses a versioned reference for Core REAL arithmetic, with exact binary32
  rounding at the operations and published results. For example, the binary64
  value 0.3333333333333333 becomes binary32 0.3333333432674408. The existing frozen
  capture stays immutable. The new reference must name these 64 paths; no
  tolerance or general float coercion is accepted.
- Core's three UDINT millisecond buckets wrap at 2^32 ms (about 49.7 days).
  A legacy bucket value 4,294,967,296 becomes 0. OEE factors must use the same
  Core bucket semantics. The remaining UInt32 counters/metrics use their full
  declared unsigned domain. High-bit and wrap cases require explicit offline
  and applicable native qualification; this inventory establishes neither.

Int16 declaration ranges must be validated before generation; an incompatible
application is refused rather than silently clipped or wrapped. Durations keep
the approved DINT-millisecond transport. Existing DateTime rules and enum
ordinals are unchanged.

## Implementation and acceptance after approval

The PLC owns the published values, metadata and derivations. The generic
reader imports no declaration and does not reconstruct OEE, labels or profiler
rows. Existing event owners remain single owners; unchanged profiler rows are
not rebuilt every scan. Unsupported system-health metrics remain explicitly
unavailable with their existing values.

Create the versioned S3g reference and path/type map, then implement the PLC
publication and prove exact equivalence, including nontrivial OEE fractions,
unsigned high bits/wrap, profile history and all three AUTO renditions.
Run the full AB/spec/contracts/strict-consistency gates, both v38 builds and
read-backs, automatic exact-image Studio Capacity and native scan measurements.
No feature or validation is removed to fit.

Approval of this draft authorizes the finite contract amendment and dependent
offline work. A later guarded S3g deployment needs its own concrete image,
current target authorization and rollback/regression gates. V2 stays inactive
until the complete staged acceptance passes.
