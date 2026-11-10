# Generic Control-Module Library Audit — 2026-11-10

Scope: Independent audit of `feature/generic-cm-phase0` merge commit `2c5f9b2c9` (covering Core 0.26.0.0 → 0.26.7.0 and Modules 0.12.0.0 → 0.17.0.0), executed against [`Specification/Reports/TC3_GENERIC_CM_AUDIT_PLAN_2026-11-03.md`](../Reports/TC3_GENERIC_CM_AUDIT_PLAN_2026-11-03.md).
Deliverable report: [`Specification/Reports/TC3_GENERIC_CM_AUDIT_REPORT_2026-11-10.md`](../Reports/TC3_GENERIC_CM_AUDIT_REPORT_2026-11-10.md).
Bound by SHA-256 in [the receipt](2026-11-10_TC3_GenericCM_Audit.json).

---

## 1. Evidence Verification Summary (Phase A)

* **11 Sealed Receipts Audited:**
  1. `2026-10-26_TC3_GenericCM_Phase0.json` (Debounce, Channel Unit Codes)
  2. `2026-10-26_TC3_GenericCM_Phase1.json` (Cylinder Valve Timing, `FB_ValveDrive`)
  3. `2026-10-27_TC3_GenericCM_NokPolicy.json` (NOK Rejection Limit Reason 2028)
  4. `2026-10-30_TC3_GenericCM_AnalogInput.json` (`FB_AnalogInputCM`)
  5. `2026-10-30_TC3_GenericCM_AnalogOutput.json` (`FB_AnalogOutputCM`)
  6. `2026-11-02_TC3_GenericCM_AxisDepth.json` (Positions, Rel Moves, Override)
  7. `2026-11-02_TC3_GenericCM_ConfigurableCylinderTiming.json` (Configurable Timing)
  8. `2026-11-02_TC3_GenericCM_CurveMonitor.json` (`FB_CurveMonitor`)
  9. `2026-11-02_TC3_GenericCM_CurveRecord.json` (`FB_CurveRecord`, Generic HMI Tab)
  10. `2026-11-03_TC3_RobotCompletion.json` (Core Robot CM, Modes, Safety, Jog)
  11. `2026-11-03_TC3_RobotBacklog.json` (Capabilities, Routines, Untaught Points, Declared Moves)
* **File Integrity:** 192 of 192 evidence files verified against their recorded SHA-256 hashes (100% match, 0 mismatches, 0 missing).
* **Source Binding Integrity:** 290 of 290 source bindings verified against git tree blobs at the recorded commit hashes (100% match, 0 mismatches, 0 missing).
* **Test Reconciliations:** All 22 JUnit XML files verified (0 failures, 0 errors). Reconciles with CI and raw test logs: 353 aggregate tests across 54 suites (26 `RobotCmTests`, 11 `RobotConnectorTests`, etc.), and 9 press tests across 2 suites.
* **Compiler & Object Checks:** 78 `ObjectCheck` logs and 23 raw build logs verified clean: 0 errors, 0 warnings.
* **Incidents & Waivers Honesty:** All 5 recorded development incidents cataloged and reconciled. Unproven items (no physical robot, no NC license, synthetic test curves, first-consumer robot waiver) noted.

---

## 2. Gate Verification (Phase B)

Executed on current audit branch (`audit/generic-cm-library`):

* **PLC Lint:** `plc_lint.py` checked across 468 files under both default and `--profile 4024`: 0 errors, 0 warnings.
* **TC3 Tool Tests:** 79 tests passed (1 skip).
* **Cross-Specification Consistency:** `check_consistency.py --strict` passed: 0 errors, 0 warnings.
* **Repository Contract Tests:** 85 tests passed.
* **Allen-Bradley & Siemens Contract Gates:** AB frozen/spec gates clean; TIA candidate V2 clean (plain and `--generated`).
* **Siemens TIA Tooling:** `tia_lint` 0 findings, `fraktal_tia_generate` (24 verified), `fraktal_tia_examples` (286 replayed), `fraktal_tia_io_bridge` (5 replayed), 271 tool tests passed.
* **Localization & Reason Catalog:** `generate_reason_catalog.dart --check` clean (0 diffs).
* **HMI Verification:** `flutter analyze lib` passed with 0 issues; `dart analyze` in `FraktalCore/HMI/gateway` passed with 0 issues. Unit tests for curve tab, channel unit codes, and reason catalog passed.

---

## 3. Findings

| ID | Severity | Package | Target | Description |
|---|---|---|---|---|
| **F-01** | **S3** | Robot | `Annex I §15` | Route preview not implemented on connector or simulator. |
| **F-02** | **S2** | Robot | `FB_RobotCM.TcPOU:122` | `_safetyPermit` defaults to TRUE when no alias is supplied. |
| **F-03** | **S4** | Robot | `ST_RobotCapabilities.TcDUT:13` | Capabilities `Commands` bitmask is `DWORD` (limited to ordinals 0..31). |
| **F-04** | **S4** | Cylinder | `FB_ValveDrive.TcPOU:45` | Cylinder timeout without `ResetOnTimeout` leaves pulsed coil at instantaneous state. |
| **F-05** | **S5** | Axis | `FB_AxisCM.TcPOU` | ASCII `S` used instead of section symbol `§` in comments. |

---

## 4. Follow-Up Action Items

1. **[S2] Require explicit safety permit on Robot CM (F-02):** Prevent arm power and motion when no safety permit alias is provided unless explicitly in simulation mode.
2. **[S3] Document route preview status in Annex I.15 (F-01):** Note route preview as deferred to vision integration work.
3. **[S4] De-energize pulsing cylinder coil on timeout (F-04):** Update `FB_ValveDrive` so travel timeout de-energizes pulsed coil.
4. **[S4] Widen `Commands` mask in `ST_RobotCapabilities` (F-03):** Change `DWORD` to `LWORD` before robot command ordinals exceed 31.
5. **[S5] Clean up section symbols in `FB_AxisCM.TcPOU` comments (F-05):** Replace ASCII `S` with `§`.

---

## 5. Audit Conclusion

**Recommendation: GO (Approved).**
The generic control-module library expansion strictly complies with Fraktal core design principles, contracts, lifecycle mechanics, and diagnosability standards. The findings are non-blocking and scheduled into the S1→S5 follow-up backlog.
