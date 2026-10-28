# S3k request attempt stopped at document restore; genealogy restored

Client date: 2026-10-25, America/Mexico_City. The owner explicitly instructed
"please continue, run request cases **then restore genealogy**". This
authorized the prepared request walk on the already-downloaded S3k image,
followed by genealogy rollback, five-document restore, 31 baseline cases and
final checks. Fault clears, clock changes, power operations and vendor-state
edits remained excluded. **Genealogy rollback and every baseline/final check
pass. S3k native acceptance fails and remains open.** No commit or push.

## Exact image and earlier download

Echo: **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0, Remote keyswitch,
controller GUID `91dec7d6-8ac3-45c9-ab2e-0d039c7006fd`. Service and the
`EmulateControlLogix5580` listener, exact identity and no-fault guard pass.

The earlier download-only instruction is recorded unchanged in
`Download/authorization.json`; its scope excluded request writes and rollback.
That download completed before the current instruction:

- Downloaded S3k ACD: `5B62CAC28C8EB5A819850D49FC854123C0B0B00449E2E8663FAC08B96C3000F6`.
- Generated PLC source: `426289A5E71CDEC1DBC5A4C5C7FBCDE4E706676B311362A12A91CFD36083EE78`.
- Canonical V6.6 ContentHash: `C3501F2A7CFD6D33D3C221669BE3AE9862A96ED58002216E1D836F5BFB94DECC`.
- Legacy S3k manifest: `E34F2AA88FEA0175`, configuration revision **14896938**.
- Fresh pre-download backup: `59516E7601DCE49DDB4297917CE4C6BFA51149F92C1D94DB5F93511C0F4EC3BC`.
- Pinned genealogy original: `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.

The original genealogy ACD was never opened by the SDK. Rollback opened a
hash-checked copy; SDK Save changed that disposable copy, as expected.

Initial SDK download, read-back and access audits passed. The first generic
acquisition failed with `KeyError: handle` because a V6.6 scalar commit Symbol
has no structure handle. The client manifest-discovery fix retained its
shape/magic validation and the second acquisition passed: **4,220 values,
seven modules, nine command arguments and one binding**. The first idle
equivalence invocation omitted the oracle declaration; the correctly selected
invocation passes. Both failed runs remain archived. Live Template discovery
measured **784 payload bytes** and attribute-1 structure handle **41413**;
no command input record was acquired or persisted by generic acquisition.

## Request attempt and failure

Fresh checks before the current attempt confirmed that exact image, an idle
Unit and no active operator session. The restore-only helper builds at 0
warnings/errors and preserves target, fault, image/hash and active-session
guards. The original download-only approval was not overwritten.

| Step | Result |
|---|---|
| Initial request invocation | Refused before any write: the inherited guard selected genealogy's manifest instead of S3k's |
| Harness correction | S3k selects its declaration for every imported helper; shared genealogy main accepts an exact expected-declaration argument whose default remains genealogy. Identity, validity, capacity and hash checks remain intact |
| Write-surface comparison | Identical ten inherited writable fixture tags; no tag added or removed |
| Regenerated PLC source after harness correction | Byte-identical to the downloaded source pin above |
| Full AB suite after correction | **2,287 tests**, OK; `ab_suite_request_cases_02.log` |
| Root tests / spec / contracts / strict consistency | **74 tests**, OK; all gates clean |
| Correctly selected request walk | Two Access cases pass: unknown-user login refusal and a class read-level edit/restoration |
| Paired captures | **5 / 5** Access captures independently replay: raw fragments, frame slices, native inputs, values/types and reference agree; 4-27 of 100 polls, four reader sockets |
| Five-document restoration | **Fails: `configuration restore failed: station load refused`** |
| Inherited 31 regression rows / eight configuration cases | Not reached; zero main regression rows |
| Typed vectors / one-packet write proof / live secret wipe / collision observation | **Not run**; the fixture stopped at the restore failure |
| Candidate cleanup | Simulation inputs, policy and session restored; Unit idle/unlatched and logged out. Candidate live documents were still restoring |
| Post-request idle acquisition/equivalence and timing | Skipped after the first request failure |

The initial pre-write mismatch was corrected under the same current scope;
it consumed no controller-changing action. After the actual document failure
the candidate walk was not repeated. The five captured Access pairs and all
failed invocation logs are preserved.

## Rollback and final state

The first rollback-readiness helper incorrectly required an unaccepted
candidate's live-document restore to have completed. It refused without a
write. The rollback-specific helper records that restoring state instead;
the stable-baseline deployment preflight is unchanged. Exact candidate/serial,
no-fault, MANUAL/idle and no-active-session checks remain required, including
a fresh check after SDK open immediately before Program mode.

| Gate | Result |
|---|---|
| Candidate MANUAL normalization | Guarded LOGIN, SET_MODE(1), LOGOUT; idle and level 0; `restoringBeforeRollback=true` recorded |
| Program / pinned-copy genealogy download / Run | Pass; SDK Open project, Download, Save and Save As audit clean |
| Genealogy effective access and exact baseline guard | Pass |
| Five-document restore and baseline regressions | **31 / 31** pass |
| Final mode / fault / scan | **Run, no fault, scanning** |
| Final application/session state | **MANUAL, idle, logged out, not restoring, policy restored** |
| Saved/live documents | **5 / 5 equal**, including exact preflight comparison |
| Controller dumps | None before or after |
| Fault clears / clock changes / power operations / hard kills | **0 / 0 / 0 / 0** |

Current authorization is consumed. Genealogy remains loaded; another S3k
download and request session need new current exact-image authorization.

## Memory, timing and diagnosed blocker

Exact-image offline Studio Capacity remains **1,907,592 used / 1,238,136
available / 3,145,728 total Blocks**, 60% displayed. The harness fixes did not
change PLC source or that image. Before the failed request walk, twenty
candidate samples measured LastScan **945 us median**, maximum 1,007 us,
cumulative MaxScan **7,607 us**, zero overlaps under the 10,000 us period.
This is an idle measurement, not an active request-workload acceptance result.
Baseline timing and its exact outputs are archived separately.

Offline reproduction finds every saved document header and record at revision
**7203916** (the prior `6DEC4C1DC2F7F78A` publication). The generated S3k
`revision_rejected` predicate rejects all five documents. The candidate and
baseline configuration Record declarations compare exactly equal, and deriving
the candidate at the prior publication stage reproduces the precise prior
manifest. S3k's versioned release owner/localization changed publication identity
without changing those configuration schemas. The keeper continues after model/
line refusals and reports the final station refusal; that explains the observed
error. The reproduction is archived; no document or revision was rewritten.

Next: recognize the exact prior publication revision in the existing shared
configuration validator, retaining schema, identity, type, range, permission
and transaction checks. Validate offline, compile/read back both v38 targets,
measure the corrected image and prepare a separately authorized native retry.
The ten typed dry-run vectors remain offline evidence only.

S3 final press ST/SFC/LD and real-module identity/offline proof, S4 desktop,
S5 gateway/installer, S6 retirement/persistence/event ownership and S7 physical/
CIP Security remain. V2 remains inactive. No HMI change; Flutter is not applicable.

Work: `C:/work/fraktal-ab-s3k-20261025/download_01/`.
Payload: [manifest](AB_S3K_CANONICAL_ATTEMPT_2026-10-25/manifest.json).
All prior sealed records and the owner's Siemens archive edits are untouched.
No credential file or ACD/BAK binary is archived.
