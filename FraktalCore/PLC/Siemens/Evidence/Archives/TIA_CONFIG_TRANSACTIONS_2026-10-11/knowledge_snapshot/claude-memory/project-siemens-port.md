---
name: project-siemens-port
description: "Fraktal/TIA state 2026-10-10 — native 1214C restart/RUN deltas 19/19, GRAPH semantics/restart 28/28 PLCSIM, S9 sessions measured; diagnostics-only restored, enumeration driver approved; Web API, no paid runtime licence"
metadata:
  node_type: memory
  type: project
  originSessionId: 557e92d1-b71c-4c7c-8e05-907ccca6dc19
  modified: 2026-10-10T02:12:01Z
---

Fraktal/TIA (Siemens TIA Portal V20) port: Part IV `Specification/Fraktal_TIA_Part_IV.md`, plan `Specification/Siemens/SIEMENS_PORT_PLAN.md` (§11 = next steps), evidence `Specification/Siemens/Evidence/` (R1 baseline + `TIA_S2_S15_FIRST_BENCH_RUN_2026-10-08.md` with raw logs), tree `FraktalCore/PLC/Siemens/` (driver `tools/TiaCli`, `s7_probe.py`, `Spikes/S2_Shape` with station/build/download plans).

**Why:** owner asked for Part IV + tooling + programs downloaded to the physical PLC 192.168.0.10 (free to use, nothing connected) + a full plan for core, modules and press demo **without power control**.

**How to apply:**
- Bench 192.168.0.10 = **S7-1200 CPU 1214C 6ES7 214-1AG40-0XB0 FW V4.7.3** (not S7-1500); TIA PG/PC interface "Intel(R) 82574L Gigabit Network Connection" #2. It currently runs S2 + S11_Scl (19/19, TCP 2000 and pinned HTTPS 443); see the continuation below.
- 2026-10-08: S15 + S2 PASS (bench), 17/17 ×3 harvested via `s7_probe.py harvest --tcp 2000`.
- **Use the station project** `%LOCALAPPDATA%\Fraktal\TiaStations\FrkSpikeS2\FrkSpikeS2.ap20` — the CPU is secure-only and trusts only that project's certificate. Never recreate it per build; build plan deletes/re-imports the program. Recovery from a foreign certificate = `download ... --trust-plc PLC_1` (logged TOFU).
- **Every driver rebuild must be re-whitelisted by the user in an elevated shell** (Openness firewall is per exe hash, headless too; VS Code is not elevated). Batch driver changes; prefer generic `service-get/set/call`, `block-attribute`, `hw-attributes` plan lines. Never rebuild over an approved exe while it is still needed (2026-10-08: an in-place rebuild discarded a just-approved build) - build candidates to a separate output dir and swap only when the next whitelist round is due. Check with the registry key `HKLM\SOFTWARE\Siemens\Automation\Openness.0\Whitelist\Fraktal.Tia.Cli.exe\Entry` FileHash (Base64 SHA-256) vs the built exe.
- 2026-10-08 evening: **S1W PASS (functional, bench)** — web server + UMAC user `fraktal` live on 192.168.0.10, ASCII image 17/17 x3; evidence `Specification/Siemens/Evidence/TIA_S1W_WEBAPI_2026-10-08.md`. The 1200 web certificate type is a manual TIA-editor step (Openness has no getter/setter). Downloads need `--set um=...` and `--set protection=`. Gateway `WebApiSessionClient` + `s7web://` transport DONE and live-tested end to end (2026-10-08 evening); S7-1200 TLS handshake ~2.75 s, so one persistent socket (dart HttpClient did not reuse connections). Web HMI in headless Chrome (CDP driver, evidence §10) rendered + commanded the spike Unit: S7 PASS spike scope. S3 (evening): only the CPU web page Diagnostics>Memory reports memory (user fraktal-diag, WebAllowDiagnostics; ALWAYS log out via /FormLogin?LOGOUT — unclosed sessions locked logins ~30 min); S2 19.7 KB, ~1.16 KB + ~0.04 ms per idle CM with the new quiescent fast path in the CM frame (Part IV §3.14). tia_lint.py + 18 tests + pre-commit done. PLCSIM V20 + PLCSIM Advanced 5.0 installed (licence unverified). Next: S11 GRAPH on PLCSIM, Unit fast path, real type sizes, S9 remainder.
- 2026-10-09: committed+pushed 32f879b (Part IV, spikes, Web API transport). **S11 GRAPH leg PASS on PLCSIM** (evidence `TIA_S11_GRAPH_PLCSIM_2026-10-09.md`): `tools/fraktal_tia_graph.py` generates GRAPH from `Spikes/S11_Graph/chain_auto.json` against TIA's exported `reference/FB_GraphSample.xml`; station `%LOCALAPPDATA%\Fraktal\TiaStations\FrkS11` (1516-3 V3.0, PLCSIM Advanced 5.0, IP 192.168.252.1, softbus); 19/19. Facts: GRAPH actions take no IF/expressions (exit conditions in FBD transitions), GRAPH FB not a multi-instance but OK as InOut parameter instance, Execute raised on the 2nd active scan, INIT_SQ runs active S0. PLCSIM: host via `Invoke-PlcSimInstance.ps1 -Action host` (background), `-Action read -DataBlocks 'A,B'`; a NEW instance needs one logged `--trust-plc` download. Open S11: GRAPH supervision/ack, STOP→RUN, download-in-RUN, error OBs.
- **Transport decision (owner, 2026-10-08): no paid runtime licence.** Default HMI path = the CPU's licence-free **Web API** (JSON-RPC/HTTPS) into the Fraktal gateway as a new `WebApiSessionClient` beside `AdsSessionClient` (TC3 uses ADS, AB uses CIP); OPC UA is only an optional licensed projection. PROFINET/PUT-GET/S7CommPlus/Modbus rejected (Part IV §1, plan D4). Spike S1W: `webapi_1214c.plan` + `tools/tia_webapi.py`; web password only via env `FRAKTAL_TIA_WEB_PASSWORD`.
- SCL source rules learned: ASCII only (TIA reads BOM-less as ANSI), one TYPE per .udt with nothing before it, quote `"Name"` members, FC string params without length, no case-only identifier collisions, `#w := GetInstancePath(SIZE := 0);`, statics for records a block reads back. Full list: `C:\Projects\SiemensAgent\siemens-kb\tia-automation\verified-gotchas.md`.
- Never write PowerShell `Get-Content -Raw` → `WriteAllText` on UTF-8 files (it double-encodes); use [IO.File]::ReadAllText or the Edit tool.
- Language rule: [[feedback-siemens-sfc-st-no-ld]].

