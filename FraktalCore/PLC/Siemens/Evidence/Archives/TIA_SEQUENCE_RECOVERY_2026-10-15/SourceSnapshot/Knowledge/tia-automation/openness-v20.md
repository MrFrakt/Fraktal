# TIA Portal Openness V20 — working notes

## Prerequisites

| Requirement | Detail | Source |
|---|---|---|
| Group membership | The Windows account must be in local group **`Siemens TIA Openness`** (created by the Openness installer). Takes effect at the **next logon**. Without it: `EngineeringSecurityException: ... Owner '<PC>\<user>' of this process is not member of the windows group 'Siemens TIA Openness'`. | [help] topic "Adding users to the Siemens TIA Openness user group"; [measured] 2026-10-08 |
| Openness firewall | The help says it prompts when an app **attaches to a running TIA Portal**; **measured on V20: it also gates new headless instances** — an unknown exe hash fails with `EngineeringSecurityException: The operation has timed out` (`verified-gotchas.md`). Pre-approve via `HKLM\SOFTWARE\Siemens\Automation\Openness\20.0\Whitelist\<exe name>\Entry` with `Path`, `DateModified` (`yyyy/MM/dd HH:mm:ss.fff`, UTC last-write time) and `FileHash` (Base64 SHA-256 of the exe). Bound to the hash: re-whitelist after every rebuild. | [help] "TIA Portal Openness firewall" |
| Windows service use | Allowed with a dedicated account in the group; only headless new instances; LocalSystem always refused. | [help] "Using Windows Service" |
| Target framework | .NET Framework 4.8 (x64 recommended). Modern `dotnet` SDK can build `net48` with no Developer Pack (pulls `Microsoft.NETFramework.ReferenceAssemblies`). | [measured] |

## Loading the API

- Registry: `HKLM\SOFTWARE\Siemens\Automation\Openness\20.0\PublicAPI\<20.0.0.0>` → values
  `Siemens.Engineering`, `Siemens.Engineering.Hmi` = full DLL paths (also 17/18/19 API versions
  are installed under Portal V20 for compatibility). **[measured]**
- Reference `Siemens.Engineering.dll` with `Private=false` and resolve it at run time in
  `AppDomain.AssemblyResolve` from that registry path. `TiaPortal.GetProcesses()` works without
  group membership; `new TiaPortal(...)` is where the security check fires. **[measured]**

## API map (signatures verified in `Siemens.Engineering.xml`, V20)

