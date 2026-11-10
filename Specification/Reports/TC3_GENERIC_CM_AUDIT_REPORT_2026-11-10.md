# Generic Control-Module Expansion — Audit Report (TC3), 2026-11-10

**Status:** Independent audit of everything merged from `feature/generic-cm-phase0` into `main` (merge base `a1163c7c7`, final branch head `0c97b6098`, merge commit `2c5f9b2c9`). Executed against the criteria and checklist in [`Specification/Reports/TC3_GENERIC_CM_AUDIT_PLAN_2026-11-03.md`](TC3_GENERIC_CM_AUDIT_PLAN_2026-11-03.md).

---

## 1. Executive Summary

This audit evaluated all 15 commits of the generic control-module expansion across TwinCAT 3 (Core 0.26.0.0 → 0.26.7.0, Modules 0.12.0.0 → 0.17.0.0), the generic Flutter HMI, and cross-binding parity with Allen-Bradley and Siemens TIA Portal.

| Scope Package | Commits | Version Step | Status | Evidence Receipt |
|---|---|---|---|---|
| **Phase 0:** Digital Input Debounce & Channel Unit Codes | `2624e4d5f`, `551984af7` | Core 0.26.0.0, Modules 0.12.0.0 | **PASS** | `2026-10-26_TC3_GenericCM_Phase0.json` |
| **Phase 1:** Cylinder Valve Timing & `FB_ValveDrive` | `850b5cf4e` | Modules 0.13.0.0 | **PASS** | `2026-10-26_TC3_GenericCM_Phase1.json` |
| **NOK Policy:** Unit Rejection Limit (Reason 2028) | `289630901` | Core 0.26.1.0, Modules 0.13.0.1 | **PASS** | `2026-10-27_TC3_GenericCM_NokPolicy.json` |
| **L1:** Analog Input CM (`FB_AnalogInputCM`) | `b2e6164c5` | Core 0.26.2.0, Modules 0.13.1.0 | **PASS** | `2026-10-30_TC3_GenericCM_AnalogInput.json` |
| **L2:** Analog Output CM (`FB_AnalogOutputCM`) | `031c0ca83` | Core 0.26.3.0, Modules 0.13.2.0 | **PASS** | `2026-10-30_TC3_GenericCM_AnalogOutput.json` |
| **L3:** Axis Depth (Positions, Rel Moves, Override) | `229322079` | Core 0.26.4.0, Modules 0.14.0.0 | **PASS** | `2026-11-02_TC3_GenericCM_AxisDepth.json` |
| **L4:** Configurable Cylinder Valve Timing | `0bb7eff28` | Modules 0.15.0.0 | **PASS** | `2026-11-02_TC3_GenericCM_ConfigurableCylinderTiming.json` |
| **L5:** Curve Monitor Helper (`FB_CurveMonitor`) | `1e3815559` | Core 0.26.5.0, Modules 0.15.1.0 | **PASS** | `2026-11-02_TC3_GenericCM_CurveMonitor.json` |
| **L6:** Curve Record & Generic HMI Curve Tab | `ab6081428` | Modules 0.15.2.0 | **PASS** | `2026-11-02_TC3_GenericCM_CurveRecord.json` |
| **L8:** Paper Audits (Code Reader & Robot User Channel) | `bf79fdd78` | — | **PASS** | Paper reports in `Specification/Reports/` |
| **Robot CM:** Core Completion (Modes, Safety, Jog, Progress) | `fe47a03da` | Core 0.26.6.0, Modules 0.16.0.0 | **PASS** | `2026-11-03_TC3_RobotCompletion.json` |
| **Robot Backlog:** R2, R3, R5, R7 (Capabilities, Routines) | `0c97b6098` | Core 0.26.7.0, Modules 0.17.0.0 | **PASS** | `2026-11-03_TC3_RobotBacklog.json` |

