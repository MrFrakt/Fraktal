# TwinCAT XAE compile, library, and TcUnit workflow

Status: binding procedure and historical execution record for Fraktal/TC3. The
normative architecture remains in Part I and the binding requirements remain in
Part II. This document is the operational source of truth for the XAE interactions
used to compile the reference implementation, install its two local development
libraries, and execute its two isolated test applications.

## 1. Evidence boundary

Four different operations were used. They are not interchangeable:

| Operation | What it proves | What it does not prove |
|---|---|---|
| Nested IEC project **Build/Rebuild** in XAE | The selected PLC application compiles for the selected platform; updates compile information and, when enabled, the TMC | Target configuration validity, runtime behavior |
| **Check all objects** on the nested IEC project | Every POU/DUT/GVL in that PLC project is compilable, including unused library objects | A full TwinCAT system build, target activation, download, or test execution |
| **Save as library and install** | Saves the compiled PLC library and registers it in the local TwinCAT Library Repository | A released/distributed package or proof that consumers were rebuilt against it |
| Activate → Login/Download → Start on the isolated runtime | The selected compiled test application executes on that runtime | Production-machine, hardware, safety, or site acceptance |

Beckhoff documents these boundaries in [Check all objects](https://infosys.beckhoff.com/content/1033/tc3_system/2525041803.html),
[Save as library and install](https://infosys.beckhoff.com/content/1033/tc3_plc_intro/4189307403.html),
and [loading, logging in, and starting the PLC](https://infosys.beckhoff.com/content/1033/tc3_plc_intro/3470887819.html).

The maintained repository automation,
`FraktalCore/PLC/TwinCAT/tools/Invoke-TwinCatBuild.ps1`, performs
the second operation only. It deliberately does not activate a target, download,
start a PLC, or install a library. Do not call its green result a full system
build or runtime test.

## 2. Environment actually used

The recorded 2026-08-01/02 baseline used:

- TwinCAT XAE/XAR 3.1.4026; the checked-in wrappers currently identify
  `3.1.4026.24`.
- Visual Studio/TwinCAT DTE automation through `VisualStudio.DTE.18.0` for the
  maintained hidden object-check gate.
- `Debug|TwinCAT OS (ARMV7-A)` for the initial Core, Modules, and internal Press
  bench nested builds associated with the saved target.
- `Debug|TwinCAT OS (x64)` for the subsequent library/test reconciliation and the
  isolated Windows 10 x64 test runtime.
- TcUnit installed in the local Library Repository.
- An isolated Windows 10 x64 runtime identified by the operator as
  `192.168.1.11`, using PLC ADS port 851. The event log records the initiating
  engineering AMS Net ID as `192.168.1.6.1.1`; that is not the target identity.

Platform is an input to the evidence. Reproduce the build for every platform a
release claims; do not copy an x64 result into an ARM acceptance record.

## 3. Solution isolation—the prerequisite that prevented GUID damage

A `.plcproj` is a nested PLC project, not a standalone Visual Studio solution.
Open the supplied `.slnx` wrapper, or create a TwinCAT XAE Project and use
**PLC → Add Existing Item…**.

Use these wrappers independently:

| Order | Purpose | Wrapper |
|---:|---|---|
| 1 | Core library | `FraktalCore/PLC/TwinCAT/Framework/FraktalCore.slnx` |
| 2 | Modules library | `FraktalCore/PLC/TwinCAT/Framework/FraktalModules.slnx` |
| 3 | Internal Press feature bench | `FraktalCore/PLC/TwinCAT/Examples/PressDemo/PressDemo.slnx` |
| 4 | Core/Modules test gate | `FraktalCore/PLC/TwinCAT/Tests/FraktalTests.slnx` |
| 5 | Internal Press integration gate | `FraktalCore/PLC/TwinCAT/Examples/PressDemo/PressTests.slnx` |

Close one wrapper before opening the next when source-library and consuming
projects would otherwise coexist. In particular:

- never load Core/Modules source projects beside an application that consumes
  their installed versions;
- never load `Fraktal_Press_Demo.plcproj` beside `PressTests.plcproj`, because the
  test project links the same physical Press Unit/sequence/release objects;
- after installing a changed library or editing a `.plcproj` reference, close and
  reopen the consumer solution so XAE discards its in-memory resolution.

This isolation was introduced after one combined solution produced duplicate
object ownership, GUID/Line-ID rewrites, and more than one thousand warnings.

## 4. Full compile and local library installation

### 4.1 Build and install Fraktal_Core

1. Close any application or Modules solution that consumes `Fraktal_Core`.
2. Open `Framework/FraktalCore.slnx`.
3. Select the required `Debug|TwinCAT OS (<platform>)` combination.
4. Under **PLC → Fraktal_Core**, select the nested `Fraktal_Core Project`.
5. Run **Build** (use **Rebuild** when replacing an installed version). Also run
   **Check all objects** for a library, because unused public objects must compile.
6. Open **View → Error List**. Accept only zero errors and zero warnings for the
   Fraktal source. In automation, the corresponding result was
   `LastBuildInfo=0`; that is DTE's count of projects that failed in the last
   solution build, not a substitute for inspecting diagnostics.
7. Confirm that `Framework/Fraktal_Core/Fraktal_Core.tmc` was regenerated when
   TMC generation is part of the build evidence.
8. Confirm the PLC project properties before saving:
   - title `Fraktal_Core`;
   - company `fraktal-automation`;
   - project version `0.4.0.0` for the recorded baseline;
   - placeholder `Fraktal_Core`.
9. Right-click the nested **Fraktal_Core Project** and select **Save as library
   and install**. Choose the local development artifact path in the save dialog.
10. Open **PLC → Library Repository**, find company `fraktal-automation`, and
    confirm that exactly the intended `Fraktal_Core` version is installed.
11. Save and close the solution.

The recorded libraries had `<Released>false</Released>` and were installed into
the local development repository. The saved `.library`/`.compiled-library` file
path was not archived, so the 2026-08-01 action is local-development evidence,
not a claim that a signed release library was distributed.

### 4.2 Build and install Fraktal_Modules

1. With the Core source solution closed, open
   `Framework/FraktalModules.slnx`.
2. Expand **References** and verify that placeholder `Fraktal_Core` resolves to
   the just-installed intended version. If every Modules type is unknown, stop:
   fix this one reference rather than editing dependent POUs.
3. Select the same claimed platform used for Core.
4. Select the nested `Fraktal_Modules Project`; run **Build/Rebuild** and
   **Check all objects**.
5. Require zero errors/warnings and, when applicable, confirm regeneration of
   `Framework/Fraktal_Modules/Fraktal_Modules.tmc`.
6. Verify title/company/version/placeholder. The recorded baseline was
   `Fraktal_Modules`, `fraktal-automation`, `0.3.0.0`, and
   `Fraktal_Modules`.
7. Right-click the nested project → **Save as library and install**.
8. Verify the intended version in **PLC → Library Repository**, save, and close.

TwinCAT's Automation Interface exposes the equivalent
`ITcPlcIECProject.SaveAsLibrary(path, install)`, and `tools/Invoke-TwinCatLibraryInstall.ps1`
now automates the §4.1/§4.2 sequence above: it installs Core then Modules in that
order (Modules consumes Core through an installed reference, so the order is not
optional), opens each solution in its own isolated hidden XAE, and runs
`CheckAllObjects()` first so a library that does not compile never replaces a good
one in the repository. Its evidence boundary is exactly the GUI action’s — a local
development install, not a released or distributed package, and no proof that any
consumer was rebuilt against it (§4.3 still applies).

**This step is not optional after changing a library.** A consumer such as
`Tests/Fraktal_Tests` resolves `Fraktal_Modules` as an *installed placeholder*, never
from library source, so a newly added type stays invisible until the library is
reinstalled. The symptom is the object-check gate failing the consumer with a wall of
`C0046: Identifier ... not defined` naming everything except the real cause.

### 4.3 Reload and compile consumers

After both installs, open each consumer in its own solution, reload its
placeholders, and compile the nested IEC project. The recorded sequence was:

1. reopen the internal Press bench and build `Fraktal_Press_Demo Project`;
2. open `FraktalTests.slnx` separately and check/build its nested test project;
3. open `PressTests.slnx` separately and check/build its nested test project.

The initial direct nested Core, Modules, and Press builds returned
`LastBuildInfo=0`, an empty Error List, and regenerated their TMC files. A full
system-project build then stopped at **Check config** because its saved remote
target was unavailable. That system-level result was not reported as a PLC
compiler failure; the nested IEC build was the compiler authority.

## 5. Maintained hidden-XAE object-check gate

From the repository root:

```powershell
.\tools\Invoke-TwinCatBuild.ps1
```

For each test solution the script:

1. creates a fresh hidden `VisualStudio.DTE.18.0` process;
2. opens only that `.slnx`;
3. selects `Debug|TwinCAT OS (x64)`;
4. gets the TwinCAT System Manager from the first solution project;
5. resolves `TIPC^<PLC name>^<PLC name> Project`;
6. fails if `BootProjectAutostart` is true;
7. calls `CheckAllObjects()`;
8. writes one log under `artifacts/twincat-build/`;
9. closes the solution without saving, quits DTE, and releases COM objects.

An OLE message filter retries transient `RPC_E_CALL_REJECTED` responses while PLC
Control is loading. It does not fix a broken XAE registration. If startup returns
`CO_E_SERVER_EXEC_FAILURE`, close stale hidden XAE processes created by the failed
attempt and retry from a clean interactive session; never kill an unidentified or
operator-owned XAE process.

The command's success means `CheckAllObjects=TRUE` and autostart false for both
test wrappers. It does not regenerate every build artifact reliably and never
contacts a target.

### 5.1 Diagnostic boundary when `CheckAllObjects()` returns `FALSE`

`ITcPlcIECProject2.CheckAllObjects()` returns a Boolean; the documented TwinCAT
Automation Interface exposes no message collection *on that method*. Beckhoff
also states that **Check all objects performs no code generation and creates no
compilation-information file**. The Boolean and detailed diagnostics therefore
come from separate automation surfaces.

Beckhoff documents reading the IDE Error List through
`EnvDTE80.DTE2.ToolWindows.ErrorList.ErrorItems`. The `DTE2` qualification is
essential: a COM object created from `VisualStudio.DTE.<version>` is commonly
seen by PowerShell as base `EnvDTE.DTE`; reading `ToolWindows` through that base
wrapper can report no property or lead to an empty/incorrect probe. Load the
`envdte80.dll` from the same Visual Studio/TcXaeShell installation, query the
`DTE2` COM interface, and read the collection only after synchronous
`CheckAllObjects()` returns. The Build Output pane is a second useful source: on
the pinned host PLC Control writes the full IEC compile transcript there.

Verified 2026-08-05 with Visual Studio 18 and TwinCAT 3.1.4026: a hidden check of
`FraktalTests.slnx` returned `FALSE`; the corrected DTE2 access returned six
`ErrorItems`, including description, project, file/object, line, and column, and
the DTE **Build** pane contained the same six coded compiler messages plus
`Compile complete -- 6 errors, 0 warnings`. The IDE window did not need to be
visible.

Consequently:

- `FALSE` is authoritative evidence that the all-object gate failed;
- DTE2 ErrorItems and Build-pane text are diagnostic detail, not the pass/fail
  authority; zero captured rows never override `FALSE`;
- base-DTE access, checking before the operation completes, or loading interop
  types from a different IDE installation can explain a misleading zero count;
- a `.compileinfo` file is not a Check-all-objects error log. Build/Rebuild may
  create compile information, but checks only used objects and therefore cannot
  replace the library-oriented all-object gate.

References: Beckhoff's [Automation Interface call](https://infosys.beckhoff.com/content/1033/tc3_automationinterface/242730891.html),
[Check all objects command](https://infosys.beckhoff.com/content/1033/tc3_plc_intro/2531345035.html),
the official [Automation Interface manual](https://download.beckhoff.com/download/Document/automation/twincat3/Automation_Interface_EN.pdf)
(Error List access and the `DTE2` requirement), and
[PLC Error List](https://infosys.beckhoff.com/content/1033/tc3_userinterface/2531042955.html);
Microsoft's [Output-window automation](https://learn.microsoft.com/en-us/visualstudio/extensibility/extending-the-output-window)
and [`OutputWindowPane.TextDocument`](https://learn.microsoft.com/en-us/dotnet/api/envdte.outputwindowpane.textdocument).

### 5.2 Automated capture and visible fallback

`FraktalCore/PLC/TwinCAT/tools/TcXaeDte.ps1` loads the matching `EnvDTE80`
interop, captures the DTE2 Error List, and snapshots every readable Output pane.
It is dot-sourced by **both** `Invoke-TwinCatBuild.ps1` and
`Invoke-TwinCatTcUnitGate.ps1`.

That sharing is not tidiness. Until 2026-08-16 each gate carried its own copy,
and the copies diverged: the TcUnit gate reached the Output window by walking
`$Dte.Windows` probing `.Caption`, and read panes through `Selection.SelectAll()`.
Both hit exactly the late-binding failure §5.1 warns about — `The property
'Caption' cannot be found on this object` — so its capture threw on the first
window and fell into a catch on *every* run. That gate had no Output-pane
diagnostics at all, which is why an activation that silently did nothing was
indistinguishable from a capture limitation for weeks. One implementation, so
this section has one thing to be true about.

The per-solution log contains:

- `CheckAllObjects=True|False`;
- `Dte2Interop=<loaded assembly>` or an explicit capture-unavailable reason;
- `DteErrorListCount=<n>` and one structured line per item;
- the **Build** pane transcript, including TwinCAT compiler codes and the final
  error/warning count when XAE supplies it;
- other DTE panes as host/package troubleshooting context.

This is the primary detailed-message artifact. If `CheckAllObjects=False` and the
log has neither nonzero ErrorItems nor a compiler transcript, use the visible
fallback without changing the project or platform:

1. Record the failing log's solution path, configuration, platform, IEC project
   path, and XAE build.
2. Open only that wrapper in a visible XAE process and activate the same
   configuration/platform. Do not use an already-open solution with extra source
   or consumer projects.
3. Open TwinCAT's **View -> Error List**, clear its existing rows and filters,
   select the whole PLC project/solution scope, and enable Errors, Warnings, and
   Messages.
4. Select the same nested `<name> Project` and run **Check all objects** again.
5. Click inside the PLC Error List, select all rows, and use **Copy** from its
   context menu (or `Ctrl+C` after selecting the rows). Paste the tabular result
   into a UTF-8 text/TSV file beside the hidden log, for example:

   ```powershell
   Get-Clipboard -Raw | Set-Content -Encoding utf8 `
     artifacts\twincat-build\FraktalTests-check-all-objects-errors.tsv
   ```

6. Retain the unedited export with the Boolean log. Add a screenshot only when
   the clipboard omits a column or related-position row; the text export remains
   the searchable diagnostic artifact.

Do not parse visible clipboard columns as a stable CI protocol: labels,
localization, and related-position formatting can vary by XAE build. Prefer the
documented DTE2 collection and raw Build-pane text. A version-pinned Windows UI
Automation helper could scrape the grid, but it is unnecessary on the verified
host and remains an undocumented UI dependency. It shall never turn an
unreadable list into a pass.

### 5.3 Other logs and what they mean

- `TcXaeShell.exe /Log <path>` (where that shell accepts the Visual Studio
  switch) produces the Visual Studio activity log. Use it for package loading,
  COM registration, extension crashes, and IDE startup failures—not for IEC
  source diagnostics. Microsoft documents `/Log` as an IDE troubleshooting log.
- The DTE **Build** Output pane is the verified textual IEC diagnostic log for the
  direct `CheckAllObjects()` call on this host. Retain it with the Boolean. A
  separate `devenv.com ... /Build ... /Out <file>` invokes Build, not Check all
  objects, and therefore does not cover unused library objects.
- TwinCAT Event Logger output belongs to activation, runtime, ADS, and TcUnit
  evidence. It does not contain an offline Check-all-objects error list.

Reference: Microsoft's [`/Log` switch](https://learn.microsoft.com/en-us/visualstudio/ide/reference/log-devenv-exe).

## 6. Manual isolated-runtime TcUnit execution

The runtime part of the recorded acceptance was performed by the operator under
agent instructions, not by `Invoke-TwinCatBuild.ps1`.

### 6.0 First check the host can run a gate at all

An engineering-only install compiles every solution and passes the whole
object-check gate, so a host can look fully capable and still have nowhere to
download to. One command settles it, and it is the ONLY one that does:

```powershell
cd FraktalCore/HMI/gateway
dart run tool/probe_sim_flag.dart <amsNetId> 851
```

Distinguish the two ADS failures, because they send you to different places:
error **6** is "the router answered, nothing is on that port" (no runtime, or
the PLC is in Config mode); error **7** is "no such target" (routing or
AmsNetId wrong). Only the second is a network problem.

**Do not conclude "no runtime" from the filesystem.** A TwinCAT 4026 usermode
runtime is instantiated under

```
C:\ProgramData\Beckhoff\TwinCAT\3.1\Runtimes\<InstanceName>\3.1\
```

and **not** beside the shipped `UmRT_Template` under `Program Files (x86)`,
which stays empty however many instances exist. There is likewise no
`HKLM:\SOFTWARE\WOW6432Node\Beckhoff\TwinCAT3\Runtimes` key to consult. This note
previously recommended exactly those two checks and drew the wrong conclusion
from them on a host that did have a working `UmRT_Default` instance: absence
under `Program Files` proves nothing. `TcSysSrv` running only means the AMS
router is up; the process that indicates a usermode runtime is
`TcSystemServiceUm`.

The instance directory is also where the evidence lives: `Boot/Plc/Port_851.*`
is the downloaded boot application, `Boot/CurrentConfig.xml` the activated
configuration, and `Boot/LoggedEvents.db` the TcEventLogger store.

**`LoggedEvents.db` does not contain TcUnit results.** It is the §‑alarm/event
API store and is empty on a test runtime. TcUnit reports through `ADSLOGSTR`,
which reaches the AMS router log that XAE renders in its event view and which
TwinCAT does not persist to disk anywhere on the target. That, not a missing
hook, is why §9 records the runtime gate as un-automated: the numbers exist
only in a live view, so a result is read by a person or by something that
subscribes to the router log.

### 6.1 Target safeguards

1. Use only the isolated test VM/runtime. Confirm its route/identity before any
   activation; do not infer the target from the engineering AMS Net ID shown in
   the event log.
2. Keep the local Press bench or any machine runtime out of scope.
3. Confirm **Autostart Boot Project** is disabled in the selected test wrapper and
   on the target. The serialized false value prevents a new autostart selection;
   it does not delete old boot data already present on a runtime.
4. If an older test application returns after restart, disable/remove that stale
   boot project on the isolated target before continuing.

### 6.2 Execute one gate

Perform this sequence first for `FraktalTests.slnx`, then close it and repeat for
`PressTests.slnx`:

1. Open only the gate's solution.
2. Select the isolated TwinCAT target and `TwinCAT OS (x64)`.
3. Run **Check all objects** or build the nested test project and require an empty
   Error List.
4. Select the test PLC as **Active PLC Project**.
5. Select **TwinCAT → Activate Configuration** and confirm the restart into Run
   mode for the isolated target.
6. Select **PLC → Login**. When prompted to create/load the application, answer
   **Yes**; this downloads the PLC application.
7. Select **PLC → Start**, or press **F5**.
8. Watch the TwinCAT Event Logger output from `PlcTask`, and capture the complete
   TcUnit runner lines and final summary.
9. Stop the test PLC or return the isolated target to Config mode after harvesting
   evidence. Do not create a boot project.

### 6.3 Prove the selected gate, not merely a green summary

Accept a result only when runner identity, suite count, test count, and failure
count all match the intended source inventory. For the archived 2026-08-02
baseline:

| Gate | Required runner in the log | Archived result |
|---|---|---:|
| Core/Modules | `PRG_TcUnitRunner` | 84 tests / 26 suites / 0 failed |
| Internal Press integration | `PRG_PressTestRunner` | 8 tests / 2 suites / 0 failed |

These numbers describe that source snapshot; an intentional test inventory
change must update the expected CI counts and evidence together. A first attempt
at the Press gate reported `PRG_TcUnitRunner` and 84/26, proving that the Core test
application was still selected. Selecting/downloading `PressTests.slnx` produced
the correct 8/2 result.

**The Core/Modules inventory has since grown to 30 suites / 98 tests.**
`FB_SequenceRaise_Tests`, `FB_SequencePar_Tests` and `FB_StateFlag_Tests` were
added after the 2026-08-02 baseline and two of them did not compile, so
`Fraktal_Tests` was carried as a known red and its runtime gate could not run at
all — a project that does not compile cannot be downloaded. They compile now.
Expect these counts for the next run:

| Gate | Required runner in the log | Expected from current source |
|---|---|---:|
| Core/Modules | `PRG_TcUnitRunner` | 140 tests / 36 suites / 0 failed |
| Internal Press integration | `PRG_PressTestRunner` | 8 tests / 2 suites / 0 failed |

Derive them from source rather than trusting this table — the suite count is the
`VAR` block of the runner POU, and the test count is the `TEST('…')` calls in the
suites it instantiates. A suite that exists but is not instantiated does not run,
and would make the log's own totals self-consistent while silently under-testing.

Validate captured logs with:

```powershell
python tools\tcunit_to_junit.py <raw-log> <junit.xml> `
  --gate-name <name> --expected-tests <n> --expected-suites <n> `
  --expected-runner <PRG_runner>
```

The validator fails on missing or multiple summaries, inconsistent totals,
failures, wrong counts, and missing/mixed/wrong runner identities.

## 7. Warnings observed and their disposition

- `Persistent data of symbol 'PRG_TcUnitRunner.…' not restored` appeared when the
  Press test application replaced the Core test application on ADS port 851. The
  old symbols did not exist in the new application, restoration was skipped, and
  the correct Press suites then passed. This was stale test-runtime metadata, not
  a Press implementation failure.
- `TwinCAT USB support could not be initialized. System start continued` was
  non-blocking on the Windows VM and irrelevant to the simulated test gates.
- A full solution **Check config** failure with an unavailable saved target did
  not invalidate a clean nested IEC build. It did mean target/configuration
  acceptance was still unproven.
- A hidden-DTE timeout or COM startup failure is tooling/environment evidence,
  not a compiler result. Do not reuse an old artifact log as a new pass.

## 8. Evidence retained

- `Specification/Evidence/2026-08-01_Core_Modules_TcUnit.md`
- `Specification/Evidence/2026-08-02_Press_TcUnit.md`
- `Specification/Evidence/2026-08-02_Press_TcUnit.raw.log`
- `artifacts/twincat-build/<solution>-build.log` for local object-check output
- `FraktalCore/PLC/TwinCAT/IMPLEMENTATION_NOTES.md` §§83–94 for the chronological
  compiler/runtime reconciliation

For every future run, retain: repository revision, `.plcproj`/runner/TMC hashes,
XAE/XAR build, platform, target identity and ADS port, autostart state, runner
identity, all five TcUnit summary fields, raw log, and generated JUnit. A result
without those identities is diagnostic information, not release evidence.

## 9. What was deliberately not automated

- no hidden script selected or activated a runtime;
- no hidden script logged in, downloaded, started, or stopped a PLC;
- no script created or deleted a boot project;
- no maintained script saved/installed the two libraries;
- no test project was loaded on the local Press bench/machine runtime;
- no internal Press result was treated as electrical, safety, SAT, or production
  evidence.

Future automation may use the official Automation Interface, but target identity
and destructive-state checks must remain explicit. Library creation can use
`SaveAsLibrary(path, install := TRUE)`; online actions must stay isolated from all
machine routes and preserve the same evidence boundaries.

### 9.1 Attempted automation and what it measured (2026-08-16)

`Invoke-TwinCatTcUnitGate.ps1` automates the engineering half of §6.2 under those
conditions: it refuses to activate a target it was not given by name, asserts
Autostart is disabled, and requires a clean `CheckAllObjects()`. Everything up to
and including activation works — activation reports `Ready for download`, the
runtime restarts into Run, and the application instance exists, is active, and
reports ADS port 851.

`ITcPlcOnline.Login()` does nothing. It returns immediately, writes no text to any
of the ten DTE output panes, and leaves `IsLoggedIn` false with
`OnlineOperationState` 0 indefinitely. Eliminated by measurement: all
`PLC_LOGIN_FLAGS` combinations including `SILENT` and `FORCEDOWNLOAD`; 90 s of
polling for asynchronous completion; an alternative DTE ProgID; the
`Unknown TMC file version` warning, which also appears in *successful manual
runs* and is therefore benign; releasing the tree item before use; and selecting
the active application instance.

The working explanation is that login requires answering the create/load prompt
of §6.2 step 6, and a hidden `SuppressUI` DTE cannot answer it — a suppressed
prompt is declined. On that reading the second bullet above records a
**constraint, not a preference**, and closing it needs a mechanism that does not
drive the IDE (TcUnit-Runner is the known one), not another login flag.

Two rules follow, and they are the durable part:

- **A void automation call that succeeds silently is not evidence.** `Login()`
  and `Start()` both return `void` and both complete without error while doing
  nothing. The gate now asserts `IsLoggedIn` and `PLC_APPSTATE_RUN` after them.
  Revisions before this date asserted neither and reported clean exits for runs
  in which no test executed — see the correction in
  `Specification/Evidence/2026-08-15_Core_Modules_TcUnit.md`.
- **Once the PLC is running by any route, the result no longer needs a human
  reader.** `Read-TcUnitResults.ps1` reads TcUnit's own
  `GVL_TcUnit.TestResults.TestSuiteResults` over ADS — per-suite and per-test,
  with failure messages — and writes it in the summary format
  `tcunit_to_junit.py` already validates. It waits on TcUnit's
  `AllTestSuitesFinished` flag rather than a fixed window, and reads by name
  through `ADSIGRP_SYM_VALBYNAME` so it consumes no symbol handles.
