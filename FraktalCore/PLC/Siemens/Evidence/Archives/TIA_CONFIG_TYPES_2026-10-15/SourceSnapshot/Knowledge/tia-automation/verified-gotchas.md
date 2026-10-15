# TIA V20 / S7-1200 V4.7 — verified gotchas (measured 2026-10-08)

For the2026-10-10 reference1500 generator, see
[generated frames and registry](generated-frames-and-registry.md): empty optional
IF bodies fail compilation, native source reorders parameter sections, and
VAR_IN_OUT attributes are dropped. Compare native interface/code and actual
private-path exclusion; do not assume an accepted source attribute survived.

Every item below was hit on the real bench (CPU 1214C V4.7.3, TIA Portal V20,
Openness V20) while building the Fraktal/TIA S2 fixture. Evidence and raw logs:
`C:\Projects\Fraktal\Specification\Siemens\Evidence\TIA_S2_S15_FIRST_BENCH_RUN_2026-10-08.md`.

## Openness access

| Symptom | Cause | Fix |
|---|---|---|
| `EngineeringSecurityException ... not member of the windows group 'Siemens TIA Openness'` | account not in the group | add it (admin), then **log off/on** — the running session's token does not change |
| `EngineeringSecurityException: Security error. The operation has timed out` | the Openness **firewall** applies to *new headless instances* too, keyed by the exe's SHA-256; a rebuilt exe is unknown, TIA waits for a prompt nobody answers | whitelist the exact build: `HKLM\SOFTWARE\Siemens\Automation\Openness\20.0\Whitelist\<exe>\Entry` (`Path`, `DateModified` UTC `yyyy/MM/dd HH:mm:ss.fff`, `FileHash` Base64 SHA-256) — elevated; redo after every rebuild |
| `FileNotFoundException: Siemens.Engineering, Version=20.0.0.0` at start | `Main` named a Siemens type, so the JIT loaded the API before the `AssemblyResolve` handler was registered | keep `Main` free of Siemens types; put API use in other methods |
| `GenerateBlocksFromSource` throws with no useful text | `EngineeringException.DetailMessageData` is **empty** for source-generation errors | bisect by splitting sources one block/type per file |

## SCL external sources

- **`Name` as a member name is silently dropped** in a source declaration (`NAME` is a
  block-header keyword). The UDT compiles as "A structure without components is not
  allowed" and every user breaks. Declare it quoted: `"Name" : String[80];` (TIA's own
  regenerated source does the same). Code can still write `#Status.Name`.
- A **multi-TYPE `.udt` with comments before the first `TYPE`** failed generation;
  one `TYPE` per file with nothing before the keyword works.
- **BOM-less sources are read as ANSI**: UTF-8 `—`/`§` in comments are stored
  double-encoded (`â€”`/`Â§`). Keep sources ASCII (BOM untested).
- FC `String` parameters: **no length** (`Description : String;`) — "Please remove the
  length specification".
- Identifiers are **case-insensitive**: a `VAR CONSTANT BUSY` and a parameter `Busy` in
  one block collide ("A constant is not permitted here", odd type errors).
- `dt` is reserved (the `DT` type) — "Tag #dt not defined".
- `GetInstancePath`: call as **`#w := GetInstancePath(SIZE := 0);`** (the help's `OUT =>`
  form is rejected); it returns `"IDB".Inst.Sub` and pulls the system blocks
  `GetSymbolPath` + `SymbolInformation*` into the image. Call once, not cyclically.
