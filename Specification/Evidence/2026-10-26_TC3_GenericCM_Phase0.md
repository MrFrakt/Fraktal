# Generic control-module expansion, Phase 0 — 2026-10-26

Working source: branch `feature/generic-cm-phase0` on `main` `a1163c7c7` (first commit
`2624e4d5f`). Core **0.26.0.0**, Modules **0.12.0.0**. Every artifact below is bound by
SHA-256 in [the receipt](2026-10-26_TC3_GenericCM_Phase0.json), together with the
changed sources.

## What was implemented

- **Analog channel unit as a code** (IMPLEMENTATION_NOTES §164, Part I §10.5.1,
  HMI_CONTRACT): `ST_IoChannel.UnitCode`, manifest-only; the legacy `Unit` text derived
  from it; a catalog that gives one channel both a code and a text is refused as a
  mapping defect. The HMI renders its own translated symbol through one shared rule.
- **Digital-input debounce at the source** (§165): `ST_DigitalInputParCfg` v2
  `DebounceTime`; bad quality and an unhonourable `ParCfg` publish an invalid input.
- **Read-surface gate**: the AB absence of `UnitCode` is declared, and the gate's
  staleness check now judges a fieldbus entry against the fieldbus surface.

## Passed on the final source

- Both PLC lint profiles (426 files), 79 TC3 tool tests (one skip), strict consistency
  (0 errors, 0 warnings) and its 36 tests — `…_CheapGates.log`.
- Core then Modules saved and installed from an isolated worktree through
  **TcXaeShell.DTE.15.0** in 32-bit PowerShell (Debug, TwinCAT RT (x86)); the installer
  aborts on a failed object check — `…_LibraryInstall.log`.
- Six `CheckAllObjects` solutions through **VisualStudio.DTE.18.0** (Debug, TwinCAT OS
  (x64)) — FraktalCore, FraktalModules, PressDemo, CoreDemo, FraktalTests, PressTests:
  `CheckAllObjects=True`, Error List empty, "0 errors, 0 warnings" each.
- On the isolated **UmRT_Default 192.168.1.6.1.1:851** (Autostart off, started by
  `Invoke-TwinCatTcUnitGate.ps1 -StartBootProjectWithAds`): aggregate **243/243 in 49
  suites** (`PRG_TcUnitRunner`, 20:28:36), including the five new `InputModuleTests` rows
  and the three new `IoTopologyTests` rows; Press **9/9 in 2 suites**
  (`PRG_PressTestRunner`, 20:30:20) in the shipped Ladder AUTO rendition. Both validated
  by `tcunit_to_junit.py`.
- HMI: `flutter analyze` clean; `flutter test` **622 passed, 12 skipped**, including the
  new `channel_unit_code_test.dart` (mapper, and the channel row in all 14 themes).

## Failed attempt, retained

The first aggregate run compiled, activated `Fraktal_Tests` and restarted the runtime,
which refused Run: *License Violation: License 'TC3 PLC' not found, Requested by
'Fraktal_Tests Instance'*. The runtime's `TrialLicense.tclrs` had been issued
2026-10-05T19:10 and expired 2026-10-13T00:00. The hidden XAE stopped on a modal
"Target system reports a fatal error"; once it was dismissed the gate exited through its
own cleanup ("ADS port 851 never answered after activation", `.tsproj` restored) —
`…_TcUnitAggregate_LicenceBlocked.log`, `…_RuntimeLicenceEvents.log`. The owner renewed
the trial (captcha; new file valid to 2026-11-04T00:00) and both gates were rerun
unchanged.

## Not executed, and why

- **The pinned Flutter SDK.** Only Flutter **3.44.6** is installed on this host; the
  3.47.x pin is absent. `flutter pub get --enforce-lockfile` refuses the committed lock
  on 3.44.6 (it would change five SDK-pinned packages), so analyze/test ran on the
  existing package resolution. `pubspec.lock` is byte-for-byte unchanged.
- Full offline Press builds (x86/x64 code generation and memory figures), the Press ST
  and SFC AUTO renditions (no sequence code changed), and any machine controller. The
  Press bench has no analog channel with a unit and no debounced input, so both features
  are proven by the test rows only.
- The test runtime is left in Run with the PressTests application stopped, as the
  owner's standing instruction for this runtime allows.