- 2026-10-09 S11 continuation: evidence `Specification/Siemens/Evidence/TIA_S11_SEMANTICS_2026-10-09.md`, numbered logs + raw source/export snapshots + SHA manifests. GRAPH supervision/ack/skip probes read back identical, compile 0/0; 28/28 on PLCSIM after download and direct Stop→Run. Empty V/C networks exceeded 100 ms T_MAX (T=499–500 ms), no ERR_FLT; explicit supervision with acknowledgement waits for ACK_EF; SkipSteps TRUE loses intermediate step records. Part IV §3.5 keeps V/C empty and skip false. Absolute source `ORGANIZATION_BLOCK OB100` creates Startup (renumbering a named cyclic OB fails); OB121 creates ProgrammingError on 1500. GET_ERR_ID in offending FC: 16#2522, zero + continuation, bypasses OB121; without local handling on PLCSIM OB121 records 16#22 / Reaction 1 and continues. Same local error measured on physical 1214C: **S2 + S11_Scl test image now running, 19/19** (old 17 cases + 29 safe startup + 30 local error). Station/certificates kept, TCP 2000 and Web API unchanged. No commit/stage/push.
- 2026-10-09 native S11 continuation: evidence `TIA_S11_NATIVE_2026-10-09.md`. Owner whitelisted `candidate_s11` hash `4e9MOBqor869GuopfT52OXsrliXn/5n+IviIq7tSAAM=`; role-only --keep-password grant and two SoftwareOnlyChanges downloads passed 0/0. Authenticated native /CPUCommands STOP→RUN without download passed **19/19** and changed OB100 stamp. SZL states observed:3 STOP,6 startup,8 RUN (decoder also accepts4 STOP). Initial successful POSTs were followed by decoder failures; never replay control after observation/response failure. Pin native HTTPS every connect and log out.
- Code-only RUN delta **idle SCL fixture scope**: imports only20_Cycle.scl, OB124; onlyS11SclCycle loaded, noDB/type changes or stop/start/reinit questions. Marker1101→1102 preserves sentinel21265, OB100stamp, mailbox1005/1005; counter218993→320559, scan count increases;19/19 each. `check_native.py` verifies snapshots+canonicalDBinterfaces+exactcaseIDs. CPUclock2012-01-05 is unsynchronized; comparewithinCPU only. Stillopen: GRAPH download-in-RUN, active-command recovery, othererrors/no-handler, manual/semi-auto GRAPH, retentive classes.
- **Cleanup PASS:** owner whitelisted `tools/TiaCli/bin/candidate_s11_enumeration/Fraktal.Tia.Cli.exe`, Base64 SHA256 `5FXuk+YWxHiAAbB4MBZNqSty44F9apDJDgPZiTcCbzM=`. Current approved driver, never overwrite it or earlier approved binaries. V20 GetAssignedDeviceFunctionRights IList has Count2 and enumerates two valid rights but ToList produces one null (measured on same collection). Direct foreach into identifier sets, catalog mutation arguments and exact final-set verification fixed the restore. Hardware compile and full UMAC download0/0 with keep-online-password. Diagnostics role now exactly WebAllowDiagnostics; gateway WebReadTags|WebWriteTags; both existing passwords authenticate, native mode forms absent, CPU RUN marker1102 and19/19. Final evidence `TIA_S11_ENUMERATION_2026-10-09.md`; previous failures and incorrect role/removal causal guesses frozen in prior records, not edited. New raw logs01ident02restore03native04snapshot05results06UMAC. `web_mode.py inspect --diagnostics-only` is read-only/authenticated. No commit/stage/push; pre-existing CMake untouched.
- S9 read/session probe now `Spikes/S9_WebRecovery/read_sessions.py`: two distinct tokens, tenreads/client concurrent PASS; local socketclose/newpinnedconnection preserves token; logoutA yields2Permissiondenied, explicitreloginA and otherclientB PASS. Ten16-read batchesofsamecycliccounter all differ (106–111increments): **batchcoherence singlePLCscan disproved on1214C**. Finalcleanlog04 in `TIA_S9_READ_SESSIONS_2026-10-09/`; earlierfailures retained (missingwebpassword, incorrect102expectation, summarytypo). `idle_session.py` PASS160.010sec noAPIidle; readat163.114s code2 thenreloginPASS(log05), noCPU/UMACchangeduringinterval. `mode_session.py` PASS retainedreadclientnativeSTOP→RUNwithsameToken; counter1807978 frozenSTOP→44/77 increasingRUN;19/19postwarm(log06/07). CurrentimageinRUNmarker1102. Stillowesretained-clientdownload/cablepull, concurrentmailboxwriters andHMIfreshness. NoHMIcodeedited.
- PythonWebAPIprobe hardened: pin beforeeach reconnect; explicitreadonlymethodset permitsone retry; writes/login/passwordchanges/mixedbatch neverreplayed afterlostresponse (unknownoutcome). Fourfaulttests+livereadsnapshot pass. Tooltests44/44, tia_lint0findings(fourpending), rootconsistency0/0+33tests. FullS9tokenexpiry/cablepull/concurrentclients/coherence remainsowed.
- PLCSIM FrkS11 is now **unregistered**: the old host hit its 120-minute limit after being powered off for builds. New registration needs one logged --trust-plc PLC_1 on first download. Helper has halt/run/off with -ConfirmTarget matching ControllerIP + Softbus; stop unregisters. Workstation ~4 GB RAM + 12 GB page file: simultaneous TIA + PLCSIM + help service exhausted commit; compile with sim off and stop only confirmed owned orphan helpers. A download succeeded 0/0 but trailing GoOnline killed TIA; the plan failed, independent runtime harvest passed. `plcsim_results.py` checks exact case IDs and complete table before JUnit. Physical build must do software compile AND --hw separately. DPAPI encrypted hex files need .Trim() before ConvertTo-SecureString; passwords stay in env only.

