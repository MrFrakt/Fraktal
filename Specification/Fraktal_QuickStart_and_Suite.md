# fraktal-core — Base Suite, Scaffold & Quick-Start (Fraktal/TC3)
*Completes P1-b/P3 deliverables. Draft — validate against pinned TwinCAT + TcUnit.*

## 1. Base-class TcUnit suite — T1/T4 proven ONCE (§5.7)
```iecst
FUNCTION_BLOCK FB_ProbeCM EXTENDS FB_ControlModuleBase   // minimal concrete probe for the base
VAR_INPUT SimDone, SimFault : BOOL; END_VAR
METHOD PROTECTED _M_Dispatch
    IF SimFault THEN _M_Fault(E_Reason.TEST_FAULT, 'probe');
    ELSIF SimDone THEN _M_Complete(); END_IF

FUNCTION_BLOCK FB_Base_Tests EXTENDS TcUnit.FB_TestSuite
VAR _p : FB_ProbeCM; END_VAR
TEST('T1_handshake_and_execute_drop_reset');
    _p.Execute := TRUE;  _p();                        AssertTrue(_p.Busy,  'Busy on edge');
    _p.SimDone := TRUE;  _p();                        AssertTrue(_p.Done,  'Done on complete');
    _p.Execute := FALSE; _p();  AssertFalse(_p.Busy OR _p.Done, 'idle after drop');  TEST_FINISHED();
TEST('T4_abort_reports_and_no_auto_resume');
    _p.Execute := TRUE; _p();  _p.Abort := TRUE; _p();
    AssertTrue(_p.Aborted, 'Aborted reported');  _p.Abort := FALSE; _p();
    AssertFalse(_p.Busy, 'no self-resume while Execute held');  TEST_FINISHED();
```
Every type inheriting the base inherits these guarantees; its own suite covers T2/T3/T5(+tier rows).

## 2. Scaffold template — **test-first** (new idea, O1+O6)
`FraktalCore/PLC/TwinCAT/scaffold/FB_TemplateCM/` ships THREE files, generated together:
- `FB_⟨Type⟩CM.TcPOU` — `EXTENDS FB_ControlModuleBase`; stub `Command : E_⟨Type⟩Command`, `ParCfg` (+`SchemaVersion`), HAL ref, empty `_M_Dispatch` with `// TODO CASE _step`.
- `FB_⟨Type⟩CM_Tests.TcPOU` — **pre-wired, initially RED**: `T2_first_out_reason_and_path`, `T3_interlock_withholds_output`, `T5_recipe_invalid_faults` with `Expected := E_Reason.⟨TODO⟩` placeholders that fail until the type earns them.
- `SKELETON.md` — the §5.7 row map + reason-band reservation reminder (§8.8).
**The checklist thus *drives* development**: a type is born failing its conformance bar and is done when CI turns it green — no post-hoc audit gap.

## 3. Quick-start — *your first Fraktal module* (the §1.1 deliverable)
1. **Scaffold** `FB_GateCM` from the template; reserve a reason band (§8.8, e.g. `10401–10403`).
2. **Declare** `E_GateCommand (OPEN/CLOSE)`, `ST_GateHal` (2 outs, 2 sensors), `GateParCfg (MoveTimeout, SchemaVersion)`.
3. **Write `_M_Dispatch` only** (~15 lines): CASE step → drive output → await sensor → `_M_Complete()` / `_M_Fault(GATE_NOT_OPEN,…)`. Interlocks via `FB_PermIntlk`; lifecycle is inherited.
4. **Turn the RED suite GREEN**: fill the T2/T3/T5 expected values; run TcUnit against the sim HAL (§2.6) — no rig.
5. **Wire once** in the parent's `Setup` (§3.11); the tile renders itself (§3.13). *Total: one CASE body + three expected values. Everything else is Fraktal.*

## 4. Deferred by design
Incremental `[TC3]` tagging of the existing body proceeds opportunistically per the §1.1 convention (all *new* platform text is tagged); a dedicated tagging pass is scheduled with the Part I/II split.
