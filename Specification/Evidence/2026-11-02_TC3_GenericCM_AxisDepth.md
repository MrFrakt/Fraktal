# Generic control-module expansion, L3 — 2026-11-02

Working source: branch `feature/generic-cm-phase0` on `031c0ca83` (L2). Core **0.26.4.0**
(generated reason catalog only), Modules **0.14.0.0**. Every artifact below is bound by
SHA-256 in [the receipt](2026-11-02_TC3_GenericCM_AxisDepth.json), together with the
changed sources.

## What was implemented

- **Axis depth** (IMPLEMENTATION_NOTES §170) on `FB_AxisCM`: declared named positions
  in a second retained image (`ST_AxisTeachCfg`), each an editable value with a capture;
  `ParCmd.PositionIdx` target selection; `MOVE_REL` and manual `STEP_POS`/`STEP_NEG` on
  `MC_MoveRelative`; a validated speed-scale band (`ST_AxisParCfg` v2) and a set-and-hold
  override published as `OutImm.Override`.
- Reasons `10207–10209` (`AXIS_POSITION_UNDECLARED`, `AXIS_PARAM_OOR`,
  `AXIS_CFG_INVALID`), rationalized; catalog 85 → 88; operator text in English and
  Spanish; Part I §8.8 registry row and Annex G; AB census and TIA rows; TIA packages
  regenerated for the `PL_ModuleReasons` hash.
- Unrelated HMI fix carried in the same change: the Shifts card header no longer
  overflows at narrow widths (`facet_cards.dart`).

## Found in review and fixed before commit

The package arrived from a previous session uncommitted. Review found four defects:

1. `_M_MoveRel` re-judged `ActPos + distance` every scan, so a legal relative move would
   have faulted halfway. The distance is now resolved and judged once and latched.
   **Reasoned, not runtime-proven**: no row can reach the moving step without an NC axis.
2. Index resolution and `M_DeclarePosition` used plain `AND`/`OR` around an array read,
   so an out-of-range index still read past the array. Now `AND_THEN`/`OR_ELSE`.
3. Seven `FB_Axis_Tests` rows shared an instance that was never set up, so they never
   started. The first aggregate run (`…_TcUnitAggregate_FirstRunStalled.log`, raw log
   `…_Aggregate_FirstRun_145241.raw.log`) never reached `AllTestSuitesFinished`: TcUnit's
   result print stopped after suite 32, just before `AxisTests`. The previous session's
   2026-10-31 attempts stopped at the same suite. Two rows also used a `Setup` result as
   their done mark, and the stored-v1 row passed on `Setup`'s own refusal (no valid default
   record).
4. In `FB_AxisJog_Tests` the out-of-range and empty-label refusals were behind a flag the
   previous row always set, so they never ran. That row now has its own instance.

## Passed on the final source

- Both PLC lint profiles (452 files), 79 TC3 tool tests (one skip), strict consistency
  (0/0), the 85 repository gate tests, both AB gates, the TIA candidate-contract gate
  (plain and `--generated`), `tia_lint`, the TIA generator, examples and I/O-bridge
  replays, 271 Siemens tool tests and the reason-catalog generator check —
  `…_CheapGates.log`.
- Core 0.26.4.0 and Modules 0.14.0.0 saved and installed from the isolated worktree
  (TcXaeShell.DTE.15.0, 32-bit PowerShell, Debug, TwinCAT RT (x86)) —
  `…_LibraryInstall.log`.
- Six `CheckAllObjects` solutions: 0 errors, 0 warnings each, on the final source.
- On the isolated **UmRT_Default 192.168.1.6.1.1:851** (Autostart off, ADS Run start):
  aggregate **309/309 in 53 suites** (15:19:55), including all 27 `AxisTests` and
  `AxisJogTests` rows; Press **9/9 in 2 suites** (15:22:28). Both validated by `tcunit_to_junit.py`.
- HMI: analyzer clean, **622 passed / 12 skipped** on Flutter 3.44.6, `pubspec.lock`
  unchanged (lock unenforced on this SDK).

## Not executed, and why

- No NC PTP licence on this host: every axis row asserts behaviour before any `MC_*`
  call; the `MC_MoveRelative`/`MC_Power.Override` interaction, the latched relative
  distance and a running move under a changed override are unproven.
- No station instantiates the new members (owner waiver 2026-10-29, plan D2); consumers
  are the TcUnit suites and the generic HMI.
- The test runtime is left in Run with the PressTests application stopped.
