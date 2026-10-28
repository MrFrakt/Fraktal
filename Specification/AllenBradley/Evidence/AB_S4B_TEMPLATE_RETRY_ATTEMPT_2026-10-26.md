# S4b Template retry attempt — 2026-10-26

**Template discovery passed; qualification failed at the first root-sample
check, before candidate writes. Genealogy rollback is verified.** S4b native,
row-coherence, active-workload, performance and desktop acceptance remain open.

The owner answered “Approve guarded S4b Template retry” to
`call_378e7db52cb749e49ad59c696606376a:0`, authorizing the
[sealed retry](AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26.md).
This exact-image session completed with rollback; its approval is consumed.

## Passed

- Fresh service/listener, serial and identity checks: local Echo 601FC87B,
  1756-L81E v38.011, 127.0.0.1 slot 0; Run/Remote, not faulted. Initial
  MANUAL/idle, logged out and five saved/live document equality pass.
- Fresh preflight, backup, Save As audit and baseline access audit pass.
- ACD `7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF`
  downloaded and returned to Run. Source
  `C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F`.
  SDK log, exported L5X read-back and external-access audits pass. The SDK
  changed its working ACD through Save; the pinned original remains intact.
- Corrected Dart Template discovery and manifest/publication discovery reached
  the first snapshot. The previous unterminated-name failure did not recur.
- Pinned genealogy was restored from a hash-checked copy; its original remains
  `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
  Restore SDK/access audits, exact original host-document restoration,
  **31/31 baseline regressions**, MANUAL cleanup, final checks and preflight pass.
- Final state: Run, not faulted, scanning, MANUAL/idle, logged out, not restoring,
  policy restored, five saved/live documents equal. No dumps, fault clears,
  clock changes, power/vendor-state operations or Echo hard kills.

## Failed and skipped

The observer reported **`FormatException: Fresh canonical root sample is
unavailable.`** at the first snapshot, before its readiness marker and before
any candidate fixture writes. The qualification condition checks root presence,
root Status/Name and sample age together. It did not preserve that refused
snapshot, so this record cannot distinguish the specific failing condition or
claim an exact cause. The guard was retained and the runner rolled back.

There are zero complete qualification samples, zero configuration pages and
**0/41 candidate cases**. Candidate all-path equivalence, generic acquisition,
native candidate scan and desktop rendering were not reached. The separate
approved rollback normalization and baseline writes ran as recorded.

All 743 runtime source bindings remain unchanged except the SDK-saved working
ACD. Offline 2,336 AB /74 root /635 Flutter tests (12 skipped), both v38 builds,
Windows build and exact-image **65% Capacity** remain preparation results.

## Next

Preserve the rejected snapshot and root quality/age/reason diagnostics in the
read-only qualification tool, and reproduce any scheduling/quality issue with
recorded bytes and a controlled clock before changing production logic. The
current error is insufficient to justify changing freshness, coherence or retry
limits. A fresh controller-changing session needs current authorization under
AGENTS.md §3a. S4-S7 and S3 physical I/O proof remain open. V2/Part III stay
inactive. Nothing is committed or pushed; no credentials or ACD binaries are
archived.
