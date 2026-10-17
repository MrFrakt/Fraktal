# Fraktal/TIA — Siemens TIA Portal (S7-1500 / S7-1200) Binding (Part IV)
*Unified PLC Programming Standard · **Part IV: the Siemens TIA Portal binding of Fraktal Core***

**Status:** **Draft — Phase 0. First bench run recorded 2026-10-08: S15 and S2 PASS at bench scope, the S2 fixture 17/17 three runs in a row on the physical CPU 1214C; no R-gate PASS yet.** Part IV (Part I: `Fraktal_Core_Part_I.md`; Part II: `Fraktal_TC3_Part_II.md`; Part III: `Fraktal_AB_Part_III.md`)
**Platform:** Siemens SIMATIC S7-1500 / S7-1200 · TIA Portal (STEP 7 Professional) V20 · IEC 61131-3 ST (SCL) and SFC (S7-GRAPH) **without** the IEC OOP extensions

> Every clause in this Part **binds** a Core contract and cites it as **Core §x.y**; a binding clause carries the number of the Core clause it realizes. Nothing here introduces new normative model content — tiers, contracts, state machines, diagnostics and routing live in Part I. Core §1.1 O8 already names this binding **Fraktal/TIA**; a port to another platform re-implements this document only.

---

## TIA §0 — How to read this document

This Part is written before its Phase 0 spikes, deliberately and for the same
reason Part III was (AB §0): a binding document with explicit holes drives a
spike programme better than a spike list drives a document. Two kinds of clause
must therefore never be confused.

| Marker | Meaning |
|---|---|
| *(unmarked)* | **Fraktal's decision to make.** Architecture, naming, structure, generation and gate rules. Normative now; changing it is a specification change. |
| **[PROVISIONAL Sn]** | **Depends on Siemens platform behaviour not yet verified on a controller.** Best current understanding from the TIA Portal V20 information system and Siemens data sheets; not a conformance claim; settled by spike `Sn` (TIA §12). |

**No `[PROVISIONAL]` clause may be cited as conformance evidence.**

**Implementation-readiness rule.** Only disposable Phase 0 fixtures
(`FraktalCore/PLC/Siemens/Spikes/`) may be written while this Part is pre-spike.
The runtime library shall not begin until these gates record PASS:

| Gate | Status | Required evidence |
|---|---|---|
| R0 Core authority | **PASS by inheritance** | Core §2.2/§3.14/§5.5 already permit generated composition and §3.10/§11 define the transport-neutral Self-Description Service (AB R0). This Part needs no further Core amendment; one editorial item (Core header lists "Part I of III") is tracked in the port plan. |
| R1 platform baseline | **OPEN — partly evidenced** | Bench controller identified from the controller itself (CPU 1214C DC/DC/DC `6ES7 214-1AG40-0XB0`, firmware V4.7.3, 2026-10-08); TIA Portal V20 (STEP 7 `20.00.0000`) and Openness V20; Openness access granted (group membership + new logon) and every build whitelisted by hash; PG/PC interface `Intel(R) 82574L Gigabit Network Connection` #2. Compile and download ran, so a usable STEP 7 licence is present (its exact key not yet inventoried). Still owed: licence inventory, S7-1500 target choice. No runtime licence is needed on the default (Web API) path; an OPC UA runtime licence only where a site uses that optional projection. Evidence: [`TIA_R1_PLATFORM_BASELINE_2026-10-08.md`](Siemens/Evidence/TIA_R1_PLATFORM_BASELINE_2026-10-08.md), [`TIA_S2_S15_FIRST_BENCH_RUN_2026-10-08.md`](Siemens/Evidence/TIA_S2_S15_FIRST_BENCH_RUN_2026-10-08.md) |
| R2 executable shape | **OPEN — S2 and S15 PASS (bench)** | S1W/S2/S4/S11/S12 prove the Web API data path, module FB form, source round-trip, both sequence forms and physical type map. S2/S15 passed on1214C; S11 GRAPH passed at its recorded prototype scope ([evidence](Siemens/Evidence/TIA_S11_GRAPH_PLCSIM_2026-10-09.md)); S1W passed functionally on1214C ([evidence](Siemens/Evidence/TIA_S1W_WEBAPI_2026-10-08.md)). S12 complete type layout, native Web API/HMI type/date mapping and S4 canonical SCL source leg pass on simulated1516 V3.0/Advanced7; full generated runtime and timing acceptance remain open |
| R3 frozen contracts | OPEN | the TIA type map, Web API (and optional OPC UA) browse projection, mailbox layout and step-table encoding frozen at version 1 and gated |
| R4 gates | OPEN | a fresh clone regenerates every fixture, imports it through Openness, compiles warning-clean and round-trips canonically |
| R5 test execution | OPEN — first evidence | a reference suite downloaded to the named bench and run, machine-readable rows harvested, three consecutive green runs. Recorded: the S2 fixture's 17 assertion rows harvested over the test image's TCP result server as JUnit, green on three consecutive download-and-restart runs, and again ×3 on the ASCII, web-enabled image (S1W record); still owed: the reference suite of ≥2 module types and the generated runner |
| R6 security | OPEN — web part measured on the bench posture | declared zone/conduit, web-server users and rights, HTTPS certificate pinning, OPC UA security policy where that projection is used, protection level, PUT/GET posture and secret handling |

A failed gate changes this binding or stops the port; it is never converted into
an undocumented implementation exception.

**Gate scope:** evaluate readiness for the controller family being implemented.
The S7-1500 reference track uses its selected CPU's limits and SCL/GRAPH support;
S7-1200 fit, compact capacities and press-lite feasibility gate only that
constrained profile. They shall not block or narrow the S7-1500 implementation.
Simulation may establish compiler/runtime behavior with an explicit simulation
scope; physical timing, memory/communication budgets and hardware conformance
still require reference hardware evidence.

---

## TIA §1 — Binding identity & technology baseline

*Binds Core §1.1 (technology baseline), §1.2 (scope), §1.6 (definitions).*

**Fraktal/TIA** is the Siemens TIA Portal binding of Fraktal Core. Conformance
claims compose as *"Fraktal Core + Fraktal/TIA (+ profiles)"* (Core §1.1 O8),
and every claim names the controller **family**: *"Fraktal Core + Fraktal/TIA
(S7-1500)"* or *"Fraktal Core + Fraktal/TIA (S7-1200, constrained)"*.

**Technology baseline.** SIMATIC S7-1500 (reference family) and S7-1200
(constrained family, TIA §1.1) programmed in TIA Portal STEP 7 Professional;
**SCL** (IEC ST) for the framework, module types, permissives and the reference
sequence form; **S7-GRAPH** (IEC SFC) for the chart sequence form on S7-1500;
**PROFINET IO** for fieldbus and device integration (TIA §10); **STEP 7 Safety /
PROFIsafe** on an F-CPU for functional safety (TIA §9); the CPU's licence-free
**Web API** (JSON-RPC 2.0 over HTTPS), reached through the Fraktal gateway, for
connectivity and self-description (TIA §3.10, TIA §11.1a); the CPU's embedded
**OPC UA server** as an optional, licensed projection (TIA §11.1); the same
generic Flutter HMI — the Web build through the gateway on every station, the
native desktop build directly where the OPC UA projection is licensed (Core §3.13).

> **Transport decision (project owner, 2026-10-08): no paid runtime licence on
> the default path.** The Fraktal gateway reaches a TwinCAT PLC over ADS
> (`AdsSessionClient`, selected by an `ads://` endpoint) and an Allen-Bradley
> controller over EtherNet/IP CIP; Fraktal/TIA gives it the S7's own licence-free
> protocol in the same way. The **Web API** is built into
> every S7-1500 and every S7-1200 from V4.5: symbolic browse, read and write of
> optimized data, authenticated web-server users with per-user rights, HTTPS, and
> the same "Accessible / Writable from HMI/OPC UA/Web API" member attributes
> Fraktal already sets (TIA §3.10.1). The gateway gains one more session client
> (`WebApiSessionClient`, selected by its endpoint scheme exactly as ADS is), so
> the gateway protocol and the Web HMI are unchanged. The embedded OPC UA
> server stays a supported projection for a site that licenses it (a runtime
> licence per CPU); then the native HMI connects directly, as it does to TC3.
> **S1W PASS (functional, bench, 2026-10-08)** on the 1214C V4.7.3: browse, symbolic
> leaf reads, attribute-gated writes, the mailbox, authentication and certificate
> pinning work as §11.1a requires; throughput is the S7-1200 constraint (§3.10.3).
> [Evidence](Siemens/Evidence/TIA_S1W_WEBAPI_2026-10-08.md).
>
> Rejected, with the reason:
> - **PROFINET IO** is a fieldbus (TIA §10): cyclic process-image exchange between
>   an IO controller and its devices, a fixed byte layout decided at engineering
>   time (an S7-1200 I-device transfer area is ≤ 1,024 bytes each way), no names,
>   no structure, no browse, no authentication. The HMI host would also need a
>   PROFINET controller stack. It cannot carry self-description.
> - **S7comm PUT/GET** reads absolute addresses of non-optimized DBs only, has no
>   authentication, and the hardening guidance is to leave it off (on an S7-1200
>   its switch is not even reachable through Openness, measured).
> - **S7CommPlus** is proprietary and undocumented; a reverse-engineered client is
>   not a conformance basis.
> - **Open user communication** (TCP/UDP, `TSEND_C`/`TRCV_C`) is licence-free and
>   fast, but every byte of the protocol and its security would be Fraktal's to
>   write and review. It stays the test-result harvest path (TIA §5.7) and the
>   fallback if S1W fails.
> - **Modbus TCP**: flat registers, no names, no structure.
>
> The cost moves to polling (the Web API has no subscriptions, so the gateway
> polls at the display rate; step history stays PLC-side, as on every binding),
> per-request overhead on an S7-1200, and the web server's session and request
> budgets — all measured by S1W.

**Optional Ladder examples.** The owner extended the earlier SCL/GRAPH scope on
2026-10-11 to include ST, LD and GRAPH examples. On 2026-10-12 the owner
requested wiring GRAPH sequences and ST permissives into the demo; ST/LD twins
remain optional examples and physical testing awaits the bench. Shared framework
behavior remains SCL. LD
sequence/release examples use the same declared actions and conditions as ST;
their native SimaticML shall be generated and read back. Compiler acceptance
alone does not prove contacts, call pins or transitions exist correctly.
See [the press examples](../FraktalCore/PLC/Siemens/Examples/PressDemo/README.md).

### TIA §1.1 Controller families and profiles

| Family | Role in this binding | Why |
|---|---|---|
| **S7-1500** (FW ≥ V3.1, CPU 1515 or larger recommended) | **Reference conformance family.** Full Core + press-bench scope. | References (`REF_TO`), named value types, `LTIME`/`LDT`, S7-GRAPH, `RT_INFO`, larger OPC UA budgets (≥ 32 sessions, 2,000–10,000 recommended monitored items), MB-class work memory. |
| **S7-1200 G1** (FW V4.7) | **Constrained family.** Base lifecycle, handshake, diagnostics, SCL sequences, mailbox and Web API projection, with declared capacity reductions and declared exclusions (TIA Annex A). | The measured1214C bench has150 KB combined program/data work memory,14 KB retentive,16 KB OB1 local data; these are bench-model limits. No references, no named value types, no `LTIME`/`LDT`/`ULINT`, **no S7-GRAPH**; OPC UA server ≤ 10 sessions,5 subscriptions/session,≤1,000 recommended monitored items,2,000 nodes per user-defined server interface,≤20 server methods,100 ms minimum sampling. |
| S7-1200 G2 | Not yet assessed | Separate catalog and firmware line; owes its own R1/S12. |

The figures above come from the Siemens data sheet for `6ES7214-1AG40-0XB0`
(firmware V4.7, data sheet dated 2026-09-28) and Siemens entry 109755846
(OPC UA system limits, 02/2024); both are archived in the engineering
knowledge base. **They are inputs to spikes, not measured results.**

> **The evidence baseline and the reference family are not the same, and this
> matters** — exactly as AB §2.1 says of v33 versus v37. The only physical
> controller available on 2026-10-08 is a CPU 1214C at V4.7.3. Everything the
> spikes prove on it is valid for that controller only. S7-1500 behaviour is
> evidenced on S7-PLCSIM (V20) until hardware exists, and PLCSIM evidence
> **shall** be labelled as simulation: it says nothing about OPC UA budgets,
> scan time, memory fit or communication load on a real CPU.

**Binding definitions** (extends the Core §1.6 table):

| Term | Meaning |
|---|---|
| SCL | Structured Control Language — Siemens' IEC 61131-3 ST. |
| S7-GRAPH | Siemens' IEC 61131-3 SFC language (an FB with a sequencer). S7-1500 only in TIA V20. |
| External source | A text file (`.scl`, `.udt`, `.db`) compiled into blocks by "Generate blocks from source" (TIA §2.5). |
| SimaticML | TIA Portal's Openness XML export/import format for blocks, types and tag tables. |
| Openness | TIA Portal's .NET engineering API (TIA §5.4). |
| Instance DB / multi-instance | Storage of an FB instance as its own data block, or as a static member of the calling FB. |
| Parameter instance | An FB instance passed to another block as an `InOut` parameter (TIA §3.5). |
| `FRK_Core` | The private lifecycle-state record every module instance carries (TIA §3.1). |
| `FRK_Registry` | The CPU-wide bounded array of module rows (TIA §3.2). |
| Web API | The S7 web server's JSON-RPC 2.0 interface (`POST /api/jsonrpc` over HTTPS): `Api.Login`, `PlcProgram.Browse/Read/Write`. Licence-free. |
| Standard SIMATIC server interface | The S7 OPC UA server's automatic namespace of every HMI/OPC UA-accessible tag (optional projection). |

---

## TIA §2 — Development & runtime environment

### TIA §2.1 Toolchain & versions
*Binds Core §2 (pinned-toolchain rule).*

- The **exact** TIA Portal version and update (e.g. `V20 Update 3`), the CPU
  article number and firmware, the Openness API version, and every installed HSP
  used by the project **shall** be pinned and recorded; every station on a line
  uses the same pins.
- The framework uses only STEP 7 features available in the pinned TIA version for
  the pinned firmware. A feature present on S7-1500 but absent on S7-1200 (TIA
  §1.1) is used only in code generated for the S7-1500 family, and the generator
  — not a project engineer — selects it (TIA §5.2).
- The framework requires no language extension beyond SCL, S7-GRAPH and the
  standard instruction set. Where Part II relies on OOP, this binding relies on
  **composition plus generation** (TIA §3.1, §3.14), the mechanism Core §2.2 permits
  and Part III already proved on Logix.

### TIA §2.2 Library distribution
*Binds Core §2.2.*

- **The reviewed artifact is source.** The framework ships as versioned SCL
  external sources and generated SimaticML, plus the generator and gates. The
  repository is the single source of truth (Core §1.1 O9).
