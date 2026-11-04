# Generic control-module expansion, L5 — 2026-11-02

Working source: branch `feature/generic-cm-phase0` on `0bb7eff28` (L4). Core **0.26.5.0**
(generated reason catalog only), Modules **0.15.1.0**. Every artifact below is bound by
SHA-256 in [the receipt](2026-11-02_TC3_GenericCM_CurveMonitor.json), together with the
changed sources.

## What was implemented

- **`FB_CurveMonitor`** (IMPLEMENTATION_NOTES §172): an owner-private helper that judges
  one measured curve online against windows (entry/exit edges) and upper/lower envelopes,
  decides completeness and returns a verdict naming the first failing rule, with its
  operator text. It raises nothing itself.
- Types `ST_CurvePoint`, `E_CurveEdge`, `ST_CurveWindow`, `ST_CurveEnvelope`,
  `ST_CurveSpec`, `ST_CurveResult`, sizing in `PL_Curve`.
- Reasons `10901–10904` (`CURVE_WINDOW_VIOLATED`, `CURVE_ENVELOPE_VIOLATED`,
  `CURVE_INCOMPLETE`, `CURVE_SPEC_INVALID`), rationalized; catalog 88 → 92; operator
  text in English and Spanish; Part I §8.8 registry row; AB census and Siemens plan
  rows; TIA regenerated for the `PL_ModuleReasons` hash.
- Lint rule C2 now rejects the IEC generic types (`ANY`, `ANY_INT`, …) as identifiers,
  with a test (see below).

## Found by the gates and fixed before commit

1. Lint C2 rejected the plan's window member `Exit` (reserved) and a local `limit`
   (standard function): renamed `EntryEdge`/`ExitEdge` and `bound`.
2. The first library install failed: XAE rejected the enum member `ANY` (IEC's
   generic-type keyword; C0368 on the declaration, C0004 at every use) —
   `…_LibraryInstall_FirstRunRejected.log`, `…_ModulesDiagnosis_FirstRun.log`. Renamed
   `ANY_EDGE`; C2 did not know the generic types, so it now does.

## Passed on the final source

- Both PLC lint profiles (462 files), 79 TC3 tool tests (one skip), strict consistency
  (0/0), the 85 repository gate tests, both AB gates, the TIA candidate-contract gate
  (plain and `--generated`), `tia_lint`, the TIA generator, examples and I/O-bridge
  replays, 271 Siemens tool tests and the reason-catalog generator check —
  `…_CheapGates.log`.
- Core 0.26.5.0 and Modules 0.15.1.0 saved and installed from the isolated worktree
  (TcXaeShell.DTE.15.0, 32-bit PowerShell, Debug, TwinCAT RT (x86)) —
  `…_LibraryInstall.log`.
- Six `CheckAllObjects` solutions: 0 errors, 0 warnings each.
- On the isolated **UmRT_Default 192.168.1.6.1.1:851** (Autostart off, ADS Run start):
  aggregate **328/328 in 54 suites** (16:45:53), all eleven `CurveMonitorTests` rows;
  Press **9/9 in 2 suites** (16:47:28). Both validated by `tcunit_to_junit.py`.
- HMI: analyzer clean, **622 passed / 12 skipped** on Flutter 3.44.6 (the regenerated
  catalog and its count pin), `pubspec.lock` unchanged.

## Not executed, and why

- No library type owns a curve yet (owner waiver 2026-10-29, plan D2): the helper is
  proven by its own suite; an owner's fault or part-verdict path is not exercised.
- The test runtime is left in Run with the PressTests application stopped.
