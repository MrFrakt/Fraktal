# Fresh-chat handover prompt — Core and Press TC3

Copy the following prompt into a fresh chat working in `C:\Projects\Fraktal`.
It describes the current working tree; uncommitted work is part of the baseline.

---

Implement the remaining Core/Press TwinCAT features in this repository. Carry
the work through native compilation and meaningful acceptance; use the existing
framework mechanisms and preserve the current application and HMI behavior.

Start by reading `AGENTS.md`, `Specification/README.md`, the relevant clauses of
`Fraktal_Core_Part_I.md` and `Fraktal_TC3_Part_II.md`,
`FraktalCore/PLC/TwinCAT/IMPLEMENTATION_NOTES.md` (especially §§154–159),
`Specification/HMI_CONTRACT.md`, and these current records:

- `Specification/Reports/TC3_CORE_PRESS_FEATURE_AUDIT_2026-10-06.md`
- `Specification/Guides/TC3_WINDOWS_CLOCK.md`
- `Specification/Evidence/2026-10-06_TC3_WindowsClock.md` and its JSON receipt
- `Specification/Evidence/2026-10-06_TC3_WindowsClock_Packaging.md` and JSON
- `Specification/Guides/TWINCAT_XAE_WORKFLOW.md`
- `Specification/Guides/FIRST_PROJECT_AGENT_GUIDE.md` before target commissioning
- `Specification/Reports/HMI_MANUAL_IO_2026-10-06.md`

Inspect the current source and installed dependencies before treating an old
report or TODO as an absent feature. Make a prioritized work list and progress
independently on code while collecting hardware facts needed for commissioning.
Use primary Beckhoff/Microsoft documentation for target APIs; do not invent
function names, ADS indices, PDO names, license requirements or healthy samples.

## Baseline to preserve

Public repository: `https://github.com/MrFrakt/Fraktal`, fresh AGPL main baseline
`c66e91ce353c578b439e258f588777ab9f071cc8`. The working tree contains later
uncommitted PLC, HMI, wrapper and documentation changes. Inspect and preserve
them; do not reset to the public commit. Existing license/history work is done.

Current libraries: **Core 0.23.1.0**, **Modules 0.11.0.1**. Both canonical
`Framework/Release` and `Framework/Release/x32` exports were refreshed; consumers
pin these versions. Modules changed only its Core dependency. Avoid reinstalling
an old export; stale Modules exports previously recreated x32 dependency errors.

The user operates **TcXaeShell.DTE.15.0**, the actual x32 XAE IDE. Run its COM
automation in `C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe`.
Legacy `.sln` wrappers accompany the `.slnx` files. Native offline Press builds
pass for both TwinCAT RT x86 and x64 in that IDE. All six object checks pass.
The only known full-build warnings concern hidden credential persistence.

Clock integration now exists: `FB_TcWindowsTime`, its packed V1 sample and CRC,
`FB_TcSystemHealthProbe.M_UseWindowsTime`, and the target-local Windows observer.
The user selected the **target's existing Windows Time service**. The provider
validates/ages samples and publishes through the existing single time authority;
Press derives its task period from `_TaskInfo` and avoids the former false 9 ms
jitter. Preserve truthful availability and synchronization flags.

The current native observer packages were built with **MSVC 19.51** and require
**Windows 10 or later**. The actual x32 PLC target's Windows version is still
unconfirmed. Ask for it early. Windows 7/Embedded Standard 7 needs a compatible
earlier toolchain and its own acceptance; the installer rejects incompatible
packages before changing the target. No observer task has been deployed. The
development host currently reports **Local CMOS Clock**, so unsynchronized
quality is correct. Do not change NTP/domain policy or manufacture sync to clear
the alarm; coordinate actual upstream commissioning with the user.

The fresh aggregate inventory is **216 tests / 45 suites**, including a new
clock-decoder fixture. It compiled, but has **no fresh runtime pass**: both silent
and interactive Automation Interface Login left `IsLoggedIn=false`, operation
state 0. ADS remained Invalid; new TMC symbol metadata is not proof of execution.
Historical Oct 5 acceptance was 215/215, plus Press 9/9 for ST/SFC/LD. Preserve
those dated records and distinguish them from new results.

The previously approved isolated test target is **192.168.1.6.1.1:851**,
**UmRT_Default**. Its last configuration was `FraktalTests`, containing PLC
`Fraktal_Tests`, with Autostart disabled. Verify this identity and current state
again before any test activation; back up its Boot/configuration. The fresh
test checkout is `artifacts/tc3-clock-2026-10-06/checkout`. Manual PLC Login/Start
may be required; independently read results with `Read-TcUnitResults.ps1`.
No actual machine controller download/activation is authorized by this handover.
Read target facts and prepare reviewable changes before requesting any additional
physical commissioning authorization.

