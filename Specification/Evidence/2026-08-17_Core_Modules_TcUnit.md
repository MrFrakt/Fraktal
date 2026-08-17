# Core/Modules TcUnit evidence — 2026-08-17

**The first runtime record produced without a person reading numbers off a
screen.** The tests were started by an operator, but the result was read out of
the PLC over ADS, validated against the expected counts and runner identity, and
emitted as JUnit. Every previous record in this folder was transcribed by hand.

## Result

| Field | Result |
|---|---:|
| Test suites | 31 |
| Tests | 106 |
| Successful tests | 106 |
| Failed tests | 0 |
| Duration | 3.163544e-1 s |

`tcunit_to_junit.py` verdict: `CoreModules: PASS: 106/106 tests across 31 suites`,
exit 0, checked against `--expected-tests 106 --expected-suites 31
--expected-runner PRG_TcUnitRunner`.

## Identity (§8)

| | |
|---|---|
| Repository revision | `ef22dc8` (working tree, this commit) |
| Gate | `FraktalCore/PLC/TwinCAT/Tests/Fraktal_Tests.plcproj` |
| Runner | `PRG_TcUnitRunner` |
| Libraries | Fraktal_Core **0.5.0.0**, Fraktal_Modules **0.4.0.0** |
| XAE / XAR | TwinCAT **3.1.4026.24** |
| Platform | `TwinCAT OS (x64)`, Debug |
| Target | `192.168.1.6.1.1`, ADS port **851** |
| Autostart Boot Project | **disabled** — attribute `false`, no `Port_851.autostart` marker on the runtime |
| `Fraktal_Tests.plcproj` | `77968d502b138e8ea057d68b0af1b18ff022ae6f460bc757a349269940e622c4` |
| `Fraktal_Tests.tmc` | `2a27af35f91af924738181037e8bee49268c8044cd3f11ca0adbab0cf10bf3b0` |
| Raw log | `2026-08-17_Core_Modules_TcUnit.raw.log` — `bbf996c25ae03bd529736976d7a61dfe067c87834ba0e10cc4eb7048ca1a6092` |
| JUnit | `2026-08-17_Core_Modules_TcUnit.junit.xml` — `ccb6c301c9e9e2a6cbcc35d8ff690f7b93608b7c2336e91f46129c348b55f879` |

Both artifacts are committed beside this record, so the result is re-checkable
rather than asserted.

## How it was produced

Activation, download and start were performed by an operator in XAE per
`Guides/TWINCAT_XAE_WORKFLOW.md` §6.2. The automated gate still cannot log in
(§9.1), and that is a recorded decision rather than an open defect.

The result was then read with:

```powershell
.\FraktalCore\PLC\TwinCAT\tools\Read-TcUnitResults.ps1 `
  -NetId 192.168.1.6.1.1 -OutputLog artifacts\tcunit\manual-2026-08-17.log
```

which reads TcUnit's own `ST_TestSuiteResults` over ADS — per-suite and per-test,
including each test's name, class and pass state — waits on the runner's own
completion flag rather than a fixed window, and reads by name through
`ADSIGRP_SYM_VALBYNAME` so it consumes no symbol handles.

## What the first live run corrected

`Read-TcUnitResults.ps1` had never read a running PLC before today. It did not
work first time, and both faults were invisible in source:

- **Wrong symbol root.** It looked for `GVL_TcUnit.AllTestSuitesFinished` and
  `GVL_TcUnit.TestResults`. Those members belong to `FB_TcUnitRunner`, not to the
  GVL: the real paths are under **`GVL_TcUnit.TcUnitRunner`**. A live symbol
  upload settled it — `GVL_TcUnit` publishes exactly 14 symbols and neither name
  is among them.
- **The diagnostic that should have revealed this was itself broken.**
  `TcAdsSymbolInfo` exposes both `Datatype` and `DataType`; PowerShell refuses to
  bind either ("differs only in letter casing … must be CLS compliant") and the
  exception aborted the whole enumeration. Finding the correct names required
  bypassing the .NET wrapper and parsing the raw symbol upload
  (`ADSIGRP_SYM_UPLOADINFO` `0xF00F` then `ADSIGRP_SYM_UPLOAD` `0xF00B`).

Recorded because it is the same shape as the defect this folder's 2026-08-15
record carries a correction for: **a tool that has never met a live system is an
assumption, not a capability.**

## Limits

Executed on the **local development usermode runtime**, not the isolated VM the
committed wrappers name (`192.168.132.128.1.1`, currently unreachable) and not a
machine. This is not a machine-acceptance result, and standing up an isolated
runtime is a deferred decision.

The tests were started by a person. Under Core §5.7 a type is done when its rows
are green **in CI**; this is a green run, and it is not that.
