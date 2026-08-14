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

Re-teaching one link regenerates everything downstream — re-teach a drawer **frame** and every pallet/point follows; re-teach pallet **corners** and every nest regenerates; edit the **affinity table** and routing changes with no code. This is §3.8 "recipe, not code" taken to its structural conclusion.

---

## I.2 Reasons (per-module-type block — register in §8.8)

```iecst
// E_Reason — robot CM band 10300–10399 (per module-type, §8.8)
//   ROBOT_POINT_UNREACHABLE  := 10301   // taught point not reachable with active tool/frame (rejected, §5.6)
//   ROBOT_POINT_UNKNOWN      := 10302   // point/list/pallet ID not in the controller's database
//   ROBOT_MOVE_TIMEOUT       := 10303   // point/path did not complete within MoveTimeout
//   ROBOT_CONTROLLER_FAULT   := 10304   // drive/controller fault reported by the robot
//   ROBOT_NOT_REFERENCED     := 10305   // MOVE/RUN before a valid home/reference
//   ROBOT_TOOL_FRAME_CONFLICT:= 10306   // controller tool/frame values differ from the stored values
//   ROBOT_SAFETY_DROPPED     := 10307   // STO / safe-zone / E-stop dropped during motion (read-only, §9)
//   ROBOT_NO_ROUTE           := 10308   // routing model defines no path between the two positions (I.9)
//   ROBOT_AREA_UNRESOLVED    := 10309   // current planning area not resolvable (I.11)
//   ROBOT_NO_HELP_FOR_NEST   := 10310   // no help point resolves for a nest given the move endpoints (I.10)

// Link supervision reuses the Annex D Framework band (LINK_TIMEOUT := 2010, …).

{attribute 'qualified_only'}
TYPE E_RobotCommand : (
    NONE := 0, POWER_ON := 1, POWER_OFF := 2, HOME := 3, MOVE_TO := 4, RUN_PATH := 5,
    RUN_PALLET := 6, MOVE_TEMPLATE := 7, MOVE_FROM_AREA := 8, SET_TOOL := 9, SET_FRAME := 10
) DINT;
END_TYPE
```

---

## I.3 The connector contract (`I_RobotConnector`)

`I_RobotConnector` is `I_DeviceConnector` (Annex D) plus the **primitive** robot surface observed in real applications — arm power, point/path execution, **template-generated** motion (from a known position *or* resolved from the current area), pallet nests, and ID-addressed element management. Everything below it — protocol, point database, kinematics, path planning, the routing model — is confined to the connector (§3.15).

```iecst
INTERFACE I_RobotConnector EXTENDS I_DeviceConnector
    // ── power / referencing ─────────────────────────────────────────────
    METHOD PowerOn  : BOOL   METHOD PowerOff : BOOL   METHOD Home : BOOL      // SET_ARM_POWER / home
    // ── point / path execution (taught data, ID-addressed) ──────────────
    METHOD MoveToPoint : BOOL (PointId : DWORD)                              // EXECUTE_ROBOT_POINT
    METHOD RunPath     : BOOL (ListId : DWORD; StartIdx, EndIdx : DINT)      // EXECUTE_ROBOT_PATH_*  ((-1,-1)=whole)
    METHOD RunPallet   : BOOL (PalletId : DWORD; Nest : DINT)                // one generated nest
    // ── template-generated motion (the connector computes the route) ─────
    METHOD MoveTemplate  : BOOL (FromPosId, ToPosId : DWORD)                 // POS_TO_POS — start is a known position
    METHOD MoveFromArea  : BOOL (ToPosId : DWORD)                            // AREA_TO_POS — start resolved from current area (I.11)
    // ── element selection / management (configuration, by ID) ───────────
    METHOD SetTool  : BOOL (ToolId : DWORD)    METHOD SetFrame : BOOL (FrameId : DWORD)   // frame may be chained (I.12)
    METHOD Jog      : BOOL (Mode : E_JogMode; Axis : INT; Dir : INT)         // manual only, release-gated (§7.6)
    METHOD Abort    : BOOL
    // ── status ──────────────────────────────────────────────────────────
    PROPERTY Referenced  : BOOL       PROPERTY Busy : BOOL
    PROPERTY CurrentArea : DWORD                                            // planning area the TCP is in (0 = none/undefined)
    PROPERTY LastResult  : ST_Diagnostic                                   // first-out reason + SourcePath
    // (Linked / LastSeen / LinkReason / Cyclic inherited from I_DeviceConnector, Annex D)
END_INTERFACE
```

