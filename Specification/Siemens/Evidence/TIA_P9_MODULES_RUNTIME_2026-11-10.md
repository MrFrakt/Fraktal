# P9 module types run natively (2026-11-10)

[The first native compile](TIA_P9_MODULES_NATIVE_2026-11-10.md) left
`FB_ClampEM`, `FB_ConfigurableCylinderCM` and `FB_SeparatorCM` compiled but
never executed. This record adds a native behaviour suite, three defects it
confirmed on the controller, and their fixes.

## The suite

`Tests/ReusableModules/make_fixture.py` now replaces the composition's `Main`
with a case driver: one case per scan, an injected `FRK_Clock.NowMs`, the root
Unit called exactly as the composition calls it, and `FRK_TestAssert` codes
published through `FRK_TestStatus` (the Lifecycle fixture's form on the gate's
runtime). It mirrors the TC3 suites `FB_ConfigurableCylinderCM_Tests`,
`FB_Separator_Tests` and `FB_ClampEM_Tests`: duplex agreement and settle,
discrepancy, T3 hold, move timeout with and without `ResetOnTimeout`, the
configured abort reaction, invalid timing; separator interlock, one-carrier
release with and without `CheckAfter`, no-carrier fault, unsupported command;
clamp parallel children, T3 through the EM naming the blocked child, and the
child first-out rollup. 46 assertions; reserved bench `FrkModulesTest`
(`169.254.212.57`, unmapped). The gate compiles and runs it beside Operations.

## The defects

| Defect (TIA port) | TC3 behaviour | Pre-fix codes failing |
|---|---|---|
| Configurable cylinder outputs were ANDed with `Exec <> ERROR AND <> ABORTED`, so `SafePosOnAbort`, `DeenergizeOnAbort := FALSE` and `ResetOnTimeout := FALSE` had no effect | `OnAbort` sets the coils once; a fault leaves them unless configured | 21, 23, 24 |
| A HELD configurable cylinder kept its move timer running, so releasing a hold longer than `MoveTimeout` faulted at once | (TC3 faults on interlock loss instead; the TIA port holds per Core §6.1, as the separator and cylinder do) | 15, 16 |
| Separator with `CheckAfter := FALSE` entered step 40 without stamping `CloseStartMs`, closing against a stale stamp | `_tClose` starts on entering step 40 by either path | 35 |

Fixes: the abort regions state the safe position as device state that the
per-scan output law honours, and the law no longer forces the coils off by
state (the live permit still always withdraws them); a hold in step 20
re-enters step 10, which re-arms the move timer; the separator stamps the close
timer on both paths into step 40.

## Native results

| Run (`%LOCALAPPDATA%\Fraktal\TiaSpikes\…`) | Result |
|---|---|
| `P9_ModulesPreFix_20261110_01` (unfixed templates, same suite) | compile 0/0; bench 46 checks, **6 failures**: codes 15, 16, 21, 23, 24, 35, exactly the three defects; all others pass |
| `P9_ModulesFixed_20261110_01` | compile 0/0, read-back 305 objects, 93 interfaces, 18 DB interfaces; bench **46/46**, image hash `4ccc14c35d36eb03ac553541f18ce3ddb709bd453a470a9ad1eed3e531d7b31c` |
| `TiaGate_P9Run_20261110_01` (full gate) | PASS: 292 tool tests, lint/consistency/contracts clean, press replay 286; Operations 0/0, read-back 297/85/22, bench **108/108**; modules 0/0, read-back 305/93/18, bench **46/46** with the same image hash as the run above |

In every run the saved `Fraktal` instance read RUN with unchanged addresses and
zero mappings before and after, and the test CPU was released.

## Divergences from TC3 kept on purpose

- The configurable cylinder holds on a lost interlock (TC3 faults). Core §6.1
  and the binding's other actuators treat an expected, restorable condition as
  HELD.
- `FB_CylinderCM` on this binding has no device timeout reason; the clamp
  rollup therefore adopts CylB's frame `TIMEOUT` (2001) with CylB's path, where
  TC3 adopts `CYL_NOT_EXTENDED`. The rollup itself (verbatim first-out naming
  the child) is what the row proves.

## Harness findings

- The bench reader now reports every failing code, not only the first, and the
  JUnit label lists them. While making that change a variable reuse made an
  empty failure list report PASS; it was caught when a failed download printed
  "PASS, 0 assertions", fixed before any commit, and the earlier P8 gate ran
  before the change.
- Three earlier attempts crashed TIA Portal during the download (the first
  report says `System.OutOfMemoryException`): with the test CPU powered on,
  free commit was about 4 GB. With no test CPU, the same project reopened and
  compiled 0/0. The runs above followed freeing memory and disk.
