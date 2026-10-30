# Generic control-module library — remaining work plan (TC3), 2026-10-29

**Status:** plan for the remaining library work of the generic control-module
expansion. Phase 0, Phase 1 and the NOK-part limit are implemented and gated on
branch `feature/generic-cm-phase0` (IMPLEMENTATION_NOTES §164–§167; evidence
`Specification/Evidence/2026-10-26_TC3_GenericCM_Phase0.md`, `…_Phase1.md`,
`2026-10-27_TC3_GenericCM_NokPolicy.md`). Baseline for this plan: **Core 0.26.1.0,
Modules 0.13.0.1**, aggregate TcUnit inventory **269 tests / 51 suites**, Press
**9 / 2**, HMI **622 passed / 12 skipped**.

Paths are relative to the repository root. `TC3/` abbreviates
`FraktalCore/PLC/TwinCAT/`.

---

## 0. Owner decisions that bind this plan

| # | Decision | Date | Consequence here |
|---|---|---|---|
| D1 | **Only generic library work** (`Fraktal_Core`, `Fraktal_Modules`, the generic HMI). No Press bench or other example-application implementation. | 2026-10-29 | No package below edits `TC3/Examples/`. The Press needs only the version pins every library step already touches. |
| D2 | The "first consuming station" rule of the earlier plan is **waived** for these packages. | 2026-10-29 | Each PR states *"no station consumer (owner waiver 2026-10-29); consumers: TcUnit suite, generic HMI"*. Nothing is published that the generic HMI does not render. |
| D3 | Native TCP channel (TF6310), EL6001 serial, PartFeed NC axis and RFID/MES/historian adapters are **out of scope**. | 2026-10-06 | No RFID part carrier, no code-reader extension; the code-reader and robot items are paper audits only (§9). |
| D4 | TIA candidate contract changes need an explicit, versioned owner review (V2 reviewed 2026-10-27 for `NOK_LIMIT_REACHED`). | 2026-10-27 | No package below touches a frozen Core record or `E_Reason`. If one ever must, stop and ask (V3). |

**Owner question Q1 — answered 2026-10-29: keep the wiring.** WP5.1 (commit `289630901`) wired a NOK policy
into the Press composition root (`TC3/Examples/PressDemo/Fraktal_Press_Demo/00_System/MAIN.TcPOU`:
`NokPolicy` declaration and the `SetNokPolicy` block after `SetPartCarrier`). Under D1 the owner
may want it removed. If so: delete exactly those 8 lines, run the gates, commit
*"Remove the Press NOK policy wiring (library-only scope)"*, and drop the "Press" bullet from
IMPLEMENTATION_NOTES §167 with a dated one-line correction.

---

## 1. Rules for every package (read once, apply always)

### 1.1 Editing
- The repository pins `* -text`. Edit bytes, never `read_text/write_text`; many `.TcPOU`,
  `.plcproj`, `.md` and `.json` files mix CRLF and LF *within* the file. Measure endings with
  Python, give new lines the terminator of the anchor line, assert every anchor matches once,
  and check `git diff --stat` for whole-file rewrites. The Edit tool is safe only on pure-LF files.
- New POU/DUT/method GUIDs come from `uuid.uuid4()`. New files go into their project manifest
  (`Fraktal_Core.plcproj`, `Fraktal_Modules.plcproj`, `Tests/Fraktal_Tests.plcproj`).
- 4024 profile: no defaulted METHOD inputs; every caller passes every input (lint C1).
- Type layout version: when a type validates its own `ParCfg` without a recipe provider, compare
  `SchemaVersion` with a method-local default instance of the DUT (the DUT initializer is the one
  source), as `FB_DigitalInputCM._M_ParCfgValid` does.
- Vendor-neutral: tracked files never name the reference projects or vendor objects.
  The reference-material folder listed in `.gitignore` is ignored working material.

### 1.2 New module type checklist (Modules)
1. DUTs `ST_<Type>Hal`, `ST_<Type>ParCfg` (SchemaVersion first), `ST_<Type>ParCmd`,
   `ST_<Type>OutCmd`, `ST_<Type>OutImm`, `E_<Type>Command` (`qualified_only`, `NONE := 0`),
   optional `ST_<Type>StationCfg` (`SchemaVersion` first, 0 = never written).
2. `FB_<Type>CM EXTENDS FB_ControlModuleBase`; body `Cyclic();` only; `Setup` sets name,
   `_M_SetPresentation(DisplayNameKey, DescriptionKey, TypeKey := 'std.moduleType.<type>')`,
   publishes commands, restores StationCfg (`M_RestoreStationCfg`), registers editable values.
   `_M_Dispatch` has a `CASE` with an `ELSE` and refuses unknown commands with
   `E_Reason.UNSUPPORTED_COMMAND`. Derived flags through `_M_State` **unconditionally every scan**.
3. Reason block: constants in `TC3/Framework/Fraktal_Modules/Params/PL_ModuleReasons.TcGVL`;
   the Part I §8.8 registry row "Per module-type `10000+`"; one entry per reason in
   `Specification/reason_rationalization.json`; then
   `cd FraktalCore/HMI && dart run tool/generate_reason_catalog.dart` (writes `PL_ReasonCatalog`,
   `F_ReasonMeta*` and `lib/localization/reason_catalog.g.dart`), then `--check`.
   Update the pinned count in `FraktalCore/HMI/test/reason_catalog_test.dart` (78 today) and,
   if a symbol needs an acronym, `_defaultText` replacements in the generator.
4. Operator texts (`std.error.*`, `std.config.*`, `std.state.*`, `std.command.*`,
   `std.moduleType.*{,.name,.description}`) in `FraktalCore/HMI/lib/localization/default_catalogs.dart`
   in **both** `standardEnglish` and `standardSpanish`; `python tools/check_consistency.py --strict`.
