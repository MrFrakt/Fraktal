# Prepared S3c session ? current approval required

Target: local Echo 127.0.0.1 slot 0, L81E v38.011 serial 601FC87B.
Candidate: A255918860C3062D8F0DF3FA4E70373EF84372DDB3214E050AF23A08A0C2286C.
Source: E58BB88F9E63BE9144AF90C4032714F9B44B167CA02E2B2A64C933788F4E70A2.
No controller-changing operation has run. authorization.template.json is false.
Fault clear and clock changes are outside this scope. No commit/push.

## Before approval

Offline builds/read-backs/access pass; measured Capacity is 35%, 1,107,552 used
and 2,038,176 available of 3,145,728 Blocks, +115,940 over S3b. The inherited
MANUAL=0 guard was wrong. Current Echo is AUTO=0/idle, logged out; the corrected
preflight refuses it. MANUAL normalization is an explicitly separate part of
the proposed session and must be included in current owner approval.

## After current approval of this exact session

Record the owner's exact response and scope in a new authorization.json,
setting CurrentOwnerApproved and ManualNormalizationAuthorized true; bind the
exact serial and original pin. Do not authorize fault clearing. Recheck all
source bindings and prepared pins. Create a new runtime directory and a copy
of run_logged.py there; use it for every operation with a fresh label. The SDK
helper's fixed files remain in this preparation folder and must not exist
before the session. Audit every SDK log with fraktal_ab_sdk_log_gate.audit_log.
A nonzero/content-audit failure stops dependent work; keep recovery available.

1. Run scripts/guard_echo.py: service/listener/exact identity, Remote keyswitch,
   not faulted, Run. No service start/fault clear by this helper.
2. Run ensure_manual.py --output <new>.json. It requires current approval,
   idle/unlatched/logged-out/not-restoring state and exact legacy image. Only
   existing LOGIN / SET_MODE(1) / LOGOUT frames are used; the credential file is
   read internally, never printed or archived. No change if already MANUAL.
3. Run scripts/preflight.py once to create preflight.json. Later --verify-only
   calls compare against it. Correct manual ordinal, idle, logout and all five
   saved/live documents must pass; never overwrite the preflight.
4. S3cSession.exe backup. Audit Save As (SDK upload label is Open Project From
   Controller), backup.sha256 and read-back access/inventory as applicable.
5. S3cSession.exe deploy-canonical. Audit clean Build/Download/Save/Run and the
   equivalent canonical_downloaded.L5X; audit its R6/member access. Preserve
   original pin even though SDK saving changes the deployment ACD hash.
6. With FRAKTAL_AB_DECLARATION=fraktal_ab_genealogy_demo run
   fraktal_ab_s3c_fixture_execute.py --execute-fixture --expect-serial 601FC87B
   --credential-file C:/work/fraktal_echo38_access_fixture.json --output <new>.json.
   This restores five documents and runs the inherited 31 regressions. It adds
   read-only decision/held/fault pairs and 21 sequence pairs. Audit with
   verify_runtime_acceptance.py <fixture> --output <new>.json: all 647 values,
   types and same-scan proof; four decisions; held/fault across ordinals 0/1/2;
   seven sequence cases across ST/SFC/LD, including mode clear, sparse warning
   and retained completed steps shorter than 100 ms. Never waive missing coverage.
7. Run ensure_manual.py again after fixture cleanup, then read-only
   fraktal_ab_s3c_equivalence.py --expect-serial 601FC87B --output <new>.json.gz;
   generic fraktal_ab_canonical_acquire.py capture/snapshot; measure_timing.py
   <new>.json --candidate. Retain native TASK scan/overlap observations.
8. S3cSession.exe restore-genealogy. It verifies and copies the immutable
   genealogy original, then downloads only that copy. Audit the SDK log and
   equivalent restored read-back. Never open the immutable original.
9. Run original fraktal_ab_genealogy_execute.py with the same fixture/serial/
   credential flags and a new output. Require 31 passing rows, configuration
   and policy restoration. Run ensure_manual.py after its AUTO cleanup.
10. Run guard, inspect, final_checks.py <new>.json, preflight --verify-only and
    measure_timing.py <new>.json. Require Run, Remote, not faulted, scanning,
    MANUAL=1/idle, logged out, not restoring, saved/live documents equal,
    restored policy and unchanged genealogy original. Record native timing.
11. Record every failed run, actual extra row/write count and acceptance scope.
    Rerun changed-source gates only if needed. Seal a new runtime report and
    payload; never edit this preparation seal. Update mutable plan/notes.

If the candidate path fails after an authorized download attempt, preserve
failure evidence and use the approved genealogy rollback/restore sequence.
Never infer permission for a fault clear, clock set, new image or extra stimuli.
