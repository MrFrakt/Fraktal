# Core/Modules and Press TcUnit evidence — 2026-09-28 (third run, Core 0.19.0.0)

**Both runtime gates green on Core 0.19.0.0 / Modules 0.10.0.0.** This covers model data
editable for every model (IMPLEMENTATION_NOTES §149): the model region and staging view
in the base classes, `I_RecipeStore` on the local provider, and the press's recipe
write-back moved into the library. The new suite `FB_ModelData_Tests` (4 tests) is part
of the Core/Modules count. Both gates passed on the first attempt.

## Result

| Gate | Runner | Suites | Tests | Passed | Failed |
|---|---|---:|---:|---:|---:|
| Core/Modules | `PRG_TcUnitRunner` | 43 | 193 | 193 | 0 |
| Internal Press integration | `PRG_PressTestRunner` | 2 | 9 | 9 | 0 |

`tcunit_to_junit.py` verdicts, each against its expected runner and counts:
`FraktalTests: PASS: 193/193 tests across 43 suites` and
`PressTests: PASS: 9/9 tests across 2 suites`.

## Identity (workflow §8)

| | |
|---|---|
| Repository revision | `fbc9f46` |
| Libraries | Fraktal_Core **0.19.0.0**, Fraktal_Modules **0.10.0.0** (installed 2026-09-28) |
| XAE / XAR | TwinCAT **3.1.4026.24** |
| Platform | `TwinCAT OS (x64)`, Debug |
| Target | `192.168.1.6.1.1`, ADS port **851** (local UmRT) |
| Autostart Boot Project | **disabled** — asserted by the gate before activation |
| `Fraktal_Tests.plcproj` | `35a11e11e6393b870e4def3ad274dc0994630c620f334da9cb0475e91270e616` |
| `Fraktal_Tests.tmc` | `8f9687f28502cda150e03d025326acf5aece5e812dab76a69b06f907684dfef3` |
| `PressTests.plcproj` | `6cc616b9b276812eaeda10f65d41546a482cdd63abb508b1753a285d45597d89` |
| `PressTests.tmc` | `583254191ce9883f4fc7c7565c727fed74a30dcd4eb6780338cbfb9165bb922e` |
| Core raw log | `2026-09-28c_Core_Modules_TcUnit.raw.log` — `109cd9f62cbbfd35545c39a8ab67ec6aa54bae5a9d4ac5f8a7d86b1e51cb8953` |
| Core JUnit | `2026-09-28c_Core_Modules_TcUnit.junit.xml` — `68f68ad6250b8c3a8124b1551bbf341a754fb571d06c6d490b4d85b568ad29ab` |
| Press raw log | `2026-09-28c_Press_TcUnit.raw.log` — `4b420532819c7f230da7223f4d8a0e3964ac115fad74ff6fd2cad9ac73dc8fcc` |
| Press JUnit | `2026-09-28c_Press_TcUnit.junit.xml` — `6eb18d4669c645d9b24a2cd8ca3ac483fa84c396b98a173082d1171132982ed4` |

## How it was produced

`tools/Invoke-TwinCatTcUnitGate.ps1 -Interactive`, one gate at a time, with the owner at
XAE answering the download prompt; results were read over ADS and converted with
`tcunit_to_junit.py`. The gate restored each `.tsproj` that activation rewrote. The
target was left in Run mode with the application stopped.
