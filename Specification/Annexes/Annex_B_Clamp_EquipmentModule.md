# Annex B — Worked Example: Clamp Equipment Module

*Companion to **Fraktal Core** (Part I) exercised through the **Fraktal/TC3** binding (Part II); slots under Core §12.*
*Core concepts demonstrated: EM orchestration through the handshake (§3.5/§6.3), parent-child rollup (§8.2), reusable sub-trees via `Setup` (§3.11). / TC3 mechanics used: `OPC.UA.DA` pragmas (TC3 §3.10), member `FB_init` ordering that motivates `Setup` (TC3 §3.11).*
*Reference implementation — illustrative, not compile-tested; validate against the pinned TwinCAT version and your HAL.*

This annex builds the **Equipment Module** tier (§3.5, §6.3) and shows the three things a CM example can't: an EM **orchestrating child Control Modules through the handshake**, a **short non-looping step chain**, and the **parent-child diagnostic rollup** (§8.2) that carries a child's first-out reason up to the operator.

The example is a synchronized dual clamp: a `FB_ClampEM` holding two clamp cylinders. Each cylinder is itself a Control Module — a cylinder plus its two position sensors (extended/retracted), the "clamp = cylinder + 2 sensors" leaf — built on the Annex A pattern. The EM exposes two commands, `CLAMP` and `UNCLAMP`, that string the cylinder commands together and add no device logic of their own (§3.5).

```
ClampStation (FB_ClampEM, Equipment Module)
 ├─ CylA  (FB_CylinderCM, Control Module)   ── HAL: ExtendOut/RetractOut, ExtendedFb/RetractedFb
 └─ CylB  (FB_CylinderCM, Control Module)   ── HAL: …
```

---

## B.1 The cylinder Control Module (surface)

The cylinder CM follows Annex A exactly (PLCopen handshake, four-structure contract, first-out diagnostic, interlocks in Ladder), so only its surface and reasons are shown here. Note it provides **`Setup(...)`** for nested use (§3.11).

```iecst
{attribute 'qualified_only'}
TYPE E_CylinderCommand : (NONE := 0, EXTEND := 1, RETRACT := 2) DINT;
END_TYPE

// E_Reason additions — cylinder CM band 10100–10199
//   CYL_NOT_EXTENDED   := 10101   // ExtendedFb not made within MoveTimeout
//   CYL_NOT_RETRACTED  := 10102   // RetractedFb not made within MoveTimeout
//   CYL_BOTH_SENSORS   := 10103   // both feedbacks active → wiring/jam fault

TYPE ST_CylinderHal : STRUCT
    ExtendOut, RetractOut : BOOL;   // outputs
    ExtendedFb, RetractedFb : BOOL; // the two position sensors
END_STRUCT END_TYPE

// Annex A/B pattern on the base class: the type is ONLY its device logic.
// Execute/Abort arrive through ExecuteCommand/AbortCommand, and Busy/Done/Error/
// Aborted/ErrorID, first-out stamping, rollup and publication are base-owned (§2.2).
FUNCTION_BLOCK FB_CylinderCM EXTENDS FB_ControlModuleBase
VAR_INPUT
    Command : E_CylinderCommand;
    ParCfg  : ST_CylinderParCfg;   // SchemaVersion, MoveTimeout …
    ParCmd  : ST_CylinderParCmd;   // latched by the base on the Execute rising edge
END_VAR
VAR_OUTPUT
    OutCmd : ST_CylinderOutCmd;    // valid on Done
    OutImm : ST_CylinderOutImm;    // Extended, Retracted, Diagnostic (ST_Diagnostic)
    Intlk  : FB_PermIntlk;         // conditions are DECLARED BY THE APPLICATION, not by this type
END_VAR
VAR
    {attribute 'OPC.UA.DA' := '0'}
    _hal   : REFERENCE TO ST_CylinderHal;
    _tMove : TON;
END_VAR

METHOD Setup : BOOL                       // late binding for nested use (§3.11)
VAR_INPUT Name : STRING(80); HalRef : REFERENCE TO ST_CylinderHal; Recipe : I_RecipeProvider; END_VAR
    THIS^._hal REF= HalRef;
    // No interlock is named here. "Area safe" / "Air pressure OK" are station facts, and a
    // reusable library cannot name them for a station it has never seen: the application
    // supplies them through DeclareCondition/SetCondition and the type only reads Intlk.AllOk (§7.2, §9.2).
    // recipe wiring as Annex A …
```

Behaviour (body as Annex A): `EXTEND` drives `ExtendOut`, waits `ExtendedFb` within `ParCfg.MoveTimeout` → `_M_Complete()`, else `_M_FaultStopped(Code := PL_ModuleReasons.CYL_NOT_EXTENDED, Text := 'std.error.cylinderNotExtended')`; `RETRACT` is the mirror. `OutImm.Diagnostic.SourcePath` is the cylinder's own browse path (e.g. `ClampStation.CylA`).

