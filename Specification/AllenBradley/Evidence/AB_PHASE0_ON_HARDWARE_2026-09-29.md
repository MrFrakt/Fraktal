# Fraktal/AB — Phase 0 on the bench: compiled, downloaded, re-proved

**Result:** Phase 0 of the AB/TC3 parity plan
([`Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md`](../../Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md))
**compiled, was downloaded, and re-passed §146 parity 17 of 17** in all three
renditions. Everything Phase 0 changed in control flow was observed on the
controller, not only in generated ST.

**Date:** 2026-09-29 · **Repository revision:** `28b2366`
**Raw record:** [`AB_PHASE0_ON_HARDWARE_2026-09-29.json`](AB_PHASE0_ON_HARDWARE_2026-09-29.json)

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510` |
| Loaded build | `press28.L5X`: `ContentHash 4D11673BCE65B2F2`, manifest schema **major 2** |
| Declaration | the same hash, so the controller matches the repository |

## 1. D3 is closed, by the path that was available

The Logix Designer SDK probe on the bench workstation refused every import in
this session with `OperationFailedException: No valid license`. press26 failed
the same way, and it had already been imported and downloaded successfully, so
the refusal was the licence and not any build. So the offline compile gate could
not run from here.

The owner imported press28 in Studio 5000 v33 on the licensed desktop and
downloaded it, and the controller now reports its hash. That is the real
compiler accepting every construct this generator emitted for the first time:

- an **array-of-UDT controller tag**, `FRK_Press_ModelCfg[3]`, with decorated
  element data;
- an **expression subscript**, `FRK_Press_ModelCfg[FRK_Press_Unit.CommitModel - 1]`,
  in the routine and in the mailbox;
- the **library AOI** `FRK_M_Cylinder`, called by three instances, reading its
  task period from the instance context;
- the module context type **`FRK_T_ModuleCtx`**, named for no application.

## 2. §146 parity, re-run because Phase 0 changed control flow

Phase 0 moved the changeover commit out of the chain and into the routine, and
moved module timing from a literal into the instance context. The morning's
17/17 therefore did not transfer, and Part III said so. Re-run:

| | ST | SFC | LD |
|---|---|---|---|
| Cycle completes, `OrderFail` 0 | 1337.2 ms | 1139.2 ms | 1319.7 ms |
| HELD at step 180 → self-resumed to 200 | ✓ | ✓ | ✓ |
| Held reason / severity / error while held | 6130 / LOW / 0 | same | same |
| Abort stands down to step 0, Running 0, Error 0 | 3.0 ms | 2.0 ms | 3.1 ms |

Trace and visited step set match ST for SFC and LD. **17 of 17.** The mailbox
sequence seed was 12, so the harness began above what the controller had
already answered.

**The cycles are about 400 ms longer than this morning's run, and that is
correct.** M-200's dwell (600) plus settle (300) exceeds M-100's (300 + 200) by
exactly 400 ms, and the press was running M-200 (§3).

## 3. The Phase 0 behaviour the parity pass does not reach

The parity pass drives AUTO. Changeover and restore are outside it, so they
were read off the controller directly. Reads only; nothing was written.

| Behaviour | Observed |
|---|---|
| Per-instance task period (the library) | `Par_TaskPeriodMs` = 10 in `PressRam`'s context: the AOI reads the period the instance carries |
| Per-model §3.8a restore, never-written path | all three `ModelCfg` elements at `SchemaVersion 1`, each holding its model's declared values |
| Changeover commit, now performed by the routine | `ModelOrdinal` 2 (M-200); running `ParCfg` = `TransferSettleMs 300`, `PressDwellMs 600`, identical to `ModelCfg[1]` |

The last row is conclusive rather than suggestive. `ParCfg` boots at the default
model's values, M-100's 200 / 300, so M-200's numbers are there only because a
commit ran. press28's changeover step contains no literal model values, and
that was checked in the generated file. The only way those numbers reached
`ParCfg` is the routine copying `ModelCfg[CommitModel - 1]`.

## 4. Not observed on hardware, and why

- **Editing another model's stored value** (`WRITE_CONFIG` with a model in
  `DurationMs`). `ModelCfg[1]` still holds its declared values, so no
  such edit has happened yet. It needs the owner's browser test.
- **The rejected-image path of the restore** (D1's `ELSIF`). It needs an
  element with an unrecognized, non-zero version. The records are
  `ExternalAccess="Read Only"`, so no permitted path can put one there. It is
  covered by generated-ST tests and a mutation check.
- **`ACK_CONFIG_RESTORE`** (D2). It needs `RestoreLost = 1`, which follows from
  the item above.
- **The ENGINEER check on that acknowledgement.** This binding holds no session
  level until per-user access lands (audit Q1). That is recorded, not missed.