The HMI now has exact-owner Inputs/Outputs on the manual-command card. Like a
Bosch LEDs are circular white arrows: input down/green ON, output up/light red ON,
gray OFF and a distinct unavailable mark. The multicolor strip, event colors and
semantic module icons remain. Signals are read-only; commands still use their
release/hold/access path. Module I/O demand is scoped to the visible card's
channels and bus ancestors and coexists with the full fieldbus view. Preserve
the freshness timer's early-callback re-arming and rounded-up delay; its negative
regression proved that abandoning an early tick can leave a stalled sample LIVE.
The HMI suite now passes **552 tests with seven live-only skips**, and analyzer
and strict consistency are clean. Preserve the original HMI `pubspec.lock`;
it is a pre-existing local SDK change. Verification uses Flutter **3.47.5**
under `artifacts/flutter-3.47.5` and the
canonical lock in the isolated HMI build checkout, `artifacts/like-bosch-theme`.

## Implement in this order

1. **Complete clock acceptance and target integration.** Run the fresh decoder
   fixture, verify native observer status against Windows Time, then test the
   PLC file-reader path, service loss, observer expiry, corrupt samples, recovery,
   sync-age/offset limits and consistent timestamp flags. Use an isolated
   runtime for mutations. Prepare the correct target-OS package and deployment
   procedure; record exactly what was and was not commissioned.
2. **Fix protected local-user persistence.** `FB_LocalAccessProvider`'s hidden
   `_users`/`_n` cannot persist. Provide a protected, validated persistence path
   without exposing credentials/hashes in discovery, manifests or HMI bindings.
   Test restart/power-loss or the appropriate persistence mechanism, download,
   failed/corrupt restore, access changes and logout. Simply removing `hide` to
   silence the compiler warning is insufficient.
3. **Implement real controller/IPC metrics providers.** Press currently ties
   CPU/memory availability to simulation and sets IPC availability false. Wire
   supported APIs for the verified host/runtime; unsupported metrics remain
   explicitly unavailable. Reuse the health probe and publisher, with actual
   limits and loss/recovery evidence. Keep task timing based on the real task.
4. **Wire aggregate fieldbus counters and DC quality.** The default bus health,
   project catalog and topology publisher already exist. Press still supplies
   zero lost-frame/slave-error counts and no real DC availability. Use verified
   master diagnostics and retain bounded on-demand scans and diagnostic joins.
5. **Complete the native TCP byte channel where TCP devices are used.**
   `FB_TcpChannelTc3` is a fail-closed skeleton; device parsers/CMs and simulation
   already exist. Implement bounded async connect/send/receive/close, framing,
   reconnection and errors. Verify pinned `Tc2_TcpIp`/TF6310 prerequisites and
   licensing. Keep optional device dependencies from needlessly breaking the
   standard Press build or introducing unused platform surface.
6. **Finish Press serial and feed-axis hardware binding with real facts.**
   EL6001 raw symbols exist but their `TcLinkTo` PDO links are absent after guessed
   names failed. Read the actual terminal assignment before linking. PartFeed
   is not configured/registered until the NC channel and motion are commissioned;
   verify the current wrappers and physical linkage before enabling it. Verify
   config restore, jog permissions, output withdrawal and relevant licenses.
7. **Handle deployment-specific extensions only where required.** Rich
   `FB_EcFieldbusScanner` discovery is optional; the default catalog/publisher
   path is implemented. Local BY_POSITION carrier and event/history seams are
   implemented. Select real RFID/host/historian/MES endpoints with the user
   before adding those adapters, then prove their failure/acknowledgement paths.

Continue work that does not depend on missing hardware facts. Record precisely
what remains blocked by an unavailable target, PDO assignment or endpoint.
Do not replace unknown hardware facts with simulation or remove release gates.

## Engineering and completion gates

Apply O9/O4: one source per fact, owning framework behavior, additive/versioned
released types and minimum runtime surface. Absorb repeated project wiring into
the framework; preserve schema versions and enum ordinals. Device types extend
the existing bases. Keep the inherited lifecycle and reset/hold semantics.
Generate/dump any changed SFC/LD graph rather than hand-editing its archive.

Preserve `USE_SIMULATION`, commissioning constants, control-domain ownership,
safety boundaries, release guards and the single hardware-driver I/O boundary.
Protect unrelated user wrapper, NC, I/O configuration, HMI and lockfile changes.
No secret-bearing data should appear in logs, OPC UA or generated UI metadata.

For PLC changes, run both lint profiles and the TC3 tool tests. Install Core
before Modules before checking consumers. Run all six object checks and full
Press x86/x64 builds in the actual x32 IDE. Run aggregate and separate Press
TcUnit gates; cover all affected ST/SFC/LD renditions and add meaningful negative
tests for the changed behavior. A successful void Login/Start call or symbol
metadata does not prove a runtime test passed. Preserve failed attempts as well
as passing evidence, with counts, targets, versions and artifact hashes.

Run cross-artifact consistency and its tests. For HMI changes, use the pinned
SDK/build checkout, analyzer, relevant/full widget tests and actual visual QA;
preserve the Bosch strip and circular LEDs. Rebuild the gateway/desktop/Web
installer when shipped HMI behavior changes. Refresh both library export
locations after a library change, and verify hashes/dependencies.

Append dated evidence; never rewrite earlier evidence to match new results.
Update implementation notes, guides and the current audit around the final
behavior. Report completed features, exact validation, remaining target work
and locations of refreshed deliverables. Do not claim production acceptance
from offline compilation or a simulated fixture, and do not push/deploy the
repository without the user's instruction.
