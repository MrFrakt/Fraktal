# Fraktal/AB R1 — Platform Baseline Evidence

**Gate:** R1 platform baseline

**Result:** **PASS — named workstation, controller, licences, and routes proved**

**Date:** 2026-08-12–13

**Scope:** workstation discovery, read-only browse of the user-authorized
isolated controller over USB and EtherNet/IP, and offline opening/export of a
disposable copy of an existing ACD. No download, controller-mode change, fault
clear, firmware update, tag write, clock set, or controller-memory write was
performed. No activation identifier, credential, or controller key is recorded
here.

## 1. Decision

R1 passes. Studio 5000 v33 and FactoryTalk Linx browse the named isolated
CompactLogix target over USB. The Logix Designer SDK opens and exports the
matching disposable ACD copy. The Phase 0 gateway/engineering host now owns
`192.168.100.99/24`, reaches the controller directly at `192.168.100.89`, and
the EtherNet/IP identity at that address matches USB serial `7036B510`.

This closes only the platform baseline. It does not claim project/controller
parity, a canonical L5X round trip, Build/Verify, controller write behavior,
CIP Sync, runtime conformance, gateway security, or any complete S1–S15 spike.

## 2. Engineering workstation

| Item | Observed fact | Evidence |
|---|---|---|
| Role | Current Fraktal engineering workstation; machine name intentionally omitted from the repository | user-provided repository/workstation context |
| Operating system | Windows 10 Pro 21H2, build `19044.1889`, x64 | `HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion`; `PROCESSOR_ARCHITECTURE` |
| Processor architecture | AMD64 | `PROCESSOR_ARCHITECTURE` / `PROCESSOR_IDENTIFIER` |
| Gateway-host decision | this workstation is the Phase 0 engineering/gateway probe host; production deployment remains S8 work | user-authorized isolated test target and direct test interface |
| Python/runtime baseline | CPython `3.14.7`, installed under `C:\Users\Rockwell Automation\AppData\Local\Python`; the working launcher is `bin\python.exe` | `python --version`; AB gate/test execution |

The Windows instance exposes two VMware Intel 82574L interfaces. `Ethernet0`
is the ordinary `192.168.1.12/24` interface. The isolated PLC interface is
`Ethernet1`, index `12`, MAC `00-0C-29-A6-F1-8A`, `192.168.100.99/24`, link Up
at 1 Gbit/s, with no default gateway. Windows installs the direct
`192.168.100.0/24` route on that interface. The target resolves by ARP as
`192.168.100.89 -> E4-90-69-BE-EB-14`; no broad network scan was performed.
The final production zone/conduit and firewall policy remain S8 evidence, not
an R1 platform-acquisition blocker.

## 3. Studio 5000 Logix Designer

Installed Logix Designer major revisions were discovered from the registered
products and installation directories:

`21, 23, 24, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37`

The v31–v37 `LogixDesigner.exe` files report their matching major product
versions. The selected controller/project editor is Studio 5000 Logix Designer
`v33.00.00`; it opened the v33 ACD and browsed the v33 controller successfully.
The installed v37 executable reports `V37.00.00`; the installed v37
release-notes package reports `37.0.7116.0`. Controller firmware `33.014`
selects v33 for the live-project baseline; v37 remains the separate S15
offline Build-capable SDK candidate.

No `.ACD`, `.L5X`, or `.L5K` controller project exists in the repository. An
existing `FIS_Aptiv_Rev1.ACD` was found outside the repository under the user's
Studio 5000 Documents tree. A byte-for-byte disposable copy was opened offline
in Studio 5000 v33; the source was not edited. Its name and controller family
match the USB and Ethernet target. A later fresh Studio USB upload produced a
separate disposable ACD and completed an upload-derived canonical v33 round
trip, but it did not prove that this earlier stored ACD was equivalent to the
live controller. That comparison was not equivalent. A hand-authored L5X file
would not prove S4 or S15.

## 4. Logix Designer SDK

| Item | Observed fact |
|---|---|
| Installed product | Logix Designer SDK `2.00.00` |
| API/service binary | `LdSdkServer.exe` file version `2.0.861.0`, product version `2.00.861.0+150374706cb061f9075b9d0d5ac3471a92e5313c` |
| Windows service | `LdSdkService` / “Logix Designer SDK Service”, Running, Automatic |
| Local client artifacts | C# and C++ documentation/examples; C# NuGet package `RockwellAutomation.LogixDesigner.CSClient.2.0.861.nupkg` |
| SDK release-note date | September 2024 |