- **The deliverable is a TIA global library** built from that source by the gate
  (`Fraktal_Core_TIA` and `Fraktal_Modules_TIA`), whose **library types** carry the
  Fraktal semantic version as the type version. A project instantiates released
  library types; it never copies and edits a framework block. **[PROVISIONAL S4]**
  that Openness can create, version and release library types from generated
  blocks reproducibly; if it cannot, the source set itself is the distribution
  and the gate verifies a consumer's copy by hash.
- Each framework block also carries the `VERSION` attribute and an
  `FRK_FRAMEWORK_VERSION` constant published on every root (TIA §3.10), so a
  running CPU can be asked which framework it holds.
- **Which component to step** follows TC3 §2.2's soft rules. On TIA, any change to
  a published or retained data layout is a `minor` step: it reinitializes instance
  data on download (TIA §2.8) and moves OPC UA nodes.

### TIA §2.4 Project & controller settings
*Binds Core §2 note; baseline in TIA §4.1.*

- Every Fraktal block uses **optimized block access**. Non-optimized ("standard")
  access is permitted only for a test-harness result DB read by the bench harvest
  path (TIA §5.7), never in a deployed program.
- CPU protection: access level and passwords per project security plan (TIA §14);
  **"Permit access with PUT/GET communication" shall be off** in a deployed
  project. A test project may enable it for result harvest only (TIA §5.7).
- The web server is on for the Web API, with a server certificate created once in
  the station project and kept for the station's life (clients pin its fingerprint,
  TIA §11.1a), and one least-privilege web user per gateway (read and modify tags,
  nothing else). HTTPS only where the family offers that switch — on the 1214C
  V4.7 Openness offers no `WebserverHttpsOnly` (measured), so whether port 80
  answers is recorded by S1W and closed at the conduit if it does. Its password lives in the site secret
  store, never in a plan or an evidence record.
- The OPC UA server is enabled **only** where a site uses that projection: then
  with the standard SIMATIC server interface or a generated user-defined interface
  (TIA §3.10.3), and its runtime licence configured. On that station a missing
  licence is a commissioning defect, not a warning to live with.
- The system and clock memory bytes are **not** used by framework code; the
  framework has its own timing source (TIA §8.11).

### TIA §2.5 Source-control form
*Binds Core §2.5.* **The text-diffable storage form is the SCL external source**
(`.udt` types, `.scl` FBs/FCs/OBs, `.db` data blocks), plus **SimaticML XML for
S7-GRAPH blocks**, PLC tag tables and anything external sources cannot express.

- Sources are **generated** or hand-authored as text and **imported** through
  Openness (`Generate blocks from source`); they are never typed into the editor
  and exported afterwards. The **program** in a TIA project is therefore a build
  output: every build deletes the program blocks and types and re-imports them.
- **The TIA project itself is engineering state, one per station, never committed.**
  It holds the PLC communication certificate the CPU receives on download (and the
  confidential-data password when one is set); a V4.7 / V3.1+ CPU then accepts
  secure PG/PC communication only from a project holding that certificate.
  Recreating the project per build locked the bench out of engineering access
  (measured 2026-10-08). A station project is created once (hardware, security,
  certificate) on the engineering workstation (`%LOCALAPPDATA%\Fraktal\TiaStations`)
  and is part of the workstation's backup, not the repository.
- **Sources are ASCII.** TIA imports a BOM-less source file as ANSI: UTF-8 text in
  comments was stored double-encoded (measured). A UTF-8 BOM is untested; the gate
  rejects non-ASCII source text (T-ASCII, TIA §5.3).
- **One `TYPE` per `.udt` file, no comment before the keyword.** A multi-type file
  with leading comments failed generation with no detail text (measured).
- **S4 source leg measured; other legs remain provisional.** Round-trip stability: import → compile → *Generate source*
  → compare must be equal modulo a declared ignore list. First look (2026-10-08):
  declarations, attributes and in-block comments survive; whitespace is
  normalized, a file-level comment moves inside its block after `VERSION`, and
  multi-line trailing comments are joined — so the gate compares a canonicalized
  form defined in TIA §5.3. S7-GRAPH SimaticML round-trip is a separate leg of
  the same spike.
  The2026-10-10 S12 fixture passes authored→GenerateSource→reimport/compile→
  GenerateSource for269 sources and88 complete Core-derived types on simulated
  1516 V3.0. `Spikes/S12_TypeMap/verify_roundtrip.py` owns its narrow ignore list
  and verifies native member order/types/bounds/publication attributes. It does
  not ignore statements, string payloads or custom OB inputs. This is not proof
  of library-type upgrade/version retention.
- Unlike TwinCAT's SFC `XmlArchive` (TC3 §3.5), S7-GRAPH SimaticML has a published
  schema (`SW.PlcBlocks.Graph_v5.xsd` in V20), so **a chart may be generated**;
  it shall still be read back after import (TIA §5.3), because a schema-valid
  chart can still import with a different graph than intended.

### TIA §2.6 Simulation
*Binds Core §2.6, §5.7.*

Every reusable type runs against the same semantic HAL in real and simulated
projects. The project's hardware-driver FB selects simulation by a build constant
(TIA §7.5) and never writes `%Q` while simulating. S7-PLCSIM Advanced is the isolated
runner for S7-1500 code. It runs **headless** (S11, 2026-10-09):
`Invoke-PlcSimInstance.ps1` registers and powers on an instance through the Runtime
API 5.0; `Fraktal.Tia.Cli` downloads a V20 project over the `PLCSIM` PG/PC interface;
and the API's read-only tag access harvests the results. The project must enable
*simulation support during block compilation* (`IsSimulationDuringBlockCompilationEnabled`),
or the download is refused. A newly registered instance presents a new certificate,
so its first download is a logged trust-on-first-use act (§14). The physical S7-1200 bench is the hardware runner. No
test image is ever a production download.

### TIA §2.7 Time-synchronization mechanics
*Binds Core §2.7.*

The station clock is the CPU's system time (UTC), read with `RD_SYS_T`, and
disciplined by the CPU's **NTP client** (S7-1200 and S7-1500); S7-1500 may use PTP
where the network provides it. `FRK_Now()` wraps the read once, so every framework
timestamp has one source (Core §2.7 "one clock feeds all timestamps").

**[PROVISIONAL S1]** The CPU exposes no documented instruction reporting NTP
synchronization state to the user program on S7-1200. Until S1 finds one,
`ST_TimeQuality.Synchronized` on S7-1200 is derived only from a project-declared
source (an external time master the project supervises) and otherwise stays
**FALSE** — never a healthy default. A CPU that cannot state its own sync quality
is reported as unsynchronized, exactly as AB §2.7 reports `IsSynchronized=0`.

### TIA §2.8 Restart, download, and retention classes
*Binds Core §2.3, §3.14, §6.1, §8.3, §13.*

The generated program distinguishes: STOP→RUN warm restart (OB100 runs), power
cycle (OB100 runs; retentive data restored), **download with reinitialization**
(instance data takes start values), and **download of changes without
reinitialization** (memory reserve). On every path, `Execute`/`Abort`, sequence
latches, mailbox in-flight state, manual and force requests start safe and
cannot self-resume.

- Only data declared retentive survives a power cycle. The generator owns the
  retention list (Core §3.8b); project engineers do not tick individual
  "Retain" boxes on framework members.
- **The S7-1200 retentive area is 14 KB.** Configuration documents, parameter sets
  and the user table therefore live in **load-memory data blocks**
  (`READ_DBL`/`WRIT_DBL`) or on the memory card, not in retentive work memory
  (TIA §3.8b) **[PROVISIONAL S16]**.
- **[PROVISIONAL S11]** that a download with reinitialization while RUN cannot
  energize an output or replay a committed mailbox request; the gate forces
  STOP for any download that reinitializes data (TIA §5.4).

**Measured S11, physical 1214C V4.7.3 (2026-10-09):** authenticated native web
STOP→RUN ran OB100 again and passed all 19 fixture cases. Two software-only
code deltas downloaded in RUN with 0/0; the second changed the executing marker
1101→1102 while preserving the DB sentinel, startup timestamp and mailbox
sequence/ack, with increasing scan counters. The DB interfaces compare equal
([evidence](Siemens/Evidence/TIA_S11_NATIVE_2026-10-09.md)). This proves an idle
SCL fixture's code-only update, not type growth, active-command recovery,
retentive classes or the GRAPH download path.

---

## TIA §3 — Language & wiring mechanics

### TIA §3.1 The module type form
*Binds Core §2.2, §3.1–§3.3, §3.12.*

A reusable Fraktal module type is **one SCL function block** whose interface
carries the Core contract **as direct members of the instance** — the generic
HMI recognises a module by a `Status : ST_ModuleStatus` child and reads the
PLCopen strip at module level (HMI_CONTRACT "Per-tile bindings"), so the contract
cannot be nested inside a wrapper record:

```
FUNCTION_BLOCK "FB_<Type>"            // optimized access
VAR_INPUT    Execute, Abort : Bool;  Command : DInt;  ParCmd : "ST_<Type>ParCmd";
             ParCfg : "ST_<Type>ParCfg";
VAR_OUTPUT   Busy, Done, Error, Aborted : Bool;  ErrorID : DWord;
             Timing : "ST_ModuleTiming";
             OutCmd : "ST_<Type>OutCmd";  OutImm : "ST_<Type>OutImm";
VAR          Status { ExternalWritable := 'False' } : "ST_ModuleStatus";   // published static
             Core   { ExternalAccessible := 'False' } : "FRK_Core";        // private lifecycle state
             <child multi-instances>   <device state, ExternalAccessible := 'False'>
```

