# Fraktal Core — Modular Automation Architecture (Part I)
*Unified PLC Programming Standard · **Part I: platform-neutral normative core***

**Status:** Draft · Part I of III (Part II: the TwinCAT 3 binding, **Fraktal/TC3**; Part III: the Allen-Bradley Logix binding, **Fraktal/AB**, draft/R0-complete/spike-ready)
**Platform:** none — this Part is platform-neutral. Platform-specific clauses live in binding Parts (Part II: TwinCAT 3; Part III: Allen-Bradley Logix).
**Grounded in:** ISA-88 / IEC 61512 (physical & procedural model), PLCopen (command-handshake vocabulary, motion & safety function blocks), ISA-TR88.00.02 PackML / OPC 30050 (optional overlay), ISA-95 / IEC 62264 (MES integration), ISA-18.2 / IEC 62682 (alarm management), IEC 62443 (cybersecurity), and OPC UA / IEC 62541 companion models — reconciled into a single recursive-module architecture.

> Normative language: **shall/must** = requirement · **should** = recommendation · **may** = permitted · **can** = possible.
> This document is **Part I (Core)**: Foreword and environment requirements (§1–2), the architecture and coding core (§3–8), and safety principles, I/O abstraction & motion model, connectivity mappings, worked-example index, change management, and cybersecurity (§9–14). Platform mechanics are cited as **TC3 §x.y** (`Fraktal_TC3_Part_II.md`) or **AB §x.y** (`Fraktal_AB_Part_III.md`); Core section numbering is preserved across bindings where applicable.

---

## 1. Foreword

### 1.1 Project description & objectives

**Description.** This standard defines a single, unified way to write equipment software for the production line — defined platform-neutrally and delivered first as its **TwinCAT 3 binding** (O8). It synthesises established industry practice — the ISA-88 (IEC 61512) physical/procedural architecture with disciplined alarm (ISA-18.2), safety, and naming rules, and a proven object/handler framework of coding conventions — into one recursive three-tier module model (`FB_Unit` / `FB_EquipmentModule` / `FB_ControlModule`). Every module shares one data contract, one PLCopen command handshake, and one diagnostic model, and the whole station describes itself through the transport-neutral **Fraktal Self-Description Service** (§3.10/§11) so a single generic Flutter HMI can render and navigate it without per-station screen building.

**Concept.** The standard is organised around one intention: bring a machine into service with **as little application programming as possible**, so that what remains to be written is the part that is genuinely specific to that machine.

- **Equipment is composed, not written.** A station is assembled from reusable module *types*, each of which ships with its own tests, its own reason-code band, and its own published contract. A type is declared and wired once (§3.11); it is then finished.
- **Everything common is reused, not repeated.** The command handshake (§6.1), mode and state machines (§6.2), first-out diagnosis (§6.9), the alarm model (§8), recipe load and migration (§3.8), traceability (§3.16), and the published data contract (§3.12) are defined **once at the level that owns them**. A concrete type supplies its device logic and declared lifecycle extensions, and nothing else (§2.2, §3.14). A binding may enforce that reuse through inheritance or through generated composition, but a project never re-implements the lifecycle.
- **The operator interface is discovered, not engineered — and not generated.** Because every module publishes the same self-describing contract (§3.10), a generic HMI walks the live forest at run time and renders the tree, its commands, its alarms and its flow charts (§3.13). Adding a module makes it appear. A binding may generate the controller-side manifest or exposure metadata from the same authoritative declaration, but there is no separately hand-maintained per-station HMI artifact to regenerate, redeploy, or keep synchronised when the machine changes.
- **What the application author writes is the step sequence** — the process itself — in whichever of ST, SFC or Ladder suits the author and the site (§5.5, §6.8), all three implementing the same sequence contract through the binding's proved execution form.

The effort model that follows from this is stated in O1 and made normative by the trimming rule below: standardisation is paid **once per reusable module type**, and once per framework mechanism — never once per step, per station, or per screen.

**Technology baseline.** The Core assumes a deterministic cyclic PLC environment capable of the bounded records and state machines defined here, a transport-neutral Fraktal Self-Description Service (§3.10, §11), a generic operator HMI that auto-discovers the module forest (§3.13), and pluggable recipe/type transports — local, OPC UA, socket (JSON/XML), REST, or a binding-defined equivalent (§3.8). It does **not** require IEC object-oriented extensions or a particular connectivity transport. Each **binding** declares its concrete technology baseline — toolchain, language mechanisms, fieldbus, safety system, self-description transport, and optional industry projections — in its own Part (**TC3 §1**, **AB §1**).