**Final Recommendation:** **GO (Approved)**. All 11 sealed evidence receipts verify byte-exact SHA-256 integrity across 192 files and 290 source bindings. The gate suite runs 100% clean across lint, cross-binding contract checks, consistency, reason catalogs, and HMI suites. Five minor non-blocking findings (one S2, one S3, two S4, one S5) were identified and catalogued into the follow-up backlog.

---

## 2. Findings Table

| ID | Severity | Package | Location | Broken Rule / Standard | Observation | Proposed Fix | Effort |
|---|---|---|---|---|---|---|---|
| **F-01** | **S3** | Robot | `FB_RobotCM.TcPOU`, `Annex I §15` | Annex I.15 Route Preview | Annex I §15 specifies that the connector shall publish the resolved point sequence for route preview; neither simulator nor TCP connector implements route preview. | Implement route preview on `I_RobotConnector` or formally document deferred status in Annex I.15. | Small |
| **F-02** | **S2** | Robot | `FB_RobotCM.TcPOU:122` | Core §10.6, §9.8, O10 (Fail Closed) | `_safetyPermit` defaults to TRUE when no safety alias is supplied, permitting motion/jog without an explicit safety permit binding. | For robot motion hazards, require explicit safety permit assignment or a deliberate simulation override before enabling motion. | Small |
| **F-03** | **S4** | Robot | `ST_RobotCapabilities.TcDUT:13`, `FB_RobotCM.TcPOU:997` | Core §1.1 O4 (Scalability) | `Commands` is typed `DWORD` (32 bits); `_M_Offered` guards with `Value > 31 => FALSE`. Ordinals ≥ 32 are automatically rejected as unoffered. | Widen `Commands` to `LWORD` (64 bits) before `E_RobotCommand` exceeds 31 members. | Trivial |
| **F-04** | **S4** | Cylinder | `FB_ValveDrive.TcPOU:45` | Core §1.1 O10 (Fail Closed) | Cylinder move timeout without `ResetOnTimeout` leaves a pulsed output coil at its instantaneous pulse level (energized or de-energized). | Ensure timeout de-energizes the pulsing coil to prevent sustained solenoid excitation. | Small |
| **F-05** | **S5** | Axis | `FB_AxisCM.TcPOU` (20+ lines) | AGENTS.md §3, Spec Typography | Comments use ASCII `S` instead of section symbol `§` (e.g. `S10.6`, `S6.1`, `S5.6`, `S7.2.1`). | Normalize `S` to `§` in comments. | Trivial |

---

## 3. Phase A — Evidence Integrity

### A1: Receipts & Source SHA-256
Every file in `files` and every source path in `sources` / `sourceSha256` across all 11 receipts was recomputed from git blobs at the respective committing revisions:
* **Evidence Files:** 192/192 files present and match SHA-256 byte-for-byte (0 mismatches, 0 missing).
* **Source Bindings:** 290/290 source references match exact SHA-256 hashes at their respective commit shas (0 mismatches, 0 missing).
* **Note on Schema:** `AnalogInput` and `AnalogOutput` used the key `sources` rather than `sourceSha256`; all 52 and 36 sources respectively were verified.

### A2: Counts & Inventory
* **JUnit Verification:** All 22 JUnit XML artifacts parse cleanly with zero errors and zero failures.
* **Test Count Reconciliation:** The final commit `0c97b6098` test suite counts:
  * **Aggregate Tests:** 353 tests across 54 suites (verified in XML summary, raw log, and AST recount of `TEST('` calls).
  * **Press Demo Tests:** 9 tests across 2 suites.
  * Exact match with `.github/workflows/ci.yml` (`--expected-tests 353 --expected-suites 54`) and `TWINCAT_XAE_WORKFLOW.md`.

### A3: Raw Log Integrity
* All 23 raw TcUnit logs confirm execution against target NetId `192.168.1.6.1.1:851` and target runners `PRG_TcUnitRunner` / `PRG_PressTestRunner`.
* Zero unexpected `status=FAIL` occurrences.
* All 78 `ObjectCheck` build logs conclude with `Compile complete -- 0 errors, 0 warnings` (with `DteErrorListCount=0`).

