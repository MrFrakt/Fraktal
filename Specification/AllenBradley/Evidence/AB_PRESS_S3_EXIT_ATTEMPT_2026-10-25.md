# Press S3 exit attempt - walk stopped at its first capture; genealogy restored

2026-10-25, America/Mexico_City. The owner approved the prepared session with
"approve press S3 exit session". **The press image downloaded and ran, but the
press walk stopped at its first paired capture; no press check row was
recorded.** The rollback completed in full: Echo ends on genealogy with the
original host documents, all 31 baseline cases and every final check passing.
The authorization is consumed. This record accepts nothing for the press
declaration. No commit or push.

## Target, artifacts and the refused first start

Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0. The exact identity,
fault and keyswitch guard passed immediately before each start.

- Press candidate ACD (pristine): `15E8902551FD6C6D8041727E69D5C2FE917D5BAC0E031D808DB66D8EBFCFD76F`.
- Generated source: `6FD00A4825A2ADFA0BE9E662446905B53461C17CE40A50C1DE02733F530FBB02`.
- Fresh backup: `9CCE5387D97A310D75B9787B797DC5061248C4B6513E080B79B9717A26B50268`.
- Genealogy original (only hashed; a checked copy was downloaded): `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.

The first start refused before any controller contact: two status documents
(the plan and the S3 exit notes) had been edited after the session bound 406
sources. No executable source, gate, image or pin had changed. Those two
bindings were re-recorded with their old and new hashes; the refused log and
the original binding list are kept.

## What happened

| Stage | Result |
|---|---|
| Initial guard, MANUAL normalization, preflight (five documents) | Pass |
| Backup upload, SDK audit, baseline access | Pass |
| Program / download / Run, SDK audit | Pass; final mode Run |
| Native read-back of the downloaded image; effective access | Equivalent; pass |
| Candidate guard | Pass |
| Press walk | **Stopped**: first S3e access capture refused before comparing, `projection lacks a stage contract path` |
| Walk cleanup | Its re-login was refused `std.error.accessLoginBusy`; the negative unknown-user login was still hashing |
| Rollback guard, MANUAL, pre-restore idle/logout guard | Pass |
| Genealogy download from the checked copy, SDK audit, access | Pass; final mode Run |
| Exact original host documents restored (5), record values unchanged | Pass |
| 31 genealogy baseline cases | **31 / 31** |
| MANUAL, final checks (scan, MANUAL, idle, logged out, not restoring, saved = live, policy), preflight | Pass |
| Restored baseline timing | LastScan median 99 us, cumulative maximum 1,167 us |

No dumps, fault clears, clock changes, power operations or hard kills.

## Cause and correction

The canonical image always publishes `MachineState`. With a signal tower it is
the tower's value; without one, the PLC classifies it from the Unit and the
alarm log's `Blocking` through `fraktal_ab_machine_state`. The legacy oracle
took `MachineState` only from the tower snapshot, so on the press, which has no
tower, the S3h contract path had no oracle value. The genealogy bench declares
a tower and could not expose this.

`fraktal_ab_s3h_equivalence.extra_values` now derives `MachineState` through
the same classifier when no tower is declared. An offline replay of the S3k
oracle with the press declaration over the accepted genealogy idle capture's
recorded inputs (absent Part/host/tower owners, localization keys translated by
portable name) produced 4,057 of 4,058 contract paths before the fix, missing
only `Press/MachineState`, and all 4,058 after it. That replay is now a repository
test. **2,305 AB tests** and the root, spec, contract, consistency and whitespace
gates pass. The genealogy S3k and press images regenerate byte-identically, so
the press image, its builds and its Capacity are unchanged.

The cleanup's busy-login refusal followed from stopping mid-login; the
genealogy rollback covers it. A retry needs a new current authorization.

Work: `C:/work/fraktal-ab-s3-exit-20261025/press_session_01/`.
Payload: [manifest](AB_PRESS_S3_EXIT_ATTEMPT_2026-10-25/manifest.json).
