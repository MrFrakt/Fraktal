# Fraktal/AB engineering interface and tool catalog

**Inventory cutoff:** 2026-08-13 on `DESKTOP-07VCTIN`, revised after the
completed S11 run

This is the complete known interface inventory from the Allen-Bradley Phase 0
work completed through S2 and S11. It complements the
procedural
[`AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md`](AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md):
the runbook says how to operate the proved paths, while this document records
every interface and tool used, discovered, developed, rejected, or found
unavailable. A fresh agent shall use the status column and must not turn a
discovery into a conformance claim.

This inventory is not controller-change authority. Upload is controller-read-
only, but download, mode change, tag write, fault clear, clock set, firmware,
network configuration, safety operation, and SD-card operation require current
explicit authorization and an exact target check immediately before use.

## 1. Handoff state

| Item | State at cutoff |
|---|---|
| Controller | `1769-L24ER-QB1B/A` / `LOGIX5324ER`, firmware `33.014`, serial `7036B510` |
| Ethernet | PLC `192.168.100.89:44818`; host `Ethernet1` at `192.168.100.99/24` |
| USB | `USB\VID_14C0&PID_001F\7036B510`; Studio/FactoryTalk Linx virtual route `Backplane\16` |
| Controller project | clean memory-only S9 coherence fixture, Remote Run; `FRK_S9_Freeze` at zero and `FRK_S9_MutationPeriod` at its default 10; PTP disabled and unsynchronized |
| Studio | all `LogixDesigner` processes closed; the S9 download completed and the controller was returned to Remote Run |
| Readiness | R0-R3 PASS with S1, S2, S4, S7, S11 and S12 settled, the six logical contracts frozen and eight of nine capacities resolved; S8 and S9 have their postures decided and partly evidenced; R4-R6 OPEN; no production AB runtime authorized |
| Rollback ACD | `C:\Users\Rockwell Automation\Documents\Studio 5000\Projects\Fraktal_Rollback\FIS_Aptiv_Rev1_USB_upload_2026-08-13_serial_7036B510.ACD` |
| Rollback SHA-256 | `B3A1291ACDBFBD1A84C95354D550FB9A6FC6E908D766789508F8EFB2B83C8B60` |

The rollback ACD is intentionally outside the repository and may contain
proprietary controller source. Do not copy it, uploaded source, online values,
Studio screenshots, activation data, or credentials into version control.

Status terms used below:

- **Proved** means the interface produced recorded positive evidence on this
  workstation or exact physical target.
- **Exploratory** means it was inspected or exercised but is not a supported or
  sufficient evidence path.
- **Failed/limited** means a precisely identified path did not complete or does
  not prove the claimed property.
- **Discovered only** means installed material was found but not exercised.
- **Not installed** means it was checked and was unavailable at the cutoff.

## 2. Operating-system and physical interfaces

| Interface | Status | Access and result |
|---|---|---|
| Windows network inventory | **Proved, read-only** | `Get-NetAdapter`, `Get-NetIPAddress`, and `Test-NetConnection 192.168.100.89 -Port 44818` established the exact source adapter/address and TCP reachability. |
| Windows USB/PnP inventory | **Proved, read-only** | `Get-PnpDevice -PresentOnly` found the Rockwell USB CIP device by VID/PID and serial. USB presence must be rechecked after reconnect/reboot. |
| EtherNet/IP TCP port | **Proved** | TCP/44818 from `192.168.100.99` to `192.168.100.89`; used by the fixed CIP and symbolic probes. |
| Physical USB CIP | **Proved** | Studio v33 upload and authorized fixture downloads completed through the Rockwell USB virtual chassis route `Backplane\16`. |
| Integral controller Ethernet route | **Proved for browse/direct CIP; limited for Studio upload** | The L24ER is the endpoint: `Fraktal_AB\192.168.100.89`. Do not append a ControlLogix `Backplane\slot` suffix. |

The two paths intentionally look different. `Backplane\16` is the USB driver's
virtual chassis representation; it is not the Ethernet route to the integral
CompactLogix port.

## 3. FactoryTalk Linx interfaces

