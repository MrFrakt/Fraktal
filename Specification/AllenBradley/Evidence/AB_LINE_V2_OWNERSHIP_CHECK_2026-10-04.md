# Line V2 — final ownership regression

Client date: 2026-10-04, America/Bogota; baseline `733a0df`. This supersedes
only the source-hash/test-count boundary of the
[preparation record](AB_LINE_V2_PREPARED_2026-10-04.md), whose JSON is preserved
at SHA `4BF62539895CA0051F68FEEB89E9E958AF786A614E00D583FFE4D889D6187AEB`.

Final review found model-scope checks comparing bare member names across
records. A Line field called `StartMin1` could therefore inherit a same-named
recipe field's bank routing, permission coverage or audit attribution. One
generator helper now derives scope from the owning ParCfg record and declared
model members; ordinary writes, set export/validation, creation and projection
use it.

The regression uses a valid synthetic application with identically named
recipe/Line fields. It executes emitted ST with model ordinal 2, checks both
storages and audit attribution, and checks the actual projected Line page.
Removing record ownership kills this test by assertion, with no interpreter
error. This is the seventh killed semantic mutant for the prepared stage.

The full final AB suite passes **1,591 tests**, including **20 Line behavior
tests** (217.434 seconds). Root tool tests pass 33; consistency has zero errors
and warnings. All HMI source hashes still match the prepared release, so its
495 passes/seven expected skips, clean analyzer and served asset proof remain
the applicable unchanged checks.

Fresh generation to `C:/work/press71_ownership_check_01.L5X` is byte-identical
to `C:/work/press71.L5X`, SHA
`381F1878F60CDFF79FBD3948ED622E1047319054A14F09CD65A21117EB96B140`.
The Press declaration has no colliding member names, so its manifest, UDT
layouts, memory/source trends and download artifact did not change.

No controller writes, clock changes, downloads or gateway restarts occurred.
The SDK's previously recorded missing activation still requires owner Studio
Verify/full download. Native Line, browser and physical-retention acceptance
remain pending; shared-root/mirror composition stays unbound.

[Machine-readable final checks](AB_LINE_V2_OWNERSHIP_CHECK_2026-10-04.json)
bind the final six source hashes, preserved preparation JSON, exact artifact
and private test-log hashes. No credentials are included.
