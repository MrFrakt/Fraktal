# S3f prepared session — current controller authorization pending

Local Echo 127.0.0.1 slot 0, L81E v38.011 serial 601FC87B.
Prepared ACD A05695F15ED162B500D353528621CE0AB92D36E8240339DAAD001DA928E3EB66.
Source 7BBAD050BFD82D3C76DD84E82644AC1AAE5A772125CC02AAC7DD93FE1F621C28.
The approved contract correction permits offline work only. No current
controller authorization exists. No commit/push, fault clear or clock set.
Automatic exact-image Capacity: 73%, 2,298,412 / 3,145,728 Blocks.

## Approval scope

Guarded MANUAL normalization when needed; fresh backup; Program/download/Run;
five-document restore; 31 inherited candidate regressions plus the two inherited
Access vectors; eight configuration cases described below; read-only paired
equivalence, native sizes and scan; genealogy rollback; five-document restore
and 31 baseline regressions; MANUAL cleanup and final checks. Planned recorded
rows: 41 candidate, 31 baseline, 72 total. Per-tag writes are unmeasured.

The additional configuration commands are fixed: QUERY_CONFIG page 0/1/2 and
model bank 2; one station scalar edit and exact restoration; raising the last
class read level to 4, logout/login and exact policy restoration; isolated
SAVE/LIST/EXPORT/IMPORT/LOAD/DELETE and one absent-set refusal; four malformed
provider proposals (stale parent, stale login, count overflow, invalid UTF-8).
All responses use the appended public HmiRequest.ConfigProvider frame, bounded
chunks and a separate final Commit. No private work tag or arbitrary public
record becomes writable. Only the two fixed names in the new isolated directory
are deleted. Actual credential contents are never printed or archived.

## Execute only after current exact-session approval

1. Verify the sealed preparation, current source bindings, both prepared/review
   pins and immutable genealogy pin. Create a unique runtime folder with a
   run_logged.py writing only there. Never overwrite any preparation output.
2. Record owner approval in a new authorization.json bound to the exact ACD and
   serial. Set CurrentOwnerApproved, ManualNormalizationAuthorized,
   AccessVectorsAuthorized and ConfigurationVectorsAuthorized true. Keep
   FaultClearAuthorized false. The contract approval cannot arm the helper.
3. Run scripts/guard_echo.py. It requires Running Echo service, local 44818
   listener owned by EmulateControlLogix5580, exact CIP/controller identity,
   not faulted and Remote keyswitch. Run ensure_manual.py --output <new> when
   needed, then scripts/preflight.py --verify-only. Never replace preflight.json.
   Refuse active operator sessions, configuration differences or a fault.
4. S3fSession.exe backup, hidden detached. Audit Save/Save As with
   fraktal_ab_sdk_log_gate.py. Verify backup.sha256 and audit_baseline_access.py
   <backup-L5X> --output <new>. Require exact baseline tag access.
5. Verify preflight again; S3fSession.exe deploy-canonical. Audit Download,
   Save/Save As/Change Controller Mode. Compare read-back with generated source
   using fraktal_ab_readback.py, then audit_access.py <export> <new>. SDK saves
   change the ACD hash; never replace its original pin or redeploy a spent session.
6. With FRAKTAL_AB_DECLARATION=fraktal_ab_genealogy_demo, run
   FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s3f_fixture_execute.py
   --execute-fixture --expect-serial 601FC87B
   --credential-file C:/work/fraktal_echo38_access_fixture.json --output <new>.json.
   No concurrent controller reads. The fixture restores the five documents before
   the config vectors. Verify_runtime_acceptance.py <fixture> --output <new>
   requires all 31 inherited/2 Access/8 config cases and unchanged same-scan proof.
   Each page compares every declared path and type: 2,617 / 2,567 / 2,217 for
   pages 0 / 1 / empty. Keep 100 attempts / five seconds; do not relax the proof.
7. Normalize MANUAL; capture idle S3f equivalence and generic snapshot/raw bytes;
   measure native root and bound record sizes; measure_timing.py <new> --candidate.
   Provider catalog/document are empty after cleanup; the pending audit stamp
   must still have independent provenance for the standalone reference oracle.
8. S3fSession.exe restore-genealogy downloads a hash-checked new copy. Never open
   C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD. Audit SDK, read-back
   against the sealed genealogy export and exact baseline access. Rollback stays
   available after an interrupted authorized candidate download.
9. Run fraktal_ab_genealogy_execute.py with the same flags and a new output.
   Require 31/31, restoration and original policy. Normalize MANUAL afterward.
10. Final guard/inspect/final_checks/preflight --verify-only/native baseline scan:
    Run, not faulted, Remote, scanning, MANUAL=1/idle, logged out, not restoring,
    five documents equal live, policy/preflight/genealogy original unchanged.
11. Retain every failure. Record actual rows and known commands; replay all raw
    captures independently. Verify source bindings and predecessor seals; append
    runtime evidence. Add Capacity calibration only after accepted runtime.

Native retained restart/active-model-change coverage is not added by this fixture;
its separate acceptance remains open. S3f is not fully accepted while those
required native vectors are unproved. Later S3 surfaces, S4-S7, physical security
and HMI remain open. No full-Core or shipping activation follows from preparation.
