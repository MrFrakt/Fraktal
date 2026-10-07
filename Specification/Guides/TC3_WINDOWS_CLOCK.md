# TC3 Windows clock quality

This guide describes the Windows Time integration added in Core 0.23.1.0, as
corrected in Core 0.24.0.0 (IMPLEMENTATION_NOTES §162), and its use in the Press demo.
Core §2.7 remains the authority: a working wall clock does not prove synchronization.
The selected source for this bench is the target's existing Windows NTP/domain time service.

## What is implemented

`F_Now()` continues to read the target operating-system UTC clock. The new
`FraktalWindowsClock.exe` observes that same host's Windows Time service through
the documented, authenticated, local MS-W32T RPC status query. It never sets time,
changes peers, or starts Windows Time. Microsoft documents the structured
[status query](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-w32t/7e80a465-f5f4-4c3c-87ef-12f76e45f8d1)
and [status fields](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-w32t/f60ebce0-df96-4c96-b40b-fdbd34a2c936).

The observer writes an atomic, CRC-protected, versioned 76-byte sample every
30 seconds. `FB_TcWindowsTime` reads it through existing `Tc2_System` file APIs;
no TCP/IP PLC library or additional function license is introduced. The default
path is owned by `PL_Fraktal.WINDOWS_CLOCK_SAMPLE_FILE`; the native package's
`clock.defaults.json` is generated from that constant.

The owning `FB_TcSystemHealthProbe` handles reading and expiry after one setup
call to `M_UseWindowsTime`. Quality feeds `GVL_FraktalTime.Current` and the root's
existing `SystemHealth.TimeQuality`; the HMI contract and released structure
layouts are unchanged. Other projects may retain the explicit quality inputs,
or configure this provider once. Do not run competing station clock providers.

The Press demo enables this provider only for its real profile. Simulation
remains explicitly synthetic. Its task period and overrun indication now come
from the current `_TaskInfo` entry rather than assuming a 1 ms task. This removes
the false 9 ms jitter produced by the bench's 10 ms task configuration.

## Build and install

Build the native packages with the Visual Studio C++ toolchain, CMake and a
Windows SDK containing MIDL:

```powershell
& .\FraktalCore\PLC\TwinCAT\tools\Invoke-TcWindowsClockBuild.ps1
```

Packages are under `FraktalCore/PLC/TwinCAT/Framework/Release/clock/windows-x86`
and `windows-x64`. Select the **target Windows architecture**, independently of
whether XAE itself is 32-bit. Copy that package directory to the target. In an
elevated PowerShell on that target:

```powershell
& .\Install-TcWindowsClock.ps1 -PackageDirectory $PWD.Path
```

The current packages were built with MSVC 19.51 and require **Windows 10 or
later**. The Press target NEXEED-O650RLB3 (`5.132.128.188.1.1`) runs Windows 10
Embedded (owner statement, 2026-10-06), so these packages apply; install the package
whose architecture matches that Windows installation (32-bit Windows runs the x86
package, 64-bit Windows the x64 one) and let the installer's own checks refuse a
mismatch. Microsoft's [target platform table](https://learn.microsoft.com/en-us/cpp/overview/supported-platforms-visual-cpp)
states that VS 2026 no longer targets Windows 7/Embedded Standard 7. The package
records its compiler and minimum OS; installation checks it before changing
anything. Older Windows targets need a compatible earlier toolchain and their
own native/runtime acceptance, irrespective of the PLC architecture.

This explicit installation creates a dedicated protected directory and the
`Fraktal Windows Clock Observer` SYSTEM startup task, and starts the observer.
Ordinary users receive read access; SYSTEM and administrators can write. A
custom `-SampleFile` must be a local drive path, fit `STRING(255)`, and match the
path passed to `M_UseWindowsTime` in the PLC. Installation refuses a directory
containing unrelated files. Updating an already running observer requires
stopping its scheduled task before replacing its executable.

Install Core before Modules with `Invoke-TwinCatLibraryInstall.ps1`, then build
the consumer with the pinned Core 0.25.0.0 / Modules 0.11.0.3 references. The
Modules revision changes only its Core dependency. Actual machine download and
physical commissioning follow the existing XAE/first-project workflow.

## Quality and acceptance

The Press settings read every 10 seconds, expire observations after 90 seconds,
and require a successful sync within 7,200 seconds. The existing configured
maximum offset is also enforced; the bench default is 1,000 microseconds. This
is the measured Windows service phase offset, not a PTP-grade bound on absolute
timestamp accuracy. Commission the upstream service and tolerance for the station.

The decoder rejects wrong schema/size/magic, bad CRC, invalid flags, malformed
source termination, reserved bytes, stale/future observations and clock
regression. A monotonic freshness check also expires an unchanged sample.
Synchronization additionally requires an available service, a non-local valid
reference, a successful recent synchronization, and an offset within tolerance.
Unavailable or unsynchronized quality follows the existing `TIME_SYNC_LOST`
alarm path; the implementation never substitutes a healthy value. The offset, last
sync and observation time are those of the last **accepted** record: a rejected or
stale record never publishes its bytes as a measurement.

`FB_TcWindowsTime.ErrorID` says why quality is unavailable: the observer's own service
error (1062: Windows Time not running), 1460 (a record that stopped changing, or is
older than the sample age), 13 (a record that does not validate), or the file-service
error when the record cannot be read at all (1804: no observer record at that path -
the observer is not installed or writes elsewhere). 1398 means the record is fresh
and readable but the PLC's own clock - the TwinCAT system time behind `F_Now()` that
stamps every event - is more than the sample age behind the OS clock that stamped the
record: the station is then unsynchronized even if Windows Time is. On the usermode
test runtime TwinCAT time fell 475 s behind Windows within about 2.4 hours, so on a
target compare an event timestamp with the OS clock during commissioning.

Check `w32tm /query /status /verbose` on the target, then verify the PLC's
`SystemHealth.TimeQuality` and `GVL_FraktalTime.Current`. A `Local CMOS Clock`
source correctly remains unsynchronized. Stop the observer and verify expiry;
restart it and verify recovery without a PLC reset. Stop Windows Time in an
isolated commissioning test and verify unavailable quality. Confirm timestamps
carry the same synchronized flag. This change does not configure NTP/PTP/DC,
fix unrelated CPU/IPC telemetry, or implement an Allen-Bradley clock adapter.

The dated [validation record](../Evidence/2026-10-06_TC3_WindowsClock.md)
distinguishes compiled behavior, decoder tests, native observer reads and
target-side commissioning. The PLC file-reader path was then accepted on the isolated
test runtime with the real observer (1062, expiry to 1460, corruption 13, recovery
without reset, missing 1804) - see the
[2026-10-06 acceptance record](../Evidence/2026-10-06_TC3_MissingFeatures.md). That
host's Windows Time was stopped throughout; an observer task on the Press target and
an upstream time source remain target commissioning.
Final installer/package hashes are in the
[packaging receipt](../Evidence/2026-10-06_TC3_WindowsClock_Packaging.json).
