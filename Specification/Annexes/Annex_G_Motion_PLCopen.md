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
//   AXIS_JOG_NOT_ENABLED := 10205 // teach jog asked with no enabling device held (G.4a)
//   AXIS_JOG_RELEASED    := 10206 // the held jog request stopped arriving (G.4a)

{attribute 'qualified_only'}
// JOG_POS/JOG_NEG are HELD commands (§7.6.1a): two entries rather than one plus a
// direction, so a generic HMI renders two hold-buttons with no axis-specific code.
// They never reach _M_Dispatch — a jog is not an Execute/Done command.
TYPE E_AxisCommand : (NONE := 0, HOME := 1, MOVE_TO := 2, JOG_POS := 3, JOG_NEG := 4) DINT;
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

## G.4a Teach jog under an enabling device (§7.6.1a, §9)

An axis has no teach pendant. Where a robot arrives with its own enabling device and its own jog, a
servo axis has neither — so if Fraktal does not offer a conformant way to move one by hand, there
isn't one, and the gap gets filled per station with something worse.

The axis therefore publishes two **held** commands and accepts them through `RequestHeldCommand`:

```iecst
_M_PublishHeldCommand(Value := TO_DINT(E_AxisCommand.JOG_POS), Label := 'std.command.jogPositive');
_M_PublishHeldCommand(Value := TO_DINT(E_AxisCommand.JOG_NEG), Label := 'std.command.jogNegative');
```

Every gate is weighed once per scan, in one place, so there is one thing to review:

```iecst
drive := (_jogReqDir <> 0)
    AND NOT _tJogStale.Q      // the request is still arriving (§7.6.1a, O10)
    AND _jogEnabled           // a safety-rated enabling device is permitting (§9)
    AND Intlk.AllOk           // the module's own interlocks — NOT bypassed for teaching
    AND NOT Busy              // a commanded move owns the axis (§6.1)
    AND __ISVALIDREF(_axis);
```

Four things about this are deliberate:

- **Interlocks are not bypassed.** The station is expected to have wired its guard condition so the
  safety system's teach grant satisfies it. If it has not, the axis simply does not jog. The enabling
  device is an **additional** requirement layered on the interlock, never a replacement — so a
  mis-wired station fails safe rather than gaining a back door.
- **`ParCfg.JogVelocity` is defence in depth, not the protection.** The safety-rated reduced speed is
  the drive's SLS or the cell's safe-speed monitor. A limit a scan overrun or a download can remove is
  not what keeps a person safe.
- **Stopping is not a fault.** A jog that ends because the operator let go is the designed behaviour,
  so it publishes `OutImm.JogStopReason` as status and raises no alarm — the same argument §6.1 makes
  for `HELD`. Filing it as a fault would fill the record with events that were never faults.
- **A functional stop stops the jog too.** `WithdrawOutputs` withdraws it like any other output;
  otherwise an abort would stop the commanded move and leave a jog running.

The `MC_Jog` realization is **[TC3]**; another binding supplies its own level-driven jog behind the
same `RequestHeldCommand` contract (O8).

---

## G.4b Teaching the position — the other half of the jog (§3.8c)

Jogging an axis is only useful if where you got to can be kept. The axis therefore registers a
taught position as an ordinary editable value and offers a **capture** for it:

```iecst
M_RegisterConfigNumber(Key := 'axis.taughtPosition', Kind := E_ConfigKind.STATION_CFG,
    Storage := E_ConfigStorage.AS_LREAL, pTarget := ADR(_station.TaughtPosition),
    Minimum := ParCfg.SoftMin, Maximum := ParCfg.SoftMax, ...);
M_RegisterCapture(WriteKey := 'axis.taughtPosition',
    pSource := ADR(OutImm.ActPos), SourceStorage := E_ConfigStorage.AS_LREAL);
```

- **`STATION_CFG`, not `PAR_CFG`.** A taught position is what this *machine* is, not what the current
  product needs. It also could not live in `ParCfg` even if one wanted it to: `I_RecipeProvider` has
  `Load` and no `Store`, so the next changeover would overwrite a number an operator spent time
  teaching.
- **The capture rides the field it writes.** `M_RegisterCapture` refuses a key that is not already
  registered as editable, so §3.8c(a)'s "a capture reaches only an already-editable field" is
  structural rather than a check someone could forget. The source is `OutImm.ActPos`, which the module
  already publishes, so the operator sees the number before storing it (§3.8c(b)).
- **Validation is the write path, unchanged.** The capture resolves the live value to text and then
  goes through the same revision check, the same `_M_OnConfigWrite` invariant hook, the same range and
  domain validation and the same storage as a typed write. A machine-supplied number is not more
  trustworthy than a human-supplied one (§14).
- **Schema-versioned restore, written once in the base.** `ST_AxisStationCfg` carries
  `SchemaVersion` first (§3.8b), and the axis calls `M_RestoreStationCfg` rather than carrying its
  own copy of the rule: version 0 is a first boot and initializes **silently**; any other
  unrecognized version means a real image was rejected, so the module runs on its declared defaults
  and the loss is reported to the root, which annunciates it with the axis's own canonical path and
  the framework reason `CONFIG_RESTORE_LOST` (§8.8 band 2040–2049). Running on defaults while
  presenting itself as a commissioned machine is the failure that rule exists to prevent.
- **The axis does not decide what a loss costs.** The consequence is the deployment's, through
  `E_ConfigRestorePolicy`: `DEFAULTS_AND_ANNUNCIATE` runs the station with the annunciation standing,
  `BLOCK_UNTIL_ACKNOWLEDGED` refuses `START_STOP` until an operator of at least `ENGINEER` level
  acknowledges the loss. An axis that faulted itself — which this annex previously described — would
  impose the strictest reading on every station that instantiates one.

> **Durability is now behind this (§3.8b).** An accepted write is marked pending and driven to
> non-volatile storage within a declared bounded window, and the root publishes `PersistPending` /
> `PersistFailed`; the taught position takes part in named parameter sets as an ordinary
> `(Scope, WriteKey)` record, so a commissioned axis position can be saved, listed, exported as a
> JSON document, carried to another machine and replayed through this same validation. What remains
> unbuilt is the **model-set load**: a `PAR_CFG` set must be applied through the §3.8 changeover
> transaction rather than as per-field writes, which needs a recipe provider that can store as well
> as load, so that load is refused rather than performed the forbidden way.

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
- A **held manual action** (§7.6.1a): jogging under a safety-rated enabling device, level-driven
  because PLCopen models it that way, stopping when the request stops arriving — including when it
  stops because the transport died rather than because the operator let go.
- A new **per-module-type reason block** (axis CM `10201–10206`) registered per §8.8.

---

*End of Annex G (draft).*