**Outputs are written, never read, by their own block.** STEP 7 warns ("might not
be initialized") when an FB reads its own output — which is exactly what the
lifecycle does with `Status` — so `Status` is a **static** published member, and the
PLCopen strip is produced by `FRK_End` as FC *outputs* assigned with `=>`. A static
is published to the HMI projections and readable by the parent like an output (measured: the
S2 harness and parent read `#Child.Status` and statics of instances).

The lifecycle is written **once**, in shared framework functions taking the
private record by reference. The generated frame supplies the non-optional Core
ordering, parameter latch and command metadata; device regions contain no
lifecycle copy:

```
BEGIN
  "FRK_Begin"(Core := #Core, Status := #Status, Execute := #Execute, Abort := #Abort, Command := #Command);
  <Init reaction, when requested>
  <accepted edge: latch ParCmd; FRK_Start validates declared command/ParCfg timeout>
  <CommandStart reaction, when requested>
  <Cyclic management reaction; unconditional child calls>
  "FRK_RouteAbort"(Core := #Core, Abort := #Abort);
  <Abort / AbortInError reactions, when requested>
  IF #Core.Dispatch THEN <device logic using Core.Command and LatchedParCmd> END_IF;
  "FRK_End"(Core := #Core, Status := #Status, Busy => #Busy, Done => #Done, ...);
  <unconditional derived data and device output permits>
END_FUNCTION_BLOCK
```

Measured on the bench (S2, 2026-10-08): this frame compiles warning-clean on S7-1200
V4.7 and passes T1/T2/T4/T6, HELD and self-resume, registry, identity and the
mailbox cases on hardware.

`FRK_Begin` resets a previously published command terminal and accepts an
Execute edge. Generated initialization, parameter/metadata latching, management
and child work precede `FRK_RouteAbort`; dispatch follows abort reactions.
`FRK_End` resolves HELD, timeout, timing, outputs, status and one-shot release.
Tier is declared data, not a type relationship. The shared command kernel is
measured on simulated1516/Advanced7; full Unit facets remain subsequent work
([evidence](Siemens/Evidence/TIA_CORE_LIFECYCLE_2026-10-10.md)).

**The frame is generated, the device logic is authored.** The generator emits the
interface, both framework calls, the child calls and the hook skeleton from the
type declaration; the author writes only the regions marked as device logic and
hook reactions (TIA §5.2). A gate proves, on every commit, that each module FB
contains exactly one `FRK_Begin` first and one `FRK_End` last, both unconditional,
and that no authored region writes `Core` lifecycle members (TIA §5.3).

> This is where the binding is genuinely weaker than Part II, and it says so:
> on TC3 the compiler rejects a module that bypasses the base; here a gate does.
> The same is true of Core §3.3's containment rule (no Unit inside an EM), which
> the generator refuses to emit and the gate re-checks on the source.

### TIA §3.2 Capability query and module identity
*Binds Core §3.2, §3.7, §3.9.*

There are no interfaces and no upcasts. Capability is **declared data**, as in
AB §3.2:

- every module registers one row in the CPU-wide
  `FRK_Registry.Rows : ARRAY[0..FRK_MAX_MODULES] OF "FRK_RegistryRow"` during its
  first-scan setup; row `0` is reserved and means "none";
- a module reference used generically — the awaited child of a step, the rollup
  parent link, the mode-cascade target — is a **`DInt` registry index**;
- capability is a bitfield `Core.Capabilities`, set by the generator from the type
  declaration. Code tests a bit; it never infers capability from a tag's presence.

Typed, statically known relations do not go through the registry. A parent owns
its children as multi-instances and calls them directly; a sequence receives the
children it commands as **parameter instances** (TIA §3.5). The registry serves
only the *generic* walks — mode cascade, recipe prepare/commit/abort over every
descendant, the §6.9 stall walk, rollup — whose subject is "any module".

Registry rows hold compact, string-free fields (identity indices, tier, type id,
capabilities, `ExecState`, the first-out `ReasonCode`, severity, source index,
`DataRevision`); operator-facing paths and keys stay in each module's own
`Status` (Core §1.1 O9 — one source). Every index is range-checked before use
(Core §5.6); registry overflow is a fail-closed startup fault.

**[PROVISIONAL S2]** S7-1500 could hold `REF_TO` the registry rows, but references
may only be declared as FC parameters or `TEMP`, never stored (TIA V20 help,
"Declaring references"); the binding therefore uses indices on **both** families —
one mechanism, not two (Core §1.1 O9).

### TIA §3.3 Public contract variable classes
*Binds Core §3.10(a′)/(a″), §3.12, §6.1.*

- Module request data (`Execute`, `Abort`, `Command`, `ParCmd`, `ParCfg`) are
  `VAR_INPUT`; result data the block only writes (`Busy`, `Done`, `Error`,
  `Aborted`, `ErrorID`, `Timing`, `OutCmd`, `OutImm`, `HmiResponse`) are
  `VAR_OUTPUT`; published records the lifecycle also reads (`Status`) and the root
  `HmiRequest` (which the root itself writes when it clears `Secret`) are
  **published statics** — TC3 §3.3's input/output split exists because TwinCAT gives
  external code no other access, whereas STEP 7 publishes statics and warns when a
  block reads its own output or writes its own input (measured). Published child
  instances are static multi-instances; everything else is static with
  **`ExternalAccessible := 'False'`**.
- A record consumed by teach capture is also lifecycle-owned: captured
  `OutImm` / `OutCmd` records are readonly published statics. LOAD_DB quiescence
  likewise owns its `OutImm` mirror. This preserves the same published name,
  type and value without reading an unassigned FB output before publication.
- TIA's member attributes are the exposure control: **only `HmiRequest` carries
  `ExternalWritable := 'True'`.** Every other published member is
  `ExternalWritable := 'False'`, so neither the Web API, OPC UA nor an HMI connection can write
  a module input directly; the mailbox is the single Fraktal write surface and
  the PLC re-checks every request (Core §3.10(a″)).
- PLC composition code may assign a child instance's inputs (`#Ram.Execute :=
  TRUE`) — STEP 7 permits writing an instance's inputs outside its call — and reads
  its outputs; it shall not write a child's outputs (the compiler refuses).

### TIA §3.4, §3.6–§3.7 Mode, device, and cascade mechanics
*Binds Core §3.4–§3.7, §6.1, §6.3, §6.4.*

State machines and ordinals port unchanged. Execution rules:

- every module instance is called **unconditionally exactly once per scan** by its
  owner: children by their parent's generated call list, roots by the composition
  OB (TIA §3.11). No `EN` gating, no call inside `IF`; a conditional call skips
  edge, timeout, hold, abort and Execute-drop handling and is a gate failure;
- Unit mode, start/stop/reset, manual, decision and configuration requests arrive
  only through the root mailbox (TIA §7.7);
- one chain owns each sequence token and one owner calls each child; two chains
  never command the same child in one scan;
- child-Unit mode cascade and rollup use validated registry indices.

### TIA §3.5 Sequence binding — SCL reference form and S7-GRAPH chart form
*Binds Core §3.5, §5.5, §6.2–§6.3, §6.8, §6.12.*

A multi-step sequence is a **separate function block** called by its owner's
lifecycle-only adapter, with the same `FRK_Sequence` contract (`Seq : "FRK_SeqCtx"`:
step token, shared `RetVal`, step-scoped latches, step record) whichever language
renders it. SCL and GRAPH remain the measured runtime forms; the owner-requested
unwired LD examples add a third rendering:

1. **SCL (reference form, both families).** The Core §6.8 skeleton:
   `CASE #Seq.Step OF` where each branch owns its step's real behaviour —
   `"FRK_Seq_Step"(...)` record, child `Execute`/`Done` handshake, waits, timers,
   decisions — and ends with `"FRK_Seq_Advance"(Seq := #Seq, OnAdvance := <next>, ...)`,
   which commits the transition and clears the step-scoped latches. `RetVal` has
   exactly one writer per scan.
2. **S7-GRAPH (chart form, S7-1500 only).** The same graph as a GRAPH FB,
   **generated** from the chain declaration (`fraktal_tia_graph.py`, TIA §5.2) and
   never drawn by hand; the one exception is the reference chart whose TIA export is
   the writer's template. Settled by S11 on PLCSIM
   ([evidence](Siemens/Evidence/TIA_S11_GRAPH_PLCSIM_2026-10-09.md)):
   - A step `N<StepNo>` carries the step's behaviour in **actions**, which are `CALL`s
     of the `FRK_Seq_*` services (one parameter per line) and single-operand
     assignments, each `N` or once on activation (`S1`) or deactivation (`S0`). A GRAPH
     action admits **no `IF` and no expression** (measured), so a step's exit
     condition is its **transition**: an FBD network, the AND of the declared
     operands into the `TrCoil`. A condition a service needs is passed as an
     operand (`FRK_Seq_AwaitPending(..., Done := #CylA.Done, ...)` names a child only
     while it is pending). The chart is the only progression owner. `RetVal` and
     `FRK_Seq_Advance` belonged to the S11 SCL prototype. In the current typed
     example services, RetVal is shared: actions select ADVANCE/JUMP1, native
     transitions compare it, and only SCL/LD call FRK_SeqRoute to commit an exit.
     One declaration renders those exits (O9).
   - **Native scan boundary and fault recovery.** The current typed adapter uses
     `FRK_SeqGraphBegin`: GRAPH evaluates transitions before the new step actions,
     so the preceding active scan's result survives that evaluation. The mandatory
     `FRK_SeqStep` clears it before the current action decides. Fault, restart and
     recovery rearm boundaries discard the result. While faulted the owner continues
     shared command-release services and withholds the chart call, retaining the
     failed step. Leaving ERROR rearms step-scoped command/delay/event state and
     clears row errors; an accepted Start then follows the application's explicit
     resume-or-restart policy (Core §6.9(d)). The generated Unit frame owns these
     boundaries, including late kernel faults and restore quiescence, without an
     application scheduling call. The wired press chooses whole-chain restart on
     each accepted Start. See the [selected native recovery qualification](Siemens/Evidence/TIA_SEQUENCE_RECOVERY_2026-10-15.md).
   - GRAPH switches step and runs the new step's actions **in the same call**,
     together with the old step's `S0`. A child issued by a step is therefore
     raised one scan after entry: `S1 #Seq.Issued := FALSE`,
     `N #<child>.Execute := #Seq.Issued`, `N #Seq.Issued := TRUE`,
     `S0 #<child>.Execute := FALSE`. Without the delay, a child commanded by two
     consecutive steps would never see the Execute drop that Core §6.1 needs. Cost:
     one scan per issuing step compared with SCL.
   - The Core restart edges (first scan, mode change, fresh Start policy, both abort paths) drive
     **`INIT_SQ`**. On that call the chart runs the active step's `S0` (dropping its
     child commands), returns to the initial step and runs that step's actions.
   - A GRAPH FB **cannot be a multi-instance** (refused with or without GRAPH alarm
     handling). The owner takes it as a **parameter instance**
     (`VAR_IN_OUT Chart : "FB_<Thing><Mode>"`), exactly as it takes its children,
     and the composition root declares one single-instance DB per deployed chain.
     This is AB's per-owner chart rule (AB §3.5). A reusable owner type stays a type.
   - **Supervision and skip policy (S11, PLCSIM 1500).** Generated Fraktal charts
     shall keep the supervision/interlock networks empty and `SkipSteps = FALSE`;
     the Core services own pending waits, HELD and faults. `MaximumStepTime` and
     `WarningTime` values alone do not monitor a step: an empty-network step ran
     for 499–500 ms with `T_MAX = 100 ms` and no `ERR_FLT`. An explicit supervision
     condition does create a separate latch: with `AcknowledgeErrorsRequired`, a
     cleared condition and valid transition still wait for `ACK_EF`; without it,
     the chart advances. `SkipSteps = TRUE` omitted two intermediate steps and
     their `FRK_Seq_Step` records. Native acknowledgement therefore is not the
     Core operator reset, and skip mode would lose authoritative PLC history.
     The reader includes these settings, step times and V/C network topology in
     its read-back comparison ([evidence](Siemens/Evidence/TIA_S11_SEMANTICS_2026-10-09.md)).
   - **Download boundary (S11, PLCSIM 1516 V3.0).** An ordinary FC body delta
     loaded with `SoftwareOnlyChanges` while a child was BUSY, preserving the
     observed step, handshake and owner DB state without a stop/reinitialization
     question. A GRAPH action-label delta with unchanged exported DB interfaces
     requested **`TurnOffSequence` and `DataBlockReinitialization`** and loaded
     the chart DB. It therefore does not pass the state-preserving RUN gate.
     Changes-only download shall not imply preservation: the engineering workflow
     shall quiesce the affected owner and withdraw its outputs before a load that
     requires native chart turn-off/reinitialization. Restart requires the owner's
     reset policy and a fresh Start, rather than inferring permission from the
     retained command inputs ([evidence](Siemens/Evidence/TIA_S11_GRAPH_RECOVERY_2026-10-10.md)).
     **[PROVISIONAL S11]** enforcement by the production engineering driver,
     GRAPH manual/semi-automatic interface modes and physical S7-1500 evidence.

**Children are parameter instances.** The sequence FB declares the modules it
commands as `VAR_IN_OUT Ram : "FB_CylinderCM"; ...` and its owner passes its own
child instances: `#Auto(Seq := ..., Ram := #Ram, Door := #Door)`. This is the TIA
equivalent of TC3's owner-bound `REFERENCE TO` aliases: the step branch names the
child, the command and the wait, and no alias is stored or published.
Settled for S7-1200 V4.7 SCL by S2 and for GRAPH FBs on S7-1500 V3.0 by S11, where
InOut FB-instance members are read and written in actions and transitions. The call
cost is measured in S3.

**Encapsulated device actions.** New examples call the reusable module's typed
semantic functions, such as `F_CylinderExtend`/`F_CylinderRetract`, instead of
assigning child `Execute`, `Abort`, command ordinals or private state. The module
API and shared sequence services own issue ownership, completion/fault adoption,
release and the Execute-low boundary. Generated sequence frames own Begin/End
assembly. LD captures its dispatch step once per scan so rung order cannot
re-enter a later step after a forward transition. The process definition is the
authority for each carried rendition; no per-language lifecycle copy is allowed
(Core O1/O4/O9). Wiring into the complete Unit/diagnostic/sequence-view contract
remains an integration gate; the examples are not a full Core conformance claim.

The framework services that are methods on `FB_SequenceBase` in Part II become
**FCs taking `Seq` as `InOut`**: `FRK_Seq_Step`, `FRK_Seq_Await`, `FRK_Seq_Gate`,
`FRK_Seq_TryIssue`, `FRK_Seq_Delay`, `FRK_Seq_Advance`, `FRK_Seq_RunSub`,
`FRK_Seq_RunPar`/`FRK_Seq_ParJoin`, the part/decision/completion forwards and the
§6.9(d)/(e) raise/report services. The per-scan `RetVal` clear and the chain
restart on first scan, mode change and both abort paths are performed by the Unit
lifecycle for every attached chain (Core §6.8, O1); a project writes neither.

**Which renditions a station carries is a declaration choice** (AB §3.5): ST
only on S7-1200; SCL and/or GRAPH on S7-1500. Where a chain carries both, a
rendition gate proves identical steps and transitions (TIA §5.3):
`fraktal_tia_graph.py parity` reads the GRAPH SimaticML, including TIA's own
re-export, and the SCL `CASE`, and compares the step graphs. It is the same check
`check_consistency.py` performs for TC3's three AUTO renditions.

### TIA §3.8 Configuration, providers, and value-type binding
*Binds Core §3.8, §3.8a–e, §3.10.2, §5.6.*

**Physical type map, version 0.** The S7-1500 layout and Web API type/date
mapping pass S12 at the simulated1516 V3.0/Advanced7 scope below. S7-1200
timestamp/wide-field projection and optional OPC UA mappings remain
**[PROVISIONAL S12]**; clock accuracy is a separate gate.

| Core type | S7-1500 | S7-1200 | As observed through the projection (Web API / OPC UA) |
|---|---|---|---|
| enum (`E_*`) | `DInt` + generated constants (named value types not used, TIA §3.2 one-mechanism rule) | `DInt` + generated constants | Int32 |
| `BOOL`/`INT`/`DINT`/`UDINT`/`REAL` | same | same | same |
| `LREAL` | `LReal` | `LReal` | Double |
| `TIME` (durations) | `Time` (ms, 32-bit) | `Time` | Int32 ms — the HMI's `time` transport value (Core §3.10.2 ordinal 3) |
| `DT` (`Since`, timestamps) | `LDT` | **`DTL`** (no `DT`/`LDT`) | S7-1500 Web API: signed Unix-nanosecond decimal string decoded to DateTime ISO UTC with nine fractional digits; zero is Core's unset sentinel. S7-1200/OPC UA projection remains provisional |
| `STRING(n)` | `String[n]` through254; `WString[n]` for wider Core fields | `String[n]`, n ≤ 254, **narrowed widths** (TIA §3.8.1) | String; native Web API/HMI preserve the tested1500 widths255/480, Unicode and punctuation |
| fixed arrays | `Array[a..b] of T` | same | arrays / per-element nodes |
| `ULINT`/`LINT` | available | **not available** → `UDInt` pairs or `LReal` | S7-1500 Web API: exact decimal strings labelled UInt64/Int64; never round through a JSON floating-point number |

Core value type `TIME` keeps wire ordinal 3 and the transport name `time` (TC3 §3.8).

#### TIA §3.8.1 String widths and capacities are per-family constants

TwinCAT declares `STRING(255)` source paths, `STRING(160)` keys and 480-character
set lines. S7 strings stop at 254 characters, and every `String[254]` costs 256
bytes of a 150 KB work memory on S7-1200. The generator therefore emits the Core
string widths and table capacities (`MAX_MODULES`, `MAX_STEP_CONDS`,
`MAX_SEQUENCE_STEPS`, history/alarm ring depths, `MAX_CONFIG_SETS`, …) from a
**family profile**, and the gate rejects a deployment whose generated identities
or keys exceed the declared width — at generation, never by truncation at run
time (Core §5.6, O10). The S7-1200 profile values are fixed by S3 from measured
memory, not chosen in advance.

The S7-1500 reference profile retains Core capacities and declared character
widths subject to Siemens native representation limits. A Core field wider than
254 shall use a width-preserving representation; String's254-character limit
shall not silently narrow that field. S12 proves WString255/480 through the
compiled layout, native Web API and HMI adapter at the recorded1500 scope.
The 150 KB 1214C budget and compact candidate below are
specific to the constrained S7-1200 work; they shall not narrow the reference
family's contract or press scope.

**S3 candidate allocation (2026-10-10)** is recorded in
[the budget evidence](Siemens/Evidence/TIA_S3_BUDGET_2026-10-10.md) and generated
from the authoritative Core DUTs by `Spikes/S3_Budget/make_fixture.py`. Every
field remains present; enums use DInt, DT uses DTL, and configuration pointers
become UDInt indices for this storage experiment. The compact profile remaps
widths and reduces capacities; some short label fields become wider under its
uniform key policy. Its exact manifest and TIA read-back bind the measurements.
These are **candidate physical layouts**, not released types or proof of their
algorithms, retentive behavior or complete press fit.
The width gate shall also cover encoded configuration values, enum-domain lists
and constructed persistence/mailbox pieces. The candidate's 80-character
`ValueText` is not permission to truncate a longer declared parameter value.

The constrained S7-1200 generator shall share immutable configuration-write metadata by type or
generate it as constants (Core §1.1 O4/O9), rather than replicate maximum-sized
string tables in every module instance. Instance-dependent limits, revisions,
captures and dispatch targets remain instance-owned; identity is derived from
the registry. A persistence snapshot remains keyed by `Scope`/`WriteKey`
(Core §3.8b), never an opaque copy of an instance DB.

#### TIA §3.8b Persistence mechanics

**Retentive work memory is small and binary.** A retentive DB survives power loss
by Siemens' backup mechanism, but its layout is the instance layout: a changed
structure reinitializes it, which Core §3.8b treats as a restore failure, so the
`SchemaVersion`-first rule applies to every retained record.

The binding's `I_PersistMedium` realizations **[PROVISIONAL S16]**:

| Medium | Family | Mechanism |
|---|---|---|
| `LOAD_DB` | both | documents kept in load-memory DBs (`WRIT_DBL`/`READ_DBL`, asynchronous, write-cycle-limited flash — the gate bounds the write rate) |
| `CARD_FILE` | S7-1500 (S7-1200 if available) | memory-card files via the CPU file instructions, two slots per key with header/CRC exactly as TC3 `FB_FilePersistMedium` |
| `RETAIN` | both | a small retentive pool for counters and confirmations only |