- **2026-10-10 S3 measured:** evidence TIA_S3_BUDGET_2026-10-10.md,40+1317 new artifacts, all1695 hashes verified including338 previous unchanged. Thirteen physical images compile/download0/0 and19/19 each (247rows);49 exported types and43 storage arrays match complete manifests. Five Units/tenCMs: full3.451796ms vs quiet2.442849ms, about0.201789ms saved per idle Unit,+0.06KB. S2 50_Unit.scl now quiet: mailbox first; paired lifecycle fences only; children/scan-result clear/Mode+CurrentStep mirrors unconditional. Linter enforces boundaries; full mode hooks still unproven. Builder derives full/quiet variants and imports S11 with90_ prefix after S2.
- S3 Core-derived optimized allocation, addedKB wide→compact: status+states47.03→22.84 (16statuses,6states/module compact); alarms75.57→12.41; sequence48.57→21.77; config48.07→19.42. Eight compact write rows alone5.49KB: cannot copy TC3 dense per-module table into2.5KB total-module budget. Share immutable metadata; retain instance captures/limits/revisions/targets; preserve Scope/WriteKey persistence. Compact all-tables96.89/150KB,free53.11KB,one write array only. Not full runtime/press proof. Candidate caps/widths in Spikes/S3_Budget/make_fixture.py; enumsDInt,DT→DTL,pointers→UDInt indices allocation only. Some labels widen; ValueText80 requires encoded-value/domain/persistence-piece gates, never truncate. Profile PROVISIONAL until full runtime/press with≥15KB reserve and published-surface cost.
- **Current bench restored:** S2+S11_Scl quiet Unit,no extra Units/storage,20.53KB work,RUN marker1102,19/19. Native mode forms absent; unchanged passwords work; UMAC/certificates/pin kept. Approved enumeration driver and all5 executables unchanged. Tools52/52;tia_lint0,4pending;rootconsistency0/0+33tests;diffclean,.githooks,no stage/commit/push,pre-existing HMI CMake untouched. Next S12 physical type/time map+S4 round-trip,then Phase2 declaration generator;S9/S11 remainders open.
- **Native logout correction:** standalone logins exhausted native pool despite GET logout. Refusal302/no cookie while diagnostics password authenticates via API. Recovered00:43:10UTC(~30.5min after first series login); reuse one session across measurements/downloads. Corrected live probes: old cookie STILL reads protected memory after ordinary and cookie-only GET /FormLogin?LOGOUT. Initial33/39 raw-HTML matcher falsely reported revocation, explicitly superseded. NativePage.close clears local cookies/socket even on timeout/disconnect (2fault/cleanup tests), no server-revocation claim. Local-clear live proof39 retains old cookie separately for check. Failed reads frozen; never replay completed controller changes. CPU clock still2012,unchanged.

- **Owner scope clarification 2026-10-10:** primary target is the simulated S7-1500 (existing FrkS11 CPU1516-3 V3.0 / PLCSIM Advanced5.0), with full Core/modules/press, SCL plus generated GRAPH. The physical1214C is secondary compatibility/hardware evidence. Its150KB cap, compact candidate widths/caps and press-lite fit must NOT gate or reduce reference implementation. S3 numbers remain1214C-only; no further1200 budget work on the critical path. Next S11 reference remainder and S12/S4 on simulated1500, then reference declaration generator/runtime/modules/press. Plans/PartIV gates now family-scoped. Keep Core capacities subject to actual Siemens native limits; simulator prototype firmware vs declared hardware baseline must be resolved before conformance claims. Do not edit dated evidence to match this priority correction.

- **2026-10-10 active GRAPH recovery:** `TIA_S11_GRAPH_RECOVERY_2026-10-10.md`, Recovery fixture/generated inputs/four export sets. Sixteen recovery checks passed; fifteen completed baseline harvests28/28. FC marker2101→2102 SoftwareOnlyChanges during BUSY preserved observed command/step/DB state, no stop/reinit question. GRAPH action-label delta kept exported DB interfaces but asked TurnOffSequence and DataBlockReinitialization, loaded chart DB; generic driver chose StopPlcAndReinitialize. GRAPH state-preserving RUN gate NOT PASSED, even though endpoint BUSY survives. Quiesced production deployment workflow still owed, along with retention/other errors/manual-semi-auto/full Unit integration. Same approved enumeration driver/hash, no rebuild/whitelist.
- Reset while BUSY and native STOP→RUN require fresh Arm, safe first scan/no automatic motion. NON_RETAIN StartupCalls resets to1 (not incrementing2), Calls/ResetCount reset; observe native state and DTL stamp. Reset after completed READY initially FAILED: cylinder kept Extend coil. S2 30_CylinderCM now applies same IntlkOk to outputs outside quiet guard; Recovery owner supplies idle permit, never writes coils. Fixed image motion/completion/reset/active restart pass, compile/download0/0. Initial failure27 and first verifier36 retained; historical FALSE safety flags persist across code load29, fresh reset35 re-arms proof. Physical1214C image untouched this run (still prior19/19 baseline), corrected CM proven on simulated1500 only.
- PLCSIM typed writes added to Invoke-PlcSimInstance: exact ControllerIP+Softbus/type guard, wrong physical IP/type refused before write. `[string] $Tag` collided with foreach `$tag` (PowerShell case-insensitive) and silently erased native fields; rename loop leafTag and reject empty harvest. Nested quoted plan substitutions through PS5.1 lost target quotes; use Python argument lists/absolute Windows executable path. Tool55 tests, lint0/fourpending. Host15176 parent12752 shut down normally via stop file after final safe idle; FrkS11 now unregistered, saved station/image preserved, next registration needs logged TLS trust. No stage/commit/push; pre-existing HMI CMake untouched.
- Recovery evidence frozen: **531 new artifacts**, previous **1695** unchanged, **2226** total SHA256 bindings across nine manifests. Final source CM normalized to LF only; compiled CRLF input preserved, mapping53 and final diff54. Current generator includes output_delta and regenerates the compiled correction/GRAPH canonical read-back. Gate55 tool tests,33 consistency tests,consistency0/0,lint0/fourpending,diff clean. Remaining critical path: quiesced GRAPH deployment/other S11 mechanisms, S12/S4 on simulated1500, then reference declaration generator/runtime/modules/full press; no1200 budget gate.

## S12/S4 full Core census continuation (2026-10-10)

- Primary remains full simulated S7-1500;1214C/150KB secondary. New persistent
  station FrkS12,1516-3 V3.0 at169.254.212.49/16 on existing virtual adapter
  169.254.212.48/16. TCP/IP is required for web server, not Softbus (V5p337).
  All physical mappings0, no host IP/route change, no physical CPU mutation.
- Complete Core layout88 structs/610 fields,42 enums/295 ordinals. Initial
  line regex skipped13 same-line fields in ModelField/Oee/ShiftRecord/ShiftRecordV3;
  corrected parser rejects residual/duplicate/implicit syntax, preserves18 private
  OPCUA attributes and lives once in tools/fraktal_tia_types.py (S3/S12 use it).
  Frozen S3 groups did not contain those four types; allocation numbers unaffected.
- Final v10 fixture has269 sources; native build/download0/0; authored/export/
  reimport/compile/export equality269/269 and88 native interfaces/access flags.
  Ignore only whitespace/comments, identifier forms, exact DTL annotation/OB title/
  native OB inputs; string payload, statements, bounds and custom inputs significant.
  Full SDK1405/1405 (incl296 timestamp-component witnesses), scalar43/43 twice
  after restore. WString255/480, LEN254/255/480, CONCAT256/MID tail, Unicode,
  exact64-bit bounds and295 constant count. DT->DTL candidate, PVOID->UDInt slot
  storage only. HMI/native Web API gate is NOT passed; no HMI code changed.
- Native web pin33f3df01cd14f8dd4faf73da564f0162fc25b634707a9793c75b9d2bf76d8f15,
  ApiVersion3.00207. Classic DPAPI password28 chars;36 rejected (<33 required).
  Mask6 gives no API rights;24/30 read_value/write_value but symbolic Read/Browse
  denied2. Controlled30->31 adds only DoDiagnosis/read_diagnostics, still denied2.
  Restored24, final permissions read_value/write_value only. Quoting/header/Origin/
  newTLS/mode variants do not fix; optional-cookie returns token only. Wrong login
  rejected100. GetQuantityStructures/GetAuthenticationMode unavailable.
  ReadSystemTime works with omitted params; params{} is Invalid Params. Cause of
  symbolic denial unknown; do not blame security or simulator unsupported without proof.
