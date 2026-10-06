# Core/Modules TcUnit evidence — 2026-08-23

**The first runtime record of the robot route planner.** `FB_RobotPlanner_Tests`
(suite ID 30) ran for the first time on the runtime and passed 10/10 on its
first execution — the declarative routing model of Annex I I.9–I.10.2, built in
commit `39c0650`, now has runtime proof and not only a compiling type.

## Result

| Field | Result |
|---|---:|
| Test suites | 34 |
| Tests | 126 |
| Successful tests | 126 |
| Failed tests | 0 |
| Duration | 0.3447692 s |

`tcunit_to_junit.py` verdict: `CoreModules: PASS: 126/126 tests across 34 suites`,
exit 0, checked against `--expected-tests 126 --expected-suites 34
--expected-runner PRG_TcUnitRunner`.

Of the 126, ten are the planner suite: the scan junction resolving HELP5 from
the process side and HELP4 from the drawer side **from the same two table rows
and in both directions**; nest-to-nest emitting depart → transit → approach;
the approach corridor emitted reversed and landing exactly on the nest;
per-gripper corridors differing with no conditional code; a taught-list
corridor; `ROBOT_NO_ROUTE` on a disconnected graph; the one-way nest refusing
its reversal loudly; malformed endpoints rejected before planning; and the
direct nest list bypassing help routing.

## Identity (§8)

| | |
|---|---|
| Repository revision | `3189fdf` (working tree, this commit) |
| Gate | `FraktalCore/PLC/TwinCAT/Tests/Fraktal_Tests.plcproj` |
| Runner | `PRG_TcUnitRunner` |
| Libraries | Fraktal_Core **0.6.0.0**, Fraktal_Modules **0.6.0.0** |
| XAE / XAR | TwinCAT **3.1.4026.24** (ADS 4.3.32, Base v170) |
| Platform | `TwinCAT OS (x64)`, Debug |
| Target | `192.168.1.6.1.1`, ADS port **851** (local UmRT) |
| Autostart Boot Project | **disabled** — asserted by the gate before activation |
| `Fraktal_Tests.plcproj` | `d7b9642cd5c612d6262e14b72699b274f1ac05d4521ba19695910e40376bd7b4` |
| `Fraktal_Tests.tmc` | `54e1dbf5619613d1bd88a7d9daddd58ff49cadaa2d1343ac9e83ab38b4afc9e2` |
| Raw log | `2026-08-23_Core_Modules_TcUnit.raw.log` — `efcfc416fcecb2e6e6622545aa89f0f41d97500f53e7326b944eece834273fd4` |
| JUnit | `2026-08-23_Core_Modules_TcUnit.junit.xml` — `8003e334e13e988b3829842bfd34014fa32df5a4cfe77931c55e9b1915b56106` |

Both artifacts are committed beside this record, so the result is re-checkable
rather than asserted.

## How it was produced

`Invoke-TwinCatTcUnitGate.ps1 -Interactive` drove compile (clean), activation,
and the restart into Run on the local UmRT. Its own DTE `Login()` remained the
documented no-op (guide §9.1: the create/download prompt must be answered, and
a suppressed or unattended prompt is declined), so the operator answered the
PLC login prompt in the visible XAE — guide §6.2 step 6 — which downloaded and
started the application. The tests ran to completion at 18:29:24 while the
script was still polling its own login object, and the script then failed its
post-hoc assertion; the record here rests on the two independent reads below,
not on the script's exit.

The result was then read with:

```powershell
.\FraktalCore\PLC\TwinCAT\tools\Read-TcUnitResults.ps1 `
  -NetId 192.168.1.6.1.1 -OutputLog artifacts\tcunit\run2-2026-08-23.log
```

which reads TcUnit's own `ST_TestSuiteResults` over ADS — per-suite and
per-test — and validated with `tcunit_to_junit.py`.

A first attempt at 18:02 stalled at the same DTE login step with the prompt
unanswered. The `'TC3 PLC' not found` license-violation line appears in **both**
attempts' logs (the known UmRT demo-mode pattern; validation then reports
`Valid(3)`), so it did not differentiate them — the answered prompt did.
