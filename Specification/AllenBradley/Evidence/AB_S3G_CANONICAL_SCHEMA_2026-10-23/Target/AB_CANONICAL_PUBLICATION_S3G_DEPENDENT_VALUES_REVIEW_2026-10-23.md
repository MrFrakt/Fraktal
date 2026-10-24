# S3g dependent values at unsigned boundaries

Owner approved the [200 numeric type corrections](AB_CANONICAL_PUBLICATION_S3G_CONTRACT_REVIEW_2026-10-23.md)
and offline work. This follow-up makes an omission in that draft explicit:
its requirement that all other values remain identical conflicts with the
already approved Core arithmetic at boundary states. No controller access or
production algorithm change was used to demonstrate this.

Two pure counterexamples are recorded in
`C:/work/fraktal-ab-s3g-20261023/prepare_feb76c7a0968442293ee0d20b812eb17/boundary_implications_02.json`:

- RunMs=4,294,967,296, DownMs=0, no parts and IdealCycleMs=1,000. Core's wrapped
  RunMs=0 makes AvailValid, PerfValid and OeeValid FALSE; the legacy values are
  TRUE. Preserving those old flags would claim valid factors with zero divisors.
- Good/NOK bit patterns `0xffffffff` / `1` produce a Core UDINT total of 0,
  so QualValid becomes FALSE; the legacy signed/clamped calculation makes it TRUE.
- A native profiler count with bits `0x80000000` is -2,147,483,648 as DINT and
  2,147,483,648 as Core UDINT. The old `Count > 0` test hides the row's Id,
  Label, TimeClass, Avg and Maximum. Core's unsigned count keeps the row visible.

The proposed addition is a finite **224 value-path list**: the four Oee validity
flags, 60 OeeTrend[].OeeValid flags, and those five dependent fields in each of
32 profiler StepStats rows. Their types remain unchanged. The machine-readable
counterexample enumerates every path; none overlaps the 200 approved type paths.
The union is 424 affected paths out of S3g's 1,055 added paths.

Approve these dependent values to follow the same Core arithmetic and unsigned
counter semantics as their approved numeric fields. Every other value/type stays
exact; the five D2 bounds, S3f rules and consumed path set stay unchanged. No
general coercion, tolerance, clipping or ignored path is allowed. Exact boundary
vectors and the ordinary-state equivalence gates must pass before deployment.

This approval covers the additional finite value amendment and dependent offline
work. The separate image/Capacity/current-authorization gate for any download
remains. No commit or push is requested.