FactoryTalk Linx `6.50.00` is the supported communications server used here.
The global point-to-point display alias is `Fraktal_AB`; Linx reported internal
driver name `Ethernet 2`.

| Interface | Status | Scope |
|---|---|---|
| `FTLinxCfgIETool.exe` browse | **Proved, read-only** | Supported bounded browse of `Fraktal_AB\192.168.100.89`; writes its result to `%LOCALAPPDATA%\Temp\FTLinxCfgIETool_log_*.txt`. |
| `FTLinxCfgIETool.exe /AddDriver` | **Proved workstation configuration** | Created the global `PointToPoint` alias with `/DEVICEADDRESSES '192.168.100.89'`. Use only if missing; do not create duplicates. |
| FactoryTalk Linx topology in Studio Who Active | **Proved for reachability; failed/limited for project identity** | Exposed Ethernet and USB targets and correlated catalogue and serial. Its **project name is a cached discovery string**: during S11 the slot-16 node still read `FIS_Aptiv_Rev1` after an explicit refresh while the controller was demonstrably running the S2 fixture, and Studio's own pre-download dialog reported `FraktalPhase0`. Never treat the browse label as live project identity. |
| `BrowseServices` COM type library | **Exploratory, read-only** | From 32-bit PowerShell, a temporary `Interop.BrowseServices.dll` exposed `TopologyProvider`, `DriverProvider`, and `BrowseProvider`; calls used were `GetDriverList`, `GetTargetInfo`, `GetAdapterList`, `GetChildren`, and `GetTopologyNode`. Use the supported command-line tool for configuration. |
| RSLinx Classic | **Not selected/unsupported by Logix Designer SDK** | Do not substitute it for FactoryTalk Linx in SDK routes. |

Installed supported executable:

```text
C:\Program Files (x86)\Rockwell Software\RSLinx Enterprise\FTLinxCfgIETool.exe
```

The exact browse and add-driver commands are in the runbook.

## 4. Studio 5000 Logix Designer interfaces

| Interface | Status | Result |
|---|---|---|
| Studio v33 executable | **Proved** | `C:\Program Files (x86)\Rockwell Software\Studio 5000\Logix Designer\ENU\v33\Bin\LogixDesigner.Exe`; exact live firmware revision, manual Who Active, USB upload/download, and offline Verify Controller. |
| Studio v37 executable | **Proved offline only** | `C:\Program Files (x86)\Rockwell Software\Studio 5000\Logix Designer\ENU\v37\Bin\LogixDesigner.Exe`; SDK Build fixtures and negative semantic Verify. It was never used to download or upgrade the v33 controller. |
| Ethernet Who Active | **Proved connection; failed/limited upload** | Selected `Fraktal_AB\192.168.100.89` and matched identity. Upload reached late processing then failed `Error 731-0` / communications timeout and reverted the disposable ACD. |
| USB Who Active | **Proved** | Selected `16, 1769-L24ER-QB1B, FIS_Aptiv_Rev1` under USB; selected route `Backplane\16`; upload completed 0 errors/0 warnings. |
| Offline Verify Controller | **Proved semantic gate** | `Logic > Verify > Controller`; v33 positive project returned 0/0, while a deliberately invalid v37 ST body returned two errors. This is stronger than SDK `BuildAsync`. |
| Authorized USB download workflow | **Proved on disposable fixtures** | Visible pre-download identity correlation, Remote Run to Remote Program, download, and explicit return to Remote Run; used only under prior authorization with all I/O disconnected. |
| Studio UI Automation | **Proved but version-specific** | Used to inspect/control v33 dialogs and to package the offline Verify script. It is not a supported Rockwell API and never supplies authorization or target identity. |

### 4.1 UI Automation and Win32 details

PowerShell loaded `UIAutomationClient` and `UIAutomationTypes`. The following
v33 `AutomationId` values were observed:

| UI element | `AutomationId` |
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
| pre-download confirmation | `1` |
| post-download Remote Run prompt: Yes / No | `6` / `7` |

