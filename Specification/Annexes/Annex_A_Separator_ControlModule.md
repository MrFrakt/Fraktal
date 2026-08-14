# Annex A — Worked Example: Separator/Stopper Control Module

*Companion to **Fraktal Core** (Part I) exercised through the **Fraktal/TC3** binding (Part II); slots under Core §12.*
*Core concepts demonstrated: four-structure contract (§3.12), recipe provider (§3.8), PLCopen handshake (§6.1), first-out diagnostic (§6.9/§8.8), `FB_PermIntlk` (§7.2), HMI contract (§3.13), simulation (§2.6). / TC3 mechanics used: `OPC.UA.DA` pragmas (TC3 §3.10), `FB_init`/`REF=` injection (TC3 §3.11), driver SIM toggles.*
*Reference implementation — illustrative, not compile-tested; validate against the pinned TwinCAT version and your HAL.*

This annex builds one `FB_ControlModule` end-to-end — a separator/stopper that releases workpiece carriers one at a time, a common conveyor device — and shows every contract working together: the four-structure data model (§3.12), recipe via `I_RecipeProvider` (§3.8), the PLCopen handshake (§6.1), first-out `ST_Diagnostic` (§6.9, §8.8), interlocks in **Ladder** with device logic in **ST** (§5.5, §7.2), the HMI bindings (§3.13), and unchanged behaviour in simulation vs. hardware (§2.6).

The device has three inputs and one output, presented through the HAL:

| HAL signal | Meaning (short signal name) |
|------------|-----------------------|
| `CarrierAt` | carrier present at the separator (`SAt`) |
| `CarrierAfter` | carrier present just past the separator (`SOn`) |
| `OpenedFb` | separator-opened feedback (`SOpen`, optional) |
| `ValveOpen` | drives the open solenoid (`Value`) |

---

## A.1 Supporting types

```iecst
{attribute 'qualified_only'}
TYPE E_SepCommand : (
    NONE       := 0,
    SEPARATE   := 1,    // release exactly one carrier
    OPEN_CLOSE := 2     // hold the stopper open or closed
) DINT;
END_TYPE

{attribute 'qualified_only'}
TYPE E_SepMode : (        // separation behaviour variants
    SEPARATOR  := 0,      // check carrier at AND after
    STOPPER    := 1,      // check carrier at only
    ASISTOPPER := 2,
    LEADFRAME  := 3
) DINT;
END_TYPE

{attribute 'qualified_only'}
TYPE E_ExecState : (READY := 0, BUSY := 1, DONE := 2, ERROR := 3, ABORTED := 4) DINT;
END_TYPE
```

Reason codes use the bands of §8.8 — framework reasons in `2000–9999`, this module type's reasons in its `10000–10999` block:

```iecst
{attribute 'qualified_only'}
TYPE E_Reason : (
    NONE                    := 0,
    // 2000–9999  framework (common)
    TIMEOUT                 := 2001,
    PERMISSIVE_NOT_MET      := 2002,
    INTERLOCK_DROPPED       := 2003,
    RECIPE_INVALID          := 2004,
    // 10000–10999  Separator/Stopper Control Module
    SEP_NO_CARRIER_AT       := 10001,  // SAt never made
    SEP_CARRIER_NOT_CLEARED := 10002,  // SAt did not clear after opening
    SEP_CARRIER_NOT_ARRIVED := 10003,  // SOn did not arrive in time
    SEP_NOT_OPENED_FB       := 10004,  // open feedback missing
    SEP_SON_NOT_CLEARED     := 10005   // SOn did not clear after close
) DINT;
END_TYPE
```

The HAL channel for this device (the leading-underscore raw `%I`/`%Q` symbols live in the Hardware Driver, §10.2; the HAL presents clean, typed signals):

```iecst
TYPE ST_SepHal :
STRUCT
    CarrierAt    : BOOL;   // input  (driver applies invert/debounce config)
    CarrierAfter : BOOL;   // input
    OpenedFb     : BOOL;   // input  (optional)
    ValveOpen    : BOOL;   // output
END_STRUCT
END_TYPE
```

The four-structure data contract (§3.12), named `Separator…`:

