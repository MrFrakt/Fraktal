# Siemens (TIA Portal) port — implementation plan

Status: **plan, not a commitment — Phase 0 started 2026-10-08.** The binding is
[`Fraktal_TIA_Part_IV.md`](../Fraktal_TIA_Part_IV.md) (draft, spike-ready). The
implementation tree is `FraktalCore/PLC/Siemens/`; at this date it holds the
Openness engineering driver and the first Phase 0 fixture, and no runtime library.

This plan is the third binding's version of
[`ALLEN_BRADLEY_PORT_PLAN.md`](../AllenBradley/ALLEN_BRADLEY_PORT_PLAN.md). It
reuses that plan's discipline — spikes before library, evidence before claims,
gates with the feature they protect — and differs where Siemens differs.

---

## 0. Decisions already taken

| # | Decision | Owner / source | Consequence |
|---|---|---|---|
| D1 | Engineering system is **TIA Portal V20** (STEP 7 Professional) driven through **Openness V20** | project owner, 2026-10-08 | one pinned toolchain; V17–V19 installs on the workstation are ignored |
| D2 | Sequences in **SFC (S7-GRAPH) + ST (SCL)**, permissives and release conditions in **SCL**; **no Ladder** renditions (unlike the AB port) | project owner, 2026-10-08 | Part IV §1, §3.5, §7; no LD generator, no LD gate |
| D3 | Press bench ported **without power control** | project owner, 2026-10-08 | `FB_PowerGroupCM`, control domain, Control On circuit and the §9.8 profile are out of the initial claim |
| D4 | **No paid runtime licence on the default path:** self-description through the CPU's licence-free **Web API** (JSON-RPC over HTTPS) into the Fraktal gateway, as TC3 uses ADS and AB uses CIP; the embedded OPC UA server is an optional, licensed projection. PROFINET IO, PUT/GET, S7CommPlus and Modbus rejected (Part IV §1) | project owner, 2026-10-08 (replaces "embedded OPC UA") | one new gateway session client (`WebApiSessionClient`); the Web HMI is unchanged; the native desktop HMI reaches a TIA station only where OPC UA is licensed; polling replaces subscriptions |
| D5 | **Generated composition** (`FRK_Begin`/`FRK_End` frame) instead of inheritance | Core §2.2 (R0), Part IV §3.1 | generator + lint are first-class deliverables, as on AB |
| D6 | **S7-1500 is the reference family; S7-1200 is a constrained family** | measured facts (§1) | the full press bench is an S7-1500 target; the 1214C carries a declared subset |
| D7 | The physical bench **192.168.0.10** may be downloaded, stopped and reset freely (nothing connected) | project owner, 2026-10-08 | every controller-changing operation still names this target and is logged |

---

## 1. What is measured, and what follows from it

Facts recorded on 2026-10-08 (evidence:
[`TIA_R1_PLATFORM_BASELINE_2026-10-08.md`](Evidence/TIA_R1_PLATFORM_BASELINE_2026-10-08.md)):