- Hour observation completed117 samples,3390384 scans,Ready/BadDelta0, max39.602ms.
  PLC3479.983755s versus host3600.001412-3603.015396s FAILS3.601508s criterion.
  Independent10min virtual-system-time comparison121 samples max8.664ms within
 500ms PASS;ScaleFactor1. V5pp87-88 Windows suspends simulator clocks. This is
  virtual-time consistency, not hardware drift or UTC/NTP quality. No tuning/reset/
  download during hour. Still prototype below planned physical FW3.1+.
- Finished evidence TIA_S12_TYPES_ROUNDTRIP_2026-10-10.md +raw/archive frozen:
 6989 new SHA bindings,2226 prior unchanged,9215 total across10 manifests.
 65 tools/33 consistency tests pass,consistency0/0,lint0/fourpending,diff clean.
  Code/spec/plan/README and SiemensAgent core-type-map-and-roundtrip KB updated.
- HostPID12476 stopped via owned stop file, unregistered07:01:10UTC; manager
  Promiscuous restored. FrkS12 saved station/image/DPAPI/pin retained, future
  registration may require logged engineering TLS trust. Existing enumeration
  driver unchanged/approved; runner exact virtual-target guard tested/read-only
  preflight59. No whitelist request, stage/commit/push; HMI CMake untouched.
- Next: resolve native symbolic data boundary, HMI/time projection and release
  type decision; then declaration generator/frame/registry/full runtime/modules/
  press without power control. Quiesced GRAPH deployment and other S11 remainder
  remain; source roundtrip does not prove library updates/retention.

- **2026-10-10 native Web API isolation:** new `TIA_S12_WEBAPI_RECOVERY_2026-10-10.md`.
  Cold restart and CommunicationMode1->0 still symbolic2. Absent/invalid tokens
  GetPermissions[]; valid token reports read/write. Mask95 grants diagnostic/page
  rights and ReadOperatingMode returnsrun, symbolicRead still2. Broad524287 TIA
  rejected before compile/save/download, not an API test. Copied station with
  three-field DB also Read/Browse2; SDK ready/marker/scans and web-access TRUE.
  Original complete image restored,1405/1405+43/43 pass, mode1+mask24+samepin.
  V5 manual p20 documents TIA V14-V18; actual manager/instance5.0.0.0 file50.42.10.
  V20 bundledclient7 does not mean installedmanager7. Session not elevated;4GiB
  host. Compatible runtime comparison needed, not proven fix. Owner asked async
  about compatible V7/V8 availability; source declaration/generator proceeds
  independently with native WebAPI/HMI gate open. Host6652 unregistered07:40:03UTC,
  managerPromiscuous restored. No physical change, driver rebuild or commit/push.

- **R4 declaration model started2026-10-10:** `tools/fraktal_tia_declaration.py`, `Tests/Declaration/two_root_forest.json`; reusable type child definitions + roots expand to8 planned rows, no superroot. Core-derived Status.Name/TypeKey widths + E_ModuleType ordinals; strict schema/tier/name/cycle/capacity/unused checks,18 focused tests. Inventory only, no PLC frame/registry runtime generated yet; all4 source lint rules remain pending. Report `TIA_R4_DECLARATION_MODEL_2026-10-10.md`. Next fraktal_tia_generate frame/registry/HAL/hooks/GRAPH integration; keep nativeWeb/HMI gate open.

- Final preservation of prior run: native isolation66 + R4model27 =93 new SHA bindings; all9308 across12 manifests verified, prior9215 unchanged. Those evidence folders/reports are frozen.83 tool tests+33 consistency tests passed. Approved enumeration driver e455ee93e616c4788001b07830164da92b72e3817d6a90c90e03d98937026f33 unchanged. The pending compatible-runtime question was subsequently resolved by the owner's installation; see below.

## Advanced7 native comparison and LDT reference mapping (2026-10-10)

- Owner installed Advanced7: manager7.0.0.0/file70.0.323.0, updated API5 shim
  50.43.04.00, PowerOn OK. Virtual adapter11 now169.254.105.123/16; CPU still
  169.254.212.49/16 TCPIP, all physical mappings0. No physical CPU change.
- Native Read/Browse work on saved DTL image before download/config, alsoSTOP.
  Api.Version5, original pin33f3df...f15, mask24 read/write only.1340/1340 pass.
  Upgrade changed manager/shim/adapter together; no single cause isolated.
- Reference1500 Core DT now LDT.88 structures/610 fields,42 enums/295 constants,
  full Core widths/capacities retained.37 scalar dates replace296 components;
  SDK1146/1146 types and43/43 scalars, native1081/1081,88 interfaces and269/269
  canonical authored/reimport sources pass. Compile/incrementalHW/download0/0.
  PVOID remains witness/index only;1200 date projection separately owed.
- Native wholeDTL204; LDT exact decimal Unix nanos/raw big-endian, DTrawBCD
  differs SDKpackedUInt64. HMIclient LDT->DateTime ISOZ ninefractiondigits,
  zero unset, integer bounds, malformed->Bad clearing oldGood; TIME Int32ms,
  LInt/ULInt exactstrings. Real pinned transport/date parser36checks,99Good/0Bad;
  generic DateTime microseconds. Full Unit rendering/mailbox/UTCquality unproven.
- CURRENT SAVED SIM IMAGE IS LDT CANDIDATE. Project:
  %LOCALAPPDATA%\Fraktal\TiaStations\S12_Ldt_20261010\FrkS12\FrkS12.ap20.
  Original TiaStations\FrkS12\FrkS12.ap20 remains DTL; secret/certs/pin retained.
  Generated S12_Types_20261010_v11_ldt; defaultLDT, --timestamp DTL reproduces
  control. with_secret -Work supportscopy; use explicitworkpaths, avoidolddefault.
- Host1076 unregistered via stopfile19:11:56UTC, exactprior manager mode2 restored.
  Savedimage remains, no registeredFrkS12; nextregistration needs loggedtrust.
  Approved enumeration driver unchanged; no C#build/whitelist/stage/commit/push.
- Evidence TIA_S12_WEBAPI_ADVANCED7_2026-10-10.md/rawarchive; failedprep/analyzer
  retained then corrected.85 tools/24 HMI/33consistency tests pass, lint0/fourpending,
  consistency0/0. CMake untouched. PriorhourFAIL/virtualtimePASS notretested.
  Next declarationframes/registry/HAL/hooks, fullruntime/modules/press without
  powercontrol. R4partial; Phase3 forest/render/commands and S11 deployment/modes owed.

