# S3e prepared session - no current authorization

Local Echo 127.0.0.1 slot 0, L81E v38.011 serial 601FC87B.
Source 3BFFCEADB98EC7B7B7AA05550202CC187C736A8C2B22C75B7B7D158BE4F5AD87.
Original ACD pin 95E85B507387A548553688C1B5CCF52D7D99B35751C68F1B02DE92AC2A1B240B.
No S3e controller-changing operation has run. authorization.template.json is false.
No commit/push. Fault clearing and clock changes need separate authorization.

Both v38 builds/read-backs/access pass. The prepared ACD was reopened/rebuilt
and exported equivalently. Automatic exact-image Capacity is 49%, 1,568,852
used / 1,576,876 available / 3,145,728 total Blocks, +278,836 over S3d.
76 source bindings are pinned. S2/S3a/S3b/S3c/S3d outputs and replays are unchanged.

## Scope for the next explicit approval

Guarded MANUAL normalization when needed; fresh backup; Program/download/Run;
five-document restoration and the inherited 31 candidate rows; two additional
fixed Access checks; read-only 2,154-path decision/condition/sequence/reset/
access captures, native record sizes and scan; genealogy rollback; five-document
restore and original 31 baseline rows; MANUAL cleanup and final checks.

The two additional checks add one unknown-user LOGIN (fraktal_s3e_no_user,
public noncredential test input) before the existing valid login, then one
read-level change/restore on the last declared data class (commissioning here).
Its original level is captured and restored in a finally block. The captured
policy must equal its exact original after restoration. These add two separate
s3eAccessRows, leaving the inherited rows at 31. Expected planned rows total
64: 31 + 2 candidate, 31 baseline. Additional tag-write call count is unmeasured.

Do not archive/read/print the actual credential file contents. Tools read it
internally from C:/work/fraktal_echo38_access_fixture.json. Observer metadata
never includes command arguments. LOGIN stays plain PIN; no declaration-based
prehash is used by this canonical acquisition path.

## After exact current approval and preparation seal

1. Create a unique runtime folder and copy run_logged.py. Every output is new.
   Verify the seal, all 76 sources, prepared/review pins and immutable genealogy.
2. Record the owner's response/scope in a new authorization.json. Set
   CurrentOwnerApproved, ManualNormalizationAuthorized and AccessVectorsAuthorized
   true, bound to the exact pin/serial. FaultClearAuthorized remains false.
   The completed S3d approval grants no S3e authorization.
3. Run scripts/guard_echo.py; ensure_manual.py --output <new>; scripts/preflight.py
   --verify-only. preflight.json was recorded once; never overwrite it.
4. S3eSession.exe backup, hidden detached. Normal upload takes about 2 min 40 s.
   Audit Save/Save As with fraktal_ab_sdk_log_gate; verify backup.sha256 and
   audit_baseline_access.py <backup-L5X> --output <new>. Require exact baseline.
5. Verify preflight again; S3eSession.exe deploy-canonical. Audit Download/Save/
   Save As/Change Controller Mode, strict read-back and audit_access.py <L5X> <new>.
   SDK saves change the candidate hash; never replace the original pin.
6. With FRAKTAL_AB_DECLARATION=fraktal_ab_genealogy_demo, run
   fraktal_ab_s3e_fixture_execute.py --execute-fixture --expect-serial 601FC87B
   --credential-file C:/work/fraktal_echo38_access_fixture.json --output <new>.json.
   No concurrent controller reads. It includes the two explicit Access vectors.
   Audit verify_runtime_acceptance.py <fixture> --output <new>: 31 inherited
   rows, two Access rows, four decisions, held/fault all renditions, 21 sequence
   captures, reset pairs all renditions, six Access phases, 2,154 typed values,
   equal-even live scan proof, V6.2 metadata revision coherence. LoginBusy,
   failure, authenticated authority, logout, manual/class-policy changes and
   audit actor/action text must be observed. Never weaken retries/time budgets.
   Ring wrap and WAIT_RESET runtime coverage are recorded as observed.
7. Normalize MANUAL; idle equivalence; generic capture/snapshot; measure native
   root/binding Template and payload sizes; measure_timing.py <new> --candidate.
8. S3eSession.exe restore-genealogy uses a hash-checked new copy of the immutable
   original; never open C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD.
   Audit SDK/read-back/exact baseline access. Restoration stays available after
   an interrupted authorized deployment; no fault clear is authorized.
9. Original fraktal_ab_genealogy_execute.py with the same flags, new output;
   require 31/31 and document/policy restoration. Normalize MANUAL afterward.
10. Final guard/inspect/final_checks/preflight --verify-only/native baseline scan:
    Run, not faulted, Remote, scanning, MANUAL=1/idle, logged out, not restoring,
    five saved/live documents equal, original policy/preflight/genealogy hash.
11. Preserve all failures and actual extra rows/known mailbox commands. Replay
    captures independently; verify sources and all 15 prior seals. Seal new
    runtime evidence and update mutable records. Add Capacity to calibration
    only after accepted runtime. Mark approval consumed. No commit/push.
