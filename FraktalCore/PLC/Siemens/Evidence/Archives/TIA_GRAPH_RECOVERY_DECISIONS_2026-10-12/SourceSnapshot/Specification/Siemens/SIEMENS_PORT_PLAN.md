# Siemens (TIA Portal) port — implementation plan

Status: **plan, not a commitment — Phase 0 started 2026-10-08.** The binding is
[`Fraktal_TIA_Part_IV.md`](../Fraktal_TIA_Part_IV.md) (draft, spike-ready). The
implementation tree is `FraktalCore/PLC/Siemens/`; at this date it holds the
Openness engineering driver and the first Phase 0 fixture, and no released runtime library. A shared command-kernel prototype now exists.

This plan is the third binding's version of
[`ALLEN_BRADLEY_PORT_PLAN.md`](../AllenBradley/ALLEN_BRADLEY_PORT_PLAN.md). It
reuses that plan's discipline — spikes before library, evidence before claims,
gates with the feature they protect — and differs where Siemens differs.

---

## 0. Decisions already taken

| # | Decision | Owner / source | Consequence |
|---|---|---|---|
| D1 | Engineering system is **TIA Portal V20** (STEP 7 Professional) driven through **Openness V20** | project owner, 2026-10-08 | one pinned toolchain; V17–V19 installs on the workstation are ignored |
| D2 | Sequences in **SFC (S7-GRAPH) + ST (SCL)**; optional **LD examples**; GRAPH sequences and ST release wired in the press demo | project owner, 2026-10-08; examples added by explicit directive 2026-10-11 | Part IV §1, §3.5, §7; generate and read back every native chart/rung; owner requested demo wiring on 2026-10-12; physical testing pending |
| D3 | Press bench ported **without power control** | project owner, 2026-10-08 | `FB_PowerGroupCM`, control domain, Control On circuit and the §9.8 profile are out of the initial claim |
| D4 | **No paid runtime licence on the default path:** self-description through the CPU's licence-free **Web API** (JSON-RPC over HTTPS) into the Fraktal gateway, as TC3 uses ADS and AB uses CIP; the embedded OPC UA server is an optional, licensed projection. PROFINET IO, PUT/GET, S7CommPlus and Modbus rejected (Part IV §1) | project owner, 2026-10-08 (replaces "embedded OPC UA") | one new gateway session client (`WebApiSessionClient`); the Web HMI is unchanged; the native desktop HMI reaches a TIA station only where OPC UA is licensed; polling replaces subscriptions |
| D5 | **Generated composition** (`FRK_Begin`/`FRK_End` frame) instead of inheritance | Core §2.2 (R0), Part IV §3.1 | generator + lint are first-class deliverables, as on AB |
| D6 | **S7-1500 is the reference family; S7-1200 is a constrained family** | measured facts (§1) | the full press bench is an S7-1500 target; the 1214C carries a declared subset |
| D7 | The physical bench **192.168.0.10** may be downloaded, stopped and reset freely (nothing connected) | project owner, 2026-10-08 | every controller-changing operation still names this target and is logged |