File and load-memory access never blocks the cyclic task: every operation is an
asynchronous instruction polled across scans and surfaced as a Core §6.1 command.

### TIA §3.9 Feature selectability
*Binds Core §3.9.* Optional features are declared per type; the generator omits
storage and code for an unselected feature rather than publishing an inert one —
on S7-1200 the omission is memory, not just tidiness.

### TIA §3.10 Self-description exposure mechanics
*Binds Core §3.10(a)–(c), §3.10.1–§3.10.2, Core §11.1.*

#### TIA §3.10.1 Exposure by deployed root

Each deployed root Unit is a **single-instance FB with its own instance DB named
exactly as the root's local browse name** (`"PneumaticPress"`), called from the
composition OB. Its children are static multi-instances named as the schematic
names them (`Ram`, `Door`, …), so both projections publish the instance tree as
the browse tree — the Web API as symbolic names, the optional OPC UA standard
server interface as nodes:

```
Web API:  "PneumaticPress".Status."Name"      "PneumaticPress".Ram.Status.State
OPC UA:   Objects/<PLC name>/DataBlocksInstance/PneumaticPress/Ram/Status/State
```

The HMI mapper keys on `Status : ST_ModuleStatus`, deduplicates by the qualified
`Status.Name` and builds parentage from it (OPCUA_TRANSPORT "Snapshot"), so neither
the DB quoting nor the `DataBlocksInstance` prefix enters Fraktal identity.