Native Studio buttons did not expose `InvokePattern`. The working diagnostic
path used `NativeWindowHandle` plus Win32 `BM_CLICK` (`0x00F5`). Focus/menu and
visual inspection used `WScript.Shell.AppActivate`,
`Microsoft.VisualBasic.Interaction.AppActivate`,
`System.Windows.Forms.SendKeys`, and
`System.Drawing.Graphics.CopyFromScreen`. The Verify menu sequence was
`Alt+L`, `v`, `c`. Screenshots were temporary corroboration; Error List counts
and detail text were the machine result.

Never invoke online buttons from a cached coordinate or control ID. Re-read the
visible route, controller type, project, serial, protection state, and requested
operation each time.

## 5. Logix Designer SDK interfaces

Installed material:

```text
C:\Users\Public\Documents\Studio 5000\Logix Designer SDK\dotnet\
C:\Users\Public\Documents\Studio 5000\Logix Designer SDK\dotnet\RockwellAutomation.LogixDesigner.CSClient.2.0.861.nupkg
C:\Program Files (x86)\Rockwell Software\Studio 5000\Logix Designer SDK\LdSdkServer.exe
```

`LdSdkService` was running with Automatic startup. The client must be 32-bit;
the proven target runtime is .NET 8 `win-x86`. A later x64 .NET SDK can build a
`win-x86` target, but it does not change the Rockwell client architecture.

| API/workflow | Status | Finding |
|---|---|---|
| `GetProcessorTypesAsync` | **Proved offline** | Enumerated available controller targets. |
| `CreateNewProjectAsync` | **Proved offline** | Created disposable projects. The repository offline probe now exposes it as `--create-seed`, so the empty v33 skeleton every generator consumes is reproducible from a clean checkout instead of being a hand-made temporary file. The scripted seed is canonically identical to the original hand-made one. |
| `OpenLogixProjectAsync` | **Proved offline** | Opened ACD, L5K, and L5X through repository tooling. |
| `ConvertAsync` / complete-project L5X import | **Proved offline, but not a type gate** | Converted generated complete L5X into a disposable ACD with import warnings/errors gated. S12 found it accepts an `LREAL` tag with `Warnings="0" Errors="0"` that Studio Verify then rejects as unsupported by the controller type; a clean import summary is necessary, never sufficient. |
| `BuildAsync` | **Proved but limited** | Works for v37 SDK evidence; unsupported for v33 physical-target projects in SDK 2.00 and does not detect all semantic ST errors. Never substitute it for Studio Verify. |
| `SaveAsync` and `SaveAsAsync` | **Proved offline** | Saved disposable ACD/L5X artifacts and supported canonical round trips. |
| `GetCommunicationsPathAsync` | **Proved but limited** | Called successfully, but SDK 2.00 returned empty after Studio saved the route in the disposable ACD. |
| `UploadToNewProjectAsync` | **Failed/limited online** | Studio-confirmed Ethernet route reached a communications timeout and created no ACD. USB Studio upload is the proved acquisition path. |
| Partial export/import examples | **Proved offline for S2 signature experiment** | Leaf AOI export plus optional/required signature variants imported with SDK warning/error summaries 0/0; Studio Verify determined compatibility. |

The repository `Fraktal.Ab.OfflineProbe` intentionally exposes only open,
saved-path read, and save-as/export operations. It contains no online, upload,
download, controller-mode, tag-write, fault, firmware, safety, or SD-card API.

### 5.1 Installed Rockwell SDK examples

All example folders discovered under the installed SDK are listed here so a
fresh agent can distinguish available reference code from exercised evidence:

```text
BuildProject
ChangeControllerMode
ChangeControllerType
ConvertProject
CreateDeploymentSdCard
CreateNewProject
DownloadProject
GenerateDeleteGetSafetySignature
GetCommPath
GetProcessorType
GetSafetyNetworkNumber
GetTagValue
GoOnlineOffline
LoadImageFromSDCard
LogixSDKDemoApp
LogixSDKDemoApp.Test
ManyAcdManyControllerDownload
OpenAndSaveFile
PartialExportOffline
PartialImportOffline
ProvisionAndValidate
ReadControllerMode
SafetyLockUnlock
SetCommPath
SetTagValue
SingleAcdManyControllerDownload
StoreImageOnSDCard
UploadProject
UploadToNewProject
```

