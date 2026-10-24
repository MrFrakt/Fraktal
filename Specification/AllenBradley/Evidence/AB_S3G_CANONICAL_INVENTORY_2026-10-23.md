# S3g publication inventory — owner review required

2026-10-23. Offline analysis after the accepted
[S3f revision follow-up](AB_S3F_CANONICAL_REVISION_RUNTIME_2026-10-23.md).
**No S3g implementation or native acceptance is claimed.** Controller access,
tag writes, production source changes and acceptance-rule changes are zero.

The immutable genealogy projection expands to SHA-256
`5ca907e6076a02833a5670ef3741cd62aca626f762f9dd557f1e4b9c2c3bbe0c`.
The analyzer reads its values and the owning Core declarations, verifies the
existing profile/history/trend bounds, and identifies 1,055 additional paths:
11 Oee, 121 OeeTrend/head, 900 Profiler, 23 SystemHealth. None overlaps the
previous 2,955-path legacy inventory; cumulative legacy coverage is 4,010.

There are 200 numeric type conflicts: **64 Double→Float, 101 Int32→UInt32,
35 Int32→Int16**. Float32 rounding and the three Core UDINT time-bucket wraps
can change values; the record includes explicit counterexamples. No oracle
value, numeric type or allowed exception was changed by the analysis.

The [review draft](../AB_CANONICAL_PUBLICATION_S3G_CONTRACT_REVIEW_2026-10-23.md)
and [complete path inventory](../AB_CANONICAL_PUBLICATION_S3G_INVENTORY_2026-10-23.json)
define the proposed finite amendment. Owner approval is required because the
current plan's allow-list covers D2 and S3f, not these new S3g differences.
Later memory/scan, compiler/read-back, exact equivalence and native gates remain.

The initial analyzer emitted a Python ElementTree truth-value deprecation
warning; its output and source remain. The corrected analyzer uses explicit
None checks, verifies the owning Unit fields and all three bounded tables,
and reproduces exactly the same 1,055 paths and 200 differences.

The AB executable sources are unchanged from the completed S3f closing gates:
2,114 AB tests pass. Repository gates/tests are repeated for the new documents.
All 22 predecessor canonical seals / 4,849 artifacts verify unchanged.
No new PLC build or download is applicable to this inventory-only change.
No ACD or credential file is archived; no commit or push is authorized.

The sibling payload holds the analyzer versions, both inventories, current
source/hash bindings, validation and gate outputs, predecessor seals and the
review snapshot. Its manifest binds every artifact and this report.