| Task | Call |
|---|---|
| start / attach | `new TiaPortal(TiaPortalMode.WithoutUserInterface)`; `TiaPortal.GetProcesses()[i].Attach()` |
| project | `tia.Projects.Create(DirectoryInfo, string)`, `Open(FileInfo)`, `OpenWithUpgrade(FileInfo)`; `project.Save()`, `Close()` |
| add CPU | `project.Devices.CreateWithItem("OrderNumber:6ES7 214-1AG40-0XB0/V4.7", "PLC_1", "<station>")` |
| PLC software | `deviceItem.GetService<SoftwareContainer>().Software as PlcSoftware` |
| IP address | `deviceItem.GetService<NetworkInterface>().Nodes[i].SetAttribute("Address", "192.168.0.10")` (+ `"SubnetMask"`). **Pick the Ethernet node** (`NodeType`): on a CPU with a PROFIBUS port (1516-3 PN/DP) `Nodes[0]` of the first interface found was the PROFIBUS node, and the address went there **[measured]** |
| project properties | `project.GetType().GetProperties()` reflection, e.g. `IsSimulationDuringBlockCompilationEnabled` (bool; S7-PLCSIM refuses blocks compiled without it). There is no per-block switch: `PLCSimAdvancedSupport` is read-only **[measured]** |
| access levels (S7-1500) | `cpu.GetService<PlcAccessLevelProvider>().PlcProtectionAccessLevel` (`FullAccess` for a simulator; a new V3.0 CPU defaults to NoAccess). Not offered on the 1214C V4.7, which uses UMAC **[measured]** |
| create a block | `PlcBlockComposition.CreateFB(…, ProgrammingLanguage)` accepts **only ProDiag** in V20; for GRAPH, export a drawn chart and import generated XML **[measured]** |
| SCL source → blocks | `plc.ExternalSourceGroup.ExternalSources.CreateFromFile(name, path)` then `GenerateBlocksFromSource()` / `(GenerateBlockOption.KeepOnError)` / into a `PlcBlockUserGroup` or `PlcTypeUserGroup` |
| blocks → source | `plc.ExternalSourceGroup.GenerateSource(IEnumerable<IGenerateSource>, FileInfo[, GenerateOptions.WithDependencies])` |
| XML import/export | `PlcBlockComposition.Import(FileInfo, ImportOptions[, SWImportOptions])`; `ImportFromDocuments(DirectoryInfo, string, ImportDocumentOptions)`; `block.Export(FileInfo, ExportOptions.WithDefaults)`; types `plc.TypeGroup.Types.Import`; tag tables `plc.TagTableGroup.TagTables.Import` |
| compile | `plcSoftware.GetService<ICompilable>().Compile()` (software) or the CPU `DeviceItem`'s `ICompilable` (hardware + software) → `CompilerResult` {State, ErrorCount, WarningCount, Messages (recursive: Path, State, Description)} |
| connection | `deviceItem.GetService<DownloadProvider>().Configuration` → `Modes.Find("PN/IE")` → `PcInterfaces.Find(name, number)` → `TargetInterfaces.Find("1 X1")`; `ConfigurationPcInterface.GetAccessibleDevices()` |
| download | `DownloadProvider.Download(IConfiguration, pre, post, DownloadOptions.Hardware \| Software)` (also `SoftwareOnlyChanges`; overload with `ConfigurationAddress`; overload to a folder) → `DownloadResult` |
| online | `deviceItem.GetService<OnlineProvider>()`: `Configuration.ApplyConfiguration(targetInterface)`, `GoOnline()`, `GoOffline()`, `State` |

## Download questions (`DownloadConfiguration` subclasses, V20)

Selection questions (set `CurrentSelection` to an enum member): `StopModules` (StopAll),
`StartModules` (StartModule), `AlarmTextLibrariesDownload`, `AllBlocksDownload`,
`ConsistentBlocksDownload`, `DataBlockReinitialization`, `DifferentTargetConfiguration`,
`ExpandDownload`, `InitializeMemory`, `LoadIdentificationData`, `OverwriteOnMemoryCard`,
`OverwriteSystemData`, `ProtectionLevelChanged`, `ResetModule`, `SelectiveDeleteDownload`,
`StartBackupModules`, `StopHSystem(OrModule)`, `SwitchBackupToPrimary`, `TargetForSoftware`,
`WaitOnReboot`, `ActiveTestCanBeAborted/PreventDownload`, `UserManagementDownload`.

Check questions (`Checked = true/false`): `OverwriteTargetLanguages`, `CheckBeforeDownload`,
`UpgradeTargetDevice`, `DowngradeTargetDevice`, `FitHmiComponents`, `OverwriteHmiData`,
`ReplaceDownloadedData`, `TurnOffSequence`, `DownloadCertificate`, `DeleteWebApplication`,
`DownloadWebApplication`, `UpdateWebApplication`, **`AcceptDownloadOfUnencryptedSensitiveData`**
(security decision — answer only explicitly).

Password questions (`DownloadPasswordConfiguration.SetPassword(SecureString)`):
`ModuleReadAccessPassword`, `ModuleWriteAccessPassword`, `BlockBindingPassword`,
`PlcMasterSecretPassword`. Online: `OnlineAuthenticationConfiguration`
(`IsSecureCommunication`, `OnlineCredentials`), `OnlinePasswordConfiguration`. **[api]**

Practice: log every question with the offered selections and the answer; never
blanket-accept security questions; refuse a download unless the operator restates the
target address (as `Fraktal.Tia.Cli download --confirm-target` does).

## SCL external sources — syntax that matters

