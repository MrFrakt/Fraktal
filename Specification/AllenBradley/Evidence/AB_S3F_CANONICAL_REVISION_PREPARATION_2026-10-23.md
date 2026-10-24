# S3f revision follow-up — offline preparation

Date: 2026-10-23, America/Mexico_City. Append-only. Work directory:
`C:/work/fraktal-ab-s3f-revision-20261023/prepare_c66f76a368304f6981b436dbf651e009/`.
The same-named payload folder's manifest binds this report and all artifacts.

**Offline gates pass. No follow-up controller operation ran.** The previous
S3f session remains accepted only at its recorded scope; its approval is
consumed. Retained restart and active-model native revision checks remain open.
The owner-approved S3f contract already requires these semantics; the fix below
adds no contract exception. Nothing is committed or pushed. V2 is inactive.

The offline retained-state check reproduced an exact revision collision:
old token **10,000,000**, new boot seed **9,999,999**, resulting token
**10,000,000**. The first-scan branch selected a seed unequal to the old token,
but the normal changed-data increment immediately incremented it back. The
fix sets Initialized=0 inside the first-scan initialization path. The ordinary
increment is skipped for that scan, leaving the already checked different seed.
Lower/equal/zero/wrap retained-seed tests pass. The original reproductions,
including the first unbound diagnostic and subsequent source-hash-bound result,
remain archived. There was no native collision injection or clock write.

| Artifact | SHA-256 |
|---|---|
| Generated source | `B71E30ABBE8221AAA39A0DF8EEB934897FE0A4B0711047EFDC7D653A20AE7CF3` |
| Prepared ACD and unchanged review copy | `BD030AEB01D58469D452D877A9CFF2868B79DE45055A3795D1D1479BB2771183` |
| Immutable genealogy original, hash checked only | `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084` |

Comparison against the first S3f source proves **one added initialization
assignment in one ST body and one additional ST line**. Every layout, initial,
other executable body and the SFC graph remains identical. The initial local
delta audit incorrectly required an identical Program inventory, which includes
ST line counts; a second audit initially compared a spaced statement with
whitespace-normalized code. Both failed outputs remain. The corrected audit
accounts for exactly the one line and verifies all remaining structure/code/
initials unchanged. This does not weaken native build/read-back comparison.

Both v38 EchoController/PhysicalController imports/builds/read-backs and the
reopened/rebuilt ACD pass cleanly: **124 UDTs, seven AOIs, 138 tags, one
program/task, 52 executable bodies, 21 SFC steps, 353 descriptions and 37,556
authored initial values**, no native differences. SDK log audits require
successful operations and zero import warnings/errors. Source, both exports
and prepared export pass the same whole-tag/member access allow-list. No public
layout/access or generic reader changed. Native ACDs are excluded from payloads.

Closing gates include **Ran 2111 tests in 258.484s / OK** by AB tools discovery,
**Ran 74 tests in 1.919s / OK** at root, focused model/fixture/retained-snapshot
tests, specification/contracts, strict consistency and whitespace. Six prior
stage images/replays remain identical. Fresh regeneration matches the exact
compiled source. **142 sources** and their local Python import closure are bound.
**20 predecessor seals / 4,032 artifacts** verify unchanged. Two failed local
delta-audit runs remain; no native compiler/test/Capacity gate failed. HMI/
Flutter is not applicable; no HMI code change was made.

Qualified automatic Studio Capacity passes at **73%: 2,298,448 used /
847,280 available / 3,145,728 total Blocks**, **+36** over the first S3f image.
Two stable UI samples, source preservation and process closure pass. Blocks
are not assumed bytes; this is the offline estimate. No feature or validation
was cut. The image is held out of forecasting calibration pending native
acceptance. No new native scan-time or payload-size result is claimed here.

The prepared follow-up adds one fixed active-model case to the full S3f
fixture. It runs two simulated CHANGEOVER chains through the existing tooling
confirmation, proves active ModelCode/revision change, and restores the exact
original active model, all live recipe values, banks, public fixture inputs and
mode. Private ModelRequest is never written. Failure-path tests prove that a
failed observation cannot block cleanup or re-enter observations. Existing
public SET_MODEL owns its private requested-model state normally.

The new helper's one-shot restart-canonical command requires the completed
exact deployment and MANUAL/idle/logout/not-restoring. It changes Program then
Run **without downloading**. Read-only snapshots require records, banks,
catalogue, active model, policy and page content unchanged, root/page revision
equal and a different valid retained token. Both additional authorization flags
are false, along with the prior fixture/session flags; authorization.json and
all backup/deployment/restart markers are absent. A fault clear or clock set
remains outside scope. No completed-session authorization is reused.

The concrete proposed session includes fresh backup, guarded deploy, five-doc
restore, **42 candidate fixture rows plus one retained restart check**, native
equivalence/sizes/scan, hash-checked genealogy-copy rollback, five-doc restore
and **31 baseline rows**, MANUAL cleanup and final checks: **74 planned checks**.
Per-tag writes are unmeasured. The prior scan proof and 100-attempt/five-second
budget remain unchanged. Fresh read-only guards/preflight/final checks see
genealogy Run/not faulted/Remote/scanning, MANUAL=1/idle/logout, five documents
equal live, original policy/preflight and immutable genealogy hash unchanged.

Exact commands and recovery are in `Preparation/RUNBOOK.md`. The native
retained/model checks and both new-image regression matrices remain pending.
Actual credential files and native ACD files are excluded from the seal. Ask
for current authorization before the added controller operations. S3g remains
behind S3f's outstanding native exit gates.
