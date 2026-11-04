# Generic control-module expansion, Phase 1 — 2026-10-26

Working source: branch `feature/generic-cm-phase0` on `551984af7` (Phase 0). Core
**0.26.0.0** (unchanged), Modules **0.13.0.0**. Every artifact below is bound by SHA-256 in
[the receipt](2026-10-26_TC3_GenericCM_Phase1.json), together with the changed sources.

## What was implemented

- **Cylinder valve timing** (IMPLEMENTATION_NOTES §166, Annex B): `ST_CylinderParCfg` v2 —
  `SettleTime`, `MinOutputTime`, `PulsingWidth`/`PulsingPeriod` (a move that starts from no
  end position pulses until its target makes), `ResetOnEndPos`, `ResetOnTimeout`; every
  default reproduces v1. Invalid timing is refused at prepare with `CYL_CFG_INVALID`.
- **`FB_ValveDrive`**, the owner-private timing helper, and a withdrawal latch so a pulsed
  move can never undo an owner's `WithdrawOutputs`.

## Passed on the final source

- Both PLC lint profiles (429 files), 79 TC3 tool tests (one skip), strict consistency
  (0 errors, 0 warnings) and its 36 tests — `…_CheapGates.log`.
- Modules saved and installed from the isolated worktree through **TcXaeShell.DTE.15.0**
  in 32-bit PowerShell (Debug, TwinCAT RT (x86)); Core 0.26.0.0 was already installed —
  `…_LibraryInstall.log`.
- Six `CheckAllObjects` solutions through **VisualStudio.DTE.18.0** (Debug, TwinCAT OS
  (x64)): `CheckAllObjects=True` and "0 errors, 0 warnings" each. FraktalTests, PressDemo
  and PressTests each list one Error List row, XAE's *Unknown TMC file version found -
  ignoring the file* for the TMC an earlier activation regenerated; it is not a compile
  diagnostic and is recorded verbatim in their logs.
- On the isolated **UmRT_Default 192.168.1.6.1.1:851** (Autostart off, ADS Run start):
  aggregate **260/260 in 50 suites** (`PRG_TcUnitRunner`, 23:49:02), including the thirteen
  new `CylinderTests` rows, the restamped T5 and the four `ValveDriveTests` rows; Press
  **9/9 in 2 suites** (`PRG_PressTestRunner`, 23:50:28) in the shipped Ladder AUTO
  rendition, whose ram, door and part slide are `FB_CylinderCM` and whose fault-recovery
  row withdraws and restores the ram. Both validated by `tcunit_to_junit.py`.

## Not executed, and why

- The HMI suite: no HMI code changed, and the HMI renders the cylinder's published
  `ParCfg` generically (nothing mirrors its members), so there was nothing new to run.
- Full offline Press builds, the Press ST and SFC AUTO renditions (no sequence code
  changed), and any machine controller. No Press cylinder sets a valve-timing member, so
  the new behaviour is proven by the test rows only.
- The test runtime is left in Run with the PressTests application stopped.
