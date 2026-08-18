# Annex A — Worked Example: Separator/Stopper Control Module

*Companion to **Fraktal Core** (Part I) exercised through the **Fraktal/TC3** binding (Part II); slots under Core §12.*
*Core concepts demonstrated: four-structure contract (§3.12), condition ownership (§7.2.1), recipe provider (§3.8), PLCopen handshake (§6.1), first-out diagnostic (§6.9/§8.8), HMI contract (§3.13), simulation (§2.6). / TC3 mechanics used: `OPC.UA.DA` pragmas (TC3 §3.10), `REF=` injection (TC3 §3.11), driver SIM toggles.*

**Realized, not illustrative.** This annex describes shipping code:
`FraktalCore/PLC/TwinCAT/Framework/Fraktal_Modules/FB_SeparatorCM.TcPOU` and its
suite `Tests/Fraktal_Tests/FB_Separator_Tests.TcPOU`. Both compile under the
pinned TwinCAT and executed green on 2026-08-17 —
`Specification/Evidence/2026-08-17_Separator_TcUnit.md`, 112/112 across 32
suites. Where this text and the source disagree, the source is correct and this
document is a defect.

The device releases workpiece carriers one at a time — a common conveyor
separator/stopper. Three inputs and one output, presented through the HAL:

| HAL signal | Meaning (short signal name) |
|------------|-----------------------|
| `CarrierAt` | carrier present at the separator (`SAt`) |
| `CarrierAfter` | carrier present just past the separator (`SOn`) |
| `OpenedFb` | separator-opened feedback (`SOpen`, optional) |
| `ValveOpen` | drives the open solenoid (`Valve`) |

---

## A.1 Supporting types

Commands and behaviour variants. `NONE` exists so an unset command is a value the
dispatch can reject rather than a state it must guess at (§5.6):

```iecst
{attribute 'qualified_only'}
TYPE E_SeparatorCommand : (
    NONE       := 0,
    SEPARATE   := 1,    // release exactly one carrier
    OPEN_CLOSE := 2     // hold the stopper open or closed per ParCmd.OpenStopper
) DINT;
END_TYPE

{attribute 'qualified_only'}
TYPE E_SeparatorMode : (
    SEPARATOR  := 0,      // check carrier at AND after
    STOPPER    := 1,      // check carrier at only
    ASISTOPPER := 2,
    LEADFRAME  := 3
) DINT;
END_TYPE
```

**Reason codes are not redefined here.** Core already owns the framework band
(`TIMEOUT := 2001`, `PERMISSIVE_NOT_MET := 2002`, `INTERLOCK_DROPPED := 2003`,
`RECIPE_INVALID := 2004`, `UNSUPPORTED_COMMAND := 2008`, `STEP_STALLED := 2005`)
in `E_Reason`. This type contributes only its own §8.8 band, in
`PL_ModuleReasons` beside every other module type's:

```iecst
    // separator/stopper CM 10001-10005 (Annex A)
    SEP_NO_CARRIER_AT       : DINT := 10001;   // SAt never made
    SEP_CARRIER_NOT_CLEARED : DINT := 10002;   // SAt did not clear after opening
    SEP_CARRIER_NOT_ARRIVED : DINT := 10003;   // SOn did not arrive in time
    SEP_NOT_OPENED_FB       : DINT := 10004;   // open feedback missing
    SEP_SON_NOT_CLEARED     : DINT := 10005;   // SOn did not clear after close
```

The HAL channel — the leading-underscore raw `%I`/`%Q` symbols live in the
Hardware Driver (§10.2); the HAL presents clean, typed signals:

```iecst
TYPE ST_SeparatorHal :
STRUCT
    CarrierAt    : BOOL;   // input  (driver applies invert/debounce config)
    CarrierAfter : BOOL;   // input
    OpenedFb     : BOOL;   // input  (optional)
    ValveOpen    : BOOL;   // output
END_STRUCT
END_TYPE
```

The four-structure data contract (§3.12). `SchemaVersion` comes **first** in
`ParCfg` (§3.8) so a migrate-or-fault decision can be made before reading
anything else:

