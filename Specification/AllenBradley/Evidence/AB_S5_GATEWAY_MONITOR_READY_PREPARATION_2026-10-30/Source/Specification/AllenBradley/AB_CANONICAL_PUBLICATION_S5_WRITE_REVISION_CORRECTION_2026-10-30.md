# S5 configuration write revision — publication correction

Non-normative implementation finding, 2026-10-30. The
[native C6 attempt](Evidence/AB_S5_GATEWAY_WRITE_REVISION_ATTEMPT_2026-10-30.md)
passed C1–C5, then refused the first configuration edit with
`project.mailbox.refused.config_revision_stale`. Genealogy, the five original
documents, 31 baseline cases and final checks were restored successfully.

The HMI sends the descriptor's `WriteRevision` as `IntValue`, as required by
Core §3.10.2 and HMI_CONTRACT's configuration capability contract. The generated
typed ingress validates that argument against the configuration owner's live
`Status.ConfigRev`. Both canonical page and read-only view publishers instead
assigned the old build capability hash. S4b was read-only and did not exercise
this inconsistency. S3k's fixed typed vectors used the live owner revision.

The correction publishes that existing live owner token in `WriteRevision`
whenever typed ingress is enabled. The page, read-only view and ingress then
refer to one owner. The temporary legacy Frame adapter retains its existing
build capability ABI. No new layout, command kind, client translation, retry,
permission exception or stale-write bypass is introduced. This implements the
already approved S3f PLC-owned revisions and S3k typed argument contract; it
does not select a new wire contract.

The independent S3f and read-only-view reference projections use the independently
read configuration-owner revision for this field on typed profiles. The frozen
legacy capture and legacy projection remain unchanged. Prior evidence remains
sealed against the source that produced it.

The new regression executes the real configuration publisher, submits its
published argument to generated typed ingress, changes configuration, and proves
that the previous revision is refused while the new published revision is
accepted. Native acceptance, Capacity and the remaining S5 cases require a fresh
image and preparation; the accepted S4b image's fit/timing cannot be transferred
to this source change. Echo currently holds the restored genealogy baseline.
