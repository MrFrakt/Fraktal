# TC3 maintenance handover acceptance — 2026-11-10

Base main: `4af593db73a6bdd1ebfbf94eea7a9a27cabe9634`. Executes
[`TC3_HANDOVER_PROMPT_2026-11-11.md`](../Reports/TC3_HANDOVER_PROMPT_2026-11-11.md).
Core **0.26.8.0**, Modules **0.18.0.0**. The release, native regression fixes,
force-status proposal and output/forcing parity review are described in
[the review](../Reports/TC3_MAINTENANCE_HANDOVER_REVIEW_2026-11-10.md) and
IMPLEMENTATION_NOTES §176. Files and source inputs are bound by
[the SHA-256 receipt](2026-11-10_TC3_MaintenanceHandover.json).

## Final measured results

| Gate | Result |
|---|---|
| PLC lint | modern + 4024: 469 files clean each |
| TwinCAT tools | 79 tests OK, one skipped |
| Strict consistency / its tests | 0 errors / 0 warnings; 36 tests OK |
| Generated reason catalog | --check clean, 97 entries; Dart 3.12.2, no package resolution |
| Library installation | Core 0.26.8.0 then Modules 0.18.0.0, x32 XAE Shell / TwinCAT RT x86; Modules reinstalled after repairs |
| CheckAllObjects | all six solutions TRUE, 0 compiler errors / 0 warnings each, VS18 / TwinCAT OS x64 |
| Core/Modules TcUnit | PRG_TcUnitRunner: 353 / 353 in 54 suites, zero failures |
| Press TcUnit | PRG_PressTestRunner: 9 / 9 in 2 suites, zero failures |

Both runtime logs were independently accepted by `tcunit_to_junit.py` with
the exact runner and inventory counts. Target: isolated **UmRT_Default
192.168.1.6.1.1:851**, runtime binary product 3.1.4026.24, autostart disabled,
ADS boot-project start. The trial ExpireTime read before runtime work was
2026-11-12T00:00:00. The gate left PressTests stopped in Run mode.

An isolated checkout held byte-equal copies of 503 tracked PLC source, project,
solution and configuration files before the final checks. Each selected manifest
defines compiler scope. XAE's project/TMC rewrites stayed there. The generated
TMCs for both final runtime gates are archived. The x32 library exports and
their hashes remain in the local task artifact directory. Detailed compiler
logs retain the benign IDE message `Unknown TMC file version found - ignoring
the file and waiting for a new one.` where it occurred; the compiler transcript
itself is warning-free.

## Failed attempts retained

1. The first invocation rejected an absolute artifact directory before target
   access. The corrected call used a relative directory; the invocation log is
   retained.
2. The first actual aggregate loaded and reached Run, then raised Windows/PLC
   exception **0xc00000fd (stack overflow)**. The safety-alias test had two large
   function blocks as method locals: 39,712 and 4,288 bytes in the generated TMC.
   They were moved to suite instance storage; cyclic status is sampled after
   `Cyclic`. No task-stack increase or relaxed assertion was used. The missing
   summary is explicitly rejected by the validator even though the gate wrapper
   exited zero.
3. The next run completed **351 successful / 2 failed**. Withdrawal erased the
   cylinder pulse selection, and an empty simulation marker admitted the real
   connector fixture. The withdrawal latch is kept and its extra pulse reset is
   removed; the simulation interface now declares a read-only identity property.
   Both existing failing rows and the positive/negative interface checks remain.
   Modules was reinstalled and the six compiler checks and both runtime gates
   rerun. Every raw log, validator result and intermediate source snapshot is
   preserved in the receipt.

4. The last solution in the final compiler pass encountered XAE COM startup
   error **0x80080005 (CO_E_SERVER_EXEC_FAILURE)** before opening PressTests.
   The five preceding solutions had compiled cleanly. No XAE process remained;
   a fresh isolated PressTests invocation completed its own clean check. The
   failed wrapper transcript and retry transcript are both retained.

5. A further aggregate reached **352 / 353**. The remaining robot row also
   enables a deliberate simulation override in its second scenario. Its fixture
   now explicitly starts and ends with that override disabled through the normal
   API and asserts permission is removed on withdrawal. The no-alias assertion
   and both interface-query assertions remain. The failed run and validator
   rejection are retained, followed by the final clean run.

## Boundaries

No other controller was activated. No physical output, real robot or NC motion
acceptance, and no live engineering force experiment was performed. The AB/TIA
trees and HMI lockfile are unchanged. HMI analysis/full tests were not repeated
because the handover changes no HMI behavior; its requested generated-catalog
check passed. The controller-force detector is a concrete proposal awaiting the
owner decision required by task 5, not an implemented alarm source. A read-only
ADS probe read both documented native force flags as FALSE on this runtime;
no active-force scenario was introduced. Release
changes remain uncommitted and unpushed as requested by the handover.
