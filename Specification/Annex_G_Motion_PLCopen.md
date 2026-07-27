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
FUNCTION_BLOCK FB_AxisCM IMPLEMENTS I_ControlModule
VAR_INPUT  Execute : BOOL; Command : E_AxisCommand; Target : LREAL; Abort : BOOL; END_VAR
VAR_OUTPUT Busy, Done, Error, Aborted : BOOL; ErrorID : DWORD; END_VAR
VAR
    Axis    : AXIS_REF;
    ParCfg  : AxisParCfg;         // SoftMin, SoftMax, Vel, Acc, Dec, MoveTimeout
    OutImm  : AxisOutImm;         // ActPos, Homed, Diagnostic
    _name   : STRING(80);
    _exec   : E_ExecState;  _step : INT;  _homed : BOOL;
    _pwr    : MC_Power;  _home : MC_Home;  _move : MC_MoveAbsolute;
    _stop   : MC_Stop;   _reset: MC_Reset;
    tMove   : TON;       _rTrig: R_TRIG;
    SafeIntlk : FB_PermIntlk;     // e.g. "STO cleared" / "Zone2 safe" (read-only, §9.2)
END_VAR

METHOD Setup : BOOL
VAR_INPUT Name : STRING(80); AxisRef : REFERENCE TO AXIS_REF; Recipe : I_RecipeProvider; END_VAR
    THIS^._name := Name;  THIS^.Axis REF= AxisRef;
    SafeIntlk.Define(1, 'STO cleared', E_Reason.INTERLOCK_DROPPED);   // §9.2 status, read-only
    // recipe wiring (limits, velocities) as Annex A …
```

### Cyclic body

```iecst
// power + safety: enable only while the safety alias is healthy (§9.2/§9.3)
_pwr(Axis := Axis, Enable := TRUE, Enable_Positive := SafeIntlk.AllOk, Enable_Negative := SafeIntlk.AllOk);

IF NOT SafeIntlk.AllOk AND _exec = E_ExecState.BUSY THEN
    _M_SafeStop(E_Reason.INTERLOCK_DROPPED, 'STO/zone dropped during move');   // G.4
END_IF

_rTrig(CLK := Execute);
IF _rTrig.Q AND _exec = E_ExecState.READY THEN _exec := E_ExecState.BUSY; _step := 10; END_IF

IF _exec = E_ExecState.BUSY THEN
    CASE Command OF
        E_AxisCommand.HOME:    _M_Home();
        E_AxisCommand.MOVE_TO: _M_MoveTo();
    END_CASE
END_IF

OutImm.ActPos := Axis.NcToPlc.ActPos;  OutImm.Homed := _homed;
Busy := (_exec = E_ExecState.BUSY);  Done := (_exec = E_ExecState.DONE);
Error := (_exec = E_ExecState.ERROR);  Aborted := (_exec = E_ExecState.ABORTED);
ErrorID := TO_DWORD(OutImm.Diagnostic.ReasonCode);
IF NOT Execute AND _exec IN (E_ExecState.DONE, E_ExecState.ERROR, E_ExecState.ABORTED) THEN
    _exec := E_ExecState.READY;
END_IF
```

*With the framework base class (§2.2), this entire cyclic body is **inherited**: a conforming `FB_AxisCM EXTENDS FB_ControlModuleBase` keeps only the safety/power lines and the `_M_Home`/`_M_MoveTo` dispatch — the Execute edge, state mapping, reset, and `ErrorID` publication come from the base. The expanded form is shown here for pedagogy.*

---

## G.3 The move command — validate target first (§5.6), map `MC_*` to the handshake

```iecst
METHOD PRIVATE _M_MoveTo
CASE _step OF
  10:  // defensive coding: reject an out-of-range or un-homed move before commanding motion
    IF NOT _homed THEN  _M_Fault(E_Reason.AXIS_NOT_HOMED, 'Move before home');  RETURN;  END_IF
    IF (Target < ParCfg.SoftMin) OR (Target > ParCfg.SoftMax) THEN
        _M_Fault(E_Reason.AXIS_TARGET_OOR, 'Target outside soft limits');  RETURN;        // §5.6
    END_IF
    _move(Axis := Axis, Execute := FALSE);  _step := 20;

  20:  // issue the PLCopen move; map its outputs onto the CM handshake (§6.1)
    _move(Axis := Axis, Execute := TRUE, Position := Target,
          Velocity := ParCfg.Vel, Acceleration := ParCfg.Acc, Deceleration := ParCfg.Dec);
    tMove(IN := TRUE, PT := ParCfg.MoveTimeout);
    IF _move.Done THEN
        _move(Axis := Axis, Execute := FALSE);  tMove(IN := FALSE);
        _exec := E_ExecState.DONE;  _step := 0;  _M_ClearDiag();
    ELSIF _move.Error THEN
        _M_Fault(E_Reason.AXIS_DRIVE_FAULT, 'Drive/move error');
    ELSIF _move.CommandAborted THEN
        _exec := E_ExecState.ABORTED;  _step := 0;
    ELSIF tMove.Q THEN
        _M_Fault(E_Reason.AXIS_MOVE_TIMEOUT, 'Move did not complete');
    END_IF
END_CASE
```

`MC_MoveAbsolute`'s `Busy/Done/Error/CommandAborted` map one-to-one onto the CM's `ExecState`, so the parent Unit commands `MOVE_TO` exactly as it commands a cylinder `EXTEND` — it neither knows nor cares that a servo is involved (§6.1).

---

## G.4 Safe stop on a dropped alias (§9)

Safe-motion stays in the safety system; the CM only **reads** its status and reacts:

```iecst
METHOD PRIVATE _M_SafeStop
VAR_INPUT reason : E_Reason; text : STRING(120); END_VAR
    _stop(Axis := Axis, Execute := TRUE, Deceleration := ParCfg.Dec);   // controlled stop
    OutImm.Diagnostic := _M_MakeDiag(reason, text, _name);
    _exec := E_ExecState.ERROR;
```

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
