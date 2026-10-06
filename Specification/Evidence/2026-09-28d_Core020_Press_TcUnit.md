# Core/Modules and Press TcUnit evidence — 2026-09-28 (fourth run, Core 0.20.0.0)

**Both runtime gates green on Core 0.20.0.0 / Modules 0.10.0.0.** This covers local PINs
kept only as salted hashes (IMPLEMENTATION_NOTES §150): `F_Sha256` checked against the
three FIPS 180-4 example vectors (`FB_Sha256_Tests`, a new suite) and
`Re_registering_replaces_the_PIN` in `FB_Access_Tests`. Every earlier login test now runs
against the hashed table. Both gates passed on the first attempt.

## Result

| Gate | Runner | Suites | Tests | Passed | Failed |
|---|---|---:|---:|---:|---:|
| Core/Modules | `PRG_TcUnitRunner` | 44 | 197 | 197 | 0 |
| Internal Press integration | `PRG_PressTestRunner` | 2 | 9 | 9 | 0 |

`tcunit_to_junit.py` verdicts, each against its expected runner and counts:
`FraktalTests: PASS: 197/197 tests across 44 suites` and
`PressTests: PASS: 9/9 tests across 2 suites`.

## Identity (workflow §8)

| | |
|---|---|
| Repository revision | `7824052` (PLC source as of `b0e2be4`; later commits are HMI and documents) |
| Libraries | Fraktal_Core **0.20.0.0**, Fraktal_Modules **0.10.0.0** (installed 2026-09-28) |
| XAE / XAR | TwinCAT **3.1.4026.24** |
| Platform | `TwinCAT OS (x64)`, Debug |
| Target | `192.168.1.6.1.1`, ADS port **851** (local UmRT) |
| Autostart Boot Project | **disabled** — asserted by the gate before activation |
| `Fraktal_Tests.plcproj` | `ba1f82acbd5d14801c911fd2e4cebd9876bb04f323684b1a4624a4d0673f9f84` |
| `Fraktal_Tests.tmc` | `6e48e5a03d22231b8997279209353c432140a0f6cf9523fca5485dc34e1a1c4b` |
| `PressTests.plcproj` | `ff721c187ecbcbc598be31ceb329f6c96c46451272ce68150f2340b7411cca7a` |
| `PressTests.tmc` | `4929ae3418c1b9bde2ff6fb1c7b5f183ca8457593edaf616ef121a6fd920be8a` |
| Core raw log | `2026-09-28d_Core_Modules_TcUnit.raw.log` — `d3d97911d23914a14913c141792b3c5f5da2548f8d784144e5ff266f05986241` |
| Core JUnit | `2026-09-28d_Core_Modules_TcUnit.junit.xml` — `977fa0ed9e7636839a7164f6de41219ce94c6869be881fec6d786c129dc409d3` |
| Press raw log | `2026-09-28d_Press_TcUnit.raw.log` — `d12a4436a24b7746d9e7dc283ddd9da49b069f6fb8f8433083b064b7422405e8` |
| Press JUnit | `2026-09-28d_Press_TcUnit.junit.xml` — `c17e251ab071844cd235d8c739d351fb8fdcbe5ac9ff593ba32e22ddf4d90bb5` |

## How it was produced

`tools/Invoke-TwinCatTcUnitGate.ps1 -Interactive`, one gate at a time, with the owner at
XAE answering the download prompt; results were read over ADS and converted with
`tcunit_to_junit.py`. The gate restored each `.tsproj` that activation rewrote. The
target was left in Run mode with the application stopped.
