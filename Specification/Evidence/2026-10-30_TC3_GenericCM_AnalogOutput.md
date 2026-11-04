# Generic control-module expansion, L2 — 2026-10-30

Working source: branch `feature/generic-cm-phase0` on `b2e6164c5` (L1). Core **0.26.3.0**
(generated reason catalog only), Modules **0.13.2.0**. Every artifact below is bound by
SHA-256 in [the receipt](2026-10-30_TC3_GenericCM_AnalogOutput.json), together with the
changed sources.

## What was implemented

- **`FB_AnalogOutputCM`** (IMPLEMENTATION_NOTES §169): one command, `SET`, driving the
  channel to a bounded, release-gated target that stays applied until the next `SET`.
  Whatever state nobody stands behind drives `SafeValue`: before the first `SET`, while
  an interlock withholds it (§6.1 HELD during the command; **no self-resume** after Done,
  §9.3 — only `RestoreOutputs` or a new `SET` re-applies), while withdrawn by the owner's
  functional stop, and after an abort. The operator's manual set point is retained
  station data with the band as bounds.
- Reasons `10801–10802` (`AO_TARGET_OOR`, `AO_CFG_INVALID`), rationalized; catalog 83 →
  85; operator text in English and Spanish; Part I §8.8 registry row; HMI `analogOutput`
  module symbol; AB census and TIA M13 parity rows; TIA regenerated for the
  `PL_ModuleReasons` hash.

## Passed on the final source

- Both PLC lint profiles (449 files), 79 TC3 tool tests (one skip), strict consistency
  (0/0), the 85 repository gate tests, both AB gates, the TIA candidate-contract gate
  and `tia_lint` — `…_CheapGates.log`.
- Core 0.26.3.0 and Modules 0.13.2.0 saved and installed from the isolated worktree
  (TcXaeShell.DTE.15.0, 32-bit PowerShell, Debug, TwinCAT RT (x86)) —
  `…_LibraryInstall.log`.
- Six `CheckAllObjects` solutions: 0 errors, 0 warnings each, **re-run after the
  test-row fixes** so the evidence matches the final source.
- On the isolated **UmRT_Default 192.168.1.6.1.1:851** (Autostart off, ADS Run start):
  aggregate **294/294 in 53 suites** (19:23:06), including the nine new
  `AnalogOutputTests` rows; Press **9/9 in 2 suites** (19:24:21). Both validated by
  `tcunit_to_junit.py`.
- HMI: analyzer clean, **622 passed / 12 skipped** on Flutter 3.44.6,
  `pubspec.lock` unchanged.

## Not executed, and why

- No station instantiates the type (owner waiver 2026-10-29, plan D2); consumers are the
  TcUnit suite and the generic HMI.
- The first aggregate run failed three rows — all test-authoring defects, recorded in
  the receipt's `runtime.incidents`; the FB needed no change. The passing runs are the
  final source.
- The test runtime is left in Run with the PressTests application stopped.