- Advanced7 evidence frozen:1844 new SHA bindings; all9308 prior bindings unchanged,11152 total across13 manifests verified. Do not edit the new report/raw/archive. Final manager state0 registered instances, exactmode2 restored, ownedhost1076 exited. Archive snapshots precede this final ledger entry.

## R4 generated frame/registry continuation (2026-10-10)

- `tools/fraktal_tia_generate.py` now emits24 common-contract/frame/HAL/registry/
  composition/OB1 sources. One shared Tests/Declaration/two_root_forest.json
  now carries optional records/contracts/CM HAL/capability masks/authored regions;
  engineering inventory and PLC assembly derive from it, no duplicateforest.
  Three reusable FBs,8 instances,16 project-fixture registry slots,0reserved.
  Core type widths/caps/defaults/exposure derive from DUTs; S12 uses the shared
  native_scalar map,270 regenerated files byte-identical (269sources+manifest).
- Registry indicesDInt; compactstringfreerows, setup parentfirst, identity from
  GetInstancePath. Separate root IDBs StationA/B, compositionFB notmodule/superroot.
  Badparent/overflow checkedbeforearrayaccess, index0+fault disablesdispatch.
  Full initializationdiagnostics/genericwalks stillfuture. GeneratorownsOB1 call;
  defaultentrypoint compiles0/0 in copiedcompiler-onlyproject,25blocks/17interfaces.
- Separate testBoundary FRK_Core/Begin/End are ORDER PROBES, NOT CORE LIFECYCLE.
  Package31sources/36blocks/19interfaces, software/hardwarecompile/download0/0,
  canonical authored/native + orderedreimport/compile/export36/36.103 runtime
  assertions pass:identity/parents/typeids,initonce/begin-end/order,CMquiet+cyclic
  every scan, HAL values,invalidparents/overflow withGET_ERR_ID0. STOP/RUN same8rows
  and103pass; final316841scans/0fails. Compositesunconditional; cyclicregion is
  post-lifecycle derived/outputwork, notfullOnCyclichook. FullUnit facets absent.
- Nativepublic81/81 +private5/5(code200) pass originalpin/ApiVersion5/mask24;
  no writes/HMIrender/commands. TypedHalaliasesbareInOut: TIA silentlydropsInOut
  attributes. Hideownedstorage; nativealiasesabsent. InitialemptyIF3compileerrors,
  parametersectionreorder andattribute-drop controls preserved/corrected.
  Manifestreplay rejectseditedfiles evenwithrewrittenhashes; source-scoped
  T-TIER/T-IO/T-WIDTH/T-GEN work, broader4pending remain explicit.98 tooltests,
  33consistencytests,lint0,consistency0/0,LF/ASCII/diffpass. NoHMIcodechanged.
- CURRENT SAVED FRKS12 IMAGE/PROJECT is R4 frame probe, NOT prior LDT typefixture:
  %LOCALAPPDATA%\Fraktal\TiaStations\R4_Frame_20261010\FrkS12\FrkS12.ap20.
  Earlier DTL/LDTprojects untouched; secrets/certs/pin retained. R4_Entry_20261010
  is compiler-only copy, notdownloaded. Workpaths always explicit.
- Host11724 unregistered via ownedstopfile20:35:08UTC; exactmode2 restored,
  0registeredinstances. Savedimage persists; newregistration needs loggedtrust.
  Approvedenumerationdriverunchanged e455ee93...; no rebuild/whitelist/physical
  change/stage/commit/push, CMake untouched. EvidenceTIA_R4_FRAME_REGISTRY_2026-10-10.
- NEXT: sharedCoreBegin/End lifecycle, Unit mode/mailbox/Part facets, nativePhase3
  forest/render/commands, thenfullmodules/presswithoutpowercontrol. Retention,
  clockquality,GRAPHintegration,genericcapabilitywalks/tagtable/profiles stillopen.

- R4 evidence frozen:815 new SHA bindings,11152 prior unchanged,11967 total across14 manifests verified. Do not edit new report/raw/archive. Final 98tools+33consistency tests pass; no registered simulator. Archive snapshots precede this final preservation ledger.


## Shared command kernel continuation (2026-10-10)

- Framework/Core/command_kernel.scl.in owns command lifecycle once. Generator0.2
  --shared-runtime includes it:27sources; every type requires declared command
  ids/labels and a TIME ParCfg timeout. Core ordinals/caps, timing-label width,
  rationalization generated from authorities. Strict replay includes kernel.
- Frame: Begin reset/edge, Init, latch ParCmd + FRK_Start validation/tag, accepted
  CommandStart, Cyclic management/children, FRK_RouteAbort + abort reactions,
  BUSY dispatch, End hold/timeout/timing/mirror, lowercase cyclic derived/permits.
  CMs with management run full path eachscan; otherCMs retainquietguard; composite
  callsunconditional. Boundarytype/FCstubs updatedABI; frozenR4evidence unchanged.
- Lifecycle fixture actualkernel+generatedframes,55deterministicscan cases,
  238PLCassertions pass fullisolateddownload and guardedSTOP/RUN. Tests reset
  fixturedefaults onInitial_Call; NOT productionretention/safe-restart proof.
  EarlyExecute dropcontinuesBUSY;terminalpulseonecall;Armedterminalreset;
  backgroundfaultlatched/retryedge;AbortlevelBUSY/errorabortedge;HELDresume/
  abortandSince;pendingtimeout/verbatimfaultadoption;invalidcmd/timeout;
  samecallcompletiontiming,statsaverage andUDIntrollover10ms.
- First211/212failedcheck142case33expectedMED butcatalogue PERMISSIVE_NOT_MET LOW.
  Kernelrationalizationcorrect, testcorrected. Unknownprojectpendingreason defaults
  MEDontimeout. Priorfailrawretained. DBinline-1 movedbyTIAtoBEGIN;fixturedefault
  sentinels nowsetinInitial_Call; no canonicalignore. Oneprojectlock retry preserved:
  awaitdriverprocess exit, notonlyplan-completebeforeanotheropen.
- Native100public+7private(code200)passoriginalpin/mask24/API5; Core/latchedParCmd/Device/
  HAL/Registry/Clock/defaultteststoragehidden.47blocks/18interfacesmatchnative,
  orderedreimport/compile/export. Productiondefaultentrypoint43blocks/18interfaces
  also compile0/0 in separatecompiler-onlyproject; notdownloaded.
- Current saved FrkS12 project/image is Core_Lifecycle_20261010/FrkS12/FrkS12.ap20
  underLOCALAPPDATA/Fraktal/TiaStations. EarlierR4/DTL/LDTpreserved; secret/pin/certs
  unchanged. Isolated1516V3.0/TCPIP169.254.212.49/physicalmappings0; Advanced7API5
  compatibilityDLL. Approvedenumerationdriverunchanged; no rebuild/whitelist.
- Next Unitmode/mailbox/Part +genericcompositecapability/rollupselection, stateflags/
  alarm/recipe/retention/fullsequence services, nativePhase3HMIrender/commands,
  thenmodules/presswithoutpowercontrol andGRAPHparity. No150KBcap onreference1500.
  Clockquality/hardwaredrift/extremeTIMEsaturation controls remainunmeasured.