`MoveTemplate` (known start) and `MoveFromArea` (start resolved live from the current area) are **both everyday motion commands** — the real application uses area-resolved moves as its *primary* form because they are robust to wherever the arm currently is; pose recovery (I.11) is one important use of the same primitive, not a separate mode.

---

## I.4 The Control Module (`FB_RobotCM`)

`FB_RobotCM` exposes the ordinary CM handshake (§6.1). Its additions over a plain CM are Annex D's *“every command first requires `Linked`”*, Annex G's *validate-then-command / read-only safety*, and dropping **arm power** on a safety-alias loss.

```iecst
// Publication is inherited from the explicitly marked deployed root instance.
FUNCTION_BLOCK FB_RobotCM IMPLEMENTS I_ControlModule
VAR_INPUT
    Execute : BOOL;  Command : E_RobotCommand;  Abort : BOOL;
    TargetId : DWORD;              // point/list/pallet/tool/frame — or the TO position (MOVE_TEMPLATE/MOVE_FROM_AREA)
    FromId   : DWORD;              // FROM position (MOVE_TEMPLATE only)
    Nest     : DINT;               // nest index (RUN_PALLET only)
    StartIdx, EndIdx : DINT;       // sub-path bounds (RUN_PATH; -1,-1 = whole list)
END_VAR
VAR_OUTPUT Busy, Done, Error, Aborted : BOOL; ErrorID : DWORD; END_VAR
VAR  _conn : I_RobotConnector;  OutImm : RobotOutImm;  _name : STRING(80);
     _exec : E_ExecState;  _step : INT;  _rTrig : R_TRIG;  tMove : TON;
     SafeIntlk : FB_PermIntlk;  END_VAR                      // read-only safety alias (§9.2)
```

Cyclic body is Annex D §D.3 + Annex G safe-stop; the dispatch validates first (§5.6), then issues the ID-addressed primitive, then maps the reply onto `ExecState`:

