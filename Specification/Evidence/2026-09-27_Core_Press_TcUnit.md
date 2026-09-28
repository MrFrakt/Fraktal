# Core/Modules and Press TcUnit evidence — 2026-09-27

**Both runtime gates green, for the first time since 2026-08-24 (Core/Modules) and
2026-08-02 (Press).** Neither had executed on a runtime in between: the Core/Modules
application stopped on a task-stack overflow before TcUnit reported, and the press
gate had been red since the bench selected its Ladder renditions on 2026-08-12.

## Result

| Gate | Runner | Suites | Tests | Passed | Failed |
|---|---|---:|---:|---:|---:|
| Core/Modules | `PRG_TcUnitRunner` | 39 | 167 | 167 | 0 |
| Internal Press integration | `PRG_PressTestRunner` | 2 | 8 | 8 | 0 |

`tcunit_to_junit.py` verdicts, each against its expected runner and counts:
`CoreModules: PASS: 167/167 tests across 39 suites` and
`PressTests: PASS: 8/8 tests across 2 suites`.

## Identity (workflow §8)

| | |
|---|---|
| Repository revision | `eccabfe` plus the working tree committed with this record |
| Libraries | Fraktal_Core **0.8.0.0**, Fraktal_Modules **0.7.0.0** (installed 2026-09-27) |
| XAE / XAR | TwinCAT **3.1.4026.24** |
| Platform | `TwinCAT OS (x64)`, Debug |
| Target | `192.168.1.6.1.1`, ADS port **851** (local UmRT) |
| Autostart Boot Project | **disabled** — asserted by the gate before activation |
| Press AUTO / release renditions | `LADDER_DIAGRAM` / `LADDER_DIAGRAM` (the bench's selection) |
| `Fraktal_Tests.plcproj` | `9cf0589223a3c1df2b65e613157c3ab248b8a021e7f8dc175ac22589bb72d54f` |
| `Fraktal_Tests.tmc` | `9e0d1118717fb2489905dee766b628c022bdee29ffef814693a6531a7fdfee6d` |
| `PressTests.plcproj` | `0a859dca3b5078d0decab882f60ecd3249efb168eeeb3c8c75d9dcbc8c83a979` |
| `PressTests.tmc` | `03a2b35876bcd1159d5bbe3d638823b005ba6ea1b37260d2520e973a91b53619` |
| Core raw log | `2026-09-27_Core_Modules_TcUnit.raw.log` — `0e0105081e00e338e50a832e23df5995a3e2d5da881216f01fc69ac08627e494` |
| Core JUnit | `2026-09-27_Core_Modules_TcUnit.junit.xml` — `54517d1ed9e188ad4e5f16e64e28b0b21d4a58a94fc53fc5cff8749c9bafb978` |
| Press raw log | `2026-09-27_Press_TcUnit.raw.log` — `00edc4bd16964e27c9539719b5949bac52db21f74c3553bbea8f9a9437d5933f` |
| Press JUnit | `2026-09-27_Press_TcUnit.junit.xml` — `2ae28dd9a4a6fe2fe9a4c5852fd3c0f0fb1369e0ed6ff878441b4563dadb2ab7` |

## How it was produced

`Invoke-TwinCatTcUnitGate.ps1 -Interactive -TargetNetId 192.168.1.6.1.1` drove the
object check, activation and restart into Run for each gate; the operator answered
the PLC login prompt in the visible XAE (guide §6.2 step 6). The results were read
with `Read-TcUnitResults.ps1` from the stopped PLC and validated with
`tcunit_to_junit.py`.

**The gate's own harvest reported `0 tests / 0 suites` on several runs today** while
TcUnit's `AllTestSuitesFinished` read TRUE. Re-reading the same stopped PLC with
`Read-TcUnitResults.ps1` returned the full, correct result each time. The harvest
evidently reads before TcUnit's result table is populated; the raw logs recorded
here are the re-reads. That race is owed a fix in the gate.

## What had to change to get here

Recorded in `FraktalCore/PLC/TwinCAT/IMPLEMENTATION_NOTES.md` §135–§137. In short:

- **Stack overflow (§135).** A test method declared a whole Unit as a local:
  332 192 bytes against a 49 152-byte task stack. `CheckAllObjects` does not report
  C0297, so every object-check gate had passed it.
- **Three product defects the Core suite found on its first run (§136):** `CONFIG_SET`
  refused by construction, `BLOCK_UNTIL_ACKNOWLEDGED` blocking nothing, and a faulted
  safety facet still granting jog.
- **Two defects in the Ladder AUTO chain the bench runs (§137):** good parts never
  counted without a traceability carrier, and the ram left down at the end of a cycle
  because two rungs commanding it ran in one scan.
- **Test defects** in each, and a store that kept the previous run's sets; the store
  can now delete a set (Core 0.8.0.0).

Between the red and green press runs the diagnostic step was a controlled experiment:
the same suite with `AUTO_SEQUENCE_LANGUAGE` temporarily set to ST passed 8/8, which
put both remaining failures in the Ladder rendition. That edit was reverted before the
run recorded here; the bench still selects Ladder.
