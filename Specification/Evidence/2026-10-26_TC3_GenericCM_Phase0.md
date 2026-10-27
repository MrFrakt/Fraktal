# Generic control-module expansion, Phase 0 — 2026-10-26

Working source: branch `feature/generic-cm-phase0` on `main` `a1163c7c7`. Core
**0.26.0.0**, Modules **0.12.0.0**. Every artifact below is bound by SHA-256 in
[the receipt](2026-10-26_TC3_GenericCM_Phase0.json), together with the changed sources.

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
- HMI: `flutter analyze` clean; `flutter test` **622 passed, 12 skipped**, including the
  new `channel_unit_code_test.dart` (mapper, and the channel row in all 14 themes).

## Not executed, and why

- **Both TcUnit runtime gates.** The aggregate gate compiled, activated
  `Fraktal_Tests` on the isolated **UmRT_Default 192.168.1.6.1.1** and restarted it,
  and the runtime refused Run: *License Violation: License 'TC3 PLC' not found,
  Requested by 'Fraktal_Tests Instance'*. The runtime's `TrialLicense.tclrs` was issued
  2026-10-05T19:10 and expired **2026-10-13T00:00**. Renewal is an interactive captcha
  (CI_RUNTIME_GATE_RUNBOOK §B1), so no unattended route exists. The gate exited through
  its own cleanup ("ADS port 851 never answered after activation", `.tsproj`
  restored) after XAE's modal "Target system reports a fatal error" was dismissed; the
  runtime is left in Config with no application. The new rows — five in
  `FB_InputCM_Tests`, three in `FB_IoTopologyPublisher_Tests` (243 tests / 49 suites
  expected) — and the Press gate are therefore **compiled, not executed**. Logs:
  `…_TcUnitAggregate_LicenceBlocked.log`, `…_RuntimeLicenceEvents.log`.
- **The pinned Flutter SDK.** Only Flutter **3.44.6** is installed on this host; the
  3.47.x pin is absent. `flutter pub get --enforce-lockfile` refuses the committed lock
  on 3.44.6 (it would change five SDK-pinned packages), so analyze/test ran on the
  existing package resolution. `pubspec.lock` is byte-for-byte unchanged.
- Full offline Press builds (x86/x64 code generation and memory figures), the Press ST
  and SFC renditions, and any machine controller. The Press bench has no analog channel
  with a unit and no debounced input, so both features are proven by the test rows only.
