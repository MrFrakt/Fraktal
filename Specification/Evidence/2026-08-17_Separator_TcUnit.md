# Annex A separator — TcUnit evidence, 2026-08-17

First execution of `FB_SeparatorCM`, the Annex A worked example, and the first
runtime record covering a module type written after the ADS reader existed.

## Result

| Field | Result |
|---|---:|
| Test suites | 32 |
| Tests | 112 |
| Successful tests | 112 |
| Failed tests | 0 |

`tcunit_to_junit.py`: `CoreModules: PASS: 112/112 tests across 32 suites`, exit 0,
against `--expected-tests 112 --expected-suites 32 --expected-runner
PRG_TcUnitRunner`.

`SeparatorTests` — all six green:

- `Library_declares_no_interlocks_and_application_conditions_are_fail_closed`
- `Interlock_withholds_the_valve_and_holds_rather_than_faults`
- `Separate_releases_one_carrier_and_completes`
- `No_carrier_at_the_separator_faults_10001`
- `Open_close_confirms_feedback_only_when_configured`
- `Unsupported_command_is_rejected`

## Identity (§8)

| | |
|---|---|
| Gate | `Tests/Fraktal_Tests.plcproj`, runner `PRG_TcUnitRunner` |
| Libraries | Fraktal_Core **0.5.0.0**, Fraktal_Modules **0.5.0.0** |
| XAE / XAR | TwinCAT **3.1.4026.24**, `TwinCAT OS (x64)`, Debug |
| Target | `192.168.1.6.1.1`, ADS port **851**, Autostart disabled |
| Raw log | `2026-08-17_Separator_TcUnit.raw.log` — `007430b526f344d785627e10e7da03de19dacd3b9dfe117a8c666abb6bc0c09d` |
| JUnit | `2026-08-17_Separator_TcUnit.junit.xml` — `419f550164bed2266a87c1a4eff8d42cb0529fe3ddf2aba28670f71c35d2fca3` |

Started by an operator per `Guides/TWINCAT_XAE_WORKFLOW.md` §6.2; read over ADS
with `Read-TcUnitResults.ps1`.

## What the three runs cost

The module compiled clean on the first attempt. Execution still took three
passes, and the failures are worth keeping because they are three *different*
classes:

| Run | Symptom | Cause |
|---|---|---|
| 1 | never completed; `AllTestSuitesFinished` stayed FALSE | **test**: no `TEST_FINISHED()`. 31 of 32 suites call it; this one did not |
| 2 | `the command faults` | **test**: `MaxOpenTime := T#1MS` never expired — calling the FB N times inside one test scan does not advance a `TON` |
| 3 | `the valve is dropped on fault` | **module**: `_M_FaultN` raises the reason but does not touch outputs, so the separator faulted with the stopper still energised |

The third is the significant one: **a genuine implementation defect**, not a test
defect — the first in this session's new suites, where the previous five were all
fixtures. A separator that reports ERROR while holding itself open keeps
releasing carriers it can no longer account for. Annex A faults and closes in one
step for exactly that reason; the implementation split them and lost it. Fixed by
`_M_FaultClosed`, which withdraws before raising, used on all five fault paths.

Source review would not have found it. Every individual line reads correctly; the
defect is in what the two correct lines together fail to do.

The first failure is also worth recording for its *shape*: a missing
`TEST_FINISHED()` does not produce a failing test, it produces a suite that never
finishes and reports nothing at all. Under the old log-scraping gate that is
indistinguishable from "the tests never ran". The ADS reader said instead that
the symbol root resolved and `AllTestSuitesFinished` never went true, which
separated the two on the first attempt.

## Limits

Development usermode runtime, not the isolated VM and not a machine. Operator
started; under §5.7 this is a green run and not "green in CI".
