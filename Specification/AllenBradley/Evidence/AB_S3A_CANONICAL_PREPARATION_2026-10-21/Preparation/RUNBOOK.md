# Proposed guarded S3a session - local Echo 601FC87B

This preparation authorizes no controller changes. The owner selected logical
array views, not a download. Current owner approval for the following exact
session, plus the new candidate Capacity result, is required.

Source: genealogy_s3a_final.L5X
SHA-256: 83443758841A5B5F8D334106079EB8B041F2FF3E3419DB99564108532E361095
Prepared ACD: s3a_canonical.ACD
SHA-256: F1D24CA83A3A452E02402AD7604A373B592909A55AA4858F510111A54A7EE79F
Studio review copy: capacity_review.ACD (initially byte-identical).

Open only the review copy in Studio. Record Used Standard / Available / Total
blocks and fit. Preserve Blocks; do not invent bytes. The prior-stage baseline
is the sealed S2 candidate measurement: 745244 used, 2400484 available, 3145728
total blocks. baseline_capacity.json is hash-bound by baseline_reference.json;
its source is the immutable S2 runtime record. Genealogy's 22% and the S0 probe's
69% are not the S3a incremental baseline. No repeat S2 Capacity report is needed.

The false authorization.template.json and capacity_review.template.json are
proposals. Only after the owner's actual responses, create authorization.json
and capacity_review.json. Do not overwrite proposal files or preflight.json.
No fault clear is authorized; the helper has no such operation.

Every invocation gets a new log/output, preferably in a new runtime UUID
folder. run_logged.py creates logs/exit records with exclusive file creation.
For long SDK calls, a hidden Start-Process wrapper keeps the call independent
of chat steering. Only one controller operation runs at a time.

1. Read-only guard_echo.py and preflight.py --verify-only. Check service,
   EmulateControlLogix5580 listener, identity, Run/not-faulted/Remote, MANUAL,
   idle, logged out, unchanged policy and five saved documents equal live.
2. session/bin/Debug/net8.0/win-x86/S3aSession.exe backup.
   Upload is SDK Open Project From Controller; audit successful Save As.
3. Same helper deploy-canonical. It verifies backup/pin/prepared read-back,
   exact candidate and baseline Capacity, current approval, then guarded
   Program/download/Run. Audit Download, Change Controller Mode and Save As;
   compare canonical_downloaded.L5X to the source and run the access audit.
4. Set FRAKTAL_AB_DECLARATION=fraktal_ab_genealogy_demo. Run
   python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s3a_fixture_execute.py
   --execute-fixture --expect-serial 601FC87B
   --credential-file C:/work/fraktal_echo38_access_fixture.json --output <new>.
   It restores the five documents and runs the existing 31 regressions. Before
   the existing decision answers it adds read-only paired captures: one tower
   case and one NOK case in each ST/SFC/LD rendition, four in total. These add
   no tag command, simulation stimulus or regression row. Require all 31 rows
   plus the active-prompt paired comparisons to pass.
5. Read-only fraktal_ab_s3a_equivalence.py --expect-serial 601FC87B --output
   <new>.json.gz. Require the explicit current 94 paths/types/values and
   same-even entire-scan generation. Generic fraktal_ab_canonical_acquire.py
   --host 127.0.0.1 --slot 0 --expect-serial 601FC87B --output <new>.json
   --capture-output <different-new>.json.gz records native discovery/bytes.
   Run measure_timing.py <new>.json --candidate for native TASK timing.
6. Restore genealogy even after a failed candidate gate, subject to identity,
   fault and session guards. Same helper restore-genealogy opens only a fresh
   verified copy of the immutable genealogy original D67561C4...ED4084.
   Never open or repin that original. When the candidate is readable, verify
   idle/logout and original preflight before rollback. Do not download over
   another active HMI session. A fault clear needs a separate current answer.
7. Run the original fraktal_ab_genealogy_execute.py with the same arm/serial/
   credential arguments and a new output. Restore five documents and run 31
   baseline regressions. Thus the proposed session has 62 regression rows;
   it does not create a model or add new command stimuli.
8. Final read-only final_checks.py <new>.json, guard, preflight --verify-only:
   Run/not faulted/Remote/scanning, MANUAL/idle, logout, not restoring, original
   policy, saved documents equal live; verify original genealogy hash again.
   Audit rollback and compare its export to the pinned genealogy source.

S2's accepted native timing (median LastScanTime 109 us, cumulative MaxScanTime
1177 us, zero overlaps) is the prior-stage observation; compare the S3a result
at its recorded workload. The four extra read-only captures are disclosed.
Native observations are not an isolated controlled cost benchmark.

Seal new runtime evidence including failures. Never archive credentials/native
ACDs. The SDK saves the deployment ACD; retain its original pin and record the
post-save hash rather than repinning or reusing it. S3a's model-count changes
are covered by synthetic reader tests; this proposed runtime fixture does not
append/delete models. Decision.Timeout/SourcePath remain an explicit full-Core
gap. Neither offline preparation nor this session activates shipping V2.