```iecst
TYPE SeparatorParCfg :   // recipe/config — filled by I_RecipeProvider (§3.8)
STRUCT
    Mode         : E_SepMode := E_SepMode.SEPARATOR;
    CheckAfter   : BOOL := TRUE;          // require the carrier-after check
    MaxOpenTime  : TIME := T#3S;          // SAt must clear within this after opening
    SOnMaxTime   : TIME := T#3S;          // SOn must arrive/clear within this
    CloseDelay   : TIME := T#0S;
    Timeout      : TIME := T#10S;         // overall command timeout
END_STRUCT
END_TYPE

TYPE SeparatorParCmd :   // latched on the Execute rising edge
STRUCT
    OpenStopper  : BOOL;                  // OPEN_CLOSE: TRUE = open, FALSE = close
END_STRUCT
END_TYPE

TYPE SeparatorOutCmd :   // valid on Done
STRUCT
    SeparateOk    : BOOL;
    SeparatorOpen : BOOL;
END_STRUCT
END_TYPE

TYPE SeparatorOutImm :   // cyclic live status + first-out diagnostic
STRUCT
    CarrierAt    : BOOL;
    CarrierAfter : BOOL;
    OpenedFb     : BOOL;
    ValveOpen    : BOOL;
    Diagnostic   : ST_Diagnostic;         // §8.8: ReasonCode, SourcePath, Description, Severity, Category, Since
END_STRUCT
END_TYPE
```

---

## A.2 Interlocks in Ladder

The interlock conditions are authored in **Ladder** (§5.5, §7.2) — the natural form for an interlock — and feed the framework container `SepIntlk : FB_PermIntlk`. The condition records (index, description, reason) are set once in `FB_init`; the rungs only drive the boolean inputs:

```text
( Separator interlocks — Ladder rungs driving the FB_PermIntlk condition coils )

  AllSafetyOk────────────────────────────────────( SepIntlk.Cond[1] )   // idx1 "Area safe"
  _AirPressureOk─────────────────────────────────( SepIntlk.Cond[2] )   // idx2 "Air pressure OK"
  _JamSensor/(NC)────────────────────────────────( SepIntlk.Cond[3] )   // idx3 "No jam at separator"
  DownstreamReady────────────────────────────────( SepIntlk.Cond[4] )   // idx4 "Downstream ready"
```

`AllSafetyOk` is the read-only safety alias from §9.2; `_AirPressureOk` / `_JamSensor` are HAL/flag signals (leading `_`, §4.4). Because each condition carries a description and `ReasonCode`, the *first* FALSE one becomes the module's first-out reason automatically (§6.9).

---

## A.3 The Control Module (ST)

