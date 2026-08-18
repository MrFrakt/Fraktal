# Annex G — Worked Example: Motion Control Module (PLCopen Motion)

*Companion to **Fraktal Core** (Part I) exercised through the **Fraktal/TC3** binding (Part II); slots under Core §12.*
*Core concepts demonstrated: motion CM behind the handshake (§10.6), target validation (§5.6), read-only safety & no auto re-enable (§9), base-class inheritance (§2.2). / TC3 mechanics used: TwinCAT NC PLCopen Motion `MC_*`/`AXIS_REF` (`NcToPlc`), `OPC.UA.DA` pragmas (TC3 §3.10).*
*Reference implementation — illustrative, not compile-tested; validate against the pinned TwinCAT version and your axis/drive.*

This annex builds a **motion Control Module** (§10.6) and shows what the pneumatic CM of Annex A can't: an **axis driven through the PLCopen Motion `MC_*` blocks** behind the **same handshake** every other CM uses, with **target validation** before motion (§5.6) and a **safe stop on a dropped safety alias** (§9). To the Unit, a servo indexer looks identical to a cylinder — named commands in, `Busy/Done/Error` out.

It slots under the Annex A–C station as the infeed indexer:

```
InfeedUnit (FB_InfeedUnit : FB_Unit)                       ← Annex C
 └─ Indexer (FB_AxisCM, Control Module)                    ← here
       └─ MC_Power / MC_Home / MC_MoveAbsolute / MC_Stop / MC_Reset  (PLCopen Motion)
```

---

## G.1 Reasons (per-module-type block — register in §8.8)

```iecst
// E_Reason — axis CM band 10200–10299 (per module-type, §8.8)
//   AXIS_TARGET_OOR    := 10201   // commanded target outside soft limits (rejected, §5.6)
//   AXIS_MOVE_TIMEOUT  := 10202   // MC move did not complete within MoveTimeout
//   AXIS_DRIVE_FAULT   := 10203   // MC_* .Error / drive fault
//   AXIS_NOT_HOMED     := 10204   // MOVE_TO before a valid home

{attribute 'qualified_only'}
TYPE E_AxisCommand : (NONE := 0, HOME := 1, MOVE_TO := 2) DINT;
END_TYPE
```

---

## G.2 The axis CM (PLCopen Motion behind the handshake)

The CM holds the standard `AXIS_REF` and the `MC_*` instances; soft limits and scaling live in the driver/axis config (§10.3), not in sequences.

```iecst
// Publication is inherited from the explicitly marked deployed root instance.
// Execute/Abort arrive through the base's ExecuteCommand/AbortCommand, and
// Busy/Done/Error/Aborted/ErrorID plus first-out stamping are base-owned (§2.2):
// the type is only its device logic.
FUNCTION_BLOCK FB_AxisCM EXTENDS FB_ControlModuleBase
VAR_INPUT
    Command : E_AxisCommand;
    ParCfg  : ST_AxisParCfg;      // SchemaVersion, SoftMin/Max, Vel, Acc, Dec, MoveTimeout, HomeTimeout
    ParCmd  : ST_AxisParCmd;      // Target — latched by the base on the Execute rising edge
END_VAR
VAR_OUTPUT
    OutCmd : ST_AxisOutCmd;       // InPosition, Homed — valid on Done
    OutImm : ST_AxisOutImm;       // ActPos, ActVelocity, Homed, DriveEnabled, Diagnostic
    Intlk  : FB_PermIntlk;        // e.g. "STO cleared" / "Zone2 safe" (read-only, §9.2)
END_VAR
VAR
    _axis   : REFERENCE TO AXIS_REF;
    _step   : INT;  _homed : BOOL;
    _pwrFb  : MC_Power;  _homeFb : MC_Home;  _moveFb : MC_MoveAbsolute;
    _stopFb : MC_Stop;   _resetFb: MC_Reset;
    _tMove  : TON;
END_VAR

METHOD Setup : BOOL
VAR_INPUT Name : STRING(80); AxisRef : REFERENCE TO AXIS_REF; Recipe : I_RecipeProvider; END_VAR
    THIS^._axis REF= AxisRef;
    // This type declares NO interlock of its own: safe motion lives in the certified
    // system and a library cannot name "STO cleared" for a station it has never seen.
    // The application supplies that status through DeclareCondition/SetCondition (§9.2).
    // recipe wiring (limits, velocities) as Annex A …
```

### Cyclic body

`OnCyclic` is the type's device logic only — the Execute edge, `ExecState`, the `Busy`/`Done`/
`Error`/`Aborted`/`ErrorID` outputs, first-out stamping and reset are all base-owned (§2.2) and
proven once in `FB_Base_Tests` (§5.7):

```iecst
METHOD PROTECTED OnCyclic
// power + safety: enable only while the application's safety condition is healthy (§9.2/§9.3)
_pwrFb(Axis := _axis, Enable := TRUE, Enable_Positive := Intlk.AllOk, Enable_Negative := Intlk.AllOk);

IF NOT Intlk.AllOk AND Busy THEN
    _M_SafeStop();                                   // G.4
END_IF

OutImm.ActPos       := _axis.NcToPlc.ActPos;
OutImm.ActVelocity  := _axis.NcToPlc.ActVelo;
OutImm.Homed        := _homed;
OutImm.DriveEnabled := _pwrFb.Status;
```

