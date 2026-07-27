# Annex C — Worked Example: Station Unit

*Companion to **Fraktal Core** (Part I) exercised through the **Fraktal/TC3** binding (Part II); slots under Core §12.*
*Core concepts demonstrated: Unit mode chain (§6.2), mode cascade with graceful rejection (§3.7), top-down recipe (§3.8), stall walk & condition records (§6.9), verdict hook & routing by ID (§10.6/§10.7). / TC3 mechanics used: `__QUERYINTERFACE` cascade (TC3 §3.2), `OPC.UA.DA` pragmas (TC3 §3.10).*
*Reference implementation — illustrative, not compile-tested; validate against the pinned TwinCAT version.*

This annex builds the top tier — a `FB_Unit` (the ModeHandler) — and ties Annexes A and B together. It shows the four things only the Unit tier can: a **continuous mode step chain** that runs until Stop, **mode cascade to a child Unit** with graceful rejection (§3.7), **top-down recipe load** on changeover (§3.8), and the **stall-diagnostic walk** that lands a child's rolled-up reason on the operator screen (§6.9).

The station is an infeed Unit composed of one of each tier from the earlier annexes, plus a nested child Unit to exercise recursion:

```
InfeedUnit (FB_InfeedUnit : FB_Unit, ModeHandler)         ← top instance = station
 ├─ Separator1   (FB_SeparatorCM,  Control Module)         ← Annex A
 ├─ ClampStation (FB_ClampEM,      Equipment Module)       ← Annex B (→ CylA, CylB)
 ├─ RobotHandling (FB_RobotHandlingEM, Equipment Module)    ← Annex I §I.6 (→ Robot130 : FB_RobotCM → I_RobotConnector)
 └─ FixtureUnit  (FB_FixtureUnit : FB_Unit, child Unit)    ← recursion + mode cascade
```

---

## C.1 Modes, step record, reasons

```iecst
{attribute 'qualified_only'}
TYPE E_Mode : (AUTO := 0, MANUAL := 1, HOME := 2, CHANGEOVER := 3, CALIBRATION := 4) DINT;
END_TYPE

TYPE ST_StepRecord : STRUCT          // §6.5 — what the stall walk reads
    StepNo        : INT;
    StepName      : STRING(80);
    AwaitingLabel : STRING(120);     // e.g. "ClampStation.CLAMP"  ("" if none)
    ExpectedTime  : TIME;            // defaults from the awaited command's timeout
    Conds         : ARRAY[1..4] OF ST_CondRecord;  // named plain-condition waits (§6.9(b))
END_STRUCT END_TYPE

TYPE ST_CondRecord : STRUCT  Label : STRING(60);  Ok : BOOL;  END_STRUCT END_TYPE   // §6.9(b)

// E_Reason additions — framework band
//   STEP_STALLED := 2005   // step exceeded ExpectedTime with no child fault

INTERFACE I_VerdictProvider          // optional per-cycle part-verdict hook — Annex E implements it (§E.2–E.3)
    METHOD Evaluate : BOOL           // TRUE = part OK; called once at the verdict step
    PROPERTY Reason : E_Reason       // first NOK reason when Evaluate() = FALSE — same vocabulary as a fault (§8.8)
END_INTERFACE

// Robot point-list / point IDs are stable controller-side handles (Annex I §I.1) —
// the application references them by ID, never by coordinate:
//   ID_PROCESS_G1_1 : DWORD   // taught list "ProcessG1-1" (10 pts) on the robot controller
//   NEST_DRAWER_NIO : DWORD   // NIO-drawer disposition position (Annex I §I.10.1)
```

---

## C.2 The Unit (composition & wiring)

The Unit holds its children both directly (to command them) and as `ARRAY OF I_Module` for the generic walks — discovery, fault rollup, and mode forwarding (§3.2). Wiring is one-shot via `Setup` because member `FB_init` runs first (§3.11).