```iecst
TYPE ST_SeparatorParCfg :   // recipe/config — filled by I_RecipeProvider (§3.8)
STRUCT
    SchemaVersion : UINT := 1;
    Mode          : E_SeparatorMode := E_SeparatorMode.SEPARATOR;
    CheckAfter    : BOOL := TRUE;    // require the carrier-after arrival/clear checks
    UsesOpenFb    : BOOL := FALSE;   // require the open feedback on OPEN_CLOSE
    MaxOpenTime   : TIME := T#3S;    // SAt must clear within this after opening
    SOnMaxTime    : TIME := T#3S;    // SOn must arrive/clear within this
    CloseDelay    : TIME := T#0S;
    Timeout       : TIME := T#10S;   // overall command timeout
END_STRUCT
END_TYPE

TYPE ST_SeparatorParCmd :   // latched by the base on the Execute rising edge
STRUCT
    OpenStopper : BOOL;                   // OPEN_CLOSE: TRUE = open, FALSE = close
END_STRUCT
END_TYPE

TYPE ST_SeparatorOutCmd :   // valid on Done
STRUCT
    SeparateOk    : BOOL;
    SeparatorOpen : BOOL;
END_STRUCT
END_TYPE

TYPE ST_SeparatorOutImm :   // cyclic live status + first-out diagnostic
STRUCT
    CarrierAt    : BOOL;
    CarrierAfter : BOOL;
    OpenedFb     : BOOL;
    ValveOpen    : BOOL;
    Diagnostic   : ST_Diagnostic;         // §8.8
END_STRUCT
END_TYPE
```

---

## A.2 Interlocks: the library declares none

This is the part of the annex worth reading twice, because the obvious design is
the wrong one.

A separator plainly *has* interlocks — area safe, air pressure, no jam
downstream, downstream ready. The tempting move is to define them in the reusable
type, since every separator needs them. **Core §7.2.1 forbids it:**

> A reusable type derives its conditions from its HAL, parameters, child
> contracts, and explicitly injected semantic status—not by reaching into
> application globals or raw schematic I/O. […] Cross-module collision rules,
> active-mode entry permissives, and other project policy belong to the owning
> Unit's application branch (§4.2), preferably in a visible `Release`/`Permissives`
> object […] Reusable libraries retain only device-intrinsic conditions or
> explicitly injected generic policy; they shall not hide station-specific
> release logic.

Check the four candidates against the device's own HAL:

| Condition | Where it comes from | Library-ownable? |
|---|---|---|
| Area safe | `AllSafetyOk`, the §9.2 safety alias | No — injected system status |
| Air pressure OK | a utility flag | No — injected utility status |
| No jam at separator | a flag; **not on `ST_SeparatorHal`** | No — injected, not derived |
| Downstream ready | conveyor/line state | No — line policy |

Not one of them is device-intrinsic. **So `FB_SeparatorCM` defines no interlock
conditions at all**, and the application declares and drives its own:

```iecst
METHOD DeclareCondition : BOOL      // returns FALSE on an out-of-range index
VAR_INPUT
    Index : INT;  DescriptionKey : STRING(255);
    Reason : E_Reason;  Bypassable : BOOL;
END_VAR

METHOD SetCondition : BOOL
VAR_INPUT  Index : INT;  Ok : BOOL;  END_VAR
```

The records still live in this module's own `FB_PermIntlk`, which is what §7.2.1
requires — *"its constituent `ST_IntlkCond` records remain available so the gate,
first-out diagnostic, and full release report all preserve provenance"*. First-out,
the release report and the HMI drill-down are unchanged; only the *naming* moved
to the layer that has the semantic context.

In the owning Unit's `Release/` object (§4.2), authored in ST beside the rest of
the station's policy:

```iecst
// once, at composition
Separator1.DeclareCondition(Index := 1, DescriptionKey := 'project.interlock.areaSafe',
    Reason := E_Reason.INTERLOCK_DROPPED, Bypassable := FALSE);
Separator1.DeclareCondition(Index := 2, DescriptionKey := 'project.interlock.airPressureOk',
    Reason := E_Reason.INTERLOCK_DROPPED, Bypassable := FALSE);
Separator1.DeclareCondition(Index := 3, DescriptionKey := 'project.interlock.noJamAtSeparator',
    Reason := E_Reason.INTERLOCK_DROPPED, Bypassable := FALSE);
Separator1.DeclareCondition(Index := 4, DescriptionKey := 'project.interlock.downstreamReady',
    Reason := E_Reason.PERMISSIVE_NOT_MET, Bypassable := FALSE);

// every scan
Separator1.SetCondition(Index := 1, Ok := AllSafetyOk);
Separator1.SetCondition(Index := 2, Ok := _AirPressureOk);
Separator1.SetCondition(Index := 3, Ok := NOT _JamSensor);
Separator1.SetCondition(Index := 4, Ok := DownstreamReady);
```

