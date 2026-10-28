# S3k exact predecessor-revision compatibility and retry preparation

Client date: 2026-10-25, America/Mexico_City. **Offline preparation passes;
native S3k acceptance remains open. Genealogy is restored.** No corrected-image
download, mailbox write, mode change, fault clear, clock change, power operation
or vendor-state edit occurred during this preparation. No commit or push.

The preceding authorized request attempt and successful genealogy rollback are
sealed separately in the [attempt record](AB_S3K_CANONICAL_ATTEMPT_2026-10-25.md).
That instruction is consumed. This package prepares a new exact-image session;
it does not manufacture current authorization.

## Diagnosis and correction

The failed request walk passed two Access cases and five paired captures, then
stopped at `configuration restore failed: station load refused`. It never reached
the main regression rows or typed command vectors. All five saved documents
carry configuration revision **7203916**, while S3k publishes **14896938**.
Baseline and candidate configuration Record declarations are exactly equal.
Deriving the candidate at publication stage 12 reproduces the exact baseline
manifest `6DEC4C1DC2F7F78A`. S3k's report/localization publication changes identity
without changing those configuration schemas.

The existing shared `revision_rejected` validator now recognizes that exact
predecessor, derived from the same declaration only at stage 13. It does not
rewrite saved documents or substitute revisions at the client. Existing schema,
station identity, type, range, permission and transaction checks remain. Five
executed regression tests cover exact predecessor/current acceptance, changed
record shape, foreign station, unknown/invalid revisions, older-profile refusal
of the future revision and the native short-operand guard. The five saved
document headers and all 38 rows pass the corrected revision predicate offline;
this is not a claim that the full native restore has passed.

The first corrected build exceeded the native compiler's operand-character
limit. The guard now snapshots the long array-member operand into an existing
free scratch before comparing it. The following duplicate loop initializes that
scratch before use. The failure and both generated versions remain archived.
Against the failed downloaded source, the final generated diff changes only
`FRK_Press_ConfigSets`; all data types and controller tag initializers are equal.

## Exact artifacts and gates

- Generated L5X SHA-256: `D7CB30284ECCA051DAB32FDF76421B44676C75FD917F6AA5B8FB1E52BD15A494`.
- Prepared pristine ACD SHA-256: `12211B815C81C6D67AFB9ABF13137E1FC21E7FC375A7D11F6FD828A4645995D9`.
- Canonical V6.6 ContentHash unchanged: `C3501F2A7CFD6D33D3C221669BE3AE9862A96ED58002216E1D836F5BFB94DECC`.
- Immutable genealogy original: `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.

| Gate | Result / exact output |
|---|---|
| Focused revision tests | Five pass; `Preparation/focused_02.log` |
| Full AB discovery suite | **2,292 tests**, OK; `Preparation/ab_suite_02.log` |
| Root tests | **74 tests**, OK; `Preparation/final_root_tests_01.log` |
| AB spec, frozen contracts, strict consistency and whitespace | Pass; `Preparation/final_{spec,contracts,consistency,whitespace}_01.log` |
| Both v38 target builds | **0 warnings/errors**, EchoController and PhysicalController; `Preparation/native_*_02.log` |
| Both native read-backs and prepared ACD read-back | `Equivalent: true`; `Preparation/readback_*_02.log`, `prepared_compare_02.log` |
| Effective access and SDK log audits | Clean; `Preparation/access_*_02.json`, `sdk_audits_01.json` |
| Prior accepted image regeneration | **12 / 12** byte-identical on final source; `Preparation/accepted_images_02.json` |
| Prior capture replay | **1,385 / 1,385** exact values/types; `Preparation/capture_replay_01.json` |
| Retry authorization checks | **13** negative field/scope cases plus no-approval CLI refusal, before controller access; `Preparation/retry_checks_02.json` |
| Retry SDK helper build | 0 warnings/errors; `Preparation/retry_helper_build_02.log` |
| Corrected image native request/scan | **Not run**; fresh exact-image authorization required |

An earlier full suite overlapped a subsequent source edit and is explicitly
superseded by `ab_suite_02`; it is not used as final-source validation. The first
offline saved-document checker used the row revision spelling on a header and
failed before any controller access; the corrected checker treats `configRev`
and `rev` separately. Initial unexecuted helper path drafts and their corrected
build are retained. Every failed run remains in the payload.

## Memory and timing

Automatic Studio offline Capacity on a disposable review copy of the pinned
ACD measures **1,903,308 used / 1,242,420 available / 3,145,728 total Blocks**,
**60% displayed**. Source unchanged and review process closed are verified.
This is **4,284 fewer Blocks** than the failed image and **160,228 more** than
accepted S3j, within the existing 80–200 K Block budget. Capture and exact image
hash are bound in `Preparation/capacity_auto_02.json` and `capacity_capture_02.json`.
Native scan for this corrected image is pending; earlier failed-image idle
measurements are not transferred to it.

## Prepared session and rollback

Target: local Echo **601FC87B**, 1756-L81E v38.011, **127.0.0.1 slot 0**, Remote
keyswitch, GUID `91dec7d6-8ac3-45c9-ab2e-0d039c7006fd`. Work folder:
`C:/work/fraktal-ab-s3k-20261025/retry_revision_01/`.

`retry_session.py` requires a new `authorization.json`, exact source/image and
gate hashes, and an append-only single-use start record. Only an unapproved
template exists. It is prepared to:

1. Check service, listener process, exact identity, keyswitch, no fault/dumps,
   no active session and an idle Unit; normalize MANUAL only under approval.
   Record a fresh five-document preflight and backup, auditing Save As/access.
2. Program/download/Run the corrected pinned image; audit SDK, native read-back
   and effective access. Select the exact S3k declaration for the harness.
3. Run the unchanged 41-case legacy walk and prepared typed command vectors:
   queries/refusals, one restored configuration edit, login/logout with full-width
   secret/text wipe, independent ACKs and dual-ingress collision observation.
   Fixed vectors and write surfaces are unchanged. No PIN enters evidence.
4. Stop candidate work at its first failure. On success, run read-only generic
   acquisition, path/type equivalence and native scan measurement.
5. After any download attempt, attempt guarded MANUAL normalization and
   genealogy rollback in `finally`, retaining fault/dump/idle/session guards.
   SDK opens only a hash-checked copy of the immutable genealogy ACD. Restore
   five documents, run all 31 baseline checks, normalize MANUAL, and verify
   final Run/no-fault/scanning/idle/logout/not-restoring/document equality plus
   the original preflight. Record any rollback refusal instead of weakening it.

This added download is outside the completed request/rollback grant.
[AGENTS.md §3a](../../../AGENTS.md) requires “current explicit authorization”
for every controller-changing operation and says “Prior authorization is
historical and shall not be inferred.” New exact-image confirmation is the
remaining preparation gate. Fault clears, clock changes, power operations,
vendor-state edits and hard kills remain excluded.

S3 final press ST/SFC/LD and real-module identity/offline proof, S4 desktop,
S5 gateway/installer, S6 retirement/persistence/event ownership and S7 physical
CIP Security acceptance remain. V2 is inactive. HMI unchanged; Flutter gates
are not applicable. The owner's unrelated Siemens archive edits are untouched.

Payload: [manifest](AB_S3K_CANONICAL_REVISION_RETRY_PREPARATION_2026-10-25/manifest.json).
All 59 preceding seals, including the failed attempt, are verified unchanged.
No credential files or ACD/BAK binaries are archived.
