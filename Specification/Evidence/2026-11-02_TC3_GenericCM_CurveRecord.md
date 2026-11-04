# Generic control-module expansion, L6 — 2026-11-02

Working source: branch `feature/generic-cm-phase0` on `1e3815559` (L5). Core **0.26.5.0**
(unchanged), Modules **0.15.2.0**, HMI curve tab. Every artifact below is bound by SHA-256
in [the receipt](2026-11-02_TC3_GenericCM_CurveRecord.json), together with the changed
sources.

## What was implemented

- **PLC** (IMPLEMENTATION_NOTES §173): `ST_CurveRecord` and `FB_CurveMonitor.M_Record` —
  the last finished curve (first 256 samples, the spec, the verdict) copied once per
  curve for its owner to publish as `OutImm.Curve`; `Truncated` when more samples were
  judged than kept.
- **HMI**: `CurveFacet` on `ModuleNode.curve`; `OutImm/Curve` on demand except the live
  `SampleCount`; a read-only built-in **Curve** tab that demands `{Curve}` only while open
  and draws windows (pass/fail colour), envelopes, samples, the first cut and the PLC's
  verdict with its reason; colours from a measured semantic palette; the simulator's
  `PackerC.Sealer` publishes a synthetic curve. `HMI_CONTRACT.md` gains the binding table.
- **Cross-binding**: `check_consistency` declares `OutImm/Curve` absent on AB (a recorded
  gap); Siemens plan and AB census rows updated.

## Passed on the final source

- Both PLC lint profiles (463 files), 79 TC3 tool tests (one skip), strict consistency
  (0/0), the 85 repository gate tests, both AB gates, the TIA candidate-contract gate
  (plain and `--generated`), `tia_lint`, the TIA generator, examples and I/O-bridge
  replays, 271 Siemens tool tests and the reason-catalog generator check —
  `…_CheapGates.log`.
- Core 0.26.5.0 and Modules 0.15.2.0 saved and installed from the isolated worktree
  (TcXaeShell.DTE.15.0, 32-bit PowerShell, Debug, TwinCAT RT (x86)) —
  `…_LibraryInstall.log`.
- Six `CheckAllObjects` solutions: 0 errors, 0 warnings each.
- On the isolated **UmRT_Default 192.168.1.6.1.1:851** (Autostart off, ADS Run start):
  aggregate **330/330 in 54 suites** (17:06:13), including the two new
  `CurveMonitorTests` rows; Press **9/9 in 2 suites** (17:07:42). Both validated by
  `tcunit_to_junit.py`.
- HMI: analyzer clean; **628 passed / 12 skipped** on Flutter 3.44.6, `pubspec.lock`
  unchanged — six new rows (field tier, mapper, three Curve-tab widget rows across every
  theme, one contrast row).

## Incidents

- The first strict-consistency run on this source failed 18 read-surface rows: the
  mapper's curve reads went through a parameter and a closure the gate cannot resolve.
  Rewritten in the mapper's binding idiom and the record declared absent on AB.
- Three full HMI runs before that rewrite each failed one or two wall-clock tests in
  `opcua_freshness_test.dart` (a 150 ms freshness budget) —
  `…_HmiTest_Run1_UnderXaeLoad.log`, `…_HmiTest_Run2_FreshnessFlake.log`,
  `…_HmiTest_Run3_FreshnessFlake.log`. The same full
  suite on the baseline without this change fails the same test
  (`…_HmiTest_BaselineFreshnessFlake.log`); the file passes alone
  (`…_HmiFreshnessIsolated.log`). The passing full run is on the final source.

## Not executed, and why

- No library type owns and publishes a curve yet (owner waiver 2026-10-29, plan D2): the
  record is proven by the helper's suite, the tab against the simulator and test data.
  A live PLC-to-HMI read of a real `OutImm.Curve` is not exercised.
- The test runtime is left in Run with the PressTests application stopped.