**Implementation priority (owner clarification, 2026-10-10):** build the full
reference implementation on the simulated S7-1500, including SCL and generated
S7-GRAPH. The existing CPU1516-3 V3.0 / PLCSIM Advanced 7.0 is the current
simulation prototype. The physical 1214C is a secondary compatibility and hardware
test bench. Its 150 KB limit, compact S3 capacities and press-lite fit shall not
gate or reduce the S7-1500 implementation. Use the reference CPU's own limits;
retain Core capacities subject to actual Siemens representation requirements.
Resolve prototype firmware against the declared reference baseline before a
reference conformance claim. Preserve all dated S7-1200 evidence as S7-1200 evidence.

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
| PLCSIM V20 and PLCSIM Advanced7 installed; earlier Advanced5 results remain frozen | inventory + S12 upgrade record | S7-1500/GRAPH evidence is simulation-only until S7-1500 hardware exists |
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
| `STRING(255)`/`STRING(480)` | — | S7-1500 width-preserving WString candidates; S7-1200 compact widths/pieces remain a separate profile | §3.8.1 |
| `DT`, `TIME()` monotonic | — | reference1500 `LDT` with type-aware Web API codec;1200 DTL projection provisional; `FRK_Clock` from `RUNTIME` | §2.7, §8.11 |
| `VAR PERSISTENT` + `FB_WritePersistentData` | — | retentive DBs (small) + load-memory DB documents / card files | §3.8b |
| TF6100 TMC-filtered publication | — | standard SIMATIC server interface (S7-1500) / generated user-defined interface (S7-1200) | §3.10.3 |
| TcUnit + TcUnit-Runner | — | `FRK_Test*` SCL framework + `fraktal_tia_test.py` harvest + JUnit | §5.7 |
| XAE `CheckAllObjects` | — | Openness compile through `Fraktal.Tia.Cli` | §5.4 |
| `FRAKTAL_ENGINEERING` compiler define | — | generated constant table; engineering image is a separate generated artifact | §7 |
| TwinCAT SFC/LD XML archives | — | Generated S7-GRAPH and optional LAD examples, with native export readback | §2.5, §3.5 |

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
| **S7-PLCSIM Advanced7 (S7-1500)** | S7-1500 shape: GRAPH rendition, references-free registry on1500, full press logic | **verified headless** through the updated API5 compatibility DLL; native Web API recovery and LDT mapping pass in S12 |
| **Physical S7-1500** (recommended: CPU 1515-2 PN or 1516-3 PN/DP, FW ≥ V3.1; an OPC UA licence only if that projection is evidenced) | reference-family conformance, OPC UA budgets, full press bench | **to procure**; required before any S7-1500 conformance claim |

### 4.2 S7-1200 memory budget (hypothesis — S3 replaces every number)

