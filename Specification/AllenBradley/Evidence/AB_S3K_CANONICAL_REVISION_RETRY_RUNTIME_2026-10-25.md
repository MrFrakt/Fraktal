# S3k revision retry: typed login failed; genealogy restored

2026-10-25, America/Mexico_City. The owner approved the
[sealed revision retry](AB_S3K_CANONICAL_REVISION_RETRY_PREPARATION_2026-10-25.md)
with “Approve guarded S3k revision retry”. **Native S3k acceptance fails at
typed login. Genealogy, its original host documents, all 31 baseline cases
and final checks are restored.** No commit or push.

## Authorized deployment and partial request proof

Target: Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0, Remote
keyswitch. Current service/listener/identity/no-fault checks, source and all
549 preparation artifacts passed before use. Fresh backup SHA-256:
`5F8532A518E905D8C5F8DFF8B5A2C05275C3483DCC70BEDC7F07F78D6274AB7F`.

- Pristine downloaded ACD: `12211B815C81C6D67AFB9ABF13137E1FC21E7FC375A7D11F6FD828A4645995D9`.
- Generated source: `D7CB30284ECCA051DAB32FDF76421B44676C75FD917F6AA5B8FB1E52BD15A494`.
- Canonical V6.6 ContentHash: `C3501F2A7CFD6D33D3C221669BE3AE9862A96ED58002216E1D836F5BFB94DECC`.
- Genealogy original: `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.

SDK backup, Program/download/Run, log audit, native read-back and effective
access pass. SDK Save changes the disposable candidate ACD; the pristine pin
above remains the authorization identity. The original genealogy ACD is only
hashed; SDK rollback opens a hash-checked disposable copy.

| Request scope | Observed result |
|---|---|
| Five-document restore | Pass; the prior-publication compatibility correction works natively |
| Access cases | **2 / 2** pass |
| Configuration/provider cases | **8 / 8** pass, including exact edit restoration and isolated set medium cleanup |
| Typed protocol rows | **12** ACK/refusal/wipe rows recorded: queries, stale/mismatched payload, stale revision, wrong root/key/fraction, real edit/restoration, logout and login consumption |
| Typed login completion | **Fails after 15 seconds: `typed login timed out: step=0, error=0`** |
| Legacy-after-typed / dual-ingress collision | Not reached |
| Inherited main regression rows | Not reached; **0 / 31**. The inherited fixture inserts configuration/typed vectors inside its initial restore step, before the main exercise |
| Post-case generic acquisition / idle equivalence / TASK scan | Skipped at the first candidate failure |
| Candidate cleanup | Inputs/policy/configuration values restored, fallback legacy login used as needed, final logout; rollback MANUAL normalization passes |

The `login_accepted` row establishes consumption/ACK and full-width wiping;
it does **not** establish successful authentication. The following completion
wait failed. All 12 recorded typed rows verify full-width transport Secret and
TextValue wiping and that the legacy ACK stayed independent. Collision/no-replay
acceptance remains unmeasured.

## Independent capture replay and measured sizes

**39 / 39** paired captures replay independently: six Access and 33
configuration pairs. Native raw reads regenerate reference inputs and exact
value/type projections; native fragment packets regenerate frame bytes and
every sampled slice. They contain **3,820–4,220 typed paths** as logical page
extents change. Four sockets keep one outstanding request each. Proof acquisition
takes **2–27 / 100 polls** under the unchanged five-second limit.

Native Templates/fragment plans give root **147,784 bytes** and migration frame
**230,368 bytes**. Offline exact-image Capacity remains **1,903,308 used /
1,242,420 available / 3,145,728 total Blocks** (60%). Candidate TASK measurement
was skipped after failure; no previous-image scan result is transferred.

## Rollback completion and host-medium correction

Pinned-copy genealogy download/Run, SDK audit and access checks pass. The first
baseline fixture then fails at document restore: the successful S3k restore/
edit walk had saved all five host documents at revision **14896938**; the older
genealogy image accepts revision **7203916**. Configuration row values are
exactly equal to this session's original preflight documents.

Within the same approved rollback, the helper verifies exact baseline identity,
no fault, idle/logout and restoring state, preserves the post-candidate index
and five files, then restores the **exact five original preflight documents**
through FileMedium's checked atomic writer. No revisions are invented and no
controller write occurs in that host step. Original files, hashes and before/
after revisions are retained. The baseline fixture is then run again under the
same unfinished cleanup authorization; there is no additional download.

**31 / 31 baseline cases and every final check pass:** Run, no fault, Remote,
scanning, MANUAL=1, idle, logged out, not restoring, restored policy, five saved/
live documents equal and the original preflight unchanged. Native baseline
timing is retained in `Runtime/baseline_timing.json`. No dumps, fault clears,
clock changes, power operations, vendor-state edits or hard kills occurred.
The initial failed rollback record stays immutable; `rollback_completion_01.json`
records its successful completion. Current authorization is consumed.

## Diagnosed login defect and next work

An offline causal reproduction uses a synthetic test account and executes the
generated access owner. Login copies `HmiRequest.Sequence`, the legacy commit,
into its private LoginRequest and compares it with HmiLastSequence, which now
holds the independent typed owner token. Different tokens mark a correct PIN
invalid before hashing; matching tokens succeed. This reproduces the native
failure without real credentials or controller access.

Next: bind the private login snapshot to the shared committed-sequence helper,
preserving independent external commits/ACKs; add coupled ingress/access-owner
regressions; compile/read back both targets and measure the corrected image.
Future rollback preparation must restore original host documents before the
old baseline fixture. Then prepare a separately authorized exact-image retry.
All request vectors, the 15-second bound and validation remain intact.

The exact native sources are frozen before correction. Their existing **2,292
AB / 74 root tests**, both v38 builds/access/read-back and Capacity are bound
by unchanged source/image hashes; the new causal reproduction and 39-pair
replay supplement them. Native failure remains a failure despite those gates.
V2 is inactive; press ST/SFC/LD/real-I/O proof and S4–S7 remain. HMI unchanged;
Flutter gates are not applicable. Owner Siemens archive edits are untouched.

Work: `C:/work/fraktal-ab-s3k-20261025/retry_revision_01/`.
Payload: [manifest](AB_S3K_CANONICAL_REVISION_RETRY_RUNTIME_2026-10-25/manifest.json).
No credential file, PIN or ACD/BAK binary is archived. Failed runs are retained;
the 60 preceding seals are verified unchanged.
