# Core 0.25.0.0 retained data on a project-chosen medium — 2026-10-06

Working source on public commit `c66e91ce353c578b439e258f588777ab9f071cc8` plus the
uncommitted work of 2026-10-05/06. Core **0.25.0.0**, Modules **0.11.0.3** (dependency
rebuild only). Every result below is bound by SHA-256 in
[the receipt](2026-10-06_TC3_PersistMedium.json). Earlier records are unchanged.

## What was implemented

- **A persistence medium chosen per project** (IMPLEMENTATION_NOTES §163):
  `I_PersistMedium`, a file medium (`FB_FilePersistMedium`: two copies per key, readable
  80-byte header, persistent confirmed generations) and a retentive-memory medium
  (`FB_RetainPersistMedium`). A database medium is the same interface and waits for a
  named server and licence.
- **The root's live configuration on it**: `SetPersistMedium` keeps the station data,
  the owned line data and every model's data as JSON-lines documents, restored at start
  through the staged set path and rewritten after every accepted write.
- **Parameter sets on it** (`FB_MediumConfigStore`) and **the local user table on it**
  (`FB_LocalAccessProvider.M_UseMedium`, confidential media only).
- **Press demo**: one `FB_FilePersistMedium` on `C:\ProgramData\Fraktal\PressDemo\`
  for all four.
- `FB_ConfigSetJson` now parses `LINE_CFG` sets; HMI: two messages
  (`std.release.configRestoring`, `std.error.storageUnreadable`).

## Passed on the final source

- Both PLC lint profiles (426 files; `FROM` added to the reserved words after the
  compiler rejected it), 79 TC3 tool tests (one skip), strict consistency and its 33
  tests.
- Core then Modules installed through **TcXaeShell.DTE.15.0** in 32-bit PowerShell;
  installed blobs equal both refreshed exports. XAE reported "Closing project failed!
  ... Index was outside the bounds of the array." after saving Core; the dialog was
  dismissed, the IDE restarted and the Modules install completed.
- Six `CheckAllObjects` solutions: `TRUE`, 0 errors, 0 warnings; the test project again
  with the final acceptance harness: 0 errors, 0 warnings.
- Full offline Press builds for **TwinCAT RT (x86) and (x64)**: `BuildLastBuildInfo=0`,
  0 errors, 0 warnings. Memory area 0 highest used: 3,394,008 B (x86) and 3,487,000 B
  (x64), against 3,327,776 / 3,417,224 B for Core 0.24.0.0.
- On the isolated **UmRT_Default 192.168.1.6.1.1:851** (XAE/XAR 3.1.4026.24, Autostart
  off): aggregate **235/235 in 49 suites** (`PRG_TcUnitRunner`), Press **9/9 in 2
  suites** for each of **LD, ST and SFC**; all validated by `tcunit_to_junit.py`.
- HMI with Flutter 3.47.5 in the isolated checkout and canonical lock: analyzer clean,
  **552 passed, 7 live-only skipped**; both new strings are in the Web (`main.dart.js`)
  and desktop (`app.so`) packages. Installer rebuilt (`FraktalSetup.exe`, 51,245,056
  bytes, SHA-256 `48f1a21b…`); not executed. The user's local `pubspec.lock` is
  byte-for-byte unchanged.

## Failed attempts, retained

- Aggregate 233/234: `FB_MediumConfigStore.Durable` was TRUE while a set's write was
  still in flight; fixed.
- One Press ST run aborted on ADS 0x4 at the gate's first state read, before the Run
  request; the request is now retried until its deadline and the rerun passed.
- **The first file medium lost data on a real restart.** With the newest copy in slot
  `a`, its payload check compared slot `a` against slot `b`'s header (one shared buffer),
  the fallback re-chose the rejected slot, and the next write - steered by a per-key
  cache - replaced the newest copy. The acceptance harness's second runtime restart came
  back on defaults and announced intact documents lost; the host verified every file.
  234/234 TcUnit passes on that build had not shown it. The corrected medium rebuilds
  the expected header per slot, falls back to the newest valid slot, re-reads both
  headers before every write and treats an unreadable slot as "no answer"; a regression
  test pins the slot case. The first version is kept in the receipt.

## Live acceptance on the isolated runtime

Recorded in `…_LiveAcceptance.log` through the test-only `PRG_PlatformAcceptance`
harness: one file medium on `C:\ProgramData\Fraktal\Acceptance\` (created by the
medium) shared by a probe root's live documents, its set store and the user table.

- Documents are readable text; the user file holds no PIN in clear; `_users` and
  `_image` are absent from the ADS symbol table.
- Edits, a saved set and a registered user came back across **two runtime restarts**
  with the newest copies alternating between the slots, without a loss.
- Both station copies damaged through the PLC's file service → loss on
  `AcceptanceLive.station`, the value fell back, intact model documents restored, the
  next restart was silent.
- Model B's files deleted → loss by the persistent marker alone. The user table deleted
  → announced on `Acceptance.Access` once its marker had been stored in the current
  project; deleted after another project's activation had replaced the persistent data,
  it went unreported (a lost marker only misses a loss).
- A directory in place of the next station copy → `Pending`, `Failed` and
  `CONFIG_PERSIST_FAILED`, the newest copy untouched; after removal the 10 s retry wrote
  it, the alarm closed and the value survived a restart.
- The runtime's account creates the files; an unelevated host user can read but not
  change them.

## Not executed or not proven here

- The Press demo application itself was not run on any runtime; its wiring is covered by
  the compile, the full x86/x64 builds and the harness that mirrors it.
- The Press target NEXEED-O650RLB3, its write filter exclusion for the data folder, and
  uncontrolled power loss; the retentive medium's persistent write was exercised only in
  TcUnit.
- A medium that cannot answer was reasoned from the measured file-service behaviour and
  is not induced by a test (a directory opens as "not found").
- No machine controller was downloaded, activated or started. The test runtime is left
  on `FraktalTests` with the PLC stopped and Autostart off.