```iecst
// The application marks the deployed FB_InfeedUnit instance, not this type.
FUNCTION_BLOCK FB_InfeedUnit EXTENDS FB_Unit IMPLEMENTS I_Unit
VAR_OUTPUT  ErrorID : DWORD;  END_VAR
VAR
    Separator1   : FB_SeparatorCM;     // Annex A
    ClampStation : FB_ClampEM;         // Annex B
    RobotHandling : FB_RobotHandlingEM; // Annex I §I.6 — semantic ops; owns Robot130 (FB_RobotCM) + its connector
    FixtureUnit  : FB_FixtureUnit;     // child Unit (C.5)
    _children    : ARRAY[1..4] OF I_Module;

    _hal     : REFERENCE TO ST_StationHal;
    ParCfg   : InfeedParCfg;           // station recipe (cycle params, …)
    OutImm   : InfeedOutImm;           // State, StallReason, Diagnostic …

    _name    : STRING(80);
    _mode    : E_Mode := E_Mode.AUTO;
    _exec    : E_ExecState := E_ExecState.READY;   // READY=idle · BUSY=running · ERROR=held
    _step    : INT;
    _stopReq : BOOL;
    _nokPending : BOOL;               // verdict from step 35 → routes 40 to finish or disposition
    _verdict : I_VerdictProvider;     // optional hook (0 = none → always OK); Annex E injects its implementation
    _curStep : ST_StepRecord;
    _awaiting : I_Module;              // module the current step waits on (0 = none)
    _rTrig   : R_TRIG;
    tStep    : TON;                    // stall timer
END_VAR

METHOD Setup : BOOL
VAR_INPUT Name : STRING(80); Hal : REFERENCE TO ST_StationHal; Recipe : I_RecipeProvider;
          Verdict : I_VerdictProvider := 0; END_VAR                    // optional — default keeps C standalone
    THIS^._name := Name;  THIS^._verdict := Verdict;  THIS^._hal REF= Hal;
    Separator1.FB_initLikeSetup(...);                                  // per Annex A
    ClampStation.Setup(Name := CONCAT(Name,'.ClampStation'), HalA := Hal.CylA, HalB := Hal.CylB, Recipe := Recipe);
    RobotHandling.Setup(Name := CONCAT(Name,'.RobotHandling'), Endpoint := ParCfg.RobotEndpoint /* §3.8: endpoints are configuration, not I/O (audit R3) */, Recipe := Recipe);  // wires Robot130 + portable connector internally (Annex I §I.5–I.6)
    FixtureUnit.Setup(Name := CONCAT(Name,'.FixtureUnit'), Hal := Hal.Fixture, Recipe := Recipe);
    _children[1] := Separator1;  _children[2] := ClampStation;  _children[3] := RobotHandling;  _children[4] := FixtureUnit;
```

---

## C.3 Lifecycle — `SetMode`, `Start`, `Stop` (I_Unit)

```iecst
METHOD SetMode : BOOL
VAR_INPUT Mode : E_Mode; END_VAR
VAR i : INT; childUnit : I_Unit; END_VAR
    IF NOT _M_Supports(Mode) THEN SetMode := FALSE; RETURN; END_IF
    _mode := Mode;
    IF Mode = E_Mode.CHANGEOVER THEN _M_LoadRecipes(); END_IF      // top-down recipe (C.6)

    // cascade to child Units only (§3.7) — found via __QUERYINTERFACE (Robot130 is a CM, so skipped)
    FOR i := 1 TO 4 DO
        IF __QUERYINTERFACE(_children[i], childUnit) THEN
            IF NOT childUnit.SetMode(Mode) THEN
                childUnit.Stop();                                  // child lacks this mode → safe state
                SetEvent(EVENT_CHILD_MODE_UNSUPPORTED, childUnit.Name);   // §8.7
            END_IF
        END_IF
    END_FOR
    SetMode := TRUE;

METHOD Start : BOOL
    IF _exec = E_ExecState.READY THEN
        _stopReq := FALSE;  _exec := E_ExecState.BUSY;  _step := 10;  Start := TRUE;
    END_IF

METHOD Stop : BOOL
    _stopReq := TRUE;  Stop := TRUE;     // chain finishes the cycle, then idles (C.4)
```

`_M_Supports` lists the station's modes (`AUTO/MANUAL/HOME/CHANGEOVER/CALIBRATION`). `ModeActive` (property) returns `_mode`; `State` returns `_exec`.

