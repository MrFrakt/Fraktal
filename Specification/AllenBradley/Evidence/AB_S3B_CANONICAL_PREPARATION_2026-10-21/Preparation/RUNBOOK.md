# Prepared S3b guarded session (not yet authorized)

Target: local Echo 601FC87B, 127.0.0.1 slot 0, L81E/v38.011.
Prepared ACD SHA-256:
634A3A86B88E666CFFCA9F530AC1D279709078BCF3E2C7EC2727B4B134394EEF.
Generated source SHA-256:
72B9FAA0ECA228FEBAD8D19B5628A09DC06B87E739AAB3473C63E1E891CEF589.
Never repin after SDK saves. No commit/push or fault clear is authorized.

All commands run from C:/Users/SoftIndVM/Fraktal. Use new labels/output paths
for every run. Retain failed outputs. Do not rerun prepare-canonical or the
recording preflight: preflight.json already exists; use --verify-only.

1. Record the owner's new, exact S3b session approval in authorization.json
   (exclusive creation from the false template); preserve the reply and scope.
   S3a approval is historical. Do not run dependent controller steps without it.
2. Read-only: service Running; port 44818 listener EmulateControlLogix5580;
   scripts/guard_echo.py; EchoControl.exe inspect (Run, !IsFaulted, Remote);
   scripts/preflight.py --verify-only; final_checks.py <new-output>.
   An active HMI login blocks deployment. A fault requires separate approval.
3. Run S3bSession.exe backup through hidden detached run_logged.py. Wait for
   completion and SDK-log audit: require Save / Save As, no SDK errors.
   The SDK calls upload Open Project From Controller. Check backup.sha256
   and equivalent backup export. Never open immutable genealogy original.
4. Run S3bSession.exe deploy-canonical, same durable logging pattern. Audit
   required Download, Change Controller Mode, Save, Save As. Check final Run,
   post-SDK ACD hash separately from original pin; read-back and R6 audit
   canonical_downloaded.L5X. No fault clear is included.
5. Set FRAKTAL_AB_DECLARATION=fraktal_ab_genealogy_demo. Execute:
   python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s3b_fixture_execute.py
     --execute-fixture --expect-serial 601FC87B
     --credential-file C:/work/fraktal_echo38_access_fixture.json
     --output <new-candidate-regressions.json>
   This restores the five documents and runs the existing 31 rows, adding
   read-only decision/held/fault pairs. Never print or archive credentials.
   Run verify_runtime_acceptance.py <candidate-json> --output <new-audit.json>.
   Require four decisions and held/fault coverage at rendition ordinals0/1/2,
   all pairs exactly304 paths/types under the same equal-even scan proof.
   Capture failure is a finding; cleanup must still complete.
6. Read-only: fraktal_ab_s3b_equivalence.py --expect-serial 601FC87B
   --output <new-idle-equivalence.json.gz>; generic canonical capture;
   measure_timing.py <new-output> --candidate. Compare native TASK samples to S3a, keeping
   workload/retry differences explicit. Capacity is already measured:
   991612 used /2154116 available /3145728 total Blocks,31% displayed.
7. Restore after measurement, and after a failed candidate session whenever
   the matching deploy_attempt.json exists: S3bSession.exe restore-genealogy.
   It uses a fresh verified copy of immutable D67561C4...ED4084, never opens
   the original. Audit SDK log and compare exported genealogy_restored.L5X.
8. Run fraktal_ab_genealogy_execute.py with the same fixture arm/serial/
   credential-file and a new output. Require five restored documents,31/31,
   restored policy/logged-out state. Check final Run,not faulted,scanning,
   MANUAL/idle,not restoring,saved documents equal live; inspect/guard again.
9. Seal a new append-only runtime record with original/current candidate
   hashes, backup hash, all successful/failed outputs, actual scan observations,
   Capacity binding and all final checks. Do not edit preparation/prior seals.

Durable SDK launch:
Start-Process C:/Python314/python.exe with arguments run_logged.py, a new
label, the full S3bSession.exe path, mode; use -WindowStyle Hidden.
Only one SDK/controller operation at a time; poll its log and exclusive
<label>_exit.json. Audit before the next dependent operation.

The immutable rollback ACD:
C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD
D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084.
