# Fraktal/AB engineering workstation and PLC access runbook

**Verified:** 2026-08-13 on `DESKTOP-07VCTIN`

This is the fresh-chat operational handoff for the Allen-Bradley Phase 0
workstation. It records the interfaces that actually reached Studio 5000 and
the isolated CompactLogix controller. It is not authority to download, change
mode, write tags, clear faults, set the clock, update firmware, or change the
controller project. A new agent shall confirm the user's current authorization
before any controller-changing operation.

For the exhaustive inventory of proved, exploratory, failed, discovered-only,
and unavailable interfaces, read
[`AB_ENGINEERING_INTERFACE_AND_TOOL_CATALOG.md`](AB_ENGINEERING_INTERFACE_AND_TOOL_CATALOG.md)
before using this procedural runbook.

Do not commit ACD files, uploaded PLC source, tag values, screenshots containing
application logic, activation details, or credentials. Use a disposable copy in
`%TEMP%` for every Studio or SDK experiment.

## 1. Proven baseline

| Item | Proven value |
|---|---|
| Host adapter | `Ethernet1`, `192.168.100.99/24`, MAC `00-0C-29-A6-F1-8A` |
| Controller endpoint | `192.168.100.89:44818`, direct connected route |
| Controller | `1769-L24ER-QB1B/A` / `LOGIX5324ER`, firmware `33.014`, serial `7036B510` |
| Pre-test controller project observed by Linx | `FIS_Aptiv_Rev1` |
| Current isolated test project | S9 coherence memory-only fixture retained in Remote Run; `FRK_S9_Freeze` at zero and `FRK_S9_MutationPeriod` at its default 10; clock host-aligned with PTP disabled/unsynchronized |
| USB identity when attached | `USB\VID_14C0&PID_001F\7036B510`, Rockwell USB CIP driver |
| FactoryTalk Linx | `6.50.00`, point-to-point driver alias `Fraktal_AB` |
| Studio executable used | `C:\Program Files (x86)\Rockwell Software\Studio 5000\Logix Designer\ENU\v33\Bin\LogixDesigner.Exe` |
| Logix Designer SDK | `2.00.00`; C# client package `2.0.861`; `LdSdkService` |
| Proven .NET host | .NET SDK `8.0.423`, `win-x86` |
| Python | `C:\Users\Rockwell Automation\AppData\Local\Python\bin\python.exe` |

The controller is a CompactLogix 5370 with an integral Ethernet port. Its
Ethernet Studio/Linx path ends at the controller node; do not append a
ControlLogix-style `Backplane\slot` segment to that route. The Rockwell USB
CIP driver is different: Studio reports the selected USB controller as
`Backplane\16` inside the driver's virtual chassis.

## 2. Safety classification

| Class | Examples | Rule |
|---|---|---|
| Read-only health/discovery | adapter inspection, TCP test, CIP identity/object reads, Linx browse | safe Phase 0 default |
| Named symbolic reads | explicitly approved tags through the redacting probe | read-only, but keep tag names and values out of committed evidence |
| Upload | controller to a new/disposable ACD | controller-read-only; it changes the local file and can take several minutes |
| Workstation configuration | add/update/delete a FactoryTalk Linx driver | changes this engineering PC only; record the exact driver |
| Controller-changing | download, mode change, tag write, fault clear, clock set, firmware, controller/network configuration | require current explicit authorization and an exact target immediately before use |

The repository read probes deliberately expose no generic CIP service and no
write operation. The separate Phase 0 execution tool has a fixed `FRK_*` write
surface, serial guard, fixture fingerprint, explicit arm flag, and mandatory
cleanup. Do not replace either boundary with an interactive client that makes
arbitrary services or writes easy during evidence collection.

## 3. Network preflight

Run these read-only checks before opening Studio. Adapter names can change, so
the source address is the decisive fact.

```powershell
Get-NetAdapter | Where-Object Status -eq 'Up' |
  Select-Object Name, InterfaceDescription, MacAddress, LinkSpeed

Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object IPAddress -Like '192.168.100.*' |
  Select-Object InterfaceAlias, IPAddress, PrefixLength

Test-NetConnection 192.168.100.89 -Port 44818 -InformationLevel Detailed |
  Select-Object RemoteAddress, RemotePort, InterfaceAlias, SourceAddress,
                TcpTestSucceeded
```