```iecst
// safety is read-only: a dropped alias mid-command → PowerOff + controlled stop + fault, no auto re-enable (§9.3/§9.4)
IF NOT SafeIntlk.AllOk AND _exec = E_ExecState.BUSY THEN
    _conn.Abort();  _conn.PowerOff();
    _M_Fault(E_Reason.ROBOT_SAFETY_DROPPED, 'Safety dropped during motion');
END_IF
...
METHOD PRIVATE _M_Dispatch
CASE _step OF
  10:  // defensive coding (§5.6): reject impossible commands before they reach the floor
    IF NOT _conn.Linked THEN _M_Fault(E_Reason.LINK_TIMEOUT, 'Robot link not up'); RETURN; END_IF
    IF (Command IN (E_RobotCommand.MOVE_TO, E_RobotCommand.RUN_PATH, E_RobotCommand.RUN_PALLET,
                    E_RobotCommand.MOVE_TEMPLATE, E_RobotCommand.MOVE_FROM_AREA)) AND NOT _conn.Referenced THEN
        _M_Fault(E_Reason.ROBOT_NOT_REFERENCED, 'Command before reference'); RETURN;
    END_IF
    _step := 20;
  20:  // issue the ID-addressed primitive; FALSE = unknown/unreachable/no-route/no-help → first-out reason (§5.6)
    CASE Command OF
      E_RobotCommand.POWER_ON:      _conn.PowerOn();
      E_RobotCommand.POWER_OFF:     _conn.PowerOff();
      E_RobotCommand.HOME:          _conn.Home();
      E_RobotCommand.MOVE_TO:       IF NOT _conn.MoveToPoint(TargetId)               THEN _M_Fault(_conn.LastResult); RETURN; END_IF
      E_RobotCommand.RUN_PATH:      IF NOT _conn.RunPath(TargetId, StartIdx, EndIdx) THEN _M_Fault(_conn.LastResult); RETURN; END_IF
      E_RobotCommand.RUN_PALLET:    IF NOT _conn.RunPallet(TargetId, Nest)           THEN _M_Fault(_conn.LastResult); RETURN; END_IF
      E_RobotCommand.MOVE_TEMPLATE: IF NOT _conn.MoveTemplate(FromId, TargetId)      THEN _M_Fault(_conn.LastResult); RETURN; END_IF  // I.9
      E_RobotCommand.MOVE_FROM_AREA:IF NOT _conn.MoveFromArea(TargetId)              THEN _M_Fault(_conn.LastResult); RETURN; END_IF  // I.11
      E_RobotCommand.SET_TOOL:      _conn.SetTool(TargetId);
      E_RobotCommand.SET_FRAME:     _conn.SetFrame(TargetId);
    END_CASE
    tMove(IN := TRUE, PT := _M_TimeoutFor(Command)); _step := 30;   // per-command timeout from recipe (audit R2);
    // the Unit step's ExpectedTime (§6.5) remains the outer guard
  30:  // map controller Busy/Done/Error/timeout onto ExecState (§6.1)
    IF NOT _conn.Busy AND _conn.LastResult.ReasonCode = E_Reason.NONE THEN
        tMove(IN := FALSE); _exec := E_ExecState.DONE; _step := 0; _M_ClearDiag();
    ELSIF _conn.LastResult.ReasonCode <> E_Reason.NONE THEN  _M_Fault(_conn.LastResult);
    ELSIF Abort THEN  _conn.Abort(); _exec := E_ExecState.ABORTED; _step := 0;
    ELSIF tMove.Q THEN  _M_Fault(E_Reason.ROBOT_MOVE_TIMEOUT, 'Command did not complete');
    END_IF
END_CASE
```

A point, a 26-point path, a generated route, or a pallet nest is **one** command that runs to completion — so the robot looks identical to any other CM (§6.1). Commands are **not** auto-repeated on error; resumption is deliberate (Annex D / §9.3).

---

## I.5 Default vs. alternative connectors, and *why the portable one is the default* (§12)

`I_RobotConnector` is the injected seam, like `I_RecipeProvider` (§3.8) and `I_PartCarrier` (Annex E) — brand is configuration, not code. The framework controls robots **regardless of model or manufacturer** by capturing per-model facts (digital-signal counts to the PLC, Euler conventions, supported functions) as a **per-robot record the connector reads at runtime** — so `FB_PortableTeachConnector` is the **recommended default** (brand differences are *data*, not *branches in app code*), and per-vendor connectors are **conformant alternatives** on the same interface, parent Unit unchanged. Exposing a robot via the portable framework is a **§12 conformance option** (claimed like §11.7), not a mandate — but the recommended path.

---

## I.6 The two tiers — robot **CM** (primitive) vs. handling **EM** (semantic)

The reference application does not command the robot with pick/place semantics directly. It uses **two tiers**, which map exactly onto the standard:

- **`FB_RobotCM`** (this annex) = the robot **object / connector**: the primitive surface (`MOVE_TEMPLATE`, `MOVE_FROM_AREA`, `RUN_PATH`, `MOVE_TO`, `POWER_ON`…). This is the Control Module.
- **`FB_RobotHandlingEM`** = a thin **Equipment Module** exposing the station's *semantic* operations — `PICK_PART`, `PLACE_PART`, `PLACE_PART_NOK`, `SCAN_PART`, `PROCESS_PART`, `CHECK_TOOL`, `HOME`, `MOVE_REF` — each a short completing step chain that composes the robot CM's primitives with the gripper/tool CMs, **adding no device logic** (Annex B §3.5). For example `PICK_PART` ≈ `MOVE_FROM_AREA(nest)` → gripper close → `MOVE_TEMPLATE(nest, transitHelp)`.

