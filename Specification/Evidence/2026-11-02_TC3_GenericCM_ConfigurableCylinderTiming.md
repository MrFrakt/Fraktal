# Generic control-module expansion, L4 — 2026-11-02

Working source: branch `feature/generic-cm-phase0` on `229322079` (L3). Core **0.26.4.0**
(unchanged), Modules **0.15.0.0**. Every artifact below is bound by SHA-256 in
[the receipt](2026-11-02_TC3_GenericCM_ConfigurableCylinderTiming.json), together with
the changed sources.

## What was implemented

- **`FB_ConfigurableCylinderCM` adopts the valve timing** (IMPLEMENTATION_NOTES §171):
  `ParCfg` v2 (`MinOutputTime`, `PulsingWidth`, `PulsingPeriod`, `ResetOnEndPos`,
  `ResetOnTimeout`), driven through the shared `FB_ValveDrive` exactly as
  `FB_CylinderCM`: pulsing only for a move from the sensed middle, Done after settle and
  minimum output time, end-of-move and timeout reset policies.
- `PrepareRecipe` refuses (`CYL_CFG_INVALID`) an unhonourable minimum output time, a
  pulse as long as its period, `ResetOnEndPos` on a single-acting cylinder, and pulsing
  without a sensor on both positions.
- Found while adopting it and fixed: a refused prepare could leave an earlier prepare's
  "prepared" mark over the refused record, so a later commit would have applied it.
- Siemens plan and AB census record the layout as not carried.

## Passed on the final source

- Both PLC lint profiles (453 files), 79 TC3 tool tests (one skip), strict consistency
  (0/0), the 85 repository gate tests, both AB gates, the TIA candidate-contract gate
  (plain and `--generated`), `tia_lint`, the TIA generator, examples and I/O-bridge
  replays, 271 Siemens tool tests and the reason-catalog generator check —
  `…_CheapGates.log`.
- Core 0.26.4.0 and Modules 0.15.0.0 saved and installed from the isolated worktree
  (TcXaeShell.DTE.15.0, 32-bit PowerShell, Debug, TwinCAT RT (x86)) —
  `…_LibraryInstall.log`.
- Six `CheckAllObjects` solutions: 0 errors, 0 warnings each.
- On the isolated **UmRT_Default 192.168.1.6.1.1:851** (Autostart off, ADS Run start):
  aggregate **317/317 in 53 suites** (16:21:00), all twelve `ConfigurableCylinderTests`
  rows; Press **9/9 in 2 suites** (16:22:30). Both validated by `tcunit_to_junit.py`.
- HMI: untouched by this package; not re-run.

## Not executed, and why

- No station instantiates the configurable cylinder with the new members (owner waiver
  2026-10-29, plan D2); the TcUnit suite is its consumer.
- The rows drive the sensors directly (no plant model), so a real valve's switching
  time is not measured; the timing is proven against the task clock.
- The test runtime is left in Run with the PressTests application stopped.