5. TcUnit suite `TC3/Tests/Fraktal_Tests/FB_<Type>_Tests.TcPOU`, one instance per multi-scan row
   (TcUnit runs a suite's rows side by side), a done flag per row, timed rows asserting elapsed
   `TIME()` (never scan counts), registered in `PRG_TcUnitRunner`. Update the inventory pins
   (`.github/workflows/ci.yml` `--expected-tests/--expected-suites` and
   `Specification/Guides/TWINCAT_XAE_WORKFLOW.md` §6 table) — `check_consistency` names both.
6. T1/T4 are proven once in `FB_Base_Tests`; a type proves T2 (its first-out reason +
   `SourcePath`), T3 (interlock withholds output) where it has outputs, T5 (configuration refused).
7. Docs: IMPLEMENTATION_NOTES next section (`§168` onward), Annex or Part I text where a Core
   clause changes, `AGENTS.md` version sentence, `TC3/README.md` header, AB census row in
   `Specification/AllenBradley/AB_MISSING_FEATURES_HANDOVER_2026-10-06.md`, TIA row in
   `Specification/Siemens/SIEMENS_PORT_PLAN.md` §7.1/§7.2.

### 1.3 Gates, in order (a package is not done until all are green)
```
python FraktalCore/PLC/TwinCAT/tools/plc_lint.py
python FraktalCore/PLC/TwinCAT/tools/plc_lint.py --profile 4024
python -m unittest discover -s FraktalCore/PLC/TwinCAT/tools -t FraktalCore/PLC/TwinCAT/tools
python tools/check_consistency.py --strict
python -m unittest tools.test_check_consistency tools.test_check_ab_spec tools.test_check_ab_contracts tools.test_check_tia_contracts
python tools/check_ab_spec.py ; python tools/check_ab_contracts.py
python tools/check_tia_contracts.py
python tools/check_tia_contracts.py --generated FraktalCore/PLC/Siemens/Examples/PressDemo/generated
python FraktalCore/PLC/Siemens/tools/tia_lint.py
python FraktalCore/PLC/Siemens/tools/fraktal_tia_generate.py --verify FraktalCore/PLC/Siemens/Tests/Generator/generated
python FraktalCore/PLC/Siemens/tools/fraktal_tia_examples.py --verify FraktalCore/PLC/Siemens/Examples/PressDemo/generated
python FraktalCore/PLC/Siemens/tools/fraktal_tia_io_bridge.py --verify FraktalCore/PLC/Siemens/Examples/PressIoBridge/generated/Physical
python -m unittest discover -s FraktalCore/PLC/Siemens/tools -t FraktalCore/PLC/Siemens/tools
cd FraktalCore/HMI && dart run tool/generate_reason_catalog.dart --check && flutter analyze && flutter test
```
- **The TIA generator hashes TC3 Core DUTs, `PL_Fraktal`, `E_Reason` and `PL_ModuleReasons`
  (even a comment) as authoritative inputs.** After any such edit, regenerate:
  `python FraktalCore/PLC/Siemens/tools/fraktal_tia_generate.py FraktalCore/PLC/Siemens/Tests/Declaration/two_root_forest.json --out <empty temp dir>`,
  copy every differing file over `FraktalCore/PLC/Siemens/Tests/Generator/generated/`, then
  `python FraktalCore/PLC/Siemens/tools/fraktal_tia_examples.py --refresh FraktalCore/PLC/Siemens/Examples/PressDemo/generated`.
  A new or grown Core struct moves the pinned field total in
  `FraktalCore/PLC/Siemens/tools/test_s12_type_map.py` (615 today). Modules-only types do not
  change TIA sources, only the recorded hash of `PL_ModuleReasons`.
- The AB tool suite (`python -m unittest discover -s FraktalCore/PLC/Allen-Bradley/tools`) shows
  8 native-connection errors with or without these changes; it is not a CI gate. Do not "fix" it.
- Flutter: only **3.44.6** is installed (`C:\Apps\FlutterSdk\flutter`, on PATH). Never run a plain
  `flutter pub get` (it rewrites `pubspec.lock`); `--enforce-lockfile` refuses on this SDK, so
  analyze/test run on the existing resolution. Confirm `git status FraktalCore/HMI/pubspec.lock`
  is clean and record "Flutter 3.44.6, lock unenforced".

### 1.4 Compile and runtime gates (TwinCAT)
1. Build in an isolated worktree, never the working tree (XAE rewrites project files):
   `git worktree add --detach artifacts/<task>/checkout HEAD`, apply `git diff HEAD` and copy
   untracked files, then **verify every changed file byte-equal** with `cmp`.
2. Install from the worktree, dependency order, x32 shell in 32-bit PowerShell:
   `& "$env:WINDIR\SysWOW64\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File <wt>\FraktalCore\PLC\TwinCAT\tools\Invoke-TwinCatLibraryInstall.ps1 -DteProgId TcXaeShell.DTE.15.0 -Platform 'TwinCAT RT (x86)' -OutputDirectory 'FraktalCore\PLC\TwinCAT\Framework\Release\x32'`
   (`-Library Fraktal_Modules` when Core did not change).
3. `<wt>\FraktalCore\PLC\TwinCAT\tools\Invoke-TwinCatBuild.ps1 -ArtifactDirectory 'artifacts\twincat-build'`
   — six solutions, `CheckAllObjects=True`, "0 errors, 0 warnings". XAE's *Unknown TMC file version
   found* row is not a compile diagnostic; record it verbatim.
4. Runtime target: the isolated **UmRT_Default 192.168.1.6.1.1:851**, owner-designated for TcUnit
   gates and left on tests. **Before activating, read `<ExpireTime>` in
   `C:\ProgramData\Beckhoff\TwinCAT\3.1\Runtimes\UmRT_Default\3.1\Target\License\TrialLicense.tclrs`**
   — the current trial expires **2026-11-04T00:00**. Renewal is an interactive captcha: ask the
   owner, never automate it.
5. `Invoke-TwinCatTcUnitGate.ps1 -Solution 'FraktalCore\PLC\TwinCAT\Tests\FraktalTests.slnx' -ExpectedNetId 192.168.1.6.1.1 -TargetNetId 192.168.1.6.1.1 -ExpectedRunner PRG_TcUnitRunner -ExpectedTests <n> -ExpectedSuites <m> -StartBootProjectWithAds -RunSeconds 60 -ArtifactDirectory 'artifacts\tcunit'`,
   then the same for `Examples\PressDemo\PressTests.slnx` (`PRG_PressTestRunner`, 9 / 2).
   Validate each raw log with `FraktalCore/PLC/TwinCAT/tools/tcunit_to_junit.py`. If the hidden XAE
   hangs, look for a visible `#32770` modal ("Target system reports a fatal error") and close it with
   `PostMessage(dlg, WM_COMMAND, <button control id>, <button hwnd>)` — the gate then exits through
   its own `finally`.
6. Evidence: `Specification/Evidence/<date>_TC3_GenericCM_<Package>.md` plus a JSON receipt binding
   every copied log/JUnit and every changed source by SHA-256 (the earlier receipts are the model).
   State what was *not* run and why. Evidence is append-only.

### 1.5 Versions and pins
- Part II §2.2: **minor** = a consumer must act (removed/renamed member, changed published or
  persistent layout or meaning); **patch** = additive and compatible; **revision** = rebuild only.
  A Core step always brings a Modules revision rebuild with its Core pin moved.
- Every step updates `<ProjectVersion>` of the stepped library and the `DefaultResolution`
  pins in: `TC3/Framework/Fraktal_Modules/Fraktal_Modules.plcproj` (Core pin),
  `TC3/Examples/CoreDemo/Fraktal_Demo/Fraktal_Demo.plcproj`,
  `TC3/Examples/PressDemo/Fraktal_Press_Demo/Fraktal_Press_Demo.plcproj`,
  `TC3/Examples/PressDemo/PressTests.plcproj`, `TC3/Tests/Fraktal_Tests.plcproj`
  (version pins are not "example implementation" under D1), plus `AGENTS.md` (the "current Core is"
  sentence and the "Install Core … Modules …" sentence) and `TC3/README.md`.
- Commit per package after its gates, push to the branch, end commit messages with the
  `Co-Authored-By` line the session supplies.

### 1.6 Facts that constrain designs
- No NC PTP licence on this host: **no TcUnit row can move an axis**. Axis rows assert only what
  happens before any `MC_*` call (validation, resolution, registration, published state); every
  evidence record says the `MC_*` interaction is unproven.
- `MAX_CONFIG_WRITES` 12 per module, `MAX_STATE_FLAGS` 12, `MAX_CMD_CATALOG` 12.
- A capture (`M_ApplyCapture`) is routed through `M_ApplyConfigWrite`, so `_M_OnConfigWrite`
  sees captured and typed candidates alike. The hook sees raw text and must have no side effects.
- `M_RestoreStationCfg` keeps one restore-loss slot per module; a type with two retained images
  reports a loss of both once, with the second image's versions.
- `_M_RaiseMaintenance(Reason, Text)` exists only on `FB_UnitBase` (protected); a CM has no
  maintenance-event path.
- CM reason blocks are 100 wide in `10000–10999`. After this plan reserves `10700`, `10800` and
  `10900`, **every CM block is allocated**; any further CM type needs a Part I §8.8 registry
  amendment first (stop and ask).

---

## 2. Order and version steps

| Order | Package | Library step | Tests added (aggregate after) | Estimate |
|---|---|---|---|---|
| — | Q1 answered (Press NOK wiring kept or removed) | none / Press only | — | 0.25 d |
| L1 | Analog input CM (incl. stable measurement and tare) | Modules patch **0.13.1.0** | +16 / +1 suite (285 / 52) | 2.5 d |
| L2 | Analog output CM | Modules patch **0.13.2.0** | +9 / +1 (294 / 53) | 1.5 d |
| L3 | Axis: named positions, relative/step moves, speed scale and override | Modules minor **0.14.0.0** | +15 in existing axis suites (309 / 53) | 4 d |
| L4 | Configurable cylinder adopts the valve timing | Modules minor **0.15.0.0** | +8 (317 / 53) | 1.5 d |
| L5 | Curve monitor helper | Modules patch **0.15.1.0** | +11 / +1 (328 / 54) | 3 d |
| L6 | Curve record publication and HMI curve tab | Modules patch **0.15.2.0** + HMI | +2 PLC, HMI tests | 3 d |
| L7 | Utility and energy metering (§8.14) | Core minor **0.27.0.0** + Modules revision | see L7 | 4 d — **owner confirms scope first (Q2)** |
| L8 | Paper audits: code readers, robot user channel | none | — | 1 d |

Counts are the planned rows; update the pins to what the source actually has.

---

## 3. L1 — `FB_AnalogInputCM`

One type covers a plain analog signal, a measuring sensor (a value taken once it is stable)
and a scale (a tared, stable reading): the differences are configuration, not types (O9), and
the CM reason blocks are nearly exhausted (§1.6).

### 3.1 Files (all new, `TC3/Framework/Fraktal_Modules/`)
`FB_AnalogInputCM.TcPOU`; `DUTs/ST_AnalogInputHal.TcDUT`, `ST_AnalogInputParCfg.TcDUT`,
`ST_AnalogInputParCmd.TcDUT`, `ST_AnalogInputOutCmd.TcDUT`, `ST_AnalogInputOutImm.TcDUT`,
`ST_AnalogInputStationCfg.TcDUT`, `E_AnalogInputCommand.TcDUT`. Tests:
`TC3/Tests/Fraktal_Tests/FB_AnalogInputCM_Tests.TcPOU`. No sim plant (no station; rows drive the HAL).

### 3.2 Contract
```
ST_AnalogInputHal       : Raw : LREAL; Quality : BOOL := TRUE;
ST_AnalogInputParCfg    : SchemaVersion : UINT := 1;
                          RawMin : LREAL := 0.0;  RawMax : LREAL := 32767.0;
                          EngMin : LREAL := 0.0;  EngMax : LREAL := 100.0;
                          UnitCode : E_EngUnit := E_EngUnit.NONE;
                          UnderRange : LREAL := 0.0;  OverRange : LREAL := 100.0;   // engineering units, after tare
                          FilterTime : TIME := T#0MS;                              // first-order, 0 = off
                          StableBand : LREAL := 0.0;  StableTime : TIME := T#0MS;  // 0 band = no stability wait
                          MeasureTimeout : TIME := T#5S;
ST_AnalogInputParCmd    : Reserved : BOOL;                 // MEASURE has no parameter
ST_AnalogInputOutCmd    : Value : LREAL;                   // the measured value, valid on Done
ST_AnalogInputOutImm    : Value : LREAL; Gross : LREAL; Raw : LREAL;
                          Valid : BOOL; InRange : BOOL; Stable : BOOL; IoTag : STRING(80);
ST_AnalogInputStationCfg: SchemaVersion : UINT;            // 0 = never written, 1 = this layout
                          Ref1, Ref2, Meas1, Meas2 : LREAL; Tare : LREAL;
E_AnalogInputCommand    : NONE := 0, MEASURE := 1
```
FB: `VAR_INPUT Command : E_AnalogInputCommand; ParCfg; ParCmd`; `VAR_OUTPUT OutCmd; OutImm`;
`VAR PERSISTENT StationCfg : ST_AnalogInputStationCfg` (published name, as the air-pressure CM);
private `_hal : REFERENCE TO ST_AnalogInputHal` (`OPC.UA.DA` 0), `_identity : ST_IoPointIdentity`,
`_filtered : LREAL`, `_lastMs : TIME`, `_anchor : LREAL`, `_tStable : TON`, `_tMeasure : TON`;
`VAR CONSTANT AI_STATIONCFG_SCHEMA : UINT := 1; AI_FILTER_MAX : TIME := T#10S; AI_GAIN_MIN : LREAL := 0.5; AI_GAIN_MAX : LREAL := 2.0;`

Methods: `Setup(Name : STRING(80); HalRef : REFERENCE TO ST_AnalogInputHal; DisplayNameKey,
DescriptionKey : STRING(160)) : BOOL` (as `FB_DigitalInputCM`); `ConfigureIoIdentity(Identity :
ST_IoPointIdentity)`; `OnCyclic`; `_M_Dispatch`; `_M_OnConfigWrite`; private `_M_ParCfgValid : BOOL`,
`_M_AdjustmentPlausible(Ref1, Ref2, Meas1, Meas2 : LREAL) : BOOL`.

### 3.3 Behaviour (every scan, `OnCyclic`)
1. `cfgOk := _M_ParCfgValid()`: layout = compiled default; `RawMin <> RawMax`; `EngMin <> EngMax`;
   `UnderRange < OverRange`; `FilterTime <= AI_FILTER_MAX`; `StableBand >= 0`;
   `MeasureTimeout > T#0MS`; `StableBand = 0 OR StableTime < MeasureTimeout`.
2. `Raw := _hal.Raw`. Gross: if the adjustment is **active** (`Ref1 <> Ref2 AND Meas1 <> Meas2`)
   and plausible, `Gross := Ref1 + (Raw - Meas1) * (Ref2 - Ref1) / (Meas2 - Meas1)`; otherwise
   `Gross := EngMin + (Raw - RawMin) * (EngMax - EngMin) / (RawMax - RawMin)` (inverted ranges allowed).
3. Plausible = active pair whose gain, divided by the nominal gain, lies in
   `[AI_GAIN_MIN, AI_GAIN_MAX]` (a negative ratio — reversed sign — is implausible). An active,
   implausible pair (only possible after a restore or a layout change) makes the input invalid.
4. `Valid := ref valid AND _hal.Quality AND cfgOk AND NOT (active AND NOT plausible)`. Invalid →
   `Value := 0`, `Gross := 0`, filter re-initialises, `_tStable` reset — never the last good value.
5. Filter on `Gross - Tare`: first valid scan `_filtered := x`; then with `dt` = `TIME()` since the
   last scan, `_filtered := _filtered + (x - _filtered) * dt / (FilterTime + dt)`; `FilterTime = 0`
   passes through. `Value := _filtered`.
6. `InRange := Valid AND UnderRange <= Value AND Value <= OverRange`.
7. Stable: with `StableBand = 0`, `Stable := Valid`. Otherwise re-anchor when
   `ABS(Value - _anchor) > StableBand` (timer restarts), `Stable := _tStable(IN := Valid, PT := StableTime).Q`.
8. Publish `OutImm.Valid/InRange/Stable` through `_M_State(Idx 1..3, Key 'std.state.analogInputValid'
   / '…InRange' / '…Stable')`, unconditionally.

### 3.4 Command `MEASURE` (`_M_Dispatch`)
Step 10: `NOT Valid` → `_M_FaultIoN(AI_SIGNAL_INVALID, 'std.error.analogInputSignalInvalid',
_identity.Tag, _identity.Address)`; else start `_tMeasure`, step 20. Step 20: when `Stable` →
`Value < UnderRange` → `AI_UNDER_RANGE`; `Value > OverRange` → `AI_OVER_RANGE`; else
`OutCmd.Value := Value; _M_Complete()`. `_tMeasure.Q` before stable → `AI_NOT_STABLE`. Valid lost
in step 20 → `AI_SIGNAL_INVALID`. `ELSE` → `STEP_STALLED`. The command is published with
`_M_PublishCommand(Value := 1, Label := 'std.command.measure')`. Passive publication never faults.

### 3.5 Editable values (`Setup`, 5 of 12; all `Kind := STATION_CFG`, `Storage := AS_LREAL`, `RequiresReady := TRUE`)
| Key | Item | Unit | Bounds | Capture source |
|---|---|---|---|---|
| `analogInput.ref1`, `analogInput.ref2` | `StationCfg/Ref1`, `/Ref2` | `ParCfg.UnitCode` | `MIN(EngMin,EngMax) … MAX(…)` | — |
| `analogInput.meas1`, `analogInput.meas2` | `StationCfg/Meas1`, `/Meas2` | `NONE` | `MIN(RawMin,RawMax) … MAX(…)` | `ADR(OutImm.Raw)` |
| `analogInput.tare` | `StationCfg/Tare` | `ParCfg.UnitCode` | `±ABS(EngMax - EngMin)` | `ADR(OutImm.Gross)` |

Label keys `std.config.analogInputRef1|Ref2|Meas1|Meas2|Tare`. `_M_OnConfigWrite` refuses a
`ref*`/`meas*` candidate (parsed with `STRING_TO_LREAL`, substituted into the current pair) that
would make an **active** pair implausible; it accepts anything that leaves the pair inactive, so
an operator can capture one point at a time. Restore: `M_RestoreStationCfg(ADR(StationCfg.SchemaVersion),
AI_STATIONCFG_SCHEMA)`; on FALSE all five values := 0.0 (no adjustment, no tare).

### 3.6 Reasons (block **10700–10799**), rationalization, texts
| Code | Symbol | Rationalization (priority / category / shelvable) | Text key |
|---|---|---|---|
| 10701 | `AI_UNDER_RANGE` | MED / PROCESS / false | `std.error.analogInputUnderRange` |
| 10702 | `AI_OVER_RANGE` | MED / PROCESS / false | `std.error.analogInputOverRange` |
| 10703 | `AI_SIGNAL_INVALID` | MED / SYSTEM / false | `std.error.analogInputSignalInvalid` |
| 10704 | `AI_ADJUSTMENT_INVALID` | MED / SYSTEM / false | `std.error.analogInputAdjustmentInvalid` |
| 10705 | `AI_NOT_STABLE` | LOW / PROCESS / false | `std.error.analogInputNotStable` |
`AI_ADJUSTMENT_INVALID` is raised by `MEASURE` (step 10) when the active pair is implausible,
before `AI_SIGNAL_INVALID`, so the operator is sent to the adjustment, not the wiring. Give each
an `action` and `consequence`. Add `'AI': 'analog input'` to the generator's `_defaultText`
replacements so 10701 reads "Analog input under range." Also add
`std.moduleType.analogInput{,.name,.description}`, `std.command.measure`, the three
`std.state.analogInput*` keys and the five `std.config.analogInput*` keys.

### 3.7 Tests — `FB_AnalogInputCM_Tests` (16 rows)
`Linear_scaling_and_inverted_ranges`, `Invalid_parcfg_refused_at_setup_and_published_invalid`,
`Bad_quality_publishes_invalid_never_the_last_value`, `In_range_is_derived_every_scan`,
`Measure_completes_with_the_value_when_valid`, `Measure_refuses_an_invalid_signal_with_its_tag` (T2),
`Measure_under_and_over_range_fault` (T2), `Two_point_adjustment_applies_when_both_points_are_set`,
`Points_are_captured_from_the_live_raw_value`, `An_implausible_pair_is_refused_typed_or_captured` (T5),
`Tare_is_captured_from_gross_and_subtracted`, `Filter_settles_over_FilterTime` (timed),
`Stable_needs_the_band_for_StableTime` (timed), `Measure_waits_for_stable_then_times_out` (timed),
`A_first_boot_initializes_station_data_without_a_loss`, `Unsupported_command_is_refused`.
Write/capture rows go through `M_ApplyConfigWrite`/`M_ApplyCapture` (`Scope := <module name>`,
`Revision := 1`, `RootReady := TRUE`) — the station path. `+16 tests, +1 suite`.

### 3.8 Docs, version, cost
Part I §8.8 registry: add *"analog input CM `10701–10705`"*. IMPLEMENTATION_NOTES §168 (state the
one-type decision and the exhausted-blocks fact). AB/TIA census rows. **Modules patch 0.13.1.0.**
Upgrade cost: none (new type). TIA: regenerate (PL_ModuleReasons hash); no contract change.

---

## 4. L2 — `FB_AnalogOutputCM`

### 4.1 Files
`TC3/Framework/Fraktal_Modules/FB_AnalogOutputCM.TcPOU`; DUTs `ST_AnalogOutputHal`,
`ST_AnalogOutputParCfg`, `ST_AnalogOutputParCmd`, `ST_AnalogOutputOutCmd`, `ST_AnalogOutputOutImm`,
`ST_AnalogOutputStationCfg`, `E_AnalogOutputCommand`; tests `FB_AnalogOutputCM_Tests.TcPOU`.

### 4.2 Contract
```
ST_AnalogOutputHal       : Raw : LREAL;
ST_AnalogOutputParCfg    : SchemaVersion : UINT := 1; RawMin := 0.0; RawMax := 32767.0;
                           EngMin := 0.0; EngMax := 100.0; UnitCode : E_EngUnit := NONE;
                           Minimum : LREAL := 0.0; Maximum : LREAL := 100.0;   // accepted target band (eng)
                           SafeValue : LREAL := 0.0;                            // within [Minimum, Maximum]
ST_AnalogOutputParCmd    : Target : LREAL;
ST_AnalogOutputOutCmd    : Applied : LREAL;
ST_AnalogOutputOutImm    : Value : LREAL; Raw : LREAL; Withdrawn : BOOL; IoTag : STRING(80);
ST_AnalogOutputStationCfg: SchemaVersion : UINT; ManualTarget : LREAL;          // the HMI manual SET's target
E_AnalogOutputCommand    : NONE := 0, SET := 1
```
Methods: `Setup(Name, HalRef, DisplayNameKey, DescriptionKey) : BOOL`, `ConfigureIoIdentity`,
`SetAreaSafe(Ok : BOOL; DescriptionKey : STRING(255))` (identical meaning to `FB_CylinderCM.SetAreaSafe`,
`Intlk.Cond[1]`), `WithdrawOutputs()`, `RestoreOutputs()` (same latch semantics as the cylinder:
withdrawn until restored or the next `SET`), `OnAbort`, `_M_Dispatch`, private `_M_ParCfgValid`.

### 4.3 Behaviour
- Output written each scan: `_hal.Raw := RawMin + (_value - EngMin) * (RawMax - RawMin) / (EngMax - EngMin)`
  where `_value` is the commanded engineering value, or `SafeValue` while withdrawn, held, aborted,
  interlocked, or before the first `SET`.
- `SET`: target = `ParCmd.Target`, or `StationCfg.ManualTarget` when the request came through the
  manual path (`_manualReq`). Validation before writing: config invalid → `AO_CFG_INVALID`;
  target outside `[Minimum, Maximum]` → `AO_TARGET_OOR`; interlock not OK → §6.1 HELD with
  `SafeValue` (resumes with the target when the condition returns, like the cylinder). Done in the
  scan the value is written; `OutCmd.Applied := target`.
- After Done the value is **held**. An interlock lost after Done drives `SafeValue` and does **not**
  self-resume (§9.3 principle): only `RestoreOutputs` or a new `SET` re-applies it.
- Config validity: compiled layout; `RawMin <> RawMax`; `EngMin <> EngMax`; `Minimum <= Maximum`;
  `Minimum <= SafeValue <= Maximum`; both `Minimum` and `Maximum` inside the scalable range.
- Editable value: `analogOutput.manualTarget` (STATION_CFG, AS_LREAL, bounds `Minimum … Maximum`,
  `RequiresReady := TRUE`, label `std.config.analogOutputManualTarget`). Command catalog:
  `SET` labelled `std.command.set`.

### 4.4 Reasons (block **10800–10899**)
`AO_TARGET_OOR := 10801` (MED/PROCESS, `std.error.analogOutputTargetOutOfRange`),
`AO_CFG_INVALID := 10802` (MED/SYSTEM, `std.error.analogOutputConfigurationInvalid`).
Generator replacement `'AO': 'analog output'`.

### 4.5 Tests — `FB_AnalogOutputCM_Tests` (9 rows)
`Scales_the_target_to_raw`, `Target_outside_the_band_is_refused_before_writing` (T2),
`Invalid_configuration_is_refused` (T5), `Interlock_holds_with_the_safe_value_and_resumes` (T3),
`Interlock_lost_after_done_drives_safe_value_without_self_resume`, `Abort_drives_the_safe_value`,
`Withdraw_holds_until_restore_or_the_next_set`, `Manual_set_uses_the_station_target`,
`Safe_value_before_the_first_set`. **Modules patch 0.13.2.0**; Part I registry row; notes §169.

---

## 5. L3 — Axis depth (`FB_AxisCM`)

Files throughout: `TC3/Framework/Fraktal_Modules/FB_AxisCM.TcPOU`, `DUTs/E_AxisCommand.TcDUT`,
`ST_AxisParCmd.TcDUT`, `ST_AxisParCfg.TcDUT`, `ST_AxisOutImm.TcDUT`, new `DUTs/ST_AxisTeachCfg.TcDUT`,
new `Params/PL_Axis.TcGVL`, tests `TC3/Tests/Fraktal_Tests/FB_Axis_Tests.TcPOU` and
`FB_AxisJog_Tests.TcPOU`, `Specification/Annexes/Annex_G_Motion_PLCopen.md` (G.3–G.5).
**`ST_AxisStationCfg` (v2) and its keys `axis.taughtPosition` / `axis.jogRequiresEnable` stay
unchanged**, so no deployed image is lost.

### 5.1 Second retained image
```
PL_Axis (VAR_GLOBAL CONSTANT): MAX_POSITIONS : INT := 8;
ST_AxisTeachCfg : SchemaVersion : UINT;                       // 0 = never written, 1 = this layout
                  ManualStep : LREAL;                          // distance of one manual STEP_POS/STEP_NEG
                  Positions : ARRAY[2..PL_Axis.MAX_POSITIONS] OF LREAL;   // position 1 = TaughtPosition
```
`VAR PERSISTENT TeachCfg : ST_AxisTeachCfg;` restored by a second
`M_RestoreStationCfg(ADR(TeachCfg.SchemaVersion), AXIS_TEACHCFG_SCHEMA := 1)` (defaults all 0.0).
A first boot after the upgrade has version 0 and initializes silently.

### 5.2 Named positions (WP3.1)
- `M_DeclarePosition(Index : INT; LabelKey : STRING(160)) : BOOL` — composition root, **before**
  `Setup` (the `SetJogRequiresEnable` idiom). Refused for `Index < 2`, `> PL_Axis.MAX_POSITIONS`,
  an empty label, a second declaration of the same index, or after `Setup`. Labels in
  `_positionLabel : ARRAY[2..PL_Axis.MAX_POSITIONS] OF STRING(160)` (`OPC.UA.DA` 0).
- `Setup` registers, per declared index n: `M_RegisterConfigNumber(Key := 'axis.position<n>',
  Item := 'TeachCfg/Positions[<n>]', LabelKey := <declared>, Unit := MILLIMETER, Kind := STATION_CFG,
  Storage := AS_LREAL, pTarget := ADR(TeachCfg.Positions[n]), Minimum := SoftMin, Maximum := SoftMax,
  RequiresReady := FALSE)` and `M_RegisterCapture('axis.position<n>', ADR(OutImm.ActPos), AS_LREAL)`;
  and always `axis.manualStep` (Item `TeachCfg/ManualStep`, MILLIMETER, `0 … SoftMax - SoftMin`,
  label `std.config.axisManualStep`). Budget: 2 existing + 1 + up to 7 = 10 of 12.
- `ST_AxisParCmd` appends `PositionIdx : INT := 0`. `MOVE_TO`: 0 → `Target`; 1 → `TaughtPosition`;
  2…MAX declared → `TeachCfg.Positions[n]`; anything else → `AXIS_POSITION_UNDECLARED` (10207)
  **before** the soft-limit and homed checks. The resolved target then passes the existing
  `AXIS_TARGET_OOR` and `AXIS_NOT_HOMED` checks in that order.

### 5.3 Relative and step moves (WP3.2)
- `E_AxisCommand` appends `MOVE_REL := 5` (sequence: `ParCmd.Distance`, appended `Distance : LREAL := 0.0`),
  `STEP_POS := 6`, `STEP_NEG := 7` (manual catalog only: `±TeachCfg.ManualStep`). All three run
  `MC_MoveRelative` (new private `_moveRelFb`, `OPC.UA.DA` 0) behind the same handshake mapping as
  `MOVE_TO` (G.3). Target `ActPos + distance` is checked against the soft limits before motion
  (`AXIS_TARGET_OOR`), then homed (`AXIS_NOT_HOMED`). A zero distance completes at once without an
  `MC_*` call. `STEP_*` with `ManualStep = 0` is refused `AXIS_PARAM_OOR`.
- Command catalog: `_M_PublishCommand(STEP_POS, 'std.command.stepPositive')`,
  `(STEP_NEG, 'std.command.stepNegative')`; `MOVE_REL` is not published (it needs a distance);
  the manual-path filter in `_M_Dispatch` admits `HOME`, `MOVE_TO`, `STEP_POS`, `STEP_NEG`.

### 5.4 Speed composition and override (WP3.3)
- `ST_AxisParCfg` → `SchemaVersion := 2`, appended `SpeedScaleMin : REAL := 1.0`,
  `SpeedScaleMax : REAL := 100.0` (REAL and percent, as `ST_RobotParCfg`).
  `ST_AxisParCmd` appends `SpeedScale : REAL := 100.0`.
- Before motion (MOVE_TO/MOVE_REL/STEP_*): `SpeedScale` outside `[SpeedScaleMin, SpeedScaleMax]` →
  `AXIS_PARAM_OOR` (10208, `std.error.axisSpeedScaleOutOfRange`). Velocity
  `ParCfg.Velocity * SpeedScale / 100.0`; manual STEP_* use 100.
- `SetOverride(Percent : LREAL) : BOOL` — set-and-hold, refused (FALSE, value kept) outside
  `0.0 … 100.0`; drives `_power(Override := _override)` (today the literal `100.0` in `OnCyclic`), so
  it acts on a running move and on jog. Default 100. Published as appended `OutImm.Override : LREAL`.
  No freshness fallback: a silent owner can only leave an already accepted, lower-or-equal value.
- `PrepareRecipe` refuses `SpeedScaleMin <= 0` or `SpeedScaleMin > SpeedScaleMax` or
  `SpeedScaleMax > 100` with `AXIS_CFG_INVALID` (10209, `std.error.axisConfigurationInvalid`);
  existing members keep today's (absent) validation.

### 5.5 Reasons (axis block 10200–10299)
`AXIS_POSITION_UNDECLARED := 10207` (LOW/PROCESS), `AXIS_PARAM_OOR := 10208` (MED/PROCESS),
`AXIS_CFG_INVALID := 10209` (MED/SYSTEM); texts `std.error.axisPositionUndeclared`,
`axisSpeedScaleOutOfRange`, `axisConfigurationInvalid`; registry row "axis CM `10201–10209`".

### 5.6 Tests (15 rows, all before any `MC_*` call)
`FB_Axis_Tests`: `Undeclared_index_refused_before_motion`, `A_declared_index_resolves_inside_the_soft_limits`
(stored 50 → reaches the not-homed check, not OOR), `A_stored_position_outside_new_limits_is_refused`,
`Index_one_is_the_taught_position`, `Relative_target_outside_limits_refused_before_motion`,
`Relative_move_before_home_refused`, `Zero_distance_completes_without_motion`,
`Step_without_a_manual_step_refused`, `Speed_scale_outside_its_band_refused_before_motion`,
`Override_is_set_and_held_and_published`, `Override_outside_0_100_refused_and_kept`,
`Invalid_speed_band_refused_at_prepare` (T5), `Stored_v1_parcfg_record_refused` (probe DUT
`ST_ProbeAxisParCfgV1` in `Tests/Fraktal_Tests/`). `FB_AxisJog_Tests`:
`Declared_positions_register_and_capture` (capture from `NcToPlc.ActPos`),
`Declare_out_of_range_twice_or_after_setup_refused`. Rows that need `Homed` keep using the
existing seams; no row may require an NC axis.

### 5.7 Version, cost, docs
**Modules minor 0.14.0.0** (ParCfg v2, ParCmd growth, enum append, new image, OutImm member).
Upgrade cost: `ST_AxisParCfg` records **stored** in `FB_LocalRecipeProvider` are refused
(`RECIPE_INVALID`) until re-saved; no StationCfg loss. Annex G G.3/G.4b/G.5; notes §170; evidence
says plainly that `MC_MoveRelative` and the override's effect on motion are unproven on this host.
Deferred, safety-worded: held `VELOCITY`, torque mode, `SET_REFERENCE`, standstill window, brake
functions (the safety system owns brake control and test).

---

## 6. L4 — `FB_ConfigurableCylinderCM` adopts the valve timing

- `ST_ConfigurableCylinderParCfg` → `SchemaVersion := 2`, appended `MinOutputTime`, `PulsingWidth`,
  `PulsingPeriod : TIME := T#0MS`, `ResetOnEndPos`, `ResetOnTimeout : BOOL := FALSE`
  (`SettleTime` exists — default `T#30MS` stays).
- The commanded output (`ToWorkOut`, or `ToHomeOut` when not `SingleActing`) is driven through one
  `FB_ValveDrive` exactly as `FB_CylinderCM` does: pulsing only for a move that starts with neither
  position confirmed; `Done` needs settle **and** `MinTimeElapsed`; the reset policies at Done/timeout.
- `PrepareRecipe` additionally refuses (`CYL_CFG_INVALID`): non-zero `MinOutputTime >= MoveTimeout`;
  `PulsingWidth > 0` with `PulsingWidth >= PulsingPeriod`; **`ResetOnEndPos` with `SingleActing`**
  (withdrawing a spring-return coil at its end would return the cylinder).
- `OnAbort` keeps `DeenergizeOnAbort`/`SafePosOnAbort` semantics unchanged; a lost interlock still
  withdraws both outputs. This type has no `WithdrawOutputs`; do not add one.
- Tests in `FB_ConfigurableCylinderCM_Tests` (8): settle+min, pulsing from the middle, steady from
  an end position, ResetOnEndPos, ResetOnTimeout, single-acting+ResetOnEndPos refused,
  defaults reproduce v1, stored v1 record refused (probe DUT). **Modules minor 0.15.0.0**; notes §171.

---

## 7. L5 — `FB_CurveMonitor` (owner-private helper)

### 7.1 Files
`TC3/Framework/Fraktal_Modules/FB_CurveMonitor.TcPOU`; `Params/PL_Curve.TcGVL`
(`MAX_WINDOWS : INT := 4; MAX_POINTS : INT := 32; MAX_SAMPLES : INT := 256`); DUTs
`ST_CurvePoint {X, Y : LREAL}`, `E_CurveEdge {ANY := 0, LEFT := 1, RIGHT := 2, BOTTOM := 3, TOP := 4}`,
`ST_CurveWindow {XMin, XMax, YMin, YMax : LREAL; Entry, Exit : E_CurveEdge}`,
`ST_CurveEnvelope {Count : INT; Upper : BOOL; Points : ARRAY[1..PL_Curve.MAX_POINTS] OF ST_CurvePoint}`,
`ST_CurveSpec {SchemaVersion : UINT := 1; WindowCount : INT; Windows : ARRAY[1..PL_Curve.MAX_WINDOWS] OF ST_CurveWindow; EnvelopeCount : INT; Envelopes : ARRAY[1..2] OF ST_CurveEnvelope}`
(the owner embeds it in its own ParCfg), `ST_CurveResult {Complete : BOOL; Verdict : E_Verdict;
Reason : DINT; WindowPassed : ARRAY[1..PL_Curve.MAX_WINDOWS] OF BOOL; EnvelopeCutIdx : ARRAY[1..2] OF INT;
Samples : INT}`. Tests `FB_CurveMonitor_Tests.TcPOU`.

### 7.2 API and semantics
- `M_Validate(Spec : REFERENCE TO ST_CurveSpec) : BOOL` — counts in range; every window
  `XMin < XMax AND YMin < YMax`; every envelope `Count >= 2` with strictly increasing X. The owner
  calls it in its `PrepareRecipe` and refuses with `CURVE_SPEC_INVALID`.
- `M_Begin(Spec : REFERENCE TO ST_CurveSpec)`, `M_Sample(X, Y : LREAL)` (O(windows + 2) per call,
  evaluated online — no sample buffer is needed for the verdict), `M_Finish() : ST_CurveResult`.
- Window with `Entry = Exit = ANY`: passes when any sample lies inside. Otherwise the curve must
  enter through `Entry` (the segment from the last outside sample to the first inside sample crosses
  that edge) and leave through `Exit`; a sample inside but entered/left through another edge, or no
  sample inside, fails it.
- Envelope: every sample with `X` inside the envelope's X span is compared with the linear
  interpolation; `Upper` requires `Y <= env(X)`, lower `Y >= env(X)`; the first violating sample index
  is recorded.
- `Complete` = the curve reached `X >= max(XMax of windows, last envelope X)`; otherwise
  `CURVE_INCOMPLETE`. Verdict `OK` only when complete, every window passed and no envelope cut; the
  first failing rule names `Reason`: incomplete before window before envelope.
- The helper has no identity and raises nothing: the owner faults with `_M_FaultN(Result.Reason, …)`
  or, in a Unit chain, records `M_PartProcessed(NOK, Result.Reason)` and values via `M_PartRecord`.

### 7.3 Reasons (block **10900–10999**, registered to the helper, raised by its owner)
`CURVE_WINDOW_VIOLATED := 10901`, `CURVE_ENVELOPE_VIOLATED := 10902`, `CURVE_INCOMPLETE := 10903`
(MED/PROCESS each), `CURVE_SPEC_INVALID := 10904` (MED/SYSTEM).

### 7.4 Tests (11, pure logic, single scan)
Spec validation (degenerate window, non-increasing envelope, count out of range); ANY window
pass/miss; entry through the declared edge; entry through another edge fails; exit edge; upper
envelope cut with interpolation; lower envelope; incomplete curve; verdict precedence; begin resets.
**Modules patch 0.15.1.0**; notes §172.

---

## 8. L6 — Curve record publication and the HMI curve tab

- Modules: `ST_CurveRecord {SampleCount : INT; Samples : ARRAY[1..PL_Curve.MAX_SAMPLES] OF ST_CurvePoint;
  Spec : ST_CurveSpec; Result : ST_CurveResult}` and `FB_CurveMonitor.M_Record(Target : REFERENCE TO
  ST_CurveRecord)` — copies the last finished curve once per part. L6 gives the helper a bounded
  buffer of the first `MAX_SAMPLES` samples (the L5 verdict needs none); later samples are still
  evaluated but kept out of the record, which carries `Truncated : BOOL`, and `Result.Complete`
  is unaffected. The owner publishes the record as `OutImm.Curve`. 2 PLC rows (record copy,
  truncation flag).
- HMI: `lib/domain/types.dart` `CurveFacet` (samples, windows, envelopes, verdict); mapper detects a
  module publishing `…/Curve/SampleCount` and reads it on demand (slow tier, not cyclic);
  `lib/ui/` read-only **Curve** tab: windows as rectangles, envelopes as polylines, the curve, the
  verdict; geometry as fractions of the container; colours from semantic tokens. Sim repository:
  one module with a synthetic curve. Tests: mapper row, widget row in every theme
  (`kThemes`/`themeAt`), contrast row in `test/theme_contrast_test.dart`.
- `Specification/HMI_CONTRACT.md`: a row for `Curve : ST_CurveRecord` (on-demand, read-only, ≤ 8
  series, no writes). **Modules patch 0.15.2.0** + HMI; notes §173.

---

## 9. L7 — Utility and energy metering (§8.14) — scope question Q2 first

**Q2 — answered 2026-10-29: deferred** until a station meters utilities. Original question: implement the optional §8.14 profile now (Core minor), or leave it until a
station meters utilities? If yes, the design is:
- Core DUTs `E_UtilityMedium {ELECTRICAL := 1, AIR := 2, WATER := 3, COOLANT := 4}` (append-only,
  HMI-mirrored), `ST_UtilityChannel {Medium; UnitCode : E_EngUnit; Instant : LREAL; Total : LREAL;
  Valid : BOOL; DescriptionKey : STRING(160) (OPC.UA.DA 0)}`, `PL_Fraktal.MAX_UTILITIES : INT := 4`.
- `FB_UnitBase`: published `Utilities : ARRAY[1..MAX_UTILITIES] OF ST_UtilityChannel`,
  `UtilityCount`, `SetUtility(Idx, Medium, UnitCode, DescriptionKey) : BOOL` (composition root),
  `M_UtilitySample(Idx, Instant, Total, Valid)` (per scan, from the driver), and an EnPI
  `EnergyPerGoodPart : LREAL` derived from the ELECTRICAL total and `GoodCount` between resets.
- Leak/anomaly: per channel a learned idle baseline (`ST_UtilityParCfg`), deviation beyond a band
  for a time → `_M_RaiseMaintenance(E_Reason.UTILITY_DEVIATION, 'std.maintenance.utilityDeviation')`
  (code 18 already exists). Never gates motion (§8.14).
- Cross-binding: new Core records are not in the TIA frozen subset, but the TIA generator inputs
  change (regenerate; S12 pin moves). HMI facet + HMI_CONTRACT row.
Estimate 4 d. Not started without Q2 = yes.

---

## 10. L8 — Paper audits (no code)

- **Code readers**: compare `TC3/Framework/Fraktal_Core/DeviceCMs/FB_TcpCodeReaderCM`,
  `FB_TcpVisionCM`, `TC3/Framework/Fraktal_Modules/FB_Matrix220CM`, `FB_Iv3VisionCM` against: read
  retries with a bounded count, a quality grade value and text, configuration download, multi-code
  reads. Output `Specification/Reports/TC3_CODE_READER_PARITY_AUDIT_<date>.md` listing gaps and the
  type that should own each. Implementation waits (D3).
- **Robot user channel**: compare `FB_RobotCM`/`I_RobotConnector` against user bit/int/real exchange
  and the §10.6 mandatory facts (mode request/report pair, bounded speed, protective stop).
  Output `Specification/Reports/TC3_ROBOT_USER_CHANNEL_AUDIT_<date>.md`.

---

## 11. Not planned, and why

| Item | Why not |
|---|---|
| RFID/data-tag part carrier | Out of scope (D3). |
| Measuring-sensor CM, scale CM as separate types | Folded into L1 (stable measurement, tare). |
| Cylinder "reached too fast", valve presets, mode-dependent pulsing, growing pulse width | No demand recorded anywhere; a CM cannot know its Unit's mode. Reopen only on request. |
| Config-declared observer conditions | Overlaps the Unit's project-owned release branch (§7.2.1/§7.8); needs a design decision first. |
| Core promotion of the live-influence overlay and the capability declaration | Needs a second reusable consumer; after L3 only the axis has a set-and-hold override. |
| Measurement-system studies | Application templates on the `CAPABILITY` mode, not library types (D1). |
| Working-code taxonomy on `E_CarrierKind` | A spec discussion, not code. |
| AB / TIA implementations of the new types | Other bindings; each package records its parity row only. |