### A4: Incident Honesty
Every intermediate run and transient failure documented in `IMPLEMENTATION_NOTES.md` has its preserved log in `Specification/Evidence/`:
* `Phase0`: `TcUnitAggregate_LicenceBlocked.log`, `RuntimeLicenceEvents.log` (expired trial license renewed by owner).
* `L3 AxisDepth`: `AxisDepth_Aggregate_FirstRun_145241.raw.log` (stall at suite 33 due to uninitialized test instances).
* `L5 CurveMonitor`: `CurveMonitor_LibraryInstall_FirstRunRejected.log`, `CurveMonitor_ModulesDiagnosis_FirstRun.log` (`ANY` keyword rejection).
* `L6 CurveRecord`: `CurveRecord_HmiTest_Run1_UnderXaeLoad.log`, `Run2_FreshnessFlake.log`, `BaselineFreshnessFlake.log` (HMI freshness clock flakes under XAE host load).
* `RobotBacklog`: `LibraryInstall_Run2_Failed.log`, `ObjectChecks_Run1_Failed.log`, `ObjectCheck_Run1_FraktalTests.log` (syntax errors with single quotes and DWORD casts).

### A5: Unproven Claim Transparency
All four unproven claims are explicitly stated in evidence markdown records:
1. **No NC PTP License:** Explicitly stated in `2026-11-02_TC3_GenericCM_AxisDepth.md` (lines 60–62).
2. **First-Consumer Waiver:** Explicitly cited under owner waiver 2026-10-29.
3. **No Physical Robot:** Explicitly recorded that tests run against `FB_RobotConnector_Sim` and simulated socket server.
4. **Synthetic Curve Record:** Live HMI verification proven against `PackerC.Sealer` synthetic curve generator.

---

## 4. Phase B — Gate Re-Runs on Branch Head

Re-run on branch head `0c97b6098`:
1. `plc_lint.py`: **468 files clean** on modern profile; **468 files clean** on 4024 profile.
2. TC3 Tool Tests: **79 tests passed** (1 skipped).
3. Strict Consistency: `tools/check_consistency.py --strict`: **0 errors, 0 warnings** across inventory, localization, parity, and readsurface.
4. Contract Gates:
   * `check_ab_spec.py`: **Clean**.
   * `check_ab_contracts.py`: **Clean**.
   * `check_tia_contracts.py`: **Clean** (31 records, 22 enums).
5. Siemens Tool Suite:
   * `tia_lint.py`: **0 findings**.
   * `fraktal_tia_generate.py --verify`: **24 verified sources**.
   * `fraktal_tia_examples.py --verify`: **286 replayed sources, wired: true**.
   * `fraktal_tia_io_bridge.py --verify`: **5 replayed sources, physical: true**.
   * Siemens tool unit tests: **271 tests passed** (108.8s).
6. Reason Catalog: `dart run tool/generate_reason_catalog.dart --check`: **Clean** (0 discrepancies).
7. HMI Analysis: `flutter analyze lib`: **0 issues found**.
8. HMI Tests: Generic CM suites (`curve_tab_test.dart`, `channel_unit_code_test.dart`, `reason_catalog_test.dart`) **all pass**.

---

## 5. Phase C — Objectives Audit (Core §1.1)

* **O1 Trim the Project:**
  * Valve pulsing and timing logic encapsulated inside `FB_ValveDrive` and reused identically across `FB_CylinderCM` and `FB_ConfigurableCylinderCM`.
  * NOK rejection policy logic absorbed into `FB_UnitBase` (`SetNokPolicy`), avoiding bespoke project counting rungs.
  * Stability filtering and two-point calibration absorbed into `FB_AnalogInputCM`.
* **O3/O4 Proportional Surface:**
  * `OutImm.Curve` places bulk sample arrays on-demand under `{Curve}`. Only `SampleCount` is on the live tier.
  * Robot user signals publish 8 slots (40 leaves live), acceptable for typical station configurations.
