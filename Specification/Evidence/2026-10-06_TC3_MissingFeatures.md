# Core 0.24.0.0 retained users, platform health and clock acceptance — 2026-10-06

Working source on public commit `c66e91ce353c578b439e258f588777ab9f071cc8` plus the
uncommitted work of 2026-10-05/06. Core **0.24.0.0**, Modules **0.11.0.2** (dependency
rebuild only). Every result below is bound by SHA-256 in
[the receipt](2026-10-06_TC3_MissingFeatures.json). Earlier records are unchanged.

## What was implemented

- **Retained local users** (IMPLEMENTATION_NOTES §160): the hidden table is kept as two
  CRC-protected images in the TwinCAT Boot directory, serviced by the root's access
  manager; a lost table is a §3.8b restore loss on `<root>.Access`, a failed write is
  `CONFIG_PERSIST_FAILED` until a retry succeeds.
- **Controller/IPC metrics and EtherCAT master health** (§161): Tc3_IPCDiag provider,
  per-metric fan/storage availability, always-on master device state, frame and CRC
  windows, DC from the device state, live master health in `M_BusOk`; enabled in the
  Press real profile.
- **Clock reader corrections** (§162): file errors reported, accepted-only measurements,
  freshness by record change, PLC/OS clock disagreement reported as unsynchronized.
- **Unattended runtime gate**: `Invoke-TwinCatTcUnitGate.ps1 -StartBootProjectWithAds`.
- **HMI**: two localized messages (`std.error.accessRestoreLost`, `std.error.accessPersistFailed`).

## Passed on the final source

- Both PLC lint profiles (415 files), 79 TC3 tool tests (one skip), strict consistency
  and its 33 tests.
- Core then Modules installed through **TcXaeShell.DTE.15.0** in 32-bit PowerShell;
  installed blobs equal both refreshed exports (`Framework/Release`, `Release/x32`).
  The installed Modules library references `Fraktal_Core, 0.24.0.0`.
- Six `CheckAllObjects` solutions: `TRUE`, 0 errors, 0 warnings.
- Full offline Press builds in the x32 IDE for **TwinCAT RT (x86) and (x64)**:
  `BuildLastBuildInfo=0`, `0 errors, 0 warnings`. The two `hide`/persistence warnings of
  the previous builds are gone. Memory area 0 highest used: 3,327,776 B (x86) and
  3,417,224 B (x64), against 3,086,280 / 3,161,400 B in the clock build.
- On the isolated **UmRT_Default 192.168.1.6.1.1:851** (XAE/XAR 3.1.4026.24, TwinCAT OS
  x64, Autostart off), started through the new ADS route and read back over ADS:
  aggregate **227/227 in 47 suites** (`PRG_TcUnitRunner`), Press **9/9 in 2 suites**
  for each of **LD, ST and SFC** (`PRG_PressTestRunner`); all validated by
  `tcunit_to_junit.py`. The runtime's boot application equalled the compiled aggregate
  (`39d7b8b6…`).
- The 216-test aggregate of the clock change ran for the first time before any change
  here: **216/216 in 45 suites**.
- HMI with Flutter 3.47.5 in the isolated checkout and canonical lock: analyzer clean,
  **552 passed, 7 live-only skipped**; both new strings are in the Web (`main.dart.js`)
  and desktop (`app.so`) packages; rendered in English and Spanish in the event banner.
  Installer rebuilt (`FraktalSetup.exe`, 51,245,056 bytes, SHA-256 `9e35e6cc…`); not
  executed. The user's local `pubspec.lock` is byte-for-byte unchanged.

## Failed attempts, retained

- Aggregate 226/227 twice, both test staging, both corrected in the fixture: an
  obstruction directory `FB_CreateDir` refused under `PATH_BOOTPATH` (0x70C: exists or
  invalid), and a delete that met the clock reader's open handle (no delete sharing).
- One Press ST run aborted on a transient ADS 0x4 (router mailbox) while the boot
  application loaded; no result was read and nothing was left running. The gate's poll
  now retries until its deadline and marks the start before the request; ST then passed.
- Passing runs on intermediate sources (before the clock fixes) are kept as such.

## Live acceptance on the isolated runtime

Recorded in `…_LiveAcceptance.log`, through the test-only `PRG_PlatformAcceptance`
harness, whose provider keeps its default instance-path storage:

- **Users**: register, login, wrong-PIN refusal, logout and secret clearing through the
  root; images decoded on the host (schema, size, generation, CRC, no PIN in clear); the
  table, transfer buffers and salt sequence absent from the ADS symbol table. Retained
  across a **runtime restart** (volatile counter reset, ~22 s of task cycles, boot data
  loaded) and across **re-activation (download)** after three other test projects.
  Both images corrupted → loss on `Acceptance.Access` (2040, `std.error.accessRestoreLost`),
  old users refused, empty baseline rewritten, next restart silent after re-registration.
  Both images deleted → loss detected by the persistent marker alone. A directory in place
  of the next slot → `durable=0`, `storageError=0x70C`, `CONFIG_PERSIST_FAILED` open, user
  live; removed → retried within 10 s, durable, alarm cleared, retained over a restart.
- **Clock** with the native x64 observer looping: 1062 (Windows Time stopped, as `w32tm`
  reports), 1460 after 90 s without a record, 13 for a corrupted record, recovery without
  a PLC reset, 1804 for a missing record. Hours later the harness read 1460 while the
  observer still wrote: TwinCAT time (`F_Now`, measured on an audited login stamp) was
  **475 s behind** Windows UTC, so fresh records looked future-dated; the corrected
  reader accepts them (1062 again on the final build) and reports such a lag as
  unsynchronized (1398, TcUnit-covered).
- **IPC diagnostics**: not registered, `0xECA8070C` — no Beckhoff Device Manager on this
  PC; every metric unavailable, as intended. **EtherCAT master**: derived
  `192.168.1.6.2.1`, ADS 0x7 — no master on this runtime; unavailable.

## Not executed or not proven here

- Windows Time **running** on the test host: the owner agreed to start it but it stayed
  stopped; the running-service PLC read is not executed today.
- Uncontrolled power loss; the Press target NEXEED-O650RLB3 (`5.132.128.188.1.1`, Windows
  10 Embedded, unreachable over ADS today); observer installation there; positive IPC
  metrics and limits; real EtherCAT counters, DC and their loss/recovery; the
  TwinCAT-versus-Windows clock comparison on that target.
- TCP transport, EL6001 linking, PartFeed axis and external adapters: out of scope by
  owner decision.
- No machine controller was downloaded, activated or started. The test runtime is left
  on `FraktalTests` with the PLC stopped and Autostart off; its pre-session Boot folder is
  backed up under `artifacts/tc3-missing-2026-10-06/runtime-before`.