The installed Rockwell release notes state:

- SDK 2.00 supports Logix Designer projects v31 and later;
- the C# client is the recommended client;
- project Build and safety lock/unlock are supported only with Logix Designer
  v37 and later;
- FactoryTalk Linx is the supported communication software; RSLinx is not; and
- a Professional Edition licence or toolkit is required to activate the SDK.

FactoryTalk Activation Manager `5.01.01`, its activation services, FactoryTalk
Linx services, and the SDK service are installed/running. The SDK entitlement
was proved on 2026-08-13 by compiling Rockwell's supplied C#
`OpenAndSaveFile` example against the installed `2.0.861` package and using it
to open the disposable v33 ACD copy and export a new L5X. The operation reported
`Open project succeeded` and `SaveAsAsync succeeded`. The repository's
read-only `Fraktal.Ab.OfflineProbe` then repeated open, saved-path query, and
export while proving the input SHA-256 stayed
`678A813C9C307F1789810C2B32BDCB4E4FF265176B716C1BC59E0924C1FD236A`.

The saved communications path returned by the SDK was empty. A string inside
the application (`192.168.0.222`, described as an FIS server endpoint) is not a
controller-interface address and is not accepted as one. These offline exports
prove SDK activation and ACD→L5X conversion only; they do not prove a canonical
round trip, Verify/Build, project/controller parity, or live communications.
The successful SDK call proves a usable qualifying Professional Edition or
toolkit activation as required by the installed Rockwell SDK. The exact
entitlement identity is intentionally not copied into the repository.

## 5. Simulation and isolated execution

FactoryTalk Logix Echo and the Echo SDK were not found in installed-product
records or the standard Rockwell install roots. Studio 5000 Logix Emulate
(RSLogix Emulate 5000) is installed, including v35 and directories for several
earlier revisions. Emulate is not recorded as an R5 substitute: Part III names
Logix Echo/SDK or an explicitly isolated hardware CI target, and no evidence
here changes that gate.

The user explicitly authorized the physically isolated USB/Ethernet-connected
controller for this investigation. FactoryTalk Linx and Studio 5000 v33 proved:

| Item | Observed fact |
|---|---|
| Controller | CompactLogix 5370 L2, `1769-L24ER-QB1B/A` (`LOGIX5324ER`) |
| Project/controller name | `FIS_Aptiv_Rev1` |
| Firmware | `33.014` |
| Hardware revision | `1.001` |
| Serial number | `7036B510` |
| USB identity | Windows `USB\VID_14C0&PID_001F\7036B510`, Rockwell USB CIP driver |
| FactoryTalk Linx routes | USB browse reports `Backplane\16`; Ethernet point-to-point alias `Fraktal_AB` connects at `Fraktal_AB\192.168.100.89` |
| Read-only project upload | Studio v33 over USB completed with `0 error(s), 0 warning(s)`; saved only to a disposable local ACD |
| Offline semantic check | Studio v33 **Verify Controller** completed with `0 error(s), 0 warning(s)`; ACD hash unchanged after close without save |
| Embedded network | `A, EtherNet 2`; dual embedded Ethernet ports form one controller network interface |
| Local bus | `CompactBus, CompactLogix System`; controller at slot `00`, embedded discrete I/O at slot `01` |
| Controller health observed | Device Properties reported `Minor Recoverable Fault`; it was not cleared |

The live EtherNet/IP route is `Ethernet1` (`192.168.100.99/24`) directly to
`192.168.100.89:44818`. Ten read-only ListIdentity exchanges returned the same
model, firmware, and serial as USB, with 5.252 ms minimum, 15.973 ms median,
and 26.020 ms maximum elapsed time. TCP/IP Interface Object `0xF5`, instance 1,
reported address `192.168.100.89`, mask `255.255.255.0`, gateway and name
servers `0.0.0.0`, status `1`, configuration control `16`, and startup
configuration field `0` (stored configuration). The controller was in
`REMOTE RUN` during the later read-only symbolic probe.