```iecst
// Publication is inherited from the explicitly marked deployed root instance.
FUNCTION_BLOCK FB_SeparatorCM IMPLEMENTS I_ControlModule
VAR_INPUT
    // PLCopen handshake (public I/O — §6.1)
    Execute  : BOOL;
    Command  : E_SepCommand;
    Abort    : BOOL;
END_VAR
VAR_OUTPUT
    Busy     : BOOL;
    Done     : BOOL;
    Error    : BOOL;
    ErrorID  : DWORD;          // = TO_DWORD(diagnostic reason), §8.8
    Aborted  : BOOL;
END_VAR
VAR
    // Data contract (§3.12) — exposed over OPC UA
    ParCfg   : SeparatorParCfg;
    ParCmd   : SeparatorParCmd;
    OutCmd   : SeparatorOutCmd;
    OutImm   : SeparatorOutImm;

    // Injected at instantiation (A.4)
    _name    : STRING(80);
    _hal     : REFERENCE TO ST_SepHal;
    _recipe  : I_RecipeProvider;
    _recipeLoaded : BOOL;

    // Interlocks (framework container; conditions driven in Ladder, A.2)
    SepIntlk : FB_PermIntlk;

    // Internal sequencing
    _exec    : E_ExecState := E_ExecState.READY;
    _step    : INT;
    _rTrig   : R_TRIG;
    tCmd     : TON;            // overall command timeout
    tPhase   : TON;           // per-phase timeout (open/clear/arrive)
    tDeb     : TON;            // debounce helper
END_VAR

// ---------------------------------------------------------------------------
// 1) Recipe load (once, when the provider has valid data) — §3.8
IF NOT _recipeLoaded THEN
    IF _recipe.Ready THEN
        IF _recipe.Load(_name, ADR(ParCfg), SIZEOF(ParCfg)) THEN
            _recipeLoaded := TRUE;
        ELSE
            _M_Fault(E_Reason.RECIPE_INVALID, 'Recipe load/validate failed');
        END_IF
    END_IF
END_IF

// 2) Read HAL into live status (device-logic, ST — §10.3)
OutImm.CarrierAt    := _hal.CarrierAt;
OutImm.CarrierAfter := _hal.CarrierAfter;
OutImm.OpenedFb     := _hal.OpenedFb;

// 3) Evaluate interlocks (Ladder rungs of A.2 ran this scan; container summarises)
SepIntlk();

// 4) Start on Execute rising edge — latch ParCmd, go Busy
_rTrig(CLK := Execute);
IF _rTrig.Q AND _exec = E_ExecState.READY THEN
    IF SepIntlk.AllOk THEN
        _exec := E_ExecState.BUSY;
        _step := 10;
        OutCmd.SeparateOk := FALSE;
        tCmd(IN := FALSE); tCmd(IN := TRUE, PT := ParCfg.Timeout);
    ELSE
        _M_Fault(SepIntlk.Diagnostic.ReasonCode, SepIntlk.Diagnostic.Description);
    END_IF
END_IF

// 5) Abort request
IF Abort AND _exec = E_ExecState.BUSY THEN
    _hal.ValveOpen := FALSE;
    _exec := E_ExecState.ABORTED; _step := 0;
END_IF

// 6) Interlock dropped mid-action → immediate halt + first-out reason (§7.1)
IF _exec = E_ExecState.BUSY AND NOT SepIntlk.AllOk THEN
    _hal.ValveOpen := FALSE;
    _M_Fault(SepIntlk.Diagnostic.ReasonCode, SepIntlk.Diagnostic.Description);
END_IF

// 7) Overall timeout
tCmd(IN := (_exec = E_ExecState.BUSY));
IF tCmd.Q THEN
    _M_Fault(E_Reason.TIMEOUT, 'Command timed out');
END_IF

// 8) Command bodies
IF _exec = E_ExecState.BUSY THEN
    CASE Command OF
        E_SepCommand.SEPARATE:   _M_Separate();
        E_SepCommand.OPEN_CLOSE: _M_OpenClose();
    END_CASE
END_IF

// 9) Map internal state → PLCopen outputs + ExecState/ErrorID + clear on de-assert
Busy    := (_exec = E_ExecState.BUSY);
Done    := (_exec = E_ExecState.DONE);
Error   := (_exec = E_ExecState.ERROR);
Aborted := (_exec = E_ExecState.ABORTED);
ErrorID := TO_DWORD(OutImm.Diagnostic.ReasonCode);
OutCmd.SeparatorOpen := _hal.ValveOpen;
OutImm.ValveOpen     := _hal.ValveOpen;

IF NOT Execute AND _exec IN (E_ExecState.DONE, E_ExecState.ERROR, E_ExecState.ABORTED) THEN
    _exec := E_ExecState.READY;     // ready for the next command
    Done := FALSE; Error := FALSE; Aborted := FALSE;
END_IF
```

### Command body — `SEPARATE` (private method `_M_Separate`)