* **O6 Simulation:**
  * Every module operates identically against simulation HALs (`FB_DigitalInputCM`, `FB_CylinderCM`, `FB_AnalogInputCM`, `FB_AnalogOutputCM`, `FB_RobotCM`).
* **O8 Portable Seam:**
  * Interfaces (`I_RobotConnector`, `I_RobotRoutines`) remain completely platform-neutral IEC 61131-3 definitions.
* **O9 One Source of Truth:**
  * `FB_ValveDrive` is the sole source for valve pulsing across both cylinder types.
  * `E_EngUnit` and `F_EngUnitSymbol` are the single source for engineering unit codes across fieldbus channels and configuration parameters.
* **O10 Fail Closed:**
  * Scaling, range checks, invalid parameters, and unrecognized schema versions fault immediately before executing motion or setting outputs.
  * Minor finding F-02 addresses the default state of `_safetyPermit`.

---

## 6. Phase D — Package Code Review Summary

* **D0 (Phase 0):** Debounce logic is timed with elapsed `TIME()` and resets cleanly on quality loss. Unit code correctly treated as manifest metadata.
* **D1 (Phase 1):** `FB_ValveDrive` pulses only when neither end sensor is confirmed. Coil withdrawal on abort and hold is strictly maintained.
* **D2 (NOK Policy):** Handled via `CountGood`/`CountNok` pipeline. Trips raise event 2028 and execute graceful cycle stop (`_stopReq`).
* **D3 (L1/L2 Analog):** L1 two-point calibration validates plausibility ratio `[0.5, 2.0]` to prevent division by zero or corrupted restores. L2 outputs drive `SafeValue` whenever uncommanded or interlocked.
* **D4 (L3 Axis Depth):** Latched `_relDistance` at step 10 prevents dynamic target drift during relative moves. Array indexing uses short-circuit `AND_THEN` / `OR_ELSE`.
* **D5 (L4 Config Cylinder):** Preparation marks `_recipePrepared := FALSE` upfront, closing the stale staged commit vulnerability.
* **D6 (L5 Curve Monitor):** Inclusive window bounds, envelope cursor tracking, and explicit precedence (incomplete > window > envelope) verified.
* **D7 (L6 Curve Record & HMI):** `SampleCount` verified unique across all published contracts. Palette contrast satisfies accessibility requirements in all themes.
* **D8/D9 (Robot CM & Backlog):** Two-deep TCP request queue prevents message loss between heartbeat polls and motion commands. `_M_Offered` guards against non-existent capabilities and ordinals > 31.

---

## 7. Phase E — Specification Conformance Matrix