Expected: source `192.168.100.99` through `Ethernet1`, TCP test true. Stop and
reconcile the route if Windows chooses another source interface.

## 4. FactoryTalk Linx command-line interface

The supported configuration executable and its installed help are:

```text
C:\Program Files (x86)\Rockwell Software\RSLinx Enterprise\FTLinxCfgIETool.exe
C:\Program Files (x86)\Common Files\Rockwell\Help\FactoryTalk Services Platform\Help\ENU\ftlinx\common-content\
```

The verified global driver already exists. Browse it first:

```powershell
$linxTool = 'C:\Program Files (x86)\Rockwell Software\RSLinx Enterprise\FTLinxCfgIETool.exe'
& $linxTool /Browse /NetworkPath 'Fraktal_AB\192.168.100.89' `
  /Timeout 10000 /Silent
```

The result is written to
`%LOCALAPPDATA%\Temp\FTLinxCfgIETool_log_*.txt` and shall contain
`Browse Fraktal_AB\192.168.100.89 successfully`.

Only if the driver is absent, the installed Rockwell tool's supported creation
form is:

```powershell
& $linxTool /AddDriver /Scope Global /driverName Fraktal_AB `
  /driverType PointToPoint /DEVICEADDRESSES '192.168.100.89' /Silent
```

Do not add duplicate aliases. The Phase 0 run used a point-to-point device list
so discovery is bounded to the isolated PLC. FactoryTalk Linx's topology record
returned display alias `Fraktal_AB`, internal name `Ethernet 2`, project
`FIS_Aptiv_Rev1`, catalogue `1769-L24ER-QB1B`, and serial `7036B510`.

The `BrowseServices` COM type library is also usable from 32-bit PowerShell.
During discovery it was imported to `%TEMP%\Interop.BrowseServices.dll` and
provided `TopologyProvider`, `DriverProvider`, and `BrowseProvider`. Useful
read-only calls were `GetDriverList`, `GetTargetInfo`, `GetAdapterList`,
`GetChildren`, and `GetTopologyNode`. This is an inspection interface, not the
preferred configuration path; use `FTLinxCfgIETool.exe` for supported driver
changes.

### USB interface and proven Studio upload

The controller enumerates through Rockwell's USB CIP driver as
`USB\VID_14C0&PID_001F\7036B510`. FactoryTalk Linx and Studio v33 **Who Active**
browse it through the `1789-A17` virtual chassis; Studio displays
`Backplane\16` for the selected USB controller. This proves the same serial
identity independently of Ethernet. USB depends on the physical cable, so
recheck rather than assuming it is attached:

```powershell
Get-PnpDevice -PresentOnly |
  Where-Object InstanceId -Like 'USB\VID_14C0&PID_001F*' |
  Select-Object Status, Class, FriendlyName, InstanceId
```

On 2026-08-13, after the USB cable was reconnected, Studio v33 selected
`16, 1769-L24ER-QB1B, FIS_Aptiv_Rev1` under **USB** and displayed
`Backplane\16`. The **Connected To Upload** dialog matched controller type,
project, serial `7036B510`, and `No Protection`. A read-only upload completed
with `0 error(s), 0 warning(s)` and the explicit message `Upload complete with
no errors or warnings.` The uploaded project and its online tag-value refresh
were saved only to a disposable `%TEMP%` ACD. No controller-changing operation
was issued.

Later that day, under explicit download/mode/tag-write authorization with all
I/O disconnected, the same USB identity/path was used to download the verified
memory-only `FraktalPhase0` v33 fixture. The pre-download dialog again matched
type, path, serial, and `No Protection`. Studio reported `Download complete with
no errors or warnings.`, returned the controller to Remote Run, and showed
`Controller OK` plus expected `I/O Not Present`. Exact artifact, rollback, and
execution details are in
[`AB_PHASE0_PHYSICAL_EXECUTION_EVIDENCE.md`](AB_PHASE0_PHYSICAL_EXECUTION_EVIDENCE.md).