- **Exposure by attribute, not by marker.** STEP 7 exposes every member whose
  "Accessible from HMI/OPC UA/Web API" attribute is set, to both projections at
  once; "Writable from HMI/OPC UA/Web API" gates writes the same way. The generator sets
  `ExternalAccessible := 'False'` on `Core`, every private member, every provider
  and scratch structure, and on every instance DB that is not a deployed root or a
  separately published data product (e.g. `FieldbusTopology`). A gate rejects an
  accessible private member (TIA §5.3, the TC3 §3.10 "no definition-level
  publication" rule restated for TIA).
- **Instance DBs of reusable types are never global roots.** Infrastructure FBs
  (drivers, catalogs, providers) live as multi-instances of the composition FB with
  `ExternalAccessible := 'False'`, so they cannot become extra browse roots.

#### TIA §3.10.2 Mailbox

`ST_HmiRequest`/`ST_HmiResponse` and `E_HmiRequestKind` ordinals are identical to
TC3 (wire contract, append-only); `HmiRequest` is a published static with
`ExternalWritable := 'True'` (TIA §3.3). The mailbox path (SET_MODE, START, STOP,
OPERATOR_RESET, acknowledgement by sequence) passed on the bench from PLC-side
writes; the client leg is S9 (Web API first, OPC UA where licensed). The client writes argument leaves, then
`Sequence` last; the root samples a changed `Sequence` once, copies the request to
private storage, clears `Secret`, routes it through the same gated operations
local code uses, and writes `AckSequence` after processing. **[PROVISIONAL S9]**:
write atomicity — whether a multi-tag write (an OPC UA multi-node Write, or a
Web API JSON-RPC batch of `PlcProgram.Write`) is applied within one cycle
boundary, or leaves may land in different scans. Neither protocol is relied on:
the client writes `Sequence` in a **separate** request after every argument write
returned success, which removes the ordering question by construction (the open
TC3/AB verification item, TC3 §3.10). A request that times out before
`AckSequence` matches is reported, never replayed.

#### TIA §3.10.3 Projection budgets

Both projections publish every accessible member, so published surface is a
budget, not a free choice (Core §1.1 O4). The Web API has no node or monitored-item
budget but a request and session budget (`Api.GetQuantityStructures`, **not offered
on S7-1200 G1 V4.7**, measured), and it polls: the gateway reads the fast tier at
the display rate and the rest on demand, exactly the tiering the HMI already
applies. **Measured on the 1214C V4.7.3 (S1W):** ≈ 57 ms per request + ≈ 15 ms per
leaf, nearly independent of batching — 10 leaves 205 ms, the spike Unit's 126 leaves
2.13 s in one batch. On S7-1200 the generator therefore budgets the **fast tier**
(what the HMI polls at 1–2 Hz) to a few dozen leaves per CPU and serves everything
else on demand; a whole-tree poll at display rate is not a design option there.
**[PROVISIONAL S3]** for the scan time the web server adds under that polling.
For the optional OPC UA projection:

- **S7-1500:** the standard interface plus the HMI's targeted/tiered reads; the
  generator reports the published node count per root against the CPU's
  recommended monitored-item figure.
- **S7-1200:** a press-sized Fraktal namespace exceeds the 1,000 recommended
  monitored items and may exceed comfortable Read sizes. The binding therefore
  defines a **generated user-defined server interface** (≤ 2,000 nodes) holding the
  fast tier and mailbox, with slow/on-demand data read on demand. **[PROVISIONAL
  S3]** for both the node count of a real tree and the scan-time cost of serving
  it; if S3 fails, the S7-1200 profile's self-description narrows to that
  interface and its declared exclusions grow (TIA Annex A).
- The configuration manifest (Core §3.10.2) is served paged through the mailbox
  exactly as on TC3, which is what keeps static metadata out of the cyclic set.

### TIA §3.11 Composition-root wiring
*Binds Core §3.11.*

The composition root is **`FB_<Project>Main`**, a single-instance FB called
unconditionally from the program-cycle OB `Main` (OB1). It owns the root call
sites, drivers, catalogs, providers and registry setup, performs scan ordering, and
contains no individual raw channel assignments (TIA §10.2.1). There is no
constructor, and there is nothing to construct:

Deployed roots use separate instance DBs named by their local root identities;
the composition FB calls them unconditionally. This gives each Web API root a
direct Status member and avoids a composition-DB prefix in its identity. The
2026-10-10 generated two-root fixture verifies eight exact native identities
and parent-first registration. The composition DB is not a super-root or module.

- **Identity is read, not written.** On its first scan each module calls
  `GetInstancePath` (S7-1200 and S7-1500) inside its own frame, strips the quotes
  (`"PneumaticPress".Ram` → `PneumaticPress.Ram`) and that is `Status.Name`. The
  qualified identity therefore *is* the instance tree — no generated or typed
  name can drift from the browse path (Core §1.1 O9, §4.8). Siemens advises
  against calling the instruction cyclically; the frame calls it once.
- **HAL is passed down the call tree.** A CM declares its HAL record as `VAR_IN_OUT`;
  each parent's generated call passes its own HAL bundle member
  (`#Ram(Hal := #Hal.Ram)`), and the composition FB passes each root its bundle
  from the project's HAL DB. The mapping is typed, visible in the call, and
  stored nowhere — the TIA counterpart of TC3's `REF=` injection.
- **Registration** happens in the same first-scan block, parent before children
  (the parent's frame runs before it calls them), so every child knows its
  parent's registry index.

The first-scan flag comes from OB1's `Initial_Call` (or OB100) and is consumed by
the roots. A gate proves every module instance contains the identity block and is
called before any code reads its identity (Core §3.11, AB G-SETUP).
**[PROVISIONAL S2]** `GetInstancePath`'s code-memory and one-shot runtime cost on
S7-1200, and its result inside parameter-instance calls.

### TIA §3.13 HMI projection and snapshot coherence
*Binds Core §3.13.* The HMI binds the same data as on TC3 and adds no per-station
or per-type code. **Measured S9, 1214C V4.7.3:** a Web API JSON-RPC batch does
**not** observe one scan. Ten batches each read the same cyclic counter sixteen
times; every batch returned differing values (spanning 106–111 increments).
Two authenticated clients, pinned socket reconnect with an existing token,
token invalidation after 160 s idle with explicit re-login, and retained-token
reads through native STOP→RUN also passed
([evidence](Siemens/Evidence/TIA_S9_READ_SESSIONS_2026-10-09.md)).
**[PROVISIONAL S9]** the S7-1500 and optional OPC UA read boundaries, and recovery
under a physical link interruption. The HMI treats each snapshot as eventually consistent
and gates writes on freshness (OPCUA_TRANSPORT "Snapshot"), so this bounds the
display, not command acceptance.

### TIA §3.14 Lifecycle binding — generated `FRK_Begin`/`FRK_End` composition
*Binds Core §2.2, §3.14.*

Hooks use framework-owned one-shot event flags (`EvInit`, `EvCommandStart`,
`EvAbort`, `EvAbortInError`) and generated reaction blocks. Abort flags are raised
after cyclic/child work by FRK_RouteAbort. The framework action precedes each
reaction; omitted reactions emit no empty IF. Cyclic management is a separate
per-scan region before abort, while derived data/output permits follow the mirror.

A reaction returning a value writes `Core.HookResult`; the owning framework
phase shall consume it. **OnModeExit is the specified exception** (Core §3.14.4):
the pending-mode reaction precedes cancel; >0 holds the transition and0 consents
to cancel/commit exactly once. The optional generator0.3 Unit profile now consumes this result before
cancellation and bounds pending exit with ParCfg timeout. Native deferral,
commitment and timeout controls pass in the Unit evidence. Other Unit/sequence
facets remain provisional.

**Quiescent fast path (measured, S3).** On a 1214C an idle CM costs ≈ 0.20 ms per
scan, of which ≈ 0.16 ms is the lifecycle re-deriving an unchanged READY state.
The generated frame therefore wraps `FRK_Begin` … reactions … device logic …
`FRK_End` in one guard and skips them while the module is **quiescent**:
`Core.Initialized AND Core.Exec = READY AND NOT Execute AND NOT Abort AND NOT
Core.ExecPrev AND NOT Core.AbortPrev AND Core.HoldReason = 0 AND NOT Core.EvInit`.
Every input that can change the state (an edge, an abort, a pending one-shot, a
hold, any non-READY state) takes the full path, and the outputs, `Status` and the
registry row already hold READY from the last full scan, so the result is
identical. Identity setup and the derived `OutImm` stay **outside** the guard
(Core §3.12: derived state is computed unconditionally). Measured: the S2 harness
17/17 on hardware with the guard, and an idle CM ≈ 0.053 ms instead of ≈ 0.20 ms
(≈ 0.039 ms is the bare call). The gate T-FRAME checks the guard's exact condition;
a type may not narrow it. Output permits shall remain outside the guard and
withdraw outputs in every applicable state, including READY after a completed
command. The S11 recovery probe exposed a latched cylinder coil when its
interlock was evaluated only during BUSY; the unconditional permit corrected
reset after completion ([evidence](Siemens/Evidence/TIA_S11_GRAPH_RECOVERY_2026-10-10.md)).
A CM declaring a cyclic management extension shall keep that extension and
its lifecycle resolution active every scan. The current generator emits its
full path without an idle guard; only CMs without management use the guard.
Composites remain unconditional in the current runtime slice.
Named statics called by name are the generated form: a
loop-indexed array of module instances costs ≈ 0.03 ms more per call
([S3 evidence](Siemens/Evidence/TIA_S3_SCAN_AND_MEMORY_2026-10-08.md)).

**Unit idle path (measured, S3, 2026-10-10).** A Unit keeps its mailbox,
unconditional child calls, per-scan sequence-result clear and published mirrors
outside the lifecycle guard. The S2 frame computes `LifecycleActive` once after
mailbox handling, with the condition above using `RunReq`/`AbortReq`, and uses
that same value around begin/reactions and end. Five idle Units plus ten child
CMs passed 19/19 with both frames; mean cycle fell from 3.452 to 2.443 ms,
about **0.202 ms per idle Unit**, for 0.06 KB additional work memory
([evidence](Siemens/Evidence/TIA_S3_BUDGET_2026-10-10.md)). This is the minimal
S2/S11 lifecycle, not proof of all Unit hooks. The full generated Unit predicate
shall also take the active path for pending mode exit/change, operator reactions
or any other framework one-shot; authored cyclic work remains unconditional.

### TIA §3.15 External connector and byte transport
*Binds Core §3.15.1a.* `I_ByteChannel` binds to the open-user-communication
instructions (`TCON`/`TDISCON`/`TSEND`/`TRCV`, or `TSEND_C`/`TRCV_C`), driven
non-blocking from the channel's state machine; S7-1500 may use secure OUC (TLS).
**[PROVISIONAL S13]** buffer sizes, connection counts (S7-1200: 8 reserved / 14
max open-user connections) and simulator support.

### TIA §3.16 Traceability and provider binding
*Binds Core §3.16.* `I_PartCarrier`, `I_RecipeProvider` and the other provider
seams become a **provider index plus one dispatch FB per seam kind** (AB §3.3's
"fewer seams" rule): a provider is a registered instance, selected by index, and
one `CASE` dispatches to the provider kinds the station declares. The shipped
default carrier is the local BY_POSITION carrier, as on TC3.

### TIA §3.17 Extension modes
*Binds Core §3.17.* Additional modes are declared values of the Unit's mode set;
an unsupported mode is rejected through the same path as on TC3.

### TIA §10.2.1 I/O integration placement

- a project **PLC tag table** `IO_<Project>` holds only `%I`/`%Q` symbols with
  leading-underscore names (Core §4.4 HAL marker);
- an `FB_<Project>IoDriver` is the only block that reads or writes those tags and
  maps them to typed HAL records;
- an `FB_<Project>IoCatalog` holds the approved tag/address/description/module-role
  join and configures `FB_IoTopologyPublisher`;
- the composition FB calls setup and the driver in scan order and contains no raw
  channel assignments. A gate rejects any other block referencing an `IO_` tag.

---

## TIA §4 — Project settings

### TIA §4.1 CPU and task baseline
*Binds Core §2.3, §4.1.*

- One program-cycle OB (`Main`, OB1) runs the composition FB. Cycle monitoring
  time and (on S7-1500) minimum cycle time are recorded per project; a cyclic
  interrupt OB is used for the forest only with controls-engineering approval
  (Core §2.3) and never shares state except through documented exchange.
- **Error handling is family-bound.** The project's supported event OBs cover
  time errors and hardware diagnostics (OB80/OB82, plus OB83/OB86 where offered).
  Framework blocks on both families use local error handling
  (`GET_ERROR`/`GET_ERR_ID`) and consume its result: continuing with a substitute
  value is not recovery. On the 1214C V4.7.3 and PLCSIM 1516 V3.0, a variable
  array index outside its bounds returned `GET_ERR_ID = 16#2522` and continued;
  on S7-1500 this bypassed OB121. S7-1500 also provides the programming-error
  OB121 as a fallback: the same access without local handling invoked it with
  `Fault_ID = 16#22`, `Reaction = 1`, then continued with zero. OB121/OB122 are
  not an S7-1200 fallback. A handler shall withdraw outputs and publish a Fraktal
  diagnostic, rather than merely suppressing the platform reaction.
  [S11 evidence](Siemens/Evidence/TIA_S11_SEMANTICS_2026-10-09.md) proves detection
  at fixture scope; **[PROVISIONAL S11]** other error classes, the no-handler
  reaction, and the generated diagnostic/output-withdrawal path.
- Instance DBs and multi-instances are optimized; the "IEC check" compiler option
  is **on** for framework blocks (no implicit conversions).

### TIA §4.2 Startup and deployment state
OB100 sets the framework's startup flag and nothing else; every root performs its
own first-scan setup from that flag (TIA §3.11). Startup parameter "Warm restart
— RUN" is the deployed default; the test projects use "No restart (STOP)" so a
test image never starts by itself after power-up (Core §5.7, TC3 §5.7).

### TIA §4.3–§4.7 Naming
Core prefixes apply with these TIA spellings:

| Core object | TIA object | Name |
|---|---|---|
| `FB_` function block | FB | `FB_<Type>` |
| `F_` function | FC | `F_<Name>`; framework FCs `FRK_<Name>` |
| `ST_` structure | PLC data type | `ST_<Name>`; framework-private `FRK_<Name>` |
| `E_` enumeration | generated constant family in a constant tag table | `E_<Enum>_<MEMBER>` |
| `GVL_` global variable list | global DB | `GDB_<Name>`; framework DBs `FRK_<Name>` |
| `PL_` parameter list | constant tag table | `PL_<Name>` |
| `PRG_`/`MAIN` | OB `Main` (OB1) + composition FB `FB_<Project>Main` | |
| `GVL_<Project>IO` | PLC tag table | `IO_<Project>` |

STEP 7 block and tag names are quoted identifiers and are not case-sensitive;
Fraktal names never rely on case to differ. Block numbers are assigned
automatically and are never part of a contract (the one exception is a test-only
result DB read by number, TIA §5.7).

### TIA §4.8 Browse-name source
*Binds Core §4.8.* A root's local name **is** its instance-DB name; a child's local
name **is** its static multi-instance member name. `Status.Name` carries the
dotted qualified identity built at setup. The gate proves that the final segment
of every generated `Status.Name` equals the member name it is published under.

---

## TIA §5 — Quality tooling

### TIA §5.2 Generation
*Binds Core §1.5, §2.2, §5.5, §6.8.*

`fraktal_tia_generate.py` reads a declaration (types, instances, sequences,
reasons, profile) and emits SCL external sources, GRAPH SimaticML, the constant
tag table and the OPC UA server-interface definition. Its GRAPH writer
(`fraktal_tia_graph.py`, implemented for S11) writes against a block TIA itself
exported, never against the schema alone. It reads every chart back, its own output
and TIA's re-export, into one canonical dump (steps, actions, edges, transition
operands). It is the only author of:
module frames, registry indices, `ExternalAccessible`/`ExternalWritable`
attributes, the enum constants (generated from the same ordinals as the TC3
DUTs and `reason_rationalization.json`), family-profile widths and capacities,
and the retention list. Generated files are committed and reviewable; hand
edits to a generated region are rejected by the gate.

### TIA §5.3 Structural gates
`tia_lint.py` (`FraktalCore/PLC/Siemens/tools`) runs on the source tree without TIA
(rule ids `T*`). Implemented 2026-10-08 for 11 rules, each proven by a test that breaks
exactly that invariant in a copy of the S2 sources (`test_tia_lint.py`, 18 tests);
T-TIER, T-IO, T-WIDTH and T-GEN need the generator's declaration model and are
reported as **pending**, never as passed. It runs in `.githooks/pre-commit`.
The2026-10-10 [structural declaration model](Siemens/Evidence/TIA_R4_DECLARATION_MODEL_2026-10-10.md)
now rejects containment/name/identity-width/registry-capacity violations and
derives a reference forest inventory. The subsequent
[frame/registry slice](Siemens/Evidence/TIA_R4_FRAME_REGISTRY_2026-10-10.md)
emits typed common contracts, HAL bundles/calls, setup and compact registry
services. Manifest-scoped source replay now checks containment, HAL/raw-I/O
boundaries, identity widths and generated bytes; the four rules retain pending
scope for unmodelled fixtures and later generator facets. Test boundary FCs
prove ordering/registration, not the full Core lifecycle. Composites in this
initial generated slice remain unconditional; its CM quiet guard and per-scan
derived work are compiled and exercised.

| Rule | Checks |
|---|---|
| T-FRAME | every module FB calls `FRK_Begin` and `FRK_End` once each, in that order; CMs without management may use the exact guard of §3.14; management/child work stays active; the measured S2 Unit may use two fences driven by its one exact `LifecycleActive` predicate, with mailbox, children and mirrors outside; other frames remain unconditional pending their generator model |
| T-CYCLIC | every child multi-instance called exactly once, unconditionally |
| T-CORE | no authored region writes `#Core.` lifecycle members |
| T-EXT | only `HmiRequest` is `ExternalWritable`; private members not `ExternalAccessible` |
| T-TIER | no Unit reachable inside an EM (Core §3.3) |
| T-SEQ | every non-terminal `CASE #Seq.Step` branch ends in `FRK_Seq_Advance`; GRAPH steps/transitions equal the SCL rendition (`fraktal_tia_graph.py parity`, run on the exported chart) |
| T-IO | no block but the project IoDriver references `IO_` tags |
| T-WIDTH | generated identities and keys fit the family profile's widths |
| T-GEN | generated regions unchanged since generation (hash) |
| T-CASE | every `CASE` has an `ELSE` (Core §5.6) |
| T-ASCII | source text is ASCII (TIA reads BOM-less sources as ANSI — TIA §2.5) |
| T-KEYWORD | a member whose name is a source-header keyword (`Name`, …) is declared quoted (`"Name"`): unquoted, STEP 7 drops it silently (measured) |
| T-COLLIDE | no two identifiers in one block differ only in case (constants vs. parameters: `BUSY`/`Busy`), and no reserved word (`dt`, …) is used as a name |
| T-OWNIO | a block never reads its own output nor writes its own input (TIA §3.3) |
| T-TYPEFILE | one `TYPE` per `.udt` file, nothing before the keyword |

### TIA §5.4 Import, compile, download and CI
The engineering driver is **`Fraktal.Tia.Cli`** (`FraktalCore/PLC/Siemens/tools/TiaCli`),
a TIA Portal Openness V20 program. One invocation runs a plan in one TIA session:
create the project, add the CPU by article number and firmware, set its address,
import external sources and SimaticML in dependency order, compile (software, and
hardware where configured), and optionally download. Every step, every compiler
message and every download question with the answer given is written as one JSON
line — the run is its own evidence record.

- **Compile is the build gate.** A compile with any error or warning fails the gate
  (Core §2 warning-clean rule).
- **Download is never implied.** It requires `--confirm-target <ip>` equal to the
  configured CPU address, and every security-relevant download question is
  answered only by an explicit flag: unencrypted sensitive data
  (`--accept-unencrypted-sensitive`), a lower CPU protection level
  (`--accept-lower-protection`; unanswered, the download stops before anything is
  written — measured), the CPU's user-management data (`--user-management
  keep|update|reset`, a required plan variable with no default) and passwords (the
  name of an environment variable, never the secret). Download is a controller-changing operation: it needs
  current authorization for the named target (AGENTS.md).
- The engineering account must be a member of the Windows group
  `Siemens TIA Openness` (Siemens requirement); without it TIA refuses the session
  with `EngineeringSecurityException` (recorded in R1). Membership takes effect in a
  new logon session.
- **The Openness firewall applies to headless instances too and is bound to the
  driver's file hash** (measured): a rebuilt driver fails with
  `EngineeringSecurityException: The operation has timed out` until its new hash is
  whitelisted by an administrator (`tools/Enable-TiaOpenness.ps1 -WhitelistExe`).
  Driver changes are therefore batched, and the driver reaches new settings through
  generic, reflection-based commands (`service-get/set/call`, `block-attribute`,
  `hw-attributes`) so a new setting needs a plan line, not a new build.
- **Online questions arrive as `ConnectionConfiguration.OnlineLegitimation` events**
  (TLS certificate verification, read password, user authentication); unanswered
  they default to "not trusted" and the connection fails with no detail. The driver
  answers TLS verification `Trusted` only when `--trust-plc` names the PLC asking,
  and logs the verification text; a second subscription in one session throws, so
  each step releases its handler. TIA dialogs arrive as `TiaPortal.Confirmation`
  events and are logged, never answered implicitly.
- **Source-generation errors carry no detail through Openness** (`DetailMessageData`
  was empty); a failing source is located by its file, which is one more reason for
  one type per file.
- Plans: `station_<target>.plan` once per target (TIA §2.5), `build_<target>.plan`
  every build (delete program, import, compile 0/0, export), `download_<target>.plan`
  for the controller-changing step, and `webapi_<target>.plan` once to switch the
  web server on (HTTPS only), create its certificate (`webserver-certificate`, kept
  once created) and the gateway's web user (`webserver-user`, password read from an
  environment variable only) — all offline engineering state the next download carries.

### TIA §5.5–§5.6 Language and defensive coding
*Binds Core §5.5, §5.6.* Framework: SCL only. Application sequences: SCL or
S7-GRAPH (S7-1500), plus the optional unwired LD examples of TIA §1/§3.5.
Permissives/release examples carry ST and LD; shared collection/diagnostic behavior
stays in SCL. Defensive rules are Core §5.6 unchanged; the IEC
check option and T-CASE make implicit conversions and missing `ELSE` compile- or
gate-time failures.

### TIA §5.7 Unit-test framework and runner
*Binds Core §5.7.* There is no TcUnit equivalent in STEP 7. Fraktal/TIA ships a
small SCL test framework, `FRK_Test*`: a suite is an FB that drives modules
through their HAL against the shared sim plant models and records assertion rows
(suite, case, expected, actual, pass) in a bounded result table; a runner FB
sequences the suites after start-up. The host-side runner
(`fraktal_tia_test.py`) downloads the test image through `Fraktal.Tia.Cli`, waits
for completion, **harvests the result table**, and emits JUnit.

Harvest paths: the Web API (a read of the result DB, **[PROVISIONAL S1W/S5]**); or —
measured on the S7-1200 bench, where `ProtectionEnablePutGetCommunication` is not
reachable through Openness and no web server is assumed — the **test image's own TCP
result server**: a passive open-user-communication connection (`TSEND_C`, port
2000) sending the non-optimized result table every 500 ms to whichever host
connects; the host only receives (`tools/s7_probe.py harvest --tcp 2000 --junit`).
It needs no licence and no PUT/GET, and exists only in test images. A non-optimized
result DB read over PUT/GET remains possible where a test project can permit it. A test
image is downloaded only to the isolated bench and is never a boot image (its
startup mode is STOP, TIA §4.2). Rows T1/T4 and the T2/T6/T7/T10 mechanisms are
proven once in the framework suite (Core §5.7); a generated-composition binding
additionally proves that every concrete type contains exactly one frame
(T-FRAME), which the gate does statically.

---

## TIA §6 — Command execution & sequencing binding
*Binds Core §6.1–§6.12.* Semantics are Core's, unchanged: the PLCopen handshake,
Execute-drop reset, abort and hold, `OperatorReset` that releases the Unit command
and every child command the suspended chain issued, run styles, single-step,
decisions, parallel legs (`FRK_Seq_RunPar`), and the §3.13 four-table step
publication. The TIA scan order follows Core §2.2 exactly: composition FB →
each root (mailbox, `FRK_Begin`, hook reactions, **children**, rollup, attached
chains while BUSY, `FRK_End`). Because children are cyclic work and the chain is
dispatch, a chain's command is seen by the child on the **next** scan and the
child's `Done` by the chain on the scan after — a two-scan command/result loop,
the same deliberate latency AB §3.5 documents for its SFC runner. S11 measured it
for SCL on the 1214C and for GRAPH on PLCSIM. The GRAPH form adds one scan per
issuing step (§3.5). No project compensates for it.

---

## TIA §7 — Permissives, interlocks, access, and mutation surface

*Binds Core §7.1–§7.8.*

- `PermIntlk` is an SCL FB with the Core condition records; conditions are
  written in SCL by the project, under the owning Unit branch (`Release/`).
- **Commissioning gates (Core §7.5).** A gate is a **PLC user constant** in a
  generated constant tag table (or a block `CONSTANT`), never a tag: changing it
  needs a source change and a download. STEP 7 has no conditional compilation, so
  the framework gate `OUTPUT_FORCING` is a constant in the framework's constant
  table whose production value is FALSE; an engineering image is generated with
  TRUE and is therefore a different, auditable artifact. Gates are declared into
  `FB_EngineeringMode` exactly as TC3 §7.5 describes.
- **Access (Core §7.7).** The Fraktal principal is the mailbox `LOGIN` session
  checked by the root's access manager, as on TC3. STEP 7's own user management
  (UMAC: S7-1200 V4.7 offers 42 users / 14 groups / 20 roles) protects the
  *engineering and web* access to the CPU and is not a substitute for the Fraktal
  session. The local user table is kept as salted iterated hashes in a load-memory
  document (TIA §3.8b), never in an accessible DB.
- **Act-or-explain (Core §7.8).** A Unit's `Start` consumes the Boolean returned by
  `ReleaseReportStart`, which fills a caller-owned report in place (`InOut`), as TC3
  §5.7 requires for stack reasons; S7-1200's 16 KB OB1 local data makes the in-place
  rule binding here too.

---

## TIA §8 — Diagnostics & performance binding

### TIA §8.11 Timing sources
*Binds Core §8.11.4(e).* S7-1200 has no `TIME()`-style monotonic function. The
framework's timing source is one `FRK_Clock` record updated once per scan in the
composition FB from the `RUNTIME` instruction (S7-1500: `RUNTIME` or `RT_INFO`),
accumulated as a monotonic millisecond counter that wraps like TC3's `DWORD`
difference. Wall-clock stamps come from `FRK_Now()` (TIA §2.7). **[PROVISIONAL
S12]** `RUNTIME` resolution and drift on S7-1200.

On simulated1516 V3.0, the S12 once-per-scan accumulator follows the simulator's
system clock within8.664ms across the recorded ten-minute comparison. It falls
120-123 seconds behind host time over the separately recorded hour, outside
the declared prototype tolerance. Virtual-time consistency and physical
oscillator accuracy are separate claims; the host comparison shall not be
presented as a successful physical drift test or repaired by an undocumented
scale factor.

### TIA §8.12 System health
*Binds Core §8.12.* Cycle time and jitter come from `FRK_Clock`. Controller
metrics (memory use, CPU load, temperature) are read where an instruction
provides them (`RT_INFO`, `Get_IM_Data`, diagnostic buffer access on S7-1500);
any metric the family cannot supply is a **declared exclusion**
(`Available=FALSE`, AB press81 precedent), never a standing alarm or a healthy zero.

### TIA §8.9 Alarm rationalization
*Binds Core §8.8/§8.9.* `reason_rationalization.json` remains the authority; the
generator emits the reason constants and the catalog lookup FC from it. The
Fraktal alarm log is PLC data published through the Self-Description Service.
Projecting it to STEP 7 Program_Alarm/ProDiag (S7-1500) is an optional,
binding-qualified projection, never the source.

### TIA §8.13 Signal tower
*Binds Core §8.13.* Unchanged from TC3 §8.13: semantic outputs only; the project
IoDriver maps them to `%Q`.

---

## TIA §9 — Safety binding

*Binds Core §9.1–§9.8.* The certified safety system is **STEP 7 Safety** on an
F-CPU (S7-1500F / S7-1200F) with **PROFIsafe** F-I/O. Safety functions are written
in the F-program with certified F-blocks; the standard program reads F-data
(F-runtime group outputs, F-I/O status) read-only and maps it into
`ST_SafetyStatus`/`ST_ControlPowerStatus`. Standard-to-safety values are requests
only. The F-program's collective signature is tracked separately (Core §13, §14.2).

**Scope note.** The bench CPU 1214C is not an F-CPU, and the press bench is ported
**without power control** (owner decision 2026-10-08): `FB_PowerGroupCM`, the
control-domain coordinator and the Control On circuit are out of the initial
claim (TIA Annex A). The §9.8 profile is therefore not claimed by Fraktal/TIA yet.

---

## TIA §10 — Fieldbus binding

### TIA §10.1 PROFINET
*Binds Core §10.1.* PROFINET IO is the primary fieldbus; the IO system, device
names, topology and update times shall be documented. S7-1200 controls up to 16
IO devices (RT, no IRT); S7-1500 per its data sheet.

### TIA §10.5–§10.6 Fieldbus diagnostics and topology
*Binds Core §10.5, §10.5.1.* `FB_PnBusHealth` derives IO-system and device state
from `DeviceStates`/`ModuleStates` and `Get_Diag`/`GET_DIAG` (bounded, sampled,
never per-scan per-device), plus OB82/OB83/OB86 events; `FB_IoTopologyPublisher`
joins it with the project catalog and publishes `ST_FieldbusTopology` exactly as
TC3 §10.6 describes for EtherCAT. **[PROVISIONAL S3]** instruction availability
and cost on S7-1200. Output forcing (Core §10.5.1) follows TC3 §10.6 semantics
with the TIA §7 constant gate.

### TIA §10.6 Motion
*Binds Core §10.6.* PLCopen `MC_*` on technology objects: S7-1500 `TO_PositioningAxis`/
`TO_SpeedAxis`; S7-1200 `TO_PositioningAxis` (PTO or PROFIdrive). The press
`PartFeed` axis is the first motion module; **[PROVISIONAL S14]** for both families.

---

## TIA §11 — Connectivity binding

### TIA §11.1a Web API projection (default)
*Binds Core §11.1, §3.10, §14.* The CPU's web server publishes the forest through
its Web API (TIA §1 transport decision); the gateway's `WebApiSessionClient`
(`s7web://` endpoint, `packages/fraktal_opcua_client`, specified in
OPCUA_TRANSPORT "Siemens S7 Web API transport") turns it into the gateway
protocol the Web HMI already speaks — **implemented and measured end to end on the
bench** (gateway discovery, snapshot, mailbox commit + acknowledgement, write-root
and replay refusal; the unchanged mapper rebuilds the forest from the captured
snapshot). First deployment is
accepted in layers, each its own checkpoint: TCP 443 listening; the TLS server
certificate's SHA-256 fingerprint equal to the one pinned at commissioning (a
self-signed CPU certificate is verified by pin, never by "accept any");
`Api.Ping`; `Api.Login` as the gateway's web user; `PlcProgram.Browse` of each
deployed root DB exposing `Status`; a read of the fast tier; writable root
`HmiRequest` leaves only (every other write refused by the attribute); and a
matching `HmiResponse.AckSequence`.