- Evidence TIA_CORE_LIFECYCLE_2026-10-10. Prior11967bindings/14manifests audited
  unchanged. This turnno physicalPLCchanges, staging, commits orpush; CMakeuntouched.

- Final108 tooltests and33 consistencytests pass, lint0/four broaderpending,
  consistency0/0, LF/SCL-ASCII/diff checks pass. Approveddriver hash verified.

- Ownedhost2644 unregistered21:34:40UTC, exactpriorNetworkMode2 restored.
  Finalmanager0registered at21:35:17UTC. Savedtestimage persists.

- Final log audit corrected an earlier compileclaim: software had9 own-OutImm
  readwarnings though hardware0/0 anddriverexit0. Addedoptional declared private
  Device storage; fixtureholdsstate there andpublishesOutImm. Generator rejects
  ownoutputreads beforeimport. Finalv5compiler events both explicitly0errors/0
  warnings; priorwarninglogs/claims retained in newevidencecorrection narrative.
 107 tooltests pass. Secondownedhost12864 checks warning-free image.

- Warning-free final v5: bothcompileevents0errors/0warnings, same238/238 ondownload
  andSTOPRUN, native100public/7private(code200)before+afterrestart. Devicehidden.
 47blocks/18interfacescanonicalreimportanddefaultproduction43blocks/18interfaces
 0/0 incompiler-onlycopy. --require-clean-compile checks ALLresults and rejects
 software9warnings followedbyhardware0/0;108tools+33consistency pass.
- Secondownedhost12864 unregistered2026-10-10T21:43:55.5759958Z, exactmode2 restored,
 0registered. Earlierwarningattempts retained; currentimage/project v5CoreLifecycle.

- Core-lifecycle evidence FROZEN:1732 newbindings (including rootreport),11967
  prior unchanged,13699 total across15 SHA256SUMS verified. Do not edit new
  report/raw/snapshot. Final audit file outside frozen archive; snapshot precedes
  this ledger. No registeredsimulators, exactnetworkmode2 restored.


## Unit controls and local part continuation (2026-10-11)

- Generator 0.3 Unit profile declares Core-supported modes, initial mode and run
  command. Framework/Core/unit_services.scl.in owns mailbox/operation/mode/reset/
  local Part once. 45 generated sources, 46 test sources, 79 blocks/34 interfaces
  canonical authored/native and ordered reimport/compile/export. All final software
  and hardware compiles have 0 errors/0 warnings. Default production entrypoint
  is compiler-only, 78 blocks/34 interfaces, not downloaded.
- Native pinned Web API sequence passes 103 checks twice (25_native_final and
  42_native_restored), each including STOP/RUN and new post-restart commands.
  Live access/permit checks and release reports, same/zero commits, secrets cleared,
  continuous run, cycle Stop, graceful/immediate/deferred/blocked/bounded exits,
  recursive child release/reset, live faults preserved, read/write/identity/NOK
  carrier failures, provider result before canonical events, counters, private5
  code200/read-only5 code205. Root B carrier remains off. No GUI rendering claim.
- Unit run has no whole-run timeout. Child work and pending exits stay bounded.
  AUTO Core defaults CONFIRM/GRACEFUL; CONFIRM is HMI prompt policy, no new BoolValue
  gate. Cyclic management refreshes permits before common request consumption;
  ack after lifecycle. Startup consumes current commit without executing it.
  Single-writer serialized bench; not multi-writer locking or full authentication.
- Explicit local BY_POSITION carrier injection only; serial/UID restart durability,
  external providers, measurement helpers, sessions/audit/alarm/state/recipes/
  retention and full sequence/GRAPH integration remain open. Reset clears a latch,
  never its live cyclic condition. FRK_ReleaseCommand propagates through generated
  child calls and wakes quiet CMs; Start waits for READY descendants.
- Preserved corrections: first build 2 access warnings from VAR_INPUT HmiRequest;
  moved to writable static, path unchanged. Zero TIME canonical T#0S -> T#0ms.
  Extended run 83/84 passed, failed non-retained Restarts expected2/actual1; now
  BootStamp plus current post-restart commit/ack prove Initial_Call behavior.
  Initial 73 checks passed. No ignore rules or altered prior frozen evidence.
- Common command kernel regression regenerated and compiled 0/0, 238/238 in55
  cases both before and after harness CASE ELSE lint fix; 48 blocks/18 interfaces
  canonical. Unit image restored afterwards and 103 native checks repeated.
  Final 112 Siemens tools +33 consistency tests pass, lint0/four broader pending,
  consistency0/0, manifests replay45+27+24, authoredLF/SCLASCII/diff passed.
- Current saved FrkS12 Unit image/project: LOCALAPPDATA/Fraktal/TiaStations/
  Unit_Runtime_20261011/FrkS12/FrkS12.ap20. Unit_Compiler_20261011 currently holds
  the compiler/regression project, not the restored runtime image. Older projects,
  original pin, process-data mask24, DPAPI secret and certificates preserved.
  Advanced7/API5 shim, isolated CPU1516/TCPIP169.254.212.49, physical mappings0.
- Owned host15268 unregistered and exited at 2026-10-10T23:44:09UTC; manager reports
  0 registered instances and exact prior NetworkMode2. Saved Unit image persists;
  a new registration needs one logged engineering TLS trust outside a plan.
- Approved enumeration driver unchanged e455ee93e616c4788001b07830164da92b72e3817d6a90c90e03d98937026f33;
  no rebuild/whitelist/physical change/staging/commit/push. CMake untouched.
  Part IV/plan/docs and SiemensAgent KB updated; new evidence
  TIA_UNIT_CONTROLS_2026-10-11. Prior13699 bindings/15 manifests audited unchanged.
- NEXT: nested Unit mode cascade, manual command routing, complete release queries,
  then native generic HMI forest/render/mailbox gate, full modules/press without
  power control and SCL/GRAPH parity. No150KB cap on the reference S7-1500.

- Final report audit fixed the lifecycle JUnit aggregate failure count from Boolean
  text to integer. Saved SDK output was replayed byte-identically for corrected
  JUnit; a synthetic Failed=1 control is rejected with numeric failures=1. No
  additional runtime sample or prior evidence edit.

- Unit control evidence FROZEN: 2699 new SHA bindings (including root report),
  all13699 prior unchanged, 16398 total across16 manifests verified. Do not edit
  TIA_UNIT_CONTROLS_2026-10-11 report/raw/snapshot. Final hash audit outside frozen
  archive; snapshots precede this ledger. Simulator unregistered, NetworkMode2.


## Nested Unit and manual routing continuation (2026-10-11)

- Generator0.4 owns typed routes, catalogs, nested cascade and pure release
  predicates.24 instances/two roots/three Unit levels in32 registry slots.
  52 generated/54 test sources,104 blocks/40 interfaces canonical+ordered reimport,
  all final software/hardware0 errors/warnings. Production102/40 compiler-only,
  not downloaded. Native Catalog/CatalogCount follow existing HMI names.
