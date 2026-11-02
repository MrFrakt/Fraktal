# Robot user channel and §10.6 device facts audit (TC3), 2026-11-02

**Status:** paper audit, no code changed (L8 of
[the remaining-library plan](TC3_GENERIC_CM_LIBRARY_PLAN_2026-10-29.md)). It checks
`FB_RobotCM` and `I_RobotConnector` against the three device facts Part I §10.6 makes
mandatory for a robot CM (Annex I §I.4a), the on-path hold (§I.4b), and a user channel —
plain bit/integer/real signals exchanged with the robot program. Gaps name their owner;
**implementation waits for a station that needs it (plan decision D3)**, except where a
gap contradicts a claim the specification already makes (§3 below).

Sources (relative to `FraktalCore/PLC/TwinCAT/Framework/Fraktal_Modules/`): `FB_RobotCM`,
`Interfaces/I_RobotConnector`, `FB_SimRobotConnector`, the vendor connector, `DUTs/ST_Robot*`,
`DUTs/E_Robot*`, reasons in `Params/PL_ModuleReasons` (robot block 10301–10399). Tests:
`FB_RobotCM_Tests` (8 rows), `FB_RobotConnector_Tests` (6 rows).

## 1. The three mandatory facts and the hold

| Requirement (§10.6, Annex I) | Today | Verdict |
|---|---|---|
| **(i) Mode is a request/report pair** — the PLC requests a mode and publishes separately what the controller reports | `I_RobotConnector.RequestMode(Mode)` exists and both connectors implement it; `OutImm.ActualMode` publishes the report; nothing in `FB_RobotCM` ever calls `RequestMode`, and no requested mode is published | **Partial — the request half is missing at the CM** |
| (i) default to the most restrictive mode on start-up or loss of report | on link loss `OutImm.ActualMode := UNKNOWN`; `SpeedCeiling[UNKNOWN] = 0.0`; motion refused unless the report is `AUTO_REMOTE` | **Met for the report** (no request is ever made, so there is none to default) |
| (i) reject a command the reported mode does not permit | `ROBOT_MODE_NOT_PERMITTED` (10311) before motion; test `Mode_that_does_not_permit_motion_is_refused` | **Met** for automatic commands. The rule is "motion needs `AUTO_REMOTE`", so a manual-mode command (jog) has no CM path to be permitted by; jog exists only on the connector |
| **(ii) Speed is a bounded scale held as configuration**: per-mode ceiling and recipe scale compose as their minimum; out-of-band refused before motion | `MIN(SpeedCeiling[ActualMode], ParCmd.SpeedScale)` sent through `SetSpeedScale`; `ROBOT_PARAM_OOR` (10314) outside `SpeedScaleMin..Max`; `OutImm.SpeedScale` publishes the scale in force; test `Speed_scale_outside_its_band_is_refused_before_motion` | **Met at run time.** Gap: the band and the ceilings themselves are never validated — `FB_RobotCM` has no `PrepareRecipe`, so a non-positive or inverted band, or a ceiling above 100 %, is accepted silently (the axis CM refuses the same mistake with `AXIS_CFG_INVALID`, §170) |
| **(iii) A protective stop is not a safety function**: own reason, no automatic resume | `ROBOT_PROTECTIVE_STOP` (10313) through `_M_FaultStopped`, distinct from any §9 reason; a fault needs a deliberate reset; test `Protective_stop_aborts_with_its_own_reason` | **Met** |
| **Hold on path** (§I.4b): interrupt at hold onset, resume on release, refuse a resume after the arm left the path, publish resumability | `Interrupt` once at onset, `Resume` on release, `ROBOT_RESUME_INVALID` (10315) when `Resumable` is false; `OutImm.Resumable`; tests on both CM and connector | **Met** |
| Active load case *should* follow grip and release | `I_RobotConnector.SetPayload` exists; no `FB_RobotCM` command reaches it | **Gap (should)** |
| A handling application *shall* prove possession | an application/EM rule, not a CM one; no library handling EM exists | **Out of scope here** (lands with the first robot-handling EM) |

## 2. The user channel