- `TSEND_C.COM_RST` is **InOut** — pass a variable, not `FALSE` ("Invalid parameter
  assignment").
- An FB that **reads its own output** gets "The parameter '#X' might not be
  initialized"; an FB that **writes its own input** gets "you do not access the operand
  that was transferred". Use statics for records the block both reads and writes;
  have helper FCs return results as FC outputs (`Busy => #Busy`).
- Other blocks may read/write a multi-instance's inputs and read its outputs and
  statics through the instance DB path (`"Unit".CylA.Execute := TRUE`, `"Unit".Seq.TraceCount`).
- Parameter instances work on S7-1200: `VAR_IN_OUT CylA : "FB_Cyl";`, called with
  `#Seq(CylA := #CylA)`; the callee may write the instance's inputs.
- `RUNTIME(memLReal)` returns seconds; `TRUNC_UDINT(lreal)` truncates; `RD_SYS_T(OUT => dtl)`.

## Hardware and security (V20 defaults for a new 1214C V4.7)

| Item | Default | Openness handle | Note |
|---|---|---|---|
| Protection of confidential PLC configuration data | enabled, no password → **HW compile error** "Password for confidential PLC configuration data is not configured" + "communication certificate cannot be configured" | `cpu.GetService<PlcMasterSecretConfigurator>()`: `Protect(SecureString)` / `Unprotect()`; `MasterSecretConfiguration` None/WithPassword/WithoutPassword | |
| Access control (UMAC) | `EnabledWithAccessControl` → HW compile error "At least one user must have the runtime right: Full access" | `PlcAccessControlConfigurationProvider.PlcAccessControlConfiguration` (`Disabled` = classic access levels) | `PlcAccessLevelProvider` is **not offered** by the 1214C |
| PG/PC + HMI communication | **secure only** (TLS) with a project-generated certificate | CPU attribute `CommunicationMode` (UInt32, default 1), `PlcCommunicationCertificate` | |
| PUT/GET | off | `ProtectionEnablePutGetCommunication` → **EngineeringNotSupportedException on S7-1200** | documented for S7-1500 only |
| OPC UA server | off | device item `OPC UA`: `OpcUaServer` (bool), `OpcUaExportArrayMembers`, `OpcUaServerCertificate` | runtime licence "Basic" |
| Web server | off | CPU attribute `WebserverActivate` — the **only** web switch on a 1214C V4.7: `WebserverHttpsOnly` and the interface's `UseWebServerForInterface` throw `EngineeringNotSupportedException` | measured 2026-10-08 |
| Web server certificate | none; the TIA editor makes one when you tick the web server, **Openness does not** | `LocalCertificateManager` (device-item service) → `LocalCertificateStore.GetCertificateTemplate(CertificateUsage.WebServer)` → `Certificates.Create(t)` → `cpu.SetAttribute("WebserverCertificate", cert)` | `WebserverCertificate` is **not listed** by `GetAttributeInfos()` but `GetAttribute`/`SetAttribute` work — a missing name in an attribute dump does not mean unsupported |
| Web users | there is **no** `WebserverUserManagement` service on a 1214C V4.7 | web users are UMAC project users: `UmacConfigurator.ProjectUsers.Create(name, SecureString)`, `CustomRoles.Create(name, comment)`, `role.AssignDeviceFunctionRight(UmacDevice, right)`, `user.Roles.Add(role)`; access control `EnabledWithAccessControlViaAccessLevel` keeps PG/HMI on access levels | the download then asks `UserManagementDownload` (Keep / UpdateButKeepOnlinePassword / ResetToProject) — answer it explicitly |

## Download / online (the lockout and the recovery)

- After the first download, the CPU holds **this project's** communication certificate and
  accepts only secure PG/PC communication. **Recreating the TIA project generates a new
  certificate** → the next connect fails with "Connect to module PLC_1 failed" (download)
  or "Changing to online mode failed" (go online), for TLS **and** legacy. Keep one
  persistent project per station; regenerate only the program inside it.
- `ConnectionConfiguration.EnableLegacyCommunication = true` connects to a CPU that still
  allows legacy communication (e.g. one of unknown history before your first download).
- The TLS trust question arrives as **`TlsVerificationConfiguration`** on the event
  **`ConnectionConfiguration.OnlineLegitimation`** (`PlcName`, `VerificationInfo` e.g.
  "certificate not matching", `CurrentSelection` NonVerified/Trusted/NonTrusted). Unanswered
  = not trusted. Set `Trusted` to recover (trust on first use, log it).
- Subscribing to `OnlineLegitimation` **twice in one TIA session throws**
  ("Error when calling method 'Subscribe'"); unsubscribe after each operation.
- After a successful hardware download the CPU restarts; an immediate GoOnline may fail —
  wait a few seconds.
- TIA dialogs come through `TiaPortal.Confirmation` / `TiaPortal.Notification` events.
- The TIA download question set seen on this bench: `StopModules`, `OverwriteSystemData`,
  `ConsistentBlocksDownload`, `UserManagementDownload` ("...not available" / "...changed
  password for confidential configuration data"), `AlarmTextLibrariesDownload`,
  `StartModules`.

## Getting results out of a test program without licences

`PUT/GET` is not settable through Openness on S7-1200 and the OPC UA server needs a licence.
A test image can serve its own results: passive OUC TCP (`TSEND_C`, `TCON_IP_v4`,
`InterfaceId := "Local~PROFINET_interface_1"`, `ConnectionType := 16#0B`,
`ActiveEstablished := FALSE`, `LocalPort := 2000`) sending a non-optimized struct every
500 ms; the host connects and reads one record (`s7_probe.py harvest --tcp 2000`).

## Web server on a 1214C V4.7 through Openness (measured 2026-10-08)

| Symptom | Cause | Fix |
|---|---|---|
| HW compile: "No certificate type is assigned to the Web server security." | S7-1200 needs a certificate *type*: internal enum `WebserverCertificateType` (`Siemens.Simatic.HwConfiguration.BusinessLogic.Acf.Devices.WebServer`, in `Hwcn.IntItf.dll`): 0 NoneSelected, 1 HardwareGenerated, 2 SoftwareDownloaded | **Not reachable by Openness V20**: `GetAttribute` → "get_WebserverCertificateType is not supported", `SetAttribute` → "set_… is not supported". Set it once in the editor (PLC > Properties > Web server > Security) and keep the project |
| HW compile: "If access control via access level is enabled and a higher access level (= access without login) than full access … the password for full access must be set." | `EnabledWithAccessControlViaAccessLevel` with the anonymous user inactive = no access without login | bench: `UmacConfigurator.ActivateAnonymousUser()` + system role `PLCAdministrator` (warning "Anonymous has Full access … testing only"); production: set the full-access password |
| `umac.AnonymousUser` is **null** | it does not exist until activated once | call `ActivateAnonymousUser()` first |
| Web-related attributes missing from `GetAttributeInfos()` | listed only once `WebserverActivate = true` (then `WebserverCertificate`, `WebserverDefaultHTMLPage`, `WebserverHTMLDirectory` appear) | switch it on, then dump |
| Need an attribute's real name | internal names live in `Portal V20\Bin\Siemens.Simatic.Hwcn.*.dll`; `Assembly.ReflectionOnlyLoadFrom` + enum dump finds enums and values without running TIA code; a name Openness knows fails with "get_X/set_X is not supported", an unknown one with "'X' is not supported" | probe by name before concluding |
| CAx (AML) export as a discovery tool | carries addresses, channels, IP — **no** security, UMAC or web settings | not useful for security settings |

Device function rights offered (UMAC, 1214C V4.7): access levels `ProtectionLevelHMIAccess/ReadAccess/FullAccess`; `OPCUAServerAccess`; web: `WebReadTags` ("Read process data"), `WebWriteTags`, `WebReadWatchTables`, `WebWriteWatchTables`, `WebAllowDiagnostics`, `WebReadSyslog`, `WebFlashLED`, `WebChangeOperatingMode`, `WebChangeDefaultWebPage`, `WebPerformFirmwareUpdate`, `WebChangeTimeSetting`, `WebCreateBackupPLC`, `WebRestorePLCBackupFile`, `WebOpenUserDefinedWebPages`, `WebWriteUserDefinedWebPages`, `WebReadFiles`, `WebWriteFiles`. `UmacConfigurator` is a **project** service, `UmacDevice` a **device** service.

## Memory and scan cost on a 1214C V4.7 (measured 2026-10-08)

| Question | Answer |
|---|---|
| Where is the CPU's memory use? | **Only** on the system web page `Diagnostics > Memory` (`/Portal/Portal.mwsl?PriNav=Online&SecNav=Memory`) for a user with `WebAllowDiagnostics`. Openness has no block size attribute; SZL `0x0013/0x0113/0x0B13` are refused; the Web API has no memory method. |
| Logging in to the system pages by script | `POST /FormLogin` (`Redirection`, `Login`, `Password`) **with** `Origin` and `Referer` of the page, else HTTP 400; success = 302 + `siemens_ad_session` cookie. A refused login is also a 302, without the cookie. |
| Session trap | Legacy-page sessions do not end with TCP closure. Earlier scripts hit a roughly30min native login limit while Web API still worked; downloads did not clear it. The old `GET /FormLogin?LOGOUT` advice proved only connection closure. **2026-10-10 correction:** the old cookie still reads protected memory after both measured GET header forms. Reuse one session across a series, clear local credentials and let native sessions expire; see the S3 follow-up. |
| Work memory per module | A minimal Fraktal CM instance (status strings, HAL struct, call) ≈ 1.16 KB work memory; the S2 framework image ≈ 19.7 KB of 150 KB. |
| Idle module cost | An idle CM (FB + `FRK_Begin`/`FRK_End` FCs) costs ≈ 0.20 ms/scan; the bare FB call with the same interface ≈ 0.04 ms; a loop-indexed array of FB instances ≈ +0.03 ms per call. A quiescent guard around the lifecycle brings an idle CM to ≈ 0.053 ms. |
| Arrays of multi-instances | `Array[1..N] of "FB_X"` as statics and `#Cyl[#i](...)` compile and run on S7-1200 V4.7. |

## Source export

`GenerateSource` writes **UTF-8 with BOM**; with ASCII-only input sources every exported
file is BOM + pure ASCII (measured on 41 files, 2026-10-08). Compare exports after
stripping the BOM.

## S11 continuation (2026-10-09)

Evidence: `C:\Projects\Fraktal\Specification\Siemens\Evidence\TIA_S11_SEMANTICS_2026-10-09.md`.

| Symptom | Cause and measured answer |
|---|---|
| Named OB refuses Number=100 | Its event class is ProgramCycle. Absolute SCL header `ORGANIZATION_BLOCK OB100` generates Startup (export verifies SecondaryType). Absolute OB121 generates ProgrammingError on 1500. **[measured]** |
| Hardware compile 0/0 but SCL exports are inconsistent | `compile --hw` checks hardware; it is not the software gate. Run both commands separately. **[measured]** |
| Invalid array index does not stop execution | GET_ERR_ID in the offending FC activates local handling: index 99 into [0..1] returns 16#2522 and zero, following statement executes. On 1500 it bypasses OB121. Without it, OB121 records 16#22 / Reaction=1 and execution continues with zero. Consume/latch the error. **[measured]** |
| MaximumStepTime exceeded but GRAPH has no ERR_FLT | An empty V/C network does no monitoring: native T=499–500 ms, T_MAX=100 ms, no error. An explicit supervision does latch when acknowledgement is required. **[measured]** |
| Intermediate GRAPH steps absent from Core history | SkipSteps TRUE skipped N100/N200 with TRUE exits. Keep false for Fraktal. **[measured]** |
| S7comm SZL works but STOP request fails | This 1214C V4.7.3 refused classic control with 16#8104; it remained RUN. Authenticated native web STOP/RUN subsequently passed using the actual Start-page POST forms and a temporary WebChangeOperatingMode right, with identity/exact-target guards. **[measured]** |
| `umac-user` role-only update fails: password already used | The original driver calls SetPassword on an existing user; UMAC rejects the unchanged password. `--keep-password` requires an existing user and is mutually exclusive with `--password-env`; the owner-whitelisted candidate granted the temporary role right and downloaded 0/0 while keeping passwords. **[measured]** |
| ConvertTo-SecureString says wrong format on a DPAPI file | Trim trailing whitespace from the encrypted hex text first. Never print its plaintext or pass it as an argument. **[measured]** |
| NonRecoverableException / disposed TIA objects after import or GoOnline | Windows commit exhausted on the 4 GB workstation (12 GB page file); event log names TIA, PLCSIM and the help service. Power off the owned simulator for offline builds; retain failures. **[measured]** |

Owner-whitelisted candidate: `C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools\TiaCli\bin\candidate_s11\Fraktal.Tia.Cli.exe`,
Base64 SHA-256 `4e9MOBqor869GuopfT52OXsrliXn/5n+IviIq7tSAAM=`; adds `--changes-only`
(SoftwareOnlyChanges) and `--keep-password`. **[api]** SoftwareOnlyChanges is the
documented delta option. **[measured]** Grant and two code-only downloads passed
0/0. The original Release/net48 and candidate_s11 bytes are unchanged.

## S11 native restart and code-only delta (2026-10-09)

Evidence: `C:\Projects\Fraktal\Specification\Siemens\Evidence\TIA_S11_NATIVE_2026-10-09.md`.

| Symptom / question | Measured answer |
|---|---|
| Native STOP POST succeeds but decoder says unknown mode | This 1214C's SZL 0x0424 state byte was 3 in STOP (native page confirmed); state 6 is transient startup and 8 RUN. Decoder accepts 3/4 STOP, observes 6 startup and refuses mutations until stable. Do not replay the already sent POST after observation failure. **[measured]** |
| Can a code-only change download while RUN without DB reinit? | Two SoftwareOnlyChanges downloads loaded only S11SclCycle, 0/0, no stop/start/reinit questions. Marker 1101→1102 preserved sentinel 21265, OB100 stamp and mailbox sequence/ack1005; DB counter 218993→320559, scans increased, 19/19. Idle SCL fixture and unchanged DB interface only; GRAPH, active commands and type growth remain unmeasured. **[measured]** |
| UMAC restore throws NullReferenceException before save/download | V20 GetAssignedDeviceFunctionRights returns an IList that enumerates two valid rights but ToList produces one null entry (same collection, API count2 / enumerated2 / copied null1). Direct foreach into identifier sets fixes the restore; verified exact final rights and compile/download0/0. Role lookup/removal were earlier incorrect attributions. Scope: this V20 collection, not all Openness lists. **[measured]** |
| Python HTTPS reconnect or request retry loses trust/outcome boundary | Pin every reconnect; retry once only for explicit read-only methods. Lost writes/login/password-change/mixed batch responses have unknown outcome and are never replayed. Four fault tests and a live read snapshot pass; this does not close the full S9 recovery gate. **[measured]** |
| CPU timestamps look decades old | Bench DTL reports 2012-01-05; host is 2026-10-09. Compare OB100 stamps within the CPU only; no clock correction or synchronization was performed. **[measured]** |

Current owner-whitelisted driver:
`TiaCli/bin/candidate_s11_enumeration/Fraktal.Tia.Cli.exe`, Base64 SHA-256
`5FXuk+YWxHiAAbB4MBZNqSty44F9apDJDgPZiTcCbzM=`. Build and restore/download 0/0.
**Cleanup PASS:** diagnostics role now exactly WebAllowDiagnostics; gateway role
still WebReadTags|WebWriteTags; both existing passwords authenticate; native
diagnostics page offers no mode forms; CPU RUN and19/19. Never overwrite this
driver or earlier approved candidates. Frozen failures are superseded by
`TIA_S11_ENUMERATION_2026-10-09.md`, which compares both collection paths.
API source for role identifier lookup (not the cause on this station):
[Siemens V20 custom roles](https://docs.tia.siemens.cloud/r/en-us/v20/tia-portal-openness-api-for-automation-of-engineering-workflows/tia-portal-openness-api/functions-for-accessing-data-of-the-user-management/functions-for-accessing-user-roles-and-function-rights/custom-roles).

## S9 read sessions and batch coherence (2026-10-09)

Evidence: `TIA_S9_READ_SESSIONS_2026-10-09.md` in Fraktal's Siemens Evidence folder.

- Two clients with distinct tokens read concurrently, ten reads each. Closing
  a local socket then reading on a fresh pinned connection preserves the token.
  Logging client A out yields code **2 Permission denied** on protected reads;
  explicit new login succeeds, and client B still reads. **[measured]**
- Natural idle test: no API activity for 160.010 s; the next protected read
  returned code 2 at 163.114 s including new TLS setup. Explicit new login
  succeeded. No CPU/UMAC change occurred during that interval. This establishes
  invalidation by that duration, not the exact expiry threshold. A retained read
  client also crossed native STOP→RUN with the **same token**; its counter froze
  in STOP, then rebuilt/increased in RUN; 19/19. Cable pull, retained-client
  download and end-to-end HMI freshness remain open. **[measured]**
- **One JSON-RPC batch is not one PLC scan on 1214C V4.7.3.** Ten batches each
  read the same cyclic counter sixteen times; all contained different values
  spanning 106–111 increments. Keep HMI snapshots eventually consistent;
  batch transport is not an atomic snapshot guarantee. **[measured]**

## S3 Unit guard and optimized contract storage (2026-10-10)

**Scope correction (owner,2026-10-10):** all150KB budgets, timing and compact
capacities in this section belong to the physical1214C compatibility bench.
The full implementation target is the simulated S7-1500, including GRAPH. Its
work proceeds with its own CPU limits and Core capacities;1200 fit does not gate
the reference runtime or full press.

Evidence: `C:\Projects\Fraktal\Specification\Siemens\Evidence\TIA_S3_BUDGET_2026-10-10.md`.

| Question | Measured answer |
|---|---|
| What can an idle Unit skip? | S2 computes its RunReq/AbortReq lifecycle predicate after the mailbox and fences begin/hooks/end only. Five Units plus ten CMs passed19/19 with both frames; cycle3.452→2.443ms, about0.202ms/idle Unit, +0.06KB work. Children, scan-result clear and mirrors stay unconditional. Full mode hooks remain unproven. **[measured]** |
| Can string-length sums set the 1200 budget? | Use the native page's optimized allocation and exported complete fields/counts. Added KB, wide→compact: status/state47.03→22.84; alarms75.57→12.41; sequence48.57→21.77; config48.07→19.42. EnumsDInt, DT→DTL and pointer→UDInt index are explicit allocation mappings. **[measured]** |
| Do compact write rows fit a 2.5KB module? | Eight `ST_ConfigWriteDef` rows alone add5.49KB. Share immutable metadata by type and allocate only consumed instance-dependent state; do not copy TC3's per-instance maximum array. These are storage measurements, not a working writer. **[measured]** |
| Does the complete press fit? | Combined compact tables plus spike code use96.89/150KB, leaving53.11KB. This excludes additional runtime/press algorithms and full published-surface cost. Candidate capacities remain provisional; reserve at least15KB. **[measured]** |
| Why is a 302 form response insufficient? | Sequence-compact native login returned302 without a session cookie; retries failed while the PLC passed19/19 and the unchanged diagnostics password authenticated through Web API. Access recovered at00:43:10UTC, about30.5min after the first successful series login. **[measured]** |

Reuse one native-page session across an image series. Standalone measurements
still hit the session limit despite `NativePage.close` logout attempts; the
remaining series retained one cookie across downloads. Corrected probes showed
the old cookie still read protected memory after ordinary and cookie-only GET
logout. An earlier raw-HTML matcher falsely reported revocation; its record is
retained and superseded. `close` now clears local credentials/socket even on
logout failure (two fault/cleanup tests); it does not claim server revocation.
Retry only the failed read measurement, never its completed
download. Preserve these failed reads as evidence. Exact candidate maps and
capacities live in Fraktal's `Spikes/S3_Budget/make_fixture.py` (one source).
Width gates must cover encoded values/domain lists/persistence pieces as well as
paths and keys; the candidate80-character ValueText must never truncate a value.

## S11 active recovery on simulated S7-1500 (2026-10-10)

Evidence: `C:\Projects\Fraktal\Specification\Siemens\Evidence\TIA_S11_GRAPH_RECOVERY_2026-10-10.md`.
Scope: CPU1516-3 V3.0, PLCSIM Advanced5.0, Softbus. **[measured]**

- **SoftwareOnlyChanges does not guarantee GRAPH state preservation.** A label-only
  GRAPH body change with identical exported DB interfaces requested native sequence
  turn-off and DB reinitialization. FC marker delta preserved observed BUSY/step/DB
  state without those questions. GRAPH preservation gate stays unpassed; quiesce
  the owner and withdraw outputs before accepting native reinitialization.
- **Output permits must still run in READY.** Original cylinder spike left a coil on
  after command completion/reset. Apply its interlock to outputs outside the idle
  guard; the owner supplies that existing permit and never writes child coils.
  Corrected motion/completion/reset and active restart passed.
- **NON_RETAIN startup counts do not accumulate.** STOP→RUN reset Calls/ResetCount
  and StartupCalls returned to1. Use observed STOP/RUN and DTL startup components.
- **A typed parameter can silently break a loop.** `[string] $Tag` coerced case-insensitive
  foreach `$tag` objects to strings. Distinct `$leafTag` restored reads; zero matching
  readable leaves now raises an error. Wrong Softbus target and primitive-type writes
  are refused before calling the Runtime API.

Sixteen recovery checks passed and fifteen completed baseline reads passed28/28.
The run used the existing approved enumeration driver, with no whitelist round.
Eight GRAPH canonical comparisons and both full DB interfaces matched. Complete
Unit lifecycle, retention, other errors/modes and physical1500 evidence remain open.

## S12 full type-map and round-trip correction (2026-10-10)

See [the measured type/round-trip page](core-type-map-and-roundtrip.md):
multiple Core fields on one line must all be consumed; S3/S12 now share the
strict fraktal_tia_types parser. The initial census omitted13 fields and is
superseded. WString255/480 and native operations preserve tested widths; the
Advanced5 server denied symbolic Web API reads after the diagnostic-right
comparison; the Advanced7 continuation below resolves it. Final rights are process-data-only. Host time and simulator time
are separate clocks; the full-hour host criterion failed and was not tuned.

## S12 symbolic Web API denial isolation (2026-10-10)

**[measured]** Authenticated ReadOperatingMode succeeds with diagnostic permission
while PlcProgram.Read/Browse return2, including with a copied three-field DB.
Cold restart and CommunicationMode0 do not fix it. Do not keep changing token
headers or reducing Core types to treat this as an established client/layout
fault. Mode1, process-data-only mask24 and full1405/1405+43/43 witnesses restored.
**[help]** Installed Advanced5's documented project support ends at V18; the
V20 prototype needs a compatible runtime comparison. The mismatch is not a
proven cause. See `core-type-map-and-roundtrip.md`, continuation, for evidence.

## Advanced7 native type projection (2026-10-10)

**[measured]** Owner-installed Advanced7 restores symbolic Read/Browse on the
saved image with the original pin and mask24. Keep the API5 compatibility shim:
it was updated by the installer and PowerOn returns OK. Do not infer API major
from the installed manager or from TIA's bundled DLL. The virtual adapter also
changed; capture runtime and adapter versions before assigning one root cause.

**[measured]** Native LDT is signed Unix nanoseconds encoded as a decimal string;
decode it by type using integer arithmetic, never the generic numeric timestamp
heuristic. Core zero remains unset. The live HMI transport/date parser passes
36 checks with99 Good leaves. Invalid LDT yields Bad with no old Good value.
Whole DTL reads still204; it is not a scalar DateTime. The1500 reference now uses
LDT without reducing widths/capacities;1200 remains a separate projection gate.
The saved LDT simulator image uses the copied S12_Ldt_20261010 station, while
the original FrkS12 project remains the DTL control. Explicit work paths matter.
See `core-type-map-and-roundtrip.md`, Advanced7 continuation and its evidence.

## Standard PLCSIM setup has disabled Next (2026-10-10)

**[measured]** S7-PLCSIM V20 setup in product selection reports
`FeatPLCSIM -> State:Local; Request:AddLocal; Action:Null` and
`EnableNextButton(False)` when its already-installed component remains selected.
The same log reports sufficient disk space. On this host standard PLCSIM V20
file version2000.0000.2005.0001 is present, while the separate Advanced runtime
manager remains5.0.0.0/file50.42.10.00. Standard V20 setup does not upgrade
Advanced5. Use the separate S7-PLCSIM Advanced package for the compatible-runtime
comparison; do not deselect standard PLCSIM merely to enable Next, because this
setup's selection screen uses deselection to request removal.
Source: `C:/ProgramData/Siemens/Automation/Logfiles/Setup/SIA_S7-PLCSIM_V20.00.00.00_20.05.00.01@26-10-10_18-51-01.log`.
Advanced7 package entry linked by Siemens' TIA V20 release documentation:
https://support.industry.siemens.com/cs/document/109963863


## Shared command kernel continuation (2026-10-10)

**[measured]** TIA relocates inline DB member initializers into the DB BEGIN
section when exporting source. The lifecycle fixture initializes its -1 failure
sentinels in test Initial_Call to keep exact canonical comparison. Do not add a
broad source ignore for a changed initializer. A driver plan-complete log can
precede project closure; wait for process exit before opening the same project.

**[measured]** PERMISSIVE_NOT_MET remains LOW according to the authoritative
reason catalogue even when a pending timeout makes the command ERROR. A211/212
result was a test-policy expectation error; corrected tests plus project-reason
and HELD-abort checks pass238/238. Error state does not imply MED severity.
See shared-command-kernel.md and its evidence.


**[measured]** An Openness plan can exit0 while software compilation reports
warnings. The initial shared-kernel fixture had9 own-OutImm-read warnings;
hardware's later compile event was0/0. Inspect every compile event, not the exit
code or last compile result. Move test/device state to declared private Device
storage, then publish OutImm. Generator0.2 now rejects own-output reads before
import; the corrected software and hardware both report0 errors/0 warnings.


## Unit control continuation (2026-10-11)

**[measured]** Passing VAR_INPUT HmiRequest to a modifying FC triggers access
warnings. Use a writable static mailbox; all module paths and secret clearing
remain the same. Native export renders a zero TIME initializer T#0S as T#0ms;
emit the canonical zero spelling, preserving exact comparison. The non-retained
fixture restart counter resets to1 on simulator STOP/RUN; verify a new startup
with an LDT stamp and current request/ack boundary instead of assuming retention.
See unit-controls-and-local-carrier.md for103 native controls and remaining scope.


## Nested Unit/manual continuation (2026-10-11)

**[measured]** Keep wide TargetPath and place large reports outside FC TEMP; execute
manual release from the generated parent, not a write to the FB's own input.
Preserve an incoming cascade/reset event during old-command release. Nested
mailboxes inherit a read-only parent boundary; independent PLC test calls keep
normal access checks. HOME cancellation is immediate, AUTO exit graceful. See
nested-units-and-manual-routing.md for120 native controls,104-block round-trip,
remaining conformance and cleanup details. Full report polling is read-only.


## Static manifest / native HMI (2026-10-11)

INT_TO_STRING adds a leading plus; remove it from array path indices. Private
catalogs remain callable through typed PLC FCs and can be served through the
manifest. QUERY_CONFIG pages and release reports are response-only payloads:
exclude them from cyclic polling and capture the acknowledged reply. A live
Flutter widget test needs the live binding; fake-clock cleanup leaves network
RPC timers pending. Details and scope: [static manifest/native HMI](static-manifest-and-native-hmi.md). **[measured]**


## Local access / owner instance continuation (2026-10-11)

Plan-level trust is not inherited by download steps in the existing driver.
Inject explicit trust into the guarded download substitution. An empty owner
instance reports unspecified until the hardware download. FC constant arrays,
width-qualified string inputs, CASE over strings and untyped WString literals
were rejected; emit native declarations and compare exact exports. Details:
[local access and owner instance](local-access-and-owner-instance.md). **[measured]**

## State/alarm and VM reboot continuation (2026-10-11)

Capture final faults after FRK_End; keep nearest-Unit ownership and derive ancestor
blocking from nested logs. HMI root reset must recurse on blocking after the child
fault clears. Reason-code localization can supersede the raw diagnostic key.
Registering API process exit drops registration without a control-panel owner;
saved Fraktal storage restores the same CPU/image/pin after reboot, but requires
a living keeper. Never use an expiring host that unregisters the owner's instance.
See [derived state/alarm lifecycle](derived-state-and-alarm-lifecycle.md). **[measured]**

## Station/model config continuation (2026-10-11)

Do not pass editable ParCfg VAR_INPUT to a mutating FC: Siemens warns on access
rights. Own the editable static, restore before Init, and separate station/model
record restoration. VAR RETAIN fields remain retained under an optimized DB's
NON_RETAIN header. Sort generated component sets; hash-seed-dependent signatures
break replay even when they compile. HMI config cards live on Configuration and
use the normal ENGINEER display policy. See
[station/model config](station-and-model-config.md). **[measured]**

Config metadata and current values have separate lifetimes: a live scalar reading
may replace the cached value while its declared visibility, permissions and bounds
remain authoritative. Ignoring that reading left an accepted Preset21 edit showing
10 until a full metadata refetch. The focused mapper/repository32 and live editor
gates pass after correction; guarded bench display refresh6058ms. **[measured]**

## Sequence view integration (2026-10-13)

The native GRAPH/root-FB compile dependency cycle requires private typed work available before the chart/adapter/root stage; the owning Unit frame publishes readonly mirrors. Fixed-array UPPER_BOUND was rejected; use the Core bound for CurrentStep.Conds. Tested LAD T#0ms/0ms imports were rejected for this argument; a typed private zero is the qualified workaround, not a general claim about all TIME constants. ST_Diagnostic.SourcePath is the correct source member. OPERATOR_RESET requires a real blocking occurrence; presentation marks do not authorize reset. Revision assertions wait for the latest mutation. Derive E_Mode ordinals. See [measured details](shared-sequence-view.md).