```iecst
CASE _step OF
  10:  // open and require a carrier present
    _hal.ValveOpen := TRUE;
    _M_Wait(E_Reason.SEP_NO_CARRIER_AT, 'No carrier at separator');
    IF OutImm.CarrierAt THEN
        tPhase(IN := FALSE); tPhase(IN := TRUE, PT := ParCfg.MaxOpenTime);
        _step := 20;
    END_IF

  20:  // carrier must clear SAt within MaxOpenTime
    _M_Wait(E_Reason.SEP_CARRIER_NOT_CLEARED, 'Carrier did not clear separator');
    IF NOT OutImm.CarrierAt THEN
        tPhase(IN := FALSE); tPhase(IN := TRUE, PT := ParCfg.SOnMaxTime);
        _step := SEL(ParCfg.CheckAfter, 40, 30);   // skip after-check if not required
    ELSIF tPhase.Q THEN
        _M_Fault(E_Reason.SEP_CARRIER_NOT_CLEARED, 'Carrier did not clear separator');
    END_IF

  30:  // arrival check (carrier reached SOn)
    _M_Wait(E_Reason.SEP_CARRIER_NOT_ARRIVED, 'Carrier did not arrive after separator');
    IF OutImm.CarrierAfter THEN
        _step := 40;
    ELSIF tPhase.Q THEN
        _M_Fault(E_Reason.SEP_CARRIER_NOT_ARRIVED, 'Carrier did not arrive after separator');
    END_IF

  40:  // close and finish
    tDeb(IN := TRUE, PT := ParCfg.CloseDelay);
    IF tDeb.Q THEN
        _hal.ValveOpen := FALSE;
        tDeb(IN := FALSE);
        OutCmd.SeparateOk := TRUE;
        _exec := E_ExecState.DONE; _step := 0;
        _M_ClearDiag();
    END_IF
END_CASE
```

### Command body — `OPEN_CLOSE` (private method `_M_OpenClose`)

```iecst
_hal.ValveOpen := ParCmd.OpenStopper;
IF ParCmd.OpenStopper THEN
    // optional open-feedback confirmation
    _M_Wait(E_Reason.SEP_NOT_OPENED_FB, 'Separator did not report open');
    tPhase(IN := TRUE, PT := ParCfg.MaxOpenTime);
    IF (NOT _UsesOpenFb) OR OutImm.OpenedFb THEN
        _exec := E_ExecState.DONE; _M_ClearDiag();
    ELSIF tPhase.Q THEN
        _M_Fault(E_Reason.SEP_NOT_OPENED_FB, 'Separator did not report open');
    END_IF
ELSE
    _exec := E_ExecState.DONE; _M_ClearDiag();   // close is immediate
END_IF
```

### Diagnostic helpers (the heart of §6.9)

```iecst
// _M_Wait: while still waiting, publish the *pending* first-out reason (not yet an error)
METHOD PRIVATE _M_Wait : BOOL
VAR_INPUT  Reason : E_Reason;  Desc : STRING(255); END_VAR
    OutImm.Diagnostic.ReasonCode := Reason;        // "waiting for: <Desc>"
    OutImm.Diagnostic.Description := Desc;
    OutImm.Diagnostic.SourcePath := _name;
    OutImm.Diagnostic.Severity   := E_Severity.LOW;

// _M_Fault: promote to ERROR with the first-out reason → ErrorID
METHOD PRIVATE _M_Fault : BOOL
VAR_INPUT  Reason : E_Reason;  Desc : STRING(255); END_VAR
    OutImm.Diagnostic.ReasonCode := Reason;
    OutImm.Diagnostic.Description := Desc;
    OutImm.Diagnostic.SourcePath := _name;
    OutImm.Diagnostic.Severity   := E_Severity.MED;
    OutImm.Diagnostic.Since      := _M_Now();
    _hal.ValveOpen := FALSE;
    _exec := E_ExecState.ERROR; _step := 0;

// _M_ClearDiag: reset to NONE on success
```

The interface properties of `I_Module` / `I_ControlModule` are trivial getters and are elided here: `Name` → `_name`, `ModuleType` → `CONTROL_MODULE`, `State` → `_exec`, `FaultActive` → `Error`, and `GetFaultSummary` → `OutImm.Diagnostic` (the numeric `ErrorID` lives only on the PLCopen output — §3.2/§6.1). `ExecuteCommand(cmd : DINT)` validates the value against `E_SepCommand` (§5.6) and enters the same lifecycle as the typed surface; `AbortCommand()` routes through the inherited abort path.

---

## A.4 Instantiation & reuse (§3.11)

Two separators, same type, different name + HAL mapping + recipe source — full logic reused:

```iecst
VAR
    Separator1 : FB_SeparatorCM(Name := 'Separator1',
                                HalRef := Hal.Sep1,
                                Recipe := LineRecipe);   // I_RecipeProvider (OPC UA / REST / local …)
    Separator2 : FB_SeparatorCM(Name := 'Separator2',
                                HalRef := Hal.Sep2,
                                Recipe := LineRecipe);
END_VAR
```

