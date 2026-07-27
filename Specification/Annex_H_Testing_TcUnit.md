# Annex H — Worked Example: Module Test Suite (TcUnit)

*Companion to **Fraktal Core** (Part I) exercised through the **Fraktal/TC3** binding (Part II); slots under Core §12.*
*Core concepts demonstrated: conformance test checklist T1–T9 (§5.7), handshake/first-out/interlock/rollup under test (§6.1, §6.9, §7, §8.2), sim-only force hooks (§5.7). / TC3 mechanics used: TcUnit suites & TcUnit-Runner CI gate (TC3 §5.7).*
*Reference implementation — illustrative, not compile-tested; validate against the pinned TwinCAT version and the TcUnit release in use.*

This annex builds the **automated test suite** for a reusable module *type* (§5.7) and shows what no other annex does: the standard's promises — the handshake (§6.1), the **first-out diagnostic** (§6.9), and the interlock reaction (§7) — **proven automatically against the simulated HAL** (§2.6), and a small sub-tree's **rollup** (§8.2) checked end-to-end. The unit under test is the Annex B cylinder Control Module; the suite runs with no hardware and gates the merge in CI.

```
FB_CylinderCM (Annex B)  ◀── unit under test (driven through its sim HAL)
FB_CylinderCM_Tests : TcUnit.FB_TestSuite      ← H.2–H.4 (unit)
FB_ClampRollup_Tests : TcUnit.FB_TestSuite     ← H.5 (integration, reuses Annex B EM)
PRG_TcUnitRunner  ─▶  TcUnit.RUN()  ─▶  JUnit XML  ─▶  CI gate (§6.8)
```

The key enabler is §1.1 O6: because every module runs unchanged against the **simulated HAL** (§10), the same code is testable on any build agent. The test, acting as the *plant*, drives the HAL feedback the device would normally produce.

---

## H.1 Suite skeleton

A suite extends `TcUnit.FB_TestSuite`; each `TEST(...)`/`TEST_FINISHED()` pair is one case. The cylinder is wired once to a **simulated** HAL and a stub recipe (`MoveTimeout`), exactly as the Unit wires it in production (§3.11) — only the HAL is simulated.

```iecst
FUNCTION_BLOCK FB_CylinderCM_Tests EXTENDS TcUnit.FB_TestSuite
VAR
    _cm     : FB_CylinderCM;        // unit under test (Annex B)
    _hal    : ST_CylinderHal;       // sim HAL: ExtendOut/RetractOut, ExtendedFb/RetractedFb
    _recipe : FB_StubRecipe;        // MoveTimeout := T#2S
    _wired  : BOOL;
    _t      : TON;                  // for multi-cycle waits
END_VAR
IF NOT _wired THEN
    _cm.Setup(Name := 'Test.Cyl', HalRef := _hal, Recipe := _recipe);  _wired := TRUE;
END_IF
```

`_hal` is a plain struct here: with no real I/O mapped, writing `_hal.ExtendedFb` **is** the simulated sensor (the SIM toggle of §10.1, exercised by the test instead of a sim model).

---

## H.2 The handshake completes on feedback (§6.1)

A multi-cycle test (the documented TcUnit pattern): command `EXTEND`, let the CM raise `ExtendOut`, then — acting as the cylinder — make the sensor, and assert the handshake reaches `Done`.

```iecst
TEST('Extend_completes_when_feedback_made');
    _cm.Command := E_CylinderCommand.EXTEND;  _cm.Execute := TRUE;
    _cm();                                   // CM scans: drives _hal.ExtendOut, goes Busy
    IF _hal.ExtendOut THEN _hal.ExtendedFb := TRUE; END_IF   // plant: sensor reached
    _cm();                                   // CM scans again: sees feedback → Done
    AssertTrue(Condition := _cm.Busy OR _cm.Done, Message := 'should be Busy then Done');
    IF _cm.Done THEN
        AssertEquals_BOOL(Expected := TRUE,  Actual := _cm.Done,  Message := 'Done expected');
        AssertEquals_BOOL(Expected := FALSE, Actual := _cm.Error, Message := 'no Error expected');
        _cm.Execute := FALSE;  _cm();        // drop Execute → returns to idle (§6.1)
        AssertEquals_BOOL(Expected := FALSE, Actual := _cm.Busy, Message := 'idle after Execute drops');
        TEST_FINISHED();
    END_IF
```

---

## H.3 The first-out diagnostic is itself under test (§6.9, §8.8)

Withhold the sensor and let `MoveTimeout` elapse; assert the **exact** reason and source path the operator would see. This is the test that guards the standard's signature capability.

```iecst
TEST('Extend_faults_first_out_when_feedback_withheld');
    _cm.Command := E_CylinderCommand.EXTEND;  _cm.Execute := TRUE;
    _hal.ExtendedFb := FALSE;                       // plant: cylinder never arrives
    _t(IN := TRUE, PT := T#2200MS);                 // > MoveTimeout (2 s)
    _cm();                                          // tick the UUT every cycle
    IF _t.Q THEN
        AssertTrue(Condition := _cm.Error, Message := 'Error expected after MoveTimeout');
        AssertEquals_DINT(
            Expected := E_Reason.CYL_NOT_EXTENDED,
            Actual   := _cm.OutImm.Diagnostic.ReasonCode,
            Message  := 'first-out reason must be CYL_NOT_EXTENDED');
        AssertEquals_STRING(
            Expected := 'Test.Cyl',
            Actual   := _cm.OutImm.Diagnostic.SourcePath,
            Message  := 'reason must name the source path');
        _t(IN := FALSE);  TEST_FINISHED();
    END_IF
```