**Today: none.** `I_RobotConnector` carries ID-addressed commands and reported facts; there
is no member for plain user signals (robot-program flags, a gripper sensor the robot reads,
a counter the robot keeps), and `FB_RobotCM` publishes none. Annex I already lists
"digital-signal counts" among the per-model facts a connector reads as data, but nothing
consumes them.

**Should it exist?** Yes, bounded, because without it every station adds the exchange in
project code next to the CM — the duplication §1.1 O1 forbids — and its signals are then
invisible to the generic HMI. But it is also the easiest back door around §10.6: a station
that sequences the robot through user bits ("bit 3 = go to pick") has rebuilt a motion
command surface with no validation, no mode check, no speed band and no hold. The shape
must make that hard:

| Decision | Proposal | Owner |
|---|---|---|
| What is exchanged | a **declared** set of named signals, each with a direction (to robot / from robot), a kind (BOOL/DINT/REAL) and a description key — declared by the composition root before `Setup`, like axis positions (`M_DeclarePosition`) and interlock conditions | `FB_RobotCM` (declaration, publication) |
| Transport | `I_RobotConnector` gains read/write of a user signal by index; the connector maps indices to the controller's own I/O or variables using its per-model facts | the connector (vendor-specific, behind the interface) |
| Publication | every signal read-only in `OutImm` (name, value, `Since`), so the generic HMI renders it without knowing the station; bounded by a `PL_` constant | `FB_RobotCM` |
| Writes | only through a CM method the owning EM/Unit calls; **never from the HMI** and never part of a motion command | `FB_RobotCM` |
| What it must not carry | positions, motion modes, speeds, "go" requests. Documented as a rule in Annex I; a signal is data a program step may read or report, never a command | Annex I (normative text) |

This is a **specification change first** (Annex I §I.3 adds the members; the SRCI mapping
table states that they are Fraktal's, with no SRCI equivalent asserted here) and an
implementation second, with a registered reason only if a refusal needs one.

## 3. A claim the specification makes that the code does not meet

Annex I ("What the reference implementation realizes") says `FB_RobotCM` "as shipped
realizes this section, I.4a and I.4b in full", and its table of specified-but-unbuilt items
lists only the offset envelope, `OutImm.ArmPowerOn` and `ROBOT_SAFETY_DROPPED`. The I.14
suite it describes includes
`RequestedMode_stays_visibly_ungranted_when_controller_does_not_grant_it`. The shipped CM
issues no mode request and publishes no requested mode, and that row is not in
`FB_RobotCM_Tests` (eight rows). One of two corrections is due, and it is the owner's
choice:

1. **Implement the request half** (recommended): a requested-mode input or command on
   `FB_RobotCM` that calls `RequestMode`, defaults to the most restrictive mode at start-up
   and on loss of report, and publishes `OutImm.RequestedMode` beside `ActualMode`; plus the
   named test row. Additive (Modules patch), no new reason (`ROBOT_MODE_NOT_PERMITTED`
   already covers a refused request).
2. **Correct the annex** to say the request half is the connector's and the CM publishes
   only the report — weaker, and it leaves every station to request the mode itself.

## 4. Smaller findings

- **Configuration validation (fact ii).** Add `PrepareRecipe` to `FB_RobotCM` refusing a
  non-positive or inverted `SpeedScaleMin..Max` band, a band above 100 %, and a
  `SpeedCeiling` entry outside 0..100, with a code from the free part of the robot block.
- **Manual-mode commands.** Jog lives on the connector only; a CM path for it would need the
  §7.6 enabling-device gate the axis CM already applies (`ST_ManualEnableStatus`), and the
  mode check then permits `MANUAL_REDUCED`/`MANUAL_HIGH` for jog only.
- **Load case.** A `SET_PAYLOAD` command by payload ID (taught data, like `SET_TOOL`) would
  let the handling EM keep the load case in step with grip and release.

## 5. Tests a change would add

`FB_RobotCM_Tests`: the requested mode published and visibly ungranted while the report
differs; the default request after link loss; an invalid speed band refused at prepare; a
declared user signal published read-only, written through the CM method, and refused for
an undeclared index; `SET_PAYLOAD` reaching the connector. `FB_RobotConnector_Tests`: user
signal round trip over the simulated connector.