| Consumer | Budget | Basis |
|---|---|---|
| Framework code (lifecycle FCs, registry, sequence services, mailbox, PermIntlk, alarm ring, minimal config pager) | ≤ 55 KB | SCL code density is unknown on V4.7 — S3 measures `FRK_Begin`/`FRK_End` first |
| Framework data (registry 32 rows, roots' rings at reduced depth) | ≤ 20 KB | compact string-free registry rows; rings sized by profile |
| Module instances | ≤ 2.5 KB each data | S3 compact status + six state rows averages 1.43 KB/module, before private lifecycle/device/config-write storage; the complete-instance target remains unproven |
| Project (press-lite: Unit + 6 CMs + 3 SCL chains + release) | ≤ 45 KB | |
| Reserve (download of changes, growth) | ≥ 15 KB (10 %) | |

**Use compiled allocation, not a sum of string widths.** S3 2026-10-10 measures
full Core-derived UDTs in optimized, non-retentive DB arrays; TIA re-export proves
every field/type, count and access attribute. Six state rows/module and candidate
96-character identities/keys, 32-character I/O names reduce the 16-module
status/state group from 47.03 to 22.84 KB added work memory. Those are group
deltas including DB overhead, not standalone status-record sizes. The profile
and full press fit remain provisional; T-WIDTH must prove every generated key
and path fits, and reduced capacity must reject overflow explicitly.

**Dense write metadata breaks the per-module target.** The isolated eight-row
compact `ST_ConfigWriteDef` array adds **5.49 KB** before any lifecycle/device
data. TC3's `FB_ModuleBase` owns a maximum-sized write array per instance; do not
copy that allocation into the 1200 generator. Share immutable metadata by type,
derive identity from the registry, and allocate only consumed instance-dependent
state. The configuration page/snapshot still needs its value-keyed contract;
pointer-to-index substitution in S3 is an allocation probe, not a working writer.

**Exit rule for S7-1200.** If S3 shows press-lite does not fit with ≥ 10 % reserve,
the S7-1200 profile is cut to *base lifecycle + one Unit + CMs + SCL chain +
mailbox + Web API*, the press bench becomes S7-1500-only, and Annex A says so.
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
| 8 | **S11** execution & restart — **partial, measured 2026-10-10** | S2/S11_Scl physical 1214C + S11_Graph PLCSIM 1500 | GRAPH parity/supervision/ack/skip done (28/28); active reset/STOP→RUN and FC delta done on PLCSIM (16 recovery checks). GRAPH body delta requires native turn-off/DB reinitialization; quiesced deployment workflow, retention and other modes/errors remain. Physical SCL idle deltas/restart 19/19 and diagnostics role restored |
| 9 | **S4** round-trip | every fixture | import → generate source / export → compare canonical |
| 10 | **S6, S13, S16** | dedicated fixtures | online extension, OUC TCP, persistence media |
| — | **S10, S14** | S7-1500 only | optional projections; motion |

**Phase 0 exit:** a written answer per spike, each with a dated evidence record in
`Specification/Siemens/Evidence/`, an explicit go/no-go for each family, and the
selected family's applicable profile fixed. The S7-1500 reference track proceeds
independently of the constrained1200 profile's fit/width/capacity work.

---

## 6. Phases after Phase 0

Each phase ends in evidence. Gates arrive with the feature they protect.

**Phase 1 — Part IV freeze (R3).** Resolve the S7-1500 reference track's
`[PROVISIONAL]` clauses from its spike answers. Freeze its type map, the Web API
(and optional OPC UA) browse projection, the mailbox
layout and the step-table encoding as `TIA_FROZEN_CONTRACTS_V1.json`, gated
against Part IV by `tools/check_tia_contracts.py` (mirror of `check_ab_contracts.py`).
Editorial Core items: the Part I header ("Part I of III") and the binding list
gain Fraktal/TIA; O8's "future: Fraktal/TIA" becomes a reference. *Exit:* R3 PASS.

**Phase 2 — tooling (R4).**

The initial [declaration-model slice](Evidence/TIA_R4_DECLARATION_MODEL_2026-10-10.md)
validates reusable types and a two-root forest, derives eight registration rows
and rejects structural violations. The
[frame/registry slice](Evidence/TIA_R4_FRAME_REGISTRY_2026-10-10.md) now emits
typed contracts, HAL bundles/calls, identity setup and compact registry services.
The two-root fixture passes103 runtime assertions and canonical36-block/19-
interface read-back/reimport. Manifest-scoped replay checks generated source;
the broader rules remain pending. Begin/end FCs in this fixture are test-only
probes. The separate shared command kernel now implements command/reset/abort/
HELD/timeout/timing semantics and generation includes it with --shared-runtime.
Its55 cases/238 assertions and native/public/private checks pass; full Core/Unit
facets remain required.

| Tool | Location | Role |
|---|---|---|
| `Fraktal.Tia.Cli` | `PLC/Siemens/tools/TiaCli` | **built** — Openness plans: create/open, add CPU, IP, import SCL/XML, compile, interfaces/scan, guarded download, online state, export |
| `fraktal_tia_declaration.py` | `PLC/Siemens/tools` | **started2026-10-10** - strict reference type/forest model and registration inventory; Core-derived widths/tier ordinals; chains, HAL, capabilities, reasons and additional profiles remain |
| `fraktal_tia_generate.py` | ″ | **started2026-10-10**: common contract frames, typed HAL bundles/calls, registry/setup and replay manifest; constants table XML, GRAPH integration, server-interface and retention list remain |
| `fraktal_tia_runtime.py` | PLC/Siemens/tools | shared command kernel from Framework/Core template; Core enums/capacities/rationalization are generated once, replayed by the frame manifest |
| `fraktal_tia_graph.py` + `graph_dump.py` | ″ | GRAPH SimaticML writer **and reader** (every generated chart is dumped and compared to its declaration) |
| `tia_lint.py` | ″ | the T-rules of Part IV §5.3 |
| `fraktal_tia_test.py` | ″ | download test image, wait, harvest, JUnit |
| `s7_probe.py` | ″ | **built** — read-only S7comm identification (SZL) of a target; TCP result-table harvest → JUnit |
| `tia_webapi.py` | ″ | **built** — Web API probe (S1W): certificate pinning, login from the environment, browse tree, batch snapshot timing, mailbox commit/ack; the reference for the gateway's `WebApiSessionClient` |
| `Invoke-FraktalTiaGate.ps1` | ″ | lint → generate → import/compile (both families) → optional bench test |

*Exit:* a fresh clone regenerates and compiles the S7-1500 reference fixtures
warning-clean; each deliberately broken invariant is rejected by a named rule;
canonical round-trip stable (R4). The1200 profile has its own subsequent gate.

**Phase 3 — communication vertical slice.** One root, one CM, registry, mailbox
(`SET_MODE`, `START`, `STOP`, `OPERATOR_RESET`, `MANUAL_COMMAND`), the gateway's
`WebApiSessionClient` (`FraktalCore/HMI/packages/fraktal_opcua_client`, beside
`AdsSessionClient`), on the simulated S7-1500; existing1214C evidence is supporting
hardware evidence. *Exit:* the unchanged HMI discovers,
renders and commands it; stale data, disconnect, rejected write and reconnect
fail closed; latency measured.

**Phase 4 — runtime base (`Fraktal_Core_TIA`).** Object-by-object in §7.1's order;
the base suite (`FRK_Test_Base`) grows with each behaviour. *Exit:* a single
generated CM satisfies T1–T5 on PLCSIM1500; T6–T10 mechanisms proven once there.
Physical reference validation follows when hardware is available;1200 subset
validation is independent.

**Phase 5 — module library (`Fraktal_Modules_TIA`).** §7.2's set, each with its
suite. *Exit:* all base and type suites green on the simulated S7-1500 reference
target; a target-scoped resource report per type. The1200 subset follows separately.

**Phase 6 — press bench without power control.** §7.3. *Exit:* the full bench runs
on S7-1500 (PLCSIM until hardware; then hardware), the unchanged HMI operates it,
and integration suites are green. A1214C press-lite is a separate constrained
compatibility deliverable and does not block the reference press.

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
| `FB_SFC_PressDemoAuto` | **S7-GRAPH** `FB_GRAPH_PressDemoAuto` (S7-1500) | generated from the same graph; rendition gate vs. SCL |
| `FB_LD_PressDemoAuto`, `Release/FB_LD_PressDemoRelease` | — | optional examples; uninstantiated (owner extension to D2) |
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
| GRAPH semantics (interlock/supervision, skip/ack modes) conflict with Fraktal's step record | medium (actions, transitions, restart and supervision now measured) | GRAPH form narrowed | V/C networks empty, skip disabled; manual/semi-auto still open in S11; SCL remains reference |
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

**Current priority: S7-1500 reference implementation.** Extend the measured shared
command/Unit services through the native Phase3 forest/rendering/mailbox slice,
then complete release frontiers and alarm/state/recipe/retention services, modules
and full press without power control. Validate
SCL/GRAPH parity as each chain arrives. The S7-1200 S3 numbers below are retained
compatibility results; no 150 KB cap or compact profile applies to this track.

S12/S4 continued2026-10-10 on isolated simulated1516 station FrkS12: complete
88-type/610-field layout,269-source canonical round-trip,1405/1405 SDK witnesses
and43/43 scalar checks including295 enum constants and wide-string operations.
The strict parser is shared in tools/fraktal_tia_types.py. The host-time hour
fails tolerance; simulator-time accumulation agrees within8.664ms over the
separate ten-minute comparison. At that Advanced5 scope, symbolic CPU Web API
reads remained denied despite login/read_value and a diagnostic-right control.
See
[S12/S4 evidence](Evidence/TIA_S12_TYPES_ROUNDTRIP_2026-10-10.md).
Native isolation controls now reproduce the denial with a three-field DB;
a valid token reads RUN with diagnostic permission, but symbolic reads remain2.
Cold restart and CommunicationMode0 do not fix it. Full1405/1405 and43/43
witnesses pass after restoring the complete image, mode1 and process-data rights.
See [native isolation evidence](Evidence/TIA_S12_WEBAPI_RECOVERY_2026-10-10.md).
The owner installed Advanced7; symbolic Read/Browse now work on the preserved
DTL image before any program/configuration change. The upgrade also replaced
API5's compatibility DLL and virtual adapter, so no single cause is isolated.
The reference mapping is now Core DT to LDT; the candidate retains88 types,
610 fields and Core capacities. Native1081/1081, SDK1146/1146 type and43/43
scalar witnesses pass;269 sources pass canonical reimport/compile/export.
The live HMI client/date parser passes36 checks across99 Good leaves, including
full-width strings and exact64-bit values. See
[Advanced7 evidence](Evidence/TIA_S12_WEBAPI_ADVANCED7_2026-10-10.md).
The saved simulator image belongs to the copied LDT station at
`%LOCALAPPDATA%\Fraktal\TiaStations\S12_Ldt_20261010\FrkS12\FrkS12.ap20`;
the original FrkS12 project remains the DTL control. Use an explicit work path.
The frame/registry generator now emits24 sources from that shared declaration;
the independent test package compiles0/0 and passes103 runtime assertions,
native public/private reads and STOP/RUN setup.36 blocks and19 interfaces
round-trip canonically. T-TIER/T-IO/T-WIDTH/T-GEN replay applies to its manifest;
full generator facets remain open. The saved FrkS12 simulator image now belongs
to `TiaStations\R4_Frame_20261010\FrkS12\FrkS12.ap20`; both earlier projects
remain preserved. The shared Framework/Core command kernel now passes238
assertions in55 cases and again after STOP/RUN. Native public100/private7 checks
pass;47 blocks/18 interfaces round-trip. Generator0.2 owns the parameter latch,
command/timeout validation, management-before-abort order and full path for
CMs with management hooks. See
[command-kernel evidence](Evidence/TIA_CORE_LIFECYCLE_2026-10-10.md).
The current saved image/project is
`TiaStations\Core_Lifecycle_20261010\FrkS12\FrkS12.ap20`; older projects,
secrets and certificates remain preserved. The subsequent Unit control slice
passes103 native checks for mode/mailbox/release/reset/local Part and STOP/RUN;
79 blocks/34 interfaces round-trip warning-free. The active image now belongs to
TiaStations/Unit_Runtime_20261011/FrkS12/FrkS12.ap20. See
[Unit control evidence](Evidence/TIA_UNIT_CONTROLS_2026-10-11.md).
The subsequent Unit routing bench passes120 native checks across24 instances,
three Unit levels, manual catalogs/release rollup, reset and STOP/RUN.104 blocks/
40 interfaces round-trip with0 errors/warnings. The current saved project/image
is TiaStations/Routing_Runtime_20261011/FrkS12/FrkS12.ap20; prior projects remain
preserved. See [routing evidence](Evidence/TIA_UNIT_ROUTING_2026-10-11.md).
The static manifest/native HMI slice now passes241 native checks and120 routing
regressions. The production HMI path maps24 modules, hydrates492 manifest entries
and commands the rendered Instant button; peer mode changes remain isolated.
Its display preference is test-only NONE because there is no login provider.
117 blocks/41 interfaces round-trip warning-free; production114/41 compiles0/0.
Current saved image: TiaStations/Manifest_Runtime_20261011/FrkS12/FrkS12.ap20.
See [manifest/HMI evidence](Evidence/TIA_STATIC_MANIFEST_HMI_2026-10-11.md).
Next implement authentication/session/full audit and derived-state/alarm services,
then configuration/recipe/retention and full sequence/GRAPH services. Complete
application/frontier release services remain alongside that Core work.
See [frame/registry evidence](Evidence/TIA_R4_FRAME_REGISTRY_2026-10-10.md).
The broader Phase3 feature set, clock quality, library upgrades, retained-state
and remaining S11 deployment/modes are still owed. The1200 timestamp projection is separate.

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
2. **S9 Web API read/session observations measured 2026-10-09**
   ([evidence](Evidence/TIA_S9_READ_SESSIONS_2026-10-09.md)): two independent tokens,
   ten concurrent reads per client; pinned socket reconnect retaining the token;
   explicit logout invalidates protected reads with code 2, and re-login succeeds
   without disturbing the other client. **One batch is not one scan:** all ten
   batches of sixteen reads of the same cyclic counter returned differing values.
   Part IV §3.13 keeps the established eventually consistent snapshot boundary.
   Natural invalidation after 160 s idle and explicit re-login also passed;
   a retained Python read client crossed native STOP→RUN with the same token,
   counter frozen in STOP and rebuilt/increasing in RUN, followed by 19/19.
   Still owed: retained-client download and cable-pull recovery, concurrent
   mailbox writers and end-to-end HMI freshness.
3. **S3 polling cost** — done (+0.23 ms mean cycle under continuous full-tree Web API
   polling, S1W evidence §8).
4. **S3 memory and per-module cost** — first numbers 2026-10-08
   ([evidence](Evidence/TIA_S3_SCAN_AND_MEMORY_2026-10-08.md)): S2 image 19.6 KB work
   memory (only the CPU's system web page reports it — Openness, SZL and the Web API
   do not); idle CM 0.20 ms/scan → 0.053 ms with the **quiescent fast path** now in the
   generated frame (Part IV §3.14); **≈ 1.16 KB work memory per minimal CM** (S2 + 10/30
   CMs). **Unit guard and Core-derived storage measured 2026-10-10**
   ([evidence](Evidence/TIA_S3_BUDGET_2026-10-10.md)): five Units plus ten CMs,
   19/19 with both frames; guard saves about 0.202 ms per idle Unit. Added work
   memory, wide → compact: status/state 47.03 → 22.84 KB, alarms 75.57 → 12.41 KB,
   sequence 48.57 → 21.77 KB, configuration 48.07 → 19.42 KB. Complete field/type
   and DB count/access read-back accompanies the measurements. The candidate
   combined storage image uses 96.89/150 KB and passes 19/19; its 53.11 KB free
   still has to hold additional runtime/project code and at least 15 KB reserve.
   Eight compact write definitions alone add 5.49 KB. The candidate
   capacities are in `Spikes/S3_Budget/make_fixture.py`, not a released profile.
   Owed: type-shared write metadata instead of dense per-instance strings;
   encoded-value/domain/persistence-piece width gates; complete-instance and
   press runtime cost with at least 15 KB reserve, real published surface and
   full hook semantics. Freeze capacities only after those checks.
5. **S11 GRAPH leg on S7-PLCSIM — done 2026-10-09**
   ([evidence](Evidence/TIA_S11_GRAPH_PLCSIM_2026-10-09.md)). `fraktal_tia_graph.py` generates the AUTO chain as GRAPH
   SimaticML from `S11_Graph/chain_auto.json` against TIA's exported reference chart
   and dumps any chart back. It compiled 0/0 on the `FrkS11` station, and TIA's
   re-export dumps identical. It ran on PLCSIM Advanced 5.0, headless, with the SCL
   chain's trace and a mid-run `INIT_SQ` restart (19/19). Measured design facts, now
   in Part IV §3.5: actions take no `IF`/expression, so exit conditions sit in the
   transitions; the GRAPH FB is a parameter instance, never a multi-instance; and
   Execute is raised one scan after entry. **Remainder measured 2026-10-09**
   ([evidence](Evidence/TIA_S11_SEMANTICS_2026-10-09.md)): four generated probes,
   full read-back equality, 28/28 after download and a direct PLCSIM STOP→RUN;
   19/19 after download/start on the physical 1214C. Empty V/C networks do not
   enforce maximum time, an explicit supervision waits for ACK_EF when enabled,
   skip mode omits step records, and local invalid-index handling returns 16#2522
   on both families (OB121 fallback on 1500: 16#22, substitute zero). Part IV
   now keeps V/C networks empty and skip disabled. **Native SCL bench remainder
   PASS, idle fixture scope**
   ([evidence](Evidence/TIA_S11_NATIVE_2026-10-09.md)): authenticated web STOP→RUN,
   fresh OB100 stamp and 19/19; two code-only downloads in RUN, compile/download
   0/0 and 19/19 each. Marker 1101→1102 preserved the DB sentinel, startup stamp
   and mailbox sequence/ack while counters increased; DB interface unchanged.
   No stop/start or reinitialization question appeared in either delta.
   **Active GRAPH recovery measured 2026-10-10**
   ([evidence](Evidence/TIA_S11_GRAPH_RECOVERY_2026-10-10.md)): the new two-root
   fixture passed 28/28 in fifteen completed harvests and 16 recovery checks.
   Reset while BUSY and native STOP→RUN withdraw outputs and wait for a new Arm.
   An FC delta preserves observed active command/DB state. A GRAPH body-only
   delta keeps its exported interfaces but requests sequence turn-off and DB
   reinitialization: state-preserving GRAPH download is **not passed**.
   The cylinder's interlock now withdraws outputs even in READY; reset after
   completion and a second active restart passed after the fix. This remains a
   mechanism probe, not the full Unit runtime. Implement the quiesced deployment
   workflow and prove retention/other modes/errors before closing S11.
   **Diagnostics-role cleanup PASS**
   ([evidence](Evidence/TIA_S11_ENUMERATION_2026-10-09.md)): direct enumeration
   removed WebChangeOperatingMode, hardware compile and UMAC download 0/0;
   authenticated native mode forms absent, gateway reads and 19/19 retained.
   V20's assigned-rights IList enumerated two valid objects but `.ToList()`
   produced one null entry. The driver now enumerates identifiers directly and
   verifies the requested set before save/download. Previous causal guesses
   and failures remain in frozen records; this measured comparison resolves them.
   **Current approved driver:** `TiaCli/bin/candidate_s11_enumeration/Fraktal.Tia.Cli.exe`,
   Base64 SHA-256 `5FXuk+YWxHiAAbB4MBZNqSty44F9apDJDgPZiTcCbzM=`. Never overwrite
   it or earlier approved binaries. Passwords and station certificates preserved.
   Still owed: enforcing quiesced GRAPH deployment, retentive state, other error
   classes, manual/semi-auto GRAPH modes and full Unit lifecycle integration.
   Host Python Web API transport now pins each
   reconnect and never replays mutations after a lost response (four fault tests);
   this does not close the S9 runtime remainder. S3 now supplies the storage
   measurements in item 4. S12 type/date projection and S4 source checks now
   pass on Advanced7; generated frames/registry now pass their boundary fixture;
   next are the remaining Core/Unit facets behind the measured command kernel,
   with the S9 recovery/writer remainder still open.
6. **Tooling Phase 2 start** — `tia_lint.py` **done 2026-10-08** (11 rules + 18 tests, pre-commit;
   T-TIER/T-IO/T-WIDTH/T-GEN pending the generator). Original scope: `tia_lint.py` with T-FRAME, T-CYCLIC, T-EXT, T-ASCII,
   T-KEYWORD, T-COLLIDE, T-OWNIO, T-TYPEFILE over `Spikes/`, wired into
   `.githooks/pre-commit` beside `plc_lint`.


## Access/session continuation (2026-10-11)

Generator0.6 passes122 native access checks,120 current routing regressions and
the authenticated generic HMI button gate.129/42 native round-trip and production
125/42 compile0/0. Current image/project: Access_Runtime_20261011/FrkS12/FrkS12.ap20;
owner-created Fraktal instance preserved RUN on the isolated virtual network.
Next: state/diagnostic and full MESSAGE/alarm/audit services, then configuration,
recipes/user-policy retention, full sequences/GRAPH, modules and press without power.
Local table CRUD/provider substitution and concurrent mailbox writers remain open.
See [access/session evidence](Evidence/TIA_ACCESS_SESSIONS_2026-10-11.md).
Twelve newer referenced evidence reports and the old18 checksum manifests are
absent in this checkout; the new report records the availability gap precisely.

## Derived state and alarm/event continuation (2026-10-11)

Generator0.7 passes96 native state/alarm assertions,23 nested ownership/reset
assertions and122 authentication regressions. The routing-only candidate passes120.
Native148 blocks/45 interfaces round-trip0/0; production142/45 compiles0/0. The
authenticated generic HMI renders the captured fault and clears it through reset;
570 HMI tests/1skip,128 tools and33 consistency tests pass. Current owner Fraktal
image is Alarm_Runtime_20261011/FrkS12/FrkS12.ap20, preserved registered/RUN.
The reference remains simulated S7-1500 with full Core capacities and no150KB cap.
The physical1214C and approved driver were untouched.

Next: configuration/recipe transactions and persistence, including user/policy
and alarm retention. Shelving, runtime project metadata, durable sink adapter,
complete awaited-diagnostic/frontier/action release services and concurrent writers
remain open before complete Core conformance. Full SCL/generated GRAPH sequences,
modules and the press without power follow those services. The optional callback
seam and nonretained rings do not close S6/S16. See the
[state/alarm evidence](Evidence/TIA_STATE_ALARMS_2026-10-11.md).

## Station/model config continuation (2026-10-11)

Generator0.8 passes120 native config checks,23 blocking-restore checks,122 access
and96 state/alarm regressions. The live authenticated editor writes21, verifies
the PLC and inactive-model isolation, and restores10.571 HMI tests/8 opt-in skips,
135 tools and35 consistency tests pass;
190/52 native reimport and production183/52 compile0/0. The local-retain probe
passes7 checks including private exclusion and simulator power-cycle retention.
The HMI/spec category names are consistently station config, line config and
model config. Current owner Fraktal image is Config_Runtime_20261011/FrkS12/FrkS12.ap20,
kept RUN with its keeper; physical1214C/approved driver untouched.
The provider is keyed by owner/write key/model and stages model changes before
commit; station config restore is independent of model config. See
[config evidence](Evidence/TIA_CONFIG_TRANSACTIONS_2026-10-11.md).

Next: named station/model config sets and import/export, other persistence media,
user/policy/alarm retention, optional line config replication and remaining config
forms (float/enum/array/capture/custom classes). Complete diagnostics/releases,
shelving/durable sinks, full SCL/generated GRAPH sequences/modules/press without
power remain open. The current local-retain result is partial S16, not full Core
config conformance or a physical retention/download-loss guarantee.

## Progress, 2026-10-12: recovery demo and root decisions

The owner's latest directive wires GRAPH AUTO/HOME and ST permissives at the
Unit; optional ST/LD twins remain uninstantiated. Main is a calling routine and a
single hardware-driver FB owns logical I/O. Native AUTO carries nineteen TC3 chart
steps, including cancellation, deliberate scrap confirmation and parallel join.
The four-step load-position routine is reused. Core ownership includes branch
identity, and handled failures withdraw outputs while preserving their first-out.

Generator0.9 adds root decisions and an unconditional sequence hook. The isolated
two-root decision/config bench qualifies service behavior without a physical press.
The full four-table sequence frontier, durable alarm storage, named config sets,
broader provider media and remaining reusable module families are still open.
The next config slice is named config sets/import-export, using the existing
validate/stage/commit and access handlers rather than project-specific mutation.
See [the dated evidence](Evidence/TIA_GRAPH_RECOVERY_DECISIONS_2026-10-12.md).