## 5. Direct EtherNet/IP interfaces

### Fixed CIP identity/object probe

[`fraktal_ab_eip_probe.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_eip_probe.py)
uses only ListIdentity, Register/UnregisterSession, and
Get_Attribute_Single (`0x0E`) against TCP/IP Interface Object `0xF5` and Time
Sync Object `0x43`, instance 1.

```powershell
$python = 'C:\Users\Rockwell Automation\AppData\Local\Python\bin\python.exe'
& $python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_eip_probe.py `
  192.168.100.89 --expect-serial 7036B510 --samples 3 --timeout 5
```

The command fails closed on a serial mismatch. The verified result showed the
expected controller/firmware, `192.168.100.89/24`, and no gateway/DNS. The
pre-test application reported PTP enabled but not synchronized. The downloaded
fixture reports PTP disabled and not synchronized; always record both fields
with the project identity because Time Sync configuration is project-dependent.

### Redacting symbolic-read probe

[`fraktal_ab_symbolic_read_probe.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_symbolic_read_probe.py)
uses pinned `pylogix==1.1.5`, accepts only explicitly named reads, and never
prints values. Install the pinned dependency into a temporary directory:

```powershell
$phase0Packages = Join-Path $env:TEMP 'FraktalPylogix'
& $python -m pip install --target $phase0Packages --require-hashes `
  -r FraktalCore\PLC\Allen-Bradley\tools\requirements-phase0.txt
$env:PYTHONPATH = $phase0Packages
```

Then run only with tags approved for the current evidence task:

```powershell
& $python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_symbolic_read_probe.py `
  192.168.100.89 --expect-serial 7036B510 `
  --tag 'case=<approved-tag>' --array 'array=<approved-array>,25'
```

The session proved controller/program scalars, STRING, UDT members, arrays, and
a fragmented 1232-byte UDT read. Values remain redacted.

### Fixed Phase 0 data-fixture write/execution probe

[`fraktal_ab_phase0_execute.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_phase0_execute.py)
is the fixed S1 data-fixture writer. It cannot accept a caller-selected
tag or value. It requires the exact controller serial, an explicit arming flag,
and the complete disposable-fixture fingerprint before its first write; it then
cleans every writable input and verifies cleanup before returning success.

```powershell
& $python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_phase0_execute.py `
  192.168.100.89 --expect-serial 7036B510 --timeout 5 --execute-fixture
```

Use this only while the verified `FraktalPhase0` fixture is downloaded and the
user's controller-changing authorization is current. On the physical v33
target it proved DINT, REAL, DINT[25], STRING, UDT member, cyclic-result,
heartbeat, Read Only rejection, None-hidden/rejection, and cleanup cases. The
expanded fixture additionally proved controller/program-scoped DINTs and a
fragmented 4 KiB `DINT[1024]` write/read/result/cleanup path.

Do not run this tool against the controller's current S2 project: its exact
fixture fingerprint will reject it before writing.

### Fixed S9 coherence probe

[`fraktal_ab_s9_execute.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s9_execute.py)
is the only writer for the current fixture. It writes `FRK_S9_Freeze` and
`FRK_S9_MutationPeriod` and restores both; the period is range-checked in the
controller, so a bad value cannot park the fixture in a strange state.

```powershell
& $python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_s9_execute.py `
  192.168.100.89 --expect-serial 7036B510 --timeout 30 `
  --sweep 1,5,20,100 --attempts 10 --execute-fixture
```

The vector is ordered so a pass cannot be vacuous: it first shows the guard does
not reject a frozen controller, then shows unguarded reads genuinely tear, and
only then sweeps the mutation rate. The property that matters is that no
accepted read is ever internally inconsistent.

### Fixed S7 manifest read-cost probe

[`fraktal_ab_s7_execute.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s7_execute.py)
was the writer for the manifest fixture, which the S9 download has since
replaced; its fingerprint check now rejects the controller. It writes one input:
`FRK_S7_BumpRevision`, which raises `ConfigRevision` as a configuration change
would. Everything else is read-only.

```powershell
& $python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_s7_execute.py `
  192.168.100.89 --expect-serial 7036B510 --timeout 30 `
  --connection-sizes 500,4000 --repeats 3 --execute-fixture
```

Each connection size needs its own session, because the size is negotiated when
the connection opens — reusing one session silently measures the first size
twice.

### Fixed S12 type-map probe

[`fraktal_ab_s12_execute.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s12_execute.py)
was the writer for the type-map fixture, which the S7 download has since
replaced; its fingerprint check now rejects the controller. It requires the exact serial,
explicit arming and the S12 fingerprint, writes only that fixture's declared
inputs with values hard-coded in the tool, and restores all of them.

```powershell
& $python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_s12_execute.py `
  192.168.100.89 --expect-serial 7036B510 --timeout 5 --execute-fixture
```

Reading a structured tag through pylogix returns the **raw CIP payload**, which
is how the UDT layout is measured. Read a structured *array* with an explicit
element count: without one the controller returns only the first element, which
silently turns a two-instance stride measurement into a one-instance read.

### Fixed S11 sequence-execution probe

[`fraktal_ab_s11_execute.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s11_execute.py)
was the writer for the sequence-execution fixture, which the S12 download has
since replaced; its fingerprint check now rejects the controller. It requires the
exact serial, explicit arming, and the complete S11 fingerprint — which itself
checks that the root module AOI advances while idle and that the chart is not
called while idle. It writes only `FRK_S11_Command` and `FRK_S11_ResetRequest`,
then restores and verifies both.

```powershell
& $python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_s11_execute.py `
  192.168.100.89 --expect-serial 7036B510 --timeout 5 --settle 2 --execute-fixture
```

The physical v33 run proved identical step traces and identical four-scan
completion for the ST and native-SFC forms, module-AOI-before-sequence ordering,
exactly one scan of command/result latency, one numbered leg per simultaneous
Core branch, one `SFR` per start/reset edge with `JSR` only while BUSY, and
identical re-entry after reset.

### Fixed S2 nested-AOI execution probe

[`fraktal_ab_s2_execute.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s2_execute.py)
was the writer for the eight-level nested-AOI fixture, which the S11 download
has since replaced; its fingerprint check now rejects the controller. It
requires the exact serial, explicit arming, and the complete S2 tag/access
fingerprint.
It writes only `FRK_S2_Ctx.Command` and `FRK_S2_Text`, then restores and verifies
both. It accepts no arbitrary tag or value.

```powershell
& $python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_s2_execute.py `
  192.168.100.89 --expect-serial 7036B510 --timeout 5 --execute-fixture
```

The physical v33 run proved one UDT `InOut`, one STRING `InOut`, atomic
Input/Output, eight nested invocations, Read Only rejection, None-hidden paths,
unconditional scan execution, and cleanup. Limit/signature variants are
offline-only and must never be downloaded merely to repeat compiler evidence.

### Fixed transport-budget probe

[`fraktal_ab_transport_budget_probe.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_transport_budget_probe.py)
is read-only and fixed to the expanded fixture's heartbeat, completion, and
large-array tags. It requires the expected serial, bounds connection sizes,
cycle counts and concurrent readers, closes every client, and never emits tag
values.

```powershell
& $python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_transport_budget_probe.py `
  192.168.100.89 --expect-serial 7036B510 --timeout 5 --cycles 25 `
  --required-readers 4 --connection-sizes 128,256,500,1000,2000,4000 `
  --reader-levels 1,2,4,8,12,16
```

The physical run passed every size, 25 reconnect cycles, four required readers,
all tested levels through 16, and recovery through a new client after one
deliberately impossible 0.1 ms timeout. Use 500 bytes and four readers as the
conservative S1 ceiling until S3 measures the real application workload.

### Fixed wall-clock probe

[`fraktal_ab_time_probe.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_time_probe.py)
is read-only unless `--set-to-host` is explicitly present. A set requires exact
serial and fixture fingerprint checks and can invoke only `SetPLCTime(dst=0)`;
the tool has no tag-write, mode, download, fault, firmware, or network operation.

```powershell
# Read only
& $python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_time_probe.py `
  192.168.100.89 --expect-serial 7036B510 --timeout 5 --samples 7

# Controller-changing: use only with current explicit authorization
& $python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_time_probe.py `
  192.168.100.89 --expect-serial 7036B510 --timeout 5 --samples 7 --set-to-host
```

The authorized 2026-08-13 set corrected a 1998 wall clock to host UTC; seven
samples placed controller-minus-host midpoint between -19.855 and -12.629 ms.
The data and S2 fixtures remained PTP-disabled and unsynchronized, so publish
their controller source time with `TimeSynchronized=FALSE` and retain gateway
reception time separately.

## 6. Studio 5000 v33 access

Open only a disposable v33 ACD copy:

```powershell
$studio = 'C:\Program Files (x86)\Rockwell Software\Studio 5000\Logix Designer\ENU\v33\Bin\LogixDesigner.Exe'
$disposableAcd = Join-Path $env:TEMP 'Fraktal_AB_disposable.ACD'
Start-Process -FilePath $studio -ArgumentList ('"{0}"' -f $disposableAcd)
```

For Ethernet in Studio:

1. Select **Communications > Who Active**.
2. Expand **FactoryTalk Linx - Desktop** and **Ethernet, Fraktal_AB**.
3. Select the `192.168.100.89, 1769-L24ER-QB1B` node. The project name shown
   beside it is a cached Linx discovery string and may name a project the
   controller no longer holds — it stayed `FIS_Aptiv_Rev1` through the whole S11
   session. Correlate identity from the connection dialog or a direct symbolic
   read instead.
4. Wait until the selected path is `Fraktal_AB\192.168.100.89` and the required
   button becomes enabled.
5. For a read-only controller upload, choose **Upload...**, inspect the
   **Connected To Upload** identity, and upload only to the disposable ACD.

This Ethernet path positively connected in Studio and the pre-upload dialog matched
name, catalogue, serial `7036B510`, and `No Protection`. A 2026-08-13 upload
then transferred tags and built routines locally but failed near completion
with Studio `Error 731-0` / `Communications timed out`; Studio reverted the
disposable ACD. Direct CIP identity and Linx browse passed immediately after
the failure.

For the proven USB upload, expand **USB**, select
`16, 1769-L24ER-QB1B, FIS_Aptiv_Rev1`, verify that the selected path is
`Backplane\16`, and repeat the identity check in **Connected To Upload**. This
path completed the read-only upload with zero errors and warnings. Therefore
complete Studio upload is available through USB; the `731-0` result is an
Ethernet-path limitation, while SDK online upload over Ethernet remains open.

For an offline semantic check of that disposable upload, disconnect from the
controller or reopen the saved ACD offline, then choose
**Logic > Verify > Controller**. The 2026-08-13 verification completed with
`0 error(s), 0 warning(s)` and `Verify complete with no errors or warnings.`
The Error panel contained 31 diagnostic messages. Studio was closed without
saving and the ACD hash remained unchanged. This proves the positive v33
Verify path.

The complementary negative run opened the existing disposable v37 ACD whose
ST body contains `MissingTag := ;`, then invoked the same command. Studio
reported `2 Errors`, `0 Warnings`: `Invalid expression` and unexpected `;` on
line 1. Studio was again closed without saving and the fixture hash remained
unchanged. This is the fail-closed Verify/Error List evidence; SDK
`BuildAsync` had incorrectly accepted this same semantic error.

### UI automation interface used during Phase 0

PowerShell loaded `UIAutomationClient` and `UIAutomationTypes` to inspect the
native Studio dialog and embedded FactoryTalk Linx WPF tree. Useful v33 control
identifiers observed were:

| UI element | v33 AutomationId |
|---|---:|
| Who Active selected path | `1335` |
| path stored in project | `1336` |
| Set Project Path | `1456` |
| Upload / Upload... | `32085` |
| Download | `32086` |
| toolbar path | `1374` |
| Error count | `33648` |
| Warning count | `33649` |
| Message count | `33650` |
| Verify summary/detail | `33652` |
| status text | `59393` |

The WPF tree exposed text nodes for `Ethernet, Fraktal_AB` and the PLC. Native
Studio buttons did not expose an InvokePattern; the successful automation used
their `NativeWindowHandle` and the Win32 button message `BM_CLICK` (`0x00F5`).
`WScript.Shell.AppActivate`, `System.Windows.Forms.SendKeys`, and a
`System.Drawing.Graphics.CopyFromScreen` screenshot were used for menu access
and visual verification. These identifiers are version-specific diagnostics,
not a supported Rockwell API. Always re-read visible identity/path text before
invoking a button, and never automate Download or a mode change from a cached
coordinate or identifier.

The successful authorized download also observed pre-download confirmation
`AutomationId=1` and the post-download Remote Run prompt `Yes`/`No` IDs `6`/`7`.
They were invoked only after visible identity correlation; do not treat these
version-specific IDs as target selection or authorization.

The S11 download added the rest of that path. The pre-download dialog exposes
name `1016`, type `1307`, path `1304`, serial `1416` and security `1439`; read
all five and compare them with the expected target before confirming. Select the
Who Active tree node through `SelectionItemPattern` and re-read the selected
path from pane `1335`. Click the confirmation with **`PostMessage`**
`BM_CLICK`, not `SendMessage`: `SendMessage` does not return until the modal it
raises is dismissed, so an automation that uses it appears to hang with the
dialog waiting on screen.

For Verify, the controlled keyboard sequence after `AppActivate` was
`Alt+L` (**Logic**), `v` (**Verify**), `c` (**Controller**). Read the count and
summary panes above through UI Automation; do not decide pass/fail from a
screenshot. The positive result exposed `0 Errors`, `0 Warnings`, and
`Verify complete with no errors or warnings.` The negative result exposed
`2 Errors`, `0 Warnings`, and both syntax diagnostics in pane `33652`.

The repository packages that workflow as
[`fraktal_ab_studio_verify.ps1`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_studio_verify.ps1).
This workstation blocks direct script invocation by policy, so use the explicit
process-scoped bypass; it does not change the machine policy:

```powershell
$verify = 'FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_studio_verify.ps1'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $verify `
  -Revision 33 -Project $disposableAcd `
  -ExpectedErrors 0 -ExpectedWarnings 0 -TimeoutSeconds 120
```

For a deliberately invalid disposable fixture, pass its revision and expected
non-zero error count. The verified negative command used revision 37 and
`-ExpectedErrors 2 -ExpectedWarnings 0`. The script refuses ACDs inside the
repository and any pre-existing Studio session, performs no online operation,
retries the focus-sensitive menu invocation at most three times, closes Studio
without saving, proves the input hash unchanged, and returns JSON. A count
mismatch, changed input, timeout, or unclean close exits non-zero.

## 7. Logix Designer SDK interface

Installed material:

```text
C:\Users\Public\Documents\Studio 5000\Logix Designer SDK\dotnet\
C:\Users\Public\Documents\Studio 5000\Logix Designer SDK\dotnet\RockwellAutomation.LogixDesigner.CSClient.2.0.861.nupkg
C:\Program Files (x86)\Rockwell Software\Studio 5000\Logix Designer SDK\LdSdkServer.exe
```

`LdSdkService` is automatic and was running after reboot. The proven client
host was 32-bit .NET 8 (`win-x86`). Rockwell's installed examples were used for
`GetProcessorTypesAsync`, `CreateNewProjectAsync`, `ConvertAsync`,
`BuildAsync`, `SaveAsync`, `SaveAsAsync`, `GetCommunicationsPathAsync`, and
`UploadToNewProjectAsync`.

The repository's
[`Fraktal.Ab.OfflineProbe`](../FraktalCore/PLC/Allen-Bradley/tools/Fraktal.Ab.OfflineProbe/README.md)
opens ACD/L5K/L5X, reads the saved path, optionally saves a new disposable ACD
or L5X, and verifies the input hash is unchanged. It exposes no online or
controller-write operation. The ACD form is the proven SDK conversion path for
generated complete-project L5X before Studio Verify.

Important findings for a fresh agent:

- only FactoryTalk Linx is supported by this SDK; RSLinx Classic is not;
- Rockwell's example route has the form
  `AB_ETH-1\10.88.45.25\Backplane\0`, but the integral L24ER route that Studio
  actually connected with is `Fraktal_AB\192.168.100.89`;
- SDK `UploadToNewProjectAsync` with that Studio-confirmed route reached a
  communication timeout and created no ACD;
- saving the route through Studio changed the disposable ACD, but SDK 2.00
  `GetCommunicationsPathAsync` still returned an empty string;
- SDK `BuildAsync` is not semantic **Verify Project**: a deliberately invalid
  ST fixture still returned success. The uploaded project passed Studio v33
  **Logic > Verify > Controller**, while Studio v37 rejected the deliberately
  invalid fixture with two errors. Treat the Studio Error List as the semantic
  gate;
- SDK 2.00 physical-target `BuildAsync` is supported only by Logix Designer v37
  and later. Calling it for the fresh v33 upload-derived project returned
  `Operation not supported on Logix Designer version 33.0`; use v37 fixtures
  for SDK Build evidence and Studio v33 Verify for the live-revision project;
- Studio's successful USB upload was exported offline by the SDK, converted to
  a new v33 ACD with `Warnings="0" Errors="0"`, re-exported, and compared
  canonically. The documents matched after excluding exactly the three known
  timestamp attributes. This proves read-only USB upload plus v33 serialization
  round-trip, not semantic Verify or online SDK communications.
- The S2 nested-AOI project used the same complete-L5X-to-new-ACD SDK path,
  Studio v33 Verify, exact USB identity/download checks, and a post-download SDK
  export. `fraktal_ab_target_binding_compare.py` proved the post-download export
  differed only by controller minor `11→14`, local-module minor `11→14`, serial
  `16#0000_0000→16#7036_b510`, and the three known timestamps. The ordinary
  canonical comparator remains strict and intentionally does not ignore target
  binding.

The successful offline Build and L5X canonical round-trip procedure is in
[`AB_S4_S15_OFFLINE_ROUNDTRIP_EVIDENCE.md`](AB_S4_S15_OFFLINE_ROUNDTRIP_EVIDENCE.md).

## 8. End-of-session checks

After any online investigation:

1. Close Studio and confirm no `LogixDesigner` process remains.
2. Confirm no ACD/L5X or screenshot with proprietary content was created in the
   repository.
3. Re-run the fixed CIP identity probe with `--expect-serial 7036B510`.
4. Re-run the Linx command-line browse.
5. Record whether a TCP/44818 session existed and the exact Studio/SDK result.
6. State explicitly whether any download, write, mode change, fault clear,
   clock set, firmware operation, or controller configuration change occurred.

For the first 2026-08-13 acquisition/round-trip session all
controller-changing categories were **none**. In the later explicitly
authorized physical execution session, Studio changed Remote Run to Remote
Program, downloaded `FraktalPhase0`, returned to Remote Run, and the fixed tool
wrote and cleaned only fixture memory tags. The expanded fixture was then
verified/downloaded the same way, its transport budget was read-only tested, and
the fixed clock tool set only WallClockTime from host UTC. No firmware,
fault-clear, controller-network, or physical-I/O operation occurred. S2 later
downloaded the verified eight-level memory-only nested-AOI fixture,
returned the controller to Remote Run, exercised and cleaned only its command
and text inputs, and performed no clock change. S11 then downloaded the verified
sequence-execution fixture the same way, returned the controller to Remote Run,
drove two bounded runs plus one `SFR` reset, and cleaned both of its writable
inputs; no clock, firmware, fault-clear, controller-network, or physical-I/O
operation occurred. The controller remains in Remote Run with that clean S11
fixture and unsynchronized clock quality. S12 then downloaded the verified
type-map fixture the same way, returned the controller to Remote Run, measured
the CIP layout and type behavior, and restored every writable input; no clock,
firmware, fault-clear, controller-network or physical-I/O operation occurred.
The rollback location/hash are recorded in the physical execution evidence and
the current state in `AB_S12_TYPE_MAP_EVIDENCE.md`.
