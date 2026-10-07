# Windows clock adapter acceptance scope — 2026-10-06

Working source based on public commit `c66e91ce353c578b439e258f588777ab9f071cc8`.
Core **0.23.1.0**, Modules **0.11.0.1**. Modules changes only its Core dependency.
See the [receipt and SHA-256 bindings](2026-10-06_TC3_WindowsClock.json).

## Passed

- Both PLC lint profiles: 405 files clean.
- TC3 tooling: 79 tests, one skip; consistency tooling: 33 tests.
- Strict cross-artifact consistency: zero errors and zero warnings.
- Final Core installed before Modules through the actual x32 XAE IDE.
- Final `CheckAllObjects`: all six solutions passed, including both libraries,
  Core/Press applications and their two separate test applications.
- Full offline Press code generation through **TcXaeShell.DTE.15.0**, 32-bit
  PowerShell, for both **TwinCAT RT x86 and x64**: `BuildLastBuildInfo=0`.
  The two existing hidden local-credential persistence warnings remain.
- Native observers built for x86 and x64 with MSVC 19.51, static CRT; PE machine
  fields independently verified. These packages require Windows 10 or later.
- Both final observer binaries successfully queried the host's existing
  Windows Time service. They reported `available=1`, `synchronized=0`,
  `offsetUs=0`, `lastSync=0`, `serviceError=0`. `w32tm` independently reported
  leap 3, stratum 0, Local CMOS Clock and no successful synchronization.
- Both real 76-byte samples independently decoded with Python; schema, size,
  magic, reserved bytes, source termination and CRC32 verified. Archive entries
  were verified byte-for-byte against packaged executables/defaults/installer.
- PowerShell installer/build script syntax parsed successfully. No observer
  startup task, directory ACL or Windows time setting was deployed by this run.

## Fresh TcUnit runtime gate remains pending

The expected current aggregate inventory is **216 tests / 45 suites**. This
count is source inventory, not a fresh passing runtime result. The new fixture
checks valid signed offset, stale observation, excess offset, stopped service,
corruption and wall-clock regression. It compiled with the final library.

Only the previously user-approved isolated **UmRT_Default**,
**192.168.1.6.1.1:851**, was used. Its pre-existing Press test ownership was
verified and its Boot folder copied to the task artifact directory before
activation. The fresh aggregate configuration compiled and activated with
Autostart disabled. Both silent and interactive Automation Interface login
attempts failed to finish: `IsLoggedIn=false`, operation state 0. ADS remained
Invalid; the TMC exposed new clock symbol metadata, but an actual value read
failed with ADS 0x710. This proves no fresh test execution. Raw failed-login
diagnostics are retained with this record.

The fresh aggregate solution is open for manual PLC Login/Start, with the
isolated target explicitly verified and Autostart disabled. After it starts,
`Read-TcUnitResults.ps1` can provide independent per-test acceptance. No older
215-test pass is relabeled as a 216-test pass. No Press integration rerun is
claimed for this change.

## Delivery and limits

Both `Framework/Release` and `Framework/Release/x32` exports were refreshed and
match the final library hashes. Native ZIP packages and unpacked installer
directories are under `Framework/Release/clock`. The installer is prepared;
it has not been executed on any PLC target. Installation includes a minimum-OS
check before any changes. The actual machine controller was not downloaded,
activated or started.

Positive upstream synchronization, target-side scheduled-task operation, PLC
file-reader/expiry/recovery commissioning, Windows 7 support and physical
machine acceptance remain separate from this measured scope. The actual host
is currently unsynchronized; a zero phase offset does not change that verdict.
The decoder and quality propagation preserve the existing alarm contract.

Procedure: [TC3 Windows clock guide](../Guides/TC3_WINDOWS_CLOCK.md).
Remaining gaps: [Core/Press feature audit](../Reports/TC3_CORE_PRESS_FEATURE_AUDIT_2026-10-06.md).
