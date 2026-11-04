# Generic control-module expansion, WP5.1 NOK-part limit — 2026-10-27

Working source: branch `feature/generic-cm-phase0` on `27f52f1df`. Core **0.26.1.0**,
Modules **0.13.0.1** (rebuild only). Every artifact below is bound by SHA-256 in
[the receipt](2026-10-27_TC3_GenericCM_NokPolicy.json), together with the changed sources.

## What was implemented

- **`FB_UnitBase.SetNokPolicy`** (IMPLEMENTATION_NOTES §167, Part I §3.16.5): NOK parts in
  a row and/or NOK among the last N judged parts, counted on `CountGood`/`CountNok`. A trip
  is one `NOK_LIMIT_REACHED` (2028) `MANUAL_RESET` event — Start refused through the
  existing blocking-alarm release record — and a running Unit finishes its cycle at its
  stop point. One operator reset re-arms both rules.
- §8.9 rationalization, regenerated reason catalogs (PLC and HMI), operator text in
  English and Spanish; the Press bench sets 3 in a row or 5 of the last 20.
- **TIA candidate contract V2**, reviewed by the owner: V1 plus `E_Reason.NOK_LIMIT_REACHED`;
  V1 kept byte for byte; the checker now requires every earlier baseline preserved and
  bound in Part IV. TIA packages regenerated.

## Passed on the final source

- Both PLC lint profiles (431 files), the TC3 tool tests (one skip), strict consistency
  and the repository gate tests; `generate_reason_catalog.dart --check`;
  `check_ab_spec`, `check_ab_contracts`; `check_tia_contracts` against V2, plain and
  `--generated` (31); `tia_lint`; both TIA `--verify` replays and the I/O bridge replay;
  271 Siemens tool tests — `…_CrossBinding.log`.
- Core then Modules installed through **TcXaeShell.DTE.15.0** in 32-bit PowerShell —
  `…_LibraryInstall.log`.
- Six `CheckAllObjects` solutions through **VisualStudio.DTE.18.0**: `True`, "0 errors,
  0 warnings" each; FraktalTests, PressDemo and PressTests each list XAE's *Unknown TMC
  file version found* row, not a compile diagnostic.
- On the isolated **UmRT_Default 192.168.1.6.1.1:851** (Autostart off, ADS Run start):
  aggregate **269/269 in 51 suites** (01:07:46), including all nine `NokPolicyTests`
  rows; Press **9/9 in 2 suites** (01:09:36, Ladder AUTO; the PressTests composition sets
  no policy). Both validated by `tcunit_to_junit.py`.
- HMI on Flutter 3.44.6 (the 3.47.x pin is not installed; lock unchanged): analyzer
  clean, **622 passed, 12 skipped** — `…_HmiTest.log`.

## Not executed, and why

- The Press bench's own policy (`MAIN`) runs on no runtime here: it compiles in PressDemo,
  and the rule itself is proven by the nine TcUnit rows.
- Native TIA import of the regenerated package; no TIA or AB Unit implements the limit
  (both record the gap).
- The AB tool unit tests show the same eight native-connection errors with and without
  this change; they are not a CI gate.
- The test runtime is left in Run with the PressTests application stopped.