- **Users live where the family keeps them.** S7-1200 V4.7 has no classic web-user
  list (no `WebserverUserManagement` service, measured): web users are UMAC project
  users, so access control is enabled as `EnabledWithAccessControlViaAccessLevel` —
  engineering and HMI access stay on the classic access levels, and only the web
  users are UMAC users with a custom role carrying exactly the named device function
  rights (`umac-user`, TIA §5.4). The CPU's user data changes on download only by an
  explicit `--user-management keep|update|reset`.
- **Rights.** The gateway's web user holds read-tag and modify-tag rights only — no
  operating-mode change, firmware, backup/restore or file rights. Which HMI user may
  command is the gateway's Core §14 role mapping, as on AB; the PLC re-checks every
  request through its own §7.6/§7.7 gates. A read-only station gives the gateway a
  user without modify-tag right, so the CPU itself refuses writes.
- **Token.** `Api.Login` returns a session token sent as `X-Auth-Token`; it expires
  when idle, and the client re-authenticates on `Invalid token` rather than
  replaying the failed request blindly (a mailbox write is never replayed).
- **Certificate.** Created once in the station project from the WebServer template
  (`webserver-certificate`, TIA §5.4) and kept; replacing it is a deliberate act
  that re-pins every client. Measured template on the 1214C: subject
  `PLC-1/Webserver-<n>`, RSA/SHA-256, two subject alternative names, valid to 2037.
- **One manual engineering step on S7-1200 V4.7 (measured).** HTTPS also needs a
  *certificate type* (TIA's internal `WebserverCertificateType`: hardware-generated
  or downloaded with the software). Openness V20 knows the name but supports neither
  its getter nor its setter on the 1214C, so it is set once in the TIA editor
  ("loaded via the software", i.e. the project certificate above) and kept in the
  station project (TIA §2.5). Until then the hardware compile fails with "No
  certificate type is assigned to the Web server security" and download refuses —
  a gap fails closed. The engineering gate re-probes the setter on every run.
- **Measured on S7-1200 G1 V4.7.3** ([S1W](Siemens/Evidence/TIA_S1W_WEBAPI_2026-10-08.md)): `Api.Version` 1.473, 14
  methods including `PlcProgram.Browse/Read/Write` and `Syslog.Browse`; port 80 closed,
  443 open; reads are **leaf-only** — a structure or `DTL` read whole is `204
  Unsupported address`, so `DTL` is read as its 8 members; private members do not
  exist to the client (`200`); every non-mailbox leaf refuses writes (`205
  read-only`); no token → `2 Permission denied`; a second `Api.Login` on a live token →
  `101 Already Authenticated`; the mailbox acknowledges in ≈ 140 ms. Still owed: token
  expiry, restart/link-loss recovery and concurrent clients (S9), scan-time cost (S3).
- **Measured on simulated S7-1500 V3.0 / Advanced7**
  ([S12 continuation](Siemens/Evidence/TIA_S12_WEBAPI_ADVANCED7_2026-10-10.md)):
  `Api.Version`5; symbolic Read/Browse work with process-data-only rights.
  The preserved DTL image passes1340 public witnesses. Whole DTL reads return204;
  member browse succeeds. The width-preserving LDT reference candidate passes
  1081 native witnesses and the live HMI client/date parser passes36 checks
  over99 Good leaves. Native `ldt` is an exact signed64-bit decimal string;
  the transport decodes Unix nanoseconds into a DateTime ISO UTC value, retaining
  nine fractional digits, and preserves zero as unset. Invalid encodings become
  Bad values without retaining an older Good value. `time` is signed Int32 ms.
  Generic HMI DateTime parsing retains microseconds. This establishes encoding,
  not synchronized UTC quality, hardware drift, a rendered Unit forest or commands.

### TIA §11.1 Embedded OPC UA server (optional, licensed)
*Binds Core §11.1, §3.10.* Where a site licenses it, the CPU's OPC UA server
publishes the same forest (TIA §3.10) and the native HMI connects directly.
First deployment is accepted in layers, as TC3 §11.1 requires: TCP listener,
SecureChannel, activated session, the SIMATIC namespace present in
`Server/NamespaceArray`, an authorized browse exposing
`<PLC>/DataBlocksInstance/<Root>/Status`, writable root `HmiRequest` leaves only,
and a matching `HmiResponse.AckSequence`. The S7-1200 server requires the "Basic"
runtime licence; S7-1500 "Small/Medium/Large" by CPU class.

### TIA §11.2 Endpoint security
*Binds Core §11.2, §14.* Production: `Basic256Sha256` Sign&Encrypt with user
authentication, anonymous disabled; anonymous/None only for a recorded
commissioning activity, as on TC3. Web API: HTTPS only, pinned certificate,
authenticated user, no anonymous rights ("Everybody" has none). The gateway and
installer are the shared artifacts, with the Web API session client added.

### TIA §11.6 Host events
*Binds Core §11.6.* Each root publishes its bounded host-event ring through the
same projection; ordinals are the checked append-only HMI contract.

### TIA §11.7–§11.11 Optional projections
Optional, binding-qualified, generated from the same model; none is claimed.

---

## TIA §12 — Spike register

| # | Spike | Bench | Kills/narrows if… |
|---|---|---|---|
| S1W | Web API data and time path (default projection): method set, browse of a root DB, structured members, strings, arrays, `DTL` encoding, batch reads and their latency, writes refused by attribute, sessions and token expiry, scan-time cost; NTP status visibility | 1214C (+ PLCSIM 1500 for shape) | the contract cannot be read/written within budget → fallback to the OPC UA projection (licensed) or an OUC protocol |
| S1 | OPC UA data and time path (optional projection): browse of `DataBlocksInstance`, structured members, strings, arrays, `DTL`/`LDT` encoding, writes, licence behaviour | 1214C (+ PLCSIM 1500 for shape) | that projection is not offered on the family |
| S2 | Module FB form: direct contract members, `FRK_Begin`/`FRK_End` FCs with `InOut` UDT, parameter instances (incl. multi-instances), instance-input writes, attribute exclusions | 1214C | the frame cannot be expressed → §3.1 changes |
| S3 | Scale and memory: a 10–60 module forest, work-memory use per type, scan time, published leaf count and comm load under Web API polling, diagnostics instruction cost | 1214C, then S7-1500 | the S7-1200 profile cannot hold a press → exclusions grow or the family is dropped |
| S4 | Source round-trip: external source and SimaticML (incl. GRAPH) import → compile → generate source/export → compare; library-type versioning via Openness | Openness | no faithful text form → no gate |
| S5 | Test execution: harness, startup-STOP test image, result harvest (OUC TCP; Web API), PLCSIM automation | 1214C, PLCSIM | no automated runner → §5.7 narrows to the hardware bench |
| S6 | Download of changes without reinitialization vs. registry/instance growth | 1214C | online extension impossible → commissioning workflow changes |
| S7 | Live tree reconstruction by the unchanged HMI through the gateway's Web API session client; manifest paging | 1214C + HMI | the HMI needs a TIA-specific adapter |
| S8 | Security: web users and rights, HTTPS pinning, OPC UA policies (if used), protection levels, PUT/GET off, TLS PG comm | 1214C | writes cannot be protected to Core §14 |
| S9 | Repository parity: snapshot coherence, write atomicity of the mailbox, freshness, reconnect, no replay | 1214C + HMI | the HMI could act on stale/ambiguous data |
| S10 | Optional projections (Program_Alarm, companion specs) | S7-1500 | never kills the base port |
| S11 | Execution and restart: SCL vs. GRAPH parity of one graph, chain/child scan latency, OB100/first scan, download/STOP-RUN, error OB behaviour | 1214C (SCL), PLCSIM 1500 (GRAPH) | neither form reproduces the contract; a GRAPH failure disables that form only |
| S12 | Physical type map, `RUNTIME` timing, string widths, constants mechanism | 1214C, PLCSIM 1500 | the public contract narrows or changes meaning |
| S13 | Byte transports (OUC TCP) | 1214C | connector-derived families excluded from the initial claim |
| S14 | Motion (`TO_PositioningAxis`, `MC_*`) | S7-1500 | motion excluded or profiled |
| S15 | Automated executable gate: Openness import/compile/download/harvest headless | Openness | lint passes code STEP 7 cannot run |
| S16 | Persistence media: load-memory DB documents, card files, retentive pool | 1214C, S7-1500 | §3.8b persistence narrows on that family |

S1W, S2, S4, S5, S7, S8, S9, S11, S12 and S15 decide whether this is a conforming
base port; S3 decides whether the S7-1200 family is in it. S1 decides only the
optional OPC UA projection.

