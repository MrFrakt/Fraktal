# S3j retry preparation - explicit root-reference declaration

Client date: 2026-10-25, America/Mexico_City. The
[first native attempt](AB_S3J_CANONICAL_ATTEMPT_2026-10-25.md) stopped at its
first unequal condition capture and completed verified genealogy rollback.
**The reference defect is corrected offline and a fresh guarded retry is
prepared. Native acceptance remains open; current authorization is false.**
The previous session approval is consumed. No commit or push; V2 inactive.

## Correction and unchanged image

`projection.unit_status` now accepts an optional explicit declaration. The
shared acceptance oracle supplies its candidate declaration, as it already
does for child status. Existing standalone callers retain their selected
station default. No process-global declaration is replaced during a read.

The regression reproduces the saved adopted fault (ErrorSource=3,
DiagReason=10101, DiagIoRoles=2) with an unrelated global declaration that has
no I/O catalog. The shared oracle must return `_101B301A` and `Local:1:I.0`
from the candidate catalog and leave that global untouched. This restores
the reference's existing I/O join contract. No PLC behavior, path/type/value
contract, comparison tolerance or write vector changes.

All **41 saved native captures** replay with the corrected reference and
exactly equal the independently decoded PLC values and types. The original
40-pass/one-failure result remains sealed. The corrected replay also verifies
the original recorded comparisons; only the two documented reference values
in condition capture 2 change. Raw fragments, legacy inputs, configuration
provider context and generation proofs are re-decoded. Proofs use 2-30 polls,
within the unchanged 100-poll/five-second bound.

PLC regeneration is byte-identical:

- Source L5X SHA-256:
  `2F0B2CE73C2ECB69B1DD7F32BB1AE1D66550811A0EF49C1D65E9AE2C7A753EEA`.
- Pristine retry ACD SHA-256:
  `285BF972C5FD781C315F670CFEEED8AC01D566791DB84E4B17125CC9B8CC3212`.
- V6.5 ContentHash:
  `5CB700B26E0F3C48AE65FB06CB30E8BC62BDF536A0B710FBE898C9E8577C1231`.

The fresh workspace copies the pristine review ACD, never the deployment
file that SDK Save changed. Hash-bound JSON and L5X inputs are copied as
bytes. Only workspace paths and current gate-log labels change in the
session apparatus. The C# helper is byte-identical after normalizing its
workspace path. It still exposes only backup, deploy-canonical and
restore-genealogy. No existing preflight, backup or deployment record is
reused. The original workspace and evidence remain untouched.

## Gates

| Gate | Result / output |
|---|---|
| Full AB discovery | **2,249 tests, OK**, 333.778 s; Offline/ab_suite_01.log |
| Root gate tests | **74 tests, OK**; Offline/root_tests_01.log |
| AB spec / contracts / strict consistency | Pass; Offline/ab_spec_01.log, ab_contracts_01.log, consistency_01.log |
| Whitespace | Clean; Offline/whitespace_01.log |
| Captured fault regression | Pass through the shared oracle; candidate catalog independent of global APP |
| Independent corrected replay | **41 / 41 exact**, including the formerly unequal capture; no controller access |
| Regeneration | Byte-identical source and unchanged pristine ACD pins |
| Both v38 targets / strict read-back / effective access | Reuse the unchanged source/image evidence in the original preparation: 0 warnings / 0 errors, Equivalent=true, 60 bodies / 42,043 initial values, access audits pass. Compiles are not rerun for this host-reference-only fix |
| Prior generic-reader replay | 1,245 captures remain bound by unchanged reader and publisher sources; not rerun for the reference change |
| Exact-image automatic Studio Capacity | Unchanged **1,743,080 used / 1,402,648 available / 3,145,728 total Blocks**, 55% displayed; original measurement hash-bound |
| Fresh helper build | Success, **0 warnings / 0 errors**; Preparation/session_build_01.log |
| Negative authorization | **4 / 4**, before SDK/controller access; Preparation/authorization_negative_01.json |
| Offline download-gate replica | All file/Capacity/read-back/pin comparisons pass |
| Read-only guard and baseline probe | Expected service/listener/serial/firmware/Remote/Run, no fault; MANUAL/idle/logged out and five saved/live documents equal |
| Fresh retry download / remaining native cases / I/O / scan | Not run; new current authorization required |
| HMI / physical / CIP Security | No HMI change; Flutter not applicable. Physical/security acceptance remains open |

The AB suite's raw log preserves argument-refusal probes and ResourceWarning
diagnostics; its final unittest result is OK. These are not compiler warnings.
The previous R1/R2 cumulative TASK maximum was 9,829 us against 10,000 us.
S3j's candidate timing gate remains unmeasured and may not be inferred from
memory fit or saved-capture replay.

## Proposed retry - same bounded native scope

Target: local Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0.

1. Fresh current service/listener/identity/fault/keyswitch/no-driver/dump
   guards, MANUAL normalization if needed, new preflight and fresh backup.
2. Guarded Program/download/Run of the unchanged 285B... image; SDK,
   strict read-back and effective-access audits.
3. Five-document restore and all **41 candidate cases**, with independent
   read-only paired captures using the corrected reference declaration.
4. **Nine fixed simulated-word vectors**, exactly **80 DINT writes** including
   original-word restoration, only under `FRK_Press_SimIo`. Operational,
   channel fault, inhibited, offline, input-only, output-only, fault unknown,
   signed-word and ineffective unregistered-gate cases; ten captures including
   restoration. The independent 4,000-byte observer remains.
5. Read-only all-path equivalence, generic acquisition, native sizes and
   twenty TASK samples; independent packet/reference replays.
6. Hash-checked genealogy rollback copy, five-document restore,
   **31 baseline regressions**, MANUAL cleanup and final/preflight/scan checks.

The first failed candidate stage enters the inherited rollback path.
Active-login and identity guards remain. Fault clears, clock changes,
firmware/network changes, power operations, hard kills and vendor-state edits
remain excluded. No gateway write posture changes. Current confirmation is
needed for this new session under AGENTS.md section 3a.

Offline: `C:/work/fraktal-ab-s3j-20261024/retry_01/`.
Session: `C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c/`.
Append-only payload: [manifest](AB_S3J_CANONICAL_RETRY_PREPARATION_2026-10-25/manifest.json).
No credential file or ACD binary is archived. Owner Siemens archive changes
remain untouched. After native S3j acceptance: S3k mailbox/reports, production
fields and Features, then press renditions and S4-S7. The migration observation
frame is not the shipping S4 coherence model.
