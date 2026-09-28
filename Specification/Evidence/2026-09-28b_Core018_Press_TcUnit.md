# Core/Modules and Press TcUnit evidence — 2026-09-28 (second run, Core 0.18.0.0)

**Both runtime gates green on Core 0.18.0.0 / Modules 0.10.0.0.** This covers the
day's later work: the line taken out of the Unit tree (IMPLEMENTATION_NOTES §145), the
principles sweep P2–P14 (§146), the robot connector on the connector base (§147), and
one published diagnostic per module (§148). **The first two Press attempts crashed
the runtime**; the cause was a defect in a test, recorded below.

## Result

| Gate | Runner | Suites | Tests | Passed | Failed |
|---|---|---:|---:|---:|---:|
| Core/Modules | `PRG_TcUnitRunner` | 42 | 189 | 189 | 0 |
| Internal Press integration | `PRG_PressTestRunner` | 2 | 9 | 9 | 0 |

`tcunit_to_junit.py` verdicts, each against its expected runner and counts:
`FraktalTests: PASS: 189/189 tests across 42 suites` and
`PressTests: PASS: 9/9 tests across 2 suites`.

## Identity (workflow §8)

| | |
|---|---|
| Repository revision | `ff148d1` plus the Press test fix committed with this record |
| Libraries | Fraktal_Core **0.18.0.0**, Fraktal_Modules **0.10.0.0** (installed 2026-09-28) |
| XAE / XAR | TwinCAT **3.1.4026.24** |
| Platform | `TwinCAT OS (x64)`, Debug |
| Target | `192.168.1.6.1.1`, ADS port **851** (local UmRT) |
| Autostart Boot Project | **disabled** — asserted by the gate before activation |
| `Fraktal_Tests.plcproj` | `db81fcb5de35616a16764580d35fc31b292403feaba07eb1d9600c1b57b11429` |
| `Fraktal_Tests.tmc` | `3cab0a6ee228fc4caa5724d1cefd97ab8ec2f2be9dff4f7129c70237ddb5aaa7` |
| `PressTests.plcproj` | `0c9217634868641aafb0f1047048177cfe645decbfc901ec19641f049e200792` |
| `PressTests.tmc` | `a7136f05f6968f2025e03d1a730fb1e93e62b0ae2ed28c7383bd24d670916502` |
| Core raw log | `2026-09-28b_Core_Modules_TcUnit.raw.log` — `532f296b547b250589bf438ee4238734cbca672b478f0d7ec056049588ff108a` |
| Core JUnit | `2026-09-28b_Core_Modules_TcUnit.junit.xml` — `fa55f5c9494f082b15d8c644811f91430e9223abeb3ddf982ae93c0cd8ee1f0d` |
| Press raw log | `2026-09-28b_Press_TcUnit.raw.log` — `c0b2b80a6acb7b88305d60237e7263ec438f5859eb2ef720422de2811624ac62` |
| Press JUnit | `2026-09-28b_Press_TcUnit.junit.xml` — `8171e6d4733cf3b4a9c6bdb6f84aa7cf3025b846ca4519603c1adfb8e8fbc6ab` |

## How it was produced

`tools/Invoke-TwinCatTcUnitGate.ps1 -Interactive`, one gate at a time, with the owner at
XAE answering the activation and download prompts; results were read over ADS and
converted with `tcunit_to_junit.py`.

## The two crashed Press attempts

Both attempts downloaded and started, then the application stopped on its first cycle:
`Exception 0xc0000005 (Page Fault) in PLC Application PressTests Instance`, at the
same code offset `0x7f624` both times. The runtime wrote a core dump for each
(`Boot/Plc/CoreDump/Port_851.*`). TcUnit's in-memory log inside the dump named the failing
test, `Latched_fault_recovers_with_one_operator_reset`, whose first assertion ("a refused
power enable during motion is a real fault") had failed.

- **The test's fault vehicle did not fault.** When air loss became a hold (P8), the
  test switched to requesting Control On with the safety permit withdrawn. That
  never made the Unit adopt a fault while BUSY, so no event was raised.
- **The test then crashed the runtime.** It read
  `AlarmLog.Ring[AlarmLog.RingHead]` with nothing closed yet: index 0 of a `[1..N]`
  array, a page fault with bounds checking off, and every later test died with it.

The fix is in the test only. The vehicle is now a contradictory door position (both end
sensors TRUE) at N180, a step that awaits the door. The Unit therefore adopts the
`CYL_BOTH_SENSORS` defect through the rollup and freezes with `Door.Execute` asserted,
which is the original hard-lock scenario. The ring read is guarded, so a failing
assertion can no longer take the runtime down. No press or framework code changed.