```iecst
METHOD FB_init : BOOL
VAR_INPUT
    bInitRetains : BOOL;  bInCopyCode : BOOL;
    Name   : STRING(80);
    HalRef : REFERENCE TO ST_SepHal;
    Recipe : I_RecipeProvider;
END_VAR
    THIS^._name   := Name;          // = OPC UA browse name = schematic name (§4.8)
    THIS^._hal    REF= HalRef;
    THIS^._recipe := Recipe;
    // condition records set once (driven by the Ladder rungs of A.2)
    SepIntlk.Define(1, 'Area safe',              E_Reason.INTERLOCK_DROPPED);
    SepIntlk.Define(2, 'Air pressure OK',        E_Reason.INTERLOCK_DROPPED);
    SepIntlk.Define(3, 'No jam at separator',    E_Reason.INTERLOCK_DROPPED);
    SepIntlk.Define(4, 'Downstream ready',       E_Reason.PERMISSIVE_NOT_MET);
```

A step in an Equipment Module (Annex B) commands this CM through the standard handshake:

```iecst
IF NOT Separator1.Busy AND NOT Separator1.Done THEN
    Separator1.Command := E_SepCommand.SEPARATE;
    Separator1.Execute := TRUE;
END_IF
IF Separator1.Done THEN
    Separator1.Execute := FALSE;     // advances the step (§6.5)
END_IF
```

---

## A.5 HMI views (§3.13)

The Flutter app discovers the instance over OPC UA and renders it generically from the node sub-structure — no per-station screen building:

```
Station ▸ Infeed ▸ Separator1
  Identity   : { Name, ModuleType=CONTROL_MODULE }
  State      : ExecState  (READY/BUSY/DONE/ERROR/ABORTED)
  Commands   : SEPARATE, OPEN_CLOSE          (Features-gated, §3.9; release-gated, §7.6)
  ParCfg     : Mode, CheckAfter, MaxOpenTime, SOnMaxTime …   (recipe view)
  OutImm     : CarrierAt, CarrierAfter, OpenedFb, ValveOpen, Diagnostic
```

| View | Binding |
|------|---------|
| **Tile** | name; state LED ← `ExecState`; carrier LED ← `OutImm.CarrierAt`; open LED ← `OutImm.ValveOpen`; quick buttons *Separate* / *Open·Close*. |
| **Detail** | manual *Separate* / *Open* / *Close* (each inhibited unless its §7.6 release is TRUE); status LEDs for `CarrierAt`/`CarrierAfter`/`OpenedFb`/`ValveOpen` with their interlock descriptions; the live **`Diagnostic.Description`** line (the first-out reason); the recipe (`ParCfg`) panel. |

When a `SEPARATE` stalls — say a carrier never clears `SAt` — the Detail view shows *"Separator1: Carrier did not clear separator"* directly from `OutImm.Diagnostic`, and on timeout the same text becomes the `Error` with `ErrorID = 10002`. That is the §6.9 walk landing on the operator's screen with no per-step diagnostic code.

---

## A.6 Simulation vs. hardware (§2.6)

`FB_SeparatorCM` only ever touches `_hal`. Whether `_hal` is fed by the real Hardware Driver or by the DI/DO SIM is a driver-level choice; the CM is unchanged:

```iecst
IF GVL.SimEnabled THEN
    // SIM: a test model writes the HAL inputs (e.g. clear CarrierAt shortly after ValveOpen)
    Hal.Sep1.CarrierAt    := SimModel.Sep1CarrierAt;
    Hal.Sep1.CarrierAfter := SimModel.Sep1CarrierAfter;
ELSE
    // HARDWARE: the driver maps terminals to the HAL
    Hal.Sep1.CarrierAt    := _Sep1_SAt;     // %I* via driver (invert/debounce per config)
    Hal.Sep1.CarrierAfter := _Sep1_SOn;
    _Sep1_Valve           := Hal.Sep1.ValveOpen;   // %Q* via driver
END_IF
```

So a `SEPARATE` validated in Process Simulate behaves identically on the line — same handshake, same timeouts, same first-out diagnostics — which is the whole point of routing every CM through the HAL.

---

*End of Annex A (draft).*
