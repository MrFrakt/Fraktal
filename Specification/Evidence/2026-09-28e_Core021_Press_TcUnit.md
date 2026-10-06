# Core/Modules and Press TcUnit evidence — 2026-09-28 (fifth run, Core 0.21.0.0)

**Both runtime gates green on Core 0.21.0.0 / Modules 0.10.0.0.** This covers another
model's data served as one page (IMPLEMENTATION_NOTES §151), found on the live press:
`Another_model_page_holds_only_its_model_data` (which replaces
`Station_values_do_not_follow_the_model`) passed. Both gates passed on the first attempt.

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
| Repository revision | `73a2158` (PLC source as of `27b8d1e`) |
| Libraries | Fraktal_Core **0.21.0.0**, Fraktal_Modules **0.10.0.0** (installed 2026-09-28) |
| XAE / XAR | TwinCAT **3.1.4026.24** |
| Platform | `TwinCAT OS (x64)`, Debug |
| Target | `192.168.1.6.1.1`, ADS port **851** (local UmRT) |
| Autostart Boot Project | **disabled** — asserted by the gate before activation |
| `Fraktal_Tests.plcproj` | `fe8c42e4e99ce2705896624f378d41295a2bb6ccacfc95d38525634758fc56bf` |
| `Fraktal_Tests.tmc` | `577f11166aa2aca1f9b7a47a21df5b5e08e27c5317702525502a3d137f6da335` |
| `PressTests.plcproj` | `208237b6f25eb8b0490e59827d82a87d07a3db2f3c753d47e7a9e506afefe0ff` |
| `PressTests.tmc` | `f32a5150c9607795ae3e0f3d76d1c63557a34815c9e8a68f51566148912b568e` |
| Core raw log | `2026-09-28e_Core_Modules_TcUnit.raw.log` — `d6cf59d4c4ad41e6259ee7950f0707811a8d42df9fbdd9b07f8d7a2a864b3d2d` |
| Core JUnit | `2026-09-28e_Core_Modules_TcUnit.junit.xml` — `c05108d5c08796c9dd238b2da12961b38a2785f31a3db1c2e6609a82b59b4866` |
| Press raw log | `2026-09-28e_Press_TcUnit.raw.log` — `6f9a7bf0cc1056106612b1a69336c6962e61ceebab07ef12668c921a2e4befd5` |
| Press JUnit | `2026-09-28e_Press_TcUnit.junit.xml` — `1983ac23b0c2c8ff8c70cd69d51506a87feaf3eab769da41f40942d4435910ee` |

## How it was produced

`tools/Invoke-TwinCatTcUnitGate.ps1 -Interactive`, one gate at a time, with the owner at
XAE answering the download prompt; results were read over ADS and converted with
`tcunit_to_junit.py`. The gate restored each `.tsproj` that activation rewrote. The
target was left in Run mode with the application stopped.
