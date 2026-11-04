# Robot CM completion — 2026-11-03

Working source: branch `feature/generic-cm-phase0` on `bf79fdd78` (L8). Core **0.26.6.0**
(generated reason catalog only), Modules **0.16.0.0**. Every artifact below is bound by
SHA-256 in [the receipt](2026-11-03_TC3_RobotCompletion.json), together with the changed
sources.

## What was implemented

- **`FB_RobotCM` completed** (IMPLEMENTATION_NOTES §174), closing the robot user-channel audit:
  the mode request half (`REQUEST_MODE`, default most restrictive mode at link-up and on loss of
  report, `OutImm.RequestedMode`), configuration validation (`ROBOT_CFG_INVALID` 10316), the §9
  safety alias (`SetSafetyPermit`, `ROBOT_SAFETY_DROPPED` 10307), held jog (`JOG_POS`/`JOG_NEG`)
  gated by the reported manual mode, the enabling device, freshness, interlocks and the alias,
  `SET_PAYLOAD`, the arm-power fact, path progress for a deliberate continue after an abort, and
  a declared user-signal channel.
- `I_RobotConnector` gains `ArmPowerOn`, `PathIndex`, `WriteUserSignal`, `UserSignal`; both
  connectors implement them. The TCP connector carries user outputs on its status poll and reads
  power, path index and inputs from appended reply fields.
- Annex I brought into line with the shipped type; reasons rationalized and catalogued
  (92 → 94); operator text in English and Spanish; registry row; Siemens plan and AB census rows.
- Ideas from a commercial robot-integration package were reviewed: path progress adopted; the
  rest are dispositioned in the generic-CM audit plan (§12), written in the same change:
  `Specification/Reports/TC3_GENERIC_CM_AUDIT_PLAN_2026-11-03.md`.

## Defects found while finishing, and fixed

1. **Abort did not stop the arm** — no `OnAbort`; the module reported ABORTED while the robot
   moved. Now `OnAbort` sends `Abort`. Row `Aborting_a_command_stops_the_arm`.
2. **Refusal adoption against a stale snapshot** — an accepted command after a refused one
   faulted with a zero code; a repeated refusal read as "unsupported command". `LastResult` is
   now per request (I.3). Row `A_repeated_refusal_keeps_its_own_reason_and_a_success_follows`.
3. **The TCP connector could never run a move** — speed and move are sent in one scan and the
   link allowed one outstanding request, so the move was refused as a lost link (the heartbeat
   caused the same intermittently). One-deep queue, `Abort` empties it first; every refusal now
   leaves a reason. Row `Speed_then_move_in_one_scan_both_reach_the_wire`.

## Passed on the final source

- Both PLC lint profiles (466 files), 79 TC3 tool tests (one skip), strict consistency
  (0/0), the 85 repository gate tests, both AB gates, the TIA candidate-contract gate
  (plain and `--generated`), `tia_lint`, the TIA generator, examples and I/O-bridge
  replays, 271 Siemens tool tests and the reason-catalog generator check —
  `…_CheapGates.log`.
- Core 0.26.6.0 and Modules 0.16.0.0 saved and installed from the isolated worktree
  (TcXaeShell.DTE.15.0, 32-bit PowerShell, Debug, TwinCAT RT (x86)) — `…_LibraryInstall.log`.
- Six `CheckAllObjects` solutions: 0 errors, 0 warnings each.
- On the isolated **UmRT_Default 192.168.1.6.1.1:851** (Autostart off, ADS Run start):
  aggregate **346/346 in 54 suites** (08:11:44), all 21 `RobotCmTests` and 9
  `RobotConnectorTests` rows; Press **9/9 in 2 suites** (08:13:16). Both validated by
  `tcunit_to_junit.py`. Every gate passed on its first run.
- HMI: analyzer clean, **628 passed / 12 skipped** on Flutter 3.44.6 (the regenerated
  catalog and its count pin), `pubspec.lock` unchanged.

## Not executed, and why

- No real robot or controller emulator: the CM is proven against the simulated connector, the
  TCP connector against a scripted byte channel. The server side of the wire protocol (status
  fields 15+, user outputs on the poll, `JOG` stopped by `ABT`) is specified in the connector and
  in Annex I but has no server in this repository to test against.
- The simulated path progress is synthetic (a whole list is ten points).
- The bounded vision offset (Annex I.8a) stays deferred; the route preview Annex I.15 requires is
  not built and is recorded in the audit plan (R10).
- No station instantiates a robot (owner waiver 2026-10-29, plan D2).
- The test runtime is left in Run with the PressTests application stopped.