The existence of an example is **discovered only**, not authority or proof.
Apart from the API/workflows explicitly marked proved above, the online/tag,
mode, download, safety, controller-type, provisioning, and SD-card examples
were not exercised for Fraktal evidence.

## 6. Direct EtherNet/IP and Python interfaces

The proven interpreter is
`C:\Users\Rockwell Automation\AppData\Local\Python\bin\python.exe`.

| Interface | Status | Exact surface |
|---|---|---|
| Raw Python socket EtherNet/IP | **Proved, read-only** | `ListIdentity`, `RegisterSession`, `UnregisterSession`, and CIP `Get_Attribute_Single` (`0x0E`) against TCP/IP Interface Object `0xF5` and Time Sync Object `0x43`, instance 1. |
| `pylogix==1.1.5` | **Proved and selected initial private adapter** | Hash-pinned temporary install. Used `PLC.Read`, fixed-fixture `Write`, `GetTagList`, `GetPLCTime`, and one authorized `SetPLCTime`. Connected fragmented reads/writes were handled internally. No arbitrary `Message()` forwarding is allowed. |
| `pycomm3==1.2.16` | **Exploratory/failed for this baseline** | Initial full tag initialization timed out; not selected and not positive evidence. |
| `libplctag` | **Considered only** | Potential future alternative; not exercised or target-proved. |

Pinned dependency authority:

```text
pylogix==1.1.5 --hash=sha256:6bf2ab0b4ebff4e5085717cb131efa48feb547d868c6176a47c3f50f7adab56e
```

The future gateway shall keep this adapter private, versioned, and allow-
listed. The HMI must not receive an arbitrary CIP service or write surface.

## 7. Repository-developed tool catalog

All paths below are under `FraktalCore/PLC/Allen-Bradley/tools/`.