---

## H.4 A dropped interlock produces the defined reaction (§7)

With a permissive forced low, the command **shall not** drive the output and **shall** report `INTERLOCK_DROPPED` (the §7 contract), not silently stall.

```iecst
TEST('Extend_blocked_when_permissive_dropped');
    _cm.SimForceInterlock(id := 1, ok := FALSE);    // test hook: drop 'Area safe'
    _cm.Command := E_CylinderCommand.EXTEND;  _cm.Execute := TRUE;
    _cm();
    AssertEquals_BOOL(Expected := FALSE, Actual := _hal.ExtendOut,
                      Message := 'output must not energize while interlocked');
    AssertEquals_DINT(Expected := E_Reason.INTERLOCK_DROPPED,
                      Actual := _cm.OutImm.Diagnostic.ReasonCode,
                      Message := 'interlock reason expected');
    TEST_FINISHED();
```

---

## H.5 Integration: the cross-tier rollup (§8.2, §6.9)

Assemble the **Annex B clamp EM** with one cylinder's sensor withheld and assert the EM **adopts the child's first-out** — proving the recursive `GetFaultSummary` walk, not just a leaf reason.

```iecst
FUNCTION_BLOCK FB_ClampRollup_Tests EXTENDS TcUnit.FB_TestSuite
VAR  _em : FB_ClampEM;  _halA, _halB : ST_CylinderHal;  _recipe : FB_StubRecipe;  _wired : BOOL;  _t : TON; END_VAR
IF NOT _wired THEN
    _em.Setup(Name := 'ClampStation', HalA := _halA, HalB := _halB, Recipe := _recipe);  _wired := TRUE;
END_IF

TEST('Clamp_rolls_up_CylB_first_out');
    _em.Command := E_ClampCommand.CLAMP;  _em.Execute := TRUE;
    IF _halA.ExtendOut THEN _halA.ExtendedFb := TRUE; END_IF     // CylA completes
    _halB.ExtendedFb := FALSE;                                   // CylB never arrives
    _t(IN := TRUE, PT := T#2200MS);  _em();
    IF _t.Q THEN
        AssertTrue(Condition := _em.Error, Message := 'EM should fault');
        AssertEquals_DINT(Expected := E_Reason.CYL_NOT_EXTENDED,
                          Actual := _em.OutImm.Diagnostic.ReasonCode,
                          Message := 'EM adopts child first-out');
        AssertEquals_STRING(Expected := 'ClampStation.CylB',
                          Actual := _em.OutImm.Diagnostic.SourcePath,
                          Message := 'rollup must name CylB');
        _t(IN := FALSE);  TEST_FINISHED();
    END_IF
```

This is the §6.9/§8.2 promise — *"ClampStation.CylB: cylinder did not reach extended"* — asserted automatically, so a future refactor of the EM or CM that breaks the rollup fails CI immediately.

---

## H.6 Running in CI (§6.8)

A small runner program executes every suite; `TcUnit-Runner` drives it headless on the build agent and converts results to **JUnit XML**, which the CI server reports natively and uses to gate the merge — alongside the lint checks of §5.5/§6.8.

```iecst
PROGRAM PRG_TcUnitRunner
VAR  CylTests : FB_CylinderCM_Tests;  ClampTests : FB_ClampRollup_Tests; END_VAR
    TcUnit.RUN();        // discovers & runs all suites; results harvested by TcUnit-Runner
```

Gate sequence on every commit: **lint** (naming, step/condition records, contract usage — §5.5/§6.8) → **test** (these suites, against sim) → **build**. A module *type* is releasable only when its suite is green **against the §5.7 conformance checklist (T1–T9, applicable rows per tier)** — the checklist, not the suite's mere existence, is the bar (§1.5, §5.7). Coverage status (verified 2026-07-26 against the repo, 67 tests / 24 suites): the **CM tier is complete** — `FB_CylinderCM_Tests` covers **T1–T5** explicitly, so the earlier note that T4/T5 were "left as the reader's exercise" is superseded. The **EM and Unit tiers are not**: `FB_ClampEM_Tests` proves T6 (rollup) and `FB_ClampStationUnit_Tests` proves only that the root is a Unit, leaving the other applicable Unit rows (T1–T5, T8, T9, T10) unproven. Those rows are **required for a release claim** on those types (§1.5, §5.7) — see `OBJECTIVES_AUDIT.md` gap **G9**.

The gate is **open-ended by design**: every later module-type suite joins it unchanged. The Annex I robot suites — `FB_RobotCM`, the route planner, and the help resolver (§I.14) — run against their **simulated connector** on the same build agent and gate the same merge, exactly as the cylinder and clamp suites here. Adding a module type adds suites, never gate plumbing.

---

## H.7 What this annex demonstrated

- A reusable module **type** verified by a **TcUnit** suite against the **simulated HAL** — no rig (§5.7, §2.6, §10).
- The **handshake** (§6.1), the **first-out reason and source path** (§6.9, §8.8), and the **interlock reaction** (§7) all asserted automatically — the standard's promises are themselves under test.
- An **integration test** asserting the cross-tier **rollup** (§8.2), so a refactor that breaks diagnosability fails CI.
- **Scope discipline (NG2):** tests live in the type's suite, never in application step bodies — verification is paid **once per type**, reinforcing the low-effort objective (§1.1 O1).
- **CI wiring** (lint → test → build) extending the existing gate (§6.8, §1.5).

---

*End of Annex H (draft). Part of the worked-example set A–I referenced in §12.*
