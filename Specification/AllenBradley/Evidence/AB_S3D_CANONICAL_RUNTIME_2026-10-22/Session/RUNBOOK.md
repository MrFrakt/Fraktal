# Prepared S3d session ? current approval required

Target: local Echo 127.0.0.1 slot 0, L81E v38.011 serial 601FC87B.
Candidate: E5CA9AB3493AABF93E72A728EBDF5630E8056EEA2AC82254B38913B8C7CF7C9D.
Source: 03E0775EDD8A1A22D88D198D4D3CE2B7C19A2F2029A40E3C428CB838FC2EE962.
No controller-changing operation has run. authorization.template.json is false.
Fault clear and clock changes are outside this scope. No commit/push.

## Before approval

Offline builds/read-backs/access pass; 2,062 AB tests pass. Measured Capacity
is 41%, 1,290,016 used / 1,855,712 available / 3,145,728 total Blocks, +182,464
over S3c. Current Echo is verified MANUAL=1/idle, logged out, genealogy restored.
One preflight already exists and verifies; never overwrite it. Conditional
MANUAL normalization before backup and after fixtures must be included in
current approval. The completed S3c session grants no S3d authorization.

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
3. Run scripts/preflight.py --verify-only against the already recorded
   preflight.json. All later calls compare against it. Correct manual ordinal, idle, logout and all five
   saved/live documents must pass; never overwrite the preflight.
4. S3dSession.exe backup. Audit Save As (SDK upload label is Open Project From
   Controller), backup.sha256. Run audit_baseline_access.py against the backup L5X,
   requiring the exact sealed genealogy tag/access policy. Candidate audits use
   audit_access.py, with both canonical bindings; do not apply that list to legacy.
5. S3dSession.exe deploy-canonical. Audit clean Build/Download/Save/Run and the
   equivalent canonical_downloaded.L5X; audit its R6/member access. Preserve
   original pin even though SDK saving changes the deployment ACD hash.
6. With FRAKTAL_AB_DECLARATION=fraktal_ab_genealogy_demo run
   fraktal_ab_s3d_fixture_execute.py --execute-fixture --expect-serial 601FC87B
   --credential-file C:/work/fraktal_echo38_access_fixture.json --output <new>.json.
   This restores five documents and runs the inherited 31 regressions. It adds
   read-only decision/held/fault pairs, 21 sequence pairs and before/after
   captures around its existing blocking resets. Audit with
   verify_runtime_acceptance.py <fixture> --output <new>.json: all 2125 values,
   types and same-scan proof; four decisions; held/fault across ordinals 0/1/2;
   seven sequence cases across ST/SFC/LD, including mode clear, sparse warning
   and retained completed steps shorter than 100 ms; reset before/after coverage
   at all renditions, active and closed alarms/duration, state-flag transitions.
   Record observed WAIT_RESET and ring-wrap coverage separately. Never relabel
   model coverage as runtime coverage or waive missing required coverage.
7. Run ensure_manual.py again after fixture cleanup, then read-only
   fraktal_ab_s3d_equivalence.py --expect-serial 601FC87B --output <new>.json.gz;
   generic fraktal_ab_canonical_acquire.py capture/snapshot; measure_timing.py
   <new>.json --candidate. Retain native TASK scan/overlap observations. From the generic capture,
   record Template byte sizes and complete raw payload sizes for the root and
   both bindings; do not infer them from source counts.
8. S3dSession.exe restore-genealogy. It verifies and copies the immutable
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