---

## B.2 Clamp EM types

```iecst
{attribute 'qualified_only'}
TYPE E_ClampCommand : (NONE := 0, CLAMP := 1, UNCLAMP := 2) DINT;
END_TYPE

// E_Reason additions — clamp EM band 11000–11999
//   CLAMP_NOT_CONFIRMED := 11001   // both cylinders Done but a clamped sensor not held after settle

TYPE ClampParCfg : STRUCT
    SettleTime     : TIME := T#150MS;   // dwell before confirming
    ConfirmTimeout : TIME := T#1S;
END_STRUCT END_TYPE

TYPE ClampOutCmd : STRUCT  Clamped, Unclamped : BOOL;  END_STRUCT END_TYPE

TYPE ClampOutImm : STRUCT
    Clamped, Unclamped : BOOL;
    Diagnostic : ST_Diagnostic;        // own stall reason, or a rolled-up child reason (B.4)
END_STRUCT END_TYPE
```

---

## B.3 The Equipment Module (ST step chain)

The EM holds its children as **outputs**, so they publish on the module tree and the generic rollup
walk (§3.2) reaches them without a parallel `I_ControlModule` array. Its command is a **short step
chain that completes** — it does not loop (§6.3).

```iecst
// Annex B on the EM base: orchestration only, no device logic (§3.5); rollup §8.2.
// Publication is inherited from the explicitly marked deployed root instance.
FUNCTION_BLOCK FB_ClampEM EXTENDS FB_EquipmentModuleBase
VAR_INPUT
    Command : E_ClampCommand;
    ParCfg  : ST_ClampParCfg;
    ParCmd  : ST_ClampParCmd;
END_VAR
VAR_OUTPUT
    CylA, CylB : FB_CylinderCM;     // children are outputs: published, and reached by the rollup walk
    OutCmd : ST_ClampOutCmd;
    OutImm : ST_ClampOutImm;
END_VAR
VAR
    {attribute 'OPC.UA.DA' := '0'}
    _recipe  : I_RecipeProvider;
    _step    : INT;
    _tSettle : TON;
END_VAR

// ---- one-shot wiring (called from the Unit's init, §3.11) ----
METHOD Setup : BOOL
VAR_INPUT Name : STRING(80); HalA, HalB : REFERENCE TO ST_CylinderHal; Recipe : I_RecipeProvider; END_VAR
    CylA.Setup(Name := CONCAT(Name, '.CylA'), HalRef := HalA, Recipe := Recipe);
    CylB.Setup(Name := CONCAT(Name, '.CylB'), HalRef := HalB, Recipe := Recipe);

// ---- cyclic body: orchestration only; the base owns the handshake ----
METHOD PROTECTED OnCyclic
OnCyclic := SUPER^.OnCyclic();
_M_TickChildren();                       // children stay live, so their status is always current
OutImm.Diagnostic := Status.Diagnostic;
```


The command body (one method serves both directions; `confirmExtended` decides which feedback to verify):

```iecst
METHOD PROTECTED _M_Dispatch
VAR_INPUT  Dir : E_CylinderCommand; END_VAR
VAR  extend : BOOL; END_VAR
    extend := (Dir = E_CylinderCommand.EXTEND);
CASE _step OF
  10:  // command both cylinders together (parallel)
    CylA.Command := Dir;  CylA.ExecuteCommand(Dir);
    CylB.Command := Dir;  CylB.ExecuteCommand(Dir);
    _M_Wait('Clamping');                       // pending reason while children run
    _step := 20;

  20:  // wait both Done — or roll up the first child Error (B.4)
    IF CylA.Error OR CylB.Error THEN
        _M_RollupFault();
    ELSIF CylA.Done AND CylB.Done THEN
        _tSettle(IN := TRUE, PT := ParCfg.SettleTime);
        _step := 30;
    END_IF

  30:  // settle, then confirm both feedbacks held
    IF _tSettle.Q THEN
        _tSettle(IN := FALSE);
        IF (extend AND CylA.OutImm.Extended AND CylB.OutImm.Extended)
        OR (NOT extend AND CylA.OutImm.Retracted AND CylB.OutImm.Retracted) THEN
            OutCmd.Clamped   := extend;
            OutCmd.Unclamped := NOT extend;
            _M_Complete();
        ELSE
            _M_FaultN(Code := PL_ModuleReasons.CLAMP_NOT_CONFIRMED, Text := 'std.error.clampNotConfirmed');
        END_IF
    END_IF
END_CASE
```

The EM adds **no device logic** — it only sequences the cylinder CMs' existing `EXTEND`/`RETRACT` commands through the handshake (§3.5), plus an EM-level settle/confirm.