- Native120/120 twice, with STOP/RUN/fresh requests; baseline Unit103/103 passes
  current services after temporary guarded regression download. Routing restored
  afterwards.115 tools+33 consistency tests, lint/replay52+48+24/LF/ASCII/diff pass.
  Command kernel bytes unchanged from prior238/55 proof; not rerun this slice.
- Manual target+direction/common reasons, access/scope/owning-mode checks, same
  handshake and generated parent Execute drop. Query has no command/audit side
  effect. Unit Release predicate is pure and written once; ManRelease slots must
  be unique bounded literals. Internal cascade is trusted for access only.
- Native caught lost second-level cascade: child preparation cleared incoming
  events while releasing old commands; fixed. Reset event likewise preserved
  through callback, pending mode/start canceled. One active parent reset invokes
  all three reactions once. Deferred timeout releases nested runs. Unsupported
  AUTO mode change stops child gracefully; HOME policy cancels immediately.
- Child HmiRequest native writes205; keep parent read-only boundary. Independent
  nested test calls TrustedFALSE check access. Future nested HMI actions need root
  routing. Scratch/condition storage native reads200. Core event named but no
  ordinal; prototype2008/std.event.childModeUnsupported, full registration open.
- Initial build12 errors/2 warnings: wide path, bad clear-call, report TEMP>16KB,
  own-input Execute writes. Corrected wide type/private shared scratch/generated
  PARENT release; final0/0. First native mailbox refusal, lost cascade and wrong
  HOME StopPending test retained. Early export verify before completion failed,
  corrected after driver exit. Unit test CASE ELSE added; full-package lint0.
- Current saved runtime project/image LOCALAPPDATA/Fraktal/TiaStations/
  Routing_Runtime_20261011/FrkS12/FrkS12.ap20. Routing_Verify_20261011 is compiler/
  review production image; earlier Routing_Compiler copy unused. Older stations,
  original pin/mask24/API5/DPAPI secret/certs preserved. Advanced7 isolated1516
  TCPIP169.254.212.49, physical mappings0. New instance trust logged once.
- Owned host4884 exited2026-10-11T00:46:37UTC, zero instances registered, exact prior
  NetworkMode2 restored. Approved enumeration driver unchanged e455ee93...; no
  rebuild/whitelist/physical changes/stage/commit/push, CMake untouched.
- Evidence TIA_UNIT_ROUTING_2026-10-11. Prior16398 bindings/16 manifests audited
  unchanged. Next static manifest/native HMI forest/render/mailbox, full releases/
  alarms/state/session/recipe/retention/sequence/GRAPH, modules/press without power.
  Held manual actions and UID durability remain open. No150KB cap on1500 reference.

- Unit routing evidence FROZEN:4173 new bindings including root report, all16398
  prior unchanged;20571 total across17 SHA256SUMS verified. Do not edit
  TIA_UNIT_ROUTING_2026-10-11 report/raw/snapshot. Audit outside frozen archive;
  snapshots precede this ledger. Simulator unregistered, exact NetworkMode2.


## Static manifest/native HMI continuation (2026-10-11)

- Generator0.5 owns typed static walks and the shared16-entry pager. Catalogs
  are private, existing canonical HMI fragments are served from their one PLC
  source, slots are cleared and DATA_READ hides values while keeping metadata.
  ConfigRev clock seed changes on Initial_Call; no synchronized UTC claim.
  No editable capabilities/provider or configuration mutation in this slice.
- Manifest241/241, routing120/120 through manifest catalogs, native HMI live test
  passes: two roots/24 modules,492 entries, rendered Instant button and native
  counter delta1, independent peer modes. Test-only memory operations display
  preference NONE matches the prototype PLC gate; login provider remains open.
- HMI response ConfigPage/Report excluded from cyclic tiers; fast assignment
  4278->1314 of8070 paths. Release consumers capture the ack reply.123 HMI tests,
  116 Siemens tools,33 consistency tests, clean HMI analysis.117 native blocks/
  41 interfaces canonical+ordered reimport0/0; production114/41 compiler-only0/0.
  Command kernel unchanged; prior238/55 runtime scope preserved, not rerun here.
- Preserved failed plan placeholder, native cleanup method, stale catalog test,
  indentation, duplicate Dart import URI, default NONE display policy, fake-clock
  network cleanup and disk-full runs. Final widget uses live binding/real fonts.
  Deleting Flutter temporary caches was auto-review rejected; compressed three
  generated cache files instead, preserving bytes. No source/evidence deletion.
- Original host12260 unregistered at03:58:00UTC (expiry after pause), mode2 restored.
  New host11460/gateway12120 stopped cleanly at04:15:28UTC;0 instances, mode2.
  Current saved image/project TiaStations/Manifest_Runtime_20261011/FrkS12.ap20
  under its FrkS12 folder. Manifest_Verify holds compiler-only production image.
  Approved enumeration driver e455ee93... unchanged; pin/DPAPI/process mask24
  preserved. No physical changes, driver rebuild, stage/commit/push, CMake edit.
- Evidence TIA_STATIC_MANIFEST_HMI_2026-10-11;20571 prior SHA bindings/17 manifests
  verified unchanged. Next authentication/session/full audit and state/alarm
  services, then config/recipe/retention and full sequences/GRAPH/modules/press.
  Press excludes power control; reference1500 has no150KB cap.

- Manifest/HMI evidence FROZEN:1415 new bindings; all20571 prior unchanged;21986
  total across18 SHA256SUMS verified. Do not edit the report/raw/snapshot. Final
  audit lives outside the frozen archive. Simulator0, exact manager mode2.


## Access/session continuation (2026-10-11)

- Resumed after owner raised VM RAM4->16GB. Headless TIA gates complete; no proven
  Visual Studio crash cause. Owner-created Fraktal adopted from unspecified/Softbus
  to isolated TCPIP169.254.212.49; CPU1516 after hardware download, second virtual
  interface192.168.1.1, mappings0. Preserve this owner instance; leave RUN.
- Generator0.6: private Core-compatible salted hashes, one compression/scan,
  correlated asynchronous login, independent sessions, query-neutral idle expiry,
  accepted-mutation activity, gated policy edits/self-lockout. Native122/122,
  current routing120/120. Auth HMI live gate uses real operator login and normal
  OPERATOR display policy; rendered Instant counter delta1,24 modules/492 entries.
-129/42 native canonical+reimport0/0; production125/42 compiler-only0/0.122 tools,
 569 HMI pass/1skip,33 consistency tests, lint/analysis clean. Approved driver hash
  e455ee93... unchanged; no physical changes/rebuild/whitelist/stage/commit/push.
- Source declaration/TLS/stale-generated failures preserved. Top-level plan trust
  was not inherited; runner injects explicit requested trust into download only.