A declared condition starts **FALSE**. Declaring one states an intent to gate, so
the fail-closed default holds the module until the application drives it; a
station that wants no gate simply declares nothing.

> **Why not one setter per condition.** An earlier revision of this annex, and of
> the cylinder CM, exposed a named setter (`SetAreaSafe(Ok, DescriptionKey)`) per
> condition. It does not scale, and in practice it went unused: `SetAreaSafe`
> shipped, and no application ever called it, so `Cond[1]` sat at its `TRUE`
> default and operators saw an "area safe" interlock that was permanently
> satisfied and meant nothing. A library-declared condition that no application
> supplies is worse than no condition, because it *looks* like a gate.

---

## A.3 The Control Module

`FB_SeparatorCM EXTENDS FB_ControlModuleBase`. The PLCopen handshake, the
Execute-drop reset, ExecState mapping, `ErrorID` publication and abort routing are
inherited and written once in `FB_ModuleBase` (§6.1); rows **T1** and **T4** are
proven once for every inheriting type in `FB_Base_Tests` (§5.7) and are not
retested here. **The type is only its device logic.**

```iecst
FUNCTION_BLOCK FB_SeparatorCM EXTENDS FB_ControlModuleBase
VAR_INPUT
    Command : E_SeparatorCommand;
    ParCfg  : ST_SeparatorParCfg;
    ParCmd  : ST_SeparatorParCmd;
END_VAR
VAR_OUTPUT
    OutCmd : ST_SeparatorOutCmd;
    OutImm : ST_SeparatorOutImm;
    Intlk  : FB_PermIntlk;
END_VAR
```

`OnCyclic` re-applies every application condition each scan — so a manual command
obeys the same rule as a sequenced one — evaluates the container, mirrors the HAL
into `OutImm`, and republishes the diagnostic.

`_M_Dispatch` rejects an unsupported command, tags the command for §8.11.4(a)
timing, and then:

**Interlock loss is HELD, not a fault (§6.1).** An interlock is by definition a
condition that must hold *during* the action, and losing one is often expected
operator behaviour. The valve is withdrawn by the same permit that gates it, the
phase timer is reset so a hold cannot silently consume the window it was not
moving for, and the chain rewinds to its first step and resumes when the condition
returns. Under §8.4 this is a wait, not a downtime event.

**`SEPARATE`** is a five-step chain:

| Step | Waits for | Fails with |
|---:|---|---|
| 10 | open the valve; `CarrierAt` present | `SEP_NO_CARRIER_AT` |
| 20 | `CarrierAt` clears within `MaxOpenTime` | `SEP_CARRIER_NOT_CLEARED` |
| 30 | `CarrierAfter` arrives within `SOnMaxTime` — skipped unless `CheckAfter` | `SEP_CARRIER_NOT_ARRIVED` |
| 40 | close after `CloseDelay` | — |
| 50 | `CarrierAfter` clears — skipped unless `CheckAfter` | `SEP_SON_NOT_CLEARED` |

**`OPEN_CLOSE`** drives the valve from `ParCmd.OpenStopper`. Closing completes
immediately; opening confirms `OpenedFb` only when `ParCfg.UsesOpenFb` says the
station wired one, and otherwise completes at once.

**Every fault withdraws the output first.** Faults go through a private
`_M_FaultClosed(Code, Text)` that calls `WithdrawOutputs()` and *then* raises:

```iecst
METHOD PRIVATE _M_FaultClosed
VAR_INPUT  Code : DINT;  Text : STRING(255);  END_VAR

WithdrawOutputs();
_M_FaultN(Code := Code, Text := Text);
```

This is not decoration. `_M_FaultN` raises the reason and does not touch outputs,
so an earlier revision faulted from an open phase while leaving the stopper
energised — reporting `ERROR` while the device kept releasing carriers it could no
longer account for. The suite caught it on first execution; source review had not,
because every individual line was correct and the defect was in what two correct
lines together failed to do.

Diagnostic text is a **localization key**, never prose: `_M_FaultN(Code :=
PL_ModuleReasons.SEP_NO_CARRIER_AT, Text := 'std.error.separatorNoCarrierAt')`.
The HMI resolves it per operator language (§3.13); a literal English string in a
library is a defect the cross-artifact gate rejects.

---

## A.4 Instantiation & reuse (§3.11)

Two separators, same type, different name + HAL mapping + recipe source:

```iecst
VAR
    Separator1 : FB_SeparatorCM;
    Separator2 : FB_SeparatorCM;
END_VAR

// composition root, once
Separator1.Setup(Name := 'Separator1', HalRef := Hal.Sep1, Recipe := LineRecipe);
Separator2.Setup(Name := 'Separator2', HalRef := Hal.Sep2, Recipe := LineRecipe);
```

`Setup` sets the name (= OPC UA browse name = schematic name, §4.8), sets the
presentation keys, binds the HAL by reference, publishes the two commands for the
HMI, and runs the recipe prepare/commit transaction (§3.8). It defines **no**
interlocks — see A.2.

`Recipe := 0` is supported and means "no provider": `ParCfg` is used as-is. That
is what the test suite does, and what a station without a recipe source does.

A step in an Equipment Module (Annex B) commands this CM through the standard
handshake:

```iecst
IF NOT Separator1.Busy AND NOT Separator1.Done THEN
    Separator1.Command := E_SeparatorCommand.SEPARATE;
    Separator1.Execute := TRUE;
END_IF
IF Separator1.Done THEN
    Separator1.Execute := FALSE;     // advances the step (§6.5)
END_IF
```

---

## A.5 HMI views (§3.13)

The Flutter app discovers the instance and renders it generically from the node
sub-structure — no per-station screen building:

```
Station ▸ Infeed ▸ Separator1
  Identity   : { Name, ModuleType=CONTROL_MODULE }
  State      : ExecState  (READY/BUSY/DONE/ERROR/ABORTED) + Held
  Commands   : SEPARATE, OPEN_CLOSE          (Features-gated, §3.9; release-gated, §7.6)
  ParCfg     : Mode, CheckAfter, UsesOpenFb, MaxOpenTime, SOnMaxTime …   (recipe view)
  OutImm     : CarrierAt, CarrierAfter, OpenedFb, ValveOpen, Diagnostic
```

| View | Binding |
|------|---------|
| **Tile** | name; state LED ← `ExecState`; carrier LED ← `OutImm.CarrierAt`; open LED ← `OutImm.ValveOpen`; quick buttons *Separate* / *Open·Close*. |
| **Detail** | manual *Separate* / *Open* / *Close* (each inhibited unless its §7.6 release is TRUE); status LEDs for `CarrierAt`/`CarrierAfter`/`OpenedFb`/`ValveOpen` with their interlock descriptions; the live **`Diagnostic.Description`** line (the first-out reason); the recipe (`ParCfg`) panel. |

When a `SEPARATE` stalls — say a carrier never clears `SAt` — the Detail view
shows *"Separator1: Carrier did not clear separator"* directly from
`OutImm.Diagnostic`, and on timeout the same text becomes the `Error` with
`ErrorID = 10002`. That is the §6.9 walk landing on the operator's screen with no
per-step diagnostic code.

Because the interlock *descriptions* come from the application's
`DeclareCondition` calls, the drill-down names the station's own condition —
"Downstream conveyor not ready" — rather than a generic library phrase. Provenance
travels with the record (§7.2.1).

---

## A.6 Simulation vs. hardware (§2.6)

`FB_SeparatorCM` only ever touches `_hal`. Whether `_hal` is fed by the real
Hardware Driver or by the DI/DO SIM is a driver-level choice; the CM is unchanged:

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

There are **no SIM-only force hooks** in the module (§5.7, lint rule C8). The
suite drives the shipped surface: it declares conditions the way an application
does and writes the HAL the way a driver does, so what the tests exercise is what
ships.

---

## A.7 Conformance rows (§5.7)

| Row | Where |
|---|---|
| T1 handshake, Execute-drop reset | `FB_Base_Tests` — once for all inheriting types |
| T4 abort, no self-resume | `FB_Base_Tests` — once for all inheriting types |
| T2 first-out reason + `SourcePath` | `No_carrier_at_the_separator_faults_10001` |
| T3 interlock withholds output | `Interlock_withholds_the_valve_and_holds_rather_than_faults` |
| T5 recipe migrate-or-fault | `PrepareRecipe` faults `RECIPE_INVALID`; provider-less path covered by `Setup` |
| Ownership (§7.2.1) | `Library_declares_no_interlocks_and_application_conditions_are_fail_closed` |

Executed 2026-08-17: 6/6 in `SeparatorTests`, within 112/112 across 32 suites.

---

*End of Annex A — realized against `Fraktal_Modules 0.5.0.0`.*
