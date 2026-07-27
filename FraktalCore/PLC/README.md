# fraktal-core — Framework Library (Fraktal Core §2.2)

The Fraktal Core base classes, contract types, `FB_PermIntlk`, the base TcUnit suite, and the test-first scaffold — the "lifecycle written once" of Core §2.2/§6.1. Part I (the platform-neutral normative standard) is `Fraktal_Core_Part_I.md`; this library is its reference implementation on the TwinCAT 3 binding (Part II, `fraktal-tc3`).

> **Status (2026-07-22): compiles under TwinCAT 4026 and runs on a runtime.** The library set
> (`Fraktal_Core` + `Fraktal_Modules`) and the `Fraktal_Press_Demo` application build in XAE, deploy
> to a TC runtime, and have been exercised end-to-end over TF6100 (press demo cycling; generic HMI
> commanding; `QUERY_CONFIG` config manifest and `OPC.UA.DA` publication obscuring confirmed). Still
> pending: a **pinned-build CI compile** (§1.5) so drift is caught on every commit, and the items in
> `../../Specification/OBJECTIVES_AUDIT.md`. Per Core §2 / TC3 §2.1 pin your exact XAE/XAR build; the
> plcproj files target 4024+ (ABSTRACT FBs/methods). The sources are kept **source-compatible with
> TwinCAT 3.1.4024**: no optional/defaulted method inputs (a 4026+ feature) — every method input is
> passed explicitly at every call site (see `IMPLEMENTATION_NOTES.md` §62/§64/§69). File an issue for
> anything a pinned compiler rejects.

## Layout

```
Fraktal_Core/                the library (save/install as a versioned library — Core §2.2, §5.4)
  Params/PL_Fraktal.TcGVL      framework constants
  DUTs/                        E_ExecState · E_Reason (§8.8 framework bands) · ST_Diagnostic ·
                               step/condition/decision records (§6.5, §6.9(b), §6.11) ·
                               part context (§3.16) · mode/module enums
  Interfaces/                  I_Module · I_Unit · I_EquipmentModule · I_ControlModule ·
                               I_RecipeProvider (§3.8) · I_DeviceConnector (§3.15) ·
                               I_PartCarrier (§3.16) · I_VerdictProvider
  PermIntlk/FB_PermIntlk       the §7.2 container (Define / SetBypass / ClearBypass / Diagnostic)
  BaseClasses/                 FB_ControlModuleBase · FB_EquipmentModuleBase · FB_UnitBase
                               (template method: a type overrides ONLY _M_Dispatch — §2.2;
                               the Unit base adds modes/cascade, the step chain + stall walk,
                               and the wired-in cycle profiler §6.2/§6.9/§8.11.4)
  Connectivity/                FB_DeviceConnectorBase (§3.15, T7 once) · FB_LocalRecipeProvider (§3.8)
  Platform/F_Now               [TC3] synchronized-clock read (§2.7)
  Platform/F_TimingUpdate      §8.11.4 timing aggregate math (pure, unit-tested)
  BaseClasses/FB_CycleProfiler §8.11.4 cycle waterfall + per-step stats + time-class split
                               (WorkTime = real cycle time; fed by _M_SetStep)
Fraktal_Tests.plcproj        aggregate TcUnit manifest at the PLC common ancestor (no `..` links)
Fraktal_Tests/               Core + Modules + Press Demo test sources (excluded from runtime — §5.7)
  FB_ProbeCM / FB_ProbeEM      minimal concrete probes for the bases
  FB_Base_Tests                T1 · T2 · T4 (+ rollup/T6 at base level) proven ONCE
  FB_PermIntlk_Tests           first-out ordering · bypass rules
  FB_Timing_Tests              §8.11.4: exact math · classified cycle publication · command rows
  PRG_TcUnitRunner             TcUnit.RUN() — driven headless by TcUnit-Runner (TC3 §5.7)
scaffold/FB_TemplateCM/      "new CM type in 30 minutes" — pre-wired, initially RED (§5.7)
IMPLEMENTATION_NOTES.md      every reconciliation vs. the drafts + proposed Core §3.2 amendments
```

## Bring-up (first compile)

> A `.plcproj` is **not** opened directly like a solution — it is added *into* a TwinCAT
> XAE project. Verified on TwinCAT 3.1 4024.x (TcXaeShell): create/open a TwinCAT solution,
> then right-click the **PLC** node → **Add Existing Item…** → select the `.plcproj`.
> x32 vs x64 XAE does not matter for compiling; it only selects which local runtime
> (TwinCAT System Service) the shell pairs with. 4024.75 is fine — 4024+ is required
> (ABSTRACT FBs/methods).

