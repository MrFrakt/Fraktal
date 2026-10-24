# S2 canonical candidate — prepared, not authorized

Local Echo 127.0.0.1 slot 0, serial 601FC87B, product 288, v38.11.
Prepared ACD SHA-256:
`2B3F99D936FE742BAA32E888F7F6FF9244DF57B746FECA8B7C47148AAD200973`.
Source SHA-256:
`9398A04EE4ABECF74C006CF0BD2AB516D8EA3AE5607D37041AB8AE0CD0FE725E`.

Use capacity_review.ACD in Studio, preserving s2_canonical.ACD. Also review
genealogy_capacity_review.ACD for the baseline memory delta. Both copies are
bound by hash before review. Preserve the displayed Blocks units and exact
Used Standard / Available / Total values for each copy. Do not infer compiled
fit from source counts or declared bytes. The S0 probe's 69% is not this image.

Only after the owner's current authorization, create authorization.json from
authorization.template.json and capacity_review.json from
capacity_review_with_baseline.template.json, recording the actual response
and both Capacity results. The old proposal capacity_review.template.json is
retained history. The helper refuses deployment without current target/image
authorization and exact-artifact fit, including the baseline Capacity delta.
Fault clear is separately authorized; no clear path exists in the helper.

Preflight is already recorded once in preflight.json. Verify-only calls must
match its documents, policy, mode and logged-out state. Never overwrite it or
weaken an active-session refusal. Every invocation needs a new log and output.

The proposed guarded session, from repository root:

1. Run scripts/guard_echo.py and scripts/preflight.py --verify-only. This
   checks service, listener process, exact identity, fault/keyswitch readiness,
   MANUAL/idle, logged out and five saved documents equal live.
2. S2Session.exe backup: upload a fresh hash-bound backup, export it and audit
   Save As (SDK upload is named Open Project From Controller).
3. S2Session.exe deploy-canonical: verify hashes and prepared read-back,
   record the one-shot attempt, guard Program/download/Run and export.
4. Set FRAKTAL_AB_DECLARATION=fraktal_ab_genealogy_demo and run the authorized
   fraktal_ab_genealogy_execute.py --execute-fixture --expect-serial 601FC87B
   --credential-file C:/work/fraktal_echo38_access_fixture.json --output <new>.
   This restores five documents and runs 31 regressions on the candidate.
5. Run fraktal_ab_s2_equivalence.py --expect-serial 601FC87B --output <new>.json.gz.
   It is read-only: explicit 46-path coverage, generic V6 acquisition, legacy
   oracle, and a bounded equal-even entire-scan generation around all paired
   reads. A failed same-state proof is a failed gate, never a hash-only fallback.
   Also record generic fraktal_ab_canonical_acquire.py outputs and native
   FRK_Press_CanonicalTiming for scan-time evidence.
6. Even if candidate acceptance fails, restore using S2Session.exe
   restore-genealogy. This opens only a new hash-checked copy of immutable
   genealogy_current.ACD (D67561C4…ED4084). No original ACD is opened.
7. Run the same authorized five-document/31-regression harness after rollback,
   with a different output name. Thus this session includes up to 62 rows of
   regression tag writes, on the candidate and restored baseline.
8. Final read-only checks: Run, not faulted, scanning, MANUAL/idle, logged out,
   not restoring, original policy and saved documents equal live. Verify the
   original preflight and original genealogy ACD hash again.

Audit deploy/restore logs for Download, Change Controller Mode and Save As,
and compare exported L5X bodies/initial values. Retain every failed run.
Never archive credentials or native ACDs. Seal dated runtime evidence and
record the two Capacity values and native scan delta before claiming S2 exit.

This candidate adds one canonical Press record and a shape-discovered V6
manifest beside the unchanged V5 oracle. All added data tags/members are
Read Only; one scratch index is None. Legacy mailbox/stimulus surfaces remain
at their existing fixture scope. No direct write-capable canonical client or
HMI change is included. The next S3 surfaces require their own gates.