Surface (consumed by Annex C):

```iecst
{attribute 'qualified_only'}
TYPE E_HandlingCommand : (NONE := 0, PICK_PART := 1, PLACE_PART := 2, PLACE_PART_NOK := 3,
                          SCAN_PART := 4, PROCESS_PART := 5, CHECK_TOOL := 6, HOME := 7) DINT;
END_TYPE

FUNCTION_BLOCK FB_RobotHandlingEM IMPLEMENTS I_EquipmentModule
VAR_INPUT  Execute : BOOL; Command : E_HandlingCommand; TargetId : DWORD; Nest : DINT; Abort : BOOL; END_VAR
VAR_OUTPUT Busy, Done, Error, Aborted : BOOL; ErrorID : DWORD; END_VAR
VAR  Robot130 : FB_RobotCM;  _conn : FB_PortableTeachConnector;  Gripper : FB_GripperCM;   // trivial Annex A/B-pattern CM: OPEN/CLOSE + part-present feedback  END_VAR
METHOD Setup : BOOL   // wires the connector + CM internally (§3.11); Endpoint/tool ids from recipe
VAR_INPUT Name : STRING(80); Endpoint : STRING(255); Recipe : I_RecipeProvider; END_VAR
// each command = a short completing step chain composing Robot130 + Gripper (Annex B §3.5), e.g.:
//   PROCESS_PART   → Robot130.RUN_PATH(TargetId)
//   PLACE_PART_NOK → Gripper.CLOSE → Robot130.MOVE_TEMPLATE(current, TargetId) → Gripper.OPEN
// child Error → _M_RollupFault() adopts Robot130/Gripper first-out (§8.2), exactly as FB_ClampEM (Annex B §B.4)
```

So the earlier "a robot is just a CM" is precise at the device tier; a station simply adds an EM of semantic ops above it — the ordinary Annex B pattern. The parent Unit (Annex C) commands `RobotHandling.PROCESS_PART` / `PLACE_PART_NOK`, one handshake command exactly like `ClampStation.CLAMP`.

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

---

## I.9 Dynamic trajectory generation — a **declarative** routing model (simpler than imperative `User*` methods)

> **Promoted to Core.** The routing model of this section and I.10 is now **normative platform-neutral content — Core §10.7**; I.9–I.10 remain its worked realization against the reference robot framework.

The framework generates the route between any two positions at runtime. Positions are two classes: **help points** (auxiliary / **wait/transit** positions) and **nests** (**work** positions). The reference framework expresses routing through six imperative methods the application engineer fills **per station** with `CASE` logic — `UserHelpToHelp`, `UserHelpToNest`, `UserNestToHelp`, `UserNestToNest`, `UserManipulateGeneratedList`, `UserAreas`. That is exactly the per-application boilerplate the objectives discourage (§1.1 O1, NG2).

**This standard makes routing declarative data resolved by one generic planner in the connector.** The application supplies *configuration*, not traversal code:

```iecst
TYPE ST_RouteGraph : STRUCT
    HelpAdj  : ARRAY[1..MAX_HELPS, 1..MAX_HELPS] OF BOOL;   // help↔help adjacency (which transits are allowed)
    NestHelp : ARRAY[1..MAX_NESTS] OF ST_NestHelpAffinity;  // each nest → one OR MORE serving help points (I.10)
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
    a := _graph.NestHelp[nest];
    IF a.Count = 0 THEN _M_SetReason(E_Reason.ROBOT_NO_HELP_FOR_NEST, nest); RETURN; END_IF
    // 1) VALIDITY FILTER — keep only corridors legal for this direction (EITHER is always legal)
    nCand := 0;
    FOR i := 1 TO a.Count DO
        IF a.Helps[i].Role = dir OR a.Helps[i].Role = E_HelpRole.EITHER THEN
            nCand := nCand + 1;  cand[nCand] := a.Helps[i];
        END_IF
    END_FOR
    IF nCand = 0 THEN _M_SetReason(E_Reason.ROBOT_NO_HELP_FOR_NEST, nest); RETURN; END_IF  // one-way nest, wrong way
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

The framework **generates the whole pallet grid from a few taught corners** — 1-D (2 points), 2-D (3 corners), 3-D (3 bottom corners + first top nest); the nests live in a referenced point list, and the PLC just **indexes a nest** (`RunPallet(PalletId, Nest)`), next-nest tracking staying application-side. Nests are **per-gripper** (`Gripper1`/`Gripper2` enums), matching the dual-gripper cell. Re-teaching the corners regenerates every nest (the station's 4×4, 3×4 and 3×1 pallets are exactly this). **Chained frames** compound it: a pallet taught in a drawer frame follows the drawer — re-teach the one frame and every dependent pallet/point moves, no PLC change. Points → pallets → frames → RCS, each a re-teachable link.

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
```

The multi-help resolver being a **tested type** (not per-station code) is the whole point of I.10 — a station that adds a two-approach nest adds a table row, not logic.

---

## I.15 HMI (§3.13)

The robot renders as a CM tile under the handling EM; **teaching, pallets, areas, the route graph and affinities stay in the robot controller's engineer tool** — the PLC HMI shows status + release-gated manual commands, not a re-hosted teach pendant.

| View | Binding |
|------|---------|
| **Tile** | name; state LED ← `ExecState`; **link LED** ← `_conn.Linked`; **Referenced**; **CurrentArea**; current point/path. |
| **Detail** | release-gated `HOME` / `MOVE_TO` / `RUN_PATH` / `MOVE_TEMPLATE` / `MOVE_FROM_AREA` / jog (§7.6); live `Diagnostic.Description` (incl. *"no help for nest …"*, *"no route …"*, *"pose undefined …"*); last-seen; Reconnect. No auto-resume. |

---

## I.16 What this annex demonstrated

- A **whole robot as one Control Module** — point, taught path, **generated route**, or pallet nest, all one command in / `Busy/Done/Error` out — with a thin **handling EM** adding `PICK/PLACE/SCAN/PROCESS` semantics above it (the observed two-tier pattern), and **no coordinate, waypoint, motion mode, route, or help choice in PLC code** (I.1, I.6).
- **Dynamic trajectory generation** reframed as a **declarative routing graph** resolved by one generic planner — replacing six per-station imperative `User*` methods (I.9).
- **Native multi-help work positions** (I.10): a nest carries a **help-affinity list**; the planner resolves the serving help **role-first** (direction is the higher-consequence constraint), tie-breaking by region/proximity — turning the reference framework's hand-coded, state-reading two-help workaround into a two-line table, paid once and tested (Annex H). **NOK reversal** (I.10.1) falls out as an ordinary move to a different destination, exiting via the default-`EITHER` entry corridor back toward the origin, with a one-way nest failing *loudly* rather than mis-routing. Directly serves §1.1 O1 (low effort), reusability, and diagnosability.
- **Area-resolved motion** as the primary move and **pose recovery** as its extreme case, kept **distinct from the §9 safety system** and gated as a deliberate §9.4 reset (I.11).
- **Parametric/symmetric pallets**, **per-gripper nests**, and **chained frames** (I.12); the convergence of Annexes D and G with a robot fault rolling up the **same §6.9 stall walk** (I.7).
- **Composition, not duplication**: identity via Annex E, line coordination via Annex F, type/planner/resolver verification via Annex H (I.13–I.14).
- A **per-module-type reason block** (robot CM `10301–10310`) registered per §8.8, link reasons reusing the Framework band.

---

*End of Annex I (draft). Extends the worked-example set A–H referenced in §12.*