| Tool | Controller access | Purpose and boundary |
|---|---|---|
| `Fraktal.Ab.OfflineProbe/` | None | 32-bit C# SDK host; opens ACD/L5K/L5X, reports saved path, saves a new ACD/L5X, refuses overwrite, and proves the input hash unchanged. |
| `fraktal_ab_eip_probe.py` | Read-only | Fixed identity, TCP/IP Interface, and Time Sync object probe; expected-serial guard and bounded samples/timeouts. |
| `fraktal_ab_symbolic_read_probe.py` | Read-only | Explicitly named scalar/array reads through pylogix; prints shape/status/timing and always redacts values. |
| `fraktal_ab_phase0_fixture.py` | None | Generates the exact disposable memory-only S1 fixture from a fresh v33 full-project L5X; refuses overwrite and physical-I/O operands. |
| `fraktal_ab_phase0_execute.py` | Fixed writes | Exact S1 fixture fingerprint, serial, and explicit-arm guard; writes only fixed `FRK_*` inputs and restores/verifies cleanup. Not valid against the current S2 fixture. |
| `fraktal_ab_transport_budget_probe.py` | Read-only | Exact expanded-S1 fingerprint; bounded connection-size, reconnect, timeout-recovery, and concurrency tests; closes clients and redacts values. |
| `fraktal_ab_time_probe.py` | Read-only by default; fixed clock set only with `--set-to-host` | Recognizes only exact S1/S2 fixture fingerprints; the mutating branch can call only `SetPLCTime(dst=0)` after serial/fixture checks. |
| `fraktal_ab_s2_fixture.py` | None | Generates the exact memory-only nested-AOI/InOut/access fixture with configurable bounded nesting; refuses unsafe source/output conditions. |
| `fraktal_ab_s2_execute.py` | Fixed writes | Exact S2 fingerprint, serial, and explicit-arm guard; writes only `FRK_S2_Ctx.Command` and `FRK_S2_Text`, then restores/verifies both. |
| `fraktal_ab_s2_inout_limit_fixture.py` | None | Offline-only 64/65 InOut compiler boundary generator. Never download merely to repeat compile evidence. |
| `fraktal_ab_s2_signature_variant.py` | None | Offline optional/required AOI signature-change generator used with partial import and Studio Verify. |
| `fraktal_ab_s11_fixture.py` | None | Generates the memory-only sequence-execution fixture: one graph declaration emits the ST reference-form sequence AOI, the owner and root module AOIs, the `FRK_Seq_Step` service, the native SFC chart and its JSR/SFR wrapper, and sets the three controller SFC settings. |
| `fraktal_ab_s12_type_probe.py` | None | Emits one minimal project per candidate Logix type, twice: `declare` alone and `declare`+one operation, so an import or Verify failure names exactly one type and distinguishes an unknown type from an uncompilable expression. |
| `fraktal_ab_s12_fixture.py` | None | Generates the memory-only type-map fixture from the accepted types only; `COP`s the public UDT and two adjacent instances into `SINT` arrays so member layout and padded stride are measurable. Asserts no division and no variable subscript before writing. |
| `fraktal_ab_s12_execute.py` | Fixed writes | Exact S12 fingerprint, serial and arm guard; measures UDT layout differentially with paired sentinels, plus round trip, overflow, NaN, string length, array edges and the duration range check; restores every input. |
| `fraktal_ab_security_probe.py` | Read-only | Fixed probe of exactly CIP classes `0x5D`/`0x5E`/`0x5F` for CIP Security capability; no arbitrary class/service input and no write path. On the Phase 0 controller all three returned `0x05`, a positive absence. |
| `fraktal_ab_access_audit.py` | None | Offline External Access allow-list audit for AB §11.2.1: declared mailbox tags shall be `Read/Write`, declared public tags `Read Only`, everything else `None`. Nothing is inferred from a name and an omitted attribute is not treated as `None`. |
| `fraktal_ab_s9_coherence_fixture.py` | None | Publishes a `DINT[1024]` payload whose every element carries the current generation plus a `DataRevision` token, with a range-checked writable mutation period, so snapshot tearing can be provoked and measured. |
| `fraktal_ab_s9_execute.py` | Two fixed writes | Proves the guard does not falsely reject a frozen controller, that unguarded reads genuinely tear, and that no accepted read is ever internally inconsistent; sweeps the mutation rate to measure whether retry-until-stable converges. Restores both inputs. |
| `fraktal_ab_s7_manifest_fixture.py` | None | Materialises the frozen manifest contract as a header UDT plus one array-of-UDT per table at parameterised capacities; refuses a declaration too large to download. |
| `fraktal_ab_s7_execute.py` | One fixed write | Read-only apart from `FRK_S7_BumpRevision`; measures cold read cost per connection size, per-table cost, header-poll cost, snapshot coherence across the read window, and revision-change detection; restores the input. |
| `fraktal_ab_s4_matrix_fixture.py` | None | Generates the representative construct matrix: PERIODIC and CONTINUOUS tasks with schedules, ST/RLL/SFC in one program, nested and tabular records, a `StringFamily` type, a `Constant` tag, and an AOI with all three scan routines. |
| `fraktal_ab_l5x_inventory.py` | None | Censuses data types, AOIs, tags, programs, routines, tasks and descriptions, and compares two documents. Answers whether a construct survived the **first** import, which the canonical comparator structurally cannot. Reports an absent attribute rather than assuming Studio's default. |
| `fraktal_ab_phase0_gate.py` | None | R4 regeneration gate: creates the seed, regenerates every fixture, imports each with a clean-summary requirement, and requires a canonical round trip, a construct census, and ID-independent chart equality. Studio Verify is opt-in because it needs a logged-in desktop. |
| `fraktal_ab_s11_execute.py` | Fixed writes | Exact S11 fingerprint, serial and arm guard; writes only `FRK_S11_Command` and `FRK_S11_ResetRequest`; drives one run plus one `SFR` re-entry run and restores/verifies both inputs. |
| `fraktal_ab_sfc_roundtrip_compare.py` | None | ID-independent SFC content comparison (steps, action qualifiers/bodies, transition conditions, branch type/flow, link topology, controller SFC settings). Answers the S4 chart question the canonical comparator structurally cannot; fails closed on an unresolvable branch. |
| `fraktal_ab_l5x_compare.py` | None | Strict full-project canonical comparison; excludes only Rockwell's three known timestamp fields and reports raw/canonical SHA-256. |
| `fraktal_ab_target_binding_compare.py` | None | Special exact-target comparison; after assertions, normalizes only the proved minor-revision, serial, local-module-minor, and three timestamp changes. |
| `fraktal_ab_sdk_log_gate.py` | None | Converts SDK console events into a machine result; requires named successes and can require import warnings/errors 0/0. |
| `fraktal_ab_studio_verify.ps1` | None/Studio offline only | Opens one disposable ACD, invokes Verify Controller through UI Automation, checks counts/details, closes without save, verifies unchanged hash, and refuses repo ACDs or an existing Studio session. |
| `requirements-phase0.txt` | None | Hash-pinned pylogix installation authority. |
| `test_fraktal_ab_*.py` | None | Unit tests for every Python/PowerShell-adjacent tool contract above. |