Studio 5000's earlier stored recent path `Ethernet\192.168.0.202` is therefore
stale. An application value `192.168.0.222` is an FIS server endpoint, not the
controller address. Neither is accepted as route evidence. Studio 5000 v33
later connected through `Fraktal_AB\192.168.100.89` and matched the controller
identity, but its Ethernet read-only upload timed out near completion and
reverted its disposable ACD. SDK Ethernet upload also timed out and produced
no ACD. After USB was reconnected, Studio selected `Backplane\16` and completed
a read-only upload with zero errors and warnings. These results prove USB
upload and delimit the unresolved path to Ethernet/SDK rather than the project
generally. Reproducible access details are in
[`AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md`](../AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md).

## 6. Initial conformance scope

The current base scope remains the mandatory EtherNet/IP explicit-messaging
path through the Fraktal gateway. No optional OPC UA projection is requested or
claimed by this evidence. Connectors, motion, safety profiles, and optional
industry projections remain governed by their own Part III spikes.

## 7. Commands and local primary evidence

Read-only discovery used:

```powershell
git status --short --branch
git log -5 --date=iso-strict --pretty=format:'%h%x09%ad%x09%s'
Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*
Get-ItemProperty HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*
Get-Service | Where-Object { $_.DisplayName -match 'Rockwell|FactoryTalk|Logix|RSLinx' }
Get-ChildItem 'C:\Program Files (x86)\Rockwell Software\Studio 5000\Logix Designer\ENU'
Get-Item 'C:\Program Files (x86)\Rockwell Software\Studio 5000\Logix Designer\ENU\v37\Bin\LogixDesigner.exe'
Get-Item 'C:\Program Files (x86)\Rockwell Software\Studio 5000\Logix Designer SDK\LdSdkServer.exe'
Get-ChildItem 'C:\Users\Public\Documents\Studio 5000\Logix Designer SDK'
pnputil /enum-devices /connected
ipconfig /all
Get-NetAdapter
Get-NetIPAddress -AddressFamily IPv4
Test-NetConnection -ComputerName 192.168.100.89 -Port 44818 -InformationLevel Detailed
arp -a 192.168.100.89
FactoryTalk Linx Network Browser (USB browse and Device Properties)
Studio 5000 Logix Designer v33 (Who Active and successful read-only upload over USB; offline ACD-copy open)
C:\Users\Rockwell Automation\AppData\Local\Python\bin\python.exe tools/check_ab_spec.py
C:\Users\Rockwell Automation\AppData\Local\Python\bin\python.exe -m unittest tools.test_check_ab_spec
dotnet build Rockwell's installed OpenAndSaveFile.csproj
dotnet OpenAndSaveFile.dll <disposable-copy.ACD> <new-temporary-export.L5X>
dotnet Fraktal.Ab.OfflineProbe.dll <disposable-copy.ACD> --export <new-temporary-export.L5X>
python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_eip_probe.py 192.168.100.89 --samples 10 --expect-serial 7036B510
python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_symbolic_read_probe.py 192.168.100.89 <redacted read cases>
```

Primary local product evidence:

- installed *Logix Designer SDK Release Notes*, September 2024, version
  2.00.00;
- installed SDK C# documentation/examples and NuGet package; and
- Windows installed-product, file-version, and service records.

## 8. R1 exit and next gate

R1's required controller catalogue, firmware, Studio version/licence,
communication interface/route, and Phase 0 gateway-host baseline are all named
and exercised. R1 is PASS.

The next work at R1 acceptance was R2 executable-shape evidence. S1's controlled
write, time, and limit cases subsequently passed in
[`AB_S1_CIP_DATA_PATH_EVIDENCE.md`](AB_S1_CIP_DATA_PATH_EVIDENCE.md). S2's AOI
parameter/access fixture also subsequently passed in
[`AB_S2_AOI_PARAMETER_EVIDENCE.md`](AB_S2_AOI_PARAMETER_EVIDENCE.md); the current
next blocker is S11 execution-form behavior, followed by S4/S15's
representative construct/end-to-end automation evidence and S12.
Production zone/conduit and firewall ownership remain S8. No download is
authorized by this evidence record; any later controller write must use a named
disposable test tag and preserve the isolated-target evidence.