---

## B.4 Parent-child diagnostic rollup (the point of this annex)

When a child cylinder can't finish, the EM does not invent a reason — it **adopts the child's first-out diagnostic** (§8.2), so the message names the exact device and cause:

```iecst
METHOD PRIVATE _M_RollupFault : BOOL
    // Adopt the first faulted child's diagnostic VERBATIM — reason, SourcePath and Since (§8.2).
    // No parallel I_ControlModule array is kept: the children are published members, and the
    // base's rollup walk already reaches them.
    IF CylA.FaultActive THEN
        _M_AdoptFault(CylA.GetFaultSummary());
    ELSIF CylB.FaultActive THEN
        _M_AdoptFault(CylB.GetFaultSummary());
    END_IF
    CylA.AbortCommand();  CylB.AbortCommand();   // stop the partner safely
```

So if `CylB`'s cylinder never reaches its extended sensor, the chain is:

```
Unit step "Clamp"  ──awaits──▶  ClampStation.CLAMP   (EM, Busy on step 20)
ClampStation step 20  ──awaits──▶  CylB.Done
CylB  ──Error──▶  ReasonCode = CYL_NOT_EXTENDED, SourcePath = "ClampStation.CylB"
```

The EM's `OutImm.Diagnostic` becomes exactly `{ CYL_NOT_EXTENDED, "ClampStation.CylB", "Cylinder did not reach extended" }`, the Unit's stall walk (§6.9) reads it through the EM's `GetFaultSummary`, and the operator sees **"ClampStation.CylB: cylinder did not reach extended"** — a precise, device-naming root cause produced with no hand-coded conditions at the EM or Unit level, just the standard rollup.

---

## B.5 Instantiation & the Unit step that commands it

`ClampStation` is wired once via `Setup` (§3.11), injecting its name and the two cylinder HAL maps:

```iecst
VAR  ClampStation : FB_ClampEM;  END_VAR

// in the Unit's init (one shot):
ClampStation.Setup(Name := 'ClampStation', HalA := Hal.CylA, HalB := Hal.CylB, Recipe := LineRecipe);
```

A step in the Unit's `AUTO` mode chain (§6.2) commands the whole EM through the same PLCopen handshake it would use for any module — the Unit neither knows nor cares that two cylinders are involved:

```iecst
// Unit AUTO chain, step N200 "Clamp part"
IF NOT ClampStation.Busy AND NOT ClampStation.Done THEN
    ClampStation.Command := E_ClampCommand.CLAMP;
    ClampStation.Execute := TRUE;
END_IF
IF ClampStation.Done THEN
    ClampStation.Execute := FALSE;     // Done advances the chain (§6.5)
END_IF
IF ClampStation.Error THEN
    // divert; reason already rolled up in ClampStation.ErrorID / .OutImm.Diagnostic
END_IF
```

`ClampStation.Cyclic` (its body above) drives `CylA`/`CylB` every scan, so the children stay live whether or not a command is running.

---

## B.6 HMI (§3.13)

The EM is rendered by laying out its children's tiles — the automatic child view of §3.13:

```
Station ▸ ClampStation                       (EM tile: name, state LED ← ExecState)
   ├─ CylA   (child tile: Extended/Retracted LEDs, manual EXTEND/RETRACT)
   └─ CylB   (child tile: …)
```

| View | Binding |
|------|---------|
| **Tile** | name; state LED ← `ExecState`; `Clamped`/`Unclamped` LEDs ← `OutCmd`; quick *Clamp* / *Unclamp* buttons; the two cylinder tiles beneath it. |
| **Detail** | manual *Clamp* / *Unclamp* (release-gated, §7.6); the live **`Diagnostic.Description`** line — which, on a child fault, already reads *"ClampStation.CylB: cylinder did not reach extended"* via the rollup; tap-through to each cylinder's own detail view. |

The operator can therefore diagnose from the EM screen and drill straight to the offending cylinder — the same parent→child path the PLC tree and the OPC UA model already define, with no station-specific screen building.

---

## B.7 What this annex demonstrated

- An **Equipment Module orchestrating Control Modules** purely through the PLCopen handshake, adding no device logic (§3.5).
- A **short, completing step chain** for an EM command, vs. the Unit's looping mode chain (§6.2 vs §6.3).
- **Parent-child rollup**: the EM and Unit report a child's exact first-out reason and source path with zero per-level diagnostic code (§8.2, §6.9).
- A **reusable sub-tree** wired by `Setup(...)` because member `FB_init` runs before the parent's (§3.11).
- **Generic HMI**: the EM renders its child tiles and surfaces the rolled-up reason, drill-through following the same tree (§3.13).

---

*End of Annex B (draft).*