The fixed execution tools are deliberately not general clients. Their narrow
write surfaces, exact fixture fingerprints, serial checks, explicit arm flags,
and mandatory cleanup are safety properties; do not generalize them.

## 8. Offline artifact and evidence interfaces

| Interface | Status | Use |
|---|---|---|
| Full-project L5X serialization | **Proved** | Generate from an exact fresh source, SDK-convert to ACD, Studio Verify, SDK-export, then strict canonical comparison. Do not hand-author production L5X. |
| Target-binding comparison | **Proved** | Separates expected download stamps from real logic/structure drift; ordinary canonical comparison intentionally remains strict. |
| SDK event log gate | **Proved** | SDK exit code alone is insufficient; named operations and import summary are checked. |
| Studio Error List | **Proved semantic authority** | Accessed through visible Studio and UI Automation. Positive and negative fixtures established fail-closed behavior. |
| Partial AOI export/import | **Proved for S2 experiment** | Used only on disposable offline copies to test parameter-signature compatibility. |

Exact evidence and hashes are in
[`AB_S4_S15_OFFLINE_ROUNDTRIP_EVIDENCE.md`](Evidence/AB_S4_S15_OFFLINE_ROUNDTRIP_EVIDENCE.md),
[`AB_PHASE0_PHYSICAL_EXECUTION_EVIDENCE.md`](Evidence/AB_PHASE0_PHYSICAL_EXECUTION_EVIDENCE.md),
and [`AB_S2_AOI_PARAMETER_EVIDENCE.md`](Evidence/AB_S2_AOI_PARAMETER_EVIDENCE.md).

## 9. S11 SFC result

S11 is **complete and PASS**; see
[`AB_S11_SEQUENCE_EXECUTION_EVIDENCE.md`](Evidence/AB_S11_SEQUENCE_EXECUTION_EVIDENCE.md).
The interfaces it added or settled:

| Interface | Status | Result |
|---|---|---|
| Generated native SFC in L5X | **Proved** | A repository-generated chart imported at v33 with `Warnings="0" Errors="0"`, passed Studio v33 **Verify Controller** `0/0`, and survived repeated canonical export. Unlike the TwinCAT binding, machine-generated charts are a supported source form here. |
| SFC element ordering on export | **Proved** | Studio orders steps alphabetically by operand with actions interleaved, then transitions, then branches, then links sorted by source, assigning IDs sequentially. A generator that emits this order round-trips ID-for-ID. |
| Bare `SFC_STEP` / `SFC_ACTION` / transition tag declarations | **Proved** | Declared without `<Data>` blocks; Studio materialised the full tag structures on import. |
| Terminal step with no outgoing transition | **Proved** | Accepted with no error or warning, so no `Stop` element is required when Core owns the terminal state. |
| `SFR` / `JSR` from a generated ST wrapper | **Proved** | `SFR(<routine>,<step>)` and `JSR(<routine>,0)` round-tripped and executed; exactly one `SFR` per start/reset edge, `JSR` only while BUSY. |
| Studio download through UI Automation | **Proved, identity-gated** | Who Active tree item selection through `SelectionItemPattern`, selected-path pane `1335`, pre-download dialog panes `1016`/`1307`/`1304`/`1416`/`1439` for name/type/path/serial/security, confirm `1`, post-download Remote Run prompt `6`/`7`. Native buttons expose no `InvokePattern`; the confirm click must use `PostMessage` `BM_CLICK`, because `SendMessage` blocks until the modal it opens is dismissed. |

