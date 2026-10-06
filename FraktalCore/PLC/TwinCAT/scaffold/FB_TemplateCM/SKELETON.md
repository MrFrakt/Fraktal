# FB_TemplateCM — new-module scaffold (Core §5.7 / Quick-start §2)

*Copy this folder, rename `Template` → your type (e.g. `Gate`), and the §5.7 checklist drives the rest. The type is **born RED** and is done when CI turns it green — no post-hoc audit gap.*

## Files in this scaffold
| File | Role |
|---|---|
| `FB_TemplateCM.TcPOU` | `EXTENDS FB_ControlModuleBase`; `Command`, `ParCfg` (+`SchemaVersion`), HAL ref, empty `_M_Dispatch` with `// TODO CASE _step`. |
| `FB_TemplateCM_Tests.TcPOU` | Pre-wired, **initially RED**: `T2`/`T3`/`T5` with `Expected := 16#FFFF_FFFF` / `AssertTrue(FALSE)` placeholders. |
| `E_TemplateCommand.TcDUT` · `ST_TemplateHal.TcDUT` · `ST_TemplateParCfg.TcDUT` | Rename with the type: the command enum, the HAL, the recipe struct. |
| `SKELETON.md` | This file — the §5.7 row map + the reason-band reservation reminder. |

> This scaffold is **not** in any `.plcproj` (it is a copy-template, never compiled as-is). After rename, add the new files to the owning project's compile list.

## Step 0 — reserve a reason band FIRST (Core §8.8)
Before writing code, claim a free 100-block in the one number space and record it in the registry (`Twincat_Implementation` → `FraktalCore/PLC/...` §8.8 table + the type's `PL_<Type>Reasons`). The registry is the **single collision authority**.

| Range | Owner (do not squat) |
|---|---|
| `2001–2007` | Framework (TIMEOUT, PERMISSIVE_NOT_MET, INTERLOCK_DROPPED, RECIPE_INVALID, STEP_STALLED, RETRY_EXHAUSTED, CYCLE_TIME_DEGRADED) |
| `2900–2909` | Framework self-test (TEST_FAULT) — never raised in production |
| `10110–10116` | Basic cylinder CM |
| `10201–10204` | Axis CM |
| `10301–10310` | Robot CM |
| `10401–10406` | TCP/ASCII device CM |
| `11001` | Clamp EM |
| `1NNNN` | ← pick a free 100-block here for your type |

## §5.7 conformance row map — what THIS type must earn
| Row | Requirement | Proven where |
|---|---|---|
| **T1** | handshake + Execute-drop reset | **Inherited** — `FB_Base_Tests` proves it once for every type extending `FB_ControlModuleBase`. Do **not** repeat. |
| **T2** | first-out reason **and** `SourcePath` | **Earn here** — `T2_First_out_reason_and_path`: withhold the sensor, let `MoveTimeout` elapse, assert *your* band code on `ErrorID`. |
| **T3** | interlock withholds output | **Earn here** — `T3_Interlock_withholds_output`: force the interlock low (SIM-only hook), command, assert the output did not move. |
| **T4** | abort, no self-resume | **Inherited** — `FB_Base_Tests`. Do **not** repeat. |
| **T5** | recipe migrate-or-fault | **Earn here** — `T5_Recipe_invalid_faults`: stub the provider with a wrong `SchemaVersion`, assert `RECIPE_INVALID` naming both versions. |
| T6 | rollup adopts child verbatim | composites only (EM/Unit) — `FB_ClampEM_Tests` / `FB_Base_Tests`. N/A for a leaf CM. |
| T7 | link supervision | connector base — `FB_Connector_Tests`. N/A unless fronting a device. |
| T8/T9 | tier rows | per composite/Unit type. N/A for a leaf CM. |

## The path from RED to GREEN (Quick-start §3)
1. **Declare** your `E_<Type>Command`, `ST_<Type>Hal`, `ST_<Type>ParCfg` (keep `SchemaVersion` as the first `UINT`, §3.8). Rename the three DUTs.
2. **Write `_M_Dispatch` only** (~15 lines): `CASE _step` → drive output → await sensor → `_M_Complete()` / `_M_Fault(<band code>, …)`. Interlocks via `FB_PermIntlk`. Lifecycle is inherited.
3. **Turn the RED suite GREEN**: fill the `T2`/`T3`/`T5` expected values; run TcUnit against the sim HAL (§2.6) — no rig.
4. **Wire once** in the parent's `Setup` (§3.11); the tile renders itself (§3.13).

*Total: one `CASE` body + three expected values + a reserved reason band. Everything else is Fraktal.*
