# S3g offline schema and health checkpoint

2026-10-23, America/Mexico_City. **Partial offline qualification; S3g is not
complete and no S3g deployment image is prepared.** Controller access, tag
writes, mode changes, downloads and fault/clock operations are zero.

The owner answered “Approve S3g corrections and offline work” to
`call_98e771c35eec48548b860bd7ad211932:0`. The 200 enumerated numeric corrections
are recorded in the working V2 target and plan. V2 remains inactive. That
approval covers contract/offline work, without controller-changing authority.

## Qualified work

`fraktal_ab_canonical_metrics.py` defines all 1,055 consumed S3g paths with the
approved types: 64 native REAL/Float, 101 complete-word UInt32 fields using the
existing BITSTRING32 annotation, and 35 native INT/Int16 fields. The other
855 paths retain their declared types. The current generic decoder is unchanged.
Root/header names are versioned S3g V6.3 types; earlier layouts stay untouched.

Four focused tests pass: exact inventory path/type equality, INT step-number
range refusal, health-owner values/unavailable groups with full unsigned bits,
and refusal to generate an incomplete stage-9 deployment image. The health
mapper preserves existing availability/quality semantics and clock source.
Private work/label tags have effective None access.

The generated layout/health probe compiles on **both v38 targets**
(`EchoController`, `PhysicalController`). Required SDK operation log gates,
strict read-back and effective-access/type-member audits pass on both exports.
Counts are **136 UDTs / 7 AOIs / 140 tags / 1 program / 1 task**, with 353
descriptions. The native REAL `1/3` initializer and DINT high-bit words are
included in the strict typed initializer comparison, without value tolerance.

The qualified source is `metrics_layout_probe_05.L5X`, SHA-256
`d580716ab1a9edefbd78538b8062431fd37e889c52fdba09d00668de832bf76d`.
It preserves the S3f executable bodies and adds **one uncalled health routine**.
It qualifies types/layout and that mapper, not OEE/profiler behavior or a live
snapshot. Full stage-9 generation explicitly refuses until the remaining
contract and algorithms pass. No ACD, deployment helper or native authorization
file exists in this work directory.

S3f still regenerates byte-for-byte to
`B71E30ABBE8221AAA39A0DF8EEB934897FE0A4B0711047EFDC7D653A20AE7CF3`.
Current AB source bindings total 145: the existing publisher changes, with the
metrics module and its tests added. The 143 previous bound sources otherwise
match; owner's unrelated edits are preserved. All 23 predecessor canonical
seals / 5,032 artifacts verify unchanged.

## Dependent value decision

The approved type-only draft said all other values remain identical. Boundary
analysis proved that this conflicts with the approved Core arithmetic:

- At RunMs=2^32, wrapping to zero changes availability/performance/OEE validity.
- Core unsigned good/NOK total `0xffffffff + 1` wraps to zero and changes
  quality validity, whereas the legacy signed/clamped calculation stays valid.
- Count bits `0x80000000` are positive as Core UDINT; the legacy signed
  `Count > 0` test hides the profiler row's other values.

The [follow-up review](../AB_CANONICAL_PUBLICATION_S3G_DEPENDENT_VALUES_REVIEW_2026-10-23.md)
therefore enumerates **224 proposed dependent value paths**: 64 OEE validity
flags and 160 profiler row values. Their types do not change and they do not
overlap the 200 type paths. This additional amendment is **pending**, not
inferred from the original approval. The machine-readable counterexamples
and complete path list are retained in `Analysis/boundary_implications_02.json`.
The dependent publication/reference algorithms have not been applied.

## Memory, gates and remaining work

The eight-observation advisory forecast for this **partial layout/health probe**
is 2,389,568 used Blocks; its conservative planning budget is 2,706,710 of
3,145,728 Blocks. This is not a Studio Capacity measurement or a full-image
fit gate. The completed S3f image remains the latest calibration observation.
Exact automatic Capacity and scan measurements wait for a complete S3g image.

- Full AB discovery: **2,118 tests in 292.085s, OK**.
- Specification/contracts, strict consistency, repository gate tests and the
  established CRLF-aware whitespace gate pass; raw outputs are archived.
- Flutter gates are not applicable; no HMI source changed in this work.
- No controller operation ran. The last verified live image is the restored
  genealogy baseline in the S3f runtime evidence; no fresh live-state claim is made.

After the dependent value decision: implement/version the exact Core OEE and
profiler reference/publication, exercise high-bit/wrap/fraction/history cases,
generate a complete image, repeat applicable compiler/read-back/access/full
suite gates, measure exact-image Capacity, then request a concrete guarded
session with rollback/regressions. Live equivalence, scan, physical and CIP
Security gates remain open. No commit or push.

## Failed attempts retained

The first schema test used the wrong engineering root key; it was corrected.
The first layout probe's whole-document XML round-trip failed native import.
Subsequent generation preserves the native serialization/CDATA and code graph;
that source imports and compiles. One section-selector assertion caught multiple
Tags scopes, and another caught insertion into the AOI rather than the program.
Both stopped before emitting a file. A mistakenly launched missing-file SDK
invocation returned 2 without opening a project. All five failed outputs and
their source helpers remain, alongside passing retries. No controller was involved.

The sibling payload manifest binds this report, exact probes/exports, compiler,
read-back/access outputs, scope/approval records, failed runs, current source
snapshots, contract proposals, counterexamples and predecessor seals.
