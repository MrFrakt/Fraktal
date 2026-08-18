# Annex I — Worked Example: Robot Control Module (Portable Teaching & Motion-Planning Abstraction)

*Companion to **Fraktal Core** (Part I) exercised through the **Fraktal/TC3** binding (Part II); slots under Core §12.*
*Core concepts demonstrated: robot as a CM with the connector contract (§10.6, §3.15) and the **declarative routing model now normative in Core §10.7** (promoted from §I.9–§I.10 here), area-resolved recovery distinct from safety (§9). / TC3 mechanics used: `OPC.UA.DA` pragmas (TC3 §3.10), validation against a TwinCAT application export.*
*Reference implementation — illustrative, not compile-tested; validate against the pinned TwinCAT version and your robot controller / teaching transport.*
*Validated against a portable-robot framework manual and a real TwinCAT application export (a plasma-clean handling cell). Where the reference framework forces per-station boilerplate — notably one help point per work position — this annex makes the general case **native and declarative** (I.10).*

A robot is not merely a multi-axis device that needs teaching from an HMI. The portable robot framework is a complete **motion-planning** layer that **generates trajectories** between positions at runtime, **plans through 3-D areas**, **generates whole symmetric pallets** from a few taught corners, and **chains reference frames**. The thesis of this annex: *all* of that is taught/generated **configuration (§3.8) addressed by ID* — so a whole robot drops into the standard as a **Control Module** behind the §6.1 handshake, a thin **handling Equipment Module** adds the station's semantic operations on top (I.6), and faults roll up the **same stall walk** (§6.9) as a cylinder.

It is the convergence of two earlier annexes plus a robot-specific planning layer:

- **Annex D** (`I_DeviceConnector`) — the robot controller is a networked smart device; the connector owns transport + heartbeat, link loss rolls up §6.9, bounded reconnect with no self-resume.
- **Annex G** (PLCopen motion CM) — motion behind the standard handshake (§6.1), validation before motion (§5.6), safe-stop on a dropped safety alias with no automatic re-enable (§9).
- **The planning layer** (this annex) — paths, generated trajectories, planning areas, parametric pallets and chained frames, **all configuration, all ID-addressed, none of it PLC code**.

```
InfeedUnit (FB_InfeedUnit : FB_Unit)                          ← Annex C
 ├─ ClampStation (FB_ClampEM → CylA, CylB)                    ← Annex B
 ├─ Carrier      (I_PartCarrier, injected — DMC reader)       ← Annex E (SCAN_PART)
 └─ RobotHandling (FB_RobotHandlingEM)                        ← semantic ops: PICK/PLACE/SCAN/PROCESS (I.6)
       └─ Robot130 (FB_RobotCM, Control Module)               ← primitive surface (here)
             └─ _conn (I_RobotConnector)                      ← session + heartbeat + path planning
                    ├─ DEFAULT: FB_PortableTeachConnector     (recommended, out-of-the-box, vendor-neutral)
                    └─ ALT:     FB_<Vendor>RobotConnector     (conformant escape hatch)
```

---

## I.1 The boundary — what stays *out* of the PLC

The defining rule: **everything geometric, kinematic, or routing-related is taught/generated configuration (§3.8) addressed by stable ID; the PLC carries an ID and waits on the handshake — never a coordinate, waypoint, motion mode, route, or help-point choice.**