**Deliverables.** This standard (§1–13), the worked-example annex set A–I (§12) exercising every contract end-to-end, and a two-page **quick-start** ("your first module": scaffold from the binding's §2.2 lifecycle form, wire, test to the §5.7 checklist) with the Annex C chain also rendered in SFC (§6.8). The original core trio: three worked-example annexes that exercise every contract end-to-end and serve as reference implementations: a Control Module (Annex A — separator/stopper), an Equipment Module (Annex B — dual clamp with parent-child rollup), and a Unit (Annex C — station with a continuous mode chain, mode cascade, and the cross-tier stall diagnostic). Each binding supplies the framework artifacts those examples assume (§2.2).

**Objectives** (in priority order):

1. **Low development *and maintenance* effort.** Application logic stays lean — issue a command, wait for `Done` — with no per-step boilerplate. Standardisation is paid once per reusable module *type*, not once per step (§6.9); and a change to a shared contract, diagnostic, or transport is made **once at the owning level** and reused everywhere through the binding's enforced mechanism, so the cost of evolving a fleet stays bounded as it grows rather than scaling with the number of modules or stations.
2. **Easy to learn from any background.** SFC is the default, but sequences, interlocks, and conditions may also be written in ST or Ladder (§5.5); names follow the widely-known PLCopen convention (§6.1) so the interface feels native to programmers from any platform.
3. **Diagnosable by construction.** When a sequence stalls, the operator always gets a precise root cause — *"Step N stalled → awaiting Module.Command → reason"* — produced automatically from the module contract, with no hand-coded per-step conditions (§6.9, §8).
4. **Reusable, recursive, and scalable.** One module model scales structurally from a single device to the whole station; recurring assemblies are packaged as types and dropped in anywhere with a fresh mapping (§3.11). Scalability is also a *runtime and deployment* property: a station's published surface, discovery cost, and connectivity traffic **should** stay proportional to the data actually consumed, so a large forest does not degrade the HMI, MES, or server — data that is static, historical, or view-specific may be served on a lower cadence or on demand rather than continuously, without changing the module contract (§3.10, §11).
5. **Flexible data & connectivity.** Recipe/type data may be local or fetched over OPC UA, socket (JSON/XML), REST, or another binding-defined provider behind one logical provider contract (§3.8); the HMI and MES consume the Fraktal Self-Description Service generically through the selected binding transport (§3.10, §11).
6. **Simulatable.** Every module runs unchanged against simulated or real I/O through the HAL, enabling virtual commissioning before hardware exists (§2.6, §10).
7. **Safe.** Safety lives in the certified safety system; application code consumes safety state read-only and never bypasses it (§9).
8. **Portable.** The normative model — tiers, contracts, state machines, diagnostics, routing — is platform-neutral; each PLC platform is served by a *binding* that maps the model onto that platform's language extensions and services. TwinCAT 3 is the first binding and Allen-Bradley Logix the draft second binding; platform clauses are tagged **[TC3]** or **[AB]**. The standard is named **Fraktal** — one contract, self-similar at every tier — with the platform-neutral core designated **Fraktal Core** and each binding **Fraktal/⟨platform⟩** (**Fraktal/TC3**, **Fraktal/AB**; future: Fraktal/TIA). Conformance claims compose as *"Fraktal Core + Fraktal/⟨binding⟩ (+ binding-qualified profiles)"* (for example `Fraktal Core + Fraktal/TC3 + Robot` or `Fraktal Core + Fraktal/AB`). Fraktal is published as an **open-source project** in the `MrFrakt/Fraktal` monorepo.
9. **Good coding and engineering practice.** The preceding objectives are upheld through disciplined coding and engineering practice, which the standard treats as a first-class goal rather than a matter of individual style. Every fact — a contract member, a reason code, a diagnostic, a piece of configuration — has **one authoritative source** and is derived, never duplicated (§4.8, §8.8, §3.8); behaviour is written **once at the level that owns it** and reused through a binding mechanism that prevents project duplication, so concrete types add device logic only (§2.2, §3.14). Public capability contracts expose the **minimum surface** needed and no more (§3.2, §3.13); changes to a released type are **additive and versioned**, never silently breaking a consumer or a stored recipe (§1.5, §3.8). Machine-verifiable rules — naming, contract usage, lifecycle ordering, step/condition records, per-type tests — are enforced by a **CI/lint gate on every commit** (§1.5, §5.5, §6.8) so conformance is continuous, not a review-time hope. New code **should** follow the idioms and structure of the code around it, keeping the codebase legible to any engineer from any binding. This objective is cross-cutting: it names explicitly the practices the other objectives assume, so that scalability and maintainability survive as the standard and its fleets grow.
10. **Industrial-grade robustness.** The framework is built to the reliability expected of production equipment software, not of a demonstrator. Every command, recipe payload, and external input is **validated before use**, and every behaviour-selection path has a defined fail-safe fallback — never a silent default or a stall (§5.6); bounded, statically-sized structures (fixed rings, no run-time allocation on the scan) keep timing and memory **deterministic** (§8.3, §8.11); faults **fail closed** and are never masked, and a lost transport or connection **queues nothing** and resumes cleanly rather than replaying stale actions (§7.8, §11, §14). The reference implementations are held to the same bar — warning-clean builds, green per-type tests against the simulated HAL before release (§1.5, §5.7), and honest status reporting that distinguishes proven behaviour from deferred work. Robustness is a **shall** wherever safety, data integrity, or command acceptance is at stake, so a Fraktal station behaves predictably under load, fault, and recovery in a real plant.

**O1 in practice — the trimming rule.** O1 is not satisfied by *documenting* repeated project work; it is satisfied by *removing* it. Whenever the same wiring, latch, reset, or per-scan call has to be written in more than one project sequence, module, or Unit, that repetition **shall** be treated as a framework defect and absorbed into the binding's owning framework/generator mechanism — even when absorbing it makes that mechanism materially more complex. The cost is paid once by the standard's implementers; the saving recurs in every station, forever. Two consequences follow, and both are normative:

- **A project shall never be required to remember a call for correctness.** If forgetting a call yields a wrong or intermittent result — a stale transition result, a latch that never re-arms, an unreset sub-chain — the call belongs in the framework, driven from a path the application already takes (attach, cyclic, step change). An obligation a project can forget is a defect the framework chose not to fix.
- **Repeated glue is measured, not judged.** "More than once" is the threshold. The reference implementation absorbed the composite sub-chain pattern after it appeared four times at eight lines each, and the per-scan chain reset before it could appear even once in a project.

This rule is what keeps the effort model honest: standardisation is paid once per reusable module *type* (and once per framework mechanism), never once per station.

**Non-goals.** The standard deliberately does **not** mandate PackML (it is an optional overlay, §6.6), does **not** tightly standardise step bodies the way heavily templated step-body standards do (that verbosity, slow to write and error-prone, is precisely what this standard sets out to avoid), and does **not** lock sequence authoring to a single language.

**Platform-tagging convention (O8).** Binding-specific clauses carry their binding tag and live in that binding Part: **[TC3]** in Part II (`Fraktal_TC3_Part_II.md`), **[AB]** in Part III (`Fraktal_AB_Part_III.md`). Compiler pragmas/attributes, `REF=`/`__QUERYINTERFACE`, `FB_init` ordering, TF6100/TwinSAFE services, Logix AOI/UDT/L5X mechanics, CIP access, and gateway mechanics therefore do not become Core requirements. Where a binding fragment is inseparable from an otherwise-neutral Core example, it may remain here only with its tag and a pointer to the owning binding clause. Untagged normative text is platform-neutral Core; another platform implements its own binding Part without changing Core. All **new** platform-specific normative text **shall** land in its binding Part.

### 1.2 Purpose & scope

This Part defines, platform-neutrally, how PLC application software is structured, named, sequenced, interlocked, alarmed, and exposed for equipment delivered into the production line; the platform is fixed by the binding in use (Part II — TwinCAT 3, TC3 §1; Part III — Allen-Bradley Logix, AB §1). It applies to all equipment suppliers and to in-house controls work for the site. A project-specific specification may add to this standard and, only where explicitly agreed in writing, supersede a part of it.

### 1.3 Audience

Equipment suppliers' PLC programmers, controls engineers, and commissioning and maintenance personnel. Readers are assumed competent in IEC 61131-3 and in the selected binding platform (for example TwinCAT 3 for Fraktal/TC3 or Studio 5000 Logix Designer for Fraktal/AB).

### 1.4 Relationship to source standards

This standard is grounded in publicly available standards, not a proprietary lineage: the **ISA-88 / IEC 61512** physical and procedural model gives the tier architecture (§3.1); **PLCopen** supplies the command-handshake vocabulary (§6.1) and the motion (§10.6) and safety (§9.7) function-block sets; **ISA-TR88.00.02 (PackML)** with its OPC UA companion **OPC 30050** is supported as an optional overlay (§6.6, §11.7); **ISA-95 / IEC 62264** shapes MES integration (§11.6); **ISA-18.2 / IEC 62682** govern alarm rationalization (§8.9–§8.10); **IEC 62443** frames cybersecurity (§14); and **OPC UA (IEC 62541)** with its companion models — Machinery (OPC 40001), PackML (OPC 30050), Energy (OPC 34100), AAS/MTP, FX — supplies one binding transport and several optional industry projections (§3.10, §11). Where common industry practices diverge, the resolution is recorded in the relevant section — variable prefixing (§4.4), flow control and the lean-vs-diagnosable trade-off (§6), PackML made optional (§6.6), and the language policy (§5.5).


![Figure 1](diagrams/synthesis.png)

*Figure 1 — The standard synthesises ISA-88 (IEC 61512) architecture discipline and object/handler framework practice into one recursive-module standard.*

### 1.5 Conformance

- A project conforms when every **shall** requirement is met. **Should** items are strongly recommended; departures **should** be justified in the project documentation.
- Any deviation from a **shall** requirement **shall** be approved in writing by the site's controls engineering before deployment, and logged (§13).
- A CI/lint gate (§5.5, §6.8) **shall** check the machine-verifiable requirements — naming, step records, condition records, and contract usage — on every commit.
- Each reusable module **type shall** ship an automated test suite (§5.7) that runs in CI against simulation and covers its handshake, first-out diagnostics, and interlocks; the suite **shall** be green before the type is released or changed.
- **Module-type versioning.** Released types follow semantic versioning: **major** = any change to the contract surface (commands, handshake members, `ParCfg` schema, reason codes, `SourcePath` semantics — anything a consumer or a stored recipe can observe); **minor** = additive members/commands with defaults preserving old behaviour; **patch** = internal fixes with no observable change. A major bump **shall** ship the §3.8 recipe migration for its `SchemaVersion` step, and consumers pin versions per §2.2/§5.4 — so "reusable library" is a compatibility promise, not a hope.
- **Binding-qualified projections.** Core behavior-profile conformance is transport-independent. A claim for a transport or companion-model projection (for example `Fraktal/TC3 + PackML/OPC UA`) is additionally qualified by the selected binding and may be made only when that binding maps and verifies the projection. Absence of an optional projection does not invalidate base Fraktal Core conformance.

### 1.6 Definitions & abbreviations

| Term | Meaning |
|------|---------|
| Unit (`FB_Unit`) | Recursive mode-owning module (the **ModeHandler** role, §3.1). A Unit with no parent is a **root Unit** (§3.1a); a program may have several, one per station/conveyor/sub-line, forming a **forest**. |
| Station | The independently controlled operational scope represented by one root Unit. |
| PLC / cell scope | One PLC program and Self-Description Service endpoint hosting the module forest: one or more peer stations/root Units plus shared system services. |
| Equipment Module / EM (`FB_EquipmentModule`) | Discrete-command module (the **CommandHandler** role, §3.1). |
| Control Module / CM (`FB_ControlModule`) | Hardware-bound leaf module (one HAL channel). |
| HAL | Hardware-Abstraction Layer between CM logic and the I/O driver; enables simulation. |
| Hardware Driver | Lowest layer that talks to physical I/O; carries the SIM toggle. |
| `PermIntlk` | Standard permissive/interlock container with per-condition description + reason code. |
| Recipe / Type data | Parameter set shaping module behaviour (`ParCfg`); source is pluggable (§3.8). |
| `ExecState` | Derived command/module state: `READY/BUSY/DONE/ERROR/ABORTED`. |
| `ParCfg`/`ParCmd`/`OutCmd`/`OutImm` | The four-structure object data contract (§3.12). |
| OEE / MES / HMI / SCADA | Overall-Equipment-Effectiveness / Manufacturing-Execution-System / Human-Machine-Interface / Supervisory-Control-And-Data-Acquisition. |
| Fraktal Self-Description Service | Transport-neutral live discovery, typed-value, quality/freshness, bounded-read, and acknowledged-mutation contract of §3.10/§11. |
| OPC UA | OPC Unified Architecture — a permitted binding transport and optional companion-model projection. Fraktal/TC3 uses TF6100 (TC3 §3.10/§11.1); Fraktal/AB defaults to EtherNet/IP plus the Fraktal gateway (AB §1/§11). |
| Safety system | The certified functional-safety platform of the binding (§9.1); Fraktal/TC3: TwinSAFE/FSoE (TC3 §1, TC3 §9). |
| SFC / LD / ST / FBD / CFC | IEC 61131-3 languages: Sequential Function Chart / Ladder / Structured Text / Function Block Diagram / Continuous Function Chart. |
| Capability study (Cmk/Cpk) | Repeated-cycle measurement run assessing machine/process capability; the `CAPABILITY` mode (§3.17). |
| Data carrier / RFID | Part-bound data tag read/written via `I_PartCarrier` (§3.16). |
| Heartbeat / link supervision | Periodic liveness check on an external device link, with a defined loss reaction (§3.15). |
| PackML / PackTags | OMAC machine-state model (ISA-TR88.00.02; OPC UA companion OPC 30050) and its Command/Status/Administration tag groups (§11.7). |
| ISA-95 / ISA-88 | IEC 62264 enterprise-control (MES) integration / IEC 61512 batch & procedural models (§11.6). |
| AAS / MTP | Asset Administration Shell (IEC 63278) / Module Type Package (VDI/VDE/NAMUR 2658, IEC 63280) — vendor-neutral module descriptions (§11.8). |
| UNS / MQTT / Sparkplug | Unified Namespace / lightweight broker protocol / its birth-death payload spec, for north-bound telemetry (§11.9). |
| PTP / NTP | IEEE 1588 Precision Time Protocol / Network Time Protocol — station clock-sync sources (§2.7). |
| PLCopen Motion / Safety | Standard `MC_*` motion and `SF_*` safety function-block sets (§10.6, §9.7). |
| IEC 62443 | Industrial-automation cybersecurity standard: zones/conduits and security levels SL 0–4 (§14). |
| ISA-18.2 / IEC 62682 | Alarm-management lifecycle & rationalization standards (§8.9–§8.10). |

## 2. Development & Runtime Environment (platform-neutral requirements)

> The toolchain-and-versions and project-and-solution-settings clauses are binding-level — see **TC3 §2.1/§2.4** and **AB §2.1/§2.4**. The requirements below are platform-neutral and bind every implementation regardless of platform. One neutral toolchain rule is retained here:

- The build **shall** be warning-clean before release; **shall**-level compiler/lint findings are treated as errors. Exact toolchain builds **shall** be pinned per project and recorded (mechanics per binding, TC3 §2.1 / AB §2.1).

### 2.2 Libraries

- System, framework, and vendor libraries **shall** be referenced by pinned version with their dependencies; local or relative library references are not permitted (§5.4). Reference/distribution mechanics are binding-owned (TC3 §2.2 / AB §2.2).
- The framework distribution — module contracts, capability surfaces, the step-chain mechanism, permissive/interlock records, alarm/diagnostic handlers, and Self-Description Service exposure — is versioned centrally. Projects consume a pinned release, never a copy.
- **Single lifecycle authority (O1).** The binding framework **shall** implement the §6.1 lifecycle **once**: Execute edge, state/output mapping, Execute-drop reset, `ErrorID`, abort routing, status publication, command timing, and recipe-transaction defaults. Its composite mechanism adds child registration, recursive recipe handling, and diagnostic rollup without assigning a tier; its tier forms add only Unit/EM/CM obligations, so a Unit never acquires Equipment-Module identity by implementation accident. A concrete type **shall** supply only its device/sequence dispatch and explicitly declared §3.14 extensions; it shall not re-implement lifecycle-owned behavior or write lifecycle-owned state directly.

  Every binding **shall** define one non-optional cyclic execution path with this order: reset a previously published command-terminal state when §6.1's Execute-drop rule permits it, then sample/accept a new command edge; run one-shot initialization and accepted-command-start extensions; run cyclic management and child/rollup work; route abort/error-abort handling; run concrete device or sequence dispatch only while BUSY; resolve HELD, timing, terminal outputs, diagnostics, and the published status mirror; then release any framework-owned one-shot request for the next scan. The exact placement of a documented tier-specific derivation may vary only when the binding proves identical observable Core behavior. The mechanism may be inheritance (TC3 §2.2/§3.14) or generated composition (AB §3.14), but it **shall** make the required calls/order machine-checkable and shall not leave a project author to remember correctness wiring. Rows T1/T4 and the shared T2/T6 mechanisms are proven once at this owning lifecycle implementation (§5.7); generated-composition bindings additionally prove that every concrete type includes it. Expanded annex forms remain pedagogical only.

### 2.3 Tasks & timing

- One primary cyclic PlcTask runs `MAIN` and the module tree (§4.2). Its cycle time and watchdog **shall** be sized for worst-case load with margin and recorded.
- Additional tasks (fast I/O, comms) require controls-engineering approval and **shall not** share state with the primary task except through documented, lock-free exchange.
- Blocking or long-running work — recipe fetch over OPC UA/REST/socket (§3.8), file or database access — **shall** run asynchronously and never stall the cyclic task.

### 2.5 Source control

- The project **shall** be held in text-diffable form under version control; binary-only storage is not acceptable. Storage forms are binding-owned ([TC3]: TC3 §2.5; [AB]: AB §2.5).
- One repository per solution/line as agreed; the pinned framework-library release is referenced rather than vendored where the tooling allows.
- Commits are gated by the CI/lint checks of §1.5.

### 2.6 Simulation

- Every Control Module **shall** be runnable against a simulated Hardware Driver (DI/DO/Motor SIM, §3.6), selected by configuration, with no change to module logic.
- Simulation supports both local PLC test and external virtual commissioning (e.g. Process Simulate). The same `ParCfg`, handshake, and diagnostic contracts apply in simulation and on real hardware, so a sequence validated in sim behaves identically on the line.

### 2.7 Time synchronization

Every timestamp the standard produces — the `ST_Diagnostic.Since` first-out time (§8.8), alarm queue entries (§8.3), traceability records (§3.16), and host events (§11.6) — is only as trustworthy as the controller clock behind it. A station **shall** therefore derive its clock from a synchronized source, not the free-running IPC clock.

- **PTP (IEEE 1588) is the primary source.** Where the network and devices support it, the station clock **shall** be disciplined by PTP — over the fieldbus's distributed-clock mechanism and over network PTP for the controller ([TC3] mechanics: TC3 §2.7). NTP **may** be used as a fallback where PTP is unavailable; the chosen source **shall** be documented per station.
- **One clock feeds all timestamps.** Diagnostic, alarm, traceability, and host-event timestamps **shall** read the synchronized clock so that PLC, HMI, historian, and MES share a single, comparable time base (this is the precondition that makes first-out ordering across tiers and across stations meaningful).
- **Loss of sync is a System alarm.** If the clock loses its sync source beyond a configured tolerance, the station **shall** raise a System-category alarm with `ReasonCode := E_Reason.TIME_SYNC_LOST` (§8.6, §8.8) and **shall** flag subsequently generated timestamps as unsynchronized, rather than silently emitting drifting times.

Clock confidence is published once as `ST_TimeQuality := {Available, Synchronized,
Source, OffsetUs, LastSyncAt, ObservedAt}`. `Available=FALSE` is not a healthy zero
and shall never be interpreted as synchronized. Every timestamp-bearing framework
record appends a quality Boolean owned by that timestamp: `ST_Diagnostic.TimeSynchronized`,
the come/gone/reset/shelf flags on `ST_AlarmEvent`, `ST_PartResult.TimeSynchronized`,
and `StartedTimeSynchronized` on cycle/step records. The time value remains present
for forensic ordering when quality is false; clients shall mark it untrusted rather
than discard or silently present it as synchronized.

*Cross-references: §8.3/§8.8 (timestamps), §3.16 (traceability), §11.6 (host events), §10.1 / TC3 §2.7 (fieldbus distributed clocks).*

---

## 3. Module Architecture

### 3.1 Overview

The application is built from exactly **three** function-block archetypes arranged as recursive trees. Each tree's root represents one independently controlled station; a PLC/cell scope may host several peer roots as a forest (§3.1a). The leaves bind to physical hardware. The tiers map onto ISA-88 (IEC 61512) names and onto two handler behaviours:

**§3.1a Roots & the forest.** The topmost Units — those with no parent — are **root Units**; a program may run **one or more** (§4.2). They are independent peers (own mode, cycle, model, rollup); the set of roots and their sub-trees is the module **forest**.

**§3.1b Root model identity.** A root Unit **shall** expose an **active model identity** — at minimum a `ModelCode : STRING`, and optionally `Family`, `Variant`, and a fixed-size list of client-defined named fields (`ST_ModelId`, §3.8a) — describing what it is currently set up to produce. Because roots are independent, **two roots may carry different model identities at the same time** (one station running model A while another runs model B on the same PLC). The identity is what a changeover (§3.8) sets: selecting a model resolves, through the recipe provider, the `ParCfg` of every module beneath that root — so `ModelId` is the *key*, and the per-module `ParCfg` values are the *resolved data*. The identity is published for the HMI and MES (§3.13, §11.6) and is part of every traceability record (§3.16) so a part is stamped with the model that produced it. A non-production or single-product cell **may** leave `Family`/`Variant`/fields empty and use a constant `ModelCode`.


| Tier | Type | ISA-88 | Behaviour (handler role) |
|------|------|--------|-----------------------------|
| Top (recursive) | `FB_Unit` | Unit | **ModeHandler** — runs a *continuous mode sequence* from Start until Stop; owns mode and the station state machine. |
| Middle | `FB_EquipmentModule` | Equipment Module | **CommandHandler** — exposes *discrete commands*, individually triggerable (incl. manually in Manual mode). |
| Leaf | `FB_ControlModule` | Control Module | Hardware-bound device (cylinder, valve, sensor, drive). One HAL channel. |

A `FB_Unit` may nest inside another `FB_Unit`; the recursion is what lets a single type scale from a fixture to the entire station. Strict ISA-88 would insert a non-recursive *Process Cell* above *Unit* — this standard **collapses Process Cell into a recursive `FB_Unit`** as a deliberate, documented extension. The top-most `FB_Unit` instance plays the station/Process-Cell role.

![Figure 2](diagrams/arch_tiers.png)

*Figure 2 — Recursive three-tier module architecture and containment: a Unit may contain Units/EMs/CMs; an EM may contain EMs/CMs but never a Unit; a CM is a HAL-bound leaf.*

### 3.2 Type catalogue and capability surfaces

Every archetype provides the logical base capability `I_Module`, which carries everything a parent needs to discover, monitor, roll up, and re-recipe a child regardless of tier. The `I_*` names below are **Core capability-contract names**, not a requirement that a binding implement an IEC interface, method, property, pointer, or dynamic dispatch. A binding may realize them with language interfaces (TC3 §3.2) or with generated records, bounded registries, and typed operations (AB §3.2), provided the same behavior and minimum surface are available.

```text
capability I_Module
    Name, ModuleType                    // canonical identity and UNIT | EM | CM (§4.8)
    State, FaultActive                  // derived state summary
    GetFaultSummary() -> ST_Diagnostic  // first-out of this node + descendants (§8.2/§8.8)
    PrepareRecipe(Model) -> BOOL        // validate/load staging only
    CommitRecipe()                      // bounded, infallible active-data swap
    AbortRecipe()                       // discard staging
    Cyclic() -> BOOL                    // one required lifecycle invocation

capability I_Unit includes I_Module
    ModeActive
    SetMode(Mode) -> BOOL; Start() -> BOOL; Stop() -> BOOL

capability I_EquipmentModule includes I_Module
    ExecuteCommand(Command : DINT) -> BOOL; AbortCommand() -> BOOL

capability I_ControlModule includes I_Module
    ExecuteCommand(Command : DINT) -> BOOL; AbortCommand() -> BOOL
```

Two deliberate omissions keep this surface implementable and single-sourced: it carries **no numeric `ErrorID`**—the number lives only on the PLCopen output (§6.1)—and the fault summary is the `ST_Diagnostic` of §8.8. The recipe transaction is on the base capability because changeover must prepare, commit, or abort every descendant through one generic surface (O4).

**Generic command ids are the enum's numeric value (`DINT`), and the operations are named `ExecuteCommand`/`AbortCommand`.** A per-type `E_<Type>Command` cannot appear in a shared capability surface. The typed enum remains the **primary** surface (the `Command` input every step chain and HMI catalogue use); the generic operations let one logical contract serve every type ever written (O4), and an implementation **shall** validate the received value against its command set, rejecting out-of-range values with a `ReasonCode` per §5.6.

Every module additionally publishes the PLCopen signal set (`Execute`, `Busy`, `Done`, `Error`, `ErrorID`, `Abort`, `Aborted`, §6.1) as data for hand-written step code and the Self-Description Service; `State` is the single derived summary of those signals.

A composite owns a bounded child collection through binding-defined validated handles and resolves tier capabilities for a common walk. Conceptually:

```text
for each child in Children
    if Supports(child, I_Unit)
        SetMode(child, ModeActive)
    end_if
end_for
```

The collection, capability lookup, and calls **shall** be bounded, fail closed for an invalid handle/capability, and preserve the same canonical child identity. TC3 binds this to an interface array and `__QUERYINTERFACE` (TC3 §3.2); AB binds it to generated registry indices and capability bits (AB §3.2). Neither representation changes the containment or rollup contract.

### 3.3 Containment rules

| Container | May contain | Must not contain |
|-----------|-------------|------------------|
| `FB_Unit` | `FB_Unit`, `FB_EquipmentModule`, `FB_ControlModule` | — |
| `FB_EquipmentModule` | `FB_ControlModule`, nested `FB_EquipmentModule` | `FB_Unit` |
| `FB_ControlModule` | — (leaf) | anything |

The single prohibition — **no `FB_Unit` inside a `FB_EquipmentModule`** — structurally enforces the rule that a continuous mode-runner can never be subordinate to a discrete command-handler. A reviewer or a CI check can verify this by walking the instance tree and asserting no `I_Unit` is reachable through an `I_EquipmentModule`.

### 3.4 Mode model (`FB_Unit`)

A `FB_Unit` owns a **mode** and runs a **continuous sequence** for that mode. Standard modes:

| Mode (`E_Mode`) | Purpose |
|-----------------|---------|
| `AUTO` | Normal production sequence; runs continuously between Start and Stop. |
| `MANUAL` | Operator triggers individual EM/CM commands; no automatic sequence. |
| `CHANGEOVER` | Type/recipe change, guided sequence. |
| `CALIBRATION` | Calibration/reference runs. |
| `HOME` | Move to defined home/output position. |

The mode sequence is started by **Start** (operator or parent) and runs until **Stop** is requested internally or by the operator/parent — it does not "complete and exit" the way an EM command does. The sequence body is the continuous SFC step chain of §6.2, built from the command handshake of §6.1.

A Unit **shall** reject a `SetMode` for a mode it does not implement (returns `FALSE`); the caller — including a parent Unit cascading mode — must handle rejection gracefully (§3.7).

**Sequence source layout.** A concrete Unit implementing more than one sequenced mode **shall** keep
`_M_Dispatch` as a thin mode router and place each sequence in an explicitly named implementation
unit (`_M_SequenceAuto`, `_M_SequenceHome`, `_M_SequenceChangeover`, or the equivalent SFC/LD/FBD
POU). AUTO, HOME, and CHANGEOVER shall not be hidden as unrelated step-number ranges inside one
monolithic dispatcher. This is a source-organization requirement, not a second lifecycle: every
sequence still runs through the owning Unit lifecycle, the binding's step token/record service, and PLCopen child
handshakes.

**Application ownership.** A deployed Unit's concrete mode chains are application engineering and
**shall** be visible in that Unit's project branch (§4.2). A reusable library may provide abstract
helpers, reusable sub-sequences, or an opt-in generic default, but the application shall explicitly
select it and retain an extension/replacement seam. A library implementation shall not silently make
AUTO, HOME, CHANGEOVER, or other project modes opaque or final. The concrete project Unit may derive
from a reusable base, compose reusable sequence helpers, or own the complete implementation directly.

#### 3.4.1 Mode-switch policy while a sequence runs

Whether an operator may leave the *current* mode while its sequence is running is **per-mode policy**, held as station configuration (§3.8a) — not hardcoded — so a deployment tunes each mode's protection. Two orthogonal axes describe every case:
- **Shield** (`E_ModeSwitchShield`): `INTERRUPTIBLE` (switch proceeds), `CONFIRM` (the HMI **shall** prompt before switching), or `BLOCKED_WHILE_RUNNING` (`SetMode` returns `FALSE` while `BUSY`; the operator must Stop first).
- **Style** (`E_ModeSwitchStyle`): `GRACEFUL` (request Stop, let the cycle finish at its stop point, then switch — reuses `_stopReq`/§8.11.1 and `OnModeExit` §3.14.4) or `IMMEDIATE` (cancel now via `OnAbort`, then switch).

The policy of the mode being **left** governs (that is the sequence at risk). `MANUAL` has no sequence, so leaving it is always free; entering any mode still requires `_M_Supports` (§3.7). Defaults: `AUTO` = `CONFIRM`+`GRACEFUL`; `CHANGEOVER`/`CALIBRATION` = `BLOCKED_WHILE_RUNNING`; `HOME` = `INTERRUPTIBLE`+`IMMEDIATE`. A `SetMode` refused by shield is **not** a fault — it returns `FALSE` and is surfaced (§3.13), like any graceful rejection.

#### 3.4.2 Run style & single-step

A running mode advances under one of three run styles (`E_RunStyle`), an **optional** per-mode capability (a Unit advertises support like a mode): `CONTINUOUS` (default — free-running), `SINGLE_STEP` (the sequence pauses at each step boundary and advances one step per **step request**), and `HOLD_TO_RUN` (advances only while a run input is held). The sequence consults these at its §6.2 step boundaries via the base helper `_M_StepGate(Steppable)` — the sequence author marks step points; the base decides go/hold. Modes that don't opt in run only `CONTINUOUS`.

**Per-step stop points.** `_M_StepGate` takes a `Steppable` flag, **defaulting TRUE**, so *each step* declares whether it is a valid stop point: a step with `Steppable := FALSE` runs straight through even in `SINGLE_STEP` or `HOLD_TO_RUN` (group several motions into one operator step, or protect a step that is unsafe to pause mid-way). Both stepping styles honour the flag identically. The default (TRUE) means every step is a stop point unless the author opts out — stepping "just works" without annotating every step.

> **Safety — HMI hold-to-run is not a dead-man.** An HMI `HOLD_TO_RUN` button travels over the network (latency, no safety rating) and **shall not** be presented or relied upon as a safety enabling device. A real dead-man/enabling function is a monitored, safety-rated hardware device on the safety system (§9). HMI single-step/hold-to-run is a **non-safety** convenience for low-risk step-through only; interlocks (§7.2) still apply at every step regardless of run style.

### 3.5 Command model (`FB_EquipmentModule`)

A `FB_EquipmentModule` exposes a finite, named set of **discrete commands** (its per-type `E_<Type>Command` enum, §3.2) that orchestrate the primitive commands its Control Modules already provide. Each command:

- **shall** be individually executable via `Execute(Command)`, including manual triggering when the owning Unit is in `MANUAL`;
- **shall** run as a bounded action (it completes, faults, or is aborted) — it is *not* a continuous mode loop;
- **shall not** add device-level logic that belongs in a Control Module; an EM only *sequences* CM commands.

If an operation legitimately needs several CM actions in parallel, that is a signal to split the CMs across separate EMs for parallel orchestration, rather than overloading sequence branches.

### 3.6 Device model (`FB_ControlModule`)

A `FB_ControlModule` is the only tier bound to I/O, and it binds **through the HAL**, never to raw `%I`/`%Q` directly. The HAL is a data structure that sits between CM business logic and a hardware driver, so the CM can be exercised against either real I/O or a simulated driver (`DI SIM` / `DO SIM` / `Motor SIM`) without code change. Simulation is enabled at the driver, leaving the CM logic untouched — this is what allows virtual commissioning (e.g. Process Simulate) before hardware is available.

![Figure 3](diagrams/hal_layers.png)

*Figure 3 — HAL layering: identical CM logic runs against simulated or real I/O.*

### 3.7 Mode cascade (Unit → child Unit)

When a parent `FB_Unit` is Started, Stopped, or changes mode, each child `FB_Unit` **shall** follow **only if the mode is available for that child**:

```text
for each child in Children
    if Supports(child, I_Unit)
        if not SetMode(child, RequestedMode)
            Stop(child)  // defined safe state; do not force an unsupported mode
            SetEvent(EVENT_CHILD_MODE_UNSUPPORTED, Name(child))
        end_if
    end_if
end_for
```

A parent in `CALIBRATION` therefore never drags a child that has no calibration mode into an undefined state — the child is brought to a defined safe state and the condition is reported. EMs and CMs do not have modes; they respond to the commands the active mode sequence issues.

### 3.8 Recipe / type data and its source

A `FB_Unit` (and, where useful, an `FB_EquipmentModule`) **may** expose a typed recipe/type structure. Recipe data:

- **shall** land in the module's `ParCfg` structure (§3.12) regardless of where it came from, so all downstream code is source-agnostic;
- **shall** be versioned: every `ParCfg` (and serialized recipe record) carries `SchemaVersion : UINT` as its first member. During `PrepareRecipe`, the provider compares versions and either migrates into staging or rejects with `RECIPE_INVALID`; active data is never partially overwritten or guessed by field position. Adding a member is a schema change; external payloads carry the same version;
- **shall** carry, for any measured value, its limit/target and a fixed engineering unit (units are not made variable at runtime);
- **shall** load top-down through the module tree during `CHANGEOVER`.

**Two kinds of persistent data, one placement rule (§3.8a).** The standard distinguishes **model/recipe data** (varies per model — servo target positions, speeds, tolerances; resolved by `ModelId` at changeover) from **station configuration** (varies per deployment, not per model — the MES IP/port, a scanner's baud, a scale's calibration, a fixed endpoint). Both are **persistent editable data**, and both follow the same rule: *each value lives in the module that needs it.* A servo's positions belong to the axis Control Module — or, at the programmer's discretion, to the EM of an XYZ gantry that owns the three axes; the MES endpoint belongs to the host-interface module; a scanner's config to the scanner CM. There is **no** central config blob. Concretely, a module holds its persistent values in its own `ParCfg` (model data, versioned per §3.8) and/or its own `StationCfg` (deployment data), both `PERSISTENT`. Read publication and write authority are distinct: an editable value **shall** be registered as an explicit typed write capability in the §3.10.2 manifest and changed only through the acknowledged root mailbox. Browsability or `DATA_WRITE` access alone never makes a value writable. Station config is **not** keyed by `ModelId` (it does not change at changeover) and **shall not** be bundled into a model recipe; a module that needs both simply declares both structures.

**Source is pluggable.** Recipe/type data **shall not** be assumed to be local. The source is selected per deployment via `E_RecipeSource` and supplied through one logical provider capability, so the same module works whether data is held in the PLC or fetched at runtime:

| `E_RecipeSource` | Transport | Payload |
|------------------|-----------|---------|
| `LOCAL` | in-PLC `PERSISTENT`/`ParCfg` | native struct |
| `OPCUA` | OPC UA read/method from MES/SCADA | structured nodes |
| `SOCKET_JSON` / `SOCKET_XML` | TCP/UDP socket | JSON / XML (or other) |
| `REST` | HTTP client | JSON over REST |

```text
capability I_RecipeProvider
    Load(ModelCode, RecipeKey, staged target, declared size/schema) -> BOOL
    Source : E_RecipeSource
    Ready  : BOOL
```

`ModelCode` is the product/model selected at the root; `RecipeKey` identifies the consuming module role/type. They are distinct parts of the lookup key. An empty `ModelCode` may be registered explicitly as a deployment default. The provider implementation is injected at configuration time; a conforming framework ships a working local provider by default. External payloads load only into staging and shall be complete, size-checked, and schema-valid.

**Discoverable model catalog.** A Unit may publish `AvailableModelCount` plus a bounded
`AvailableModels[] : ST_ModelId` catalog. A finite local/project catalog should publish it so the
generic HMI renders a validated selection rather than requiring free text. An external or effectively
unbounded provider may leave the catalog empty; in that case the HMI may accept a model identity only
if the PLC/provider validates it transactionally. The catalog is selection metadata—not a duplicate
recipe store—and the active `ParCfg` remains the authoritative resolved recipe.

**Atomic changeover.** `SetModel` first calls `PrepareRecipe(Model)` recursively. Validation, migration, provider I/O, and every fallible operation occur only in this phase. Any rejection calls `AbortRecipe()` and leaves every active `ParCfg` and the root identity unchanged. After every participant accepts, `CommitRecipe()` is an infallible, bounded in-memory publication at the scan boundary; it performs no validation or I/O. The root publishes the new `ModelId` only after commit. Station configuration is outside this transaction.

![Figure 4](diagrams/recipe_provider.png)

*Figure 4 — Pluggable recipe/type source behind one I_RecipeProvider; data always lands in ParCfg.*

### 3.9 Feature selectability

Each module advertises a `Features` flag set — e.g. `RecipeEnabled`, `CalibrationEnabled`, `ManualFunctionsEnabled`, plus per-command enables. Disabled features:

- **shall** be omitted from the Self-Description Service catalogues/data surface (§3.10), so the Flutter HMI renders only what exists and pays no read cost for it;
- **should** be checkable by clients through declared capability metadata and by PLC code through the binding's capability lookup (TC3 §3.2; AB §3.2).

This is what makes the same reusable type behave as a "stripped" or "full" instance purely by configuration.

### 3.10 Fraktal Self-Description Service and Flutter auto-discovery

The operator app discovers and renders the module forest generically through the **Fraktal Self-Description Service**. The service is a logical runtime contract, not a prescribed wire protocol or server product. Fraktal/TC3 binds it to TF6100 OPC UA (TC3 §3.10/§11); Fraktal/AB binds it by default to EtherNet/IP explicit messaging plus the Fraktal gateway and permits OPC UA as an alternative projection (AB §3.10/§11).

A conforming service **shall** provide all of the following from one live source of truth:

- live runtime discovery of every deployed root and its hierarchy, with stable canonical identities, declared tier/type/capabilities, and a monotonic configuration/discovery revision;
- typed values with declared logical type/dimensions, explicit freshness and quality, and source timestamps plus synchronization quality where the PLC owns a timestamp;
- bounded fast/slow/on-demand reads (or equivalent bounded change detection) so discovery and traffic stay proportional to actual demand;
- one narrow, typed, acknowledged mutation vocabulary routed back through PLC access/release/validation, with no arbitrary symbol/tag write and no reconnect replay;
- explicit protocol and schema versions with fail-closed incompatibility handling; and
- authenticated principals, least privilege, and integrity/confidentiality controls appropriate to the binding's declared IEC 62443 conduit (§11.2, §14), plus optional industry projections generated from this same live model rather than maintained in parallel.

The following layers make that contract HMI-complete without station code:

**(a) Exposure by deployed root.** Exposure starts only at an explicitly deployed root instance (and at a separately defined published data product such as fieldbus topology). The binding carries that selection through the root's real child hierarchy or generated manifest, so a new module type still needs no station-specific exposure code. Reusable type definitions shall not publish every possible instance globally: doing so turns implementation storage and infrastructure aliases into additional roots and violates least privilege. Pointer/reference storage, private registry/provider state, scratch data, and aliases beneath a published root shall be excluded. Bindings define and gate the exact mechanism (TC3 §3.10; AB §3.10/G-EXTACCESS).

**(a′) The HMI contract is data, not accessors.** A client **shall not** require PLC-language properties, methods, pointers, or type introspection. Everything it renders is published data in the module mirror: `Status : ST_ModuleStatus` (`Name`, `ModuleType`, `State`, `FaultActive`, the live `Diagnostic` per §6.9(a), `TileEnable` per §3.13), refreshed each scan by the owning lifecycle — so a type is HMI-complete with zero exposure code (O1), and a port re-binds the same structures (O8). On a Unit, a live stall (`Pending`, §6.9) surfaces on the mirror whenever no fault is active, so the tile message is always the most useful sentence available (O3).

**(a″) Remote commands are acknowledged data transactions.** Every root Unit shall publish one typed request mailbox and response mailbox through the service. The client writes all arguments before changing the commit sequence. The Unit samples each new complete sequence once, copies it to private storage, routes it through the same access/release-gated operations used by local PLC code, clears transported secrets immediately, and publishes the matching acknowledgement sequence only after processing. Transport write success is not PLC acceptance; `Accepted` plus the matching acknowledgement is. A reconnect shall never replay an unacknowledged request automatically. Bindings may name the records and fields (`ST_HmiRequest`/`ST_HmiResponse`, `Sequence`/`AckSequence` in TC3; AB §7.7's physical names are frozen after S9), but these commit/acknowledgement/no-replay semantics are normative.

**(b) Type-aware discovery.** Every module record explicitly declares `ModuleType`, concrete type identity, capability flags, canonical path, and parent/root identity. The Flutter app walks this hierarchy and selects standard UI templates from the declared semantics—never from a guessed tag name, optional-field absence, PLC-language inheritance relation, or transport metadata. A binding may project richer native type metadata, but clients do not depend on it.

**(c) Standard semantics.** The **state model is the native command model by default**: expose each module's `ExecState` and, for Units, `Mode` directly (§6.1, §3.4). No companion specification is required for base conformance. OPC UA for Machinery (OPC 40001-1), PackML/OPC UA (OPC 30050), AAS/MTP, and the other §11.7–§11.11 mappings are optional, binding-qualified projections from the same service model.

Each module **shall** present the same logical sub-structure mirroring §3.12: `Identity`, `Status` (plus `Mode` for Units), `ParCfg`, `ParCmd`, `OutCmd`, `OutImm`, `Features`, and `Children`; clients read the execution summary from `Status.State`. These are canonical repository path segments. A binding may obtain them from native namespace nodes or reconstruct them from a validated manifest, but it shall not expose a competing hierarchy or identity.

![Figure 5](diagrams/opcua_hmi.png)

*Figure 5 — Live self-description driving a generic HMI and MES (TC3 transport: TF6100 OPC UA; AB default: EtherNet/IP plus gateway).*

#### 3.10.1 Digital nameplate (asset identity)

The runtime self-description (§3.10) answers *what the module is doing*; maintenance also needs *what the module **is***: who made it, which serial, which versions, where the manual lives. Every module therefore carries a **digital nameplate**, published through the same Self-Description Service:

- **Fields** (aligned with the IDTA *Digital Nameplate for Industrial Equipment* submodel template, IDTA 02006, so the projection to AAS in Annex K is direct): product URI (globally unique asset identifier), manufacturer name, product designation, serial number, year of construction, hardware/firmware/software versions, order code, and a documentation link (manual/handover docs, cf. IDTA 02004). All fields are plain published data — **static identity, set at Setup, never runtime-mutated**.
- **Cardinality.** A **root Unit shall** publish a nameplate (it is the sellable asset); **any module may** (a purchased CM — a robot, a camera — has its own identity worth keeping). Empty nameplate = none published; the HMI simply omits the card.
- **HMI (§3.13).** The nameplate renders as a facet card on the module detail view — identity, versions, and a tappable documentation link. No per-type HMI code (O1).
- **Not configuration.** The nameplate is identity, not behaviour: it is deliberately outside §3.8 (no recipe/model dependence, no §7.7 write gating question — it is not writable from the HMI at all).

*Cross-references: §3.10 (self-description), §3.13 (HMI rendering), §8.3/§10.5.1 (the diagnostic surfaces this complements), Annex K (AAS/IEC 63278 projection).*

#### 3.10.2 Bounded configuration manifest and typed write capabilities

Activation-static identity and catalog data **should** be excluded from the cyclic
namespace when the binding can serve it on demand. Each root Unit therefore exposes a
revisioned, bounded configuration-manifest page through its acknowledged mailbox. A
deterministic walk emits entries containing `Scope` (qualified module identity), `Item`
(canonical repository-path fragment), and `ValueText`; paging shall not require a full manifest buffer in
the PLC. `ConfigRev` changes after activation, model/configuration changes, or restart so
a client cannot retain stale metadata silently.

Read publication does not confer write authority. An editable entry appends all of the
following capability data:

- stable `WriteKey` scoped to the owning module and a non-zero `WriteRevision`;
- `ConfigKind` (`PAR_CFG` or `STATION_CFG`) and `ValueType` (`NUMBER`, `TEXT`,
  `BOOLEAN`, or `TIME`), with append-only ordinals;
- `Writable`, optional numeric bounds, optional exact enum domain, engineering unit and
  label key; and
- whether the owning root must be `READY` for the write.

An absent key/revision, `Writable=FALSE`, invalid metadata, or a duplicate
`(Scope, WriteKey)` registration **shall fail closed** and produce no editor control.
`Item` remains a path/display identity; `WriteKey` is the mutation identity and shall
not be inferred from `Item` or from transport-level writability. For `WRITE_CONFIG`, the
client sends `TargetPath=Scope`, `NameValue=WriteKey`, `IntValue=WriteRevision`, and the
serialized candidate in `TextValue`, committing `Sequence` last.

The root rechecks `DATA_WRITE` access and subtree ownership, then routes only a registered
key to the owning typed handler. That handler shall recheck revision, value type,
range/domain, current machine state, and all module-specific invariants before changing
data. Unknown keys, stale revisions and malformed or out-of-domain values are rejected
without mutation. Recipe-backed changes remain migrate-or-fault and transactional per
§3.8; this mailbox is not a partial recipe-write escape hatch. Accepted and denied
requests follow the §8.3 audit rules. A generic HMI may render editors from these
capabilities, but is never an authorization or validation authority.

### 3.11 Reusable sub-trees (low-effort duplication)

Reuse is achieved with a binding-native reusable type form, not copy-paste:

- Any archetype is a **type**. To duplicate, declare another instance with a fresh canonical identity and HAL/configuration mapping. The binding shall provide a deterministic, exactly-once initialization mechanism and shall fail closed before cyclic execution when wiring is invalid (TC3: constructor/`Setup`, TC3 §3.11; AB: generated first-scan setup, AB §3.11).
- A **recurring assembly** (e.g. a clamp = 1 cylinder + 2 sensors) is packaged as one conforming Equipment-Module type that owns its children internally. That whole sub-tree then drops in anywhere as one named type with a fresh mapping.
- **Nested wiring is explicit and order-safe.** A parent shall not rely on an unspecified member-construction or import order to forward identity, HAL, recipe, provider, or child registration. Each binding provides an order-safe one-shot setup form usable at any nesting depth and machine-checks exactly-once setup before first cyclic use (Annex B; TC3 §3.11; AB §3.11/G-SETUP).

### 3.12 Standard object data contract

Every module — `FB_Unit`, `FB_EquipmentModule`, `FB_ControlModule` — exposes the same four-structure data contract, which is also exactly what the Self-Description Service publishes (§3.10):

| Structure | Suffix | Role | Distribution |
|-----------|--------|------|--------------|
| Configuration | `ParCfg` | parameters/recipe set from the parent; behaviour-shaping | applied on Start, or on `disabled → operational` |
| Command params | `ParCmd` | per-command transfer parameters | latched on the positive `Execute` edge |
| Command results | `OutCmd` | values valid after a command completes | written once on `ExecState → DONE` |
| Cyclic status | `OutImm` | live status (inputs, outputs, flags) + first-out `Diagnostic` | refreshed every scan |

**Command result vs. derived state — the distinction that decides which one.** Ask
what makes the value change. If a *command produced* it and it stays true until
another command replaces it, it is `OutCmd`. If it is simply *true right now*,
recomputed from what the modules underneath actually report, it is `OutImm`.

`Homed` is the case that gets this wrong most often. Written as `OutCmd.Homed := TRUE`
at the end of a HOME sequence it goes on claiming "homed" after an operator jogs an
axis off the reference position in MANUAL — because no sequence runs to clear a latch
that only a sequence can clear. It is not a command result. It is a fact about where
the axes are, and it **shall** be derived.

A module publishes derived state through `_M_State`, which returns the value so the
assignment reads as it otherwise would:

```iecst
OutImm.Homed := _M_State(Idx := 1, Key := 'project.state.atLoadPosition',
    Ok := Ram.OutImm.Retracted AND Door.OutImm.Retracted AND Slide.OutImm.Retracted);
```

What the call adds over a bare assignment is what nobody wants to write per flag
(§1.1 O1):

- **The flag carries its own name**, so the HMI renders it without knowing the module
  type (§3.13) — the same generic-rendering bargain as the rest of the contract.
- **`Since`** — the moment the value last changed, on the synchronized clock (§2.7).
  "Door closed" is rarely the question; "closed for how long" is.
- **Fail-safe on abandonment.** A flag **shall** be published unconditionally every
  scan. One that stops being published is marked `Stale` and forced FALSE on the next
  scan: state nobody is computing is not a claim (§5.6). A latch left standing is
  precisely the failure this mechanism exists to prevent, so the mechanism must not
  be able to leave one.
- **Bounded** at `MAX_STATE_FLAGS` per module, statically sized like every other
  Fraktal table (§1.1 O10).

It is deliberately the same shape as the §6.9(b) named condition wait
(`_M_Await(Idx, Label, Ok)`) — one idiom for "a named boolean the framework
publishes", not two (§1.1 O9).

This contract makes every module uniform and self-describing: the handshake of §6.1 reads/writes `ParCmd`/`OutCmd`, the recipe of §3.8 lives in `ParCfg`, and the Flutter HMI binds to `OutImm` for live state. Module-specific structure types **shall** be named `ST_<Module>ParCfg` / `ST_<Module>ParCmd` / `ST_<Module>OutCmd` / `ST_<Module>OutImm` (e.g. `ST_SeparatorParCfg`).

![Figure 6](diagrams/data_contract.png)

*Figure 6 — The four-structure data contract and its distribution timing.*

### 3.13 HMI navigation contract (drill-down model)

The module hierarchy maps directly onto an HMI navigation tree (`FB_Unit` = ModeHandler view, `FB_EquipmentModule` = CommandHandler view, `FB_ControlModule` = device view). The operator app **shall** navigate by drill-down through the module tree, and the PLC **shall** expose the metadata that makes this automatic:

- **Two views per module.** Each module type provides a *Tile* (compact: name, state LED, key status, quick manual buttons) and a *Detail/Overview* (manual functions, status LEDs with descriptions, parameters).
- **Parent shows children as tiles.** A module flags whether it appears as a tile on its parent's child view (and whether it serves as a header control). The operator app renders a parent by laying out its children's tiles, and drills into a child on tap — the same parent→child path as the module tree.
- **Status LEDs carry descriptions.** Every status LED binds to a condition with an adaptable, multilingual text description (sourced from the channel/`PermIntlk` descriptions of §7), so the operator reads *why*, not just red/green.
- **Generic rendering.** Because the tree is self-describing through the Fraktal Self-Description Service (§3.10), every module carries the four-structure contract (§3.12) and `Features` flags (§3.9), the Flutter app builds tiles and detail views generically — no per-station screen building. New or duplicated modules (§3.11) appear in the HMI automatically.
- **Tabbed details and category facets.** Every module detail provides Overview and Description; typed/category data may add reusable Motion, Vision, Code Reader, or RFID tabs. An HMI-local Administrator may set each tab's minimum view level and add localized custom controls, but this layout cannot widen the §7.7/§14 PLC write surface or recover symbols excluded from publication. A one-visible-tab detail omits the tab strip.
- **Guided Unit work.** A Unit guidance tab may match `CurrentStep.StepNo`/`StepName` (or all `WAIT_OPERATOR` steps) and opens a full-screen localized work instruction with the live wait conditions and typed `Decision`. The PLC sequence remains the sole owner of progress and acceptance; dismissing HMI guidance never advances a step.
- **The stuck-step reason surfaces on the owning Unit's view**, exactly where the operator expects sequence state (see §6.9).
- **Discovery & binding contract.** The client discovers the tree by walking the service's canonical hierarchy (§3.10) for module records carrying `Status : ST_ModuleStatus` — that record *is* the module marker, tile caption, state LED, and message line (§3.10(a′)); child tiles are the child records with `Status.TileEnable`. A binding may expose that hierarchy as a native namespace or reconstruct it from a manifest and bounded value services. Units additionally publish `Pending`, `CurrentStep`, `History` (the §6.9(a) ring), `GoodCount`/`NokCount` (§8.11), `Decision`, and the §8.11.4 profiler structures. The write surface is deliberately narrow and is committed through the acknowledged Unit mailbox of §3.10(a″): command execution/abort, decision answer, mode/start/stop, manual commands and the other explicitly gated actions of §7.7.
- **Event path highlighting (tree).** The navigation tree **shall** tint the full ancestor path — from the root Unit down to the event's source module — with the colour of the highest-severity **active** event in each node's subtree (`ERROR` > `WARNING` > `MESSAGE`, §8.3); the source module renders strongest, ancestors as tint. An operator therefore sees *where to drill* from any depth with zero station code — the highlight derives from the same `Status.Diagnostic`/`AlarmLog` data every node already publishes (§8.2 rollup made visible).
- **Cycle-profile view (§8.11.4).** Every Unit's detail view renders, generically from the fixed profiler structures, the last cycle as a **step waterfall** (start/duration per step, `ExpectedTime` overlaid) and a **Pareto of per-step Avg/Max**; tapping a step drills to the awaited module, whose detail shows its per-command timing table. Steps are coloured by **time class** and the view header splits **Total vs Work (the real cycle time) vs the waits** (`WAIT_UPSTREAM`/`WAIT_DOWNSTREAM`/`WAIT_OPERATOR`/`WAIT_EXTERNAL`, §8.11.4(f)) — so "the station is slow" and "the station is starved" are visibly different statements. No station adds screens or code for this — the chart exists because the step records and the framework lifecycle exist.


**Localized presentation and module content.** Every operator-facing string follows `LOCALIZATION_AND_MODULE_CONTENT.md`. PLC display fields **shall carry stable localization keys rather than prose**; the HMI composes standard/project catalogs and keeps identity, protocol data, and structured diagnostic context separate. First-run language selection, administrative CSV exchange, module descriptions/PDFs, and per-module section view policy are part of the generic HMI contract and add no station-specific screen code.

### 3.14 Module lifecycle extensions (framework callbacks)

Every module has the same small set of **lifecycle extension points**. They are framework-internal callbacks at defined points in the authoritative cyclic lifecycle (§2.2), not public parent-facing capabilities. The binding **shall** state how each extension is represented and invoked. A binding with inheritance may use protected virtual methods; a binding without inheritance may use generated composition and explicit callouts. Either mechanism shall preserve the same ordering, one-shot semantics and default behaviour without project-authored correctness wiring.

These extension points replace ad-hoc callback sets and hand-written one-shot guards with one fixed contract. A module declares only the application reaction it needs; the framework or generator supplies the lifecycle behavior and the default for every omitted reaction. The `On<Event>` logical names are stable across bindings even when their native object names differ.

#### 3.14.1 Extension catalogue

| Standard extension | Owner | Invoked by framework when | Return |
|---|---|---|---|
| `OnInit` | any module | First operational scan only (one-shot, after recipe/type data is available) | `DINT` |
| `OnCommandStart` | any module | Once for each accepted `Execute` rising edge, after `OnInit` and before cyclic/dispatch work | `DINT` |
| `OnCyclic` | any module | Every scan, background management after data load | `DINT` |
| `OnModeChanged` | Unit only | After a `SetMode` is accepted and the new mode is committed | `DINT` |
| `OnModeExit` | Unit only | During a mode change, **before** leaving the old mode — lets a Unit stop gracefully instead of being cancelled outright | `DINT` |
| `OnAbort` | any module | On cancel/abort, **not** during `ERROR` or `NOT_READY` | `DINT` |
| `OnAbortInError` | any module | On cancel/abort **while** the module is in `ERROR` | `DINT` |
| `OnManRelease` | any module exposing manual functions | To (re)evaluate manual-function release conditions (see §7.6) | — |
| `OnChainAbort` | step chain | A chain is leaving via cancel | — |
| `OnChainError` | step chain | A chain is leaving via error | — |

`OnChainStart` / `OnChainDone` logical points may exist in a binding but **shall not** be used by applications; put initialization in start step `N000` and teardown in finish step `N999` instead (they always run, optional callbacks may not). See §6.5 step-chain conventions.

#### 3.14.2 Extension-order contract (mandatory)

1. **Framework behavior first.** Except for `OnModeExit`, the framework-owned behavior associated with an extension **shall** execute before the application reaction and its return shall be propagated unless deliberately changed. [TC3] realizes this with a base-method call first; [AB] realizes it in generated lifecycle routines before the application callout. A project shall never have to remember this ordering.
2. **Declare only what is needed.** An omitted extension uses the framework default; do not create empty reactions.
3. **Keep extensions side-effect-bounded.** A cyclic extension (`OnCyclic`) **shall** be idempotent per scan and **shall not** drive outputs directly — it manages state and raises events; movement stays in the step chains (§6.2–6.4).
4. **One-shot initialization belongs in `OnInit`.** Do not reproduce it with a first-scan flag in `OnCyclic`.
5. **Command-local reset belongs in `OnCommandStart`.** Reset or latch command-local wiring there when it must run once for every accepted command, including a repeated finite command in the same mode. Keep process initialization in sequence step `N000` and process completion in `N999`; the extension shall not become a second sequence body.
6. **The binding shall prove the assembly.** Generation and linting shall reject a module whose extension can bypass, reorder or duplicate the framework-owned portion of the lifecycle.

#### 3.14.3 Worked example — `OnModeChanged` on a Unit

A Unit limits actuator speed in `MANUAL` and restores it in `AUTO`. The binding-owned lifecycle first performs the common mode bookkeeping, then invokes this application reaction:

```text
OnModeChanged application reaction(NewMode, OldMode):
    when NewMode = MANUAL: OutImm.MaxOverride := 30
    when NewMode = AUTO:   OutImm.MaxOverride := 100
```

The reaction contains no duplicate bookkeeping and is identical in intent whether the binding emits an override or a composed callout.

#### 3.14.4 Mode change aborts immediately by default — `OnModeExit` provides graceful completion

By framework default, a mode change performs an **immediate software abort**: all standard-control chains and commands are cancelled so the operator lands in a defined state. This is not an emergency stop and not a safety function (§9). Where a Unit must instead finish its cycle or move to a waiting position before yielding the mode, it **shall** declare an `OnModeExit` reaction that triggers a stop-after-cycle and holds the mode until the Unit is stopped (bounded by a timeout), rather than immediately propagating abort to children. Return semantics are fixed: the framework invokes the reaction every scan while a mode request is pending; returning `0` consents to the default immediate abort, returning `>0` holds the transition while the Unit stops gracefully; the new mode commits only when the Unit leaves `BUSY`, after which `OnModeChanged` fires.

`OnModeExit` is the deliberate exception to framework-first ordering: the application reaction runs before the framework cancel while it returns `>0`; when it returns `0`, the binding invokes the framework cancellation/commit portion exactly once. [TC3] stages the base call to the end; [AB] stages the generated cancel phase after the callout. Every binding shall document and test this exception.

#### 3.14.5 Source placement

Per §6.7, lifecycle extensions **shall** be filed with the module's private/protected implementation (for example, a `Lifecycle` or `Transition States` group alongside `Steps`, `Commands`, `Sequences`). They are not step actions and **shall not** live in the `Steps` group.

*Cross-references: §2.2 (authoritative lifecycle), §3.2 (public capabilities), §6.5/§6.7 (step chains and source organisation), §7.6 (`OnManRelease` is the manual-release member of this family), §8 (extensions raise events via the §8.7 constants, never ad-hoc strings).*

### 3.15 External device connector & link supervision

The HAL (§3.6, §10.2) abstracts **bit/word I/O**. It does **not** cover **networked smart devices** — robots, programmable power supplies, chillers, testers, vision systems, scanners — which hold a session and speak a protocol (TCP/socket, S7, REST, vendor SDK) with their own connect/handshake/heartbeat. Wrapping such a device as if it were I/O hides the one failure mode that matters most for it: **the link itself going away.** The standard therefore defines a dedicated archetype and a uniform **link-supervision** contract.

### 3.15.1 The connector archetype

A smart device is represented by the logical `I_DeviceConnector` capability, which composes the `I_Module` capability (§3.2) with session and link concerns. It owns the transport; it is then composed **inside a Control Module** so the rest of the tree still commands it through the standard handshake (§6.1) and never sees the protocol. The capability surface is:

```text
I_DeviceConnector capability
  operations: Connect, Disconnect
  state: Linked, LastSeen, LinkReason
```

`Linked` means session up **and** heartbeat healthy; `LastSeen` uses the synchronized timestamp contract (§2.7); `LinkReason` carries the first-out link/protocol diagnostic. Bindings may realize this with an interface, a typed record plus routines, or a generated registry entry (§3.2).

The protocol boundary (serialization, socket lifecycle, vendor SDK) lives **entirely inside** the connector — the `FC_PlcToTst_*` / `_00FB_Eth_*`-style bridge functions in the reference programs are exactly this layer and **shall not** leak into Control Modules or sequences.

#### 3.15.1a Byte-transport abstraction (TCP/serial devices)

Many peripheral devices — vision sensors, code readers, gauges, printers — speak a simple **byte protocol over TCP/IP or serial** (typically ASCII request/response). The framework therefore defines one platform-neutral transport seam, so device modules are written once and ported by swapping only the transport:

- **`I_ByteChannel`.** This logical capability has non-blocking, cyclic-poll semantics (PLC-friendly, no blocking calls): `Open(Host, Port)`, `Close()`, `Send(bytes)`, `Poll()` (drains received bytes into the caller's buffer), and a published `E_ByteChannelState` (`CLOSED` → `OPENING` → `OPEN`, plus `FAULT`). All operations return immediately; progress is observed over scans.
- **The porting seam (O4/O8).** Platform bindings realize the capability — [TC3]: `Tc2_TcpIp`/TF6310 (TC3 §3.15); CODESYS: SysSocket/NBS; Siemens: `TSEND_C`/`TRCV_C` wrappers. **No device module names a socket API**: its protocol logic consumes `I_ByteChannel` semantics and moves between PLC brands with only its binding adapter regenerated or substituted.
- **`FB_AsciiDeviceCM`.** This reusable CM category (§3.3) owns ASCII request/response behavior: configurable terminator framing, one-outstanding-request state machine (`SendRequest` → await → response-reaction extension), response **timeout ⇒ fault** with a §8.8 band code, bounded reconnect via the channel, and link state published for the HMI (Annex D facet — no new HMI code). Device profiles (a specific sensor or reader) compose it: publish their manual commands (§7.6.1, e.g. *Trigger*), supply a response parser reaction, and keep **protocol strings as Setup parameters verified against the vendor manual — never hard-coded folklore**.
- **Device-category CMs — configure first, specialize second.** Consistent with the CM philosophy (modules are named for their *function*, never their vendor — a cylinder CM is not a Festo CM), the reusable categories above `FB_AsciiDeviceCM` are `FB_TcpVisionCM` (triggered inspection: configurable trigger command and OK/NG prefixes, publishes judgement + result payload) and `FB_TcpCodeReaderCM` (triggered read: configurable trigger and no-read token, optional match-code verification, publishes the decoded symbol). **Most devices are covered by configuration alone** (§3.8-able protocol strings, verified against the vendor manual). A model-specific type (e.g. an IV3 preset) is a *thin specialization*: preconfigured strings plus reactions only where the device has genuinely special features. Category CMs cover ASCII request/response devices; binary or unsolicited-streaming protocols need a different category (deferred until demanded).
- **Testability.** A scripted `FB_SimByteChannel` realizes the same capability, so device CMs are binding-xUnit-tested end-to-end (request → scripted reply → parse; silence → timeout fault) **without any socket or vendor hardware**.
- The connector archetype (§3.15.1) and its link supervision (§3.15.2) sit *above* this seam unchanged: a TCP connector realizes its open/close/heartbeat operations over an `I_ByteChannel` capability.

*Reason band: TCP/ASCII device CM base `10401–10406` (§8.8 registry). Cross-references: §3.3, §7.6.1, §8.8, Annex D, TC3 §3.15.*

### 3.15.2 Link supervision (mandatory for every connector)

Every connector **shall** implement a heartbeat and a defined loss reaction:

- **Heartbeat.** The connector exchanges a periodic liveness signal (counter echo, keep-alive, or cyclic read) and considers the link healthy only while heartbeats arrive within `LinkTimeout` (a `ParCfg` value, §3.8). `Linked` is FALSE the moment either the session drops or the heartbeat lapses.
- **Loss reaction.** On loss, the connector **shall** drive a configured, defined reaction — `HOLD` (freeze and wait), `ABORT` (safe-stop the dependent command), or `MODE_STOP` (request the owning Unit to stop after cycle) — never an undefined hang. The reaction is a `ParCfg` choice so the same connector behaves correctly whether it drives a critical motion or a passive scanner.
- **Reason.** Loss raises a first-out reason on `LinkReason` / the module diagnostic: `LINK_TIMEOUT` (heartbeat lapsed), `DEVICE_NOT_READY` (session up but device not operable), or `DEVICE_PROTOCOL_ERROR` (malformed/refused exchange) — Framework band, §8.8 — with the device's `SourcePath`. The owning CM adopts it via the normal rollup (§8.2), so a dead robot surfaces as *"Loc130.Robot: link timeout (see Annex I)"* on the Unit's view through the same stall walk as any other fault (§6.9), with **no** per-device diagnostic code.
- **Reconnect.** The connector **shall** attempt reconnection on a bounded backoff while holding the safe reaction, and **shall not** auto-resume a dependent command on reconnect — resumption is a deliberate sequence/operator step, mirroring the safety re-energize rule (§9.3).

### 3.15.3 Composition & wiring

A connector is assembled once via `Setup` (§3.11) like any reusable sub-tree, injecting its endpoint/credentials from configuration (never embedded — §11.4, §14). Because it presents `I_Module` semantics, the parent CM's generated/native cyclic assembly services it every scan so `Linked`/status stay live, exactly as it services the HAL. The parent adopts a false `Linked` state through the common diagnostic rollup; a project does not hand-write recurring connector wiring.

### 3.15.4 HMI (§3.13)

A connector renders a **link LED** (`Linked`), a **last-seen** time (`LastSeen`, §2.7), the live `LinkReason` line, and a **reconnect** action (release-gated, §7.6) — the same generic tile/detail pattern, so no per-device screen is built.

*Cross-references: §3.6/§10 (HAL is for I/O; connectors are for networked devices), §3.11 (Setup wiring), §8.2/§8.6 (rollup, System alarms), §9.3 (no self-resume), §14 (endpoints/credentials).*

### 3.16 Traceability & part context

The standard moves recipes **down** (§3.8). It must equally move **part identity and results up**. Production cells commonly do this — data-tag/carrier access raising per-workpiece part events, or RFID reads bound to test results — but rarely as a contract. This section defines one: a typed **part context**, a source-agnostic **carrier**, and a fixed set of **part-lifecycle events**.

### 3.16.1 Part context

A workpiece is represented by a typed record carried by the Unit (and, for multi-station lines, handed between Units):

```iecst
TYPE ST_PartContext : STRUCT
    Uid        : STRING(64);     // serial / VIN-like unique id ("" if no part)
    Present    : BOOL;           // a part is in the station
    CarrierKind : E_CarrierKind; // RFID | DATAMATRIX | BY_POSITION | HOST
    Result     : ST_PartResult;  // accumulates this station's outcome
    Parents    : ARRAY[1..MAX_GENEALOGY] OF STRING(64);  // genealogy: consumed components
END_STRUCT END_TYPE

TYPE ST_PartResult : STRUCT
    Verdict    : E_Verdict;      // NONE | OK | NOK | REWORK
    ReasonCode : E_Reason;       // first NOK reason (reuses §8.8 vocabulary)
    Records    : ARRAY[1..MAX_RESULTS] OF ST_MeasRecord;  // measured values (test cells)
    StationPath : STRING(255);   // canonical path of the producing station (§4.8)
    Stamp      : DT;             // synchronized timestamp (§2.7)
END_STRUCT END_TYPE
```

`ST_PartResult` reuses `E_Reason` (§8.8) so a NOK verdict carries the **same** reason vocabulary as a fault — the thing that stopped the part is named identically whether it halted the machine or just failed the part.

### 3.16.2 The carrier is source-agnostic (like the recipe provider)

A module reads/writes part data through an injected logical `I_PartCarrier` capability, mirroring `I_RecipeProvider` (§3.8) so the transport — RFID/data-tag, Data Matrix scan, position-tracked host lookup, or MES query — is configuration, not code. The capability has two operations: `ReadContext(Ctx) : BOOL` and `WriteResult(Ctx) : BOOL`; FALSE reports read/write failure. A binding may realize those operations with an interface or with a generated provider handle and typed routines (§3.2).

A failed read **shall** fault the consuming module with `CARRIER_READ_FAILED`, a failed write with `CARRIER_WRITE_FAILED`, and a Uid that does not match the expected part with `PART_ID_MISMATCH` (Framework band, §8.8) — never a silent continue on a missing or wrong identity.

### 3.16.3 The four canonical part-lifecycle events

A Unit's mode chain (§6.2) **shall** raise exactly these events at defined points, so every station reports a part's progress identically:

| Event | Raised when |
|-------|-------------|
| `EVENT_PART_RECEIVED` | part identity confirmed at station entry (after `ReadContext`) |
| `EVENT_PART_PROCESSING_STARTED` | the processing/test sequence begins |
| `EVENT_PART_PROCESSED` | processing completes — carries `Verdict` (OK/NOK/REWORK) |
| `EVENT_PART_PROCESSING_ABORTED` | the part leaves without a valid result (fault/abort/manual removal) |

These are the in-PLC events; their **mapping to MES/ISA-95** is §11.6. Result write-back (`WriteResult`) **shall** occur before `EVENT_PART_PROCESSED` so the carrier and the host agree.

### 3.16.4 HMI (§3.13)

The Unit tile shows the live part `Uid`, `Present`, and current `Verdict`; the detail view exposes the result record and genealogy. As everywhere, this renders from the self-describing model with no per-station wiring.

*Cross-references: §3.8 (recipe provider — the symmetric pattern), §2.7 (timestamps), §8.8 (shared reason vocabulary), §11.6 (host mapping), §14 (carrier/host data is third-party input — validate per secure-coding).*

### 3.17 Additional modes and extension control

§3.4 defines five baseline modes. Real cells run more — the reference station adds **Capability** and **Adjustment** — so the Core transport contract appends these two optional modes explicitly.

- **`CAPABILITY`** — a capability/Cmk–Cpk study: the Unit runs a defined, repeated cycle collecting measurements for machine- or process-capability assessment, outside normal production routing. Used at commissioning and re-qualification.
- **`ADJUSTMENT`** — a guided setup/teach mode for tuning positions, offsets, and forces between changeovers, without running production.

Both are added to `E_Mode` (framework band) and behave like any other mode: a Unit advertises support through `_M_Supports` (§3.4, §3.7), so the mode cascade and **graceful rejection** of an unsupported mode (§3.7) apply unchanged, and `OnModeChanged`/`OnModeExit` (§3.14) handle entry/exit.

**Extension control.** `E_Mode` ordinals are an append-only PLC↔HMI transport contract. A new mode therefore requires a coordinated Core contract revision: append the enum value, increase the declared mode count, add the HMI label/icon and policy entry, define its PackML mapping, and perform the compatibility/version review of §1.5. A project or downstream library shall not silently add a private ordinal and claim generic-client compatibility. The Unit still implements the mode's continuous chain `_M_<Mode>Chain` (§6.2), advertises it in `_M_Supports`, and reacts in `OnModeChanged` (§3.14); it reuses the normal handshake and diagnostics.

*Cross-references: §3.4 (baseline modes & `_M_Supports`), §3.7 (cascade & rejection), §3.14 (`OnModeChanged`/`OnModeExit`), §6.2 (mode chains), §11.7 (PackML Unit-Mode mapping).*

---

## 4. Project Structure & Naming

### 4.1 Project settings

- A deployed application PLC project name **shall** be `SolutionName_PLC`, matching the controller name in the electrical schematic. Framework libraries, reusable-module libraries, and test projects use their published library/gate identities instead.
- Toolchain version and all libraries (system, standard, vendor) **shall** be pinned; local library references are not permitted (§2.2).
- Documentation format: reStructuredText; project Company/Title/Version/Author/Description fields populated.
- Platform project/solution settings (symbol download for §3.10, boot behaviour, runtime ports) are binding-level — **TC3 §4.1**.

### 4.2 Ownership-first project structure

An application folder tree **shall answer “which deployed module owns this?” before “what kind of
artifact is this?”**. It follows the physical/instance tree, not global `POUs`, `DUTs`, `Sequences`,
or fixed-tier buckets. Every project object has exactly one structural owner: `00_System`, one root
Unit branch, or a descendant module inside that branch.

```text
00_System                         // MAIN, raw I/O, safety aliases, tasks, shared infrastructure
01_<RootUnitName>                 // one deployed root Unit and its project engineering data
   ├─ Release                     // cross-module/mode-entry permissives and release reports
   ├─ Recipes                     // owner-local model/recipe catalog, when present
   ├─ Io                          // approved I/O catalog and fieldbus publication, when present
   ├─ Sequences                   // only when the tool stores chains as separate objects
   │  ├─ Mode                     // this Unit's continuous mode chains
   │  └─ Sub                      // this owner’s private sub-sequences
   ├─ <ChildUnitName>             // recursion: same ownership layout
   ├─ <EquipmentModuleName>       // owner-local command chains and children
   └─ <ControlModuleName>         // project-owned leaf/HAL adaptation, if any
02_<NextRootUnitName>             // peer root; never a synthetic super-root
```

Role folders are permitted **inside** an owner branch; an application-wide `Modes` or `Commands`
folder is not. If a platform stores methods under their owning FB, those methods stay there—do not
create forwarding POUs merely to manufacture folders. Reusable library types are not deployed
instances and therefore do not pretend to be an application tree: a library may group a small public
surface by stable artifact kind, or a larger family by type with type-local `Data`, `Simulation`, and
sequence objects. In both cases the owner/type relationship shall remain unambiguous, and the
executable aggregate test runner remains outside the runtime library (§5.7).

Project-specific composition, concrete mode sequences, cross-module/mode-entry release policy, recipe
catalogs, I/O identity, and deployment adapters belong to the owning application branch. A genuinely
reusable module type and its simulation belong in a reusable library (§3.11); copying its implementation
into every instance folder defeats O1/O4. A generic Unit implementation may be offered by a library only
as an explicit, documented, extendable/replaceable choice—not as hidden final project behavior (§3.4).

`MAIN(PRG)` is linked to the PlcTask and is only the composition/call root: it initializes shared
infrastructure and calls **each root Unit's** `Cyclic()` in the defined scan order (§10.2.1). It does
not own child sequence logic or channel assignments.

**Non-normative comparison.** The reviewed Nexeed export’s location-owned folders and distinct
Mode/Command/Sub chain roles are useful orientation, but Fraktal does not claim Nexeed compatibility
and does not import its per-step wrappers, Unit/Extension pairs, Addon structure, or PLC-authored HMI
visibility. The objective-filtered comparison is recorded in `NEXEED_REFERENCE_INSIGHTS.md`.

**One or more root Units per program (§3.1a).** A PLC program **shall** host one *or more* root `FB_Unit` instances — one per independently-controlled entity (a station, a conveyor system, a sub-line). Roots are peers: each owns its own mode, cycle, recipe/model identity (§3.1b), and diagnostic rollup, and there is **no** shared super-root in PLC code. `MAIN` holds them in a fixed root collection and ticks each every scan; the folder tree gains one `0N_<UnitName>` branch per root. This is the same recursion as any nested Unit — a root is just a Unit with no parent — so nothing in the contract changes; what changes is that "the tree" is formally a **forest**, and the HMI (§3.13) may render the whole forest (all roots) or be scoped to one root. `00_System` remains single (one clock, one safety project, one alarm spine serving all roots).

### 4.3 Object / POU prefixes

| Object | Prefix | | Object | Prefix |
|--------|--------|-|--------|--------|
| Function | `F_` | | Structure | `ST_` |
| Function Block | `FB_` | | Enumeration | `E_` |
| Method (application-specific public implementation) | `M_` | | Alias type | `T_` |
| Method (non-public) | `_M_` | | Union | `U_` |
| Property (implementation) | `P_` | | Interface | `I_` |
| Action | `A_` | | GVL | `GVL_` |
| Program | `PRG_` (except `MAIN`) | | Parameter list | `PL_` |

The `M_`/`P_` prefixes apply to application-specific implementation members where the binding has methods/properties. Standard-defined logical operations/data retain their canonical contract names (`Start`, `Stop`, `Setup`, `SetMode`, `Name`, `State`, `Diagnostic`), and lifecycle extensions retain the §3.14 `OnX` names. This keeps the logical API identical across bindings while still making local extensions recognizable.

### 4.4 Variable naming

- Ordinary variables and object instances **shall not** carry type prefixes (no Hungarian). Use `Clamp1 : FB_ControlModule`, not `fbClamp1`. The type is visible in IntelliSense/mouseover.
- Interface tags (`VAR_INPUT` etc.) **shall not** be prefixed to denote declaration type or usage; group related signals into a named structure instead (`Commands.Open`, `Status.Closed`).
- Three *access-semantic* markers are retained in bindings that provide these constructs because they describe access, not data type:
  - `p` prefix for pointers, `r` for references, `i` for interface instances (`pData`, `rHal`, `iChild`);
  - leading `_` for symbols mapped to `%I`/`%Q`/`%M`, marking the HAL/hardware boundary.
- A leading `_` on internal `VAR`-block members is **permitted** (so migrated legacy code stays conformant) but **not required**.
- Local names **shall not** shadow globals.

### 4.5 Status / command naming patterns

- **Status** variable: *adjective(opt) · noun · number(opt) · past-tense verb* → `ClampClosed`, `UpperValve1Opened`.
- **Command** variable: *present-tense verb · adjective(opt) · noun · number(opt)* → `CloseClamp`, `OpenUpperValve1`.

### 4.6 Constants, enumerations, structures

- Constants: `UPPER_SNAKE_CASE`, ≤12 consecutive capitals (`BUFFER_SIZE`, `EVENT_PARTS_MISSING`).
- Structure names use the `ST_` prefix and enumeration names the `E_` prefix; redundant `Struct`/`Enum` suffixes are not used. Enums carry `{attribute 'qualified_only'}`.
- Message/event constants use the `EVENT_` prefix; specific `ERR`/`WARN`/`INF` prefixes only where the message class must be fixed.

### 4.7 Schematic priority

Where a device is named in the electrical schematic, the software **shall** use that exact name above every other rule in this section (`VLV01`, not `Valve01`).

### 4.8 Local segment and canonical qualified-identity rule

A module record's **local** service-hierarchy segment **shall** equal its local PLC
instance/schematic name. Its published `Status.Name` **shall** be the stable
qualified Fraktal identity: the root's local name, followed for each nested module
by `.` and that child's local name (for example `PneumaticPress.PressRam`). The
root's declared name is therefore both its local segment and qualified identity;
a nested child's setup assembles the qualified identity while its containing PLC
member supplies the local segment. The final segment of `Status.Name` shall equal
the record's local segment. A local module name shall not contain `.`; the dot is
reserved as the identity-path separator. This keeps diagnostics, HMI paths,
schematics and every transport projection identical without mistaking a binding
reference/handle alias for another module instance.

---

## 5. Coding Conventions

### 5.1 Declaration rules

- `VAR_EXTERNAL` is **not permitted** (it breaks modularity/reuse).
- `VAR_TEMP` only for single-scan temporaries in programs/function blocks; TwinCAT does not permit it in methods. Method-local temporaries use `VAR`; `VAR_INST` is for method variables that must persist across scans; `VAR_STAT` requires justification.
- Declaration order **shall** be: `VAR CONSTANT` → `VAR_INPUT` → `VAR_IN_OUT` → `VAR_OUTPUT` → `VAR` → `VAR_TEMP` → `VAR_INST` → `VAR_STAT`.
- Permitted attribute keywords: `RETAIN`, `PERSISTENT`, `CONSTANT` (order preserved as above).
- Identifiers **shall not** equal a binding keyword, case-insensitively. In the TwinCAT binding this includes function/operator names such as `ACTION`, `LOG`, `MIN`, `MAX`, `R`, `S`, and data-type aliases such as `DT`/`TIME`; use semantic names such as `Gate`, `AuditSlot`, `Minimum`, `Maximum`, and `DeltaMs`.

### 5.2 Formatting

- Declarations **shall** be laid out in tab-aligned columns: *name · allocation (`AT %…`) · type · init · comment*.
- Thematically related variables **shall** be grouped in a block with a header comment and a trailing blank line.

### 5.3 Structured Text style

- Keywords **shall** be UPPERCASE (`IF`, `THEN`, `END_IF`); enable editor auto-correction.
- Prefer a bounded `FOR` over `WHILE`/`REPEAT`; avoid unbounded loops in cyclic code.
- Conditions **shall** be explicitly parenthesised. A guard that protects a handle/reference dereference shall use the binding's proved short-circuit operator where available ([TC3]: `AND_THEN`/`OR_ELSE`) or nested guards; the protected access shall never be evaluated after an invalidity check fails.
- `//` comments are permitted in declaration sections.

### 5.4 Modularity and libraries

- No local library references; system and vendor libraries pinned with their dependencies.
- Each implementation unit **should** be independently testable; cross-module communication goes through declared logical capabilities/structures, not globals.

### 5.5 Implementation-language policy

To stay approachable from any background, the standard separates **framework** from **application logic**, and that split decides which IEC 61131-3 language may be used.

- **Framework language is binding-defined.** A binding **shall** implement the authoritative lifecycle, capability registry, step-chain engine, permission/interlock container, diagnostic/alarm handling, and Self-Description Service in the language/mechanism that its platform can generate, lint and test most reliably. [TC3] uses ST and OOP (`FB_init`, interfaces, methods and inheritance; TC3 §3.11). [AB] uses generated AOI/routine/UDT composition and Ladder/ST where appropriate (AB §3.14). Core conformance depends on observable behavior and machine-checkable single ownership, not IEC OOP availability.
- **Application logic is the author's choice:**

| Application logic | Languages allowed | Most natural |
|-------------------|-------------------|--------------|
| Sequences / step actions (§6) | SFC, ST, LD | SFC |
| Permissive / interlock conditions (§7.2) | LD, ST, FBD/CFC | LD |
| Manual-function release (§7.6) | LD, ST, FBD/CFC | LD |
| Alarm trigger conditions (§8) | LD, ST, FBD/CFC | LD |
| Control Module device logic (debounce, invert, simple on/off) | ST, LD | either |

Regardless of language, application logic **shall** plug into the fixed contracts — the §6.1 handshake, the §6.5 step record, and the §7.2/§8.8 condition record (index + description + `ReasonCode`) — so diagnostics work identically (§6.9). A CI/lint check **shall** enforce this. FBD/CFC are blessed only for boolean condition networks and continuous control; teams **should** keep to the smallest language set that fits, since each added language adds review and tooling burden.

When SFC is selected, it shall be a **genuine SFC implementation**: the operational logic belonging to
`Nxxx` (command issue, awaited `Done`, decision/condition evaluation, result handling, and that step's
transition result) shall be visible in that step's action/transition. A chart whose actions only publish an
`ActiveStep` number while an external ST `CASE ActiveStep OF` contains the complete sequence is an ST state
machine with an SFC visualization, not the default SFC form, and shall not be presented as the SFC reference.

### 5.6 Defensive coding (input & bounds validation)

A module **shall** validate inputs before acting on them. This is both a reliability rule (bad data faults cleanly at its source instead of crashing a downstream movement) and a security control (§14.2).

- **Command & enum inputs.** A received command **shall** be checked against the module's supported set; an out-of-range or unsupported value is rejected with a `ReasonCode` (§8.8), not silently ignored or run through a default action.
- **Array indices & bounds.** Indices into arrays, step tables, and task lists **shall** be bounds-checked before use — the reference `CheckBounds` / `F_CheckTaskIndexBounds` pattern is the canonical form. Per the drafting rules (§5, E031), the loop index is never written inside a `FOR` loop.
- **Motion & physical targets.** A motion target, force, or speed **shall** be validated against the axis/device limits (held in the CM/driver, §10.3, §10.6) before the command is issued — the `F_CheckMoveValid` pattern — so an unreachable or unsafe target is refused, not attempted.
- **External payloads.** Recipe/host (§3.8, §11.4) and carrier/part data (§3.16) are already validate-before-load; this rule generalizes the same discipline to every input boundary.
- **Fail-safe defaults.** Every `CASE`/`IF` that **selects behaviour** shall define a safe, explicit fallback (fault, hold, or refusal), never an implicit no-op that silently stalls a chain — this keeps the stall walk (§6.9) able to explain *why* nothing advanced. A guard clause is already an explicit fallback when the result is initialized fail-closed and the branch terminates with `RETURN`; an `IF` that only conditionally appends a diagnostic or performs an optional bounded update likewise needs no meaningless empty `ELSE`. `CASE` dispatchers still require an `ELSE`, because an unknown selector is an input boundary. The lint gate shall check these semantic forms rather than require syntactic `ELSE` noise on every conditional (O1/O9).

*Cross-references: §3.8/§3.16/§11.4 (payload validation), §8.8 (reason on rejection), §10.3/§10.6 (limits live in CM/driver), §6.9 (defined defaults keep diagnostics valid), §14.2 (secure-coding).*

### 5.7 Automated testing (unit & integration)

The CI gate of §5.5/§6.8 checks *static* conformance (naming, step/condition records, contract usage); it does not prove a module *works*. Because the standard's effort model is "standardise once per reusable module **type**" (§1.1 O1, §6.9), verification belongs at the same level: each reusable **type** carries an automated test suite, run against simulation, so the type can be reused or refactored (§3.11) behind a regression net instead of being re-proven by hand.

- **Framework & tooling.** Tests **shall** be written with the binding's xUnit framework and executed in CI by its headless runner, which emits JUnit-format results the merge gate consumes alongside the lint checks (§6.8) — [TC3]: TcUnit / TcUnit-Runner, TC3 §5.7. Reusable suites may ship beside their library sources, but the aggregate test runner is an executable test application and **shall not** be packaged as a runtime library or deployed with the machine application.
- **Run against the HAL, not hardware.** Suites **shall** exercise the module through its HAL in simulation (§2.6, §10), so they run on any build agent with no rig. This is the second reason simulation is mandatory (§1.1 O6): it is what makes the code testable. Each type **should** ship a small **sim plant model** (e.g. `FB_CylinderSim` with travel time) alongside its suite, shared by the unit-test framework and virtual commissioning, so tests exercise realistic dynamics instead of hand-toggled bits.
- **Sim-only force hooks.** Interlock/force test hooks (e.g. `SimForceInterlock`) **shall** exist only under the SIM build configuration and be compiled out of release builds — every §7/§9 reaction is testable, and the bypass can never ship.
- **What every module type's suite shall cover:**
  - the **handshake** (§6.1): `Execute` → `Busy` → `Done` on success; `Error`/`Aborted` on the relevant faults; idle after `Execute` drops;
  - the **first-out diagnostic** (§6.9, §8.8): a forced fault (e.g. a sim feedback withheld) yields the **expected `ReasonCode` and `SourcePath`** — the diagnosability the standard promises is itself under test;
  - the **interlocks/permissives** (§7): a dropped permissive produces the defined safe reaction and the right reason.
- **Integration tests** assemble a small sub-tree in simulation and assert the **rollup**: e.g. the Annex B clamp EM with a sim cylinder withheld must surface `CYL_NOT_EXTENDED @ ClampStation.CylB` through `GetFaultSummary` (§8.2), proving the cross-tier walk (§6.9) end-to-end.
- **Scope discipline (NG2).** Tests live in the **type's** test suite, against sim — **never** as assertions sprinkled through application step bodies. Testing therefore *protects* the low-effort objective (§1.1 O1): correctness is proven once per type, not re-checked per step or per instance.

- **Conformance test checklist (normative).** "Suite is green" is meaningful only against a defined bar. A module type **may claim conformance only when its suite covers every applicable row** below; rows are cumulative by tier. Each ✔ is at least one test case asserting the exact expected outcome (reason codes by value, paths by string):

| # | Required case | All types | Composite (EM/Unit) | Connector-fronted (§3.15) | Unit |
|---|---------------|:---:|:---:|:---:|:---:|
| T1 | Handshake completes: `Execute`→`Busy`→`Done`; idle after `Execute` drops (§6.1) | ✔ | ✔ | ✔ | ✔ |
| T2 | First-out on forced fault: expected **`ReasonCode` and `SourcePath`** (§6.9, §8.8) | ✔ | ✔ | ✔ | ✔ |
| T3 | Interlock/permissive reaction: output withheld + right reason (§7) | ✔ | ✔ | ✔ | ✔ |
| T4 | Abort path: `Aborted` reported, safe state reached, no auto-resume (§6.1, §9.3) | ✔ | ✔ | ✔ | ✔ |
| T5 | Recipe failure: invalid/partial `ParCfg` faults with `RECIPE_INVALID`, never mis-runs (§3.8) | ✔ | ✔ | ✔ | ✔ |
| T6 | Cross-tier **rollup**: child first-out adopted verbatim via `GetFaultSummary` (§8.2) | — | ✔ | — | ✔ |
| T7 | **Link loss** mid-command: adopted as module fault; bounded reconnect; **no self-resume** (§3.15) | — | — | ✔ | — |
| T8 | Mode lifecycle: unsupported mode rejected gracefully; child cascade + `Stop()` on rejection (§3.7) | — | — | — | ✔ |
| T9 | **Stall walk**: a stalled step names the awaited module *or* the first FALSE condition record (§6.9(b)) | — | — | — | ✔ |
| T10 | **Gate/report equivalence**: each Unit action accepts iff its release report is `Released`; custom mode-entry conditions are enforced and listed (§7.8) | — | — | — | ✔ |

A reusable module type is "done" when every applicable row is green in CI; anything less is not a conformance claim. Rows **T1/T4** — and the T2/T6/T7/T10 *mechanisms* (lifecycle, first-out stamping, verbatim rollup, link supervision/backoff, and the Unit lifecycle consuming its own release result) — are satisfied by the binding's authoritative framework/generator (§2.2) and proven **once** in the `fraktal-core` base suite. A generated-composition binding also proves that every concrete type contains exactly one generated lifecycle assembly. A type's suite re-proves **T2/T3/T5** and its tier rows with the type's *own* reasons and source paths; a Unit that adds mode-entry records shall exercise at least one such record through T10. Types otherwise **shall not** re-test framework-owned rows—verification, like standardization, is paid once at the level that owns the behaviour (§1.1 O1). (Worked coverage: Annex H = T1–T3, T6 for the cylinder/clamp; Annex I §I.14 = T1–T5, T7 plus the planner/resolver cases.)

*Cross-references: §1.1 (O1 per-type effort, O6 simulatable), §2.2/§2.6 (framework library, simulation), §3.11 (per-type reuse), §6.1/§6.9/§8.2 (handshake, first-out, rollup under test), §6.8 (CI gate this extends), §1.5 (conformance).*

---

## 6. Command Execution & Sequencing (flow control)

Flow control uses a PLCopen-style command/handshake model as the **baseline**. A PackML (ISA-TR88.00.02) state machine is an **optional overlay** (§6.6), not a requirement. The Unit's continuous run is itself a §6.1 command: `Start` issues it, `Stop` completes it after the current cycle, and abort/fault land in the same terminal states — one lifecycle at every tier including the top, so command timing (§8.11.4) and the reset rule need no Unit-special case (O2, O4; `FB_UnitBase`).

**Naming follows PLCopen** so the interface feels native to programmers from any platform (Siemens, Rockwell, Beckhoff, CODESYS): commands use `Execute`, `Busy`, `Done`, `Error`, `ErrorID`, `Abort`, `Aborted`. A legacy return-code transition (`_retVal = OK`) is expressed as `Done`; a legacy numeric error code is carried by the PLCopen `ErrorID` output (§8.8).

### 6.1 Command execution model (PLCopen handshake)

Every command — a CM device command or an EM command — runs through one PLCopen-style handshake. The interface signals are:

| Signal | Dir | Meaning |
|--------|-----|---------|
| `Execute` | in | rising edge starts the command; `ParCmd` latched on this edge |
| `Abort` | in | requests a controlled abort |
| `Busy` | out | command in progress |
| `Done` | out | completed successfully (`OutCmd` valid) |
| `Error` | out | command failed |
| `ErrorID` | out | numeric reason (value of `E_Reason`, §8.8) |
| `Aborted` | out | command was aborted |
| `ExecState` | out | single derived state for HMI/Self-Description Service: `E_ExecState` = `READY`/`BUSY`/`DONE`/`ERROR`/`ABORTED` |

Lifecycle: the caller checks `Done = FALSE AND Busy = FALSE` (target `READY`), writes `ParCmd`, selects `Command`, and sets `Execute := TRUE`. The module goes `Busy`, latches `ParCmd` on the rising edge, then on success publishes `OutCmd` and raises `Done`; a fault raises `Error` + `ErrorID`; an abort raises `Aborted`. The caller treats `Done` as the step transition, clears `Execute`, and the module returns to `READY`.

![Figure 7](diagrams/handshake_state.png)

*Figure 7 — PLCopen command handshake state model.*

```iecst
// Step action issuing a command to a child (PLCopen handshake):
IF NOT Clamp.Busy AND NOT Clamp.Done THEN
    Clamp.ParCmd.Force := Recipe.ClampForce;
    Clamp.Command      := E_ClampCommand.CLOSE;   // the type's own command enum (§3.2)
    Clamp.Execute      := TRUE;
END_IF
IF Clamp.Done THEN
    Clamp.Execute := FALSE;     // Done advances the step (§6.5)
END_IF
IF Clamp.Error THEN
    // divert to the chain's error handling; reason is in Clamp.ErrorID / Diagnostic
END_IF
```

**Timeout and first-out reason.** Every command **shall** carry a timeout (from `ParCfg`). While `Busy`, the module **shall** publish `OutImm.Diagnostic` (§6.9) — the *first* condition preventing completion: the first FALSE interlock/permissive (with its §7 description), or the awaited sub-result. On timeout the module raises `Error` and promotes that diagnostic to `ErrorID`. This is the Single-High / first-out rule of §8 applied per command, and it is what lets a stalled step always answer "why" (§6.9).

**`Held` — a suspended command is not a failed one.** An interlock is by definition a condition that must hold *during* motion (§7.2), and losing one is frequently expected operator behaviour rather than a defect: releasing a hold-to-run or two-hand control is the designed way to stop a movement. A module **shall** distinguish these from failures. It **shall** publish a `Held` flag, orthogonal to the terminal states, that is TRUE while the module is `BUSY`, has withdrawn the outputs of the affected function, and is deliberately not progressing because a *named* condition is unsatisfied — the ISA-88/PackML **HELD** notion. While held, the module **shall** publish that condition as its `Diagnostic` at `LOW` severity, **shall not** raise `Error`, and **shall not** open a `MANUAL_RESET` event (§8.3(b)): there is nothing to reset, because progress resumes on its own when the condition returns. A parent **shall** roll a held child up the same way it rolls up a fault (§8.2) — adopting the child's reason and `SourcePath`, as information rather than as an error — so a suspended chain explains *which* module waits on *which* condition instead of expiring into a generic stall (§6.9). `Held` is deliberately **not** an `E_ExecState` ordinal: that enumeration is transport contract (§3.10(a′)) and its ordinals **shall not** be renumbered. A condition whose loss genuinely indicates a defect (a lost feedback, an exhausted travel timeout, a process value out of range) remains a fault; HELD is for conditions the operator or the process is expected to restore.

### 6.2 Unit mode sequence (ModeHandler) — continuous step chain

A `FB_Unit` runs the **active mode's** sequence as a **step chain** that runs continuously from Start to Stop. SFC is the default and recommended implementation; ST or Ladder are permitted (§6.8) and behave identically because they share the same contract:

- the chain uses the standard step-chain contract and binding engine, whatever language implements it;
- steps are numbered in increments — `N000` init, `N100`, `N110`, …, `N999` finish — leaving gaps for insertion;
- each step's action issues commands (§6.1) to child modules; the transition to the next step is the awaited command's `Done`;
- the finish step loops back to `N000`, so the mode sequence **cycles until Stop** is requested — matching the ModeHandler "runs until Stop" lifecycle of §3.4.

```
N000 (init)            ──Done──▶ N100 (start child unit)
N100 (start child)     ──Done──▶ N110 (wait child done)
N110 (wait done)       ──Done──▶ N999 (finish)
N999 (finish)          ──Done──▶ N000  (loop)
```

![Figure 8](diagrams/mode_chain.png)

*Figure 8 — Continuous Unit mode step chain; loops until Stop.*

### 6.3 Equipment Module commands (CommandHandler)

An `FB_EquipmentModule` exposes discrete commands; each command is itself a short step chain that **completes** (it does not loop):

- individually triggerable, including manually in `MANUAL` mode, subject to release (§7.6);
- runs the matching action to `Done`, `Error`, or accepts `Abort`;
- adds **no** device logic — it only sequences CM commands through the §6.1 handshake.

### 6.4 Control Module device command (leaf)

A `FB_ControlModule` executes a primitive command bound to the HAL using the same handshake, and publishes cyclic status (`OutImm`) every scan. Example: a separator/stopper CM exposes `SEPARATE` and `OPEN_CLOSE`, sets `OutCmd.SeparateOk` when `Done`, and carries live input/output states in `OutImm`. It never sequences other modules.

### 6.5 Step-chain conventions

- Init step `N000`, finish step `N999`; user steps in increments of 10 or 100.
- Each step **shall** carry a step record — `StepNo`, `StepName`, `Awaiting` (references to the child command(s) it issued), and `ExpectedTime` — feeding the diagnostic contract of §6.9 **and the cycle-time profile of §8.11.4** — one record, two payoffs: diagnosis and measurement (the record also carries the step's `E_TimeClass`, §8.11.4(f)). `ExpectedTime` is optional and **defaults to the awaited command's timeout** (the longest, for multiple), so stall detection needs no per-step tuning; set it explicitly only when a step legitimately runs longer.
- The standard transition is the awaited command's `Done`; an `Error` diverts to the chain's error handling. Step advancement uses PLCopen status, not ad-hoc conditions.
- Chains are reusable and **shall** be side-effect-free except through the child commands they issue.
- Parallelism uses chain branches; persistent parallelism is a signal to split CMs across EMs (§3.5) rather than over-branching.
- Decisions, jumps (skip/retry), and parallel fork/join are covered in §6.10; all route through the step record so the stall walk stays valid.

### 6.6 Optional PackML overlay

PackML (OPC 30050) is **optional and binding-qualified**. A site that needs OMAC line coordination **may** additionally expose a PackML `FiniteStateMachineType` mapped from the Unit's mode + `ExecState` (for example `BUSY → Execute`, `DONE → Complete`, `ERROR → Aborted`). Conformance to this standard does **not** require it; the native `ExecState`/mode model of §6.1 and §3.4 is the default exposed through the Self-Description Service (§3.10).

### 6.7 Sequence ownership, roles, and organisation

Every chain **shall have one module owner and one writer of its step state**. Its role is one of:

1. **Mode sequence** — owned by a Unit, selected by that Unit's active mode, and continuous until
   Stop (§6.2). Each supported mode has a separately named chain behind a thin dispatch router.
2. **Command sequence** — owned by an EM (or the primitive device logic of a CM), finite, and
   externally addressable only through that module's §6.1 command handshake (§6.3–§6.4).
3. **Private sub-sequence** — a finite owner-local chain reused by one or more mode/command chains.
   It has private step state but **no module identity, public `Execute`, independent mode, or self-description
   node**; it aborts/resets with its owner and publishes progress through the caller's §6.5 step record.

A private sub-sequence shall be promoted to an EM when it needs independent commandability,
concurrency, lifecycle, recipe ownership, reuse by unrelated owners, or its own diagnostic identity.
Conversely, a forwarding sequence that contributes no parameters, release, branching, result, or
cleanup shall be collapsed; hierarchy without ownership adds effort without capability (O1/O2).

Extract a private sub-sequence when a coherent chain is used by more than one caller, owns a
non-trivial branch/cleanup path, or materially improves reviewability. Do not extract every step.
The caller remains the lifecycle owner and allocates a stable step-number window so the active private
chain remains visible in `CurrentStep`, stall diagnostics, and timing. The chain-call graph shall be
acyclic; a parent never writes a child's private step and two chains never command the same child in
the same scan.

Folders follow §4.2: Mode/Command/Sub role folders live **inside the owning module branch** when the
tool represents chains as objects. When they are methods, use distinct names and keep them under the
owner implementation unit. Lifecycle extensions (`OnInit`, `OnCommandStart`, `OnCyclic`, `OnModeChanged`,
`OnModeExit`, `OnAbort`, …) remain separate from step bodies (§3.14); their native access form is binding-defined.

### 6.8 Sequence implementation languages

A sequence **may** be written in **SFC (default)**, **Ladder**, or **Structured Text** — whichever a team knows best — per the language policy of §5.5. The language is free because the *contract* is fixed, not the syntax. Any sequence, in any of the three languages, **shall**:

- drive children only through the §6.1 command handshake;
- advance only on the standard transition (the awaited command's `Done`);
- populate the step record of §6.9 (`StepNo`, `StepName`, `Awaiting`, `ExpectedTime`).

Guidance: SFC is preferred for multi-step machine sequences (the step/transition structure is visible and self-documents the chain). ST suits data-heavy or highly conditional logic. Ladder suits simple interlock-style or maintenance-facing sequences. A `CASE StepNo OF` skeleton in ST and a step-coil pattern in LD both satisfy the same contract as native SFC steps, so diagnostics (§6.9) are identical regardless of language.

For an SFC+ST split, the SFC chart **shall be the only progression/token owner** and each non-stored ST
step action shall contain that step's application behavior: populate the step/condition records, issue or
complete the child handshake, evaluate decisions/timers, and set the transition result. An owner adapter
may run the chart and bridge framework services that the separate SFC POU cannot legally access; the
`OnCommandStart` lifecycle extension may own the reset edge. The adapter
shall not select application behavior through `CASE ActiveStep OF`, reproduce the chain, or hide commands
and waits behind one action-specific forwarding method. A token-only SFC plus an external active-step
selector is therefore non-conforming as a claimed SFC implementation, even if the chart is the only writer
of the numeric token.

A reused finite sub-sequence may retain one private step state when the owning chain invokes it as a
single, explicitly named composite step (§6.7), provided its detailed private progress is projected through
the owning Unit's normal §6.5 step record. This is reuse, not a license to hide the mode chain. The
Fraktal/TC3 pneumatic-press HOME, CHANGEOVER, and AUTO chains are the reference implementation, written as
the ST `CASE StepNo OF` skeleton on `FB_SequenceBase` (Part II TC3 §3.5); their per-step actions issue the
child handshake, evaluate waits/decisions/timers, and set the shared transition result, so the diagnostics
are identical to a native SFC per §6.8.

To keep all three languages cheap and consistent, each binding **provides**: (a) one shared step-chain engine that handles step records, the `Done`/`Error` transition, and the §6.9 diagnostic walk, so no author re-implements flow control; and (b) a template per supported language — an SFC chart, an ST `CASE StepNo OF` skeleton, and an LD step-coil rung pattern — so authors only fill in step actions. A CI/lint check **shall** verify that any sequence, whatever its language, populates the step record and advances only on the standard transition, so no language can quietly bypass the contract the diagnostics depend on.

The reference implementation of (a) is `FB_SequenceBase` [TC3]: a sequence POU extends it and receives
the active step token (`_step`), the step record (`M_Step`), condition waits (`M_Await`), run-style
pacing with a one-shot issue latch (`M_TryIssue`), declared process delays (`M_Delay`), the
part/decision/completion forwards, and the **shared transition result `_retVal : E_StepResult`**. Each
step action is `_retVal`'s only writer; at the end of the step it calls `M_Advance(OnAdvance := <next>)`
(with optional `OnJump<n>` targets for §6.10 branches), which commits the transition — advancing to the
mapped step and clearing the step-scoped latches so the next step re-arms, or holding on `NONE`. The
owning module implements `I_SequenceHost` (written once in `FB_UnitBase`) and injects itself at the
sequence's `Setup`; the host bridge carries framework plumbing only — the application's command, wait,
decision, and transition logic stays visible in each `CASE _step OF` branch (§6.8). A native graphical
SFC would place the same action bodies on its steps and read `_retVal` on its transitions; the ST
skeleton is the shipped form because it is plain reviewable text and needs no editor-generated chart XML.

**Lifetime of the shared result.** `_retVal` **shall** be a *one-scan* signal: the active step's action
writes it, the chart's transition reads it in the same PLC cycle, and it **shall** be cleared before the
next cycle's step actions run. Otherwise a result produced by one step re-fires the transition of the
step it just entered. Who performs that clear depends on who owns the transition:

- **ST chart** — `M_Advance` *is* the transition. It commits and clears in one call, so the requirement
  is met with no extra step.
- **Chart language (SFC / LD / FBD)** — the *runtime* evaluates transitions, so nothing inside the chart
  is positioned to clear afterwards. The **framework** performs the reset: a chain announces itself to its
  owner when it receives the host bridge, and the Unit base clears every attached chain's result at the
  top of each cycle, before it dispatches any step action. Clearing at the top of a scan is equivalent to
  clearing after the previous scan's transitions, and it additionally forces every step action to
  re-assert its own result each scan, making a stale `ADVANCE` impossible rather than merely unlikely.

  This is deliberately **not** a project obligation (§1.1 O1). An application that had to remember one
  call per chart would eventually forget it, and the failure — a transition firing on a result its step
  never produced — is intermittent and expensive to diagnose. The reference implementation registers the
  chain in `FB_SequenceBase.M_Attach` and drives `I_Sequence.M_BeginScan` from `FB_UnitBase`, so a project
  adding a chart in any language writes no wiring at all.

The per-scan clear **shall** reset the result only. The step-scoped helpers — the `M_TryIssue` one-shot
latch and the `M_Delay` timer — are cleared on *step change* (`M_ClearTransition`), never per scan:
re-arming them every cycle would re-issue a child command each scan and prevent any delay from elapsing.

### 6.9 Step diagnostic contract (resolving the lean-vs-diagnosable dilemma)

Lean step bodies and rich per-step diagnostics are reconciled by moving the standardization **off the steps and onto the module types** — the cost is paid once per reusable module, not once per step.

**(a) Self-diagnosing modules.** Every module **shall**, each scan, compute a single first-out reason it is not `Done` and publish it as `OutImm.Diagnostic` (fields per §8.8: `ReasonCode`, `SourcePath`, `Description`, `Severity`, `Since`) — the first FALSE interlock/permissive (with its §7 description) while `Busy`, or its timeout/fault (§6.1). Written once per module type, reused everywhere. Each module additionally **should** retain a small ring buffer of its last N first-out diagnostics (stamped per §2.7, exposed through the Self-Description Service; [TC3]: OPC UA) — shift-change post-mortem without a historian.

**(b) Self-describing steps.** Each step **shall** carry the thin record of §6.5 — `StepNo`, `StepName`, `Awaiting`, `ExpectedTime`. This is the command reference the step already sets, plus a name: near-zero extra effort, and language-agnostic (§6.8). A step that waits on a **plain condition** rather than a module **shall** additionally register each such wait as a named *condition record* — `_M_Await(n, 'Vacuum OK', VacuumOk)`, refreshed every scan — so the walk of (c) can name the first FALSE condition (*"Step N stalled → awaiting 'Vacuum OK' = FALSE"*) instead of reporting a blind `STEP_STALLED`. One line per condition closes the last non-module diagnostic gap (Annex C §C.6).

**(c) Automatic diagnostic walk.** When a chain has not advanced past a step beyond its `ExpectedTime`, one generic runtime function composes the reason with no per-step code:

> Step `{StepNo}` `{StepName}` stalled → awaiting `{Module}.{Command}` → `{Module.OutImm.Diagnostic.Description}`

The owning Unit exposes this as its current stall reason; the HMI (§3.13) shows it on the Unit's view, where the operator expects sequence state.

![Figure 9](diagrams/stall_walk.png)

*Figure 9 — Cross-tier first-out stall-diagnostic walk: Unit → EM → CM → operator.*

A stall is a **pending** reason (Low severity, published live on the Unit), not a fault: the Unit keeps waiting while naming exactly what it waits for. The *fault* path is the awaited module's `Error`, which the Unit base adopts **immediately** through the §8.2 rollup — without waiting for the stall timer — so a real failure is never delayed behind a stall guard (`FB_UnitBase`). **Outcome.** Steps stay lean; the operator gets a precise root cause; and because the answer comes from the standardized module contract (§3.12, §7, §8) rather than hand-coded step conditions, it is identical in SFC, Ladder, or ST. Standardization effort scales with the number of module *types*, not the number of steps — which is the whole point.

**(d) Raising an error the framework cannot see.** `Awaits` carries the automatic
rollup of (c), but only for a step that hands its child to the framework. A step that
decides for itself — a command inside an `IF` or `CASE`, a rule that lives in the
application — is invisible to it, and would hang until the stall guard with nothing
naming the cause. Two calls on the §6.8 base close that gap, and both are available in
every language (ST, SFC, LD):

```iecst
// a child commanded behind a guard: adopt ITS first-out, verbatim
IF M_RaiseFromChild(Source := _gauge) THEN
    _gauge.Execute := FALSE;            // §6.1 drop-reset frees the child to recover
    RETURN;
END_IF

// a rule only the application knows: the step defines the whole message
IF _measured > _parCfg.MaxDrift THEN
    IF M_RaiseCustom(Reason := PL_ProjectReasons.GAUGE_DRIFT,
        DescriptionKey := 'project.error.gaugeDrift',
        Severity := E_Severity.HIGH, Category := E_Category.PROCESS,
        LinkPath := _gauge.Name) THEN
        RETURN;
    END_IF
END_IF
```

Both return TRUE only when a fault was actually raised, so calling them every scan is
safe and the `IF ... THEN RETURN` shape reads the same everywhere. `Severity` and
`Category` are a proposal: adoption runs the §8.8 rationalization, so a **registered**
reason takes the registry's priority and category, and the caller's values survive only
for a project band code (10000+) the registry does not know — which is where a message
of a deliberately different level belongs.

The reaction is fixed and **shall not** be varied per step:

1. **Stop.** The Unit adopts the diagnostic and enters `ERROR`, so `_M_Dispatch` is no
   longer called and the chain freezes **on** the raising step — it never advances past
   a step whose command failed.
2. **Link.** The Unit stamps the §3.13 flow-chart row of the active step with
   `ErrorActive` and `ErrorSourcePath`, so the chart marks that step and drills into the
   module that actually failed — even for a step that passed `Awaits := 0`.
3. **Re-evaluate, never resume blind.** When the `ERROR` state ends, the Unit clears the
   row marks and re-arms every attached chain (`M_ResumeAfterError` → `M_ClearTransition`).
   The step-scoped latches — `M_TryIssue`'s one-shot, `M_Delay`'s timer, `M_RunSub`'s
   latch — go back to their unissued state, so the step **re-issues and re-tests its
   command** instead of resuming mid-handshake on a spent one-shot. Whether the chain
   then continues from that step or restarts from the top is the project's choice, made
   in `OnCommandStart` (§3.14); the framework only guarantees it will not skip.

A project writes none of the plumbing (§1.1 O1): registration, the row stamp, the clear
and the re-arm all live in the base. Worked example: `FB_ProbeRaiseChain` /
`FB_SequenceRaise_Tests`.

**(e) Reporting without stopping.** Not every message is a fault. A two-hand control
released mid-motion, a ram that did not reach when the step already routes to an
operator confirmation and a scrap — these are **handled** conditions with a
consequence worth recording. Adopting them would replace a designed recovery with a
hard stop; saying nothing leaves the operator with a machine that abandoned a cycle
for no visible reason. Three calls, none of which touch the exec state:

```iecst
// a rule the step states itself
_warned := M_RaiseWarning(Reason := PL_PressReasons.PRESS_TWO_HAND_RELEASED,
    DescriptionKey := 'project.warning.twoHandReleasedDuringDoorClose',
    Severity := E_Severity.LOW, Category := E_Category.PROCESS);

// a child's own first-out, published verbatim but NOT adopted
_reported := M_ReportFromChild(Source := _pressRam);
```

Guarantees:

- **Nothing stops.** `_exec` is untouched, `_M_Dispatch` keeps running, and the step
  keeps whatever branch it was going to take. This is the *whole* difference from
  (d) and **shall not** be blurred: a condition that must stop the machine belongs
  in (d).
- **It can never block a restart.** The ring entry is an AUTO_RESET come+gone event
  (§8.3(c)), so `AlarmLog.Blocking` is unaffected and the next `Start` is not gated
  on an operator reset.
- **Once per visit, not once per scan.** The base latches the message for the
  duration of the step visit and re-arms it on commit, so a step body may call it
  unconditionally every scan (§1.1 O1 — a project shall never have to remember an
  edge latch for correctness).
- **It stays visible where the operator is looking.** The active §3.13 row is marked
  with `WarningActive`/`WarningKey`, and with `WarningSourcePath` when the message is
  about a child — so a step that reports a child's failure is click-through to that
  child even though it passed `Awaits := 0`. The mark is cleared when the step is
  entered again: the chart says what happened on the last pass, not forever.

The HMI resolves a row's target most-specific-first — raised error, then reported
message, then the declared `Awaits` — and renders a message as a steady mark, never
as the error blink.

### 6.10 Branching, decisions, jumps & actions

The step model already expresses decisions and jumps directly — a transition may target **any** declared step, not only the next one — but to keep the stall walk (§6.9) reliable, every branch and jump **shall** route through the step record (`_M_SetStep`, or the SFC step itself), so `StepNo`/`StepName`/`Awaiting` always follow the active path.

**Decisions (alternative / selection branch).** A step evaluates a condition and routes to one of several successors — an `IF` choosing the next step number in ST, an alternative divergence with mutually-exclusive transitions in SFC:

```iecst
30: _M_SetStep(300, 'Measure', 'Gauge.MEASURE', T#4S, Gauge);
    IF Gauge.Error THEN _M_AdoptChild(Gauge); RETURN; END_IF
    IF Gauge.Done THEN
        Gauge.Execute := FALSE;
        IF Gauge.OutCmd.InTolerance THEN _step := 50;   // pass → skip rework
        ELSE                              _step := 40;   // fail → rework
        END_IF
    END_IF
```

**Jumps.** A jump is simply a step target that is not the next step — a forward **skip** (above) or a backward **retry**. Both are permitted; the target **shall** be a declared step in the same chain, and a jump **shall not** leave a child command running — clear `Execute` and bring affected children to a defined state before jumping.

**Bounded retry.** A backward jump used to retry **shall** be bounded by a retry counter; on exhaustion the step **shall** fault with `RETRY_EXHAUSTED` carrying the underlying child reason, so a retry never silently masks a real fault:

```iecst
40: _M_SetStep(400, 'Rework', 'Press.CYCLE', T#6S, Press);
    IF Press.Done THEN
        Press.Execute := FALSE;
        _retry := _retry + 1;
        IF _retry <= ParCfg.MaxRetry THEN _step := 30;                       // re-measure
        ELSE _M_Fault(E_Reason.RETRY_EXHAUSTED, 'Rework retries exhausted'); END_IF
    END_IF
```

**Parallel branches (fork / join).** To run actions concurrently, a step issues several child commands and advances only when **all** report `Done` — the dual-clamp step of Annex B §B.3 is exactly a parallel fork/join. Persistent parallelism is a signal to split children across separate EMs for parallel orchestration (§3.5), not to grow long parallel chains.

**Actions & action qualifiers.** Each step has one action body with two phases: a one-shot **entry** action (fire the child command on first scan of the step) and a **cyclic** body (evaluate the handshake/transition). Output behaviour **shall** be non-stored — the IEC `N` qualifier — so an output is driven only while its owning step/command is active and released when the step ends. Stored actions (IEC `S`/`R` set/reset) **shall be avoided**: they decouple an output from the step that set it and make "why is this output on?" untraceable, defeating the first-out diagnostic (§6.9). Where a state genuinely must persist across steps, it belongs in a Control Module's device logic (held through that CM's own command/state), not in a stored sequencer action.

The result is an expressive chain — decisions, skips, bounded retries, parallel joins — where every position stays visible to the stall walk and every output stays traceable to an active step.


**`M_Advance` is the declaration of a step's exits, not a convenience.** An ST branch
**shall** end with it. Assigning `_step` by hand reaches the same next step, but the
out-edges then live inside whatever conditional produced them, and the property
"every non-terminal branch has an exit" stops being checkable — the CI gate proves it
today by finding one `M_Advance` per non-terminal branch (§1.5, §5.7). Keeping the
graph in one greppable call per step is what makes a chain readable by scanning the
last line of each branch (§1.1 O2) and enforceable without dataflow analysis
(§1.1 O9). Unused jump targets are defaulted, so a step with no jump reads
`M_Advance(OnAdvance := 100);` and a step with one reads
`M_Advance(OnAdvance := 200, OnJump1 := 185);` — a jump is then visible at a glance
instead of buried among three `-1`s.

A **chart language is different and shall not be forced into it.** SFC's runtime owns
the transition, and a Ladder integer state machine moves by writing `_step` from a
rung, which is that language's native form; neither has a commit point to hang
`M_Advance` on. §6.5 is satisfied for both because `M_Step` — not `M_Advance` — is
what records the step, so the §6.9 walk and the §3.13 chart are fed identically in
every language.

### 6.11 Operator dialogs & decisions

Some sequence decisions need an **operator**, not a sensor — "remove the NOK part manually or auto-continue?", "confirm tool change". The standard defines one typed decision contract so operator interaction is uniform and never hand-built per station.

- **Typed decision request.** A step **may** raise an `ST_DecisionRequest` — prompt text, an option set, a default option, and a timeout — and wait on it. The HMI (§3.13) renders it generically from that record; the operator's choice (or, on timeout, the default) is consumed by the chain as the transition, advancing it exactly like a `Done` (§6.5).

```iecst
TYPE ST_DecisionRequest : STRUCT
    Prompt     : STRING(255);
    Options    : ARRAY[1..MAX_OPTIONS] OF STRING(64);
    Default    : INT;            // option index applied on timeout
    Timeout    : TIME;           // 0 = wait indefinitely
    SourcePath : STRING(255);    // raising module (§4.8)
END_STRUCT END_TYPE
```

- **One active decision per root.** A root Unit has one mode-chain/step-state writer (§6.7), so its base publishes one active decision slot rather than a second scheduling system. Re-presenting the same request while its step waits is idempotent; a different request arriving before the active one is consumed shall be rejected and logged, never overwrite it. A profile that genuinely permits independent concurrent decision producers may add a bounded FIFO in front of this slot, but the FIFO is an adapter and does not change the HMI contract. Each request carries its `SourcePath` so the operator sees who is asking.
- **No safety/release bypass.** A decision **shall not** override safety (§9) or manual-release (§7.6); a timeout **shall** resolve to the **safe** default, and "continue" options remain gated by the normal releases.
- **Logged.** Each decision (the request, the choice, and whether it was operator- or timeout-resolved) **shall** be logged as an event (§8.7) for audit (§14.3).

*Cross-references: §6.5/§6.10 (transitions & branches), §3.13 (generic HMI rendering), §7.6/§9 (release & safety not bypassed), §8.7/§14.3 (event logging & audit).*

---

### 6.12 Concurrent branches (parallel divergence)

A machine with two work positions that run **simultaneously and independently** —
load one while the other presses, weld two joints at once — needs more than one
active step at a time. IEC 61131-3 draws this as a *simultaneous divergence* in SFC;
this clause says what it means for the rest of the contract, and gives the form that
works in every language.

#### (a) Two forms, one contract

| | **Sub-chain fork (`M_RunPar`)** | **Native divergence (`M_Step(Branch := n)`)** |
|---|---|---|
| Available in | ST, SFC, LD — **all** | SFC / LD only (the chart draws it) |
| A leg is | its own `FB_SequenceBase` instance | a set of steps in the same POU |
| Per-leg step pointer, `_retVal`, latches | inherent — separate instances | provided by the base, keyed by branch |
| Leg written by | anyone who can write a chain | same, plus `Branch := n` on each step |
| Nests | yes, without limit | one level (a fork sits on a main line) |
| Reusable leg | yes — it is a type | no — it is drawing |

A project **should** prefer the sub-chain fork. It is the same answer §1.1 O4 gives
everywhere else: a work position is a *thing*, so make it a type and instantiate it,
rather than duplicating its steps in a picture. The native divergence stays supported
because a chart is often the clearest way to *show* two short legs, and because
existing charts use it.

#### (b) The sub-chain fork

```iecst
500: // both work positions run at once
    M_Step(StepNo := 500, StepName := 'project.step.bothPositions', Awaits := 0,
        AwaitingLabel := '', TimeClass := E_TimeClass.WORK, ExpectedTime := T#0S);
    M_RunPar(Chain := _positionA, BaseStepNo := 600, Branch := 1);
    M_RunPar(Chain := _positionB, BaseStepNo := 700, Branch := 2);
    _retVal := M_ParJoin();
    M_Advance(OnAdvance := 999);
```

`M_ParJoin` returns ADVANCE on the scan every leg run **this scan** reports `Done`.
A composite step (`M_RunSub`) **inherits** the leg of the step that runs it, so a
sub-chain inside a leg publishes its steps under that leg with nothing to declare —
the framework already knows which leg it is in, and a second place to say so is a
second place to get it wrong.
The leg list is the calls themselves, so there is nothing to register and nothing to
keep in step when a leg is added or removed (§1.1 O1). The entry latch is step-scoped:
re-entering the fork step later restarts every leg. `BaseStepNo` offsets a leg's step
records exactly as it does for a composite step (§6.5, §6.7), so the §6.9 walk and the
§3.13 chart still read one continuous chain.

#### (c) The native divergence

Legs drawn inside one POU share the function block, so the framework cannot tell them
apart. A leg step declares itself **on its own step record**:

```iecst
M_Step(StepNo := 300, StepName := 'project.step.positionBWork', Awaits := 0,
    AwaitingLabel := '', TimeClass := E_TimeClass.WORK, ExpectedTime := T#0S,
    Branch := 1);
IF M_TryIssue(Steppable := TRUE) THEN ... END_IF
_conRetVal[1] := E_StepResult.ADVANCE;     // this leg's transition result
```

and each leg's transitions read `_conRetVal[n]` where the single-threaded line reads
`_retVal`.

**Number every leg; none of them is the main line.** A simultaneous divergence has *N
equal* legs, so a two-leg fork **shall** use legs 1 and 2 — not "the main line plus
leg 1". Leaving one leg on branch 0 costs twice: the §3.13 chart draws it as an
unindented main-line row and the other as subordinate, when they are peers; and
`_retVal` comes to mean two different things depending on whether you are reading
inside the fork or outside it. `_retVal` is the line **before and after** the fork;
between them there are only legs. The join then reads every leg:

```iecst
_conRetVal[1] = E_StepResult.ADVANCE AND _conRetVal[2] = E_StepResult.ADVANCE
```

`Branch` is an input of `M_Step` rather than a call before it, so a leg cannot be
declared without recording a step, and a step cannot land on the wrong leg because a
separate declaration was forgotten (§1.1 O1). It defaults to **this chain's own leg**:
0 for a top-level chain, which is the main line, and the index the fork assigned for a
chain running as a leg — so neither a main-line step nor a leg written as its own
chain ever mentions a branch. An index outside `0..MAX_PARALLEL_BRANCHES` faults the
chain rather than silently falling back (§5.6).

> **[TC3]** `Branch` is a defaulted method input, which requires TwinCAT ≥ 3.1.4026.
> Under the legacy `FRAKTAL_TC3_4024` profile the declaration has no default, so a
> 4024 build passes `Branch := 0` at every `M_Step` call, exactly as it already does
> for `M_ResetBase` and `M_Advance` (see `Params/PL_FraktalCompat.TcGVL`).

#### (d) What the base owns

Every **step-scoped** latch is per branch: the `M_TryIssue` one-shot, the `M_Delay`
timer, the `M_RunSub` entry latch, and the §6.9(e) message latch. `M_Step` selects the
leg before any of them, so everything a step action does after its step record is
scoped to that leg. This is not an
optimisation — sharing them let one leg's issue consume another leg's, and let one
leg committing a step wipe another leg's transition result mid-motion.

The re-arm itself moved to `M_Step`, which is the one call every step of every
language makes. A chart language has no commit point to hang `M_ClearTransition` on,
so before this a chart's `M_TryIssue` fired once per chart **run** instead of once per
step.

#### (f) The chart is scoped to the running mode

Step rows are **discovered** by visit (§6.5), which is what makes the chart free to
author — but discovery has no end of its own. A Unit **shall** therefore drop its
published rows when a mode commits, so the chart shows the chain that is running
rather than the union of every chain run since power-up. Within one mode a re-run
keeps its rows, so `Visited` and `LastDuration` stay meaningful across cycles.

This is also what keeps the bound honest. A row is therefore **split by how often each
part changes**, because 98% of the original 1.16 kB row was strings that almost never
did: the live scalars stay in `SequenceSteps` (25 B), the step's text is discovered
once and served through the §3.10.2 config manifest under the same browse paths, and
the error/message text — sparse, since at most a few rows carry one — moves to a small
`SequenceAnnotations` table rather than reserving 633 B on every row for the empty
case.

Liveness is published **per concurrent leg**, not per row: a leg runs exactly one step
at a time, so an `ActiveSteps` cursor indexed by branch is ~10 entries however long the
chain is, and cheap enough to stay cyclic. What remains per row is only what a client
could **not** reconstruct by watching — `Visited`, `LastDuration`, and the error and
message marks. That boundary is deliberate: an HMI polls at a few Hz against a task at
kHz, so anything it had to accumulate from observation would drop steps shorter than
its own poll interval and lose transient faults. The chart shows what the chain did,
not what a client happened to catch (§1.1 O3).

`MAX_SEQUENCE_STEPS = 128` then costs ~46 kB per Unit instead of ~145 kB, of which
only ~1 kB is read per poll while the chart is open. That is affordable only because the rows are read on demand rather than
cyclically (§3.10); raising it further costs linearly in both, and shortening the
string fields is the lever if it ever matters. Scoping the chart to the running mode
is what keeps a Unit's actual usage near its longest single chain instead of the sum
of all of them.

#### (e) What stays singular, and why

`CurrentStep`, the §6.9 stall walk and the §8.11.4 profiler are **main-line only**. A
first-out has to name one step; letting whichever leg ran last overwrite it would make
the walk report at random. A leg is therefore timed and guarded on **its own §3.13
row** — `Active`, `Elapsed`, `TimedOut` per row — which is also what lets the HMI draw
several live steps at once and blink only the leg that overran. A leg that must raise
a *fault* still does so through §6.9(d), which stops the whole chain, as it should:
one leg failing is a failure of the step.


### 7.1 Definitions

- **Permissive** — a condition that must be **met to initiate** an action.
- **Interlock** — a condition that must be **met to initiate and maintained throughout**. If it drops mid-action, the affected output/action **shall** stop immediately. The owning module then applies the explicit classification from §6.1: an expected, operator/process-restorable condition enters **HELD** and resumes only when that same interlock returns; a defect or non-restorable loss faults. Neither classification permits motion while the interlock is false.

### 7.2 The `PermIntlk` object

Permissives and interlocks use one identical container type, **`FB_PermIntlk`** (ST, framework — written once per §5.5). Each:

- holds a set of conditions, each a Boolean where **TRUE = OK**; the object is OK only when **all** conditions are TRUE;
- carries, per condition, a **condition record** — `Index`, `Description`, `ReasonCode` (§8.8), and a `Bypassable` flag — so the *first* FALSE condition is exactly the module's first-out reason (§6.9);
- exposes: an "all OK" output, a "first failed" output (index + `ReasonCode` + description), an "at least one bypassed" output, per-condition bypass, and a clear-all.

**The condition *evaluation* is the author's choice of language** (§5.5). The container is fixed; how each condition Boolean is computed may be written in **Ladder** (the idiomatic form for interlocks — a rung of contacts), **ST**, or FBD/CFC. The author only has to drive the condition input; the container handles AllOk, bypass, and first-out.

```iecst
// ST: feed conditions into the container (each with index/description/reason set once at init)
HeatPerms.Cond[1] := TempSensorOk;          // idx 1: "Temperature sensor OK"
HeatPerms.Cond[2] := GuardClosed;           // idx 2: "Guard closed"
HeatPerms.Cond[3] := NOT EStopActive;       // idx 3: "E-stop clear"
```

```text
( Ladder: the same three conditions as rungs driving the condition coils )
  TempSensorOk───────────────────────────( HeatPerms.Cond[1] )
  GuardClosed────────────────────────────( HeatPerms.Cond[2] )
  EStopActive/(NC)───────────────────────( HeatPerms.Cond[3] )
```

Either way the gate reads the same:

```iecst
// Permissive gate at command start:
IF Start AND NOT Cm.Busy THEN
    IF HeatPerms.AllOk THEN
        // begin Heating
    ELSE
        // -> Error; HeatPerms.Diagnostic carries the first failed reason + description
    END_IF
END_IF
// Interlock maintained while Heating:
IF Heating AND NOT HeatIntlks.AllOk THEN
    // halt Heating immediately -> Error, reason = HeatIntlks.Diagnostic
END_IF
```

Because every condition carries a `Description` and `ReasonCode`, a blocked or dropped condition feeds straight into the first-out diagnostic (§6.9) and the message catalog (§8.8) — regardless of the language the condition was drawn in.

**Canonical permission/interlock container.** The logical container has a fixed public surface so every module uses it the same way. `ST_IntlkCond` carries `Defined`, stable description key, `Reason`, and `Bypassable`; the bounded condition vector carries the live Boolean values. The derived outputs are `AllOk`, `AnyBypassed`, `FirstFailed` (lowest FALSE, non-bypassed index; `0` means none), and `Diagnostic` (the first-out record, or `ReasonCode = NONE` when all pass). Its operations are `Define(Index, Description, Reason, Bypassable)`, gated `SetBypass(Index, On) : BOOL`, and `ClearBypass()`.

Conditions are declared once during binding-native setup (§3.11); the author's ST/LD logic drives `Cond[i]`; the framework evaluates the container cyclically; and the owner reads `AllOk` to gate and stamps its own `SourcePath` on `Diagnostic`. `MAX_PERMINTLK_COND` is a framework constant (default 16). [TC3] realizes the surface as `FB_PermIntlk` with methods; [AB] realizes it as bounded UDT/AOI composition. The representation shall not change the index, first-failed, bypass, or diagnostic semantics.

#### 7.2.1 Condition ownership and provenance

Each condition is owned at the **lowest module that has enough semantic context to name and act on
it**. A reusable type derives its conditions from its HAL, parameters, child contracts, and explicitly
injected semantic status—not by reaching into application globals or raw schematic I/O. The
application composition root may combine system/domain status, but it does not restate a child's
device condition. Parents aggregate the child's condition/report; they do not copy its Boolean
expression under a second description.

Cross-module collision rules, active-mode entry permissives, and other project policy belong to the
owning Unit's application branch (§4.2), preferably in a visible `Release`/`Permissives` object or
language worksheet. That project object shall expose named live condition state and append those same
records to the Unit's authoritative release report. Reusable libraries retain only device-intrinsic
conditions or explicitly injected generic policy; they shall not hide station-specific release logic.

An aggregate Boolean such as `CommonManRelease` or `AllStartConditionsOk` may exist as a convenience,
but it **shall not be the only diagnostic source**. Its constituent `ST_IntlkCond` records remain
available so the gate, first-out diagnostic, and full release report all preserve provenance. A
release expression duplicated once for execution and again for explanation is non-conformant even if
the two versions initially look identical (O1/O3).

### 7.3 Bypass handling

Bypass **shall** be per-condition and only for conditions explicitly marked bypassable. Any active bypass **shall** raise the object's "bypassed" output so the HMI and alarm system can indicate a reduced-safety/diagnostic state.

### 7.4 Granularity

Summing several discrete conditions into one permissive/interlock **shall** be avoided where reasonable: each discrete condition keeps its own description so the HMI can name the exact failed condition. Coarse summation destroys troubleshooting visibility.

### 7.5 Commissioning constants

During commissioning, manual functions and release conditions **may** be gated behind a commissioning constant (`COMM_FLAG`) so untested logic cannot drive outputs, and observe the common manual-release condition. These gates **shall** be removed (or the constant set to production) before FAT/SAT.

#### 7.5.1 Engineering gates are build constants, and they are declared

A **commissioning/engineering gate** is any deliberate, temporary departure from the production configuration: a simulation driver in place of the real one, an unverified electrical mapping held off, untested logic fenced out — and the **output-force surface of §10.5.1**. Three requirements make such a departure safe to carry in the source tree rather than in a private branch:

- **A gate is a build constant, not a runtime variable.** Each gate **shall** be a compile-time constant of the deployed program, so defeating it requires a source change plus a download — a reviewable, auditable act — and never an online write from an HMI, an engineering client, or any other data path. A gate **shall not** be exposed as a writable value, and a published mirror of a gate (for observability) **shall** have no consumer in control logic. A binding may additionally require a compiler define so the gated code is **absent** from a production build rather than merely disabled (TC3 §7.5).
- **A gate is registered, not implicit.** A station **shall** publish a bounded **engineering-gate register**: for every gate that is *active*, a stable name and a localizable description. A gate that is inactive publishes nothing, so a production station's register is empty and the surfaces the gates control are not merely disabled but **invisible** to a client (§3.9 — a disabled feature is omitted from the discovery surface, and the client pays no read cost for it).
- **A gate is annunciated for as long as it is active** (§7.5.2).

Gates **shall** be off for FAT/SAT and for production release; §14's commissioning checklist **shall** include confirming the register is empty. A deviation that outlives commissioning is a §1.5 deviation and follows §13.

#### 7.5.2 The standing engineering-gate annunciation

While **any** gate in the register is active, the station **shall** annunciate it. The requirement is deliberately shaped so the indication is impossible to lose and equally impossible to mistake for a machine fault:

- **One event per active gate**, raised through the ordinary §8.3 log with `ReasonCode := COMMISSIONING_GATE_ACTIVE` (§8.8) and the gate's own description, so each departure is named rather than summarised.
- **Lowest priority, lowest risk class.** `Severity := LOW` and `Category := SYSTEM` (§8.1). The station is not faulted and production is not impeded: a gate is a statement about *how this software was built*, not about the process or about safety, and a higher priority would displace real process alarms during precisely the phase that generates the most of them (§8.9 priority distribution).
- **`AUTO_RESET`, and therefore never blocking.** It **shall not** be a `MANUAL_RESET` event: a blocking event refuses `Start` (§8.3(b)), which would make commissioning gates prevent the commissioning they exist to serve.
- **Not clearable, and not shelvable.** No operator action closes it. An operator reset closes only `MANUAL_RESET` events (§8.3(b)), so it does not reach this one; and its rationalization record (§8.9) **shall** mark it **not suppressible**, so §8.10 shelving cannot silence it either. It closes when — and only when — its gate goes inactive, which by §7.5.1 means a new download. This is the point: the annunciation cannot be dismissed by the person most motivated to dismiss it.
- **Persistently visible, not only in the alarm list.** Because it is the lowest priority, a severity-ordered banner would bury it behind ordinary process alarms. The HMI **shall** therefore show a separate, permanent, non-dismissible indication for as long as the register is non-empty, naming the active gates (§3.13).

*Cross-references: §3.9 (a disabled feature is not published), §7.6/§7.7 (the release and access gates a commissioning gate is ANDed with, never a substitute for), §8.1/§8.3 (severity, reset classes, log), §8.9/§8.10 (rationalization and the no-shelve rule), §10.5.1 (the output-force surface this governs), §13/§14 (change control and the commissioning checklist).*

### 7.6 Manual-function release (`OnManRelease`)

Manual mode does not bypass safety. `OnManRelease` is the manual-release member of the lifecycle-extension family (§3.14), subject to the same framework-first ordering and generated/native assembly contract as the other extensions. Each module that exposes manual functions **shall** define their release conditions in one place — its `OnManRelease` reaction — following one fixed pattern: each manual function's release is the **common release** ANDed with that function's specific permissives:

```iecst
// Release conditions for this module's manual functions:
ReleaseClose := CommonManRelease AND PartPresent AND NOT AreaOccupied;
ReleaseOpen  := CommonManRelease AND SafeToOpen;
```

- `CommonManRelease` is derived by the owning Unit (ModeHandler) and is TRUE only when the module is in a mode that permits manual action and station-level conditions allow it. It is a convenience summary, not an opaque source: its common condition records **shall** be appended to every function's release report before that function's own directional/specific records (§7.2.1, §7.8).
- A manual command (§6.3) **shall** be inhibited unless its `Release<Function>` is TRUE; the same `PermIntlk` descriptions (§7.2–7.4) surface *why* a manual function is blocked.
- Being boolean release networks, these conditions **may** be authored in Ladder or ST (or FBD/CFC) per §5.5 — Ladder is the natural form, the same as interlocks.

#### 7.6.0 Show-why-blocked (release transparency)

An operator who presses a control that does not act **shall** be shown *why*. The framework therefore requires every gated action to publish, on demand, the **full set of reasons it is currently withheld** — not just the first — so the HMI can display a live "not released" panel (§3.13) rather than leave the operator guessing.

- **Rollup, not first-out.** Unlike a fault's single first-out (§6.9), a release rollup lists **every** unmet condition applicable to that action: mode/state, access (§7.7), blocking manual-reset alarms (§8.3(b)), common release records, and every FALSE function/mode-entry condition (§7.2). For Unit Start this includes the active mode's immediate command frontier, not unrelated children or future-step waits (§7.8). Each entry carries its `ReasonCode` (§8.8), human `Description`, qualified owning `SourcePath`, and `Bypassable` flag (§7.4), so two children with the same condition text remain distinguishable.
- **Per action.** The rollup is answered per gated action (Start, a specific manual command, changeover, …), because the blocking set differs. `ReleaseReport(action)` returns the report; `Released = TRUE` (empty reason list) means the action *is* released.
- **Live.** The panel updates continuously while shown, so an operator watching sees conditions clear one by one (air pressure rises → that line goes green) until the action releases — the standard's diagnosability objective (O3) applied to *pre*-action, not just post-fault.
- **No new authority.** Showing why never bypasses anything: it is read-only diagnostic data. Bypassing a bypassable permissive remains its own gated action (§7.4/§7.7).

*Cross-references: §6.9 (first-out, the fault analogue), §7.2/§7.4 (permissives & bypass), §7.7 (access), §8.3(b) (alarm blocks restart), §8.8 (reason vocabulary), §3.13 (HMI panel).*

#### 7.6.1 Manual command surface (discovery + gated entry)

A maintenance user needs to command an individual device by hand — extend a cylinder, jog an axis — without hand-written per-device HMI screens. The framework therefore gives every command-bearing module a **self-describing command catalog** and one **gated manual-command entry point**, so the HMI renders manual controls generically (§3.13).

- **Discovery.** Each Control/Equipment Module **shall** publish a command catalog: for every command it accepts, a `{Value : DINT, Label : STRING}` pair (the same values its `ExecuteCommand` accepts, §3.2; the same labels its timing rows already use, §8.11.4(a)). The catalog is published data (§3.10(a′)), so the HMI discovers the buttons — no per-type HMI code (O1). A module with no manual commands publishes an empty catalog and shows no manual panel.
- **Single manual path — MANUAL mode only.** A manual command issued from the HMI **shall** be accepted only when **all** hold: (1) the owning Unit is in `MANUAL` mode (§3.4) — the command routes *through* the module, so the module still runs and its interlocks still defend it (§7.2); (2) the function's §7.6 `Release<Function>` is TRUE; (3) the user holds the `MANUAL` access level (§7.7). There is deliberately **no** mode-bypass override: to move a device by hand, put its Unit in MANUAL first, which places the whole Unit in a known-safe state — a device must never be commanded while the rest of its Unit believes it is running automatically.
- **Routing, not bypassing.** The manual command is delivered to the module's existing command surface (§3.2) — the *same* entry the automatic sequence uses — never to the I/O directly. This is the opposite of a fieldbus channel force (§10.5.1): a manual command is *defended* by the module (interlocks, first-out, timing all apply); a channel force goes *around* it. The two **shall** be visually and functionally distinct in the HMI so the two risk levels are never confused.
- **Audit.** Every accepted manual command, and every rejected one, **shall** be logged as a §8.3 event (manual actions are always traceable).

*Cross-references: §3.2 (command surface), §3.4 (mode), §3.13 (generic HMI), §7.6 (release), §7.7 (`MANUAL` level), §8.3 (audit), §8.11.4 (command labels), §10.5.1 (contrast with channel force).*

### 7.7 User access levels (gated actions)

Access level is the **who** dimension of release, ANDed with the **machine** dimensions of §7.2–§7.6: an action executes only when its permissives/interlocks allow it *and* the active user level suffices.

**(a) Levels & actions.** Ordinal levels `E_AccessLevel` (`NONE`=0 < `OPERATOR` < `TECHNICIAN` < `ENGINEER` < `ADMIN`) and an enumerated set of **gated actions** `E_GatedAction`: `DATA_READ`, `DATA_WRITE` (ParCfg/StationCfg edits, §3.8a), `MANUAL` (manual movements), `CHANGEOVER` (`SetModel`, §3.1b), `MODE_CHANGE` (§3.4), `START_STOP`, `ALARM_HISTORY` (read, §8.3), `ALARM_RESET` (§8.3(b)), `ACCESS_POLICY` (editing this policy itself), append-only `ALARM_SHELVE` (shelve/unshelve annunciation, §8.10), and `POWER_CONTROL` (Control On/Off and power-group requests, §9.8). Ordinals are transport contract; new actions shall be appended, never inserted.

**(b) Per-station policy, PLC-authoritative and editable.** Each root Unit carries an **access policy** — a required level per gated action — held as persistent **station configuration** (§3.8a: deployment data, editable, never in a recipe). Any threshold set to `NONE` means that action needs no login; a station may therefore be **fully open** (every threshold `NONE`) or locked down per action — the deployment's deliberate choice. **Shipped default is fully open** (`NONE` everywhere): access control is never a silent lock-in (O1/O6), and the §14 commissioning checklist **shall** include provisioning an access provider and reviewing the policy. A generic HMI may edit the root's published policy, but each edit is routed through the root request mailbox and rechecked against `ACCESS_POLICY`; the policy editor is not a second authority. To prevent retained self-lockout, raising the `ACCESS_POLICY` threshold above the active session level **shall be rejected**. Per-function granularity for manual movements: `MANUAL` is the default threshold, and an individual manual function **may** declare its own higher required level in its `OnManRelease` definition (§7.6) — so "jog axis" and "open guard bypass" can differ.

**(c) Sessions & enforcement.** A per-root **access manager** holds the active level/user, authenticates through an injected **`I_AccessProvider`** — with a shipped local default (`FB_LocalAccessProvider`, persistent user/PIN table) mirroring §3.8's provider pattern — and auto-logs-out after a configurable idle timeout (`T#0S` = never). Idle time is measured since successful login or the last **accepted authenticated operator mutation**; background reads, manifest fetches, and release-report polling shall not keep an abandoned session alive. Login/logout is **data-driven** (request members in the exposed namespace, §3.10(a′)); the secret member is cleared immediately after each attempt. A transport/mailbox acknowledgement only proves that the attempt was consumed; clients **shall** determine authentication success from the resulting published `CurrentUser`, `CurrentLevel`, and `LoginFailed` state. A failed attempt shall receive explicit localized HMI feedback without revealing whether the user or secret was incorrect. Enforcement is **in the PLC** at every gated entry point (`SetMode`, `SetModel`, `Start`/`Stop`, `OperatorReset`, manual commands, decisions, power control, alarm shelving, force, and ParCfg/StationCfg writes): the HMI greys controls from the published level *and* the PLC re-checks — the client is never trusted (§14 defense in depth). Denied attempts, logins, logouts, and accepted privileged remote mutations **shall** be logged as `MESSAGE` events (§8.3), including the action identity and active user but never a secret. Thresholds are configured on the **root** the HMI addresses; framework-internal calls (the §3.7 cascade, step chains) are trusted — they only execute downstream of an already-authorized entry.

**(d) Relation to transport security.** Transport authentication/encryption remain the selected binding endpoint's job (§11.2); §7.7 is the *application authorization* layer above it. Both are required for command-capable deployments: transport identity does not grant a PLC action, and application access does not replace a secured conduit (§14).

*Cross-references: §7.6 (manual release ANDs access), §3.13 (HMI greys from published level), §3.8a (policy = station config), §8.3 (audit events), §8.9 (shelving roles now = these levels), §14 (defense in depth, commissioning checklist).*

### 7.8 Release reporting ("why is this blocked?")

An operator who presses a control that does not act **shall** be able to see *why* — never left guessing. The framework therefore requires every gated action to publish a **release report**: the complete list of currently-unmet preconditions, each with a human description and its §8.8 `ReasonCode`, so the HMI shows a full rollup rather than a single first-out.

- **Structure.** `ST_ReleaseReport` — `Released : BOOL` plus `Reasons : ARRAY OF ST_ReleaseReason` (`Description`, `ReasonCode`, `SourcePath`, `Kind`, `Bypassable`). `SourcePath` is the canonical qualified identity of the module that owns the condition; it is never a transport alias path. The report is **complete**: it lists *every* failing precondition at once (mode wrong, access insufficient, a blocking alarm active, and each failed interlock condition), not just the top one — because a fault-list that hides the second cause makes an operator fix one thing and press again fruitlessly.
- **Layered rollup sources.** A Unit **Start** report aggregates framework-common state (ready/run state, mode transition, access, blocking alarms, and control-domain readiness), one single-sourced common Start set, and any **active mode-specific immediate entry/frontier conditions** owned under §7.2.1. Modes may share the common set; they do not copy it. Conditions awaited only by a later step—part arrival, an operator confirmation, or downstream availability—belong in that step's pending record (§6.5/§6.9) and shall not over-gate Start merely because the sequence will need them later. If Start immediately commands a child, that child's applicable release records are part of the frontier and are included. A **manual command** report aggregates the Unit's common manual conditions plus mode/access and only the selected target+direction's function-specific conditions (§7.6.1).
- **One authoritative predicate; query has no side effects.** `ReleaseReport…` is a pure query, and its `Released` result is the machine gate consumed by the corresponding action after any required audited access check. The action shall not separately re-code the condition expression. Therefore `Released = TRUE` iff the action is accepted in the same stable state, and every FALSE source record is the report entry the operator sees. Pressing a blocked control commands nothing; it only surfaces the report.
- **Safety boundary.** A standard-PLC release report may include read-only safety/control-domain status to explain a block, but it never grants, bypasses, mutes, bridges, or forces a certified safety condition (§9.8).
- **HMI (§3.13).** A **persistent panel** shows the live release report of the selected Unit/action while it is blocked, each reason with its description and (where bypassable, §7.4) its bypass state; it clears when the action releases. Pressing a greyed/blocked control opens/refreshes this panel. Interlock reasons use the same `PermIntlk` descriptions surfaced everywhere else (§7.2), so the operator sees consistent wording.

*Cross-references: §3.4/§3.4.1 (mode preconditions), §7.2/§7.4 (interlocks & bypass), §7.6/§7.6.1 (manual release & commands), §7.7 (access), §8.3 (blocking alarms), §8.8 (reason codes), §3.13 (HMI panel).*

---

## 7. Permissives & Interlocks

## 8. Alarms & Diagnostics

### 8.1 Severity tiers

| Tier | Source | Alarm level |
|------|--------|-------------|
| Station Fault | top `FB_Unit` / Station Monitor | **High** |
| Unit / EM | `FB_Unit`, `FB_EquipmentModule` | **Med** |
| CM / Sequence / Alarm Instance | `FB_ControlModule`, sequencer | **Low** |
| Safety | safety zone faults | Low (rolled to station) |
| System | PLC-level faults | Low (rolled to station) |

Alarm *trigger conditions* are boolean networks like interlocks, so they **may** reuse the `FB_PermIntlk` condition pattern (§7.2) and be authored in Ladder, ST, or FBD/CFC per §5.5. Each trigger carries a `Description` + `ReasonCode`, so it feeds the queue (§8.3) and the message catalog (§8.8) the same way regardless of language.

### 8.2 Recursive parent-child rollup

Because every archetype implements `I_Module.GetFaultSummary`, fault rollup is a recursive tree walk: each module sums its own faults with its children's first-out summary and passes it upward. A Unit filters two fault classes — **sequencer faults** and **asynchronous alarms** — to decide OEE-impacting downtime, exactly as in the parent-child alarm flow, but now generated automatically by the composite structure rather than wired per level.

### 8.3 Alarm & event history (queue, duration, reset classes)

Alarm/event **come and gone** transitions **shall** enter a per-Unit event log with a defined record and lifecycle, browsable in place and streamable to a historian.

**(a) The event record (`ST_AlarmEvent`).** `ReasonCode` + `Description` + `SourcePath` (§8.8 — the same vocabulary as every diagnostic), one authoritative `Severity` (`LOW` | `MED` | `HIGH`), orthogonal `Category`, `ComeAt`/`GoneAt` plus their `ComeTimeSynchronized`/`GoneTimeSynchronized` quality (and equivalent reset/shelf quality, §2.7), **`Duration`** (monotonic come→gone difference, per §8.11.4(e)), `ResetClass`, and `State`. There is deliberately no second message/warning/error axis: annunciation, sorting, and tree tinting all use `Severity`.

**(b) Reset classes (`E_ResetClass`).** Every event is declared either **`AUTO_RESET`** — it closes by itself when its condition re-establishes (typical for low/medium transient events) — or **`MANUAL_RESET`** — after the condition clears it remains **blocking** until a deliberate operator reset (typical for high-severity faults). Lifecycle: `ACTIVE` (come) → on condition-gone: `AUTO_RESET` closes immediately with `Duration`; `MANUAL_RESET` enters `WAIT_RESET` (still blocking) → operator reset closes it (`ResetAt` stamped). A `MANUAL_RESET` event **shall never** self-close (§9.3), and the Unit's `Start` **shall** be refused while any such event is `ACTIVE`/`WAIT_RESET`.

An operator reset **shall** close a `MANUAL_RESET` event from **either** `ACTIVE` or `WAIT_RESET` — it is a deliberate external action, not a self-close, so the `WAIT_RESET` stage is where an event *waits* for the operator, never a precondition for being allowed to reset it. Requiring `WAIT_RESET` would make the reset a guaranteed no-op for the one class of event it exists to clear: whenever the blocking condition can only be re-established by running the machine — a permissive that must hold *during* motion, such as a two-hand control held through a press stroke — `ACTIVE` cannot be left, `Start` is refused because the event blocks it, and the operator has no action left. An event closed while its cause is still live is **re-raised by its owner on the next scan** through the automatic capture of (c), so this clears the *latch* and never the *condition*: the interlocks of §7.2 are untouched, no output is restored, and the release report of §7.8 still refuses `Start` and still names the live condition. A reset **shall** therefore also release the latched control state that the event was reporting — the Unit's own run command and any child command its suspended sequence had issued (§6.1) — because closing the event while those remain asserted leaves the equipment unrecoverable for the same reason. Recovery modes (HOME and equivalents) **shall** be reachable after one such reset, under the §7.7 authority for `ALARM_RESET`.

**(c) Automatic capture, manual raising.** The Unit base **shall** capture module faults automatically — entering `ERROR` raises a `MANUAL_RESET` event carrying the rolled-up first-out severity and diagnostic (§8.2, §6.9); leaving `ERROR` marks it gone. Application code raises other events explicitly with a chosen severity/reset class (one call, §8.7 `EVENT_` constants). Nothing is double-authored: the event *is* the diagnostic plus lifecycle.

**(d) Discovery & retention.** Each Unit publishes its **active list** and a fixed-size **closed-event ring** (newest-first, `Truncated` on overflow) through the Self-Description Service (§3.10) — the HMI discovers history with zero station code (§3.13), including each event's duration. In-PLC retention is bounded by design; **full history** is the historian's job: a logical **`I_EventSink`** capability is invoked at come and at close so a database/historian adapter (OPC UA A&C, SQL, MES) subscribes without touching the log. Sink realizations are deployment choices. The record path **shall** be the module's canonical path (§4.8), so HMI, historian, and MES share one address.

**(e) ISA-18.2 mapping.** `ACTIVE`/`WAIT_RESET`/closed correspond to Unack-Alarm/RTN-states of ISA-18.2 §8.9; the reset here doubles as acknowledge for the blocking class, keeping one operator action instead of two (rationalization per §8.10 decides which reasons are alarms vs logged-only events).

### 8.4 Single-High strategy

To suppress nuisance alarms, independently controlled equipment **shall** fault only on a valid downtime event, and that event **shall** carry one descriptive **High** alarm raised at the station's top level (reported by the Station Monitor). Lower tiers carry Med/Low alarms that roll up; only the top emits the single High that drives downtime reporting.

### 8.5 Station Monitor & OEE

The Station Monitor **shall** capture faults from any module in its OEE reporting area on a **first-out** basis to attribute downtime to true root cause, and **shall** integrate Safety and System alarms. OEE/performance metrics derive from the same rollup.

#### 8.5.1 OEE model & trend samples

OEE is a **derivation from contracts the standard already has** — no new instrumentation in the modules, only accounting in the Unit:

- **Time classification.** Each scan, the Unit attributes elapsed time to exactly one bucket: **run** (`BUSY`), **down** (`ERROR`, or a blocking alarm active §8.3), or **idle** (everything else). Buckets are monotonic accumulators since the last reset.
- **The three factors.** *Availability* = run ⁄ (run + down) — idle time is tracked and published but excluded from A (no demand ≠ downtime; a deployment that schedules production differently re-derives A from the published buckets). *Performance* = (ideal cycle time × total count) ⁄ run time, computed **only when an ideal cycle time is configured** (§3.8 — per-model, since a different product may cycle differently). *Quality* = `GoodCount` ⁄ (`GoodCount` + `NokCount`) (§8.11). **OEE = A × P × Q**, and each factor carries a validity flag: an unconfigured or division-by-zero factor is **invalid and omitted from the product — never assumed 100 %** (O7: the UI must not flatter).
- **Trend samples.** The Unit pushes an OEE sample (A, P, Q, OEE + validity) into a bounded ring at a fixed period, giving the HMI a recent-history series with zero historian dependency. Long-horizon trending is the historian's job (§8.3 `I_EventSink` / external), not the PLC's.
- **Reset.** `ResetOee` clears the accumulators and ring — a gated action (§7.7 `DATA_WRITE`), audited (§8.3). Typical use: shift start; a deployment automates it from its scheduler.
- **HMI (§3.13).** Units render an OEE facet: the three factors + OEE as percentages with **exception-based colouring** (muted when at/above target, colour only below — ISA-101 style), and a **sparkline** from the sample ring so the operator sees *direction*, not just a snapshot. Invalid factors render as "—", never 100 %.

*Cross-references: §3.8 (ideal cycle per model), §6.1 (`BUSY`), §8.3 (blocking, audit, historian), §8.11 (counters, timing), §7.7 (reset gating), §3.13 (rendering).*

### 8.6 Safety & System alarms

- **Safety alarms**: faults of safety devices in the zone(s) affecting the station (see Safety section, tracked separately). Mapped through the standard Safety-to-Standard alias signals (`AllEstopsOk`, `AllSafetyOk`, …).
- **System alarms**: PLC-level conditions impacting execution (fieldbus, IPC diagnostics, task health).

### 8.7 Event / message constants

Messages **shall** be defined as `EVENT_`-prefixed constants and raised with an explicit class (e.g. `WARNING`, `SOFTERROR`, error). Class selection **shall** reflect operational impact, and each event **shall** carry a description suitable for the HMI and the alarm database.

### 8.8 Reason codes & message generation

Legacy handler frameworks return a bare numeric error code (e.g. `-649231`) that the HMI maps to a message. Numeric codes are retained **as a localization/transport key**, but a bare magic number on the return value is opaque in source, conflates *what* failed with *where*, and depends on an external catalog that drifts. This standard keeps the benefits and removes the weaknesses, using PLCopen vocabulary for familiarity:

- **`_retVal` is retired.** Control flow uses the PLCopen `Done` / `Error` / `Aborted` status (§6.1, §6.5); these carry **no** message codes.
- **The number is the PLCopen `ErrorID`.** On `Error`, a module raises `ErrorID : DWORD` — the value reaching the HMI — sourced from a **namespaced enum** `E_Reason` (e.g. `E_Reason.PART_PRESENT_MISSING`) that reads meaningfully in source. `ErrorID := TO_DWORD(ReasonCode)`; never a hand-typed magic number. Codes are **positive** (PLCopen `ErrorID` is unsigned); a boundary mapping can negate for a legacy historian if ever required.
- **The full reason is a structured record.** The `Diagnostic`/event (§6.9, §8.2) is `ST_Diagnostic`:

```iecst
TYPE ST_Diagnostic :
STRUCT
    ReasonCode  : E_Reason;     // named reason; ErrorID = TO_DWORD(ReasonCode)
    SourcePath  : STRING(255);  // canonical path of the module/condition (§4.8)
    Description : STRING(255);  // localization key (from PermIntlk/module, §7)
    IoTag       : STRING(80);   // exact, untranslated electrical/schematic tag; '' if N/A
    IoAddress   : STRING(80);   // terminal/channel locator; '' if N/A
    Severity    : E_Severity;   // LOW | MED | HIGH (§8.1)
    Category    : E_Category;   // PROCESS | SAFETY | SYSTEM
    Since       : DT;           // first-out timestamp
    TimeSynchronized : BOOL;    // quality of Since (§2.7); FALSE = display as untrusted
END_STRUCT
END_TYPE
```

A generic code plus `SourcePath` renders instance-specific — *"Clamp3: part present missing"* — so no unique global number per device is needed. When a fault implicates a particular physical channel, `IoTag` **shall** carry the exact tag from the project's approved I/O/electrical list and `IoAddress` **shall** carry its physical locator. These are structured identity, not display prose: clients shall not translate or rewrite them. The localized `Description` explains the failure while the tag lets maintenance find the device on the schematic, terminal, and machine label. Diagnostics not attributable to one channel leave both fields empty; a multi-channel plausibility fault may carry a stable delimiter-separated tag/address list while the fieldbus projection highlights every implicated channel.

- **Code bands (partitioned so codes never collide):**

| Band | Range | Owner |
|------|-------|-------|
| System | `1 – 999` | PLC, task, fieldbus, IPC |
| Safety | `1000 – 1999` | safety devices / zones |
| Framework (common) | `2000 – 9999` | shared reasons: timeout, awaiting child, permissive not met, interlock dropped, recipe invalid… |
| Per module-type | `10000 +`, one contiguous block per type (100-wide for CM types within `10000–10999`; EM types from `11000` in 1000-wide blocks) | type-specific reasons |

`0` = `NONE` (no reason). Module-type codes are relative to the type; `SourcePath` disambiguates instances.

- **Band extensibility (implementation rule).** IEC 61131-3 enums cannot be extended across libraries, so the framework's `E_Reason` declares the **framework bands only** and **shall not** be compile-strict: a module type declares its band codes (`10000+`) as named constants in its own library and assigns them into `ST_Diagnostic.ReasonCode`/`_M_Fault` directly. The **registry below — not the enum — is the collision authority**, and the generated catalog is built from the union of the framework enum and the registered type bands. This keeps one number space with per-type bands (O3, O4) implementable on any platform's enum semantics (O8) without a central enum every type edit would touch (O1).

- **Reserved sub-ranges & registry.** The `E_Reason` enum is the single source of truth; to keep allocations visible across sections, the bands are sub-divided and the codes introduced by this standard are registered here. A new reason **shall** be added to the appropriate sub-range and recorded below so codes never collide:

| Band / sub-range | Reasons |
|------------------|---------|
| System `10–21` | controller & clock health (§8.12, §2.7): `TASK_OVERRUN`=10, `TASK_JITTER_HIGH`=11, `CPU_LOAD_HIGH`=12, `MEMORY_LOW`=13, `IPC_TEMP_HIGH`=14, `FIELDBUS_MASTER_FAULT`=15, `DC_SYNC_LOST`=16, `TIME_SYNC_LOST`=17, `UTILITY_DEVIATION`=18 (§8.14), `IPC_FAN_FAULT`=19, `STORAGE_HEALTH_LOW`=20, `CONTROLLER_METRICS_UNAVAILABLE`=21 |
| Framework `2000–2009` | common flow reasons: `TIMEOUT`=2001, `PERMISSIVE_NOT_MET`=2002, `INTERLOCK_DROPPED`=2003, `RECIPE_INVALID`=2004, `STEP_STALLED`=2005, `RETRY_EXHAUSTED`=2006, `CYCLE_TIME_DEGRADED`=2007 (maintenance event, §8.11.4/§8.12), `UNSUPPORTED_COMMAND`=2008 (input outside a type's declared command set, §5.6) |
| Framework `2010–2019` | external device / link supervision (§3.15): `LINK_TIMEOUT`=2010, `DEVICE_NOT_READY`=2011, `DEVICE_PROTOCOL_ERROR`=2012 |
| Framework `2020–2029` | traceability / part context (§3.16): `CARRIER_READ_FAILED`=2020, `CARRIER_WRITE_FAILED`=2021, `PART_ID_MISMATCH`=2022, `RESULT_RECORD_REJECTED`=2023 |
| Framework `2030–2039` | engineering/commissioning build gates (§7.5): `COMMISSIONING_GATE_ACTIVE`=2030 — one LOW/SYSTEM, non-clearable, non-shelvable event per active gate |
| Framework `2900–2909` | framework self-test reasons, never raised in production (§5.7 base suite): `TEST_FAULT`=2901 |
| Per module-type `10000+` | type-specific, one contiguous block per type — 100-wide CM sub-blocks within `10000–10999`, EM blocks from `11000` (registered: separator CM `10001–10005`, cylinder CM `10101–10103`, **basic cylinder CM `10110–10116`** (same 100-block; production variant of the cylinder type), axis CM `10201–10204`, robot CM `10301–10310`, **TCP/ASCII device CM `10401–10406`** (§3.15.1a base; device profiles extend within `10401–10499`), **power-group CM `10501–10502`** (§9.8), **air-pressure monitor CM `10601`**, clamp EM `11001`, per Annexes A–B, G, I) |

`TIME_SYNC_LOST` is a System-band code (17) because it is annunciated as a System-category alarm (§2.7, §8.6), even though the clock is configured in §2.

- **One catalog, generated from the numeric authorities.** The code→message catalog — with `{source}` / `{value}` placeholders for localization — **shall** be generated from the Core `E_Reason` definition plus every registered type-band parameter list, so portable framework codes and additive library bands compose without duplicating their numbers. Rationalization joins by the named symbol (§8.9), not by restating the number. The HMI localizes by `ErrorID`/`ReasonCode`; absent an entry it falls back to `Description`.

In short: keep the number as the PLCopen `ErrorID` for transport and localization, source it from a named enum, carry the full reason in `ST_Diagnostic`, and always attach the source path.

### 8.9 Alarm philosophy & rationalization

§8.1–8.8 give the alarm **mechanics**; this section adds the **governance** that ANSI/ISA-18.2 (and its international form IEC 62682) require, so the cell's alarms are actionable rather than a flood. Every alarm the standard can raise — each `E_Reason` / `EVENT_` constant — **shall** be *rationalized*, not merely defined.

- **Alarm philosophy.** A project **shall** adopt a short alarm-philosophy document that fixes the priority scheme, the operator-response expectation per priority, and the rules for suppression/shelving below. The `E_Severity` tiers (§8.1) map to that priority scheme.
- **Rationalization record.** Each registered reason **shall** carry, in one machine-readable symbol-keyed registry joined to the numeric catalog (§8.8): a **priority** (derived from consequence × required response time, not assigned ad hoc), a one-line **operator action** ("what do I do about this?"), an **alarm class** (PROCESS / SAFETY / SYSTEM, from `ST_Diagnostic.Category`), and a flag for whether it is **suppressible/shelvable**. Generated PLC and HMI projections **shall** reject missing, unknown, duplicate, or conflicting entries. An entry without an operator action is an **event**, not an alarm, and **shall** be logged (§8.3) rather than annunciated — this is the primary lever against alarm overload. Project/application bands may extend the catalog through a complete validated record, but shall not override generated standard metadata.
- **Priority distribution.** The rationalized set **should** approximate the ISA-18.2 distribution guidance (the large majority Low, few High) — a station whose alarms are mostly High has not been rationalized.
- **One reason, one priority, everywhere.** Because priority lives in the generated catalog keyed by `ReasonCode`, the same reason carries the same priority on HMI, historian, and MES — no per-screen reclassification.

*Cross-references: §8.1 (severity), §8.3 (queue/log), §8.8 (catalog from enum), §13 (changes to the alarm set follow MOC).*

### 8.10 Alarm governance and optional performance profile

Rationalization is set once. Shelving and management of change below are part of
the base contract. Long-window nuisance/flood analytics are an optional
**Alarm-performance profile** because their correct scope is normally one cell,
line, or site historian—not one duplicate rolling window beneath every root Unit
(O1/O4). A deployment shall state whether this profile is claimed and name its
single owning aggregator.

- **Flood & nuisance handling (profile).** When the Alarm-performance profile is claimed, the owning Station Monitor or external historian **shall** debounce chattering annunciation according to a rationalized minimum-on/fleeting filter per reason and **shall** detect alarm **floods** (rate over a configured threshold in a rolling window). It shall retain every underlying event and shall never suppress control, blocking, first-out, or history semantics; it may replace repeated audible/banner annunciation with one conspicuous flood indication plus drill-through to the members.
- **Shelving / suppression.** Only reasons flagged suppressible (§8.9) **may** be shelved, and only by an authorized role (§7.7 level, transported per §11.2). A shelf **shall** auto-expire (time-bounded, with auto-unshelve) and **shall** itself be logged. **Shelving suppresses annunciation only — never control**: a shelved blocking alarm (§8.3(b)) still blocks Start, interlocks (§7.2) are untouched, and release reports (§7.8) still list the condition; the HMI merely stops shouting about it (banner/list de-emphasis). Safety-category alarms (§8.6) are **never** shelvable regardless of flags. An alarm with no rationalization record (§8.9) is not shelvable — rationalize first, then shelve. Design-suppression (e.g. downstream alarms suppressed while a Unit is intentionally stopped) **shall** be defined in the philosophy, not improvised.
- **Performance KPIs (profile).** When the profile is claimed, its owner **shall** expose alarm-rate (per 10 min), standing-alarm count, and **stale**-alarm count (active beyond a configured long threshold) as Self-Description Service values, so alarm health is measurable against ISA-18.2 targets. It consumes the complete §8.3 event stream through the bounded ring and/or `I_EventSink`; application modules shall not reimplement these aggregates.
- **Management of change.** Adding, removing, or re-prioritizing an alarm **shall** follow the change process of §13; because alarms are generated from the `E_Reason` enum and catalog, a diff of those artifacts is the alarm MOC record.

*Cross-references: §8.4 (single-High), §8.5 (Station Monitor/OEE), §11.2 (roles for shelving), §13 (MOC).*

### 8.11 Performance capture (cycle time, counts, machine states)

§8.5 derives OEE from the fault rollup, but OEE also needs a **measured cycle time**, a **counted reject source**, and a **standardized machine state** — none of which §8.5 specifies. This section defines that capture so OEE is computed from real signals, not inferred. The capture is written once into the Unit and Station Monitor; it is not re-implemented per station.

### 8.11.1 Cycle markers & throughput

The Unit mode chain (§6.2) already has defined boundaries; performance capture hangs off them with no new sequencing:

- A **cycle-start** marker fires on the first productive step of the AUTO chain (`N100`), a **cycle-complete** marker on the finish/loop step (`N999`). The Station Monitor derives `CycleTime`, `LastCycleTime`, and a rolling `MinCycleTime` from these markers.
- The Unit **shall** expose **blocked** (downstream cannot accept) and **starved** (upstream has not delivered) as distinct signals, so lost time is attributed to the line, not charged to the station as a fault.

### 8.11.2 Counts

- The Unit **shall** maintain `GoodCount`, `NokCount`, and `ReworkCount`, incremented once at the part outcome. With traceability enabled this occurs at `EVENT_PART_PROCESSED` (§3.16) from the part `Verdict`; when the optional carrier is absent, the owning sequence uses the framework outcome helper instead of fabricating a part record.
- A NOK **shall** be attributed by its non-`NONE` first-out `ReasonCode` (§8.8) — the same reason vocabulary as a fault — so scrap is analysable by cause without a separate reject-code scheme. The owning NOK helper **shall** increment the counter and emit the fixed §11.6 `NOK` host event as one operation; `PartUid` is empty when traceability is not configured. Counters reset on a deliberate, logged action (shift/changeover), never silently.

### 8.11.3 Standardized machine state for OEE

The Station Monitor (§8.5) **shall** classify the station, every scan, into one fixed state set, from which Availability / Performance / Quality follow directly:

| State | Condition | OEE bucket |
|-------|-----------|------------|
| `PRODUCING` | AUTO chain cycling, not blocked/starved | uptime |
| `IDLE` | ready, no work present | — |
| `BLOCKED` / `STARVED` | §8.11.1 signals | external loss |
| `DOWN` | a fault holds the Unit (§8.2) | downtime (first-out cause) |
| `CHANGEOVER` | `CHANGEOVER` mode active (§3.4) | planned |
| `STOPPED` | operator/parent Stop | planned |

This state set maps one-to-one onto the PackML state/admin model (§11.7) and onto the host events (§11.6), so the same classification feeds local OEE, the line controller, and MES without re-derivation.

### 8.11.4 Step & command timing capture (the cycle-time profile)

§8.11.1 measures the cycle *total*; diagnosing a slow or drifting cycle needs the *breakdown* — which step, which module, which command. The standard therefore captures timing at the two places every cycle already passes through, so the profile costs the application author nothing (O1) and explains time the way the stall walk explains stalls (O3):

**(a) Command timing — in the module lifecycle (shall).** The authoritative module lifecycle (§2.2) **shall** measure every command's execution time (BUSY entry → DONE/ERROR/ABORTED) and maintain, per command id, a timing row `{Id, Label, Count, Last, Minimum, Maximum, Avg}` published in the module's standard `Timing` structure. This is written once in the framework/generator; a type identifies its commands with one binding-native declaration and adds no other timing code.

**(b) Step timing — from the step record (shall).** The step-chain base **shall** feed a **cycle profiler** from the step record the chain already maintains for diagnostics (§6.5/§6.9): each `_M_SetStep` closes the previous step's duration, and the finish step (the §8.11.1 cycle-complete marker) closes the cycle. The profiler publishes the last completed cycle and per-step aggregates (`Count/Last/Minimum/Maximum/Avg` keyed by `StepNo`). Application steps add no duplicate timing code.

**(c) Generic HMI rendering (shall).** Because both structures are fixed framework types exposed through the Self-Description Service (§3.10), the HMI **shall** render them generically for any Unit: a cycle waterfall, a Pareto of per-step `Avg`/`Maximum`, and drill-through to module command timing. `ExpectedTime` is drawn against each step so guard-versus-actual is visible.

**(d) Degradation is data, not downtime (should).** A step or command whose `Avg` drifts beyond a configured band above its baseline **should** raise a **maintenance** event via the condition-monitoring path (§8.12, Low severity, `ReasonCode := E_Reason.CYCLE_TIME_DEGRADED`) — creeping cycle time surfaces for planning before it becomes a stop, and the event names the exact step/command (O3).

**(e) Bounds & clocks.** Profile and stats arrays are fixed-size with a `Truncated` flag — capture **shall never** allocate or grow at runtime. Durations are taken from the platform's monotonic millisecond clock, wall-clock stamps from the synchronized clock (§2.7), so profiles align across tiers and stations ([TC3] sources: TC3 §8.11). Aggregate resets are a deliberate, logged action per §8.11.2, never silent.

**(f) Time classification — the real cycle time (shall).** Every profiled step carries a **time class** (`E_TimeClass`): `WORK` — the default — or a wait class: `WAIT_UPSTREAM` (starved: awaiting the next pallet/part/material), `WAIT_DOWNSTREAM` (blocked: awaiting outfeed/downstream take-over), `WAIT_OPERATOR` (a §6.11 decision or manual intervention), `WAIT_EXTERNAL` (host/MES/tool response, §3.15/§11.6). A step declares its class **in the step record it already has** — one enum argument on the *wait* steps only (`_M_SetStep(…, TimeClass := E_TimeClass.WAIT_UPSTREAM)`); every undeclared step is `WORK`, so the common case costs nothing (O1). The profiler accumulates per-class totals (`ByClass`) and publishes **`WorkTime` — the real cycle time** — and `WaitTime` alongside `Total`, so comparing against the design cycle time and OEE performance accounting use work-only time *by definition*, not by after-the-fact estimation (O3). The wait classes are the **per-step attribution of §8.11.3's Starved/Blocked**: `WAIT_UPSTREAM`/`WAIT_DOWNSTREAM` totals reconcile with the Unit's Starved/Blocked accumulators, and the Unit base **derives** its live `Starved`/`Blocked` status from the current step's wait class — one declaration, two views that cannot disagree (`FB_UnitBase`). A wait class **shall not** be used to hide process slowness: only genuine external waits qualify — that is what keeps `WorkTime` honest.

*Cross-references: §6.2 (mode-chain boundaries), §3.16 (`Verdict`/part events), §8.5 (Station Monitor/OEE), §8.8 (reason vocabulary), §8.11.3 (Starved/Blocked ↔ wait classes), §8.11.4/§8.12 (timing capture & degradation events), §11.6/§11.7 (host & PackML mapping).*

### 8.12 System health & condition monitoring

§10.5 already requires fieldbus/IPC diagnostics to surface as System alarms. This section **generalizes** that to a controller-health and condition-monitoring contract, so degradation is visible and trendable before it becomes downtime.

- **Controller health.** The station **shall** monitor primary-task cycle time, **jitter**, and overruns; CPU and memory load; and, where the hardware exposes them, IPC temperature/fan and storage health. Threshold breaches raise System-category alarms (§8.6) with System-band reason codes — `TASK_OVERRUN`, `TASK_JITTER_HIGH`, `CPU_LOAD_HIGH`, `MEMORY_LOW`, `IPC_TEMP_HIGH` — and the live values **shall** also be exposed through the Self-Description Service for trending/predictive maintenance, not only as pass/fail alarms.
- **Fieldbus & device health.** Fieldbus master state, lost frames, slave errors, and distributed-clock sync (`FIELDBUS_MASTER_FAULT`, `DC_SYNC_LOST`) surface per §10.5 ([TC3]: EtherCAT specifics, TC3 §10); smart-device links (§3.15) contribute their heartbeat/last-seen. These are System/Low events that **shall not** be silently swallowed.
- **Condition-based maintenance.** A Control Module or device connector **may** publish condition signals — actuation/cycle counts toward a service interval, drive load/temperature, vacuum/pressure trend — as **maintenance** events (Low severity, §8.1), distinct from production faults: they inform planning, they do not stop the cycle. Service thresholds are `ParCfg` (§3.8).
- **Warning vs. alarm.** Where a distinct approach threshold is configured, approaching a limit raises a Low/Med warning and exceeding it raises the alarm; otherwise the configured limit produces the single Low System event. The two use `Severity` (§8.1) on the same reason, so trending and annunciation share one source without inventing a mandatory second threshold for every metric.

The platform-neutral input is `ST_SystemHealthInput`: task, controller, IPC,
fieldbus/DC, and `ST_TimeQuality` samples with an explicit availability flag for
each optional group. Station thresholds and requirements live in schema-first
`ST_SystemHealthParCfg`. A root Unit publishes the validated bounded copy as
`SystemHealth : ST_SystemHealthStatus`; `Present=FALSE` means the profile was not
configured, while `Present=TRUE, Healthy=FALSE` means one or more required probes
are unavailable or outside limits. A reusable `FB_SystemHealthPublisher` (or
equivalent binding implementation) shall own the threshold evaluation and the
come/gone edges for the registered Low/System/AUTO_RESET events. Applications
inject platform measurements; they shall not reproduce threshold/alarm logic per
station. Several root Units on one PLC may mirror the same platform sample into
their own bounded status/alarm scope so each independently assigned HMI sees the
health affecting that Unit.

*Cross-references: §2.3 (task/watchdog sizing), §2.7 (time sync for health timestamps), §10.5 (fieldbus diagnostics — the specific case this generalizes), §3.15 (link health), §8.1/§8.6 (severity, System alarms).*

### 8.13 Signal tower (stack light) mapping

A station's signal tower (and horn) **shall** be driven from the existing state and alarm model, in one place, so no station hand-wires lamp logic.

- **Single mapping.** The lamp/beacon pattern is a fixed function of the §8.11 machine state and the highest active alarm severity (§8.1/§8.2): e.g. **red** = `DOWN`/active fault, **amber** = warning or `BLOCKED`/`STARVED`/`CHANGEOVER`, **green** = `PRODUCING`, **blue/white** = operator action required (a pending decision, §6.11, or manual step), **off** = `STOPPED`. Exact colours and the horn follow the site convention (IEC 60204-1 / ANSI), but the **mapping is defined once** and reused.
- **Driven by rollup, not by station code.** Because state and severity already roll up the tree (§8.2, §8.5), the tower reads the station summary directly; adding or changing a module never touches tower logic.
- **Lamp test.** The station **shall** provide a lamp-test function (operator-triggered) that drives every lamp/horn for a fixed interval to verify the device, then returns to the mapped state.

The reusable mapping publishes semantic outputs
`ST_SignalTowerOut := {Red, Amber, Green, Blue, White, Horn, TestActive}`; only the
project Hardware Driver maps those semantics to electrical channels. Site choices
(`OperatorUsesWhite`, `HornOnHigh`, bounded `LampTestDuration`) are a schema-first
`ST_SignalTowerParCfg`, never station-specific `IF` logic. A root Unit publishes
`SignalTower`, derives its inputs from its authoritative `MachineState`, active
alarm table, and decision state, and accepts remote lamp test only through the
acknowledged mailbox under the `MANUAL` gate while the Unit is not `BUSY`. The test
duration shall clamp to 30 seconds or less and self-clear even if the client
disconnects.

*Cross-references: §8.1/§8.2 (severity & rollup), §8.11 (machine state), §8.5 (station summary), §6.11 (operator-action signal).*

### 8.14 Utility & energy monitoring (optional)

A station that meters its utilities — electrical power, compressed air, coolant/water — **may** expose that consumption as a self-describing branch, so energy and utility use are visible for cost, sustainability (ISO 50001), and leak/anomaly detection. This is **optional**: a station without metering simply omits the branch, so the feature never burdens a simple station (§1.1 O1).

- **Model.** Per-station (and optionally per-module) **instantaneous** and **accumulated** quantities are published through the Self-Description Service — electrical kWh, compressed-air Nm³, coolant L — each with the synchronized timestamp (§2.7). When the binding-qualified OPC 34100 projection is claimed, these same values **shall** map to the OPC UA for Energy Consumption Management information model; absence of that optional projection does not invalidate the native energy profile (§1.5).
- **Performance indicators.** Combined with the good/NOK counts (§8.11), the Station Monitor (§8.5) **may** derive energy-per-part EnPIs (e.g. kWh per good part) and publish them north-bound (§11.9) for the plant energy/UNS layer.
- **Anomaly / leak detection.** A consumption that drifts from its learned baseline (e.g. a rising idle-air draw) **may** raise a **maintenance** event via the condition-monitoring path (§8.12, Low severity, `ReasonCode := E_Reason.UTILITY_DEVIATION`) — informing planning, never stopping production.
- **Not a safety or interlock function.** Utility *availability* that must gate operation (air-pressure-OK, coolant-flow-OK) remains a permissive/interlock (§7) or a safety alias (§9); §8.14 is **measurement and monitoring only** and **shall not** be used to gate motion.

*Cross-references: §8.5/§8.11 (Station Monitor, counts for EnPI), §8.12 (condition-monitoring path), §2.7 (timestamps), §7/§9 (utility gating stays an interlock/safety function), §11.9 (north-bound exposure).*

---

## 9. Safety

### 9.1 Separation of safety and standard logic

- Safety functions **shall** be implemented in the certified safety system of the binding ([TC3]: Beckhoff TwinSAFE — TwinSAFE Logic plus safe I/O over FSoE / Safety-over-EtherCAT, TC3 §9), authored and validated by a qualified safety engineer, independently of the standard PLC application.
- The standard application **shall** treat safety state as **read-only**: it consumes mapped safety status to gate motion and inform the operator, but **shall not** implement or substitute a safety function.

### 9.2 Safety-to-standard interface

- The safety system **shall** publish a fixed set of alias signals into the standard application — e.g. `AllEstopsOk`, `AllSafetyOk`, per-zone `Zone<n>Safe`, and per-actuator safe-state feedback. The names are standardized so every station reads safety identically.
- The standard application gates energize/motion on the relevant alias and raises a Safety alarm (§8.6) with a `ReasonCode` (§8.8) when an alias drops.

### 9.3 Decouple / evaluate / energize

For any actuator whose power can be safely removed:

- **Decouple** — the safety system removes enabling power/torque on a safety event (`safeDecouple`).
- **Evaluate** — the standard application detects the safe state via feedback and brings its sequences/commands to a defined safe stop (Hold/Abort, §6), surfacing the first-out reason (§6.9).
- **Energize** — re-enable only after the safety condition is restored *and* a deliberate reset (§9.4). The standard application **shall not** self-re-energize from a latched safety event.

### 9.4 Reset & restart

- Safety reset **shall** be a deliberate operator action with the guarded area clear; the standard application **shall not** auto-restart motion after a safety event.
- Restart interlocks, guard and light-curtain monitoring, and e-stop handling live in the safety system; the standard application reflects their status and blocks manual functions accordingly (§7.6).

### 9.5 Zones & rollup

Safety zones map to stations. A zone fault **shall** roll into the affected station's Safety alarm and Station Monitor (§8.5–8.6) so downtime is attributed to the true cause.

### 9.6 Manual mode

Manual mode **shall not** bypass safety. Manual-function release (§7.6) is ANDed with the relevant safety alias, and commissioning gates (§7.5) never override safety.

### 9.7 Functional-safety lifecycle & PLCopen Safety

§9.1–§9.6 fix the **separation** of safety from standard logic. This section adds the **lifecycle and library** expectations for the safety side itself.

- **Lifecycle.** The safety system (§9.1; [TC3]: TwinSAFE, TC3 §9) **shall** be designed, implemented, and validated per the functional-safety lifecycle of ISO 13849-1 (and/or IEC 62061): the required Performance Level / SIL for each safety function is determined by risk assessment, and verification/validation are performed and documented independently of the standard application.
- **Standard safety functions via PLCopen Safety.** Standard safety functions — emergency stop, guard/door monitoring, two-hand control, enabling switch, safe stop — **should** be built from the certified PLCopen Safety function-block set (the `SF_*` blocks) rather than bespoke safety logic, for traceability and certifiability.
- **Unchanged interface to the application.** None of this changes §9.2: the standard application still consumes only the published safety alias signals (`AllEstopsOk`, `Zone<n>Safe`, …) read-only, and never implements a safety function.
- **Change control.** Any change to a safety function **shall** trigger re-validation and follow the management-of-change process (§13); the safety project's version/identity is tracked separately from the standard application's (§13, §14.2).

*Cross-references: §9.1–§9.2 (separation & alias interface), §9.4 (reset/restart), §13 (MOC & versioning), §14.2 (integrity/identity).*

### 9.8 Safety and control-power profile

Stations using Control On/Off, independently switched power groups, guard access requests, safety valves, light curtains, keyed bridges, muting, or fieldbus-driven power reactions **shall** implement `SAFETY_AND_CONTROL_POWER_PROFILE.md`. The profile fixes an asymmetric interface: the standard PLC may issue untrusted stop/enable/unlock requests, while the certified safety system alone grants safe enable/unlock/reset and publishes verified state. `ControlOn` is control-domain orchestration; `PowerOn` is one named energy group. Neither may automatically resume after a safety or communication event.

The Unit forest and the control-domain graph are orthogonal. Every root Unit references zero or one `ST_ControlDomainStatus`; one domain may serve one or many peer root Units, while an unassigned Unit has no Control-On prerequisite from this profile. A control domain is cell infrastructure, not a fourth tier or a super-root Unit, and sharing it never merges Unit mode/cycle/recipe/OEE/access ownership. `Status.ControlDomainId` publishes the association; empty means none. Safety devices and power groups publish optional `ST_SafetyStatus` and `ST_ControlPowerStatus` facets; `Present=FALSE` hides an unused capability. Partial valve-island/drive isolation is expressed as an affected-power-group mapping whose execution remains in the validated safety project. Plug-and-produce means descriptor/identity/membership validation and deterministic composition, never live modification of validated safety logic.

---

## 10. I/O, Fieldbus & HAL

### 10.1 Fieldbus

- The binding defines the primary fieldbus ([TC3]: EtherCAT — TC3 §10.1). The fieldbus master(s), topology, and distributed-clock settings **shall** be documented; device order in the configuration follows the physical/schematic order.
- Drives, robots, scanners, and sub-buses are integrated as fieldbus devices or through documented gateways.

### 10.2 I/O through the HAL

- Application logic (CM/EM/Unit) **shall** access I/O only through the HAL data structure (§3.6); raw `%I`/`%Q` references in application logic are not permitted.
- Symbols mapped to `%I`/`%Q`/`%M` carry the leading `_` marker (§4.4) and live at the Hardware Driver layer; the driver presents typed, named signals to the HAL.

#### 10.2.1 Mandatory I/O responsibility distribution

“Use a HAL” is insufficient unless the surrounding responsibilities are also separated. A conforming application **shall** distribute I/O integration into the following layers; these are code-ownership boundaries, not additional module tiers:

| Layer | Owns | Shall not own |
|---|---|---|
| **Framework topology mechanism** | bounded node/channel registry, bounds and duplicate validation, health propagation, exact-tag diagnostic correlation | project tags, terminal order, station-specific HALs, sequence logic |
| **Project I/O catalog** | the approved engineering-data join: electrical tag, physical address, localization key, unique path, owning module path, and semantic role | cyclic value copying, raw `%I/%Q` access, mode/recipe/sequence behavior, generic registry algorithms |
| **Hardware Driver** | the only reads/writes of mapped process-image symbols; conversion between physical polarity/scaling and semantic HAL fields; live fieldbus-value refresh | mode sequencing, recipes, device state machines, collision logic, HMI presentation rules |
| **Control Module** | reusable device behavior expressed in semantic roles (`Extended`, `Retracted`, `Enable`, etc.) through its HAL; optional injected I/O identity used in diagnostics | terminal models, channel numbers, project electrical tags embedded in the type, direct process-image access |
| **Composition root** (`MAIN`/top-level program) | instantiate, one-shot `Setup`, select real versus simulation drivers, and execute components in documented scan order | channel-by-channel mapping, diagnostic matching algorithms, reusable device logic |

The dependency direction is fixed: the project catalog configures the generic topology mechanism and injects physical identity into module roles; the Hardware Driver moves live values between process image and HAL/topology; modules consume only HAL semantics; the composition root only wires these participants. An I/O tag/address **shall have one project source of truth**. Repeating its literal independently in `MAIN`, a CM, and an HMI publisher is non-conforming even if the values happen to match.

The project catalog is deliberately project-specific and may contain a long generated/imported list; that list is engineering **data expressed in code**, not a reason to move it into a reusable device type. Conversely, bounds checking, duplicate detection, health propagation, and `ST_Diagnostic.IoTag` matching are reusable algorithms and **shall not** be reimplemented by each project catalog. A production toolchain should generate the catalog from the approved I/O list and fail CI on an unmatched or duplicate physical join.

The non-normative implementation guide `IO_ARCHITECTURE.md` illustrates the dependency direction,
scan order, press-example placement, and recommended CI gates.

### 10.3 Hardware Driver & simulation

- Each physical channel/device has a Hardware Driver (DI/DO/Motor/…); each driver supports a SIM toggle (§3.6, §2.6) selected by configuration.
- Signal conditioning — debounce, invert, scaling — lives in the driver or CM, not in sequences. Per §5.5 this logic may be written in ST or Ladder.

### 10.4 Naming & device wrapping

- Terminal, channel, and device names **shall** match the electrical schematic (§4.7); the PLC link uses the schematic name.
- Drives, axes, robots, and scanners are wrapped as Control Modules exposing the standard handshake (§6.1) and the four-structure contract (§3.12); vendor-specific detail stays inside the CM/driver.

### 10.5 Fieldbus diagnostics

Fieldbus and controller diagnostics — lost frames, slave errors, distributed-clock sync loss, watchdog — **shall** surface as System alarms (§8.6) with a `ReasonCode` (§8.8) and **shall not** be silently swallowed ([TC3]: EtherCAT/IPC specifics, TC3 §10.5).

#### 10.5.1 Fieldbus topology & I/O diagnostics view

Beyond the *logical* module tree (§3.13), a maintenance user needs the *physical* bus picture — which node is down, which channel is stuck — because a field fault is diagnosed at the wiring, not the sequence. The framework therefore defines a platform-neutral **fieldbus topology model**, published for the HMI over the same self-description surface (§3.10):

- **Nodes.** The bus is a tree of nodes (master → slaves/couplers → terminals); each node publishes `Name`, `TypeId` (vendor/product), `Address` (topological + logical), a **node state** (`E_NodeState`: `OFFLINE` < `INIT` < `PREOP` < `SAFEOP` < `OPERATIONAL`, plus `FAULT`), and a link-health flag. The state vocabulary is the CANopen/EtherCAT-style state machine expressed neutrally so other fieldbuses map onto it.
- **Channels.** Each node publishes its **I/O channels**: `Name`, `DescriptionKey`, `Address`, `Path`, `ModulePath`, `Direction` (`INPUT`/`OUTPUT`), `Kind` (`DIGITAL`/`ANALOG`), live `Value` (BOOL for digital; scaled `REAL` + `Unit` for analog, raw available), per-channel quality/forced/fault flags, an explicit `Forceable` capability, and — where the binding implements forcing — the held force **set-point** kept separately from the live value, so a force survives a publish cycle and a cleared force restores the real value rather than freezing the last forced one. `Name` **shall equal the exact tag in the approved I/O list and electrical schematic**; it is untranslated structured identity. `DescriptionKey` is the localizable human description, `Address` is the terminal/channel locator, `Path` is the unique force/audit identity (§4.8), and `ModulePath` cross-links to the owning module. `Forceable` defaults `FALSE`; output direction alone never grants a force surface. The names and capabilities are therefore generated/imported from reviewed engineering data rather than independently retyped in the HMI.
- **Runtime validation and engineering-data join.** Installed node presence/order and health **shall** be read from the fieldbus master's own diagnostics at runtime so the view updates as nodes drop or return. Channel identity, scaling, electrical tags, and module ownership **shall** come from one reviewed project/toolchain I/O catalog (§10.2.1), because those engineering semantics are not reliably discoverable from a generic live bus. The binding shall validate the configured catalog against runtime node count/order/identity evidence and join channels by deterministic physical address; it shall never guess a missing relationship. Missing, duplicated, mismatched, or unmatched mappings set `MappingValid=FALSE` with a localizable `MappingDiagnostic`. Live values come from the same HAL/process-image authority used by the hardware driver. A node's or channel's contribution to a module fault uses the same first-out vocabulary (§8.8): matching `ST_Diagnostic.IoTag` marks the channel and makes module↔fieldbus navigation available. A binding may additionally offer richer runtime identity/channel discovery, but that optional adapter does not replace the reviewed catalog or become a base-conformance requirement.
- **HMI rendering (§3.13).** The topology view is a **second tree** beside the module tree: nodes coloured by state (operational = neutral, degraded `SAFEOP`/link-warn = warning, `FAULT`/`OFFLINE` = error), channels listed with live values, digital as on/off, analog as value + unit. This is a **read/diagnostic** surface by default. A limited **output force** is a manual function gated by §7.6 **and** §7.7 (`MANUAL`), never a casual click, and constrained by four rules so it can never become a way to defeat the controller:

  1. **It exists only in a commissioning build.** Output forcing **shall** be a registered §7.5 engineering gate. In a production build the gate is inactive, `Forceable` is `FALSE` on every channel, and the HMI therefore renders no force affordance at all — the surface is absent, not greyed out (§3.9). Whenever the gate *is* active the station carries the standing §7.5.2 annunciation, so a machine that can be forced always says so.
  2. **Explicit capability, outputs only.** The HMI exposes a force control only when the PLC publishes `Forceable=TRUE`, and the PLC resolver rechecks that capability and mapping. A runtime force **shall** write only such a mapped *output* channel (energize a valve, drive a lamp) through gated PLC code. Missing capability data is `FALSE` (fail closed). Forcing an *input* — lying to the logic to bypass an interlock or sensor — is **not** provided by this surface; it is a commissioning act performed with the engineering tool under separate authority, never a normal operating practice.
  3. **Withdrawn the moment the module can act.** The runtime path writes the output variable through the application, so the owning module still runs and still owns its interlocks (§7.2). A force is effective only while its owning Unit is stopped and in `MANUAL` (§3.4); leaving either condition **shall** withdraw every force of that Unit rather than leave it contending with live logic. This is deliberate — the force cannot silently override active logic, and it cannot survive into automatic operation.
  4. **Safety I/O is never forceable here.** Safety-rated I/O lives on the safety system (§9, FSoE/TwinSAFE) and is out of reach of this path by construction; the standard-PLC force cannot touch it.

Every force and clear is a logged §8.3 event (audit trail).
- **Relation to the HAL (§3.6).** The logical HAL struct a CM references (§3.6) is *mapped* onto physical channels in the fieldbus configuration; the topology view exposes that physical layer directly, so a "sensor not made" first-out (a module fault) and "terminal 3 channel 2 = FALSE, node in SAFEOP" (the bus view) are two lenses on the same event — the HMI lets maintenance cross from one to the other.

*Cross-references: §3.6 (logical HAL), §3.10 (self-description), §3.13 (HMI trees), §4.8 (browse paths), §8.6/§8.8 (system alarms & reasons), §7.5 (the commissioning gate that enables forcing at all), §7.6/§7.7 (forcing is gated), TC3 §7.5/§10.6 (EtherCAT/ADS binding).*

### 10.6 Motion control (PLCopen Motion)

Axes and drives are wrapped as Control Modules (§10.4); this section fixes **how** their motion is expressed so it is vendor-neutral and reuses the handshake.

- **PLCopen Motion interface.** A motion Control Module **shall** drive its axis through the PLCopen Motion function blocks (`MC_Power`, `MC_MoveAbsolute`, `MC_MoveVelocity`, `MC_Home`, `MC_Stop`, `MC_Reset`, with the standard `AXIS_REF`), not vendor-specific motion calls. The CM exposes named device commands (e.g. `MOVE_TO`, `HOME`) whose internal `MC_*` `Busy`/`Done`/`Error`/`CommandAborted` outputs map onto the CM's PLCopen status (§6.1) — so a motion CM looks identical to any other CM to its parent.
- **Coordinated motion.** Multi-axis/coordinated moves **shall** use the PLCopen coordinated-motion blocks inside the owning CM/EM; the parent still commands a single named action through the §6.1 handshake.
- **Limits & scaling.** Axis scaling, soft limits, and velocity/accel limits live in the CM/driver (§10.3); motion targets are validated against them before issue (§5.6). Vendor-specific drive detail stays inside the CM (§10.4).
- **Safety.** Safe-motion functions (STO/SS1/SLS) remain in the safety system (§9); the motion CM consumes their status read-only and brings motion to the §6 defined safe stop when an alias drops.
- **Full robots (multi-axis kinematic systems).** A complete robot is wrapped as a Control Module fronted by an `I_RobotConnector` — a specialization of the §3.15 device connector that adds an ID-addressed command surface. A robot framework is more than HMI teaching: it is a **motion-planning layer**, and the standard's rule is that *all of its geometry and kinematics are taught/generated configuration (§3.8) addressed by stable ID — never a coordinate, waypoint, motion mode, or route in a PLC sequence*. Specifically: **points and paths** (point-lists run by ID or sub-range, each point's motion mode — Joints/PTP/Linear, absolute/blended — taught data); **generated trajectories** (the application template assembles the route between a named *from* and *to* position at runtime, so the PLC issues `MOVE_TEMPLATE(from,to)` and never enumerates waypoints); **planning areas** (3-D zones for collision-free recovery from an undefined pose after an E-stop/mode change via `MOVE_FROM_AREA` (area-resolved), with deterministic priority — **distinct from the §9 functional-safety system**, which stays read-only and gates a deliberate §9.4 reset); and **parametric/symmetric pallets** plus **chained reference frames** (a grid generated from a few taught corners, frames defined relative to frames, so a moved fixture is re-taught in one place). The parent commands named/ID-addressed actions through the §6.1 handshake; a point, a 26-point path, a generated route, or a pallet nest is **one** command that runs to completion, so the robot looks identical to any other CM. In practice a thin **robot-handling Equipment Module** exposes the station's *semantic* operations (`PICK_PART`/`PLACE_PART`/`SCAN_PART`/`PROCESS_PART`…) above the robot CM's primitives, adding no device logic (§3.5). Route generation is expressed as **declarative routing data** (a help/nest graph plus a per-nest **help-affinity list**) resolved by one generic planner in the connector — so a **work position served by two or more help points is a native table entry, not hand-coded per-station branching** — and area-resolved motion (`MOVE_FROM_AREA`) is the primary form, with pose recovery its extreme case. Link supervision (§3.15.2), validation before motion (§5.6) and read-only safety (§9) all apply, and robot commands are **not** auto-repeated on error (resumption is deliberate, mirroring §3.15/§9.3). The framework controls robots **regardless of model or manufacturer** by capturing per-model facts (signal counts, Euler conventions, available functions) as data the connector reads — so a **portable, vendor-neutral teaching connector is the recommended default** implementation; per-manufacturer connectors **may** implement the same `I_RobotConnector` as conformant alternatives, with the parent Unit unchanged in either case. Exposing a robot through the portable framework is an **optional conformance profile** (claimed like §11.7), not a mandate, but is the recommended path. See Annex I.

*Cross-references: §10.3/§10.4 (driver, CM wrapping, limits), §6.1 (handshake/status mapping), §5.6 (target validation), §3.15 (device connector & link supervision — the robot connector specializes it), §3.8 (taught points/frames/tools are recipe-class configuration), §9/§9.7 (safe motion stays in the safety system), §10.7 (routing model), Annex I (robot CM worked example).*

### 10.7 Declarative routing model (help/nest graph & help affinity)

*Promoted to Core from Annex I §I.9–§I.10; Annex I remains the worked realization.* Where a motion system generates routes between taught positions at runtime (§10.6 robots being the primary case), the routing knowledge **shall** be **declarative configuration resolved by one generic planner** in the connector — never per-station imperative traversal code.

**(a) Position classes.** Positions are two classes: **help points** (auxiliary wait/transit positions) and **nests** (work positions).

**(b) The route graph is data.** The application supplies configuration, not code:

```iecst
TYPE ST_RouteGraph : STRUCT
    HelpAdj  : ARRAY[1..MAX_HELPS, 1..MAX_HELPS] OF BOOL;   // help↔help adjacency (allowed transits)
    NestHelp : ARRAY[1..MAX_NESTS] OF ST_NestHelpAffinity;  // each nest → one OR MORE serving help points
    DirectNest : ARRAY[1..MAX_NESTS,1..MAX_NESTS] OF DWORD; // optional direct nest→nest list id (else via help)
END_STRUCT
```

The planner builds `from → departHelp → (help-graph search) → approachHelp → to` generically for every station. If the graph yields no path, the planner **shall** return a **no-route** first-out (registered in the implementing type's band, §8.8 — e.g. the robot CM's `ROBOT_NO_ROUTE`) and the fronting CM raises a clean fault (§5.6) rather than an undefined move. Per-edge overrides are optional data, not code.

**(c) Multi-help work positions are native.** A nest carries a **help-affinity list** — one *or more* help points, each tagged with a **role** (`APPROACH` / `DEPART` / `EITHER`, default `EITHER`) and, optionally, the transit **region** it serves:

```iecst
{attribute 'qualified_only'} TYPE E_HelpRole : (EITHER := 0, APPROACH := 1, DEPART := 2) DINT; END_TYPE

TYPE ST_HelpAffinity : STRUCT
    HelpId   : DWORD;        // a help point serving this nest
    Role     : E_HelpRole;   // APPROACH into the nest / DEPART from it / EITHER (default)
    RegionId : DWORD;        // OPTIONAL transit region this help connects to (0 = any)
END_STRUCT
TYPE ST_NestHelpAffinity : STRUCT
    Helps : ARRAY[1..MAX_HELPS_PER_NEST] OF ST_HelpAffinity;  Count : INT;
END_STRUCT
```

The planner resolves the serving help **role-first** — direction is the higher-consequence constraint (a wrong-direction corridor can drive the tool into the fixture; a wrong region is only a longer, still-safe route) — and uses region/proximity **only to break ties** among same-direction corridors. Region is therefore required only on a nest with two corridors *for the same direction*. An unresolvable nest **shall** yield a **no-help-for-nest** first-out (e.g. `ROBOT_NO_HELP_FOR_NEST`), never a silent mis-route. Multi-help is the general case; single-help is the trivial one (`Count := 1`).

**(d) Reversal & disposition by construction.** A reversal (e.g. NOK disposition) is an ordinary move with a different destination — no special mode. Two rules keep it safe and *loud*: entry corridors default to `EITHER` (a nest is exit-able the way it was entered unless its geometry is physically one-way, in which case a reversal fails with the no-help first-out); and retract is a **separate path definition**, not the approach played backwards, so extraction geometry may differ from insertion.

**(e) Paid once, tested once.** The planner and help resolver are part of the connector *type* and are verified by the type's test suite (§5.7; worked cases: Annex I §I.14) — a station that adds a multi-approach nest adds a table row, not logic (§1.1 O1, O3, O4).

*Cross-references: §10.6 (robot CM — the primary consumer), §3.15 (connector owns the planner), §8.8 (registered first-out reasons), §5.6 (validate-then-move), Annex I §I.9–§I.11 (worked realization incl. area-resolved motion).*

---

## 11. Connectivity & External Interfaces

### 11.1 Fraktal Self-Description endpoint

- Every binding **shall** expose the Fraktal Self-Description Service of §3.10 and document its default transport, endpoint/gateway components, protocol/schema version, and any alternative projections. The service publishes only explicitly deployed roots and explicitly registered standalone data; implementation-only references/handles are excluded.
- Fraktal/TC3 uses TF6100 OPC UA by default (TC3 §3.10/§11.1). Fraktal/AB uses EtherNet/IP explicit messaging through the Fraktal gateway by default and may expose OPC UA as an alternative projection (AB §3.10/§11). Neither choice changes the Core service model.
- Canonical identity follows §4.8: each local hierarchy segment equals the local PLC/schematic instance name, while `Status.Name` carries the complete dotted module path. Every projection shall retain that identity.

### 11.2 Endpoint, namespace & security

- The selected endpoint(s), logical application namespace, protocol/schema version, and station identity **shall** be documented per station. A native hierarchical server may expose the namespace directly; a gateway may reconstruct it from the binding manifest and bounded value services.
- Command-capable transports **shall** provide authenticated principals, integrity and confidentiality appropriate to the declared IEC 62443 conduit, and least-privilege roles (operator / maintenance / engineering). Anonymous or unauthenticated write access is not permitted. A projection that is read-only shall state that restriction explicitly.
- A binding-specific security mechanism belongs in that binding: [TC3] certificate trust and sign-and-encrypt policy are defined in TC3 §11.1; [AB] gateway/controller trust boundaries and EtherNet/IP/OPC UA alternatives are defined in AB §11.

### 11.3 Clients

The Flutter operator app and any MES/SCADA connect through a binding adapter and render or consume the model generically (§3.10, §3.13). No client-specific symbol wiring is added to the PLC and no transport-specific address becomes the module's canonical identity.

A command-capable client **shall** distinguish and report transport reachability,
transport authentication/session readiness where applicable, Fraktal namespace/schema
compatibility, root discovery, request staging/commit, controller acknowledgement, and
controller acceptance as separate states. It shall not infer command success from a
connected session or a successful transport write alone: arguments are committed through
the root mailbox and command success requires the matching acknowledgement plus
`Accepted=TRUE`. `LOGIN` is the deliberate exception: `Accepted` confirms that the attempt
was consumed, while authentication success is the resulting access state defined by
§7.7(c). Repeated value refresh shall not starve or reorder a command, and reconnect shall
not replay an unacknowledged write (§3.10, §3.13, §14).

### 11.4 Recipe / type transports

- Recipe/type sources (`LOCAL` / `OPCUA` / `SOCKET_JSON|XML` / `REST`, §3.8) are configured behind the logical `I_RecipeProvider` capability; transport endpoints and credentials are documented per station and never embedded in module logic.
- External payloads are validated before load (§3.8); a failed or partial fetch faults the consuming module with a `ReasonCode` (§8.8) rather than loading a half-recipe.

### 11.5 Alarm / event & historian

The alarm queue and `AlarmQueueHandler` (§8.3) publish to the alarm database/historian using the module's canonical path as the record path and the `ReasonCode`/catalog of §8.8, so PLC, HMI, historian, and MES share one address and one reason vocabulary.

### 11.6 MES / ISA-95 host-event & transaction mapping

§3.16 defines part events *inside* the PLC; this section fixes how the cell talks to **L3 (MES)**, so integration is a mapping rather than a per-project build. The cell exposes a **fixed host-event set** and maps it to ISA-95 (IEC 62264) concepts — aligning with the PackML Administration-tag idea that higher-level systems consume performance and part data through a standard structure.

### 11.6.1 Fixed host-event set

The cell **shall** emit only these host events; sites do not invent new ones without extending this table:

| Host event | Source | ISA-95 / L3 meaning |
|------------|--------|---------------------|
| `PART_RECEIVED` / `PROCESSING_STARTED` / `PROCESSED` / `PROCESSING_ABORTED` | §3.16 | material/product tracking + production response (verdict, genealogy) |
| `CHANGEOVER_STARTED` / `CHANGEOVER_DONE` | accepted Start / successful completion of the Unit `CHANGEOVER` sequence (§3.4) | work-order / product-definition change |
| `TOOL_CHANGED` / `MATERIAL_CHANGED` | EM/Unit | resource/material lot change |
| `MODE_CHANGED` | `OnModeChanged` (§3.14) | equipment operational-mode change |
| `NOK` / scrap | performance capture (§8.11) | quality / scrap transaction |

Each event **shall** carry: the producing **station canonical path** (§4.8), the part `Uid` where applicable (§3.16), a **synchronized timestamp** (§2.7), the `Verdict`/result, and the `ReasonCode` (§8.8) for an abort/NOK — so an MES receives a self-describing, reason-coded record.

### 11.6.2 Transport & shape

- A root Unit **shall** publish one bounded, read-only `HostEvents` object through the Self-Description Service, containing a ring of `ST_HostEvent` records plus `RingHead`, valid `Count`, published `Capacity`, and an explicit `Wrapped` data-loss indicator. `ST_HostEvent` carries a monotonic sequence, fixed event kind, station path, optional part Uid/subject/value, timestamp and synchronization quality, verdict, and reason. It is on-demand data and never a command surface. Clients derive modulo/ring traversal from `Capacity`; they shall not duplicate the binding's array limit.
- The same record **may** additionally be delivered over OPC UA A&C, socket/REST, or MQTT-Sparkplug (§11.9) behind the logical `I_HostEventSink` capability, mirroring provider injection (§3.8/§11.4), so delivery transport is composition rather than Unit logic. The bounded PLC ring remains available when an optional sink is absent or unavailable.
- The event shape **should** map cleanly to ISA-95 / B2MML transactions (production performance, material lot/genealogy), so an MES that speaks B2MML consumes the cell without a bespoke driver.

### 11.6.3 Direction & trust

Host events are **produced** by the cell; commands **into** the cell (work order, recipe selection) arrive through the recipe/type path (§3.8) or a release-gated method, are treated as **untrusted third-party input** (validate per §3.8 and §14), and **shall not** bypass mode/release rules (§3.4, §7.6).

*Cross-references: §3.16 (part events), §2.7 (timestamps), §8.8 (reason vocabulary), §3.8/§11.4 (provider injection), §14 (untrusted input).*

### 11.7 PackML / OPC UA line-coordination profile

> **Interoperability note (Annex J).** The same projection philosophy extends to **MTP** (VDI/VDE/NAMUR 2658 / IEC 63280): a root Unit exports as a PEA — services from its runnable modes, DataAssemblies from the Status mirror (§3.10), parameters from §3.8, alarms from §8.3 — so any MTP-conformant orchestration layer (POL) can integrate a Fraktal station with no bespoke driver. The mapping, its honest mismatches, and the exporter checklist are Annex J.

§6.6 introduces PackML as an optional overlay. This section defines the **binding-qualified PackML/OPC UA conformance option**: only a deployment claiming that option shall expose the complete OPC 30050 projection below. The native `ExecState`/mode model (§6.1, §3.4) remains the internal source of truth, and a binding or deployment that does not claim this optional projection remains conformant to base Core (§1.5).

### 11.7.1 State-machine mapping

The native execution state and Stop/Hold/Abort transitions **shall** map to the PackML state machine:

| Native (§6.1/§8.2) | PackML state |
|--------------------|--------------|
| READY, idle | `Idle` (via `Resetting` → `Idle`) |
| Start requested | `Starting` → `Execute` |
| BUSY, cycling | `Execute` |
| Stop after cycle (§3.14 `OnModeExit`) | `Completing` → `Complete`, or `Stopping` → `Stopped` |
| Hold (§6) | `Holding` → `Held` → `Unholding` |
| Blocked/Starved (§8.11) | `Suspending` → `Suspended` |
| ERROR / fault hold (§8.2) | `Aborting` → `Aborted` → `Clearing` |

### 11.7.2 Unit-mode mapping

`E_Mode` (§3.4) maps to PackML Unit Modes; unsupported-mode rejection (§3.7) maps to a refused `SetUnitMode`:

| `E_Mode` | PackML Unit Mode |
|----------|------------------|
| `AUTO` | Producing |
| `MANUAL` | Manual |
| `CHANGEOVER` / `CALIBRATION` / `HOME` | Maintenance (or site-defined custom modes) |

### 11.7.3 PackTags (Command / Status / Administration)

The profile **shall** expose the three PackTag groups, sourced from contracts the standard already defines — so PackML is a *projection*, not new logic:

- **Command** — `UnitMode`, `CntrlCmd` (Start/Stop/Hold/Reset/Abort), `MachSpeed`, material/equipment interlocks. Consumed through `SetUnitMode` / `SetMachSpeed` methods and mapped onto the native `SetMode`/`Start`/`Stop` (§3.3/§3.4) and release rules (§7.6).
- **Status** — `UnitModeCurrent`, `StateCurrent` (from §11.7.1), `MachSpeedActual`, equipment-interlock status.
- **Administration** — alarms (from §8, with the §8.8 reason as the PackML alarm id and the first-out `StopReason` from §6.9), and the production/performance counters and cycle times from §8.11. The Admin group is where higher-level systems read performance and stop-reason data.

### 11.7.4 Conformance

When the `PackML/OPC UA` profile is claimed, the mapping above **shall** be complete and validated, and exposed through a `PackMLObjects` folder in that OPC UA projection. The conformance claim shall name the binding (for example `Fraktal/TC3 + PackML/OPC UA`). The native model is unaffected; this profile is an additional north-bound interface, coexisting with the ISA-95 host events (§11.6).

*Cross-references: §6.6 (overlay intro — now specified here), §3.4/§3.7 (modes & rejection), §8/§8.8/§8.11 (alarms, reasons, counters), §11.1 (Self-Description endpoint), §11.6 (ISA-95 events — complementary).*

### 11.8 Module self-description portability (AAS & MTP mapping)

The self-describing module tree and generic HMI of §3.10/§3.13 are conceptually the same artifact as the Industrie 4.0 **Asset Administration Shell** (AAS, IEC 63278) and the modular-automation **Module Type Package** (MTP, VDI/VDE/NAMUR 2658, advancing as IEC 63280): a vendor-neutral, importable description of a module's identity, services, communication, and HMI. To make the cell portable into AAS-/MTP-aware tooling, the standard defines an **export mapping** generated from the same self-description — the native model stays the runtime source of truth; the AAS/MTP artifacts are a generated projection, like §11.7.

### 11.8.1 AAS mapping

Each module (Unit/EM/CM) maps to an AAS asset with submodels drawn from contracts already present:

| AAS submodel | Source in this standard |
|--------------|-------------------------|
| Nameplate / Identification | module `Name`, `ModuleType`, canonical path (§3.2, §4.8) |
| TechnicalData | `ParCfg` schema (§3.8), feature flags (§3.9) |
| OperationalData | `State`, `ModeActive`, `ST_Diagnostic` (§3.2, §8.8) |
| ModuleContract (custom) | the four-structure contract (§3.12) + handshake surface (§6.1) |
| Documentation | linked drawings/manuals per project |

### 11.8.2 MTP mapping

The MTP manifest is assembled from the same model: module **commands/modes** (§3.4/§3.5) → MTP **Services**; the Self-Description Service records (§3.10) → MTP **Communication**; the tile/detail rendering (§3.13) → the MTP **HMI** template. The result is a manifest a Process Orchestration Layer can import for plug-and-produce, consistent with RAMI 4.0.

### 11.8.3 Conformance

The AAS/MTP export is an **optional, binding-qualified** conformance profile. When claimed, it **shall** be generated from the live self-description (never hand-maintained in parallel) so it cannot drift from the running cell, and it **shall** carry the same canonical paths (§4.8) as every other interface, so AAS, MTP, OPC UA, HMI, and MES all address the module identically.

*Cross-references: §3.10/§3.13 (self-description & generic HMI — the source), §3.12 (data contract), §4.8 (one address everywhere), §11.7 (sibling north-bound profile).*

### 11.9 North-bound telemetry (OPC UA Pub/Sub, MQTT Sparkplug, UNS)

§11.1's Self-Description Service supplies secured control and on-demand reads through the selected binding transport. For telemetry fan-out to many consumers and for IIoT/cloud and a plant **Unified Namespace (UNS)**, the cell **may** additionally **publish** its data.

- **Optional publish path.** The cell **may** expose a north-bound profile over **OPC UA Pub/Sub (IEC 62541-14)** or **MQTT with Sparkplug B**, publishing a projection of the same self-describing model (§3.10): state, modes, diagnostics (§8.8), performance (§8.11), and health (§8.12). This **supplements**, never replaces, the secured command/on-demand service.
- **UNS-aligned addressing.** Published topics/datasets **shall** be keyed by the module's canonical path (§4.8) so the UNS topic hierarchy mirrors the module tree — one address across the native service, OPC UA, HMI, MES, AAS/MTP (§11.8), and the UNS.
- **Liveness by design.** Sparkplug birth/death certificates (or Pub/Sub keep-alive) give consumers connection liveness without polling — the publish-side analogue of the link-supervision philosophy (§3.15).
- **Security.** The publish path is subject to §14: broker/endpoint authentication and TLS, least-privilege topics, no anonymous publish, and it lives on a documented conduit (§14.1).

*Cross-references: §11.1 (client/server control interface — primary), §3.10/§4.8 (self-description & one address), §8.8/§8.11/§8.12 (published content), §11.8 (AAS/MTP siblings), §3.15 (liveness philosophy), §14 (security/conduits).*

### 11.10 Field-level peer & device exchange (OPC UA FX) — optional/emerging

§11.7 projects the cell *upward* to a line controller (machine-to-line) and §3.15 reaches *outward* to a single smart device. **OPC UA FX (Field eXchange)** covers the third direction: deterministic **controller-to-controller (C2C)** and **device-to-device (D2D)** peer exchange across the field level, typically over **TSN** for motion-grade timing. It is the standards-based path for stations to coordinate *directly* with each other and with OPC-UA-capable devices.

- **Optional / watch profile.** Cross-vendor FX tooling is still maturing (multi-vendor demonstrations ongoing through 2026), so FX is a **may**, not a **shall**. It is **recommended where multi-station or multi-vendor-robot coordination is in scope** (e.g. an automotive line where adjacent stations or differently-branded robots hand off in lockstep, or gateway-free device integration); pilot it before committing it to a **shall**.
- **Projection, not new logic.** What a station publishes or consumes over FX **shall** be a defined slice of the same self-describing model (§3.10) — typically handshake-level command/status (§6.1) between peer stations, or to a device — keyed by the module's canonical path (§4.8). FX adds a peer interface; it does not introduce a second control path or duplicate logic.
- **Relationship to §3.15.** The smart-device connector (§3.15) fronts *proprietary* links (vendor sockets, S7, REST); FX is the **standards-based alternative** for OPC-UA-capable peers and devices. The same link-supervision philosophy applies — connection establishment, liveness, and a **defined loss reaction** (HOLD/ABORT/MODE_STOP, §3.15) — expressed over FX connection monitoring rather than a bespoke heartbeat.
- **Time & security.** FX over TSN shares the synchronized time domain of §2.7; the FX conduit is subject to §14 (authentication, TLS, documented conduit, least privilege).

*Cross-references: §11.7 (machine-to-line — complementary direction), §3.15 (proprietary-link sibling & loss-reaction philosophy), §3.10/§4.8 (projected model, one address), §2.7 (TSN time domain), §14 (conduit security), §11.1 (client/server control interface — unaffected).*

### 11.11 Discovery & identification base model (OPC UA for Machinery) — optional

**OPC UA for Machinery** (the umati base companion specification, OPC 40001) defines reusable *building blocks* — identification/nameplate, finding all machines, components, item state/monitoring, preventive maintenance, job management, and energy — so that any MES or dashboard discovers any machine uniformly, regardless of vendor. Because the cell already carries a self-describing tree (§3.10), conforming its identity, state, and component nodes to this base model lets third-party/umati tooling discover the cell with **zero custom mapping**. Like §11.8, this is an **optional, generated projection** — the native model stays the source of truth.

### 11.11.1 Mapping

The recursive model maps onto the Machinery building blocks unusually directly — in particular, the spec's **Components** concept (a machine may contain other machines, each with its own Identification) is the standard's Unit→EM→CM tree (§3.2, O4):

| Machinery building block | Source in this standard |
|--------------------------|-------------------------|
| `MachineIdentification` (Identification AddIn) | `Name`/`ModuleType` (§3.2), version/identity (§13), browse path (§4.8) → ProductInstanceUri, Manufacturer, Model, SerialNumber, SoftwareRevision |
| `Machines` object (find all machines) | the station(s) exposed on the cell's server (§11.1) |
| `Components` (recursive, each with Identification) | the child modules of the tree — each Unit/EM/CM is a Component (§3.2, §3.11) |
| `MachineryItemState` / Monitoring | the machine-state set (§8.11) and `State` (§3.2) |
| Preventive Maintenance | condition-monitoring signals (§8.12) |
| Job Management (ISA-95 / ISO 22400 based) | the MES host events (§11.6) |
| Energy | the utility/energy nodes (§8.14, OPC 34100) |

### 11.11.2 Conformance

When claimed, the Machinery mapping **shall** be **generated from the live self-description** (never hand-maintained), and **shall** carry the same canonical paths (§4.8) as every other interface. It is a sibling projection to AAS/MTP (§11.8) and the PackML profile (§11.7): the same cell, addressed identically, speaking one more discovery dialect.

*Cross-references: §3.2/§3.11/§4.8 (identity, recursive components, one address), §8.11/§8.12/§8.14 (state, maintenance, energy blocks), §11.6 (job management ↔ ISA-95 events), §11.7/§11.8 (sibling projections), §13 (version/identity for the nameplate).*

---

## 12. Worked Examples

> This section fixes the annexes' scope so they exercise every contract end-to-end. The annexes are **worked examples of the TC3 binding** (repository `fraktal-tc3`): each demonstrates Core contracts through TC3 mechanics and carries a one-line *"Core concepts demonstrated / TC3 mechanics used"* header identifying the seam.

- **Annex A — Control Module: separator/stopper** (a workpiece-carrier separation device): recipe via `I_RecipeProvider`, the PLCopen handshake (`Execute/Busy/Done/Error/ErrorID`), a first-out `ST_Diagnostic` with a real `E_Reason`, interlocks drawn in **Ladder** with device logic in **ST**, and the tile/detail HMI views. *(Drafted — see companion `Annex_A_Separator_ControlModule.md`.)*
- **Annex B — Equipment Module: clamp** (cylinder + two sensors) packaged as a reusable sub-tree type (§3.11), commanding its CMs through the handshake. *(Drafted — see companion `Annex_B_Clamp_EquipmentModule.md`.)*
- **Annex C — Unit: station** with an `AUTO` mode SFC step chain orchestrating the EMs, mode cascade to a child Unit, and the stall-diagnostic walk surfacing on the Unit's HMI view. *(Drafted — see companion `Annex_C_Station_Unit.md`.)*

Annexes A–C predate the §3.14–§3.17, §8.9–§8.13, §9.7, §10.6, §11.6–§11.9 and §14 contracts. The following annexes extend the set so every contract is exercised end-to-end; they reuse the Annex A–C station so each new feature is shown in context rather than in isolation:

- **Annex D — External device & link supervision (§3.15):** a smart device (programmable power supply or robot) wrapped as a Control Module through `I_DeviceConnector` — heartbeat, the configured loss reaction, bounded reconnect with no self-resume, and the link fault rolling up the §6.9 stall walk to the Unit view. *(Drafted — see companion `Annex_D_ExternalDevice_LinkSupervision.md`.)*
- **Annex E — Traceability & MES (§3.16, §11.6):** a station reading a part carrier (RFID), accumulating an `ST_PartResult`, emitting the four part-lifecycle events, and mapping them to ISA-95 host transactions; shows a NOK attributed by `ReasonCode` and written back before `EVENT_PART_PROCESSED`. *(Drafted — see companion `Annex_E_Traceability_MES.md`.)*
- **Annex F — PackML / OPC UA profile (§11.7):** the Annex C `InfeedUnit` projected onto the PackML state machine and PackTags (Command/Status/Admin), with `SetUnitMode`/`SetMachSpeed`, demonstrating line coordination with no change to the native model. *(Drafted — see companion `Annex_F_PackML_OPCUA_Profile.md`.)*
- **Annex G — Motion Control Module (§10.6, §5.6):** an axis CM driving PLCopen `MC_*` blocks behind the standard handshake, with target validation against axis limits and a safe stop on a dropped safety alias. *(Drafted — see companion `Annex_G_Motion_PLCopen.md`.)*
- **Annex H — Module test suite (§5.7):** a Control Module *type* with a TcUnit suite run against the simulated HAL — asserting the handshake, the first-out diagnostic (`ReasonCode`/`SourcePath`), and an interlock reaction, plus an integration test asserting the Annex B rollup — and the CI wiring that gates the merge. *(Drafted — see companion `Annex_H_Testing_TcUnit.md`.)*
- **Annex I — Robot Control Module (§10.6, §3.15):** a complete robot — including its **motion-planning framework** — as a Control Module (`I_RobotConnector`) with a thin **handling EM** for semantic `PICK/PLACE/SCAN/PROCESS` above it. ID-addressed points/paths/pallets with **no coordinates, motion modes, routes, or help choices in code**; **declarative routing** (a help/nest graph resolved by one generic planner) replacing per-station imperative methods; **native multi-help work positions** (a per-nest help-affinity list resolved from the move's endpoints — turning the reference framework's hand-coded two-help workaround into a table row); **area-resolved motion** and pose recovery kept **distinct from the §9 safety system**; **parametric/symmetric pallets**, per-gripper nests, and **chained frames**. Faults (unreachable point, no route, no help for nest, unresolved area, dropped link) roll up the §6.9 stall walk with no per-robot code. Validated against a real portable-robot manual and TwinCAT application export. An **optional conformance profile** composing with Annexes E, F and H. *(Drafted — see companion `Annex_I_Robot_ControlModule.md`.)*

The remaining new contracts do not need a standalone annex: operator dialogs (§6.11) and the signal-tower mapping (§8.13) are shown inline in Annex C's HMI; system health (§8.12), the lifecycle hooks (§3.14), defensive coding (§5.6), the AAS/MTP export (§11.8), north-bound telemetry (§11.9), utility/energy monitoring (§8.14, optional), and cybersecurity (§14) are cross-cutting and are demonstrated by the cell as a whole rather than a single object. Where a future annex touches them, it **shall** reference the relevant section rather than re-specify it.

Each annex **shall** show the same object in simulation and on hardware to demonstrate the unchanged contract (§2.6).

---

## 13. Versioning & Change Management

- This standard is versioned; each project records the standard version and the framework-library version it targets.
- The framework library follows semantic versioning. A breaking change requires controls-engineering sign-off and a migration note; projects adopt new major versions on a planned basis, not silently.
- Deviations approved under §1.5 are recorded in a project deviation register with rationale, scope, approver, and date.
- Changes to this standard are proposed through controls engineering; superseded requirements are retained as history so existing projects can be assessed against the version they targeted.

---

## 14. Cybersecurity (IEC 62443 & secure coding)

Functional safety (§9) protects people from the machine; **cybersecurity protects the machine and its data from the network.** They are separate disciplines and this standard treats them separately. Binding endpoint security (§11.2) is necessary but is only one control; this section frames the cell within IEC 62443 and mandates secure-coding practice.

### 14.1 Security level & zones/conduits

- **Target SL.** Each project **shall** declare a target Security Level (IEC 62443-3-3, SL 1–4) for the cell, sized to its risk; the controls below scale to that target.
- **Zones & conduits.** The cell **shall** be placed in a defined **zone**, with documented **conduits** to each external party — line/MES, engineering, and any smart-device sub-network (§3.15). Each conduit declares its protocol, direction, and security policy. The conduit to engineering (project download/debug) **shall** be access-controlled and **shall not** be permanently open on the production network.

### 14.2 Secure PLC coding practices

The standard **shall** apply the recognized secure-PLC-coding practices; most are already required elsewhere and are gathered here:

- **Validate all external input.** Recipe/host payloads (§3.8/§11.4), carrier/part data (§3.16), and command arguments and array indices (the defensive-coding rule, §5.6) **shall** be range/format-checked before use, faulting with a `ReasonCode` rather than acting on bad data. This is both a reliability and a security control.
- **Fail safe by default.** Outputs are non-stored and step-bound (§6.10); a lost link (§3.15), lost recipe (§3.8), lost time sync (§2.7), or lost safety alias (§9.2) drives a **defined safe reaction**, never an undefined state.
- **Least privilege.** Authenticated binding roles (operator / maintenance / engineering, §11.2) **shall** gate writes, mode changes, shelving (§8.10), and reconnect/manual functions (§7.6); anonymous or unauthenticated write is prohibited.
- **No secrets in source.** Endpoints, credentials, and keys **shall** be configuration/secret-store values (§11.4, §3.15), never literals in module code or version control.
- **Integrity & monitoring.** The running project/firmware **shall** carry a version/identity stamp (§13) checkable at runtime; fieldbus, IPC, and link anomalies surface as System alarms (§8.6, §10.5, §3.15) so tampering or unexpected disconnects are visible, not silent.
- **Minimize attack surface.** Unused services/ports on the IPC **shall** be disabled; only the documented conduits (§14.1) are reachable.

### 14.3 Governance

Security-relevant changes — conduit/endpoint changes, role changes, credential rotation — **shall** follow the change process of §13 (MOC), and the audit log **shall** record privileged actions (writes, mode changes, shelving, downloads).

*Cross-references: §9 (functional safety — separate discipline), §11.2 (binding endpoint security), §3.8/§11.4 (validated providers), §3.15 (device conduits/links), §3.16 (part-data input), §5.6 (defensive coding), §13 (MOC & versioning).*

---

*End of Fraktal Core — Part I (draft, §1–§14). Platform binding: `Fraktal_TC3_Part_II.md` (Fraktal/TC3).*