---

## C.4 Cyclic body & the continuous AUTO chain (§6.2)

```iecst
// children always tick so their status is live
Separator1();  ClampStation();  RobotHandling();  FixtureUnit();   // RobotHandling ticks Robot130 + connector

IF _exec = E_ExecState.BUSY THEN
    CASE _mode OF
        E_Mode.AUTO:        _M_AutoChain();
        E_Mode.HOME:        _M_HomeChain();        // own chain (elided)
        E_Mode.CHANGEOVER:  _M_ChangeoverChain();  // elided
        E_Mode.CALIBRATION: _M_CalibrationChain(); // elided
        E_Mode.MANUAL: ;    // no chain — operator triggers EM/CM commands, release-gated (§7.6)
    END_CASE
    _M_StallWalk();         // §6.9
END_IF

ErrorID := TO_DWORD(OutImm.Diagnostic.ReasonCode);
```

The AUTO mode sequence is a continuous step chain — it loops until Stop (§6.2). Each step commands a child through the **same PLCopen handshake** used everywhere (Annexes A/B), advances on `Done`, and adopts a child `Error` via rollup:

```iecst
METHOD PRIVATE _M_AutoChain
CASE _step OF
  10: _M_SetStep(100, 'Separate', 'Separator1.SEPARATE', T#8S, Separator1);
      IF Separator1.Error THEN _M_AdoptChild(Separator1); RETURN; END_IF
      IF NOT Separator1.Busy AND NOT Separator1.Done THEN
          Separator1.Command := E_SepCommand.SEPARATE;  Separator1.Execute := TRUE;
      END_IF
      IF Separator1.Done THEN  Separator1.Execute := FALSE;  _step := 20;  END_IF

  20: _M_SetStep(200, 'Clamp', 'ClampStation.CLAMP', T#5S, ClampStation);
      IF ClampStation.Error THEN _M_AdoptChild(ClampStation); RETURN; END_IF
      IF NOT ClampStation.Busy AND NOT ClampStation.Done THEN
          ClampStation.Command := E_ClampCommand.CLAMP;  ClampStation.Execute := TRUE;
      END_IF
      IF ClampStation.Done THEN  ClampStation.Execute := FALSE;  _step := 30;  END_IF

  30: _M_SetStep(300, 'Plasma-clean', 'RobotHandling.PROCESS_PART', T#30S, RobotHandling);
      _M_Await(1, 'Plasma gas OK', _hal.PlasmaGasOk);        // §6.9(b): plain-condition wait, named
      IF RobotHandling.Error THEN _M_AdoptChild(RobotHandling); RETURN; END_IF
      IF NOT RobotHandling.Busy AND NOT RobotHandling.Done THEN
          RobotHandling.Command  := E_HandlingCommand.PROCESS_PART;   // → Robot130.RUN_PATH internally (Annex I §I.6)
          RobotHandling.TargetId := ID_PROCESS_G1_1;                  // ID, not coordinates (Annex I §I.1)
          RobotHandling.Execute  := TRUE;
      END_IF
      IF RobotHandling.Done THEN  RobotHandling.Execute := FALSE;  _step := 35;  END_IF

  35: // ── evaluate result via the injected verdict hook (C.1) — 0 = no provider → always OK ──
      IF _verdict = 0 THEN
          _nokPending := FALSE;                          // no provider wired → C runs standalone
      ELSE
          _nokPending := NOT _verdict.Evaluate();        // NOK: _verdict.Reason is the machine's OWN
                                                         // first-out (§8.8) — no reject taxonomy. With
                                                         // Annex E wired, the provider records verdict +
                                                         // reason to carrier/MES (§E.2–E.3).
      END_IF
      _step := 40;                                       // ALWAYS unclamp first — the part must be released
                                                         // before it can be picked for disposition

  40: _M_SetStep(400, 'Unclamp', 'ClampStation.UNCLAMP', T#5S, ClampStation);
      IF ClampStation.Error THEN _M_AdoptChild(ClampStation); RETURN; END_IF
      IF NOT ClampStation.Busy AND NOT ClampStation.Done THEN
          ClampStation.Command := E_ClampCommand.UNCLAMP;  ClampStation.Execute := TRUE;
      END_IF
      IF ClampStation.Done THEN
          ClampStation.Execute := FALSE;
          _step := SEL(_nokPending, 50, 60);             // OK → finish · NOK → disposition
      END_IF

  60: // ── NOK disposition: segregate the bad part to the NIO drawer. NOT a special robot mode
      //    (Annex I §I.10.1) — an ordinary operation with a DIFFERENT destination. Transferring a part
      //    is pick + move + place, i.e. the handling EM's PLACE_PART_NOK (Annex I §I.6), which composes
      //    gripper close → MOVE_TEMPLATE(NEST_PROCESS → NEST_DRAWER_NIO) → gripper open. Shown here as
      //    one EM command; the robot exits the process nest via its default-EITHER entry corridor.
      _M_SetStep(600, 'Dispose NOK', 'RobotHandling.PLACE_PART_NOK', T#30S, RobotHandling);
      IF RobotHandling.Error THEN _M_AdoptChild(RobotHandling); RETURN; END_IF
      IF NOT RobotHandling.Busy AND NOT RobotHandling.Done THEN
          RobotHandling.Command  := E_HandlingCommand.PLACE_PART_NOK;
          RobotHandling.TargetId := NEST_DRAWER_NIO;       // disposition destination — ID only
          RobotHandling.Execute  := TRUE;
      END_IF
      IF RobotHandling.Done THEN  RobotHandling.Execute := FALSE;  _nokPending := FALSE;  _step := 50;  END_IF

  50: // finish — Stop idles the Unit; otherwise loop. Part leaves known-OK or known-NOK, never silently (Annex E)
      IF _stopReq THEN  _exec := E_ExecState.READY;  _step := 0;
      ELSE             _step := 10;  END_IF
END_CASE
```

