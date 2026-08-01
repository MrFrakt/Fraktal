# fraktal-core — Module Base Classes (Fraktal/TC3)
*Implements §2.2 / §6.1: the lifecycle written once. Draft — validate against the pinned TwinCAT version.*

> **Superseded by the implementation (M1, 2026-07-02).** The normative surface is Core §2.2/§3.2, and the source of truth is `FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core`. Known deltas of this rationale draft include the current §3.14 hook names, `ST_Diagnostic`, the transactional recipe API, `F_Now()`, and valid ST membership checks. This file is non-normative.

```iecst
// ───────── shared contract types (§6.1, §8.8) ─────────
{attribute 'qualified_only'}
TYPE E_ExecState : (READY := 0, BUSY := 1, DONE := 2, ERROR := 3, ABORTED := 4) DINT; END_TYPE

TYPE ST_Diagnostic : STRUCT
    ReasonCode  : E_Reason;        // §8.8 registered vocabulary
    Description : STRING(120);
    SourcePath  : STRING(255);     // browse path of the module that first knew (§4.8)
    Stamp       : DT;              // §2.7 synchronized clock
END_STRUCT END_TYPE

INTERFACE I_Module
    PROPERTY Name        : STRING(80)
    PROPERTY FaultActive : BOOL
    METHOD  GetFaultSummary : ST_Diagnostic          // recursive first-out walk (§8.2, §6.9)
    METHOD  PrepareRecipe : BOOL                    // load and validate staging data
    METHOD  CommitRecipe                           // infallible publish after Prepare
    METHOD  AbortRecipe                            // discard staging data
END_INTERFACE

// ───────── FB_ModuleBase — the §6.1 lifecycle, once ─────────
FUNCTION_BLOCK ABSTRACT FB_ModuleBase IMPLEMENTS I_Module
VAR_INPUT  Execute : BOOL;  Abort : BOOL; END_VAR    // Command lives in the concrete type
VAR_OUTPUT Busy, Done, Error, Aborted : BOOL; ErrorID : DWORD; END_VAR
VAR
    _name : STRING(80);  _exec : E_ExecState;  _step : INT;
    _diag : ST_Diagnostic;  _rTrig : R_TRIG;
END_VAR

METHOD PROTECTED ABSTRACT _M_Dispatch                // the ONLY thing a type must write (§2.2)
METHOD PROTECTED _M_OnAbort                          // optional override: device-safe abort action
    _exec := E_ExecState.ABORTED;  _step := 0;

METHOD PROTECTED _M_Fault                            // stamp first-out and hold (§6.9)
VAR_INPUT reason : E_Reason; text : STRING(120); END_VAR
    _diag.ReasonCode := reason;  _diag.Description := text;
    _diag.SourcePath := _name;   _diag.Stamp := SysTime();     // [TC3]
    _exec := E_ExecState.ERROR;  _step := 0;

METHOD PROTECTED _M_FaultDiag                        // adopt a ready-made diagnostic (rollup/connector)
VAR_INPUT d : ST_Diagnostic; END_VAR
    _diag := d;  _exec := E_ExecState.ERROR;  _step := 0;

METHOD PROTECTED _M_Complete   _exec := E_ExecState.DONE;  _step := 0;  _M_ClearDiag();
METHOD PROTECTED _M_ClearDiag  _diag.ReasonCode := E_Reason.NONE;  _diag.Description := '';

// I_Module
PROPERTY Name : STRING(80)          Name := _name;
PROPERTY FaultActive : BOOL         FaultActive := (_exec = E_ExecState.ERROR);
METHOD GetFaultSummary : ST_Diagnostic   GetFaultSummary := _diag;
METHOD PrepareRecipe : BOOL         PrepareRecipe := TRUE;   // override where ParCfg exists (§3.8)
METHOD CommitRecipe
METHOD AbortRecipe

// ── cyclic body: edge → dispatch → map → reset ──
_rTrig(CLK := Execute);
IF _rTrig.Q AND _exec = E_ExecState.READY THEN _exec := E_ExecState.BUSY; _step := 10; END_IF
IF Abort AND _exec = E_ExecState.BUSY THEN _M_OnAbort(); END_IF
IF _exec = E_ExecState.BUSY THEN _M_Dispatch(); END_IF
Busy    := (_exec = E_ExecState.BUSY);   Done  := (_exec = E_ExecState.DONE);
Error   := (_exec = E_ExecState.ERROR);  Aborted := (_exec = E_ExecState.ABORTED);
ErrorID := TO_DWORD(_diag.ReasonCode);
IF NOT Execute AND _exec IN (E_ExecState.DONE, E_ExecState.ERROR, E_ExecState.ABORTED) THEN
    _exec := E_ExecState.READY;                       // Execute-drop reset (§6.1)
END_IF

// ───────── FB_CompositeModuleBase — adds children + rollup (§8.2) ─────────
FUNCTION_BLOCK ABSTRACT FB_CompositeModuleBase EXTENDS FB_ModuleBase
VAR  _children : ARRAY[1..MAX_EM_CHILDREN] OF I_Module;  _nChild : INT; END_VAR

METHOD PROTECTED _M_Register                          // called from the type's Setup (§3.11)
VAR_INPUT child : I_Module; END_VAR
    _nChild := _nChild + 1;  _children[_nChild] := child;

METHOD PROTECTED _M_RollupFault : BOOL                // adopt first faulted child's first-out (§8.2)
VAR i : INT; END_VAR
    FOR i := 1 TO _nChild DO
        IF _children[i].FaultActive THEN
            _M_FaultDiag(_children[i].GetFaultSummary());  _M_RollupFault := TRUE;  RETURN;
        END_IF
    END_FOR
```

**Usage (the whole point):** `FUNCTION_BLOCK FB_AxisCM EXTENDS FB_ControlModuleBase` declares its `Command`/HAL/four-structure contract and overrides only `_M_Dispatch` plus any required §3.14 hook such as `OnAbort` (base first). Edge handling, state mapping, reset, `ErrorID`, timing, and abort routing come from `FB_ModuleBase`. Annexes B/D/G/I keep only their device-logic bodies. Rows **T1/T4** are tested once at the common base; types remain responsible for their type-specific rows.
