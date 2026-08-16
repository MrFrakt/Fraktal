# Core/Modules TcUnit evidence — 2026-08-15

Gate: `FraktalCore/PLC/TwinCAT/Tests/Fraktal_Tests.plcproj`
Runner: `PRG_TcUnitRunner`
Libraries: Fraktal_Core **0.5.0.0**, Fraktal_Modules **0.4.0.0**

Observed XAE/TcUnit summary, 01:15 local:

| Field | Result |
|---|---:|
| Successful tests | 98 |
| Failed tests | 0 |
| Total tests | 98 |
| Test suites | 30 |
| Duration | 3.128244e-1 s |

The first Core/Modules result since **2026-08-01**, and the first at the current
inventory: that run was 84 tests / 26 suites, and the suite has since grown by
14 tests and 4 suites. Those four — `SequenceRaiseTests`, `SequenceParTests`,
`StateFlagTests` and `EngineeringTests` — had **never executed** until this
sequence of runs, which is exactly why the first of them found five failures.

## What it took

Four runs, and every failure was a **test** defect. None were framework defects;
`FB_UnitBase`, `FB_SequenceBase` and the §7.5/§10.5.1 additions all behaved as
specified. Recorded because the failure modes recur:

| run | result | closed |
|---|---|---|
| 2026-08-14 21:12 | 94 / 4 failed | baseline |
| 2026-08-14 21:42 | 94 / 4 failed | `Custom_message…` (registered vs unregistered reason) |
| 2026-08-14 23:00 | 96 / 2 failed | the resume path proved correct |
| **2026-08-15 01:15** | **98 / 0 failed** | overshoot + fixture isolation |

Three of the five were one shape: **this chain advances on the scan its condition
is met, not the one after**, so a test that budgets a following scan runs the
next step too. The fourth asserted unregistered-reason behaviour while passing a
registered reason. The fifth shared a Unit with a test that leaves it BUSY
forever, because `FB_ProbeUnit` only reaches its `_M_EndOfCycle` stop point when
`SimB` is set — so a `Stop()` there is never granted.

The sharpest finding is not a defect but worth knowing: `FB_UnitBase` samples the
error-cleared edge inside `OnCyclic`, which runs **before** `_M_Dispatch`. An
ERROR raised by this scan's dispatch is therefore invisible to it, and the
Execute-drop reset clears it at the top of the next scan. A test that faults a
Unit and resets it with no cyclic pass in between never produces the edge, so the
chain is never re-armed and the §3.13 row marks stay. Real operation always has
that pass, because a Unit sits in ERROR until an operator acts.

## Target and its limits

Executed on the **local development usermode runtime** `UmRT_Default`
(AmsNetId `192.168.1.6.1.1`), not the isolated VM `192.168.132.128.1.1` the
committed wrapper names — that VM was unreachable. A development runtime is not a
machine, and this is not a machine-acceptance result.

Driven by `tools/Invoke-TwinCatTcUnitGate.ps1`, which performed target check,
autostart assertion, activation and download automatically. The summary above was
read from the TwinCAT log window, which is why this record carries no raw-log
hash.

> **Correction, 2026-08-16.** This section originally also credited the gate with
> "PLC login and PLC start", and attributed the empty capture to `ADSLOGSTR`
> output being unpersistable. Both claims were inferred from `Start()` returning
> without error, and neither holds. Measured on 2026-08-16: after `Start()`, PLC
> port 851 reports ADS state `Invalid` continuously and publishes no symbol table
> at all, while the same ADS client reads `Run` correctly on ports 10000 and 300.
> XAE also logs `Unknown TMC file version found - ignoring the file` for the
> `Fraktal_Tests.tmc` it had just generated. **The application is downloaded but
> never enters Run under this gate**, so there was never any TcUnit output to
> capture — every run recorded 0 rows from `PlcTask`.
>
> The 98/98 result itself stands: 98 tests genuinely executed and passed, with a
> real duration, and the test fixes and framework findings above are unaffected.
> What is withdrawn is the claim that the automated gate executed them. It did
> not; a person did, in XAE. Until the run step is fixed, this gate compiles,
> activates and downloads — it does not test.