---

## G.3 The move command — validate target first (§5.6), map `MC_*` to the handshake

Validate the **request** before the **state**, and both before commanding motion: a target outside
the soft limits is malformed whether or not the axis is homed, and reporting "not homed" for an
impossible target sends the operator to the wrong problem. It also makes both rejections provable
without a licensed NC axis, since neither issues an `MC_*` call.

```iecst
METHOD PROTECTED _M_Dispatch
IF (ParCmd.Target < ParCfg.SoftMin) OR (ParCmd.Target > ParCfg.SoftMax) THEN
    _M_FaultN(Code := PL_ModuleReasons.AXIS_TARGET_OOR, Text := 'std.error.axisTargetOutOfRange');
    RETURN;
END_IF
IF NOT _homed THEN
    _M_FaultN(Code := PL_ModuleReasons.AXIS_NOT_HOMED, Text := 'std.error.axisNotHomed');
    RETURN;
END_IF
IF NOT __ISVALIDREF(_axis) THEN
    _M_FaultN(Code := PL_ModuleReasons.AXIS_DRIVE_FAULT, Text := 'std.error.axisNotBound');
    RETURN;
END_IF

CASE _step OF
    10:
        OutCmd.InPosition := FALSE;
        _moveFb(Axis := _axis, Execute := FALSE);
        _tMove(IN := FALSE);
        _step := 20;
    20:  // issue the PLCopen move; map its outputs onto the CM handshake (§6.1)
        _moveFb(Axis := _axis, Execute := TRUE, Position := ParCmd.Target,
                Velocity := ParCfg.Velocity, Acceleration := ParCfg.Acceleration,
                Deceleration := ParCfg.Deceleration);
        _tMove(IN := TRUE, PT := ParCfg.MoveTimeout);
        IF _moveFb.Done THEN
            _moveFb(Axis := _axis, Execute := FALSE);
            _tMove(IN := FALSE);
            OutCmd.InPosition := TRUE;
            _M_Complete();
        ELSIF _moveFb.Error THEN
            _M_FaultStopped(Code := PL_ModuleReasons.AXIS_DRIVE_FAULT, Text := 'std.error.axisDriveFault');
        ELSIF _moveFb.CommandAborted THEN
            // Another motion command took the axis: that is an abort, not a defect —
            // route it through the base's own abort path rather than inventing a fault.
            AbortCommand();
        ELSIF _tMove.Q THEN
            _M_FaultStopped(Code := PL_ModuleReasons.AXIS_MOVE_TIMEOUT, Text := 'std.error.axisMoveTimeout');
        END_IF
ELSE
    _M_Fault(E_Reason.STEP_STALLED, 'std.error.undefinedStep');        // defined ELSE (§5.6)
END_CASE
```

`MC_MoveAbsolute`'s `Busy/Done/Error/CommandAborted` map one-to-one onto the CM handshake, so the
parent Unit commands `MOVE_TO` exactly as it commands a cylinder `EXTEND` — it neither knows nor
cares that a servo is involved (§6.1).

---


## G.4 Safe stop on a dropped alias (§9)

Safe-motion stays in the safety system; the CM only **reads** its status and reacts:

```iecst
METHOD PRIVATE _M_SafeStop
    _stopFb(Axis := _axis, Execute := TRUE, Deceleration := ParCfg.Deceleration);   // controlled stop
    _M_FaultStopped(Code := PL_ModuleReasons.AXIS_DRIVE_FAULT, Text := 'std.error.axisSafetyDropped');
```

The condition itself is **not** declared by this type: a library cannot name "STO cleared" for a
station it has never seen, so the application supplies it through `DeclareCondition`/`SetCondition`
and the type only reads `Intlk.AllOk` (§9.2).

The motion is brought to the §6 defined safe stop; re-enable after the alias returns is a deliberate reset (`MC_Reset`, then re-home if required), never automatic (§9.3, §9.4).

---

## G.5 HMI (§3.13)

```
Station ▸ Indexer            (CM tile: state LED ← ExecState; pos 124.80 mm; Homed ●)
```

| View | Binding |
|------|---------|
| **Tile** | name; state LED ← `ExecState`; live `ActPos`; **Homed** LED. |
| **Detail** | manual `HOME` / `MOVE_TO <target>` (release-gated, §7.6; target validated per §5.6); jog; the live `Diagnostic.Description` (e.g. *"Target outside soft limits"*). |

---

## G.6 What this annex demonstrated

- An axis expressed through **PLCopen Motion `MC_*`** blocks, **vendor-neutral**, mapped onto the standard handshake so a motion CM is indistinguishable from any other CM to its parent (§10.6, §6.1).
- **Target validation before motion** (`AXIS_TARGET_OOR`, `AXIS_NOT_HOMED`) — defensive coding (§5.6) producing a clean first-out reason instead of a drive crash.
- **Limits/scaling in the driver/axis** (§10.3), not in sequences.
- **Safe-motion read-only**: a dropped safety alias triggers `MC_Stop` and a fault, with no automatic re-enable (§9.2–§9.4).
- A new **per-module-type reason block** (axis CM `10201–10204`) registered per §8.8.

---

*End of Annex G (draft).*