- One file may hold several `TYPE`/`FUNCTION`/`FUNCTION_BLOCK`/`DATA_BLOCK` units; import
  in dependency order (types → global DBs → FCs/FBs → instance DBs → OBs).
- Local tags are written `#name`, global `"name"`; block attribute
  `{ S7_Optimized_Access := 'TRUE' }`; member attributes
  `Name { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : Type;`
  (= "Accessible / Visible in HMI engineering / Writable from HMI/OPC UA").
- Instance DB: `DATA_BLOCK "Name" ... "FB_Type" BEGIN END_DATA_BLOCK`.
- Typed truncation `TRUNC_UDINT(lreal)`; `RUNTIME(memLReal)` returns seconds as LREAL;
  `RD_SYS_T(OUT => dtl)` returns Int status. **[help]**
- Optimized OB1 inputs: `Initial_Call : Bool` (first cycle after warm restart), `Remanence : Bool`.

## Catalog facts measured on this workstation (2026-10-09)

- `OrderNumber:6ES7 516-3AN02-0AB0/V3.0` does **not** exist in the V20 catalog;
  `6ES7 516-3AP03-0AB0/V3.0` (CPU 1516-3 PN/DP) does, and S7-PLCSIM Advanced 5.0
  (runtime 50.42.10.00) accepts it. **[measured]**
- `6ES7 214-1AG40-0XB0/V4.7` (CPU 1214C DC/DC/DC) is the bench. **[measured]**

## Download questions met in practice (beyond the S2 set in `verified-gotchas.md`)

- `ProtectionLevelChanged` appears on the first download that lowers protection. It is
  answered only by an explicit operator flag (`--accept-lower-protection`). **[measured]**
- `UserManagementDownload` (Keep / UpdateButKeepOnlinePassword / ResetToProject) appears
  once UMAC users exist. The plan must state the answer. **[measured]**
- `TurnOffSequence` appears for every GRAPH instance DB ("Turn off the sequence (FB …,
  DB …) before loading?"); the default `True` was kept. **[measured]**
- `TlsVerificationConfiguration` (on `ConnectionConfiguration.OnlineLegitimation`) is the
  certificate-trust question. Unanswered means not trusted. **[measured]**

## `Fraktal.Tia.Cli` — the command catalogue (source of truth: `Program.cs` usage text)

`C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools\TiaCli`. One command, or a plan file
(`plan <file> --set k=v`, `${k}` substitution, `?` prefix = record the failure and
continue) runs in one TIA session; every action is a JSON line on stdout.

| Area | Commands |
|---|---|
| project | `create-project`, `open-project`, `save`, `project-get`, `project-set` |
| hardware | `add-device --order "OrderNumber:…/V…"`, `set-ip` (Ethernet nodes only), `hw-attributes [--filter] [--probe a,b]`, `set-hw-attribute [--type]`, `cax-export` |
| services (reflection) | `service-get`, `service-set`, `service-call` (parameterless), `block-attribute` |
| security | `master-secret none\|protect`, `umac-user --list \| --anonymous \| --name … [--password-env \| --keep-password] [--role --rights] [--system-roles]`, `webserver-user` (`WebserverUserManagement`; that service is absent on the 1214C V4.7, which uses UMAC), `webserver-certificate` |
| program | `import-sources [--only prefixes] [--keep-on-error]`, `import-xml --kind block\|type\|tags`, `delete-blocks`, `list-blocks`, `set-block-number`, `create-block` (ProDiag only in V20) |
| build | `compile [--hw]` (software and hardware are separate gates), `export --out D [--scl]`, `interfaces [--scan]` |
| target | `download --confirm-target IP [--software-only \| --changes-only] [--user-management keep\|update\|reset] [--accept-lower-protection] [--accept-unencrypted-sensitive] [--plc-user U --plc-password-env V] [--trust-plc PLC] [--legacy]`, `online-state` |

`--changes-only` and `--keep-password` exist only in the candidate build awaiting
whitelist (2026-10-09). Check the build you run before using them.