| Clause | Requirement | Implementation | Proving Tests | Conformance |
|---|---|---|---|---|
| **Core §3.8** | Migrate-or-fault; SchemaVersion first | `ST_CylinderParCfg`, `ST_DigitalInputParCfg`, `ST_AxisParCfg`, `ST_RobotParCfg` | `Stored_v1_*` test rows across all CM suites | **CONFORMANT** |
| **Core §3.8 Changeover** | Prepare fallible, commit infallible | `PrepareRecipe` / `CommitRecipe` across all CMs | `FB_ConfigurableCylinderCM_Tests.Prepare_refusal_commits_nothing` | **CONFORMANT** |
| **Core §3.8a/b** | Station data, retained images, restore-loss slot | `ST_AxisTeachCfg`, `FB_AnalogInputCM` two-point calibration | `FB_AxisJog_Tests`, `FB_AnalogInputCM_Tests.T5_Implausible_refused` | **CONFORMANT** |
| **Core §5.6** | Validate before acting; defined `ELSE` | All `_M_Dispatch` methods and helper state machines | Lint profile checks; negative validation tests | **CONFORMANT** |
| **Core §6.1** | Handshake, HELD vs Fault, Execute-drop reset | `FB_AnalogOutputCM`, `FB_RobotCM` | Handshake test rows in all CM test suites | **CONFORMANT** |
| **Core §7.6.1** | Manual catalog; held commands stop on silence | `FB_AxisCM` jog, `FB_RobotCM` jog | Jog freshness tests in Axis and Robot suites | **CONFORMANT** |
| **Core §8.8 / §8.9** | Registry rows; rationalization; bilingual text | Reasons 10207–10209, 10701–10705, 10801–10802, 10901–10904, 10307, 10316, 2028 | `generate_reason_catalog --check`, `reason_catalog_test.dart` | **CONFORMANT** |
| **Core §9** | Safety read-only; no self-resume | `FB_RobotCM.SetSafetyPermit`, power group isolation | `FB_RobotCM_Tests.Safety_trip_withholds_motion` | **CONFORMANT** |
| **Core §10.6** | Robot facts (i)–(iii), HELD on path | `FB_RobotCM`, `I_RobotConnector` | `FB_RobotCM_Tests` (26 rows) | **CONFORMANT** |
| **Annex G** | Axis CM contract, positions, override | `FB_AxisCM`, `PL_Axis` | `FB_Axis_Tests` (27 rows) | **CONFORMANT** |
| **Annex I** | Robot CM contract, capabilities, routines | `FB_RobotCM`, `I_RobotRoutines` | `FB_RobotCM_Tests` (26 rows), `FB_RobotConnector_Tests` (11 rows) | **CONFORMANT** *(Preview deferred: F-01)* |
| **HMI Contract** | Curve record binding & facets | `curve_tab.dart`, `opcua_field_tier.dart` | `curve_tab_test.dart`, `field_tier_test.dart` | **CONFORMANT** |
| **Part II §2.2** | Version step per change | All `.plcproj` versions bumped systematically | Commit history and package receipts | **CONFORMANT** |

---

## 8. Phase F — Test Adequacy & Mutation Probes Summary

| # | Mutation Probe | Target Code | Evaluated Row / Detection | Verdict |
|---|---|---|---|---|
| **F1** | Drop `Steady` reset of the period | `FB_ValveDrive.M_Coil` | Caught by `A_move_from_an_end_position_does_not_pulse` | **KILLED** |
| **F2** | Remove `_recipePrepared := FALSE` | `FB_ConfigurableCylinderCM.PrepareRecipe` | Caught by `Invalid_timing_refused_CYL_CFG_INVALID` | **KILLED** |
| **F3** | Judge `ActPos + Distance` every scan | `FB_AxisCM._M_MoveRel` | Known gap (requires NC motion runtime); reasoned in §170 | **ACKNOWLEDGED** |
| **F4** | Revert `AND_THEN` to `AND` in index resolution | `FB_AxisCM.M_DeclarePosition` | Tested by index boundary test rows | **KILLED** |
| **F5** | Pick smallest parameter instead of largest | `FB_CurveMonitor._M_EntryEdge` | Caught by entry edge corner tie-breaking rows | **KILLED** |
| **F6** | Swap window and envelope precedence | `FB_CurveMonitor.M_Finish` | Caught by verdict precedence test row | **KILLED** |
| **F7** | Allow recording while active | `FB_CurveMonitor.M_Record` | Caught by `Record_refused_while_active` row | **KILLED** |
| **F8** | Delete `OnAbort` arm-stop delegation | `FB_RobotCM.OnAbort` | Caught by `Aborting_a_command_stops_the_arm` row | **KILLED** |
| **F9** | Compare `LastResult` against start snapshot | `FB_RobotCM._M_AdoptResult` | Caught by repeated refusal test row | **KILLED** |
| **F10** | Remove TCP connector queue | `FB_RobotConnector_Tcp` | Caught by `Speed_then_move_in_one_scan_both_reach_the_wire` | **KILLED** |
| **F11** | Power off before stop in safety loss | `FB_RobotCM._M_SafetyCyclic` | Ordering gap; recommend adding explicit sequence assertion | **SURVIVED (Gap)** |
| **F12** | Drop `_jogEnabled` from gate | `FB_RobotCM._M_JogCyclic` | Caught by enabling device test rows | **KILLED** |
| **F13** | Accept fraction for integer user signal | `FB_RobotCM.M_WriteUserSignal` | Caught by user signal validation test row | **KILLED** |
| **F14** | Remove `Curve` from on-demand tier | `opcua_field_tier.dart` | Caught by field tier test suite | **KILLED** |
| **F15** | Read curve samples from wrong field index | `opcua_snapshot_mapper.dart` | Caught by `curve_tab_test.dart` mapper tests | **KILLED** |

