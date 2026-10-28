# Press S3 exit runtime acceptance passes on Echo; genealogy restored

2026-10-25, America/Mexico_City. The owner approved `press_session_04` with
"approve press S3 exit session". **The press declaration (AUTO in ST, SFC and
LD) passes its complete S3 exit walk on Echo: 47 candidate check rows, 85 paired
captures replayed independently with the idle capture, exact idle equivalence on
4,058 paths, generic acquisition and scan.** Echo ends on genealogy with the
original host documents, 31/31 baseline cases and every final check passing.
Three earlier attempts stopped and are sealed separately; their corrections are
in this image's walk and oracle, never in the PLC image. The authorization is
consumed. No commit or push.

## Target, artifacts and authorization

Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0, Remote keyswitch. The
exact identity, fault and keyswitch guard passed immediately before the start.
The session's 406 source bindings matched before the start and still match.

- Press candidate ACD (pristine): `15E8902551FD6C6D8041727E69D5C2FE917D5BAC0E031D808DB66D8EBFCFD76F`.
- Generated source: `6FD00A4825A2ADFA0BE9E662446905B53461C17CE40A50C1DE02733F530FBB02`.
- Fresh backup: `0E874D1A2D61CFA62ADA5FA2D920450F2E84F8B5B1FA80018D3B947E988B2702`.
- Genealogy original (only hashed; a checked copy was downloaded): `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
- Offline Studio Capacity of this image: **1,669,892 used / 1,475,836 available / 3,145,728 Blocks, 53%**.

The candidate is the press declaration retargeted to Echo with AUTO carried in
all three renditions (the L24ER's ladder-only selection is a subset), the five
S3k canonical choices, and the press I/O catalog bound to a sampled-word source;
see the [S3 exit notes](../AB_CANONICAL_PUBLICATION_S3_EXIT_NOTES_2026-10-25.md).

## Results

| Gate | Result |
|---|---|
| Backup, MANUAL, preflight, Program/download/Run, SDK audits, native read-back, effective access | Pass; final mode Run |
| Press commissioned from an isolated medium seeded with the image's own five documents; restore round trip | Pass |
| Main rows | **23 / 23**: configuration preserved, logged-out refusal, and normal cycle, handled NOK, hold and resume, hold then STOP, hold then mode change, adopted fault, single-reset restart in **each of ST, SFC and LD** |
| Access rows | **2 / 2** |
| Configuration and provider rows | **8 / 8**: page walk and model bank, edit and exact restoration, hidden values, four provider refusals, set store save/list/export/import/load/delete |
| Typed ingress rows | **14 / 14**, full-width Secret/TextValue wipe on every protocol row; both commits in one request: `collision_refused` |
| Paired captures | **85 / 85**: 6 access, 37 configuration, 21 sequence, 3 decision, 12 condition, 6 reset |
| Independent replay from raw native reads, plus idle | **86 / 86** exact values/types, frame slices and generation proofs; 2-31 of 100 polls |
| Idle equivalence | Exact on **4,058** paths, no differences |
| Generic acquisition | **4,058 values, seven modules, nine command arguments, one binding** |
| Walk cleanup | Inputs and policy restored, logged out, Unit idle |

| Native TASK timing, microseconds | Candidate | Restored genealogy |
|---|---:|---:|
| LastScan median, 20 samples | 938 | 99.5 |
| Cumulative MaxScan since task reset | **7,246** | 1,166 |
| Overlap count | **0** | **0** |

Candidate MaxScan stays below the **10,000 us** period. These cumulative
observations span different workloads; they are not isolated copy costs or
physical-controller claims.

## Rollback and final state

Guarded MANUAL normalization, idle/logout guard, genealogy download from the
checked copy, SDK audit and access pass. The exact five original host documents
are restored with record values unchanged; the press walk never touched them.
**31 / 31 baseline cases** and every final check pass: Run, no fault, scanning,
MANUAL, idle, logged out, not restoring, saved equals live, policy restored,
original preflight unchanged. No dumps, fault clears, clock changes, power
operations or hard kills.

## Attempts and corrections

1. [First attempt](AB_PRESS_S3_EXIT_ATTEMPT_2026-10-25.md): the legacy oracle had
   no `MachineState` for a declaration without a signal tower. Corrected in S3h.
2. [Retry](AB_PRESS_S3_EXIT_RETRY_ATTEMPT_2026-10-25.md): the shared host medium
   held genealogy-revision documents, which the press correctly refused. The walk
   now commissions an isolated press medium from the image's own documents.
3. [Third attempt](AB_PRESS_S3_EXIT_THIRD_ATTEMPT_2026-10-25.md): the mode-change
   case waited for `Running`, which the run level keeps; it now waits for the
   applied mode and step 0, as the generated Unit behaves.

Each attempt rolled back to genealogy with 31/31 baseline cases. **2,308 AB
tests**, the root tests and the AB spec, contract, consistency and whitespace
gates pass before and after this session. No HMI change.

## What this accepts and what remains

This accepts the press declaration's S3 publication on Echo in all three AUTO
renditions, with the [path census](../AB_CANONICAL_PUBLICATION_S3_PATH_CENSUS_2026-10-25.json)
already reconciled for genealogy. Physical-module identity and offline I/O proof
on real hardware, the consumer census before S6, and S4-S7 remain. V2 stays
inactive. Persistence medium, per-station gateway posture, S7 hardware and
commit/push policy remain owner decisions.

Work: `C:/work/fraktal-ab-s3-exit-20261025/press_session_04/`.
Payload: [manifest](AB_PRESS_S3_EXIT_RUNTIME_2026-10-25/manifest.json).