**Status 2026-10-08** ([evidence](Siemens/Evidence/TIA_S2_S15_FIRST_BENCH_RUN_2026-10-08.md)):
S15 **PASS (bench)**; S2 **PASS (fixture scope, bench)**; S5 **PASS on the TCP
harvest path (bench)**; S11 SCL leg partial (one chain's trace, two-scan
command/result loop); S13 first use (passive `TSEND_C` result server works); S4
first look (canonicalizable, ASCII rule; exports BOM + ASCII). **S1W PASS
(functional, bench; throughput-narrowed on S7-1200)**, S9 mailbox leg PASS, S8 web
part PASS on the bench posture, and the ASCII image 17/17 ×3; **S7 PASS (bench, spike
scope)** — the unchanged Web HMI, served by the gateway's `s7web` transport, discovered,
rendered and commanded (Start/Stop) the spike Unit; S3's polling cost measured
([evidence](Siemens/Evidence/TIA_S1W_WEBAPI_2026-10-08.md) §8–§10). **S3 first
numbers** ([evidence](Siemens/Evidence/TIA_S3_SCAN_AND_MEMORY_2026-10-08.md)): S2 image
19.7 KB of 150 KB work memory; **≈ 1.16 KB work memory and ≈ 0.04 ms cycle per
idle CM** with the quiescent fast path (§3.14; ≈ 0.20 ms without it); real generated
types measured in **S3 2026-10-10**
([evidence](Siemens/Evidence/TIA_S3_BUDGET_2026-10-10.md)): Unit guard saves about
0.202 ms/idle Unit; complete Core-derived status/state, alarm, sequence and
configuration fields survive TIA read-back. The combined compact storage image
uses 96.89/150 KB and passes 19/19. An isolated eight-row compact configuration
write table costs 5.49 KB, so dense per-module allocation fails the proposed
2.5 KB whole-module budget. Candidate capacities, complete runtime/press fit,
full published surface and hook coverage remain provisional.
**S11 GRAPH leg PASS (PLCSIM 1500, 2026-10-09)**
([evidence](Siemens/Evidence/TIA_S11_GRAPH_PLCSIM_2026-10-09.md)): a GRAPH chain **generated** from a declaration
compiles 0/0, survives TIA's re-export unchanged, walks the SCL chain's trace
`0,100,110,120,100,110`, and restarts mid-run through `INIT_SQ`. It runs as a
parameter instance, since a multi-instance is refused. 19/19 rows on three downloads.
**S11 supervision, acknowledgement, skip, OB100/first-scan and local-error legs
measured 2026-10-09** ([evidence](Siemens/Evidence/TIA_S11_SEMANTICS_2026-10-09.md)):
28/28 on PLCSIM after download and after a direct STOP→RUN; 19/19 on the physical
1214C after download/start. Four generated probes survive TIA read-back including
their supervision wiring/settings. S7-1500 OB121 and both families' local
invalid-index handling are measured. **Native physical restart and code-only
download-in-RUN PASS, idle SCL fixture scope**
([evidence](Siemens/Evidence/TIA_S11_NATIVE_2026-10-09.md)): 19/19 after direct
STOP→RUN and each of two code deltas, with preserved DB/OB100/mailbox state on
the second delta. The temporary diagnostics-mode right was restored to
diagnostics-only with compile/download 0/0, authenticated native mode forms
absent and gateway reads/19-case results preserved
([evidence](Siemens/Evidence/TIA_S11_ENUMERATION_2026-10-09.md)).
**Active GRAPH recovery measured on PLCSIM 1516 V3.0, 2026-10-10**
([evidence](Siemens/Evidence/TIA_S11_GRAPH_RECOVERY_2026-10-10.md)):
16 checks passed; state-preserving GRAPH download remains unpassed. Fifteen
completed baseline harvests passed 28/28. Explicit reset while BUSY and native
STOP→RUN withdraw outputs and require a new Arm in the test owner. An FC delta
preserved observed BUSY/step/DB state; a GRAPH body delta requested turn-off and
DB reinitialization despite unchanged exported interfaces. A READY-coil release
defect was corrected by applying the CM interlock to outputs outside its idle
guard; motion, completion, reset after completion and restart then passed.
This is mechanism evidence, not proof of the full generated Unit lifecycle.
S11 still owes a quiesced GRAPH deployment workflow, retentive state, other error
classes and GRAPH manual/semi-automatic modes. **S9 read/session legs measured**
([evidence](Siemens/Evidence/TIA_S9_READ_SESSIONS_2026-10-09.md)): two clients,
pinned reconnect, idle-token invalidation/re-login and retained-token STOP→RUN
reads; single-scan Web API batch coherence disproved on the 1214C. Cable-pull,
retained-client download and end-to-end HMI freshness remain open.
S12/S4 now have a complete Core-derived compiled layout and canonical source
round-trip on simulated1516 V3.0. The strict shared parser recovers same-line
fields and publication attributes; the initial incomplete census is retained
and superseded. At that Advanced5 scope, login/permissions succeeded but protected
reads returned code2; SDK observations did not close the Web API/HMI gate.
The final [S12/S4 evidence](Siemens/Evidence/TIA_S12_TYPES_ROUNDTRIP_2026-10-10.md)
records1405/1405 type witnesses and43/43 scalar checks, including295 enum
constants and wide-string operations. The one-hour host comparison fails;
the separate simulator-system-clock comparison passes. Hardware clock accuracy
and synchronized UTC quality remain unproven.
The subsequent [native Web API isolation controls](Siemens/Evidence/TIA_S12_WEBAPI_RECOVERY_2026-10-10.md)
prove authenticated operating-mode reads with diagnostic rights, but symbolic
Read/Browse still fail with a minimal three-field DB. CommunicationMode0 does
not resolve the denial; mode1 and process-data-only rights were restored.
The owner then installed Advanced7. The
[supported-runtime continuation](Siemens/Evidence/TIA_S12_WEBAPI_ADVANCED7_2026-10-10.md)
recovers symbolic Read/Browse on the preserved image before any program or
hardware configuration change. The manager, API5 compatibility DLL and virtual
adapter changed together; the comparison does not isolate one cause.
The reference Core DT mapping is now LDT. The candidate retains88 types/610
fields/Core capacities, passes1081/1081 native and1146/1146 SDK type witnesses,
43/43 SDK scalar checks and269-source canonical reimport. Its real HMI
transport/date parser passes36 checks over99 Good leaves. This closes the1500
type/date projection gate; Phase3 full forest rendering/commands, production
clock quality and the1200 timestamp projection remain open. The subsequent
[frame/registry generator](Siemens/Evidence/TIA_R4_FRAME_REGISTRY_2026-10-10.md)
passes103 runtime boundary assertions and36-block/19-interface canonical
reimport. Manifest-scoped source replay is implemented. The [shared command kernel](Siemens/Evidence/TIA_CORE_LIFECYCLE_2026-10-10.md)
now passes238 assertions in55 simulated scan cases and after STOP/RUN,
with100 native public witnesses and7 private refusals.47 blocks/18 interfaces
round-trip; generation can include the kernel with command catalogs/timeouts.
The [Unit control slice](Siemens/Evidence/TIA_UNIT_CONTROLS_2026-10-11.md)
adds declared modes, a static writable mailbox, shared operation/release checks,
generated recursive command release and a local BY_POSITION carrier.103 native
checks pass, including guarded STOP/RUN and post-restart operation.79 blocks/
34 interfaces round-trip warning-free. The subsequent
[nested Unit/manual slice](Siemens/Evidence/TIA_UNIT_ROUTING_2026-10-11.md)
passes120 native checks across24 instances: three Unit levels, safe mode
rejection, manual catalog/routing/release rollup, one parent reset and STOP/RUN.
104 blocks/40 interfaces round-trip warning-free. The subsequent
[static manifest/native HMI slice](Siemens/Evidence/TIA_STATIC_MANIFEST_HMI_2026-10-11.md)
passes241 native manifest checks plus120 routing regressions. Generator0.5 keeps
catalogs private and serves16-entry pages through a typed ownership walk. The
native HMI maps24 modules/two roots, hydrates492 entries, renders manual controls
and commands the CPU from the rendered button. Its test-only display policy is
NONE; authentication is not established.117 blocks/41 interfaces round-trip0/0;
production114/41 compiles0/0. Authentication/full audit, alarm/state/recipe/retention,
complete action/frontier releases and sequence/GRAPH remain open; this is not
complete Core conformance.

The subsequent [access/session slice](Siemens/Evidence/TIA_ACCESS_SESSIONS_2026-10-11.md)
passes122 native access checks and120 current routing regressions. Generator0.6
owns private Core-compatible salted hashes, correlated asynchronous login, root
sessions/idle expiry and gated policy edits. The native HMI uses an actual operator
login and its normal OPERATOR display policy.129 blocks/42 interfaces round-trip0/0;
production125/42 compiles0/0. User/policy persistence and the full MESSAGE/alarm
model remain PROVISIONAL; the existing trace is not full audit conformance.

The subsequent [state/alarm slice](Siemens/Evidence/TIA_STATE_ALARMS_2026-10-11.md)
passes96 native state/event checks,23 nearest-Unit/ancestor-reset checks and122
authentication regressions. Generator0.7 publishes unconditional derived states
only on consuming types and Core-sized active/closed event logs on Units. Native
148/45 round-trip and production142/45 compile0/0; the authenticated generic HMI
renders the fault and resets it. Access/Part occurrences now use AUTO_RESET events;
History remains diagnostic fault history. Shelving, runtime project metadata,
durable sinks, retention, full diagnostic selection and sequence integration
remain PROVISIONAL. This does not close full Core alarm/audit conformance.

The subsequent [config transaction slice](Siemens/Evidence/TIA_CONFIG_TRANSACTIONS_2026-10-11.md)
passes120 native config checks,122 access and96 state/alarm regressions. Generator0.8
owns editable station config/model config, keyed local-retain records and atomic
local-model prepare/commit/abort.190 authored blocks/52 interfaces round-trip0/0;
production183/52 compiles0/0. A separate7-check probe proves public/private retention
across STOP/RUN and simulator power cycle. This is partial S16 evidence; named
sets, file/load-DB media, user/policy/alarm retention and download loss boundaries
remain PROVISIONAL. The optional line config runtime is still open.

S1, S6, S10, S14 not started; S16 has the limited local-retain evidence above.

---

## TIA §13 — Versioning and change management
*Binds Core §13.* Framework and module libraries are versioned independently, as
on TC3; the generator version, family profile and TIA/firmware pins are recorded
in every generated header and in the evidence of every gate run.

## TIA §14 — Cybersecurity governance
*Binds Core §14.* Zone/conduit: the CPU in a control zone, the gateway host on a
conduit over HTTPS with a pinned certificate and a least-privilege web user (OPC UA
Sign&Encrypt where that projection is used); PG/PC communication over TLS (S7-1200
V4.7 default); PUT/GET off; the web server on for the Web API only (HTTPS only
where the family offers the switch), no anonymous rights; protection level
and passwords per site plan; Openness hosts are engineering workstations, never
operator stations. Secrets never appear in a plan file, a command line or an
evidence record: the driver takes only the *name* of an environment variable
(`--password-env`, `--plc-password-env`; the confidential-data password is
`FRAKTAL_TIA_MASTER_SECRET`), so its logged argument lists hold no secret.

**Measured V20 / V4.7 defaults and what a deployment does with them:**

| Setting | V20 default for a new 1214C V4.7 | Deployment | Bench (2026-10-08) |
|---|---|---|---|
| Protection of confidential PLC configuration data | enabled, **no password** — refuses to compile | password set (`master-secret --mode protect`), kept in the site secret store | off (`none`) — declared bench-only |
| Access control | user management (UMAC); needs a user with the Full-access runtime right | UMAC users and roles per site plan | `Disabled` (classic access levels, full access) — declared bench-only |
| PG/PC and HMI communication | **secure only** (TLS), certificate held by the project | keep secure only; station project backed up with the workstation | secure only, kept |
| PUT/GET | off | off | off (not reachable through Openness on S7-1200) |
| Web server | off | on, project certificate kept, one gateway user with read/modify-tag rights (UMAC on S7-1200 V4.7) | on since 2026-10-08: project certificate pinned, port 80 closed / 443 open, `fraktal` = `WebReadTags|WebWriteTags` only; anonymous has the access levels but no web right (S1W) |
| Access control for web users (S7-1200 V4.7) | `EnabledWithAccessControl` (UMAC) | `EnabledWithAccessControlViaAccessLevel` + full-access password + UMAC users/roles per site plan | `…ViaAccessLevel`, anonymous = `PLCAdministrator` ("full access … testing only" warning), one user `fraktal`, password DPAPI-protected on the workstation; the download lowering protection was accepted explicitly — **bench only** |

**Trust on first use is a recovery act, not a workflow.** A CPU whose certificate
the project does not hold is accepted only by an explicit `--trust-plc <PLC>`
decision, logged with the verification text; normal builds reuse the station project
and verify without any trust decision (TIA §2.5, §5.4).

---

## TIA Annex A — What this binding does not claim (initial)

- **Power control and the §9.8 safety/control-power profile** (owner scope decision;
  no F-CPU on the bench).
- **Complete runtime integration of the optional Ladder examples** (TIA §1/§3.5).
- **S7-GRAPH on S7-1200** (not supported by the platform).
- On S7-1200, until S3/S16 measure otherwise: the Line profile (Core §3.8e, §8.5.2),
  parameter sets beyond a declared small capacity, card-file persistence, the
  full-depth history/alarm rings, the step-profiler Pareto, and controller health
  metrics without a supplying instruction — each published as a declared
  exclusion, never as a standing fault.
- S7-1200 G2 and S7-1500 R/H families.

## TIA Annex B — Primary platform references and evidence rule

- TIA Portal V20 information system (en-US), packages *Data types*, *GRAPH (S7-1500)*,
  *Declaring named value data types (S7-1500)*, *TIA Portal Openness* — indexed in the
  engineering knowledge base (`SiemensAgent/siemens-kb/tia-v20-help`).
- Siemens data sheet `6ES7214-1AG40-0XB0` (firmware V4.7, 2026-09-28).
- Siemens entry 109755846, *TIA Portal OPC UA system limits for the S7-1500/S7-1200
  CPUs*, V1.0 02/2024.
- Siemens entry 109977246, *Web server* function manual 11/2025 (A5E53797648-AB):
  Web API methods, rights and error codes (written for S7-1500 and S7-1200 G2; its
  applicability to S7-1200 G1 V4.7 is what S1W measures).
- TIA Portal Openness V20 API (`PublicAPI\V20\Siemens.Engineering.xml`, schemas
  `SW.PlcBlocks.*`).

A vendor document is the authority for what a platform *claims*; only a dated
evidence record on a named controller is the authority for what this binding
*claims*.

## TIA Annex C — Core coverage crosswalk (initial)

| Core | Fraktal/TIA mechanism | Clause | Status |
|---|---|---|---|
| §2.2 single lifecycle | `FRK_Begin`/`FRK_End` + generated frame + T-FRAME | §3.1, §3.14 | design; S2 |
| §3.2 capabilities | `FRK_Registry` indices + capability bits | §3.2 | design; S2 |
| §3.3 containment | generator + T-TIER | §3.1 | design |
| §3.8/§3.8b data, persistence | DInt enums, family widths, load-DB/card media | §3.8 | S12, S16 |
| §3.10 self-description | Web API (default) / OPC UA (optional), root instance DB, attributes, mailbox | §3.10 | S1W, S7, S9 |
| §3.11 wiring | composition FB, first-scan setup | §3.11 | S2 |
| §3.14 extensions | `Core.Ev` flags, deferred ModeExit | §3.14 | S2 |
| §5.5/§6.8 languages | SCL + S7-GRAPH (1500), optional unwired LD examples | §3.5 | S11; example compile/readback gate |
| §5.7 testing | `FRK_Test*` + host runner + harvest | §5.7 | S5 |
| §7.5 gates | user constants, generated engineering image | §7 | S12 |
| §8.11/§8.12 timing, health | `FRK_Clock` from `RUNTIME`, declared exclusions | §8 | S12, S3 |
| §9 safety | STEP 7 Safety / PROFIsafe, read-only | §9 | not claimed |
| §10.5 fieldbus diagnostics | `DeviceStates`/`Get_Diag` + publisher | §10 | S3 |
| §11 connectivity | gateway `WebApiSessionClient`; S7 OPC UA server optional | §11 | S1W, S8 (S1) |

*End of Fraktal/TIA — Part IV (draft). Core: `Fraktal_Core_Part_I.md`.*

### Measured extension, 2026-10-12: wired GRAPH/ST demo and decisions

Generator0.9 supplies FB_GRAPH_PressDemoAuto/Home and ST permissives in the owning
Unit. AUTO has the TC3 chart's nineteen steps, two recovery choices, backward
jumps and separate concurrent contexts. Native alternative/simultaneous branches
and comparison wiring are read back after compilation. ST/LD preserve the sixteen
main process steps; three GRAPH-only rows express the demonstration fork/join.
The intended N200 failure condition is JUMP1; the archived TC3 chart currently
serializes ADVANCE there. The TC3 source is preserved.

Core6.11 decisions use a private pool sized by actual roots, readonly root mirrors,
full-value idempotence, a single raising owner, offered defaults, and automatic
withdrawal driven by the generated Unit frame. Only the root mailbox may answer;
START_STOP access and the live Unit permit are checked. Nested modules have no
separate decision string allocation. This bounded prototype does not claim the
complete Core3.13 frontier, every option-specific policy or durable audit retention.

The wired demo is compiled offline. Physical I/O mapping and process acceptance
are pending. The separate two-root simulator bench qualifies the decision service
and existing state/config/access behavior. Current evidence is
[GRAPH recovery and decisions](Siemens/Evidence/TIA_GRAPH_RECOVERY_DECISIONS_2026-10-12.md).


### Measured extension, 2026-10-12: named station/model config sets

