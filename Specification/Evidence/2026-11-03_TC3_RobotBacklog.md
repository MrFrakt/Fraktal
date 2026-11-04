# Robot backlog R2/R3/R5/R7 — 2026-11-03

Working source: branch `feature/generic-cm-phase0` on `fe47a03da` (robot completion). Core
**0.26.7.0** (generated reason catalog only), Modules **0.17.0.0**. Every artifact below is
bound by SHA-256 in [the receipt](2026-11-03_TC3_RobotBacklog.json), together with the
changed sources.

## What was implemented

Four items of the robot backlog in the generic-CM audit plan (§12), IMPLEMENTATION_NOTES §175:

- **R2 capabilities.** `I_RobotConnector.Capabilities` (`ST_RobotCapabilities`): the connected
  controller's offered commands, jog axes and user-signal slots, published read-only in
  `OutImm.Capabilities`. `FB_RobotCM` refuses an unoffered command before anything is sent and
  bounds jog axes and user signals by them; an unreported set filters nothing. The TCP connector
  asks `CAP` once per session. Not done: hiding an unoffered command in the HMI — the catalog is
  static, manifest-served configuration (§3.9, §3.10.2).
- **R3 the controller's routines**, on the secondary `I_RobotRoutines` that Annex I.5b requires
  for a capability group: brake test and safe reference run, their demands as state flags,
  `BRAKE_TEST`/`SAFE_REFERENCE` one press each, passed only when the demand is withdrawn, else
  `ROBOT_ROUTINE_FAILED` (10317, HIGH, SAFETY, never shelvable).
- **R5 untaught points.** `ROBOT_POINT_UNKNOWN` (10302) raised: the CM refuses a missing ID before
  sending, the controller an untaught one (the simulation holds `1..TaughtPoints`; the TCP
  connector classifies `UNKNOWN_ID`).
- **R7 declared manual moves.** `M_DeclareManualMove(Slot, PointId, LabelKey)`, up to 8, in the
  catalog; one press runs `MOVE_FROM_AREA` to the point at `ParCfg.SpeedScaleMin` through every
  program gate.
- Annex I, the Part I registry row, the reason rationalization (94 → 96 in the catalog), English
  and Spanish operator text, the audit plan (new D9, backlog dispositions), Siemens plan and AB
  census rows.

## Defect found while doing it, and fixed

**The TCP connector could still refuse the move.** §174's one-deep queue covered a free slot,
but when the heartbeat's status poll (or now the link-up `CAP`) held the slot at the very scan
the CM sends the speed and the move, the speed took the only waiting place and the move was
refused as a lost link, intermittently. The queue is now two deep, oldest first, and a request
joins it whenever others wait. Row `Speed_then_move_in_one_scan_both_reach_the_wire` now runs
with `CAP` on the wire.

## Incidents on the way

- Object checks, run 1: `FraktalTests` failed with five `C0002` errors, all in the new test
  rows — an apostrophe inside an IEC string was written `''` instead of `$'`. Fixed in the test
  messages. Logs kept: `…_ObjectChecks_Run1_Failed.log` and its `FraktalTests` transcript.
- Object checks, run 2: all six passed, but `Fraktal_Modules` and `Fraktal_Tests` reported two
  `C0195` warnings (an untyped literal in the TCP connector's `_due AND 1`); the build must be
  warning-clean. A first fix with `DINT#` literals failed the library install with `C0032`
  (bitwise `AND` needs `ANY_BIT`); the status field is now a `DWORD`, the repository's idiom.
  Logs kept: `…_ObjectChecks_Run2_Warnings.log`, `…_LibraryInstall_Run2_Failed.log`.
- Runtime gate: the UmRT trial licence lapsed at 18:00 local (its `ExpireTime`
  `2026-11-04T00:00:00` is UTC). Activation at 19:15 stopped on *'TwinCAT System' (10000): license
  not found*; the hidden XAE instance the gate had opened was closed. Renewal is an interactive
  step for the owner and was not automated. Log kept: `…_TcUnitAggregate_LicenceLapsed.log`.

## Passed on the final source

- Both PLC lint profiles (468 files), 79 TC3 tool tests (one skip), strict consistency
  (0/0), the 85 repository gate tests, both AB gates, the TIA candidate-contract gate
  (plain and `--generated`), `tia_lint`, the TIA generator, examples and I/O-bridge
  replays (examples refreshed for the two rationalized severities), 271 Siemens tool tests
  and the reason-catalog generator check — `…_CheapGates.log`, rerun on the final source.
- Core 0.26.7.0 and Modules 0.17.0.0 saved and installed from the isolated worktree
  (TcXaeShell.DTE.15.0, 32-bit PowerShell, Debug, TwinCAT RT (x86)) — `…_LibraryInstall.log`.
- Six `CheckAllObjects` solutions: 0 errors, 0 warnings each — `…_ObjectChecks.log` and one
  transcript per solution.
- On the isolated **UmRT_Default 192.168.1.6.1.1:851** (Autostart off, ADS Run start), after
  the owner renewed the trial licence: aggregate **353/353 in 54 suites** (23:33:00), all 26
  `RobotCmTests` and 11 `RobotConnectorTests` rows; Press **9/9 in 2 suites** (23:34:35). Both
  validated by `tcunit_to_junit.py`.
- HMI: analyzer clean, **628 passed / 12 skipped** on Flutter 3.44.6 (the regenerated catalog and
  its count pin), `pubspec.lock` unchanged.

## Not executed, and why

- No real robot or controller emulator: the CM is proven against the simulated connector, the
  TCP connector against a scripted byte channel. The server side of `CAP`, `BRK`, `SRF`, the
  `<due>` status field and the `UNKNOWN_ID` code is specified in the connector and Annex I but
  has no server in this repository.
- Hiding an unoffered command in the HMI (R2's last clause) is not done; see above.
- No connector without `I_RobotRoutines` exists to prove the "not offered" path for the routines;
  the path is a single guarded branch in `_M_Offered`.
- No station instantiates a robot (owner waiver 2026-10-29, plan D2).
- The test runtime is left in Run with the PressTests application stopped.