| Lives in the robot controller (taught / **generated** configuration, §3.8) | Lives in the PLC (control **logic**) |
|---|---|
| Cartesian / joint coordinates of every point; computed **approach/retract pre-positions** | nothing — never a coordinate |
| **Motion mode per point** — Joints / PTP / Linear, absolute or blended | nothing — never chosen in code |
| Coordinate systems / **frames**, including **chained** frames (frame→frame→RCS) | which **frame ID** a command runs in |
| Tools (`Gripper1`, `Gripper2`); nests are **per-gripper** indexed | which **tool ID** / **gripper** is active |
| **Pallets** — grids **generated** from a few corners (1-D/2-D/3-D) | which **pallet ID** + which **nest index** |
| **Paths** — point-lists run sequentially; sub-paths by start/end index | which **list ID** (and optional sub-range) |
| **Routing model** — help/nest graph + **nest→help affinity** (I.9, I.10) | which **from**/**to** position (by ID) |
| **Generated trajectories** — route assembled from the routing model | nothing — the route is computed, not listed |
| **Planning areas** — 3-D zones for area-resolved motion & recovery | (in recovery) a **target position** to reach |
| Vendor config STRING; per-model facts (signal counts, Euler conventions) | nothing — consulted by the connector, never branched on |

**Where the database lives is not a free choice.** Points, frames, tools, pallets and areas
**should** be held as Fraktal configuration — bounded collection capabilities (§3.10.2a) in the
owning module — and pushed to the controller by the connector, rather than living only inside the
robot's own engineering tool. The rule that the PLC program holds *identifiers and never geometry*
is about **application code**; it says nothing about where the configuration is governed, and the
two were conflated in earlier drafts of this annex.

The difference is the whole post-commissioning lifecycle. Geometry held as Fraktal configuration is
inside recipe resolution and changeover (§3.8), parameter sets that save and restore a whole
machine (§3.8b), access control (§7.7) and the audit log (§8.3), and it renders in the generic HMI
with no robot-specific screen (§3.13). Geometry held only in the vendor tool is outside all of them:
adding a model, a gripper or a re-taught tray then needs a laptop, a licence and someone trained on
that vendor, and the change leaves no record the standard can see. A controller that cannot accept
downloaded geometry is a documented exception, named in the conformance claim (§12) — not the
default.

**Commands run to completion; there is no asynchronous variant.** Real frameworks often offer a
"start and don't wait" flag on motion. This annex deliberately does not: the §6.1 handshake *is* the
completion contract, and a command that returns before the motion finishes makes `Done` meaningless,
breaks the stall walk (§6.9), and pushes the wait back into every calling sequence. Overlapping
motion belongs inside one path, where the connector can blend it.

Re-teaching one link regenerates everything downstream — re-teach a drawer **frame** and every pallet/point follows; re-teach pallet **corners** and every nest regenerates; edit the **affinity table** and routing changes with no code. This is §3.8 "recipe, not code" taken to its structural conclusion.

---

## I.2 Reasons (per-module-type block — register in §8.8)

**Reason codes are not redefined here.** Core owns the framework band (`TIMEOUT`,
`PERMISSIVE_NOT_MET`, `INTERLOCK_DROPPED`, `UNSUPPORTED_COMMAND`, `STEP_STALLED`) in `E_Reason`, and
link supervision reuses the Annex D Framework band (`LINK_TIMEOUT := 2010`, …). This type
contributes only its own §8.8 band, in `PL_ModuleReasons` beside every other module type's:

```iecst
    // robot CM 10301-10315 (Annex I)
    ROBOT_POINT_UNREACHABLE   : DINT := 10301;   // taught point not reachable with active tool/frame (rejected, §5.6)
    ROBOT_POINT_UNKNOWN       : DINT := 10302;   // point/list/pallet ID not in the controller's database
    ROBOT_MOVE_TIMEOUT        : DINT := 10303;   // point/path did not complete within ParCfg.MoveTimeout
    ROBOT_CONTROLLER_FAULT    : DINT := 10304;   // drive/controller fault reported by the robot
    ROBOT_NOT_REFERENCED      : DINT := 10305;   // MOVE/RUN before a valid home/reference
    ROBOT_TOOL_FRAME_CONFLICT : DINT := 10306;   // controller tool/frame values differ from the stored values
    ROBOT_SAFETY_DROPPED      : DINT := 10307;   // STO / safe-zone / E-stop dropped during motion (read-only, §9)
    ROBOT_NO_ROUTE            : DINT := 10308;   // routing model defines no path between the two positions (I.9)
    ROBOT_AREA_UNRESOLVED     : DINT := 10309;   // current planning area not resolvable (I.11)
    ROBOT_NO_HELP_FOR_NEST    : DINT := 10310;   // no help point resolves for a nest given the move endpoints (I.10)
    ROBOT_MODE_NOT_PERMITTED  : DINT := 10311;   // command needs a controller operating mode that is not active (I.4a)
    ROBOT_GRIP_LOST           : DINT := 10312;   // expected part absent after grip, or lost in transfer (I.6a)
    ROBOT_PROTECTIVE_STOP     : DINT := 10313;   // collision/crash-protection device tripped — NOT a §9 safety function (I.4a)
    ROBOT_PARAM_OOR           : DINT := 10314;   // a supplied command parameter is outside its configured band —
                                                 //   speed scale (I.4a) or target offset (I.8a); rejected before motion (§5.6, §14)
    ROBOT_RESUME_INVALID      : DINT := 10315;   // resume requested but the arm is no longer on the retained path (I.4b)
```

Each code **shall** land together with its `reason_rationalization.json` entry (priority, category,
shelvability, operator action, consequence) and its immutable localization key, in the **same**
change: the catalog generator validates coverage in both directions — a reason without
rationalization, and a rationalization without a reason, both fail the build (§8.9, TC3 §8.9,
`LOCALIZATION_AND_MODULE_CONTENT.md`). Fault text in code is therefore always a key
(`'std.error.robotNoRoute'`), never English prose.

```iecst
{attribute 'qualified_only'}
TYPE E_RobotCommand : (
    NONE := 0, POWER_ON := 1, POWER_OFF := 2, HOME := 3, MOVE_TO := 4, RUN_PATH := 5,
    RUN_PALLET := 6, MOVE_TEMPLATE := 7, MOVE_FROM_AREA := 8, SET_TOOL := 9, SET_FRAME := 10
) DINT;
END_TYPE
```

---


## I.3 The connector contract (`I_RobotConnector`)

`I_RobotConnector` is `I_DeviceConnector` (Annex D) plus the **primitive** robot surface. Everything
below it — protocol, point database, kinematics, path planning, the routing model — is confined to
the connector (§3.15).

**Most of this surface is not Fraktal's to define.** An open, manufacturer-independent standard for
the PLC↔robot command boundary already exists — **SRCI** (Standard Robot Command Interface, published
by PROFIBUS & PROFINET International), organised as a mandatory **Core** profile plus optional groups
and implemented by several robot vendors. Re-describing what "enable the robot" or "interrupt the
motion" means in Fraktal's own prose would create a second authority for someone else's contract and
guarantee drift (§1.1 O9). So the members below are **defined by their SRCI equivalent**, and this
table is normative for their semantics:

| `I_RobotConnector` member | Semantics defined by |
|---|---|
| `PowerOn` / `PowerOff` | SRCI `EnableRobot` *(Core)* |
| `Home` | SRCI referencing / `MoveAxesAbsolute` to the home configuration *(Core)* |
| `MoveToPoint(PointId)` | SRCI `MoveDirectAbsolute` / `MoveLinearAbsolute` *(Core)*, target resolved from the ID |
| `RunPath(ListId, Start, End)` | sequential SRCI moves over the stored list *(Core)* |
| `Interrupt` / `Resume` | SRCI `GroupInterrupt` / `GroupContinue` *(Core)* |
| `Abort` | SRCI `GroupStop` *(Core)* |
| `ResetController` | SRCI `GroupReset` *(Core)* |
| `RequestMode` / `ActualMode` | SRCI `SetOperationMode` *(Core)* |
| `SetSpeedScale` | SRCI `ChangeSpeedOverride` *(Core)* |
| `ActualPosition` | SRCI `ReadActualPosition` *(Core)* |
| `ControllerMessage` | SRCI `ReadMessages` / `ReadRobotData` *(Core)* |
| `SetTool` / `SetFrame` | SRCI `ReadToolData` / `ReadFrameData` *(Core)*, selection by ID |
| `SetPayload` | SRCI `ReadLoadData` / `WriteLoadData` |
| `Jog` | SRCI `GroupJog` *(Core)* |

The interface itself remains Fraktal's, because the seam must stay platform-neutral (O8): a vendor
connector speaking its own protocol is a conformant alternative (§I.5), and SRCI is PROFINET-centric
where Fraktal is not. What the table removes is the *duplicate definition*, not the abstraction.

**Five members have no SRCI equivalent, because they express this annex's own model:**

```iecst
// One pose type serves live readback and runtime corrections (I.8a). The connector owns the
// Euler convention and the units it speaks to the controller in; per-model facts like that are
// data it reads, never branches in application code (I.5).
TYPE ST_RobotPose : STRUCT
    X, Y, Z    : LREAL;   // mm
    RX, RY, RZ : LREAL;   // deg
END_STRUCT END_TYPE

INTERFACE I_RobotConnector EXTENDS I_DeviceConnector
    // ── defined by the SRCI table above ─────────────────────────────────
    METHOD PowerOn : BOOL   METHOD PowerOff : BOOL   METHOD Home : BOOL
    METHOD MoveToPoint : BOOL (PointId : DWORD)
    METHOD RunPath     : BOOL (ListId : DWORD; StartIdx, EndIdx : DINT)   // (-1,-1) = whole list
    METHOD Interrupt : BOOL   METHOD Resume : BOOL   METHOD Abort : BOOL
    METHOD ResetController : BOOL
    METHOD RequestMode : BOOL (Mode : E_RobotOpMode)
    METHOD SetSpeedScale : BOOL (Percent : REAL)
    METHOD SetTool : BOOL (ToolId : DWORD)   METHOD SetFrame : BOOL (FrameId : DWORD)
    METHOD SetPayload : BOOL (LoadId : DWORD)
    METHOD Jog : BOOL (Mode : E_JogMode; Axis : INT; Dir : INT)           // manual only, release-gated (§7.6)
    PROPERTY ActualMode : E_RobotOpMode      PROPERTY ActualPosition : ST_RobotPose
    PROPERTY ControllerMessage : ST_Diagnostic
    PROPERTY Referenced : BOOL               PROPERTY Busy : BOOL

    // ── Fraktal's own model — no SRCI equivalent ────────────────────────
    METHOD RunPallet    : BOOL (PalletId : DWORD; Nest : DINT)  // generated pallet nest (I.12)
    METHOD MoveTemplate : BOOL (FromPosId, ToPosId : DWORD)     // routed by the declarative graph (I.9)
    METHOD MoveFromArea : BOOL (ToPosId : DWORD)                // start resolved from the current area (I.11)
    PROPERTY CurrentArea : DWORD                                // planning area the TCP is in (0 = none) (I.11)
    PROPERTY ProtectiveStop : BOOL                              // crash device tripped — not §9 safety (I.4a)
    PROPERTY Resumable : BOOL                                   // resume still valid on the retained path (I.4b)
    PROPERTY LastResult : ST_Diagnostic                         // first-out reason + SourcePath
    // (Linked / LastSeen / LinkReason / Cyclic inherited from I_DeviceConnector, Annex D)
END_INTERFACE
```

That split is the useful summary of this annex: **seven members carry everything the standard adds
over an ordinary robot command interface** — pallets, generated routes, area-resolved motion and
pose recovery, the protective-stop distinction, and the resumability guard. The rest is a published
standard, cited rather than re-invented.

**Payload should be kept current.** A robot's dynamics, accuracy and brake margin depend on what it
carries, and the load changes the moment a part is gripped or released. An application **should**
maintain the active load case through `SetPayload`; a cell that does not will see accuracy and wear
degrade silently long before anything faults. This is a `should` rather than a `shall` until a real
cell demonstrates the failure it prevents — the standard's own trimming rule sets that bar (§1.1 O1).

`MoveTemplate` (known start) and `MoveFromArea` (start resolved live from the current area) are
**both everyday motion commands** — the reviewed application uses area-resolved moves as its
*primary* form because they are robust to wherever the arm currently is; pose recovery (I.11) is one
important use of the same primitive, not a separate mode.

---


## I.4 The Control Module (`FB_RobotCM`)

`FB_RobotCM` is an ordinary Control Module: it **extends `FB_ControlModuleBase`** and adds only its
device logic. `Execute`/`Abort` arrive through the base's `ExecuteCommand`/`AbortCommand`, and
`Busy`/`Done`/`Error`/`Aborted`/`ErrorID`, first-out stamping, rollup and publication are base-owned
and proven once in `FB_Base_Tests` (§5.7) — exactly as for the separator (Annex A) and the axis
(Annex G). Its additions over a plain CM are Annex D's *"every command first requires `Linked`"*,
validate-then-command (§5.6), and dropping **arm power** on a safety-alias loss (§9).

Because a robot command is the most heavily parameterized in the standard, its parameters travel in
`ParCmd` — latched by the base on the Execute rising edge — not as flat inputs:

```iecst
TYPE ST_RobotParCmd :   // latched by the base on the Execute rising edge
STRUCT
    TargetId   : DWORD; // point / list / pallet / tool / frame — or the TO position (MOVE_TEMPLATE, MOVE_FROM_AREA)
    SpeedScale : REAL := 100.0;   // process speed for THIS command, % of taught (recipe, §3.8 — I.4a(b))
    FromId     : DWORD; // FROM position (MOVE_TEMPLATE only)
    Offset     : ST_RobotPose;  // bounded correction to the taught target (vision-guided, I.8a)
    Nest       : DINT;  // nest index (RUN_PALLET only)
    StartIdx   : DINT;  // sub-path bounds (RUN_PATH; -1,-1 = whole list)
    EndIdx     : DINT;
END_STRUCT
END_TYPE

TYPE ST_RobotParCfg :
STRUCT
    SchemaVersion : UINT := 1;      // recipe-class config is versioned (§3.8)
    MoveTimeout   : TIME := T#60S;  // per-command guard; the Unit step's ExpectedTime (§6.5) remains the outer one
    HomeTimeout   : TIME := T#120S;
    OffsetLimit   : ST_RobotPose;   // per-axis envelope for a runtime target correction (I.8a)
    SpeedScaleMin : REAL := 1.0;    // band a recipe SpeedScale is validated against (I.4a(b))
    SpeedScaleMax : REAL := 100.0;
    // Ceiling per controller operating mode; the CM applies MIN(ceiling, ParCmd.SpeedScale)
    SpeedCeiling  : ARRAY[E_RobotOpMode] OF REAL := [0.0, 100.0, 25.0, 100.0];   // I.4a(a),(b)
END_STRUCT
END_TYPE

TYPE ST_RobotOutCmd :   // valid on Done
STRUCT
    ReachedId : DWORD;              // position actually reached
END_STRUCT
END_TYPE

TYPE ST_RobotOutImm :   // cyclic live status + first-out diagnostic
STRUCT
    Linked      : BOOL;             // mirrored from the connector (Annex D)
    Referenced  : BOOL;
    ArmPowerOn  : BOOL;
    CurrentArea : DWORD;            // planning area the TCP is in (0 = none/undefined)
    ActualMode  : E_RobotOpMode;    // what the controller reports (I.4a(a)) — read-only status
    SpeedScale  : REAL;             // scale actually in force = MIN(mode ceiling, recipe scale)
END_STRUCT
END_TYPE

// Publication is inherited from the explicitly marked deployed root instance.
FUNCTION_BLOCK FB_RobotCM EXTENDS FB_ControlModuleBase
VAR_INPUT
    Command : E_RobotCommand;
    ParCfg  : ST_RobotParCfg;
    ParCmd  : ST_RobotParCmd;
END_VAR
VAR_OUTPUT
    OutCmd : ST_RobotOutCmd;
    OutImm : ST_RobotOutImm;
    Intlk  : FB_PermIntlk;          // read-only safety alias (§9.2) — declared by the application, not by this type
END_VAR
VAR  _conn : I_RobotConnector;  _step : INT;  _tMove : TON;  END_VAR
```

`OnCyclic` runs the Annex D link supervision, mirrors the connector into `OutImm`, republishes the
diagnostic, and applies the safe-stop — safety is read-only, so a dropped alias mid-command powers
the arm down and faults with **no** automatic re-enable (§9.3/§9.4):

```iecst
IF NOT Intlk.AllOk AND Busy THEN
    _conn.Abort();  _conn.PowerOff();
    _M_FaultStopped(Code := PL_ModuleReasons.ROBOT_SAFETY_DROPPED, Text := 'std.error.robotSafetyDropped');
END_IF
```

`_M_Dispatch` validates the **request** before the **state**, and both before commanding motion
(§5.6) — an unknown ID is malformed whether or not the arm is referenced, and reporting "not
referenced" for an impossible target sends the operator to the wrong problem:

```iecst
METHOD PROTECTED _M_Dispatch
// 1) request/state validation — rejected before anything reaches the floor (§5.6)
IF NOT _conn.Linked THEN
    _M_Fault(E_Reason.LINK_TIMEOUT, 'std.error.robotLinkDown');  RETURN;
END_IF
IF NOT _M_OffsetWithin(ParCmd.Offset, ParCfg.OffsetLimit) THEN                                // I.8a, §14
    _M_FaultN(Code := PL_ModuleReasons.ROBOT_PARAM_OOR, Text := 'std.error.robotOffsetOutOfRange');  RETURN;
END_IF
IF (ParCmd.SpeedScale < ParCfg.SpeedScaleMin) OR (ParCmd.SpeedScale > ParCfg.SpeedScaleMax) THEN
    _M_FaultN(Code := PL_ModuleReasons.ROBOT_PARAM_OOR, Text := 'std.error.robotSpeedScaleOutOfRange');  RETURN;
END_IF
IF NOT _M_ModePermits(Command, _conn.ActualMode) THEN                                        // I.4a(a)
    _M_FaultN(Code := PL_ModuleReasons.ROBOT_MODE_NOT_PERMITTED, Text := 'std.error.robotModeNotPermitted');  RETURN;
END_IF
IF (Command IN (E_RobotCommand.MOVE_TO, E_RobotCommand.RUN_PATH, E_RobotCommand.RUN_PALLET,
                E_RobotCommand.MOVE_TEMPLATE, E_RobotCommand.MOVE_FROM_AREA)) AND NOT _conn.Referenced THEN
    _M_FaultN(Code := PL_ModuleReasons.ROBOT_NOT_REFERENCED, Text := 'std.error.robotNotReferenced');  RETURN;
END_IF

CASE _step OF
    10:  // clamp speed to MIN(mode ceiling, recipe scale) — I.4a(b) — then issue the primitive;
         // FALSE = unknown / unreachable / no-route / no-help
        _conn.SetSpeedScale(MIN(ParCfg.SpeedCeiling[_conn.ActualMode], ParCmd.SpeedScale));
        CASE Command OF
            E_RobotCommand.POWER_ON:       _conn.PowerOn();
            E_RobotCommand.POWER_OFF:      _conn.PowerOff();
            E_RobotCommand.HOME:           _conn.Home();
            E_RobotCommand.MOVE_TO:        IF NOT _conn.MoveToPoint(ParCmd.TargetId)                          THEN _M_FaultN(_conn.LastResult); RETURN; END_IF
            E_RobotCommand.RUN_PATH:       IF NOT _conn.RunPath(ParCmd.TargetId, ParCmd.StartIdx, ParCmd.EndIdx) THEN _M_FaultN(_conn.LastResult); RETURN; END_IF
            E_RobotCommand.RUN_PALLET:     IF NOT _conn.RunPallet(ParCmd.TargetId, ParCmd.Nest)               THEN _M_FaultN(_conn.LastResult); RETURN; END_IF
            E_RobotCommand.MOVE_TEMPLATE:  IF NOT _conn.MoveTemplate(ParCmd.FromId, ParCmd.TargetId)          THEN _M_FaultN(_conn.LastResult); RETURN; END_IF  // I.9
            E_RobotCommand.MOVE_FROM_AREA: IF NOT _conn.MoveFromArea(ParCmd.TargetId)                         THEN _M_FaultN(_conn.LastResult); RETURN; END_IF  // I.11
            E_RobotCommand.SET_TOOL:       _conn.SetTool(ParCmd.TargetId);
            E_RobotCommand.SET_FRAME:      _conn.SetFrame(ParCmd.TargetId);
        ELSE
            _M_Fault(E_Reason.UNSUPPORTED_COMMAND, 'std.error.unsupportedCommand');  RETURN;   // defined ELSE (§5.6)
        END_CASE
        _tMove(IN := TRUE, PT := SEL(Command = E_RobotCommand.HOME, ParCfg.MoveTimeout, ParCfg.HomeTimeout));
        _step := 20;
    20:  // map the controller's Busy/Done/Error/timeout onto the CM handshake (§6.1)
        IF NOT _conn.Busy AND _conn.LastResult.ReasonCode = 0 THEN
            _tMove(IN := FALSE);  OutCmd.ReachedId := ParCmd.TargetId;  _M_Complete();
        ELSIF _conn.LastResult.ReasonCode <> 0 THEN
            _M_FaultStopped(_conn.LastResult);              // adopt the connector's first-out verbatim (§8.2)
        ELSIF _tMove.Q THEN
            _M_FaultStopped(Code := PL_ModuleReasons.ROBOT_MOVE_TIMEOUT, Text := 'std.error.robotMoveTimeout');
        END_IF
ELSE
    _M_Fault(E_Reason.STEP_STALLED, 'std.error.undefinedStep');        // defined ELSE (§5.6)
END_CASE
```

An abort is routed through the base's own `AbortCommand()` rather than invented as a fault. A point,
a 26-point path, a generated route, or a pallet nest is **one** command that runs to completion — so
the robot looks identical to any other CM (§6.1). Commands are **not** auto-repeated on error;
resumption is deliberate (Annex D / §9.3).

---


## I.4a Operating mode, speed authority, and the protective stop

> **Normative model: Core §10.6.** The three facts below are requirements on any conformant robot CM;
> this section is their worked realization, as I.9–I.10 are for the routing model.

Three device facts are **mandatory** for any robot cell and are not derivable from anything else in
the standard, so they belong in the CM contract rather than in every project.

### (a) Controller operating mode is *requested*, never asserted

Every industrial robot controller has its own operating mode — automatic-remote, manual reduced
speed, manual high speed — and that mode, not the PLC, bounds what motion is physically allowed.
The PLC **shall** treat it as a request/report pair:

```iecst
{attribute 'qualified_only'}
TYPE E_RobotOpMode : (UNKNOWN := 0, AUTO_REMOTE := 1, MANUAL_REDUCED := 2, MANUAL_HIGH := 3) DINT;
END_TYPE
```

- `RequestMode(m)` asks; `ActualMode` reports what the controller says it actually is. The two are
  **separate members on purpose** — a request that was not granted must stay visibly ungranted, not
  be overwritten by optimism.
- On startup, download, or any loss of the reported mode, the requested mode **shall** default to
  the most restrictive one the cell supports, so that a freshly started controller cannot move.
- A command **shall** be rejected before it reaches the floor when `ActualMode` does not permit it —
  jogging (§7.6) requires a manual mode; `RUN_PATH`/`MOVE_TEMPLATE` in production require
  `AUTO_REMOTE` — giving `ROBOT_MODE_NOT_PERMITTED` as a clean first-out (§5.6) instead of a command
  that is silently ignored by the controller.
- Mode is **not** a substitute for §9. The enabling device, safe-reduced-speed monitoring and the
  E-stop chain stay in the certified system; `ActualMode` is published read-only status, and the PLC
  never infers "safe" from it.

### (b) Speed is a bounded scale, held as configuration

A robot's commanded speed **shall** be limited by a scale the application holds as configuration —
not by editing taught geometry. Two independent scales compose, and both are plain scalars, so
§I.1's boundary is untouched: no coordinate, waypoint or motion mode enters PLC code.

| Scale | Owner | Purpose |
|---|---|---|
| **Mode ceiling** — `ParCfg.SpeedScale[E_RobotOpMode]` | station configuration | the maximum the cell allows in each operating mode; applied by the CM, never by a sequence |
| **Process scale** — `ParCmd.SpeedScale` | recipe (§3.8) | the speed *this product* is processed at — a quality parameter, e.g. a treatment or dispense pass |

The CM applies `MIN(mode ceiling, process scale)` through `SetSpeedScale` before the move, and
rejects a process scale outside the configured band with `ROBOT_PARAM_OOR` (§5.6). Reduced speed
outside automatic is therefore a property of the *type*, not a habit each project re-implements.

### (c) A protective stop is not a safety function

Collision and crash-protection devices on the tool are **process protection**, not functional safety
(§9). The distinction is load-bearing: a protective stop is detected and acted on by the ordinary
PLC, whereas a safety stop is owned by the certified system and merely *read* here.

On `ProtectiveStop`, the CM **shall** abort the motion, fault with `ROBOT_PROTECTIVE_STOP`, and
**not** resume automatically — recovery is a deliberate reset followed by an area-resolved move back
to a defined pose (I.11), because a crash leaves the arm exactly where §I.11 says it must not be
assumed to be. It **shall not** be routed through the §9 alias, which would misrepresent a process
event as a safety event in the alarm record and in every audit built on it.

```iecst
// in OnCyclic, beside the §9 safe-stop — deliberately a separate branch and a separate reason
IF _conn.ProtectiveStop AND Busy THEN
    _conn.Abort();
    _M_FaultStopped(Code := PL_ModuleReasons.ROBOT_PROTECTIVE_STOP, Text := 'std.error.robotProtectiveStop');
END_IF
```

---


## I.4b On-path hold and resume — the robot half of §6.1 `HELD`

Fraktal already owns the *semantics* of a suspended command. §6.1's **`Held`** flag is orthogonal to
the terminal states: a module that is `BUSY`, has withdrawn the affected outputs, and is deliberately
not progressing because a **named** condition is unsatisfied publishes `Held` with that condition as
a `LOW`-severity diagnostic, raises no `Error`, opens no reset event, and resumes on its own when the
condition returns. Nothing about that needs changing for a robot, and this annex does **not** add a
handshake state.

What a robot adds is the *mechanism*. A cylinder honours `HELD` by simply de-energising: it stops
where it is, and continuing means re-issuing the same output. A robot cannot. Stopping a
26-point path wherever the scan happened to fall, and later resuming by re-commanding the path, would
re-run points already executed or approach the next one from an untaught pose. The robot must stop
**on its path**, retain where on the path it stopped, and later continue **from that same point** —
which only the controller can do. Hence the two primitives:

| §6.1 concept | Robot mechanism |
|---|---|
| condition lost → `Held := TRUE`, outputs withdrawn | `_conn.Interrupt()` — controller stops **on path**, resume point retained |
| condition returns → progress continues | `_conn.Resume()` — controller continues **from the retained point** |
| — | `_conn.Resumable` — FALSE once the arm has left the retained path |

```iecst
// in OnCyclic: the robot half of HELD. The CONDITION is named by the application (§7.2);
// this code only translates "held" into something a robot can actually honour.
IF Held AND NOT _heldOnPath THEN
    _conn.Interrupt();  _heldOnPath := TRUE;
ELSIF NOT Held AND _heldOnPath THEN
    IF _conn.Resumable THEN
        _conn.Resume();  _heldOnPath := FALSE;
    ELSE
        // The arm was moved while suspended — jogged, hand-guided, or pushed by a collision.
        // Resuming on a path the tool is no longer on would move through untaught space.
        _M_FaultN(Code := PL_ModuleReasons.ROBOT_RESUME_INVALID, Text := 'std.error.robotResumeInvalid');
    END_IF
END_IF
```

**`Resumable` is the load-bearing part.** A hold is exactly the window in which an operator is most
likely to jog the arm — that is what the pause was *for*. Resuming afterwards onto a path the tool
has left is how a robot drives through a fixture. Making non-resumability an explicit, published
property with its own first-out turns that into a clean refusal and an area-resolved recovery
(I.11), rather than a silent move through untaught space.

A held robot is therefore **not** a faulted one: it rolls up as information at `LOW` severity, names
the condition the operator must restore, and needs no reset — the §6.1 contract, unchanged.

---


## I.5 Default vs. alternative connectors, and *why the portable one is the default* (§12)

`I_RobotConnector` is the injected seam, like `I_RecipeProvider` (§3.8) and `I_PartCarrier` (Annex E) — brand is configuration, not code. The framework controls robots **regardless of model or manufacturer** by capturing per-model facts (digital-signal counts to the PLC, Euler conventions, supported functions) as a **per-robot record the connector reads at runtime** — so `FB_PortableTeachConnector` is the **recommended default** (brand differences are *data*, not *branches in app code*), and per-vendor connectors are **conformant alternatives** on the same interface, parent Unit unchanged. Exposing a robot via the portable framework is a **§12 conformance option** (claimed like §11.7), not a mandate — but the recommended path.

---

## I.5a The recommended default binding: SRCI

`I_RobotConnector` is deliberately narrow, and the obvious question is what implements it. The
recommended default is **SRCI (Standard Robot Command Interface)** — an open, manufacturer-independent
specification published by PROFIBUS & PROFINET International for exactly this boundary: the command
and data interface between a PLC client and a robot controller. It is organised as a mandatory
**Core profile** plus Extended and optional groups, and it is implemented by multiple robot vendors,
so a connector written against it is multi-vendor by construction rather than by aspiration.

This matters more than a convenient protocol choice. §I.5 argues that brand should be *data*, not
branches in application code, and that the portable connector should be the recommended default. An
open multi-vendor standard makes that claim checkable: the "conformant alternative" of §I.5 stops
being a promise about future connectors and becomes a second implementation of a published contract.

The member-by-member mapping is normative and lives in §I.3, so it is stated once.

Two differences are deliberate and are the reason this annex is not simply "use SRCI":

- **SRCI is a command interface; the routing model is not in it.** Points, paths, pallets, areas,
  help affinity and the generated route (I.9–I.12) sit *above* SRCI, in the connector. A connector
  may resolve a route locally and emit the resulting motions as SRCI commands.
- **SRCI exposes a motion vocabulary; Fraktal exposes a module.** The parent Unit commands
  `PICK_PART`, not `MoveLinearAbsolute`. The §6.1 handshake, the release report, the stall walk and
  the reason rollup are Fraktal's, and remain so whatever speaks underneath.

A per-manufacturer connector (a vendor's own protocol) stays a conformant alternative on the same
interface, with the parent Unit unchanged — SRCI is the *recommended* default, not a mandate.

---

## I.5b Optional capability groups

> **Status: catalogued, not specified.** None of the groups below is defined by this annex or
> required for conformance. They are listed so that a project meeting one knows it is a declared
> capability rather than a gap, and knows where it attaches. Each is specified when a real cell
> needs it — the standard's own threshold for absorbing work is *occurrence*, not anticipation
> (§1.1 O1, trimming rule).

The members of §I.3 are the surface every conformant robot connector provides. The capabilities
below are real, common, and deliberately **not** in it: each is declared through the ordinary
`Features` flag set (§3.9), so a cell that needs one advertises it and the generic HMI renders it,
while a cell that does not pays nothing — neither interface surface nor published nodes (§1.1 O4).

| Capability | What it adds | Why it is optional rather than core |
|---|---|---|
| **Conveyor tracking** | synchronise the tool frame to a moving belt; pick and place while it runs | changes the *frame* a move is computed in, not the command surface; only line-integrated cells need it |
| **Work-area monitoring** | permitted/forbidden volumes, actively monitored — the basis of multi-robot zone interlocking | distinct from the planning areas of I.11: those resolve *where the robot is*, these forbid *where it may go*. Needed only where workspaces overlap |
| **Force control** | force/torque limiting, compliant insertion, hard-stop search | assembly-specific; a handling cell has no use for it |
| **Collision detection / free drive / singularity avoidance** | protective sensing without a hardware crash device; hand-guiding; joint-configuration recovery | free drive is a cobot concern, singularity a kinematics-dependent one |
| **Brake test** | the periodic brake-integrity test required for arms carrying a hanging load | a maintenance obligation of *some* robots, driven by the machine's risk assessment |
| **Trigger at position** | fire an output at a path position without stopping (dispensing, blow-off) | process-specific; the standard's step model already covers stop-and-act |
| **Robot-hosted I/O** | read/write the controller's own digital and analog channels | where tool valves sit on the arm, this is the channel a HAL binds to (§10.2); the mapping stays the Hardware Driver's |

A capability group that a project needs is added as a **narrow secondary interface** the connector
may also implement, never by widening `I_RobotConnector` — the same rule §3.15 applies to every
device concern, so the common case stays small.

---


## I.6 The two tiers — robot **CM** (primitive) vs. handling **EM** (semantic)

The reference application does not command the robot with pick/place semantics directly. It uses **two tiers**, which map exactly onto the standard:

- **`FB_RobotCM`** (this annex) = the robot **object / connector**: the primitive surface (`MOVE_TEMPLATE`, `MOVE_FROM_AREA`, `RUN_PATH`, `MOVE_TO`, `POWER_ON`…). This is the Control Module.
- **`FB_RobotHandlingEM`** = a thin **Equipment Module** exposing the station's *semantic* operations — `PICK_PART`, `PLACE_PART`, `PLACE_PART_NOK`, `SCAN_PART`, `PROCESS_PART`, `CHECK_TOOL`, `HOME`, `MOVE_REF` — each a short completing step chain that composes the robot CM's primitives with the gripper/tool CMs, **adding no device logic** (Annex B §3.5). For example `PICK_PART` ≈ `MOVE_FROM_AREA(nest)` → gripper close → `MOVE_TEMPLATE(nest, transitHelp)`.

Surface (consumed by Annex C):

```iecst
{attribute 'qualified_only'}
TYPE E_HandlingCommand : (NONE := 0, PICK_PART := 1, PLACE_PART := 2, PLACE_PART_NOK := 3,
                          SCAN_PART := 4, PROCESS_PART := 5, CHECK_TOOL := 6, HOME := 7,
                          MOVE_REF := 8) DINT;   // MOVE_REF: drive to a reference/calibration pose
END_TYPE

TYPE ST_HandlingParCmd :   // latched by the base on the Execute rising edge
STRUCT
    TargetId : DWORD;   // destination position id (the NOK disposition for PLACE_PART_NOK, I.10.1)
    Nest     : DINT;    // nest index within the pallet, when the destination is one
END_STRUCT
END_TYPE

FUNCTION_BLOCK FB_RobotHandlingEM EXTENDS FB_EquipmentModuleBase
VAR_INPUT
    Command : E_HandlingCommand;
    ParCfg  : ST_HandlingParCfg;
    ParCmd  : ST_HandlingParCmd;
END_VAR
VAR_OUTPUT
    OutCmd : ST_HandlingOutCmd;
    OutImm : ST_HandlingOutImm;
END_VAR
VAR  Robot130 : FB_RobotCM;  _conn : FB_PortableTeachConnector;
     Gripper  : FB_GripperCM;   // trivial Annex A/B-pattern CM: OPEN/CLOSE + part-present feedback
END_VAR
METHOD Setup : BOOL   // wires the connector + CM internally (§3.11); Endpoint/tool ids from recipe
VAR_INPUT Name : STRING(80); Endpoint : STRING(255); Recipe : I_RecipeProvider; END_VAR
// each command = a short completing step chain composing Robot130 + Gripper (Annex B §3.5), e.g.:
//   PROCESS_PART   → Robot130.RUN_PATH(ParCmd.TargetId)
//   PLACE_PART_NOK → Gripper.CLOSE → Robot130.MOVE_TEMPLATE(current, ParCmd.TargetId) → Gripper.OPEN
// child Error → _M_RollupFault() adopts Robot130/Gripper first-out (§8.2), exactly as FB_ClampEM (Annex B §B.4)
```

So the earlier "a robot is just a CM" is precise at the device tier; a station simply adds an EM of semantic ops above it — the ordinary Annex B pattern. The parent Unit (Annex C) commands `RobotHandling.PROCESS_PART` / `PLACE_PART_NOK`, one handshake command exactly like `ClampStation.CLAMP`.

---

## I.6a Grip verification — the transfer is not complete until the part is proven held

A handling robot **shall** prove possession rather than assume it. Commanding a gripper closed says
nothing about whether a part is in it: the part may be absent from the nest, mis-picked, or dropped
in transit, and every downstream step — the scan, the process, the place — is then operating on a
fiction. This is the single most common real failure in a handling cell and it is **not** optional.

The mechanism is ordinary and already available: the gripper CM publishes part-present feedback
(§3.2), and the handling EM verifies it as a step of the transfer.

```iecst
// PICK_PART, after the close command completes:
20:  // a gripper reaching its closed end position with no part between the jaws is the
     // observable signature of a failed pick — settle first, because the feedback is
     // only meaningful once the jaws have stopped moving.
    _tSettle(IN := TRUE, PT := ParCfg.GripSettleTime);
    IF _tSettle.Q THEN
        _tSettle(IN := FALSE);
        IF Gripper.OutImm.ClosedWithoutPart THEN
            _M_FaultN(Code := PL_ModuleReasons.ROBOT_GRIP_LOST, Text := 'std.error.robotGripLost');
        ELSE
            _step := 30;
        END_IF
    END_IF
```

Two rules make this useful rather than merely present:

- **Verification is a step of the transfer, not a background monitor.** It runs where the operator
  can act on it — the Unit's stall walk names *"pick failed: no part in gripper"* at the picking
  step (§6.9), not three operations later when the process produces a mysterious result.
- **Possession is re-checked before release, not only after grip.** A part lost in transit is
  detected at the place, giving `ROBOT_GRIP_LOST` at the position where the part actually is, which
  is what recovery needs to know.

A verified failure is an ordinary NOK outcome, so it composes with what the annex already has: the
Unit branches its step chain to a disposition target (I.10.1), and with Annex E the same first-out
reason travels into the quality record — one vocabulary, no parallel taxonomy (I.13).

---


## I.7 Diagnostics — a robot fault rolls up the same stall walk (§6.9, §8.2)

`_M_Fault` adopts the connector's first-out reason and the module `SourcePath` — no per-robot scheme. All land on the **Unit's** screen through the unchanged §6.9 walk:

```
InfeedUnit  step Nxxx "Pick" ──awaits──▶ RobotHandling.PICK_PART ──▶ Robot130.MOVE_FROM_AREA(PalletG1L.Nest)
Robot130 (FB_RobotCM)        ──Error────▶ adopts connector reason
Robot130._conn               ──────────▶ ROBOT_POINT_UNREACHABLE @ "InfeedUnit.Robot130 : PalletG1L.Nest[7]"
```
> **Step … Pick stalled → awaiting RobotHandling.PICK_PART → InfeedUnit.Robot130: nest 'PalletG1L.Nest[7]' unreachable**

Each planning first-out surfaces the same clean way: no route between two positions → `ROBOT_NO_ROUTE` (I.9); no help point resolves for a nest → `ROBOT_NO_HELP_FOR_NEST` (I.10); current area unresolvable → `ROBOT_AREA_UNRESOLVED` (I.11); dropped link → `LINK_TIMEOUT @ "…Robot130.Link"` (Annex D); safety dropped → `ROBOT_SAFETY_DROPPED`. HMI message and (with Annex E) quality record are the **same sentence**, once.

---

## I.8 Paths are taught point-lists — run by ID, by sub-range, with per-point motion mode

A **path** is a robot point list run sequentially by index; the framework runs it by name/ID, or a **sub-path** between a start and end index — so the station's 10-point `ProcessG1-1` or 26-point `ProcessG2` is *one* `RUN_PATH` command. Each point carries its own **motion mode** as taught data — Joints, PTP, or Linear, absolute or blended (all three observed in the real application) — blending rounds intermediate points for a smoother, faster move. The PLC never chooses a motion type; it names a list. Approach/retract **pre-positions** are *computed* by the framework (offset from the nest, Linear), not taught per nest — confirming the trajectory is generated, not enumerated.

**The last point of a path shall be reached exactly.** Blending rounds a corner by leaving the taught
position early, which is correct for intermediate points and wrong for the final one: a pick or place
that stops short of its nest by the blend radius is a mis-grip, and an area check (I.11) run at a
blended endpoint can report the robot outside the position it believes it reached. The connector
therefore carries `ParCfg.LastPointExact := TRUE` as its default, and a project that turns it off is
making a deliberate cycle-time trade against placement accuracy. The unit of a commanded speed —
absolute (mm/s) or a percentage of taught — is likewise connector configuration, published so the
HMI can label the number it shows rather than guessing.

---

## I.8a Runtime-computed targets — the bounded exception to "never a coordinate"

> **Status: provisional.** The rule and its envelope are stated so that a vision-guided cell is not
> silently outside the standard, and the mechanism is deliberately three fields and one check. It
> has no consuming implementation yet, so treat the specifics as subject to revision by the first
> cell that uses them; the *rule* — a correction to a taught reference, never an absolute pose,
> validated before motion — is the part meant to be stable.

§I.1's rule is that the PLC carries an ID and never a coordinate. One real application does not fit
it: **vision-guided picking**. A 3-D sensor locates a part whose position is unknown until it is
seen and produces a grasp pose at runtime. There is no ID to carry, because there is no taught point
— the part is wherever it happens to lie.

Pretending otherwise would push every such cell outside the standard, so the rule is **qualified
rather than abandoned**:

> A coordinate **may** enter PLC code only as a **bounded correction to a taught reference**, never
> as an absolute pose, and **shall** be validated against a configured envelope before any motion.

```iecst
// ST_RobotPose is defined in I.3. The correction and its envelope are ordinary command/config members:
//   ST_RobotParCmd.Offset      : ST_RobotPose;   // correction applied to the taught TargetId
//   ST_RobotParCfg.OffsetLimit : ST_RobotPose;   // per-axis envelope it is validated against
```

`MOVE_TO`/`RUN_PALLET` with a non-zero `Offset` means *"the taught nest, shifted by this much"*. The
taught reference still supplies approach direction, tool, frame, motion mode and the route (I.9) —
only the endpoint is corrected. What the standard gains from that framing:

- **The blast radius is bounded.** A vision system that returns a wild pose — a mis-match, a stale
  frame, a units error — moves the arm by at most `OffsetLimit`, not to an arbitrary point in the
  cell. A pose from a vision system is **untrusted input** (§14) exactly like an operator entry or a
  host write, and it is validated the same way; failure is `ROBOT_PARAM_OOR`, refused before motion
  (§5.6).
- **Everything else in the annex still applies.** Routing, areas, help affinity, grip verification
  and the NOK path are untouched, because the pick is still "go to nest *N*" with a correction.
- **The prohibition that mattered survives.** What §I.1 exists to prevent is a PLC *enumerating a
  trajectory* — waypoints, motion modes, blend radii, a hand-built route. None of that is admitted
  here. One corrected endpoint is not a motion program.

A cell whose parts have no taught reference at all — true random bin picking, where the grasp pose is
unconstrained — is beyond this annex: its planning belongs in the vision/planning system, which then
presents the robot with a target through its own interface. The boundary is honest about that rather
than pretending a bounded offset covers it.

---


## I.9 Dynamic trajectory generation — a **declarative** routing model (simpler than imperative `User*` methods)

> **Promoted to Core.** The routing model of this section and I.10 is now **normative platform-neutral content — Core §10.7**; I.9–I.10 remain its worked realization against the reference robot framework.

The framework generates the route between any two positions at runtime. Positions are two classes: **help points** (auxiliary / **wait/transit** positions) and **nests** (**work** positions). The reference framework expresses routing through six imperative methods the application engineer fills **per station** with `CASE` logic — `UserHelpToHelp`, `UserHelpToNest`, `UserNestToHelp`, `UserNestToNest`, `UserManipulateGeneratedList`, `UserAreas`. That is exactly the per-application boilerplate the objectives discourage (§1.1 O1, NG2).

**This standard makes routing declarative data resolved by one generic planner in the connector.** The application supplies *configuration*, not traversal code:

```iecst
TYPE ST_RouteGraph : STRUCT
    HelpAdj  : ARRAY[1..MAX_HELPS, 1..MAX_HELPS] OF BOOL;   // help↔help adjacency (which transits are allowed)
    NestHelp : ARRAY[1..MAX_GRIPPERS, 1..MAX_NESTS] OF ST_NestHelpAffinity;  // per-gripper (I.12): each nest → one OR MORE serving helps (I.10)
    DirectNest : ARRAY[1..MAX_NESTS,1..MAX_NESTS] OF DWORD; // optional direct nest→nest list id (else via help)
END_STRUCT
```

The planner builds `from → departHelp → (help-graph search) → approachHelp → to` generically, for **every** station — so no station writes traversal code. If the graph yields no path, the connector returns `ROBOT_NO_ROUTE` and the CM raises a clean first-out (§5.6) rather than an undefined move. The engineer edits a table; `UserManipulateGeneratedList`-style tweaks become optional per-edge overrides in data.

---

## I.10 **Native multi-help work positions** (removing the hand-coded workaround)

> Normative model: **Core §10.7(c)–(d)**. This section shows the concrete resolver and the real cell's scan-junction case.

**The problem.** The reference framework assigns **one help point per nest** (`rHelpIndex := HELPn`). A work position that sits between two transit regions — the cell's **scan position**, reachable from the *drawer* side via `HELP4` and the *process* side via `HELP5` — cannot be expressed that way. The real application works around it by hand-writing a conditional inside two different methods (`UserHelpToNest` **and** `UserNestToHelp`) that **reconstructs the move's endpoints from private state** (`_nestTargetIndex`, `_nestCurrentIndex`, `_helpCurrentIndex`, `_helpTargetIndex`) to choose `HELP4` vs `HELP5`. It is duplicated, must be kept in sync across directions, reads state that isn't a clean input, and does not scale — every multi-approach nest needs bespoke branching.

**The native fix.** A nest carries a **help-affinity list** — one *or more* help points, each tagged with a **role** (`APPROACH`/`DEPART`/`EITHER`, default `EITHER`) and, *optionally*, the transit **region** it serves. The connector's planner already knows the move's endpoints, so it resolves the serving help **role-first** — direction is the higher-consequence constraint (a wrong-direction corridor can drive the gripper into the fixture; a wrong region is only a longer, still-safe route) — and uses region/proximity **only to break ties** among same-direction corridors. Region is therefore required only on a nest that has two corridors *for the same direction*; most nests need only the role. No private state, no per-direction duplication, no `CASE`:

```iecst
{attribute 'qualified_only'} TYPE E_HelpRole : (EITHER := 0, APPROACH := 1, DEPART := 2) DINT; END_TYPE
//   Role default is EITHER (= 0, zero-initialized): an entry corridor is bidirectional unless the geometry
//   is physically one-way. Tag APPROACH-only / DEPART-only ONLY for a truly one-way nest — that makes a
//   reversal through it (e.g. a NOK return, I.10.1) fail loudly with ROBOT_NO_HELP_FOR_NEST, never mis-route.

TYPE ST_HelpAffinity : STRUCT
    HelpId   : DWORD;        // a help point serving this nest
    Role     : E_HelpRole;   // APPROACH into the nest / DEPART from it / EITHER (default)
    RegionId : DWORD;        // OPTIONAL transit region this help connects to (0 = any); e.g. DRAWER / PROCESS
END_STRUCT
TYPE ST_NestHelpAffinity : STRUCT
    Helps : ARRAY[1..MAX_HELPS_PER_NEST] OF ST_HelpAffinity;  Count : INT;
END_STRUCT

// Resolver — ROLE-PRIMARY: filter by direction first (highest consequence of error), tie-break by region/nearest.
// `dir` = APPROACH when the nest is the move's target, DEPART when it is the source — the CM already knows which.
METHOD PRIVATE _M_ResolveHelp : DWORD
VAR_INPUT nest : DWORD; other : DWORD; dir : E_HelpRole; END_VAR
VAR i, nCand : INT; a : ST_NestHelpAffinity; cand : ARRAY[1..MAX_HELPS_PER_NEST] OF ST_HelpAffinity; END_VAR
    a := _graph.NestHelp[_activeGripper, nest];   // nests are per-gripper (I.12); MAX_GRIPPERS = 1 is the trivial case
    IF a.Count = 0 THEN _M_SetReason(PL_ModuleReasons.ROBOT_NO_HELP_FOR_NEST, nest); RETURN; END_IF
    // 1) VALIDITY FILTER — keep only corridors legal for this direction (EITHER is always legal)
    nCand := 0;
    FOR i := 1 TO a.Count DO
        IF a.Helps[i].Role = dir OR a.Helps[i].Role = E_HelpRole.EITHER THEN
            nCand := nCand + 1;  cand[nCand] := a.Helps[i];
        END_IF
    END_FOR
    IF nCand = 0 THEN _M_SetReason(PL_ModuleReasons.ROBOT_NO_HELP_FOR_NEST, nest); RETURN; END_IF  // one-way nest, wrong way
    IF nCand = 1 THEN _M_ResolveHelp := cand[1].HelpId; RETURN; END_IF                     // direction alone decided
    // 2) TIE-BREAK — among same-direction corridors, prefer the one on the other endpoint's side, else nearest,
    //    else the first candidate. _M_RegionOf() is consulted ONLY here, so region config is needed only when a
    //    nest has ≥2 corridors for the same direction.
    _M_ResolveHelp := _M_PreferRegion(cand, nCand, _M_RegionOf(other));
```

The scan position is now a two-line table entry. Both corridors are **bidirectional** (`EITHER`), so the direction filter keeps both in either direction and the **region tie-break** decides — reproducing the old hand-coded choice automatically, both ways, with no `CASE`:

```iecst
// SCAN_PART — a corridor-junction nest: both helps EITHER, distinguished by region (side), no per-direction CASE:
_graph.NestHelp[NEST_SCAN_PART] := (Count := 2, Helps := [
    (HelpId := HELP4, Role := E_HelpRole.EITHER, RegionId := REGION_DRAWER),
    (HelpId := HELP5, Role := E_HelpRole.EITHER, RegionId := REGION_PROCESS) ]);
// a move whose other endpoint is on the PROCESS side (e.g. PROCESS_START) resolves HELP5; else HELP4.
```

Multi-help is now the general case and single-help the trivial one (`Count := 1`); an unresolvable nest yields `ROBOT_NO_HELP_FOR_NEST` instead of a silent mis-route. This is paid **once** in the planner (tested per Annex H), not per station — the O1/low-effort, reusability and diagnosability the objectives call for.

### I.10.1 Reversal & NOK disposition

A bad-part outcome — a failed in-nest test, or a NOK verdict from MES/traceability (Annex E) — is **not a special robot mode**. The *Unit* (or handling EM) consumes the verdict and **branches** its step chain (§6.2): instead of advancing to the next process, it issues an ordinary `MoveTemplate(from := ProcessNest, to := disposition)` where the disposition is the NIO drawer (`PLACE_PART_NOK`), the origin pallet (return for rework/re-test), or any other destination ID. The robot CM stays dumb; only the *target* changes (Annex E `Verdict := NOK`). The reference station's own `PLACE_PART_NOK` / `PICK_PART_NOK` and dedicated NIO drawer are exactly this.

The retract then resolves correctly **by construction**: the `ProcessNest` leg runs with `dir := DEPART`, the validity filter keeps its (default `EITHER`) entry corridor, and the tie-break picks the corridor pointing back toward the chosen disposition — so the robot **backs out through its approach/gateway help** toward the origin, then routes onward. Two rules keep this safe and *loud* rather than silent:

- **Entry corridors default to `EITHER`** — a nest is exit-able the way it was entered unless its geometry is physically one-way. A NOK reversal requested through a genuinely one-way nest (`APPROACH`-only) fails with a clean `ROBOT_NO_HELP_FOR_NEST` first-out — a real cell constraint surfaced, not a silent forward mis-route.
- **Retract is a separate path, not the approach played backwards** — `help→nest` (approach) and `nest→help` (retract) are distinct list definitions through the same gateway help, so a *lift-then-clear* retract can differ from a *straight-in* approach. Returning "to the approach position" is therefore safe even when insertion and extraction geometry differ.

---

## I.11 Area-resolved motion & recovery from an undefined pose — distinct from functional safety (§9)

`MoveFromArea` (AREA_TO_POS) plans from **whichever area the TCP currently occupies** — queried live (`IsRobotInArea`) — to a target. It is the application's *primary* motion command because it needs no assumption about the start pose; its extreme case is **recovery after an E-stop or mode change**, when the pose is undefined: the framework resolves the current area and drives to a defined position with **no operator jogging** and **no hand-coded geometric conditions**. Overlapping areas carry a **deterministic priority** so resolution is unambiguous.

**Critical precision — planning areas are *not* the safety system.** E-stop / STO / safe-zones stay in the safety PLC (§9); the motion side consumes safety status **read-only** and never re-enables itself (Annex G §9.2–§9.4). Areas re-establish a *defined pose after* the safety stop clears and a *deliberate* reset is authorised — the robot-specific realization of §9.4 reset/restart and the §3.14 `OnModeChanged` hook. If the current area can't be resolved (TCP in no known zone) the connector returns `ROBOT_AREA_UNRESOLVED`, surfaced as a normal first-out (*"pose undefined — jog to a known area"*) instead of a silent stall or an undefined move.

---

## I.12 Parametric & symmetric pallets, per-gripper nests, and chained frames

The framework **generates the whole pallet grid from a few taught corners** — the corner set being a bounded collection capability (§3.10.2a) with captured pose cells (§3.8c), so re-teaching a tray is an HMI task — — 1-D (2 points), 2-D (3 corners), 3-D (3 bottom corners + first top nest); the nests live in a referenced point list, and the PLC just **indexes a nest** (`RunPallet(PalletId, Nest)`). Next-nest tracking stays application-side — it is production state, not device state — but it **shall** be retained across a power cycle and republished, because a cell that forgets which nest it was on re-picks an empty one or overfills a full one on the next start. Nests are **per-gripper**, so a cell that mounts different grippers keeps one nest set per gripper rather than re-teaching on every tool change. Re-teaching the corners regenerates every nest (the reviewed cell's drawer trays are exactly this). **Chained frames** compound it: a pallet taught in a drawer frame follows the drawer — re-teach the one frame and every dependent pallet/point moves, no PLC change. Points → pallets → frames → RCS, each a re-teachable link.

---

## I.12a Deliberately out of scope: automatic tool change

`SET_TOOL(ToolId)` selects which taught tool a move is computed against. It does **not** perform a
physical tool change, and this annex does not model one. That is a scope decision, not an oversight:
an automatic gripper change is an **Equipment Module** concern, not a robot-CM one, and adding it
here would put station material-handling policy inside a device type (§3.5).

A cell that changes grippers automatically adds, above `FB_RobotCM` and beside it in the handling EM:

- a **coupling CM** (`FB_ToolClutchCM`, an ordinary two-position Annex A/B-pattern actuator) and the
  gripper CM already present;
- **tool identity**, read where the tool is stored — an RFID/DataMatrix read is an `I_PartCarrier`
  (Annex E) pointed at a tool rather than a part, so no new mechanism is needed;
- an EM command `CHANGE_TOOL` whose step chain classifies *(mounted tool identity, recipe-required
  family, magazine occupancy, clutch state)* → place / pick / already-correct, then composes the
  existing primitives;
- **tool-identity reasons** in the EM's own §8.8 band — mismatch against the recipe family, an
  unreadable tag, an occupied or empty magazine slot — with `ROBOT_TOOL_FRAME_CONFLICT` (10306)
  reserved here for the narrower case of the *controller's* tool/frame values disagreeing with the
  stored ones.

Only the last of those is missing from the standard today; everything else composes from Annexes A,
B and E. If tool identity must be reported to MES, the tool-change events are §11.6 host events like
any other — a robot cell does **not** get a private MES vocabulary (I.13).

---


## I.13 Composition with Annexes E / F (no duplication)

- **Traceability (Annex E).** The `SCAN_PART` / DMC reader **is** the `I_PartCarrier` of Annex E; the robot presents the part (a `MoveFromArea` to the scan position resolved via I.10) and the `Uid`/verdict flow through the four lifecycle events. A robot-caused NOK carries the robot's **own first-out reason** — one vocabulary, no parallel taxonomy.
- **PackML (Annex F).** Unchanged — the robot CM's `ExecState`/counters feed the projection like any other child.

---

## I.14 Testing the type against a simulated controller (Annex H)

`FB_RobotCM`, the route planner, and the **help resolver** are verified by TcUnit against a **simulated connector** (sim HAL, §2.6/§10) — no arm, CI-gated (§6.8):

```iecst
TEST('RunPath_completes_when_controller_reports_done');
TEST('RunPath_faults_first_out_on_unreachable_point');           // names the point (§6.9)
TEST('MoveTemplate_completes_for_a_routable_pair');              // I.9
TEST('MoveTemplate_faults_ROBOT_NO_ROUTE_when_graph_disconnected');
TEST('MoveFromArea_completes_from_a_known_area');               // I.11
TEST('MoveFromArea_faults_ROBOT_AREA_UNRESOLVED_when_pose_unknown');
TEST('ResolveHelp_scanjunction_picks_HELP5_when_other_endpoint_on_process_side');  // I.10 — region tie-break
TEST('ResolveHelp_scanjunction_picks_HELP4_when_other_endpoint_on_drawer_side');    // I.10 — both directions, no CASE
TEST('ResolveHelp_prefers_APPROACH_help_on_entry_and_DEPART_help_on_exit');         // I.10 — role-primary
TEST('ResolveHelp_NOK_reversal_exits_via_EITHER_entry_corridor_toward_origin');     // I.10.1 — reversal by construction
TEST('ResolveHelp_faults_ROBOT_NO_HELP_FOR_NEST_on_reversal_through_one_way_nest'); // I.10.1 — loud, not mis-routed
TEST('ResolveHelp_faults_ROBOT_NO_HELP_FOR_NEST_when_affinity_empty');
TEST('SafeStop_powers_off_and_no_auto_resume_when_alias_drops');       // §9.3/§9.4
TEST('Link_loss_rolls_up_LINK_TIMEOUT');                               // Annex D
TEST('Move_rejected_ROBOT_MODE_NOT_PERMITTED_when_controller_not_in_auto_remote');  // I.4a(a)
TEST('Jog_rejected_when_controller_not_in_a_manual_mode');                          // I.4a(a)
TEST('RequestedMode_stays_visibly_ungranted_when_controller_does_not_grant_it');     // I.4a(a)
TEST('SpeedScale_applied_is_MIN_of_mode_ceiling_and_recipe_scale');                 // I.4a(b)
TEST('SpeedScale_outside_band_faults_ROBOT_PARAM_OOR_before_any_motion');           // I.4a(b), §5.6
TEST('ProtectiveStop_aborts_and_faults_ROBOT_PROTECTIVE_STOP_not_the_safety_reason');// I.4a(c)
TEST('ProtectiveStop_does_not_auto_resume_and_requires_area_resolved_recovery');     // I.4a(c), I.11
TEST('Pick_faults_ROBOT_GRIP_LOST_when_gripper_closes_without_a_part');             // I.6a
TEST('Place_faults_ROBOT_GRIP_LOST_when_the_part_was_lost_in_transit');             // I.6a
TEST('Held_interrupts_on_path_and_resumes_from_the_retained_point');                // I.4b
TEST('Resume_faults_ROBOT_RESUME_INVALID_when_the_arm_was_jogged_while_held');      // I.4b
TEST('Held_rolls_up_as_LOW_severity_information_and_opens_no_reset_event');         // I.4b, §6.1
TEST('Offset_within_envelope_shifts_the_taught_target');                            // I.8a
TEST('Offset_outside_envelope_faults_ROBOT_PARAM_OOR_before_any_motion');           // I.8a, §14
```

The multi-help resolver being a **tested type** (not per-station code) is the whole point of I.10 — a station that adds a two-approach nest adds a table row, not logic.

---

## I.15 HMI (§3.13) — what the generic client renders, and what stays with the robot

The robot renders as a CM tile under the handling EM. The dividing line is **not** "everything taught
belongs to the vendor" — that was the wrong cut, and it is the one that makes a cell expensive to own
after commissioning. The right cut is between **kinematics** and **structured data**:

| Stays with the robot's own tool | Rendered by the generic HMI (§3.13) |
|---|---|
| Jogging the arm; the enabling device; reachability and singularity checking; the kinematic model | Which points are in a list, and in what order |
| The safety-rated hand-guiding function | Pallet corner sets and the grid they generate |
| Vendor calibration routines (mastering, absolute accuracy) | Tool and frame tables; planning-area definitions |
| — | Motion parameters, speed ceilings, offsets, list selection and active-point counts |

Everything in the right-hand column is a **bounded collection capability** (§3.10.2a) or an ordinary
scalar (§3.10.2) on the owning module. It therefore needs **no robot-specific HMI code at all**: the
generic client walks the module, finds the capabilities, and renders a grid or a form with the
editor it already has for each field type. Where the reference framework hand-builds five wizard
object pairs — point list, reference coordinate system, pallet, tool, area — this annex specifies
none, because publishing the data as capability *is* the wizard (§1.1 O1: paid once per mechanism,
never once per module type).

Pose-valued cells are filled by **teach capture** (§3.8c), not by typing six numbers. The operator
takes the robot to the position with its own jog under the §7.6 release, and captures: the module
writes its own published `ActualPosition` into that cell, `DATA_WRITE`-gated and audited. The
kinematics stayed with the robot; the number landed in Fraktal configuration.

What this buys is the case that actually recurs. **A new model** changes which list is selected and
how many of its points are active — scalars, resolved by `ModelId` at changeover like any other
recipe value, with no geometry edited at all. **A new gripper** adds a tool row and a nest set.
**A re-taught tray** is three captured corners, and every nest regenerates. None of it requires the
vendor's engineering tool, and all of it appears in the parameter set (§3.8b) and the audit log.

| View | Binding |
|------|---------|
| **Tile** | name; state LED ← `ExecState`; **link LED** ← `_conn.Linked`; `Referenced`; `CurrentArea`; `ActualMode`; current point/path. |
| **Detail** | release-gated `HOME` / `MOVE_TO` / `RUN_PATH` / `MOVE_TEMPLATE` / `MOVE_FROM_AREA` / jog (§7.6); the **resolved route preview** (below); live `Diagnostic.Description` (incl. *"no help for nest …"*, *"no route …"*, *"pose undefined …"*); last-seen; Reconnect. No auto-resume. |
| **Configuration** | the collection capabilities of §3.10.2a — point lists, pallet corners, tools, frames, areas — rendered generically, with per-cell capture (§3.8c). |

**Route preview is not optional decoration.** A route produced by the planner (I.9) is a *generated*
artifact: unlike a taught list, no one has ever seen it. The connector **shall** publish the resolved
point sequence for the pending move as read-only status, so an operator can see the path before
authorising it and a commissioning engineer can tell a bad affinity table from a bad taught point.
Generating routes instead of enumerating them is only an O3 improvement if the result is visible;
otherwise it trades a list someone can read for a graph they cannot.

---


## I.16 What this annex demonstrated

- A **whole robot as one Control Module** — point, taught path, **generated route**, or pallet nest, all one command in / `Busy/Done/Error` out — with a thin **handling EM** adding `PICK/PLACE/SCAN/PROCESS` semantics above it (the observed two-tier pattern), and **no coordinate, waypoint, motion mode, route, or help choice in PLC code** (I.1, I.6).
- **Dynamic trajectory generation** reframed as a **declarative routing graph** resolved by one generic planner — replacing six per-station imperative `User*` methods (I.9).
- **Native multi-help work positions** (I.10): a nest carries a **help-affinity list**; the planner resolves the serving help **role-first** (direction is the higher-consequence constraint), tie-breaking by region/proximity — turning the reference framework's hand-coded, state-reading two-help workaround into a two-line table, paid once and tested (Annex H). **NOK reversal** (I.10.1) falls out as an ordinary move to a different destination, exiting via the default-`EITHER` entry corridor back toward the origin, with a one-way nest failing *loudly* rather than mis-routing. Directly serves §1.1 O1 (low effort), reusability, and diagnosability.
- **Area-resolved motion** as the primary move and **pose recovery** as its extreme case, kept **distinct from the §9 safety system** and gated as a deliberate §9.4 reset (I.11).
- **Parametric/symmetric pallets**, **per-gripper nests**, and **chained frames** (I.12); the convergence of Annexes D and G with a robot fault rolling up the **same §6.9 stall walk** (I.7).
- **Composition, not duplication**: identity via Annex E, line coordination via Annex F, type/planner/resolver verification via Annex H (I.13–I.14).
- The three **mandatory device facts** no robot cell can be built without (I.4a): controller operating
  mode as a **request/report pair** that rejects a command the mode does not permit; speed as a
  **bounded scale** composing a per-mode station ceiling with a per-recipe process scale, so reduced
  speed outside automatic is a property of the type; and a **protective stop** (collision/crash) kept
  deliberately distinct from the §9 safety path, in its own reason and its own alarm record.
- **Grip verification** (I.6a): possession is proven, not assumed — checked after grip *and* before
  release, surfaced at the step where it failed, and feeding the existing NOK disposition path (I.10.1).
- **On-path hold and resume** (I.4b) built on the existing §6.1 `HELD` contract rather than a new
  handshake state — with `Resumable` making "the arm was moved while suspended" a clean refusal
  instead of a move through untaught space.
- **A bounded exception to "never a coordinate"** (I.8a): a vision-derived pose enters only as a
  validated correction to a taught reference, treated as untrusted input (§14), so the prohibition
  that mattered — no PLC-enumerated trajectory — survives intact.
- **An open multi-vendor standard named as the default binding** (I.5a: SRCI), turning §I.5's
  "conformant alternatives on the same interface" from a promise into a published contract, with
  everything the standard does not cover (routing, areas, pallets, the module contract) staying above it.
- **Taught geometry kept as Fraktal configuration** (I.1, I.15): point lists, pallet corners, tools,
  frames and areas are bounded collection capabilities (§3.10.2a) with captured pose cells (§3.8c),
  so they live inside changeover, parameter sets, access control and audit — and the generic HMI
  renders every one of them with **no robot-specific screen**, where the reference hand-builds five
  wizard object pairs. Kinematics, jogging and reachability stay with the robot, which is the real
  boundary.
- **Route preview as a requirement** (I.15): a generated route is only an O3 improvement over a
  taught list if the operator can see it.
- **Optional capability groups** (I.5b) — conveyor tracking, work-area/zone interlocking, force
  control, brake test and the rest — declared through `Features` and added as narrow secondary
  interfaces, so the common case keeps a small surface.
- A **per-module-type reason block** (robot CM `10301–10315`) in `PL_ModuleReasons` registered per §8.8,
  link reasons reusing the Framework band, each shipping with its rationalization entry and localization key.
- **Automatic tool change is explicitly out of scope** (I.12a) and named as an EM-tier composition of
  Annexes A, B and E — a decision, not an omission.

---

*End of Annex I (draft). Extends the worked-example set A–H referenced in §12.*
