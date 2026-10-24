# AB S3a Unit core: offline preparation, 2026-10-21

The S3a candidate implements the owner's selected logical array view and
passes its offline gates. The exact prepared ACD and review copy are ready.
**No S3a controller change has run.** Its Capacity result, current guarded
session authorization, runtime equivalence/regressions and native scan
measurement remain open. Shipping Part III/V1 remain authoritative.

This follows the accepted [S2 runtime](AB_S2_CANONICAL_RUNTIME_2026-10-21.md).
See the [S3a wire candidate](../AB_CANONICAL_PUBLICATION_S3A_WIRE_DRAFT_2026-10-21.md),
[independent inventory](../AB_CANONICAL_PUBLICATION_S3A_INVENTORY_2026-10-21.json)
and [payload hashes](AB_S3A_CANONICAL_PREPARATION_2026-10-21/manifest.json).
The payload retains failed/earlier runs. No native ACD or credential file is
archived. Source commit a1163c7c7bec21988167bc971145b1366206e9ce plus the
uncommitted canonical work; no commit/push is authorized or performed.

## Implemented surface and array contract

The explicit migration subset grows from 46 to **94 paths** with the current
three models. It adds Decision, CM command catalogs/counts, mode policy,
supported modes/run styles and the available-model catalog/capacity. The
existing projection defines the expected paths independently of discovery.
Only the five previously approved D2 corrections may remap indices; three
of those arrays occur in this surface. No extra unused slot is accepted.

V6.1 appends CountPath and Indices to each physical Fields row. CountPath is
a same-root integer scalar reference; Indices is an explicit sorted JSON
selection, including [] for an empty selection. All annotations and reference
types are validated against the schema, including below empty arrays. Live
counts are checked against the declared logical capacity. Storage can reserve
more entries than the published view. Dynamic model count is not frozen into
the metadata hash. Sparse mode ordinals remain their Core ordinals.

Core capacities are derived by engineering code from the Core parameter
declarations. The runtime reader imports no station, declaration, generator
or Python projection. Native BOOL arrays, Core string widths, typed values,
effective access and strict template byte sizes remain enforced. Private
indices/caches stay outside the whole-read root. Decision text refreshes on
DecisionId changes; immutable append-only model codes refresh on Count changes.

The S2 source regenerates byte-identically as
9398A04EE4ABECF74C006CF0BD2AB516D8EA3AE5607D37041AB8AE0CD0FE725E.
The new reader replays the sealed S2 capture to exactly the same complete
46-node/seven-module snapshot. V6.0 remains readable.

Decision.Timeout/SourcePath have no oracle paths and remain an explicit
full-Core gap. This stage does not fabricate them or claim complete Core
conformance. Live creation/deletion of models is not in the proposed runtime
fixture; count changes, zero counts and sparse views have synthetic reader
coverage. Runtime acceptance is still required for this PLC publication.

## Exact artifacts and native gates

Work folder:
`C:/work/fraktal-ab-s3a-20261021/prepare_0d22cab49f6e4aeeb6fa005ef0f4f9be/`.

- Source genealogy_s3a_final.L5X:
  83443758841A5B5F8D334106079EB8B041F2FF3E3419DB99564108532E361095.
- Prepared s3a_canonical.ACD:
  F1D24CA83A3A452E02402AD7604A373B592909A55AA4858F510111A54A7EE79F.
- capacity_review.ACD is initially a byte-identical copy of that ACD. Open
  the review copy in Studio, preserving the pinned deployment file.

Both v38 SDK targets, EchoController and PhysicalController, accept the final
source with clean import/build/Save As audits and equivalent full read-backs.
These are offline compiler targets, not physical controller deployments.
Read-back checks 76 UDTs, seven AOIs, 117 controller tags, one program/task,
44 executable bodies and 23,064 authored initial values. Top-level R6 and all
18 canonical type/member access audits pass on source, both compiler exports
and the reopened prepared ACD export.

The ACD is imported/built, saved, reopened, rebuilt and exported before pinning.
Its audit and full read-back pass. Final C# session-helper build reports zero
warnings/errors and uses C:/Python314/python.exe for its guards. Current
authorization and exact candidate/prior-stage Capacity checks remain enforced.

The V6.1 manifest has 76 metadata rows, hash
1E4B991CB3328C858823F8755D8B279BECDF9F5E0FF61E4D131A6BA8790D4546,
revision 31766929. The V5 oracle remains 6DEC4C1DC2F7F78A. These are generated
metadata identities, not live S3a observations.

## Validation and retained runs

- Final full AB suite: `Ran 1960 tests in 263.458s` / `OK`.
- Focused reader/publication/fixture suite: `Ran 48 tests in 0.828s` / `OK`.
- Root suite: `Ran 74 tests in 1.943s` / `OK`.
- Spec/contracts checks pass; strict consistency reports zero errors/warnings.
- CR-at-EOL whitespace check passes while preserving existing stored CRLF.
- Prepared and both native exports have clean SDK audits, equivalent
  read-backs and passing access audits.

The first focused run retains one failure and one error: schema validation
changed the root-identity failure order and exposed a missing-handle KeyError.
Root decode/identity validation now precedes schema annotation validation;
the required refusal behavior is restored. Corrected focused runs pass.

The earlier prototype compiled/read back on both targets. It predates the
final change-driven publication and explicit JSON empty selection, so its
results are retained separately from the final source-bound native runs.
An earlier full suite passed 1,957 tests before the last fixture coverage;
the final 1,960-test run is the acceptance gate. Raw test logs retain their
Windows child-process output bytes, including expected negative-test messages;
they are hashed without transcoding. This stage changed no HMI code, so Flutter gates
are inapplicable and no Flutter SDK was selected.

Read-only S3a equivalence against the currently loaded legacy genealogy exits
1 with "canonical manifest missing or ambiguous". This expected precondition
refusal is retained; it is not a failed live S3a comparison. Readiness confirms
the expected service/listener/identity, Run/not faulted/Remote, advancing scan
273661 to 273686, MANUAL/idle, logout, not restoring, original policy and all
five saved documents equal live. A fresh preflight is recorded once.

## Proposed session and remaining gates

RUNBOOK.md and the false approval/Capacity templates describe the exact next
session: fresh backup; guarded candidate Program/download/Run; five-document
restore and the original 31 regression rows; four additional **read-only**
paired captures before existing decision answers; idle 94-path equivalence,
generic native capture and native scan measurement; genealogy rollback using
a fresh hash-checked copy; five-document restore and 31 baseline regressions;
final readiness/policy/document checks. No extra command/stimulus, model
creation or fault clear is included. The inherited fixture owns every write
and cleanup, including its active-session and identity checks.

The prior-stage Capacity baseline is the sealed S2 candidate: **745,244 used /
2,400,484 available / 3,145,728 total blocks**. baseline_capacity.json is
hash-bound to that record. Neither the S0 69% probe nor genealogy's 22% replaces
it. Only the new candidate needs a Studio measurement. The prior S2 native
observation is median LastScanTime 109 us, cumulative MaxScanTime 1,177 us,
zero overlaps; later comparison must disclose the changed read workload.

S3a exit remains open until current approval, exact-artifact Capacity,
same-scan path/type/value equality, candidate/restored-baseline regressions,
native scan and final restoration pass. S3b-S7, physical/security acceptance
and shipping V2 activation also remain open. All controller-changing
operations still require current authorization under AGENTS.md §3a.
