# Generic control-module expansion, L1 — 2026-10-30

Working source: branch `feature/generic-cm-phase0` on `79701b157` (the remaining-work
plan). Core **0.26.2.0** (generated reason catalog only), Modules **0.13.1.0**. Every
artifact below is bound by SHA-256 in
[the receipt](2026-10-30_TC3_GenericCM_AnalogInput.json), together with the changed
sources.

## What was implemented

- **`FB_AnalogInputCM`** (IMPLEMENTATION_NOTES §168): one type covering a plain analog
  signal, a measuring sensor and a scale — linear scaling (inverted ranges included), a
  two-point adjustment and tare as retained station data, a first-order filter, an
  in-range judgement and a stability-banded `MEASURE` with timeout. Bad quality or an
  implausible adjustment publishes `Valid` FALSE and `Value` 0 — never the last good
  value. Reasons `10701–10705` registered (§8.8), rationalized, catalogued 78 → 83,
  operator text in English and Spanish; the HMI gains the `analogInput` module symbol.
- **Two tooling fixes bought by the runtime gate**, both recorded in §168: the TcUnit
  gate's `Set-AdsPlcState` now re-issues a Run request swallowed while the boot
  application loads, and the CM's plausibility call is guarded by its own IF because
  IEC AND does not short-circuit (the unguarded form divided 0/0 and halted the PLC
  task with FPU exception 0xc0000090).

## Passed on the final source

- Both PLC lint profiles (440 files), 79 TC3 tool tests (one skip), strict consistency
  (0 errors, 0 warnings), the 85 repository gate tests, both AB gates, the TIA
  candidate-contract gate and `tia_lint` — `…_CheapGates.log`. TIA regenerated for the
  `PL_ModuleReasons` hash; both packages verify.
- Core 0.26.2.0 and Modules 0.13.1.0 saved and installed from the isolated worktree
  through **TcXaeShell.DTE.15.0** in 32-bit PowerShell (Debug, TwinCAT RT (x86));
  Modules reinstalled after the FPU-guard fix — `…_LibraryInstall.log`.
- Six `CheckAllObjects` solutions through **VisualStudio.DTE.18.0** (Debug, TwinCAT OS
  (x64)): `CheckAllObjects=True` and "0 errors, 0 warnings" each, re-run on the final
  source. PressTests lists one Error List row, XAE's *Unknown TMC file version found -
  ignoring the file*; it is not a compile diagnostic and is recorded verbatim.
- On the isolated **UmRT_Default 192.168.1.6.1.1:851** (Autostart off, ADS Run start):
  aggregate **285/285 in 52 suites** (`PRG_TcUnitRunner`, 01:26:20), including the
  sixteen new `AnalogInputTests` rows; Press **9/9 in 2 suites**
  (`PRG_PressTestRunner`, 09:08:19). Both validated by `tcunit_to_junit.py`.
- HMI: analyzer clean, **622 passed / 12 skipped** on Flutter 3.44.6 with
  `pubspec.lock` unchanged (lock unenforced on this SDK, recorded per plan §1.3).

## Not executed, and why

- No station instantiates the type (owner waiver 2026-10-29, plan D2); consumers are
  the TcUnit suite and the generic HMI.
- The first two aggregate attempts and the first press attempt failed before the fixes
  above; the incidents and their diagnosis are recorded in the receipt's
  `runtime.incidents`. The passing runs are the final source, re-installed and
  re-checked end to end.
- The test runtime is left in Run with the PressTests application stopped.
