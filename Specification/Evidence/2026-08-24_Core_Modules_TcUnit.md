# Core/Modules TcUnit evidence — 2026-08-24

**The first runtime record of the Stäubli VAL3 connector.** `FB_RobotConnector_Tests`
(suite ID 31) ran on the runtime twice today: 130/132 first, 132/132 after the two
test defects were fixed. The connector code itself was unchanged between the runs —
both failures were the harness being unable to observe the connector, not the
connector misbehaving — which is worth recording because it is the third time this
week the defect class was "the test", not the code.

## Result

| Field | Result |
|---|---:|
| Test suites | 35 |
| Tests | 132 |
| Successful tests | 132 |
| Failed tests | 0 |
| Duration | 0.3760926 s |

`tcunit_to_junit.py` verdict: `CoreModules: PASS: 132/132 tests across 35 suites`,
exit 0, checked against `--expected-tests 132 --expected-suites 35
--expected-runner PRG_TcUnitRunner`.

Of the 132: the ten planner tests (suite 30) pass for the **third consecutive run**,
and the six connector tests (suite 31) pass — the wire framing of an ID-addressed
`TPL,from,to`; the link refusing every command rather than queueing it; the status
poll publishing the controller's *reported* facts across real scans; a controller
error carried verbatim into `ControllerMessage`; `Resume` refused while not
resumable; and an `UNKNOWN` mode request refused before the transport. Jog is also
refused in auto — asserted inside the status test, where a linked connector
reporting AUTO actually exists, so the refusal provably comes from the mode gate
and not the link.

## Identity (§8)

| | |
|---|---|
| Repository revision | `a5246ad` (working tree, this commit) |
| Gate | `FraktalCore/PLC/TwinCAT/Tests/Fraktal_Tests.plcproj` |
| Runner | `PRG_TcUnitRunner` |
| Libraries | Fraktal_Core **0.6.0.0**, Fraktal_Modules **0.6.0.0** (installed 2026-08-24, after the `E_RobotJogMode` rename) |
| XAE / XAR | TwinCAT **3.1.4026.24** (ADS 4.3.32, Base v170) |
| Platform | `TwinCAT OS (x64)`, Debug |
| Target | `192.168.1.6.1.1`, ADS port **851** (local UmRT) |
| Autostart Boot Project | **disabled** — asserted by the gate before activation |
| `Fraktal_Tests.plcproj` | `14d37e1fed51a0ac668003d95d6f0e065e95dc554f5071bc1b023a915c451af3` |
| `Fraktal_Tests.tmc` | `29abb3d12b83f06b38216c72ffe443b0d87f53e41aa82f507c289032d2b3373f` |
| Raw log | `2026-08-24_Core_Modules_TcUnit.raw.log` — `e56880505aaa0077c9af4ef035d7a901ff339d29ec9bbcf68341f0f9e09ee787` |
| JUnit | `2026-08-24_Core_Modules_TcUnit.junit.xml` — `afffab1cd1341ecc758cbedeb0fea5174ed25006781ff6df1075315c506f8e68` |

Both artifacts are committed beside this record, so the result is re-checkable
rather than asserted.

## How it was produced

As on 2026-08-23: `Invoke-TwinCatTcUnitGate.ps1 -Interactive` drove compile,
activation and the restart into Run; the operator answered the PLC login prompt in
the visible XAE (guide §6.2 step 6), which downloaded and started the application.
The result was then read with:

```powershell
.\FraktalCore\PLC\TwinCAT\tools\Read-TcUnitResults.ps1 `
  -NetId 192.168.1.6.1.1 -OutputLog artifacts\tcunit\run-2026-08-24.log
```

and validated with `tcunit_to_junit.py` against 132/35.

## What the day's first run corrected

The 13:41 run failed two tests, both test defects (commit `a5246ad`):

- **Status poll test** drove the connector with 30 `Cyclic()` calls inside a single
  scan. The idle poll is TON-driven and a TON advances on elapsed time between
  scans, not on call count — so the poll never fired and every published fact was
  still zero. The connector was correct; the test could not observe it. It now runs
  across scans and finishes when `Referenced` turns TRUE, which only happens once a
  status reply has actually been parsed.
- **Jog test** asserted a precondition owned by the *other* test (that the
  controller was reporting AUTO), so one root cause failed two tests. The jog
  assertion moved to where a linked connector reporting AUTO exists, and the slot
  became a self-contained UNKNOWN-mode refusal.

Between the 13:41 and 15:45 runs the only change was to the test file. That is the
whole point of recording it: a red suite whose failures say nothing about the code
under test is a harness bug wearing a product bug's clothes.