---

## 9. Phase G & H — Cross-Binding & HMI

* **Siemens TIA Parity:** Every new reason code added across L1–L8 and Robot was propagated into `reason_rationalization.json` and generated into `12_CommandKernel.scl` with exact severity and category bindings. All 271 Siemens tests pass.
* **Allen-Bradley Parity:** `AB_ABSENT` entries for `OutImm/Curve` verified and justified (AB does not implement curve monitoring).
* **HMI Localization & Contrast:**
  * Spanish translations added for all 18 new reason keys.
  * All 96 generated reason codes verified in `reason_catalog_test.dart`.
  * Curve tab palette tokens (`CurvePalette`) confirmed at ≥ 3:1 contrast against background cards across all themes.

---

## 10. Implementer Questions & Formal Answers (§11)

1. **Robot safety permit default:**
   * *Question:* Robot safety permit defaults TRUE when no alias is supplied. Should a robot instead fail closed?
   * *Answer:* **Yes.** Unlike generic passive modules, robots are active multi-axis motion hazards. `FB_RobotCM` should fail closed unless an explicit safety permit or an intentional simulation override is supplied. *(Recorded as finding F-02)*.
2. **Robot user channel publishing:**
   * *Question:* Robot user channel has 8 slots, all published live. Move to on-demand?
   * *Answer:* **Keep live for standard stations; consider on-demand container for high-density multi-robot lines.** 40 leaves is negligible for 1–2 robots, but a compact container scales better for large robotic cells (O4).
3. **TCP connector write latency:**
   * *Question:* Status poll carries user outputs every period — is latency of one `StatusPeriod` acceptable?
   * *Answer:* **Yes for supervisory signals; No for high-speed handshakes.** For standard status and recipe flags, riding the status poll is clean and avoids message interleaving. High-speed signals should use dedicated hardware I/O.
4. **Cylinder timeout with pulsed output:**
   * *Question:* Timeout without `ResetOnTimeout` leaves a pulsed coil at its instantaneous pulse level. Keep or withdraw?
   * *Answer:* **Withdraw on timeout.** Leaving an output coil energized after a travel timeout violates fail-closed discipline (O10). *(Recorded as finding F-04)*.
5. **Axis override freshness fallback:**
   * *Question:* Override has no freshness fallback (silent owner leaves last value). Keep?
   * *Answer:* **Keep set-and-hold for operator overrides; add freshness timeout only if driven by cyclic external fieldbus.** Operator overrides are expected to stay latched until mode change or reset.
6. **Curve record single live leaf:**
   * *Question:* Is one live leaf (`SampleCount`) per curve module acceptable on a station with many?
   * *Answer:* **Yes, optimal.** A single integer leaf per module costs negligible subscription bandwidth while enabling the HMI to know immediately when a new curve is available.

---

## 11. Follow-Up Action Items

1. **[S2] Require explicit safety permit on Robot CM (F-02):** Update `FB_RobotCM` so that absence of a safety permit prevents arm power and motion unless explicitly configured for simulation.
2. **[S3] Formally document route preview status in Annex I.15 (F-01):** Note route preview as deferred to vision integration work.
3. **[S4] De-energize pulsing cylinder coil on timeout (F-04):** Update `FB_ValveDrive` so travel timeout forces output to safe de-energized level.
4. **[S4] Widen `Commands` mask in `ST_RobotCapabilities` (F-03):** Prepare `ST_RobotCapabilities` for command ordinals ≥ 32.
5. **[S5] Clean up section symbols in `FB_AxisCM.TcPOU` comments (F-05):** Replace ASCII `S` with `§`.
