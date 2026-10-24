# AB S2 canonical module tree: runtime acceptance, 2026-10-21

S2 passes for its explicit 46-path subset on local Echo serial 601FC87B.
The generic reader discovers seven modules through Symbol/Template objects
and the PLC's V6 manifest, without a runtime station declaration. All paths,
values and types equal the legacy Python oracle under a same-scan proof.
Genealogy is restored; candidate and restored-baseline regressions pass
31/31 each. Shipping Part III/V1 remain active; S3-S7 remain open.

This append-only record supersedes the pending runtime status in
[preparation evidence](AB_S2_CANONICAL_PREPARATION_2026-10-21.md). Raw outputs,
helper sources, generated exports and hashes accompany this report in
[the payload manifest](AB_S2_CANONICAL_RUNTIME_2026-10-21/manifest.json).
No native ACD or credential file is archived.

## Target, authorization and artifacts

Echo: 127.0.0.1 slot 0, Emulate 5580 Controller, product 288, revision 38.11,
serial 601FC87B. Service and EmulateControlLogix5580 listener checks pass.
The owner answered "Approve this guarded S2 session" for the named candidate,
backup, Program/download/Run, document restores, candidate/baseline regression
tag writes, measurement and genealogy rollback. Fault clear was not authorized
and none was performed. No commit or push was made.

Preparation folder:
`C:/work/fraktal-ab-s2-20261021/prepare_3701f795c13b4329891f4eca1346b3a5/`.
Runtime folder:
`C:/work/fraktal-ab-s2-20261021/runtime_ff4a0406689d44478b85ee71f6f94799/`.

- Generated source: 9398A04EE4ABECF74C006CF0BD2AB516D8EA3AE5607D37041AB8AE0CD0FE725E.
- Candidate before download: 2B3F99D936FE742BAA32E888F7F6FF9244DF57B746FECA8B7C47148AAD200973.
- Candidate after SDK saves: 20548C7EE440A44A58BEAAA1D2DDB923327181979937A8F12FEECE0A06224D89.
- Successful fresh backup: 91B47A02C965DC99F03F5C4C90D9612FA6E84547133C3161C1F1D391BF48231C.
- Immutable genealogy original: D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084.

The original genealogy ACD was never opened by the SDK. Recovery and final
rollback each opened a fresh hash-checked copy. The original hash is unchanged.
The candidate's original pin is retained; do not repin or redeploy the saved ACD.

## Capacity and timing

The owner supplied Studio screenshots for the two prepared review copies.
Values are transcribed in capacity_review.json; the screenshot pixels are not
a local payload artifact. The displayed unit is **Blocks**, not inferred bytes.

| Image | Displayed usage | Used Standard | Available | Total blocks |
|---|---:|---:|---:|---:|
| Genealogy baseline | 22% | 720,352 | 2,425,376 | 3,145,728 |
| S2 candidate | 23% | 745,244 | 2,400,484 | 3,145,728 |

S2 adds **24,892 blocks**. Both images fit; the S0 probe's 69% is a different image.

Native GSV TASK observations use 20 read-only samples per record:

| Image/sample window | LastScanTime range, us | Median, us | MaxScanTime, us | Overlaps |
|---|---:|---:|---:|---:|
| Genealogy before session | 98-100 | 99 | 1,167 | 0 |
| S2 after 31 regressions | 109-110 | 109 | 1,177 | 0 |
| Genealogy after rollback and 31 regressions | 99-100 | 99 | 1,167 | 0 |

Observed candidate-minus-restored-baseline median and cumulative maximum are
both **+10 us**. These are native observations after separate downloads and
the same regression workload, not a controlled isolated publication-cost test.
The existing HealthProbe and S2 CanonicalTiming agree on the candidate.

## Acceptance and retained failures

The final backup_03, deploy_01 and restore_01 runs exit 0. SDK audits are
clean: Save As for the upload (SDK name "Open Project From Controller"),
and Download / Change Controller Mode / Save As for deployment and rollback.
Candidate read-back is equivalent for 70 UDTs, seven AOIs, 114 controller tags,
44 executable bodies and 22,379 authored initial values. The R6 top-level and
all twelve canonical type/member access audits pass. Baseline read-back also
matches the pinned genealogy source.

Candidate and restored baseline each report 31 passing rows, restored inputs,
restored policy and logout. Five documents are restored on each image.
Generic acquisition reports 46 nodes and seven modules. Press is a measured
3,064-byte record. The V6 hash is
1E91CB9C99D77AAA228D5C4EABE934914EA983C36BC77662EBE39ED452E91196,
revision 32054457; the V5 oracle remains 6DEC4C1DC2F7F78A.
Equivalence reports comparedPaths=46, typedPaths=46, differences=[],
typeAcceptance=true. Two scan windows changed and were rejected; the third
closes at generation 26834 on both sides. No hash-only fallback was used.
No S2 path requires a D2 correction.

The first upload was interrupted without a backup artifact or exit record;
its audit fails for missing Save As. The retry refuses preflight because
Echo is in Program and no genealogy header is available. Native discovery
then confirms an empty controller. Its cause is **unconfirmed**; the owner's
clarification reply "ok" does not identify a clearing/download operation.
No S2 candidate download had run at that point.

A separate recovery helper uses the already-approved genealogy rollback,
exact identity/fault checks, Program mode and two successful raw empty tag
enumerations. The normal preflight and deploy-attempt guards are unchanged.
Its first empty-state check rejected pylogix's public None result; inspection
shows that wrapper maps a successful empty list to None, so the corrected
guard requires the raw successful list with length zero. The recovery download
succeeds, but post-save launch of bare python fails with Windows access denied.
A helper using C:/Python314/python.exe completes Run/export, followed by
equivalent read-back and clean operation audits. The session helper receives
the same executable-path fix, with zero-warning/error C# builds. All failed
runs and both helper versions are retained.

Recovery re-applies only the already-approved five live documents through the
existing keeper/mailbox, then logs out. It adds **zero regression rows**.
Original preflight equality passes before the successful fresh backup.
There is no fabricated deploy-attempt marker and no fault clear.

The unchanged PLC/reader source matches the sealed preparation: 1,943 AB tests,
74 root tests, clean spec/contracts/strict consistency and both v38 native
compiler/read-back targets at their recorded scope. This session adds runtime
acceptance, rather than repeating unchanged compiler/test work. No HMI change
was made; Flutter gates are inapplicable and no Flutter SDK was selected.
After the status-document updates, the root suite runs again:
`Ran 74 tests in 2.985s` / `OK`; spec/contracts pass, strict consistency
reports zero errors/warnings, and the CR-at-EOL whitespace check passes.

Final read-only checks pass: Run, not faulted, Remote keyswitch, advancing
scan, MANUAL/idle, logged out, not restoring, original policy, and all five
saved documents equal live. The original preflight verifies again. This is
the S2 exit; S3a offline preparation is next, with new Capacity, native scan,
equivalence and current authorization required for its eventual image.
