# Core/Modules and Press TcUnit evidence — 2026-09-28

**Both runtime gates green on Core 0.13.0.0.** This closes objectives-audit gap G2
(`Specification/Reports/OBJECTIVES_AUDIT_2026-09-28.md`). Core 0.9–0.11 had passed on
this runtime, but that was recorded only in commit messages, and 0.12 was never run.
This run covers everything up to 0.13. **It found a product defect** that every
compile gate had passed (see below).

## Result

| Gate | Runner | Suites | Tests | Passed | Failed |
|---|---|---:|---:|---:|---:|
| Core/Modules | `PRG_TcUnitRunner` | 42 | 187 | 187 | 0 |
| Internal Press integration | `PRG_PressTestRunner` | 2 | 8 | 8 | 0 |

`tcunit_to_junit.py` verdicts, each against its expected runner and counts:
`FraktalTests: PASS: 187/187 tests across 42 suites` and
`PressTests: PASS: 8/8 tests across 2 suites`.

## Identity (workflow §8)

| | |
|---|---|
| Repository revision | `d1772d5` plus the working tree committed with this record |
| Libraries | Fraktal_Core **0.13.0.0**, Fraktal_Modules **0.7.0.0** (installed 2026-09-28) |
| XAE / XAR | TwinCAT **3.1.4026.24** |
| Platform | `TwinCAT OS (x64)`, Debug |
| Target | `192.168.1.6.1.1`, ADS port **851** (local UmRT) |
| Autostart Boot Project | **disabled** — asserted by the gate before activation |
| `Fraktal_Tests.plcproj` | `d7ccffae341199980ee06abcb91c79b790a409f143e55607af9d1c6dd2343b8a` |
| `Fraktal_Tests.tmc` | `ffab9bf3b9e5a21067f1e1bc20fe38b45cb998849cd21439b7f1a71cf16ca2af` |
| `PressTests.plcproj` | `21912f668f4985e3e5374eba47d35d77f9281ddf6b3ed460a9e7a6380276204f` |
| `PressTests.tmc` | `fc29a2fed688934041edfe0b334ae2eafcfde79ffb32b124272f8a54d9a7a8ce` |
| Core raw log | `2026-09-28_Core_Modules_TcUnit.raw.log` — `3505348d2c1d2f17ad5761f1e24d2901cfabf33f9ecc5f4d7bc6223bb83f5275` |
| Core JUnit | `2026-09-28_Core_Modules_TcUnit.junit.xml` — `23d1a4723720f9d0272568cf44eb6963acc6509e8300056c45e9bf4f4f401fbd` |
| Press raw log | `2026-09-28_Press_TcUnit.raw.log` — `4de6e15affe5306ab24abf74baaeaf1a1a4c1437c5571a7b4730355c413f2a3e` |
| Press JUnit | `2026-09-28_Press_TcUnit.junit.xml` — `dc16fb8f55c8ddd30b226ff63e659e3c89e69d0d29b59cb280b90f1dd3500fd4` |

## How it was produced

`Invoke-TwinCatTcUnitGate.ps1 -Interactive -TargetNetId 192.168.1.6.1.1` ran each gate:

1. the object check;
2. activating the configuration;
3. restarting TwinCAT into Run.

The operator answered the PLC login prompt in the visible XAE. The gate read the
results over ADS, and `tcunit_to_junit.py` validated them. On one intermediate run the
gate stopped waiting for RUN after 30 s although the tests did run (the XAE log showed
them); the recorded runs reached RUN normally.

## What the runtime found

The first run of Core 0.13 failed the new test
`A_line_longer_than_a_request_imports_in_pieces` at its first assertion. A second run
measured the line by scanning bytes instead of calling `LEN`. It reported
**255 bytes for a line that should have been about 330**.

- **`CONCAT` truncates at 255 characters**, even into a `STRING(480)` target.
- **`LEN` reports at most 255.** On the corrected build it returned 255 for a
  290-character line.

So since the set export was written, any record whose line exceeded 255 characters had
been exported truncated, as broken JSON. That contradicts the codec's own stated rule,
"emitted or refused, never truncated". Short records, the only ones the earlier tests
used, were unaffected. Every compile gate had passed the defect, because it is a
runtime value property.

**The fix (IMPLEMENTATION_NOTES §143):**
- `FB_ConfigSetJson` builds lines with a byte-level append that refuses at the 480
  width.
- It finds and measures fields by scanning to the terminator.
- It offers `M_Join` for the piece import, which `FB_UnitBase` now uses instead of
  `CONCAT`/`LEN`.

**The test now proves the fix:**
- the rendered line is longer than 255 bytes by scan;
- it parses back with its value whole;
- two pieces rejoin into the stored record;
- a join past 480 is refused.