- Current saved image: Access_Runtime_20261011/FrkS12/FrkS12.ap20. Access_Verify holds
  production compiler image. DPAPI web secret/pin preserved; separate random PINs
  in FrkAccess.operator.secret/admin.secret. Never put their contents in logs.
- This checkout lacks12 newer referenced reports and all18 old checksum manifests;
  the previous21986-binding audit cannot be repeated without the absent archives.
 134 prior available files are preserved. New TIA_ACCESS_SESSIONS evidence records
  this explicitly. Do not reconstruct absent frozen records from current sources.
- Local table/policy retention, CRUD/provider substitution, full MESSAGE/alarm audit,
  data classes and concurrent writers remain open. Next state/diagnostic/full alarms,
  then configuration/recipe/retention and full sequences/GRAPH/modules/press without
  power. No150KB cap on reference1500. Gateway closed; application sessions logged out.

- Access/session evidence FROZEN:3360 new SHA256 bindings (~54.1MB) verified;134
  available prior files unchanged. Old18 manifests absent, not reverified. Final
  audit outside archive at Access_Session_20261011/46_final_evidence_audit.json.
  Fraktal RUN; both roots READY/MANUAL, sessions NONE, secrets cleared; no gateway/TIA
  helper left. Do not edit the new report/raw/source snapshot/checksum manifest.

## Derived state / alarm lifecycle continuation (2026-10-11)

- Generator0.7: selective unconditional state facets, Core12 rows/key120;
 16 active/64 closed ST_AlarmEvent, AUTO/MANUAL reset, monotonic duration,
  nearest-Unit capture after FRK_End, registry-derived nested blocking and reset
  cascade. HELD produces no fault alarm. Overflow/overwrite flags survive.
- Access/Part occurrences now use AUTO_RESET events; History is diagnostic faults.
  Optional composition event_sink/Ev ST_AlarmEvent + private SinkEnabled receives
  come/exact close. No binding dependency by default. Shelving, runtime project
  metadata, durable adapter, retention and full awaited-diagnostic services open.
- Native96/96, nested23/23, auth122/122; earlier routing-only candidate120/120.
 148 blocks/45 interfaces reimport0/0; production142/45 compiler-only0/0.
  Live authenticated HMI fault/reset passes,24 modules/492 entries/Instant delta1.
  Recursive reset helper fixes nested WAIT_RESET after fault clears.570 HMI pass,
 1skip,128 tools/33 consistency, lint/analysis clean. First HMI assertion used raw
  test.first instead of authoritative TEST_FAULT text; failure preserved/corrected.
- Current saved image: Alarm_Runtime_20261011/FrkS12/FrkS12.ap20. Alarm_Verify is
  compiler-only. Approved driver e455ee93... unchanged; physical1214C untouched.
- Owner VM reboot16:09:46UTC cleared registration after morning tests. Existing
  persistence Fraktal hardware/memory card restored CPU1516/pin/image without
  download. API registration disappears when registering client exits and no
  control panel owns it. Hidden keeper PID/log36 in State_Alarm_20261011 remains
  alive with no expiry/unregister. Do not stop it as routine cleanup. Post-boot
  nested23/23 passes again; final roots/exercised nested READY/MANUAL, sessionsNONE,
  no active/blocking alarms, secrets cleared. Gateway/TIA closed, keeper stays.
- New TIA_STATE_ALARMS_2026-10-11 evidence is append-only; source/raw/KB snapshots
  and SHA bindings freeze together. Access3360 +134 available older files unchanged;
 12 older referenced reports/18 checksum manifests still absent, not reconstructed.
- Next config/recipe transactions and persistence (users/policy/alarm), remaining
  shelving/runtime metadata/durable sinks/full diagnostic-action services, then
  full SCL/generated GRAPH sequences/modules/press without power. Reference1500
  retains full capacities and has no150KB limit. No stage/commit/push requested.

- State/alarm evidence FROZEN and verified:3179 SHA bindings,48,891,115 bytes,
 618 source/8 knowledge snapshot files. Previous Access3360 and134 available older
  files verified unchanged. Final audit is outside the archive at
  State_Alarm_20261011/50_final_evidence_audit.json. Never edit its report/raw/
  snapshots/SHA manifest. Fraktal remains RUN; keeper1748 is intentionally alive.

## Station/model config continuation (2026-10-11)

- Owner terminology: station config, line config, model config consistently.
  Current Core/HMI contract and EN/ES group/card labels aligned; stable layout
  keys/canonical members preserved; historical frozen evidence unchanged.
- Generator0.8: explicit typed definitions, owned static editable ParCfg, schema-
  first records, consumed-size keyed LOCAL_RETAIN pool, separate station/model
  restore, ModelId/catalog and atomic prepare/commit/abort across the root subtree.
  Own-frame FCs take components (no FB self pointer); project writes/assembly
  calls rejected. Boolean/integer/TIME/STRING only, Core scope/value80 limits.
- Native120 config,122 access,96 state/alarm on finalV6 pass; primitive retain7
  includes STOP/RUN/power-cycle/private exclusion.190 authored blocks/52 interfaces
  reimport0/0; production183/52 compiler-only0/0.135 tools (hash-seed replay),570 HMI
  pass/1skip,33 consistency; lint/analysis clean. No full Core config/S16 claim.
- Compiler V3 warned6 times on input ParCfg mutation; V4 static ownership fixes0/0.
  V5 separates restore, shares model release and preserves rejected child path.
  V6 fixes nondeterministic component signature order. Escaped Unicode simple-
  path writes rejected-32602 before commit; no PLC Unicode acceptance claim.
- Current saved runtime Config_Runtime_20261011/FrkS12/FrkS12.ap20; Config_Verify
  compiler-only. Fraktal remains RUN with keeper1748; never clean it up by expiry/
  unregister. Approved enumeration driver/pin/DPAPI/physical1214C unchanged.
- Native HMI config cards are on Configuration and require normal ENGINEER display
  access. Operator manual/fault/reset remains separately measured; use actual
  fixture Admin session proves the editor. Live73 PASS:24 modules/556 entries,
  typed Preset21/save/native read/inactive-model isolation/restore10, fault/reset.
  Cached config values ignored newer live readings; mapper fixes that within
  declared capability.32 focused tests and final571 HMI tests/8 opt-in skips pass.
 35 consistency tests pass; readsurface resolves dynamic capability to declared
  Scope/Item/ValueText and still rejects unexplained reads.23 blocking-restore
  native checks prove config-loss Start refusal and one-ack release. Final76
  owner RUN, roots/nested READY/MANUAL, sessionsNONE, no active alarms, defaults
  restored, MODEL_A; StationA historical restore loss remains acknowledged.
- Next named station/model config sets/import/export, other media/user-policy-alarm
  persistence, optional line config replication, floats/enums/arrays/capture/classes,
  then remaining diagnostics/releases/shelving/full SCL+GRAPH/modules/press without
  power. No150KB reference cap; no stage/commit/push requested.
