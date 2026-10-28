# S3k private login sequence correction and guarded retry preparation

2026-10-25, America/Mexico_City. **Offline gates pass; the corrected image has
not been downloaded. Genealogy remains restored and S3k native acceptance is
open.** No controller-changing operation occurred during this preparation.
The preceding [failed typed-login run and completed rollback](AB_S3K_CANONICAL_REVISION_RETRY_RUNTIME_2026-10-25.md)
remain sealed. Its authorization is consumed. No commit or push.

## Corrected behavior and regression proof

Typed and legacy ingress have independent sequence numbers. The shared access
owner copied the external legacy `HmiRequest.Sequence` into its private
LoginRequest, then compared it with HmiLastSequence, which holds the selected
owner token. The preceding native run acknowledged and wiped typed LOGIN but
did not authenticate. A synthetic offline reproduction confirms that a correct
PIN fails solely when those two sequence numbers differ.

At stage 13, the private login snapshot now gets its sequence from
`mailbox.committed_sequence(app)`, the existing authoritative helper. The
external legacy commit and ACK are untouched. Every other profile emits its
previous code unchanged. Credential validation, registered levels, bounded
hashing, the 15-second fixture wait and full-width wiping remain intact.
No field, type or published contract changes.

Three coupled regression tests execute generated typed ingress and the access
owner: correct PIN login using the real generated SHA-256, wrong-PIN refusal,
and legacy login after a typed request. They check result tokens, independent
legacy commit/ACK, no replay on the next scan and credential wiping. Correct-PIN
cases fail against the old owner; all three pass after correction. Only
`FRK_PressHmiMailbox` changes in generated source; data types and controller tag
initializers are exactly equal to the preceding image.

## Exact image, memory and gates

- Generated source SHA-256: `B543336202821F95BC41A5A51441E86021F1BA9EFF28D42FABCD1AA83D7C782A`.
- Pristine ACD SHA-256: `AA4239C636647527CC37F3B3F18206821FBEE108D3315C5087DC0DCD1653BBDF`.
- Canonical V6.6 ContentHash unchanged: `C3501F2A7CFD6D33D3C221669BE3AE9862A96ED58002216E1D836F5BFB94DECC`.
- Rollback original SHA-256: `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.

Automatic Studio offline Capacity on a disposable hash-matched review copy:
**1,903,344 used / 1,242,384 available / 3,145,728 total Blocks**, **60%**.
The correction adds **36 Blocks** over the preceding image and **160,264 Blocks**
over accepted S3j, inside the existing budget. Source unchanged, fit and review
process closed are verified. This corrected image has no native scan measurement;
previous-image measurements are not transferred.

| Gate | Result / payload output |
|---|---|
| Coupled login tests | Three pass; `Preparation/login_tests_green_01.log`. Expected pre-fix failures retained in `login_tests_red_01.log` |
| Full AB discovery suite | **2,295 tests**, OK; `Preparation/ab_suite_01.log` |
| Root suite | **74 tests**, OK; `Preparation/final_root_tests_01.log` |
| AB spec / contracts / strict consistency / whitespace | Pass; `Preparation/final_*_01.log` |
| v38 EchoController and PhysicalController | Both build at **0 warnings/errors**; native and prepared-ACD read-backs equivalent |
| Effective access / SDK event audit | Clean; `Preparation/access_*_02.json`, `sdk_audits_01.json` |
| Earlier accepted images | **12 / 12** byte-identical; `Preparation/accepted_images_02.json` |
| Archived captures | **1,431 / 1,431** replay exactly, including 46 V6.6 captures; `Preparation/capture_replay_01.json` |
| Generated delta | One routine; identical types and tag initializers; `Preparation/source_delta_01.json` |
| Authorization refusal checks | **13** negative field/scope cases plus missing-approval CLI refusal before controller access; `Preparation/retry_checks_01.json` |
| Retry SDK helper | Build at 0 warnings/errors; `Preparation/retry_helper_build_01.log` |
| Corrected-image runtime requests / scan | **Not run**; new exact-image authorization required |

The full unittest log retains intentional parser-refusal output and a fixture
socket ResourceWarning; the suite result is OK. Compiler/import warning counts
are the separate native SDK gate above. Failed historical runs remain unchanged.

## Prepared session and rollback ownership

Target: local Echo **601FC87B**, 1756-L81E v38.011, **127.0.0.1 slot 0**, Remote
keyswitch, GUID `91dec7d6-8ac3-45c9-ab2e-0d039c7006fd`. Work folder:
`C:/work/fraktal-ab-s3k-20261025/retry_login_01/`.

The unapproved session requires exact source/image/gate hashes and an append-only
single-use record. It keeps the same fixed request vectors and write surface:

1. Fresh service/listener/identity/fault/dump/session/idle guards; MANUAL
   normalization only as needed; original five-document preflight; fresh backup
   with Save As/access audit.
2. Program/download/Run the exact corrected image; SDK/read-back/access audits.
3. Five-document restore, the inherited 41-case scope and prepared typed cases:
   queries/refusals, real configuration edit with exact restoration, PIN login/
   logout, full-width Secret/TextValue wipe, independent ACKs and collision
   observation. The current fixture inserts configuration and typed vectors
   before the main 31-case exercise. It stops at the first candidate failure.
4. On candidate success, read-only equivalence, generic acquisition and TASK scan.
5. After any download attempt, attempt guarded genealogy rollback in `finally`.
   SDK opens only a hash-checked copy of the immutable original. Preserve the
   candidate's host medium and restore the **exact original preflight documents**
   through the existing checked atomic FileMedium writer **before** the baseline
   fixture. Require unchanged configuration row values; keep all backups/hashes.
   This prevents the known forward-publication revision from blocking rollback.
6. Five-document controller restore, all 31 baseline cases, MANUAL cleanup,
   final Run/no-fault/scanning/idle/logout/not-restoring/document equality and
   original preflight verification. Fault/dump/active-session guards remain;
   a rollback refusal is recorded rather than bypassed.

Only `authorization.template.json` exists, with approval/operation flags false.
[AGENTS.md §3a](../../../AGENTS.md) requires “current explicit authorization”
and says “Prior authorization is historical and shall not be inferred.” The
completed `12211B81…45995D9` session does not authorize downloading this different
ACD. Current exact-image approval is the remaining gate. Fault clears, clock
changes, power operations, vendor-state edits and hard kills remain excluded.

S3 native acceptance remains open; press ST/SFC/LD and real-module proof,
S4 desktop, S5 gateway/installer, S6 retirement/persistence/event ownership and
S7 physical CIP Security acceptance remain. V2 is inactive. HMI unchanged;
Flutter gates are not applicable. Owner Siemens archive edits are untouched.

Payload: [manifest](AB_S3K_CANONICAL_LOGIN_RETRY_PREPARATION_2026-10-25/manifest.json).
All 61 preceding seals are verified unchanged. No credential files, PINs or
ACD/BAK binaries are archived.