This is the **SFC step chain written in ST** (§6.8 — SFC remains the default; ST shown here for the annex). The same chain in SFC would have steps `N100/N200/N300/N400/N999` with the `Done` transitions, plus an SFC **divergence** at the verdict (`N350`) to an `N600` NOK-disposition branch that re-joins before unclamp — behaving identically:

```
 ┌N100 Separate┐→┌N200 Clamp┐→┌N300 Plasma-clean┐→ N350 verdict ─┬─OK──→┌N400 Unclamp┐→ N999 ─loop→ N100
                                                                 └─NOK─→└N400 Unclamp┘→┌N600 Dispose NOK┐→ N999
   transitions = awaited command's Done (§6.5); N350 = SFC divergence on _verdict (§6.9(b) conditions named on stall)
```

---

## C.5 Mode cascade to the child Unit (§3.7)

`FixtureUnit` supports `AUTO/MANUAL/HOME` but not `CALIBRATION`:

```iecst
FUNCTION_BLOCK FB_FixtureUnit EXTENDS FB_Unit IMPLEMENTS I_Unit
// …
METHOD _M_Supports : BOOL
VAR_INPUT Mode : E_Mode; END_VAR
    _M_Supports := (Mode = E_Mode.AUTO) OR (Mode = E_Mode.MANUAL) OR (Mode = E_Mode.HOME);
```

So when the operator puts the station into `CALIBRATION`, the cascade in `SetMode` (C.3) calls `FixtureUnit.SetMode(CALIBRATION)`, which returns `FALSE`. The station does **not** force the child: it calls `FixtureUnit.Stop()` to bring it to a defined safe state and raises `EVENT_CHILD_MODE_UNSUPPORTED` ("`InfeedUnit.FixtureUnit`: mode not supported"). A parent in Calibration therefore never drags a child into an undefined state — exactly the rule of §3.7.

---

## C.6 The stall-diagnostic walk landing on the HMI (§6.9)

`_M_SetStep` records the current step and the module it awaits, and restarts the stall timer on each step change — and it is also the feed for the §8.11.4 cycle profiler (`StepChanged` on every step change, `CycleComplete` at the finish step), so the same one-line record produces both the stall diagnostic below and the Unit's cycle-time waterfall with no additional step code:

```iecst
METHOD PRIVATE _M_SetStep
VAR_INPUT no:INT; name:STRING(80); awaitingLabel:STRING(120); expected:TIME; awaiting:I_Module; END_VAR
VAR _i : INT; END_VAR
    IF _curStep.StepNo <> no THEN
        FOR _i := 1 TO 4 DO _curStep.Conds[_i].Label := ''; END_FOR   // clear condition records (§6.9(b))
        _curStep.StepNo := no;  _curStep.StepName := name;
        _curStep.AwaitingLabel := awaitingLabel;  _curStep.ExpectedTime := expected;
        _awaiting := awaiting;                 // 0 allowed (no single awaited child)
        tStep(IN := FALSE);                    // restart stall timer
    END_IF

METHOD PRIVATE _M_Await                        // §6.9(b) — register/refresh a named plain-condition wait
VAR_INPUT n : INT; label : STRING(60); ok : BOOL; END_VAR
    _curStep.Conds[n].Label := label;  _curStep.Conds[n].Ok := ok;
```

`_M_AdoptChild` is the immediate rollup when a child raises `Error` (it copies the child's first-out summary up — §8.2):

```iecst
METHOD PRIVATE _M_AdoptChild
VAR_INPUT child : I_Module; END_VAR
    OutImm.Diagnostic := child.GetFaultSummary();   // child reason + child SourcePath
    _M_HoldAll();                                   // stop the other children safely
    _exec := E_ExecState.ERROR;
```

`_M_StallWalk` handles the *slow* case — a step that simply isn't advancing — and composes the §6.9 message:

```iecst
METHOD PRIVATE _M_StallWalk
VAR  diag : ST_Diagnostic;  i : INT; END_VAR
    tStep(IN := TRUE, PT := _curStep.ExpectedTime);
    IF tStep.Q AND _exec = E_ExecState.BUSY THEN
        OutImm.StallReason := CONCAT5('Step ', INT_TO_STRING(_curStep.StepNo), ' ',
                                      _curStep.StepName, CONCAT(' stalled → awaiting ', _curStep.AwaitingLabel));
        IF (_awaiting <> 0) AND _awaiting.FaultActive THEN
            diag := _awaiting.GetFaultSummary();                       // walk into the child
            OutImm.StallReason := CONCAT4(OutImm.StallReason, ' → ', diag.SourcePath, CONCAT(': ', diag.Description));
            OutImm.Diagnostic  := diag;                                // adopt the child's first-out
        ELSE
            OutImm.Diagnostic.ReasonCode  := E_Reason.STEP_STALLED;
            OutImm.Diagnostic.SourcePath  := _name;
            FOR i := 1 TO 4 DO             // §6.9(b): name the first FALSE registered condition
                IF _curStep.Conds[i].Label <> '' AND NOT _curStep.Conds[i].Ok THEN
                    OutImm.StallReason := CONCAT3(OutImm.StallReason,
                        ' → awaiting ''', CONCAT(_curStep.Conds[i].Label, ''' = FALSE'));
                    EXIT;
                END_IF
            END_FOR
            OutImm.Diagnostic.Description := OutImm.StallReason;
        END_IF
    END_IF
```

Concrete trace — a clamp cylinder never reaches its sensor:

```
InfeedUnit  step N200 "Clamp"  ──awaits──▶  ClampStation.CLAMP
ClampStation step 20           ──awaits──▶  CylB.Done
CylB (FB_CylinderCM)           ──Error────▶  CYL_NOT_EXTENDED @ "InfeedUnit.ClampStation.CylB"
```

The operator sees, on the **Unit's** view:

> **Step 200 Clamp stalled → awaiting ClampStation.CLAMP → InfeedUnit.ClampStation.CylB: cylinder did not reach extended**

The same walk serves the robot step with no extra code — an unreachable taught point or a dropped controller link surfaces identically through the handling EM's rollup (`RobotHandling` adopts `Robot130`'s first-out exactly as the clamp EM adopts a cylinder's, §8.2; Annex I §I.6–I.7):

> **Step 300 Plasma-clean stalled → awaiting RobotHandling.PROCESS_PART → InfeedUnit.RobotHandling.Robot130: point 'ProcessG1-1.HelpCircle2' unreachable**

And a step held up by a **plain condition** — no module at fault — now names it instead of a blind stall (§6.9(b)):

> **Step 300 Plasma-clean stalled → awaiting RobotHandling.PROCESS_PART → awaiting 'Plasma gas OK' = FALSE**

…produced with no per-step diagnostic code at any tier — only the standard handshake, the step record, and the recursive `GetFaultSummary`. That is the whole lean-vs-diagnosable resolution (§6.9) demonstrated across all three tiers.

---

## C.7 Top-down recipe on changeover (§3.8)

Entering `CHANGEOVER` performs the §3.8 subtree transaction—source-agnostic (local, OPC UA, socket, REST):

```iecst
IF PrepareRecipe(Model := RequestedModel) THEN
    CommitRecipe();                    // infallible bounded publication
    Model := RequestedModel;           // publish only after the whole subtree swaps
ELSE
    AbortRecipe();                     // active ParCfg remains unchanged everywhere
END_IF
```

A child whose fetch, migration, or validation fails rejects prepare and reports `RECIPE_INVALID`; no participant commits and the prior model remains active. Commit contains no validation or I/O and cannot reject after successful preparation.

---

## C.8 HMI (§3.13)

The Flutter app renders the station by drilling the same tree, with the Unit's mode/Start-Stop and the live stall line at the top:

```
InfeedUnit            mode: AUTO ▾   [Start] [Stop]      State ● BUSY
  ▸ current: Step 200 Clamp · "…CylB: cylinder did not reach extended"   ← StallReason
  ├─ Separator1     (CM tile)
  ├─ ClampStation   (EM tile)  ├─ CylA  ├─ CylB
  ├─ RobotHandling  (EM tile) └─ Robot130 (CM tile: link LED ← Linked; Referenced ●)
  └─ FixtureUnit    (Unit tile) …
```

| View | Binding |
|------|---------|
| **Tile** | name; state LED ← `State`; mode badge ← `ModeActive`; child tiles beneath. |
| **Detail** | mode selector (calls `SetMode`, release-gated), `Start`/`Stop`; the live **`StallReason`** / `Diagnostic.Description` line; drill-through to `Separator1`, `ClampStation` (→ `CylA`/`CylB`), `RobotHandling` (→ `Robot130`: link/Referenced status; teaching stays in the robot controller's tool, Annex I §I.15), and `FixtureUnit`. |

Because the tree is self-describing over OPC UA (§3.10) and every node carries the same contract, none of this is hand-wired per station — the same screen logic renders any Unit.

---

## C.9 What the three annexes together demonstrate

- **One recursive model, three tiers**: a leaf CM (Annex A), a composite EM with rollup (Annex B), and a Unit orchestrating both plus a child Unit (here) — all sharing one handshake, one data contract, one diagnostic.
- **A robot is just another module**: the AUTO chain commands `RobotHandling.PROCESS_PART`/`PLACE_PART_NOK` exactly like `ClampStation.CLAMP` — one ID in, `Done` advances, `Error` rolls up three tiers (Unit → handling EM → robot CM) — so a six-axis arm and a cylinder are indistinguishable to the Unit, with the robot brand hidden behind the injected `I_RobotConnector` (§6.1, §10.6, Annex I §I.6).
- **Continuous vs. completing chains**: the Unit's AUTO chain loops until Stop; EM/CM commands complete (§6.2 vs §6.3).
- **NOK disposition is ordinary branching**: a bad-part verdict — delivered through the optional injected `I_VerdictProvider` (default always-OK; Annex E implements it) — diverts the chain to route the part to the NIO drawer via a normal robot move (Annex I §I.10.1); the part leaves *known-NOK* carrying the machine's own first-out reason, with no reject taxonomy and no special robot mode.
- **Mode cascade** with graceful rejection of an unsupported mode (§3.7).
- **Cross-tier diagnostics**: a single cylinder's first-out reason walks Unit → EM → CM to the operator with no per-step code (§6.9, §8.2).
- **Source-agnostic recipe** loaded top-down on changeover (§3.8).
- **Generic HMI**: every tier renders from the same self-describing tree (§3.13).

---

*End of Annex C (draft). Part of the worked-example set A–I referenced in §12.*