Generator 0.10 accepts an optional config_sets capacity bounded by Core
MAX_CONFIG_SETS. The LOCAL_RETAIN adapter allocates catalogs, record storage and
private import/export work per deployed root, sized by consumed capabilities and
Core MAX_SET_RECORDS. Typed walks reuse the same capability definitions and scalar
parser as ordinary config writes. Complete station/model loads validate and stage
before publishing; model loads also use the shared CHANGEOVER release and publish
ModelId after commit. Unknown, missing, duplicate, stale, foreign or invalid
records refuse the complete load with LastRejectScope/Key. Applied/refused loads
raise Core configuration events rather than adopting untrusted input as a device
fault. Children schedule no set services or publish separate set catalogs.

The existing generic HMI request kinds implement save/list/load/delete and JSON
lines export/import. Published answers are readonly and fetched on demand. The
Core JSON codec supplies the line bound; imports join bounded mailbox pieces and
strictly validate object shape and every field before replacing a saved set.
Restart, session generation and intervening requests discard transfer state.
The binding declares its CPU timestamps unsynchronized. Current-value export,
runtime model creation, line config sets and file/database media are unavailable.

Native simulator qualification and the compiled offline press application are
recorded in [config-set evidence](Siemens/Evidence/TIA_CONFIG_SETS_2026-10-12.md).
The press declaration opts into four station config slots and retains its wired
GRAPH/ST composition. Physical process qualification and full-download retention
boundaries remain separate gates.

### Measured extension, 2026-10-12: private access retention

Generator 0.11 adds a reference-1500 LOCAL_RETAIN prototype for the salted local
user table and per-root access policy. This is the currently qualified adapter;
the load-memory document binding described above remains an S16 implementation
gate. Every table member and work buffer is excluded from the external symbol
surface. Native export confirms Retain on the stored records and NonRetain on
root sessions; live probes verify private reads and direct policy writes refuse.
Core salted hash/work-factor authorities and the public ST_AccessPolicy contract
are unchanged. Binding-local schema/CRC images encode fields canonically rather
than copying optimized-DB padding or the TwinCAT access-image layout.

Restore validates each complete root policy and the complete provider table.
Corrupt, duplicate, out-of-range or checksum-invalid users make the provider
unavailable; commissioned images with cleared headers are not reseeded. A damaged
policy never restores the open default: it restricts the affected root to ADMIN
and blocks Start until explicit ENGINEER acknowledgement, preserving that fallback
for later gated edits. Loss uses the existing alarm and ConfigPersist surfaces.
Accepted action-threshold and timeout edits are retained before acknowledgement.
Trusted hashed registration changes the provider generation; managers revoke old
sessions and fail a pending attempt from the prior table. Sessions, transported
secrets, recipe documents and saved sets contain no retained credential grants.

The two-root simulator qualification preserves owner registration, virtual
adapter mappings and the keeper through STOP/RUN and power cycles. The wired press
is separately compiled offline. Other media/providers, data-class policy forms,
full-download/changed-layout retention and durable alarm storage are not established
by [this evidence](Siemens/Evidence/TIA_ACCESS_PERSISTENCE_2026-10-12.md).

### Measured extension, 2026-10-12: optional closed-event history

Generator 0.12 adds a reference-1500 LOCAL_RETAIN profile selected by canonical
Unit scopes in the composition declaration. Only selected Units allocate private
Core-sized closed-ring images. The owning generated frame restores before new
mailbox/access events and the shared close path retains records before callbacks;
projects schedule no extra service. Canonical encoding derives all ST_AlarmEvent
fields and shares Core-derived CRC primitives with the access consumer.

Restore validates the complete image before publication. Schema, identity, cursor,
event-shape and checksum failure discard the whole affected history and persist
Truncated as incomplete-history indication. Peer histories remain independent.
Ring order, overflow, Unicode, timestamps, qualities and monotonic closed-event
durations survive the qualified simulator restarts; restored events do not replay
sink callbacks. This profile deliberately stores closed events only. Active and
WAIT_RESET alarm/control state retain the existing volatile startup behavior;
active-latch recovery, external historian delivery, other media and full-download
or changed-layout loss boundaries are not established by this slice. See
[the dated history evidence](Siemens/Evidence/TIA_ALARM_HISTORY_2026-10-12.md).

### Measured extension, 2026-10-12: selected manual-reset alarm recovery

Generator 0.13 accepts alarm_recovery.scopes as a subset of selected closed-history
Units. Private LOCAL_RETAIN active images preserve ACTIVE and WAIT_RESET manual
latches; commands, step/control state, outputs and sessions remain volatile. The
composition prepares conservative descendant readiness before any root runs, and
owning frames restore before mailbox command acceptance. Captured faults reconcile
against fresh module status; a gone fault waits for deliberate reset. A live explicit
owner can reclaim its restored occurrence once without a duplicate come callback.

Complete schema/identity/header/event/timing/journal validation precedes publication.
Invalid active state fails closed with a HIGH/SYSTEM MANUAL_RESET loss occurrence;
one gated operator reset closes its retained latch without clearing a live condition.
The binding-owned prototype extension reason is 11001, declared/rationalized in
Framework/Core/alarm_recovery.json, independently of released Core enum layout.
The existing readonly alarm surface and localized description expose the cause.

Duration sums controller-running observations across restart and excludes an
unobserved outage; WAIT_RESET freezes duration. No saved monotonic epoch or
unsynchronized wall-clock subtraction is restored. A private close journal commits
an authorized closed occurrence once across the qualified before/after-history
interruption points; recovery does not replay sink callbacks. File/card/external
media, durable sink acknowledgement, arbitrary physical torn-write/power-loss and
full-download/changed-layout behavior remain separate gates. See
[dated recovery evidence](Siemens/Evidence/TIA_ALARM_RECOVERY_2026-10-12.md).


### Measured extension, 2026-10-12: selected event delivery

Generator 0.14 supplies an optional retained FIFO sink adapter for explicitly
selected history-consuming Units. Only selected consumers allocate private images
and independently validated identity anchors; readonly snapshots expose one head
per consumer. Shared alarm services capture come and close records, with close
capture preceding the recovery journal/history append. Projects add no scheduling
call. A bounded queue preserves old records on overflow and declares discarded
new records. Corrupt storage is rejected whole and annunciated in the standard
alarm log; explicit engineering discard advances a valid identity epoch, while
an invalid anchor cannot be reset into reused IDs.

Internal operation identities ACK_EVENT_DELIVERY and DISCARD_LOST_EVENT_DELIVERY are
binding-owned additions declared in Framework/Core/event_delivery.json. They use
a dedicated adapter-owned metadata commit mailbox without changing released Core/HMI enums or
record layout. Receipt authority is at least ENGINEER and the configured DATA_WRITE
level; only an exact scoped head token/checksum is accepted. Receipt audits remain
local and are excluded from their own outbox to prevent a feedback loop. Automated
receipts do not refresh an operator session's idle timer.

The full-table restart gate also exposed an interrupted active-alarm elapsed/CRC
checkpoint. Private recovery image schema 2 writes an inactive timing bank and
publishes its selector last; startup validates the committed pair. Schema 1 is
rejected as a changed layout. Twelve consecutive STOP/RUN cycles restored all
sixteen manual events. This correction does not establish changed-layout or
full-download retention.

The reference SQLite adapter validates complete Core records, commits before
receipt, deduplicates the stable token, and refuses conflicting durable records.
A reconnect reads the current head rather than replaying an old request sequence.
It currently consumes the existing root session; independent service authentication
and unattended deployment remain PROVISIONAL. Bounded delivery, simulated restart
and the qualified close interruptions do not establish arbitrary physical torn
writes, changed-layout/full-download boundaries or unlimited historian retention.
See [dated evidence](Siemens/Evidence/TIA_EVENT_DELIVERY_2026-10-12.md).

### Measured S16 mechanism, 2026-10-13: load-memory byte transfers

Native READ_DBL/WRIT_DBL pass on the reference simulated CPU1516 with TIA V20
and PLCSIM Advanced V7. Optimized Byte arrays transfer across asynchronous calls;
the source stays stable while BUSY, and completion precedes acknowledgement.
Ordinary banks keep independent current/load values. UNLINKED banks retain
Optimized layout and exist only in load memory, verified through native exports,
properties and runtime reads. Both banks survive STOP/RUN and simulated power
cycles with exact complete-buffer CRCs. Private payload reads and readonly
diagnostic writes are refused through the Web API.

This closes the measured instruction leg of S16 at this scope. The keyed document
medium, tickets, two-slot generations/content validation, bounded flash writes
and consumer restore/durability integration remain PROVISIONAL. Config, saved
sets, users and policy keep the qualified LOCAL_RETAIN profiles. Physical flash
endurance, arbitrary torn writes and full-download/changed-layout preservation
remain separate gates. See [S16 evidence](Siemens/Evidence/TIA_LOAD_MEMORY_2026-10-13.md).


### Measured document adapter, 2026-10-13: generator 0.15

The optional LOAD_DB declaration now connects registered station/model configuration, named-set slots, root policy and the shared private user table to consumed-size keyed documents. The unselected profile retains its existing implementation and allocates no medium. The released Core enum/layout is unchanged: controller-local retention remains its published store category, with readonly adapter metadata identifying LOAD_DB. This is the draft Siemens binding's adapter classification, not an added Core ordinal.

Two optimized UNLINKED banks per key carry a versioned header, generation, key CRC, length and document CRC. Retained two-bank confirmation anchors detect newest-copy loss. A bounded FIFO and per-document buffer leases serialize asynchronous READ_DBL/WRIT_DBL operations; consumer polling advances one stage per scan and bounds CRC work. The declared global minimum write interval also applies after startup. Successful live writes precede durability; native read-back validation and anchor commit precede clearing Pending. Named-set apply uses the same configuration dirty hook.

Typed consumers validate whole candidates before applying them, with configuration destinations reserved first. Users are validated before installation. Unreadable boot keeps a restore barrier and retries while device abort/cyclic hooks withdraw commands, sessions and outputs. Content/anchor rejection invokes the existing owning fallback and repair policy; users fail closed, policies restrict access, and config replacement requires ENGINEER acknowledgement. Historical RestoreLost plus RestoreAcknowledged retains the existing contract meaning.

The reference fixture and separate wired press compile warning-clean. Native corruption, retry, privacy, STOP/RUN and simulated power evidence is recorded in [the document-medium report](Siemens/Evidence/TIA_PERSIST_MEDIUM_2026-10-13.md). This measurement does not qualify physical flash endurance, arbitrary torn writes, full-download/changed-layout preservation, card/external adapters, S7-1200 fit or physical press behavior.

### Measured sequence view, 2026-10-13: generator 0.16

Selected Units now publish the unchanged Core 3.13 definitions/cursors/history/annotation contract. Definitions travel through the config manifest; shared sequence helpers record visits and notes, and owning frames supply scan/mode boundaries and readonly mirrors. A private consumed-size pool removes the native GRAPH/root-FB compile dependency cycle. The press sub-chain uses one declared display-number offset to avoid main/parallel row collisions. Released Core enums/layout are unchanged.

The native synthetic fixture passes 122 checks and the separate wired press compiles warning-clean with matching GRAPH/LAD readback. Native HMI hydration/rendering, full diagnostic walks/profiling and combined LOAD_DB boot publication remain later gates. See [dated scope/evidence](Siemens/Evidence/TIA_SEQUENCE_VIEW_2026-10-13.md).

### Measured sequence diagnostics, 2026-10-14: generator 0.18

Selected sequence Units now use private consumed-module snapshots and a scoped
first-out walk. Owning frames capture after cyclic work and withdraw during
quiescence. Shared command helpers resolve target identity, default guards use
the longest awaited timeout, and main-line expiry publishes LOW Pending without
faulting. HELD disarms generic stalls; unhandled faults preserve the originating
diagnostic and mark the responsible row. Handled failures retain their recovery
branch. Generic leases abort released busy commands. Core layouts/ordinals are
unchanged; applications add no scheduling call.

Native diagnostic/restore/view gates and the separate wired press compile/readback
are recorded in [the diagnostic report](Siemens/Evidence/TIA_SEQUENCE_DIAGNOSTICS_2026-10-14.md).
Profiling, complete sequence freeze/resume policy, remaining provider/line config
and module/deployment scope remain open. Cold VM loss of the test-user document
was detected fail-closed and repaired through trusted bench provisioning; it
does not qualify abrupt-loss retention.

### Measured extension, 2026-10-15: typed configuration and current exports

Generator0.21 resolves native REAL/LREAL, bounded smaller integers, Core enums
and explicit constant-index array elements from owning declarations. The same
typed validator protects live writes, restore, recipe prepare and imported sets;
model-region completeness includes every array element. Core enum domains use
the existing manifest choice metadata. Released Core records/ordinals and the
saved-document wire format are unchanged.

Current station/model exports use EXPORT_CURRENT_CONFIG and existing ordered
EXPORT_CONFIG_SET continuations. A complete immutable snapshot reuses consumed
workspace without allocating a saved slot, including when the store is full.
Session generation, client token, document name and exact next line bind the
cursor; refusal/intervening operations invalidate it, and every line rechecks
read authorization. The generic HMI consumes the existing feature/protocol.
MAIN gains no call. See [qualification](Siemens/Evidence/TIA_CONFIG_TYPES_2026-10-15.md)
for native, source/readback, HMI and remaining provider/Line/deployment scope.

The measured numeric codec uses bounded integer rationals and direct nearest/even
binary rounding. Decimal output has17 significant digits and an exact reverse
check; integer scratch stays in FC TEMP storage. Subnormal values are refused
as underflow under the S7-1500 arithmetic profile. The REAL Web API leaf carries
seven significant decimal digits on this bench; typed configuration text is the
precision witness used by the generic editor/export contract. Native comparisons
and source limits are recorded in the qualification above.

### TIA candidate contract baseline, version 1

The implemented S7-1500 subset is frozen as a **draft candidate ABI**, not a
released reference binding. The [machine baseline](../FraktalCore/PLC/Siemens/Contracts/TIA_FROZEN_CONTRACTS_V1.json)
is derived from the owning Core DUTs, binding and native HMI adapter. Run
`python tools/check_tia_contracts.py` before changing them. The gate compares
field order, logical/native types, widths, initializers, publication flags,
referenced enum ordinals and capacities, the consumed-size sequence table
shape, and the adapter's datatype projection. Any change to this V1 subset,
including an addition, requires explicit versioned contract review; an ordinary
check never rewrites the baseline. A subsequent baseline shall preserve V1.

`--generated <package>` and `--native <Openness-export-directory>` additionally
require every frozen record and compare the complete ordered native interfaces,
including ExternalAccessible/ExternalVisible/ExternalWritable. These options
apply to a full-profile bench, not to a station that omits optional features.
Mailbox commit/acknowledgement behavior, codecs and session recovery retain
their executable tests; layout checks alone do not prove behavior.

R3 remains **OPEN**: this subset does not resolve provisional read coherence,
clock quality, optional OPC UA, S7-1200 layouts or the unimplemented facets.
The frozen records describe implemented surface and impose no extra allocation
on a station; sequence tables retain their declaration-derived dimensions.

<!-- TIA-CONTRACTS-V1 sha256:65ea0e812b82586de6f27012880a9d0200f4ed283dee39a8f420a7dead101524 -->
