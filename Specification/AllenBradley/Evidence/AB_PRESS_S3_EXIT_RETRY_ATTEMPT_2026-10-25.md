# Press S3 exit retry - walk stopped at the live-document restore; genealogy restored

2026-10-25, America/Mexico_City. The owner approved the retry with "approve
press S3 exit session", in reply to the retry request for `press_session_02`
after the [first attempt](AB_PRESS_S3_EXIT_ATTEMPT_2026-10-25.md). **The press
image downloaded and ran; the walk passed its first five paired captures and
then stopped at the live-document restore. No machine-core row was recorded.**
The walk's own cleanup restored its inputs and policy. The rollback completed
in full: Echo ends on genealogy with the original host documents, all 31
baseline cases and every final check passing. The authorization is consumed.
This record accepts nothing for the press declaration. No commit or push.

## Target and artifacts

Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0; the exact identity,
fault and keyswitch guard passed immediately before the start.

- Press candidate ACD (pristine): `15E8902551FD6C6D8041727E69D5C2FE917D5BAC0E031D808DB66D8EBFCFD76F` (unchanged).
- Generated source: `6FD00A4825A2ADFA0BE9E662446905B53461C17CE40A50C1DE02733F530FBB02`.
- Fresh backup: `1501580BC87582685EB2E9D5B3AD229F4AA030DC2826CABBCD5CCF551CDA624D`.
- Genealogy original (only hashed): `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.

## What happened

| Stage | Result |
|---|---|
| Initial guard, MANUAL, preflight, backup, SDK audit, baseline access | Pass |
| Program / download / Run, read-back, effective access, candidate guard | Pass; final mode Run |
| S3e paired captures: login busy, unknown-user login refused, authenticated, class policy changed and restored | **5 / 5** pass, with the `MachineState` correction; 2 access rows |
| Live-document restore | **Stopped**: `configuration restore failed: station load refused` |
| Walk cleanup | Inputs restored, policy restored, logged out; Unit idle, no error |
| Rollback guard, MANUAL, idle/logout guard, genealogy download, SDK audit, access | Pass |
| Exact original host documents restored (5), record values unchanged | Pass |
| 31 genealogy baseline cases | **31 / 31** |
| MANUAL, final checks, preflight | Pass; LastScan median 99 us, cumulative maximum 1,166 us |

No dumps, fault clears, clock changes, power operations or hard kills.

## Cause and correction

The host's live-document medium is keyed by serial and root name, both shared
by the genealogy bench (`601FC87B-Press`). Its documents carry the genealogy
configuration revision. A station accepts a document only at its own revision
or a declared predecessor, so the press PLC correctly refused another station's
documents. The press and genealogy configuration Records are identical; the
revision differs because the declarations differ.

The press walk now commissions the press as a new station on this host: it uses
an isolated, initially empty medium beside its output (through the existing
`FRAKTAL_AB_CONFIG_SET_DIR` override), seeds it with the documents the
downloaded press image implies at the press revision, and then runs the
ordinary restore round trip. The genealogy medium is never read or written by
the walk. Tests cover the seeding, its refusal of a used or unselected medium,
and the routing in `main`. **2,308 AB tests** and the root gates pass; the image
is unchanged. A retry needs a new current authorization.

Work: `C:/work/fraktal-ab-s3-exit-20261025/press_session_02/`.
Payload: [manifest](AB_PRESS_S3_EXIT_RETRY_ATTEMPT_2026-10-25/manifest.json).