The download remains deliberately unpackaged as a repository tool.

The earlier exploratory checkpoint that preceded this run is retained below for
provenance only. Immediately before that wrap-up, Studio v33 was used offline to
add and export an empty, Studio-authored SFC routine named `FRK_S11_SfcSeed` in
program `FRK_S2Program` of a disposable copy. The export shape was:

```xml
<Routine Name="FRK_S11_SfcSeed" Type="SFC">
  <SFCContent SheetSize="Letter - 8.5 x 11 in"
              SheetOrientation="Landscape"/>
</Routine>
```

The temporary checkpoint was under
`%LOCALAPPDATA%\Temp\FraktalAbS11-2204a19a3a0543698a42404c7f6a8686`.
Recorded hashes were:

- exported empty-SFC L5X:
  `74E70EB2E5D74C16225614B39130A1B8040617212D54421DE1E0D0CF36DD875D`;
- disposable ACD after the seed:
  `AAC8949A8DE42ADAB3D2104FCAF973FE2506F78C9D9CD64038C6ABE754E8FAB9`.

These temporary files may no longer exist and are not evidence artifacts. The
editor was opened for exploration, no substantive SFC logic was retained, the
Studio process was closed, and nothing was downloaded.

Rockwell-authored serialization references discovered in the installed samples
are:

```text
C:\Users\Public\Documents\Studio 5000\Samples\SFC_GearChange.L5X
C:\Users\Public\Documents\Studio 5000\Samples\SFC_Motion_Example.L5X
C:\Users\Public\Documents\Studio 5000\Samples\Equipment_Phase_Sequencer.L5X
```

They are read-only syntax references, not Fraktal S11 evidence; they supplied
the serialization shapes the generator was written against, and every claim was
then re-established on generated artifacts.

## 10. Virtual-controller and rejected substitutions

| Product/path | Status | Decision |
|---|---|---|
| FactoryTalk Logix Echo and Echo SDK | **Not installed** | No Echo evidence is available on this workstation. |
| RSLogix Emulate 5000 | **Installed, not selected** | Versions through the installed v33-era product tree were found. It is not a substitute for the current CompactLogix/modern SDK/physical-target evidence. |
| Studio/firmware v37 upgrade | **Explicitly excluded** | v37 is offline tooling only; do not upgrade the physical controller for this work. |
| OPC UA on the physical PLC | **Not required/likely unavailable** | Default Fraktal/AB communication is EtherNet/IP explicit symbolic access through the future gateway. OPC UA remains an optional projection, not a gate prerequisite. |

## 11. Fresh-agent start sequence

1. Read `AGENTS.md`, this catalog, the workstation runbook, Part III, and the
   S1/S2/physical evidence before opening Rockwell software.
2. Inspect `git status`; preserve unrelated work and keep all ACDs, uploaded
   source, screenshots, and online values outside the repository.
3. Confirm no existing Studio process, then run the read-only Windows network,
   USB-presence, fixed CIP identity, and Linx browse checks.
4. Confirm the current controller project and the user's current authority.
   Prior authorization is historical and must not be inferred for a new change.
   Read the project from a direct symbolic read or Studio's pre-download
   dialog, never from the FactoryTalk Linx browse label (§3).
5. Prefer offline disposable fixtures and the repository's narrow tools. Use
   Studio v33 for exact-revision semantic Verify; never claim SDK Build alone as
   semantic verification.
6. Leave the clean S9 controller state untouched unless the next evidence task
   actually requires physical execution and fresh authorization is explicit.
7. At session end, close Studio, rerun identity/Linx read checks, and state every
   controller-changing category that occurred—or explicitly state none.

As of this inventory cutoff, the tables above contain every interface and tool
known from the completed Fraktal/AB workstation investigation. New discoveries
shall be added here with an explicit status before they are relied upon by a
fresh agent.