| Fact | Source | Consequence |
|---|---|---|
| Bench CPU is **CPU 1214C DC/DC/DC `6ES7 214-1AG40-0XB0`, FW V4.7.3** (not an S7-1500) | S7comm SZL 0x0011 read from the controller | every spike result is S7-1200-scoped |
| 150 KB work memory (code + data), 14 KB retentive, 16 KB OB1 local data | Siemens data sheet, FW V4.7 | the TC3 feature set cannot fit unchanged — the AB port hit an 786 KB ceiling with a smaller feature set |
| OPC UA server: 10 sessions, 5 subscriptions/session, ≤ 1,000 recommended monitored items, 2 server interfaces, 2,000 nodes per user-defined interface, ≤ 20 methods, 100 ms min sampling, "Basic" runtime licence | data sheet + Siemens 109755846 | S7-1200 self-description needs a generated, budgeted server interface |
| Only ISO-on-TCP (102) answers; OPC UA (4840) and web (80/443) are closed (re-probed 2026-10-08 after the S2 runs: also 2000, the fixture's harvest port) | port probe | web server and OPC UA server not configured; PUT/GET off (Part IV §14) |
| S7-GRAPH, `REF_TO` references, named value types, `LTIME`/`LDT`/`ULINT` are **S7-1500 only**; VARIANT, LREAL, WSTRING exist on S7-1200 | TIA V20 information system | S7-1200 sequences are SCL only; enums are DInt constants on both families; no stored references anywhere |
| TIA Portal V20 + Openness V20 installed; Openness first refused the session (account not in `Siemens TIA Openness`) — **resolved** the same day by group membership, a new logon and per-build whitelisting | `Fraktal.Tia.Cli` probe | every driver rebuild needs an administrator's whitelist step (Part IV §5.4) |
| **First bench run:** S2 fixture compiled 0/0, downloaded, 17/17 self-test rows ×3 runs; secure-only PG/PC communication is bound to the project's certificate | [`TIA_S2_S15_FIRST_BENCH_RUN_2026-10-08.md`](Evidence/TIA_S2_S15_FIRST_BENCH_RUN_2026-10-08.md) | the module form and lifecycle composition work on S7-1200; the TIA project is per-station engineering state |
| PLCSIM V20 and PLCSIM Advanced V5.0 installed | inventory | S7-1500/GRAPH evidence is simulation-only until S7-1500 hardware exists |
| **S11 GRAPH leg PASS on PLCSIM Advanced 5.0** (CPU 1516-3 V3.0, headless): a GRAPH chain *generated* from a declaration compiles 0/0, round-trips through TIA's export unchanged, walks the SCL trace, restarts by `INIT_SQ`; 19/19 rows ×3 downloads. A GRAPH FB cannot be a multi-instance, but is accepted as a parameter instance; actions take no `IF`/expression | [`TIA_S11_GRAPH_PLCSIM_2026-10-09.md`](Evidence/TIA_S11_GRAPH_PLCSIM_2026-10-09.md) | the GRAPH form is viable for S7-1500; exit conditions live in transitions; one chart DB per deployed chain; +1 scan per issuing step |

**The honest reading.** Fraktal/TIA is very likely viable on S7-1500 — every
mechanism the TC3 reference needs has a TIA equivalent there — and the open
question is engineering effort. On S7-1200 the open question is **fit**: a
150 KB controller can host the Fraktal lifecycle, contract, diagnostics,
SCL sequences and mailbox for a small tree; whether it can host the press bench
with alarm history, configuration manifest, access table and persistence is
exactly what spike S3 must measure before anyone promises it.

---

## 2. What the binding must deliver

| Part IV section | What Fraktal/TIA must fix | Where it stands |
|---|---|---|
| §1 identity & baseline | families, firmware, TIA version, profiles | drafted; R1 partly evidenced |
| §2 environment | toolchain pins, library distribution, source form, simulation, time, restart/retention | drafted; S4/S5/S11/S16 open |
| §3 language & wiring | module FB form, registry, contract classes, sequences, type map, persistence, Web API / OPC UA exposure, setup, lifecycle | drafted; S1W/S9/S11/S12 open, S2 PASS |
| §4 project settings | OB/task baseline, error OBs, startup, naming | drafted |
| §5 quality tooling | generator, lint, Openness driver, test framework and runner | driver built; rest planned |
| §7–§11 | permissives, gates, access, diagnostics, safety, PROFINET, Web API + optional OPC UA | drafted |
| Annex A/C | exclusions, crosswalk | drafted |

Plus, as on AB, the two things outside the document: the **module library** and
the **gates**.

---

## 3. Mechanism translation (TC3 construct → Fraktal/TIA)

| TC3 construct (Part II) | Count in TC3 Core+Modules* | Fraktal/TIA mechanism | Part IV |
|---|---|---|---|
| `EXTENDS FB_ModuleBase` + `SUPER^` | 18 / 43 | generated frame: `FRK_Begin` … authored regions … `FRK_End`; T-FRAME gate | §3.1, §3.14 |
| protected virtual hooks (`OnInit`, `OnCommandStart`, …) | — | one-shot `Core.Ev.*` flags + generated reaction blocks; `HookResult` | §3.14 |
| `_M_Dispatch` override | per type | `IF #Core.Dispatch THEN CASE #Core.Step OF …` region | §3.1 |
| interfaces `I_Module`/`I_Unit`/… + `__QUERYINTERFACE` | 17 / 6+13 | `FRK_Registry` row index + capability bits | §3.2 |
| `REFERENCE TO` child aliases in sequences | 9 / 20 | **parameter instances** (`VAR_IN_OUT Ram : "FB_CylinderCM"`) | §3.5 |
| provider interfaces (`I_RecipeProvider`, `I_PartCarrier`, `I_PersistMedium`, …) | 15 | provider index + one dispatch FB per seam kind | §3.16 |
| methods (309 in Core) | 309 / 59 | FCs taking the owner's record `InOut`, or mailbox-routed operations on the root | §3.1 |
| `FB_init` / `Setup` | — | first-scan `Setup` driven from OB100's flag, generated call order | §3.11 |
| `{attribute 'OPC.UA.DA'}` | — | `ExternalAccessible`/`ExternalVisible`/`ExternalWritable` member attributes; root = named instance DB | §3.10 |
| enums with `qualified_only` | ~45 | `DInt` + generated constants (same ordinals) | §3.8 |
| `STRING(255)`/`STRING(480)` | — | `String[n≤254]`, family-profile widths; 480-char set lines → pieces (already supported by the mailbox) | §3.8.1 |
| `DT`, `TIME()` monotonic | — | `DTL`/`LDT` (S12), `FRK_Clock` from `RUNTIME` | §2.7, §8.11 |
| `VAR PERSISTENT` + `FB_WritePersistentData` | — | retentive DBs (small) + load-memory DB documents / card files | §3.8b |
| TF6100 TMC-filtered publication | — | standard SIMATIC server interface (S7-1500) / generated user-defined interface (S7-1200) | §3.10.3 |
| TcUnit + TcUnit-Runner | — | `FRK_Test*` SCL framework + `fraktal_tia_test.py` harvest + JUnit | §5.7 |
| XAE `CheckAllObjects` | — | Openness compile through `Fraktal.Tia.Cli` | §5.4 |
| `FRAKTAL_ENGINEERING` compiler define | — | generated constant table; engineering image is a separate generated artifact | §7 |
| TwinCAT SFC/LD XML archives | — | S7-GRAPH SimaticML (published XSD); no LD | §2.5, §3.5 |

\* counts from `ALLEN_BRADLEY_PORT_PLAN.md` §2 (measured on the TC3 tree).

**Two places this binding is better placed than AB.** STEP 7 FBs carry structured
inputs/outputs directly (no "atomic-only parameter" rule), and parameter instances
give a sequence typed access to the children it commands — AB had to route both
through one `InOut` context. **Two places it is worse.** Memory on S7-1200, and the
absence of any stored reference on either family, which forces every generic walk
through the registry.

---

## 4. Target strategy and the memory budget

### 4.1 Three targets, three purposes

| Target | Purpose | Available |
|---|---|---|
| **CPU 1214C V4.7.3 @ 192.168.0.10** | physical evidence: Web API path, timing, memory fit, download/restart behaviour, the S7-1200 profile | **in use** (S15/S2/S5 passed 2026-10-08) |
| **S7-PLCSIM Advanced 5.0 (S7-1500)** | S7-1500 shape: GRAPH rendition, references-free registry on 1500, full press logic | **in use headless** (Runtime API; S11 GRAPH leg 2026-10-09) |
| **Physical S7-1500** (recommended: CPU 1515-2 PN or 1516-3 PN/DP, FW ≥ V3.1; an OPC UA licence only if that projection is evidenced) | reference-family conformance, OPC UA budgets, full press bench | **to procure**; required before any S7-1500 conformance claim |

### 4.2 S7-1200 memory budget (hypothesis — S3 replaces every number)

| Consumer | Budget | Basis |
|---|---|---|
| Framework code (lifecycle FCs, registry, sequence services, mailbox, PermIntlk, alarm ring, minimal config pager) | ≤ 55 KB | SCL code density is unknown on V4.7 — S3 measures `FRK_Begin`/`FRK_End` first |
| Framework data (registry 32 rows, roots' rings at reduced depth) | ≤ 20 KB | compact string-free registry rows; rings sized by profile |
| Module instances | ≤ 2.5 KB each data | `ST_ModuleStatus` at S7-1200 widths ≈ 0.6 KB (vs ≈ 1.4 KB at TC3 widths) |
| Project (press-lite: Unit + 6 CMs + 3 SCL chains + release) | ≤ 45 KB | |
| Reserve (download of changes, growth) | ≥ 15 KB (10 %) | |

**String widths are the biggest lever.** At TC3 widths one `ST_Diagnostic` is
≈ 700 B; at the proposed S7-1200 widths (`SourcePath` 96, `Description` 96,
`IoTag`/`IoAddress` 32) it is ≈ 270 B, and `ST_ModuleStatus` drops from ≈ 1.4 KB to
≈ 0.6 KB. The family profile fixes these; T-WIDTH proves every generated key and
path fits; the HMI reads strings of any length unchanged.

**Exit rule for S7-1200.** If S3 shows press-lite does not fit with ≥ 10 % reserve,
the S7-1200 profile is cut to *base lifecycle + one Unit + CMs + SCL chain +
mailbox + OPC UA*, the press bench becomes S7-1500-only, and Annex A says so.
That is a legitimate binding outcome; quietly over-filling the controller and
discovering it on download (AB press72/73/77/79) is not.

---

## 5. Spikes (Phase 0)

Part IV §12 is the register. Order of execution on the bench, chosen so each
spike's fixture is the next one's starting point:

| Order | Spike | Fixture | Exit evidence |
|---|---|---|---|
| 1 | **S15** automated gate — **PASS (bench) 2026-10-08** | empty project → add 1214C → set IP → compile → download → online state | JSON log of a headless create/compile/download/online run against 192.168.0.10 |
| 2 | **S2** module form — **PASS (fixture, bench) 2026-10-08** | `Spikes/S2_Shape`: `FRK_Begin`/`FRK_End`/`FRK_Hold`, one CM type ×2, one Unit, one SCL chain, parameter instances | compiles warning-clean; self-test rows T1/T4/T2/T3-HELD/rollup/sequence trace PASS ×3 |
| 3 | **S5** harvest — **PASS on the TCP path (bench) 2026-10-08** | same fixture, TCP result server | host harvest of the result table → JUnit; startup-STOP test image still owed |
| 4 | **S12** type map | `S12_TypeMap` | every Core type written by PLC, read by HMI adapter; `DTL` encoding decided; `RUNTIME` drift over 1 h |
| 5 | **S1W/S7/S8** Web API — **S1W PASS (functional, bench), S7 PASS (spike scope) 2026-10-08** | S2 fixture + `webapi_1214c.plan` | layered acceptance (TCP 443 → pinned certificate → `Api.Login` → browse of `SpikeUnit` → batch read cost → writes refused off the mailbox → mailbox ack); then the **unchanged Web HMI** renders the spike Unit through the gateway's `WebApiSessionClient` |
| 6 | **S9** repository parity | S2 + HMI | separate-call `Sequence` commit, stale/expiry, token expiry and re-login, reconnect, no replay |
| 7 | **S3** scale & memory | generated forests of 10/30/60 modules | work-memory use per type, scan time, published leaf count, comm load under Web API polling → fixes the S7-1200 profile |
| 8 | **S11** execution & restart — **GRAPH leg PASS (PLCSIM) 2026-10-09** | S2 (SCL) + `S11_Graph` on PLCSIM 1500 | identical step trace SCL vs GRAPH (**done**: generated chart, 19/19); restart edge by `INIT_SQ` (**done**); STOP→RUN, download-in-RUN, OB100, error OB behaviour; GRAPH supervision/ack modes |
| 9 | **S4** round-trip | every fixture | import → generate source / export → compare canonical |
| 10 | **S6, S13, S16** | dedicated fixtures | online extension, OUC TCP, persistence media |
| — | **S10, S14** | S7-1500 only | optional projections; motion |

**Phase 0 exit:** a written answer per spike, each with a dated evidence record in
`Specification/Siemens/Evidence/`, an explicit go/no-go for each family, and the
S7-1200 profile fixed from S3.

---

## 6. Phases after Phase 0

Each phase ends in evidence. Gates arrive with the feature they protect.

**Phase 1 — Part IV freeze (R3).** Resolve every `[PROVISIONAL]` clause from the
spike answers. Freeze the TIA type map, the Web API (and optional OPC UA) browse projection, the mailbox
layout and the step-table encoding as `TIA_FROZEN_CONTRACTS_V1.json`, gated
against Part IV by `tools/check_tia_contracts.py` (mirror of `check_ab_contracts.py`).
Editorial Core items: the Part I header ("Part I of III") and the binding list
gain Fraktal/TIA; O8's "future: Fraktal/TIA" becomes a reference. *Exit:* R3 PASS.

**Phase 2 — tooling (R4).**

| Tool | Location | Role |
|---|---|---|
| `Fraktal.Tia.Cli` | `PLC/Siemens/tools/TiaCli` | **built** — Openness plans: create/open, add CPU, IP, import SCL/XML, compile, interfaces/scan, guarded download, online state, export |
| `fraktal_tia_declaration.py` | `PLC/Siemens/tools` | the declaration model: families/profiles, types, instances, chains, reasons |
| `fraktal_tia_generate.py` | ″ | emits SCL frames, constants table XML, GRAPH SimaticML, server-interface definition, setup order, retention list |
| `fraktal_tia_graph.py` + `graph_dump.py` | ″ | GRAPH SimaticML writer **and reader** (every generated chart is dumped and compared to its declaration) |
| `tia_lint.py` | ″ | the T-rules of Part IV §5.3 |
| `fraktal_tia_test.py` | ″ | download test image, wait, harvest, JUnit |
| `s7_probe.py` | ″ | **built** — read-only S7comm identification (SZL) of a target; TCP result-table harvest → JUnit |
| `tia_webapi.py` | ″ | **built** — Web API probe (S1W): certificate pinning, login from the environment, browse tree, batch snapshot timing, mailbox commit/ack; the reference for the gateway's `WebApiSessionClient` |
| `Invoke-FraktalTiaGate.ps1` | ″ | lint → generate → import/compile (both families) → optional bench test |

*Exit:* a fresh clone regenerates and compiles every fixture warning-clean for
both families; each deliberately broken invariant is rejected by a named rule;
canonical round-trip stable (R4).

**Phase 3 — communication vertical slice.** One root, one CM, registry, mailbox
(`SET_MODE`, `START`, `STOP`, `OPERATOR_RESET`, `MANUAL_COMMAND`), the gateway's
`WebApiSessionClient` (`FraktalCore/HMI/packages/fraktal_opcua_client`, beside
`AdsSessionClient`), on the 1214C. *Exit:* the unchanged HMI discovers,
renders and commands it; stale data, disconnect, rejected write and reconnect
fail closed; latency measured.

**Phase 4 — runtime base (`Fraktal_Core_TIA`).** Object-by-object in §7.1's order;
the base suite (`FRK_Test_Base`) grows with each behaviour. *Exit:* a single
generated CM satisfies T1–T5 on the bench and on PLCSIM 1500; T6–T10 mechanisms
proven once.

**Phase 5 — module library (`Fraktal_Modules_TIA`).** §7.2's set, each with its
suite. *Exit:* all base and type suites green on both targets; a scan/memory
report per type.

**Phase 6 — press bench without power control.** §7.3. *Exit:* the full bench runs
on S7-1500 (PLCSIM until hardware; then hardware), press-lite runs on the 1214C;
the unchanged HMI operates both; integration suites green.

**Phase 7 — GRAPH renditions and rendition parity.** AUTO, HOME, CHANGEOVER and
LoadPosition generated as S7-GRAPH for S7-1500 from the same graph declaration as
their SCL renditions; rendition gate green; identical step traces on PLCSIM.

**Phase 8 — conformance audit.** Clause-by-clause against Core and O1–O10, as AB
Phase 8. *Exit:* no unexplained deviation; every remaining limitation is a
versioned Annex A entry.

---

## 7. Work breakdown

### 7.1 Core (`Fraktal_Core` → `Fraktal_Core_TIA`)

Order is dependency order. "1200" = in the S7-1200 profile (✔ yes, ◐ reduced,
✘ excluded pending S3/S16).

| # | TC3 source | TIA artifact | 1200 | Notes |
|---|---|---|---|---|
| C1 | `DUTs/E_*` (≈45 enums) | `FRK_Constants` user-constant table (generated) | ✔ | ordinals generated from the TC3 DUTs; a gate diffs both |
| C2 | `DUTs/ST_*` contract records | `.udt` PLC data types at family widths | ✔ | `ST_ModuleStatus`, `ST_Diagnostic`, `ST_StepRecord`, `ST_CondRecord`, `ST_ModuleTiming`, `ST_HmiRequest/Response`, `ST_ReleaseReport`, … |
| C3 | `Params/PL_Fraktal*`, `PL_ReasonCatalog` | generated constants + `F_ReasonMeta` FC | ✔ | from `reason_rationalization.json` |
| C4 | `Platform/F_Now`, `F_TimeSynchronized`, `GVL_FraktalTime` | `FRK_Now` FC, `FRK_Clock`/`FRK_Time` global DBs | ✔ | S1/S12 |
| C5 | `FB_ModuleBase` (lifecycle) | `FRK_Begin`, `FRK_End`, `FRK_Complete`, `FRK_Fault`, `FRK_Hold`, `FRK_State` FCs + `FRK_Core` UDT | ✔ | the heart; Phase 3/4 |
| C6 | `I_Module` family | `FRK_Registry` DB + `FRK_RegistryRow` + `FRK_Reg*` FCs | ✔ | capability bits from declaration |
| C7 | `FB_ControlModuleBase`, `FB_EquipmentModuleBase`, `FB_CompositeModuleBase` | tier rules inside `FRK_Begin/End` + generated child-call list | ✔ | no separate blocks — tier is data |
| C8 | `FB_SequenceBase`, `I_Sequence(Host)` | `FRK_SeqCtx` UDT + `FRK_Seq_*` FCs | ✔ | SCL form; GRAPH uses the same FCs |
| C9 | `FB_PermIntlk` | `FB_PermIntlk` (SCL) | ✔ | condition records, first-out |
| C10 | `FB_UnitBase` (mode, start/stop, chains, mailbox, release, rollup, part, OEE…) | `FRK_UnitBegin`/`FRK_UnitEnd` + `FB_FrkMailbox` + `FRK_Release*` | ◐ | split by concern so S7-1200 can omit OEE/line/shift |
| C11 | `FB_AlarmLog`, `F_RationalizeDiagnostic` | `FB_AlarmLog` | ◐ | ring depth by profile |
| C12 | `FB_ConfigPager`, `ST_Config*` | `FB_ConfigPager` (paged manifest) | ◐ | 480-char lines in pieces (existing mailbox rule) |
| C13 | `FB_AccessManager`, `FB_LocalAccessProvider`, `F_Sha256` | same names | ◐ | hashes in a load-memory document |
| C14 | `FB_CycleProfiler` | `FB_CycleProfiler` | ◐ | Pareto excluded on 1200 |
| C15 | `FB_SignalTower` | `FB_SignalTower` | ✔ | |
| C16 | `FB_EngineeringMode`, `PL_FraktalEngineering` | `FB_EngineeringMode` + constant gate | ✔ | |
| C17 | `FB_HostEventPublisher` | `FB_HostEventPublisher` | ◐ | |
| C18 | `FB_SystemHealthPublisher`, `FB_TcSystemHealthProbe` | `FB_SystemHealthPublisher` + `FB_S7HealthProbe` | ◐ | declared exclusions for unsupplied metrics |
| C19 | `FB_IoTopologyPublisher`, `FB_EcBusHealth` | `FB_IoTopologyPublisher` + `FB_PnBusHealth` | ◐ | PROFINET instead of EtherCAT |
| C20 | `FB_LocalRecipeProvider`, `FB_LocalPartCarrier` | same, behind provider dispatch | ✔ | |
| C21 | `I_PersistMedium` family (`FB_FilePersistMedium`, `FB_RetainPersistMedium`, `FB_MediumConfigStore`, `FB_ConfigSetDocument`, `FB_ConfigSetJson`, `F_Crc32`) | `FB_LoadDbMedium`, `FB_CardFileMedium` (1500), `FB_RetainMedium`, `FB_MediumConfigStore`, `FB_ConfigSetJson` | ◐ | S16 |
| C22 | `FB_LineData*`, `FB_ShiftSchedule` | same | ✘ | Line profile: S7-1500 first |
| C23 | `FB_DeviceConnectorBase`, `FB_AsciiLink`, `FB_TcpChannelTc3`, `FB_SimByteChannel` | `FB_DeviceConnectorBase`, `FB_AsciiLink`, `FB_TcpChannelS7`, `FB_SimByteChannel` | ◐ | S13 |
| C24 | `DeviceCMs/FB_TcpVisionCM`, `FB_TcpCodeReaderCM` | same | ✘ | after S13 |
| C25 | TC3-only: `FB_TcWindowsTime`, `FB_TcIpcDiagnostics`, `F_TcWindowsClockCrc`, `FB_PersistentDataWriter`, `FB_LineAdsSource`, `FB_EcFieldbusScanner` | — | — | no TIA equivalent needed |

### 7.2 Modules (`Fraktal_Modules` → `Fraktal_Modules_TIA`)

| # | TC3 type | Priority | 1200 | Notes |
|---|---|---|---|---|
| M1 | `FB_CylinderCM` + `FB_CylinderSim` | P1 | ✔ | first generated type; T1–T5 |
| M2 | `FB_DigitalInputCM` | P1 | ✔ | |
| M3 | `FB_TwoHandStartCM` | P1 | ✔ | HELD semantics (§6.1) |
| M4 | `FB_AirPressureMonitorCM` | P1 | ✔ | "air loss held" — kept: process monitor, not power control |
| M5 | `FB_ClampEM` | P1 | ✔ | the composite/rollup proof (T6) |
| M6 | `FB_ConfigurableCylinderCM` + sim | P2 | ✔ | |
| M7 | `FB_SeparatorCM` | P2 | ✔ | Annex A worked example |
| M8 | `FB_AxisCM` | P2 | ◐ | S14; press `PartFeed` |
| M9 | `FB_RobotCM`, `FB_RobotRoutePlanner`, `FB_SimRobotConnector`, `FB_StaubliVal3Connector` | P3 | ✘ | after S13/S14 |
| M10 | `FB_Iv3VisionCM`, `FB_Matrix220CM` | P3 | ✘ | after S13 |
| M11 | `FB_PowerGroupCM` | — | — | **out of scope (D3)** |

### 7.3 Press bench without power control (`Fraktal_Press_Demo` → `Fraktal_Press_TIA`)

| TC3 object | TIA | Notes |
|---|---|---|
| `MAIN` | OB1 `Main` → `FB_PressMain` (composition FB) | scan order; no raw channels |
| `FB_PressDemoUnit` (`PneumaticPress`) | instance DB `PneumaticPress` of `FB_PressUnit` | children: `PressRam`, `Door`, `PartSlide` (cylinder), `TwoHand`, `PartPresentSensor`, `AirPressureMonitor`, `PartFeed` (axis) — **`PneumaticPower` removed** |
| `Sequences/FB_PressDemoHome`, `…Changeover`, `…Auto`, `…LoadPosition` | SCL chains (both families) | same step numbers and names as TC3; parameter instances for the children |
| `FB_SFC_PressDemoAuto` | **S7-GRAPH** `FB_PressAutoGraph` (S7-1500) | generated from the same graph; rendition gate vs. SCL |
| `FB_LD_PressDemoAuto`, `Release/FB_LD_PressDemoRelease` | — | **not ported (D2)** |
| `Release/FB_PressDemoRelease`, `FB_PressDemoReleaseState`, `ST_PressDemoReleaseConditions` | SCL, under `01_PneumaticPress/Release` | the Unit's release report remains the one execution predicate |
| `Recipes/FB_PressRecipeCatalog` | SCL | |
| `Io/FB_PressIoCatalog`, `GVL_PressFieldbus` | SCL + `PressFieldbus` DB | PROFINET topology instead of EtherCAT |
| `FB_PressIoDriver`, `GVL_PressIO` | `FB_PressIoDriver` + tag table `IO_Press` | the bench has no field I/O: the driver runs in simulation; the 1214C's onboard DI/DQ may stand in for a few channels |
| `FB_PressSimulationDriver` | same | |
| `FB_PressOutputAuthority` | same, minus power coils | |
| `FB_PressControlDomain`, `FB_PressControlOnCircuit`, `GVL_PressSafety` | — | **out of scope (D3)** |
| `GVL_PressCommissioning` gates | constant table | `USE_SIMULATION` stays a build constant; `CONTROL_CIRCUIT_MAPPING_CONFIRMED` disappears with the control circuit |
| `PL_PressReasons` | generated constants | band unchanged |
| `MAIN` services: `Storage`, `ConfigStore`, `PartCarrier`, `AccessUsers`, `PressLine`, `HealthProbe`, `EngineeringMode` | per §7.1 availability | `PressLine` (Line profile) S7-1500 only |

**Press-lite (S7-1200).** `PneumaticPress` with `PressRam`, `Door`, `PartSlide`,
`TwoHand`, `PartPresentSensor`, `AirPressureMonitor`; HOME/AUTO/LoadPosition SCL
chains; release; mailbox; reduced rings; no Line, no `PartFeed` axis until S14,
CHANGEOVER only if S3 leaves room. Final scope set by S3.

### 7.4 Tests

| TC3 gate | TIA gate | Runs on |
|---|---|---|
| `Tests/Fraktal_Tests` (Core + Modules TcUnit) | `Tests/Fraktal_Tests_TIA`: `FRK_Test_Base` (T1/T4, T2/T6/T7/T10 mechanisms) + one suite per module type | 1214C (S7-1200 profile) and PLCSIM 1500 |
| `Examples/PressDemo/PressTests` | `Examples/PressDemo/PressTests_TIA` | PLCSIM 1500 (full), 1214C (press-lite) |
| `plc_lint.py`, `check_consistency.py` | `tia_lint.py`; `check_consistency.py` extended to the TIA tree (localization keys, suite inventory, rendition parity) | host |

---

## 8. Repository layout

```
FraktalCore/PLC/Siemens/
├── README.md
├── tools/                    TiaCli/ (Openness driver), s7_ident.py, generator, lint, test runner
├── Spikes/                   disposable Phase 0 fixtures (S2_Shape, S12_TypeMap, S11_Graph, …)
├── Framework/Fraktal_Core_TIA/      (Phase 4) generated + authored SCL sources
├── Framework/Fraktal_Modules_TIA/   (Phase 5)
├── Examples/PressDemo/              (Phase 6) Fraktal_Press_TIA + PressTests_TIA
└── Tests/                           (Phase 4) Fraktal_Tests_TIA
Specification/
├── Fraktal_TIA_Part_IV.md
└── Siemens/                  this plan, handovers, Evidence/ (append-only)
```

TIA projects (`*.ap20`) are build outputs written under a scratch directory and
never committed; the committed form is source plus the plan files that build it.

---

## 9. Risks

| Risk | Likelihood | Effect | Mitigation |
|---|---|---|---|
| S7-1200 memory cannot hold press-lite | **high** | 1200 claim narrows | S3 early; family widths; feature omission; exit rule §4.2 |
| S7-1200 G1 V4.7 Web API narrower than the 11/2025 manual (written for S7-1500 / 1200 G2): a method or data type (`DTL`, `WString`) missing | medium | S1W narrows; derived members or OPC UA (licensed) | `tia_webapi.py probe` lists the method set first; S12 type map decides encodings |
| Web API polling load raises S7-1200 scan time or exceeds its request budget | medium | slow HMI on 1200 | tiered reads (fast tier only at display rate), batch size from S1W, `Api.GetQuantityStructures` |
| No OPC UA runtime licence | certain on the bench | only the optional projection is affected | the default path needs none (D4) |
| Openness access blocked by IT policy | resolved by group membership | — | documented prerequisite (Part IV §5.4) |
| Every driver rebuild needs an administrator to re-whitelist it (Openness firewall is per exe hash, headless included) | **certain** | CI on an unattended agent cannot rebuild the driver | batch driver changes; generic reflection commands; pin a released driver build per agent and whitelist it once at agent setup |
| Engineering lockout when a project's certificate is lost (station project deleted, workstation rebuilt) | medium | no download until a logged trust-on-first-use recovery | station projects under `%LOCALAPPDATA%\Fraktal\TiaStations`, part of the workstation backup; `--trust-plc` recovery documented |
| `DTL` not served as one value (Web API) or as DateTime (OPC UA) | medium | contract change for `Since` | S12 decides; derived member |
| GRAPH semantics (interlock/supervision, skip/ack modes) conflict with Fraktal's step record | medium (actions, transitions, restart now measured) | GRAPH form narrowed | supervision/ack still open in S11; SCL remains reference |
| PLCSIM not automatable headless | **retired 2026-10-09** | — | PLCSIM Advanced 5.0 registered, downloaded and harvested headless (S11) |
| SCL code density higher than assumed | medium | budgets slip | measure `FRK_Begin`/`End` first (S2/S3) |
| Download of changes reinitializes registry/instances | medium | commissioning workflow | S6; registry headroom by profile |

---

## 10. Honest estimate (shape, not schedule)

| Phase | Relative size | Note |
|---|---|---|
| 0 spikes | medium | the 1214C bench and Openness make most spikes cheap once access is granted |
| 1 freeze | small | |
| 2 tooling | **medium–large** | generator + GRAPH writer/reader + lint + runner; reuses AB's generator experience |
| 3 vertical slice | small–medium | one new gateway session client (Web API), the HMI unchanged |
| 4 runtime base | **large** | 309 Core methods change shape into FCs/frames; memory pressure on 1200 |
| 5 library | medium | mechanical after Phase 4 |
| 6 press bench | medium | three chains + release + catalog; power control removed |
| 7 GRAPH renditions | medium | depends on S11 |
| 8 audit | medium | |

---

## 11. Immediate next steps

Done on 2026-10-08: Openness access; S15; S2 fixture compiled 0/0, downloaded,
17/17 ×3 on hardware; S5 TCP harvest; station-project workflow; ASCII rebuild
17/17 ×3; **S1W PASS (functional, bench)** — web server, certificate, UMAC user,
browse/read/write-refusal/mailbox measured, throughput ≈ 57 ms/request + 15 ms/leaf
on the 1214C ([evidence](Evidence/TIA_S1W_WEBAPI_2026-10-08.md)).

1. **Gateway `WebApiSessionClient`** — **done 2026-10-08** (client, `s7web://` gateway
   transport, 11 unit tests, live end-to-end through the gateway; evidence §9) and
   **S7 PASS (bench, spike scope)**: the unchanged Web HMI discovered, rendered and
   commanded the spike Unit (evidence §10). Original scope: a third session client in
   `FraktalCore/HMI/packages/fraktal_opcua_client` beside `AdsSessionClient`, selected
   by its endpoint scheme; pinned-certificate HTTPS, login once (re-login on an
   invalid token, never on `101 Already Authenticated`), browse → the snapshot model,
   leaf-only reads (structures and `DTL` member by member), a fast tier sized for
   ≈ 15 ms/leaf, the mailbox commit as `tia_webapi.py mailbox` does it. Exit: the
   unchanged Web HMI renders and commands the spike Unit.
2. **S9 remainder over the Web API:** token expiry and re-login, CPU STOP/RUN and
   cable-pull recovery, two concurrent clients, snapshot coherence within one batch.
3. **S3 polling cost** — done (+0.23 ms mean cycle under continuous full-tree Web API
   polling, S1W evidence §8).
4. **S3 memory and per-module cost** — first numbers 2026-10-08
   ([evidence](Evidence/TIA_S3_SCAN_AND_MEMORY_2026-10-08.md)): S2 image 19.6 KB work
   memory (only the CPU's system web page reports it — Openness, SZL and the Web API
   do not); idle CM 0.20 ms/scan → 0.053 ms with the **quiescent fast path** now in the
   generated frame (Part IV §3.14); **≈ 1.16 KB work memory per minimal CM** (S2 + 10/30
   CMs). Owed: the Unit's fast path and the real generated types' sizes (alarm ring,
   step table, configuration); then fix the S7-1200 profile widths/capacities. No
   library code before these numbers exist.
5. **S11 GRAPH leg on S7-PLCSIM — done 2026-10-09**
   ([evidence](Evidence/TIA_S11_GRAPH_PLCSIM_2026-10-09.md)). `fraktal_tia_graph.py` generates the AUTO chain as GRAPH
   SimaticML from `S11_Graph/chain_auto.json` against TIA's exported reference chart
   and dumps any chart back. It compiled 0/0 on the `FrkS11` station, and TIA's
   re-export dumps identical. It ran on PLCSIM Advanced 5.0, headless, with the SCL
   chain's trace and a mid-run `INIT_SQ` restart (19/19). Measured design facts, now
   in Part IV §3.5: actions take no `IF`/expression, so exit conditions sit in the
   transitions; the GRAPH FB is a parameter instance, never a multi-instance; and
   Execute is raised one scan after entry. Still owed in S11: GRAPH
   supervision/acknowledge modes, STOP→RUN, download-in-RUN, error OBs.
6. **Tooling Phase 2 start** — `tia_lint.py` **done 2026-10-08** (11 rules + 18 tests, pre-commit;
   T-TIER/T-IO/T-WIDTH/T-GEN pending the generator). Original scope: `tia_lint.py` with T-FRAME, T-CYCLIC, T-EXT, T-ASCII,
   T-KEYWORD, T-COLLIDE, T-OWNIO, T-TYPEFILE over `Spikes/`, wired into
   `.githooks/pre-commit` beside `plc_lint`.