1. In TcXaeShell: **File → New → Project → TwinCAT XAE Project**, then right-click `PLC` →
   **Add Existing Item…** → `Fraktal_Core/Fraktal_Core.plcproj`. The referenced Beckhoff
   libraries (`Tc2_Standard`, `Tc2_System`, `Tc2_Utilities`, `Tc3_Module`) resolve from the
   local repository automatically (they are placeholder references, `*` version).
2. Build warning-clean (Core §2), then **Save as library** and install; consumers pin the
   version (§2.2/§5.4). If the compiler rejects a construct, check the watch-item list in
   `IMPLEMENTATION_NOTES.md` §8 — these are known first-compile candidates, fix at source.
3. Add `Fraktal_Modules/Fraktal_Modules.plcproj` the same way (references the installed
   `Fraktal_Core`), build it, then save/install it as a library. It deliberately has no task or `MAIN`.
4. Add either executable example: `Fraktal_Demo/Fraktal_Demo.plcproj`, or
   `Fraktal_Press_Demo/Fraktal_Press_Demo.plcproj` for the pneumatic press.
5. Add `Fraktal_Tests.plcproj` from this `PLC/` directory; install **TcUnit** (tcunit.org)
   first. Its `PlcTask.TcTTO` calls `PRG_TcUnitRunner`. Run it only on an isolated
   test runtime/ADS port and leave **Autostart Boot Project disabled**. Start it
   deliberately, harvest the result, and stop it; never make it the machine boot
   application. All suites green is the M1 acceptance bar.
6. Wire TcUnit-Runner into CI so the JUnit results gate the merge alongside lint (Core §6.8, §1.5).

**Build order matters:** save/install `Fraktal_Core`, then save/install `Fraktal_Modules`.
`Fraktal_Demo`, `Fraktal_Press_Demo`, and `Fraktal_Tests` are executable applications, not libraries;
Tests additionally needs `Fraktal_Modules` and `TcUnit` installed.

The test manifest intentionally sits beside the project directories because it compiles the deployed
Press Demo sequence sources directly. Do not move it into `Fraktal_Tests/` or introduce `..` in a
`Compile Include`: TwinCAT's Add Existing Item importer rejects that segment as an invalid folder name
before it honors the virtual `Link` path.

If a test runtime is accidentally saved as a boot project and reports a PLC
stack overflow during TwinCAT startup, keep outputs safe, return TwinCAT to
Config mode, remove/disable the `Fraktal_Tests` boot project for that ADS port,
and restart. The following PREOP→OP / ADS 1804 messages are consequences of the
crashed PLC runtime, not separate I/O mapping faults.

## Writing your first type (Quick-start, Core §1.1)

1. Copy `scaffold/FB_TemplateCM/`, rename `Template` → your type, **reserve a reason band** (Core §8.8) and record it in the registry.
2. Declare your `E_<Type>Command`, `ST_<Type>Hal`, `ST_<Type>ParCfg` (keep `SchemaVersion` — §3.8).
3. Write `_M_Dispatch` only (~15 lines): drive output → await sensor → `_M_Complete()` / `_M_Fault(<band code>, …)`. Interlocks via `FB_PermIntlk`; the lifecycle is inherited.
4. Turn the RED suite GREEN: fill the T2/T3/T5 expected values and run against the sim HAL (§2.6) — no rig. T1/T4 are already proven by `FB_Base_Tests` for every inheriting type.
5. Wire once in the parent's `Setup` (§3.11); the tile renders itself (§3.13).

## Conformance mapping (Core §5.7)

| Row | Where proven |
|---|---|
| T1 handshake + Execute-drop reset | `FB_Base_Tests` (once, for every inheriting type) |
| T2 first-out reason **and** SourcePath | base mechanism in `FB_Base_Tests`; each type re-proves with **its** reasons (scaffold) |
| T3 interlock withholds output | per type (scaffold, RED) |
| T4 abort, no self-resume | `FB_Base_Tests` (once) |
| T5 recipe migrate-or-fault | per type (scaffold, RED) |
| T6 rollup adopts child verbatim | base mechanism in `FB_Base_Tests` (`FB_ProbeEM`); composites re-prove per Annex H §H.5 |
| T7 link supervision | `FB_Connector_Tests` (once, in the connector base) |
| T8/T9 tier rows | per composite/Unit type (worked: `FB_ClampEM_Tests` rollup, `FB_Unit_Tests`) |

`Fraktal_Modules/` ships reusable module types (including Annex A/B's `FB_CylinderCM` and `FB_ClampEM`) with their §8.8 band constants, simulation models, and configured device presets; their suites run in the same gate.
