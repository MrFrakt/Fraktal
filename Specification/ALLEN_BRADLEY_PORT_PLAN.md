# Allen-Bradley (Logix) port — implementation plan

Status: **plan, not a commitment**. Nothing in `FraktalCore/PLC/Allen-Bradley/`
exists yet; the directory is reserved. This document states what a second
binding has to deliver, the architectural problems that make it hard, the
recommended controller/HMI communication path, and the evidence-gated order in
which to find out whether the plan survives contact with the platform.

**Communication decision:** use **EtherNet/IP explicit messaging (CIP symbolic
tag access)** as the recommended controller-facing interface. Put a **Fraktal
gateway** between Logix and the generic HMI; the gateway projects the live
controller contract onto the existing versioned WebSocket/REST repository
protocol. OPC UA remains a permitted interoperability projection, not a
prerequisite for the Allen-Bradley binding.

O8 says the normative model is platform-neutral and each platform is served by a
binding. **A second binding is the test of that claim, not a consequence of it.**
Until one exists, "platform-neutral" is a design intention that has never been
falsified.

---

## 1. What a binding must deliver

`Fraktal_TC3_Part_II.md` is the template. The Allen-Bradley binding is
`Fraktal_AB_Part_III.md`, and it answers the same questions, and the list is the scope definition:

| Binding section | What Fraktal/AB must fix |
|---|---|
| §1 identity & baseline | controller families, firmware revisions, Studio 5000 version |
| §2 environment | toolchain, library distribution, **source-control form**, time sync |
| §3 language & wiring | how a module type is expressed, how children are injected, how the contract is published |
| §4 project settings | task/program structure, scan model |
| §5 quality tooling | unit-test framework and CI runner |
| §8 diagnostics | timing sources, system health, signal tower, alarm rationalization |
| §9 safety | the certified safety system and its read-only boundary |
| §10 fieldbus | EtherNet/IP/CIP in place of EtherCAT; I/O and topology diagnostics |
| §11 connectivity | EtherNet/IP/CIP controller access, the Fraktal gateway, live self-description, security, and the host-event path; optional OPC UA projection |

Plus the two things that are *not* in the binding document and must also be
ported or replaced:
the **module library** (`Fraktal_Modules` equivalent) and the **gates**
(`plc_lint`, build, unit-test runner) — because a binding without gates is a
binding whose conformance is a hope.

---

## 2. The blocker, stated exactly

**Fraktal Core's technology baseline assumes the IEC 61131-3 OOP extensions.
Logix has none of them.**

This is not a detail to work around late. Part I makes it normative today:

- §2.2: *"New module types **shall** extend the appropriate tier base, never
  re-implement the lifecycle."*
- §3.14: *"Every overridden hook **shall** call `SUPER^.OnX(...)` as its first
  statement."*
- §5.5: base types *"rely on OOP (interfaces, methods, inheritance, constructor
  injection) that only ST expresses."*
- §1.1: *"The Core assumes only IEC 61131-3 (with the OOP extensions where the
  framework requires them)."*

Measured surface of what those clauses are load-bearing for:

| | Fraktal_Core | Fraktal_Modules |
|---|---:|---:|
| objects | 152 | 57 |
| function blocks | 28 | 12 |
| **methods** | **309** | **59** |
| properties | 23 | 1 |
| **interfaces** | **17** | 0 |
| `EXTENDS` | 8 | 10 |
| `SUPER^` calls | 20 | 23 |
| `REFERENCE TO` | 9 | 20 |
| `__QUERYINTERFACE` / `__ISVALIDREF` | 6 | 13 |

The inheritance spine is up to **five levels deep**
(`FB_ModuleBase → FB_ControlModuleBase → FB_AsciiDeviceCM → FB_TcpVisionCM →
FB_Iv3VisionCM`), and the 17 interfaces exist to be held polymorphically —
`Awaits : I_Module` is what makes §6.9 diagnosis work for *any* awaited child
without naming its type.

Logix offers Add-On Instructions: no inheritance, no methods, no interfaces, no
dynamic dispatch, no recursion, and no reference type. It does offer ST, Ladder,
FBD and SFC, UDTs, InOut parameters passed by reference, and arrays of UDTs.

### Three ways through

**(A) Amend Core so the obligation is neutral and inheritance is a TC3 binding
detail.** Restate §2.2 as *"the lifecycle shall be defined once and reused; a
concrete type supplies device logic only"* — an obligation about **where
behaviour lives**, not about `EXTENDS`. TC3 binds it with inheritance; AB binds
it with composition plus generation. Cost: a normative amendment to Part I and
§3.14, and a re-audit of every clause that names an OOP construct.

**(B) Keep Core OOP-normative and declare Logix out of scope.** Honest, cheap,
and abandons O8. It also makes "platform-neutral" false in the README.

**(C) Data-driven single AOI** — one generic module AOI whose behaviour comes
from a configuration table, no per-type code at all. Very AB-idiomatic and it
sidesteps inheritance entirely, but it discards the type-level test story (§5.7
proves *types*), and a table expressive enough for every device becomes its own
undocumented language.

**Recommendation: (A).** It is the only option that keeps O8 true, and the
amendment it forces is one Core arguably owes anyway — the current wording
confuses *what must be guaranteed* with *how TwinCAT happens to guarantee it*.
Doing the port is what proves the distinction is real.

---

## 3. The four mechanisms that need a new binding

Everything else is arithmetic. These four are design.

### 3.1 Inheritance → composition + generation

Template-method inheritance (`base.Cyclic()` calls the derived `_M_Dispatch`)
inverts, because there is no dispatch: the **concrete AOI drives**, and calls the
base AOI around its own logic.

```
FRK_CylinderCM (AOI)
  ├─ FRK_ModuleBase_Begin(Ctx)   ← edges, Execute latch, state entry, timing start
  ├─ <the device CASE — the only hand-written part>
  └─ FRK_ModuleBase_End(Ctx)     ← state mapping, drop-reset, publication, rollup
```

`Ctx` is one InOut UDT carrying the module's whole contract, so the base halves
share state without globals. The two calls plus the parameter list are
**generated**, not typed — this is item **G2** of
[`AI_DEVELOPMENT_AND_AUTOMATION.md`](AI_DEVELOPMENT_AND_AUTOMATION.md), and the
port is the reason to build it properly.

*Consequence to accept honestly:* "forgetting the call" becomes possible again,
which Part I §1.1's trimming rule explicitly forbids ("a project shall never be
required to remember a call for correctness"). The mitigation is that the calls
are generated and a lint rule proves every module AOI has both, in order —
enforcement moves from the compiler to the gate. That is weaker, and the plan
should say so rather than pretend otherwise.

### 3.2 Polymorphism → a module registry with integer handles

`Awaits : I_Module` becomes `Awaits : DINT` — an index into a controller-scope
`FRK_Registry : FRK_ModuleStatus[N]`. Every module registers itself once at
first scan; the §6.9 walk, the rollup, and the HMI mirror all read the registry
rather than following references.

This is arguably **better** than the interface version: the registry is a flat,
bounded surface, which is exactly what the EtherNet/IP gateway needs to mirror.
It also bounds discovery cost statically (O4). Raw registry rows are not the
external self-description contract; the manifest in §4 gives them stable
identity and meaning.

### 3.3 References → InOut parameters and indices

`REFERENCE TO FB_CylinderCM` (29 uses across the two libraries) splits:

- **child ownership** → the child AOI instance lives in the parent's UDT, passed
  as InOut where needed;
- **loose coupling** (`I_RecipeProvider`, `I_PartCarrier`, `I_EventSink` — the
  provider pattern) → a **provider index + a dispatch routine**. One `CASE` per
  provider kind, in one place, replacing 17 interfaces with a small number of
  enumerated seams. Fewer seams than the TC3 binding, deliberately.

### 3.4 Strings

Fraktal's contract is string-heavy: `STRING(255)` description keys and source
paths, `STRING(120)` step names and labels. Logix `STRING` is a UDT
(`LEN` + `DATA[82]`) and **cannot be an AOI Input or Output parameter** — only
InOut. Options: custom `FRK_STRING255`/`FRK_STRING120` UDTs passed InOut, or
replace operator-facing keys with **numeric key IDs** resolved in the HMI
catalogue.

The second is more interesting than it looks: the HMI already resolves keys
through a catalogue, and §8.9 already has a generated rationalization registry.
Numeric keys would shrink the published surface (O4) on **both** bindings. Worth
evaluating as a Core improvement rather than an AB workaround.

---

## 4. Recommended communication architecture

### 4.1 Decision and boundary

The Allen-Bradley binding **should use EtherNet/IP/CIP between Logix and one
Fraktal gateway**. The gateway then serves the existing Fraktal WebSocket/REST
protocol consumed by the HMI repository abstraction:

```text
Logix controller
  FRK_Manifest + FRK_Registry + module contract tags
        │
        │  EtherNet/IP explicit messaging / CIP symbolic access
        ▼
Fraktal gateway
  discovery · UDT decoding · batching · freshness/quality · write acknowledgement
        │
        │  versioned Fraktal WebSocket/REST protocol over TLS
        ▼
Generic Flutter HMI
  existing PlcRepository boundary; no station- or module-type screens
```

This is a **binding mechanism**, not a second Fraktal data model. The module
identity, hierarchy, contracts, release reports, diagnostics, command handshake,
and access decisions remain the Core source of truth. EtherNet/IP transports the
Logix representation; the gateway normalizes it into the same semantic snapshot
the HMI already consumes.

Direct EtherNet/IP from the Flutter application is not the reference design:

- Flutter Web cannot open the raw industrial-protocol sockets, so it needs a
  gateway in every case;
- a native CIP stack in each desktop/mobile build would duplicate UDT decoding,
  batching, reconnect, security, and compatibility logic;
- one gateway gives native and Web clients identical discovery and write
  semantics and keeps PLC-protocol credentials out of operator clients.

### 4.2 Live self-description: `FRK_Manifest`

Raw symbolic tag browsing does not by itself satisfy §3.10. The controller shall
publish a bounded, controller-resident `FRK_Manifest` generated from the same
source as the AOIs and registry. At minimum it identifies:

- protocol and schema version plus a monotonic configuration revision;
- each deployed root and module's stable ID, parent ID, local name, canonical
  qualified path, tier, type, and capability flags;
- the registry/contract location needed to obtain its standard data;
- supported command, manual, decision, state, I/O, and optional-profile
  catalogues, using bounded references or numeric keys rather than copied text;
- declared limits and feature flags so a client never infers capabilities from
  an absent or guessed tag.

The gateway reads the manifest at connect and whenever its configuration
revision changes, validates it before accepting data, and rejects incompatible
schema versions explicitly. A generated L5X file on disk may be an engineering
artifact, but it is **not** the runtime source of truth and cannot replace the
live manifest. This preserves zero per-station HMI code and prevents the HMI
from reverse-engineering Logix naming conventions.

**This is a deliberate, bounded O9 exception and shall be treated as one.** The
manifest necessarily restates what the AOIs and the registry already encode, and
§1.1 O9 requires one authoritative source per fact, derived and never duplicated.
It is admissible only because the manifest is **generated** from the same
declaration as the AOIs, the registry indices and the numeric keys — which makes
the generator the authoritative source and moves the risk into it. Two
obligations follow, and both are normative for the binding: the manifest is never
hand-edited, and a gate proves manifest ↔ registry ↔ AOI agreement on every
change (Phase 5). Without that gate a hand-edited AOI leaves the manifest quietly
describing a machine that no longer exists — the same failure class as a ladder
rung whose gate compiled and never ran.

### 4.3 Gateway responsibilities

The gateway owns all transport-specific work:

1. establish and supervise the EtherNet/IP/CIP session;
2. read and validate `FRK_Manifest`, then build the canonical module tree;
3. batch/fragment symbolic reads within measured controller and network limits;
4. decode Logix atomic types, arrays, strings, and UDTs into the repository's
   typed values;
5. preserve or derive explicit freshness, quality, source timestamp, server
   timestamp, and connection state—never present stale data as good live data;
6. expose the existing fast/slow/on-demand subscription tiers and aggregate
   demand across clients;
7. accept only the narrow Fraktal write vocabulary, validate type/range/target,
   perform the CIP write, and wait for the PLC acknowledgement rather than
   treating transport success as command acceptance;
8. discard pending writes on disconnect and require a fresh live snapshot before
   writes resume; and
9. expose bounded observability for session state, latency, read/write failures,
   manifest revision, controller identity, and protocol versions.

PLC access and release policy remain authoritative and re-check every action.
That defense in depth does not replace transport security. A deployment shall
either prove a supported CIP Security configuration or place the controller
side in an IEC 62443-aligned trusted cell/industrial zone with the gateway as
the controlled conduit; the client-facing side shall use authenticated TLS and
least-privilege roles. Anonymous controller writes are not an acceptable
baseline.

### 4.4 Alternatives and why they are not the default

| Path | Status | Consequence |
|---|---|---|
| **EtherNet/IP → Fraktal gateway → Fraktal WebSocket/REST** | **Recommended** | One Logix-specific adapter, works for Web and native HMI, preserves the existing repository and generic UI |
| Direct EtherNet/IP from native HMI | Optional experiment only | Still needs a gateway for Web and duplicates the CIP implementation/security surface |
| EtherNet/IP → commercial gateway → OPC UA → current OPC UA adapter | Permitted deployment alternative | Lowest custom transport work and useful for third-party interoperability, but adds middleware and still depends on OPC UA north-bound |
| Embedded Logix OPC UA → current OPC UA adapter | Permitted where supported and proven | Preserves the TC3-style path, but controller/firmware/node-budget availability no longer gates the AB binding |

OPC UA companion projections such as PackML, Machinery, Energy, AAS/MTP, and
third-party MES/SCADA access remain valuable optional north-bound profiles. They
shall be generated from the same live Fraktal model; EtherNet/IP does not create
a competing identity or hierarchy.

**Consequence for the conformance model.** §11.7 and Annexes F/J/K define those
projections *as OPC UA companion mappings*. If the AB binding serves them only
through the optional commercial-gateway route, then a composed claim such as
*"Fraktal Core + PackML"* is unconditional on TC3 and **conditional on the
deployment** on AB. §1.5 currently treats profile conformance as
binding-independent. Either the projections are restated against the
transport-neutral service of §4.5, or the conformance clause gains an explicit
per-binding qualifier. This is a specification decision, not an implementation
detail, and it belongs in Phase 1.

### 4.6 Two claims in this section that are aspirations, not inventories

Recorded so nobody plans against capability that does not exist yet.

**The gateway protocol is close to neutral, but not yet versioned.** Measured
against `HMI/gateway/lib/src/fraktal_gateway_server.dart`, the wire vocabulary is
already mostly repository semantics — `discoverPaths`, `discoveryRevision`,
`readValues`, `setReadTiers`, `snapshot`, `paths`, `truncated`, `plcReady` — which
is what makes this whole approach credible, and `discoveryRevision` maps directly
onto the manifest's configuration revision. But there is a `protocol` field and
**no version handshake**, and two OPC-UA-named diagnostic fields
(`lastOpcUaSuccess`, `lastOpcUaFailure`) still leak the transport. So Phase 2
**creates** the versioned neutral protocol; it does not adopt one. Budget it as
work on the TC3 side too, because both bindings must then speak it.

**The gateway becomes a required component on AB in a way it is not on TC3.**
With a native OPC UA server, any conforming client can reach the controller, and
the gateway is a Web convenience. On AB it is the only path for every client. The
PLC never depends on it — the machine runs, releases hold, and safety is
untouched if it dies — but the *operator interface*, including diagnostics, is
gone until it restarts. Treat it as cell-local infrastructure with a supervised
restart, and state the availability expectation in the AB Part III rather than
discovering it during a night shift.

### 4.5 Required Core and HMI-contract amendment

Part I currently makes OPC UA itself normative throughout the model—notably in
§3.10, §4.8, §7.7, and §11. To keep O8 honest, audit every such occurrence and
amend the Core clauses around a transport-neutral **Fraktal Self-Description
Service** whose required semantics are:

- live runtime discovery with stable canonical identities and hierarchy;
- typed values with explicit freshness/quality and synchronized timestamps;
- bounded subscriptions or equivalent bounded change detection;
- the narrow acknowledged command/write vocabulary;
- schema/protocol versioning and fail-closed compatibility handling;
- authenticated, encrypted, least-privilege access; and
- generated optional industry projections from the same source of truth.

The TC3 Part II binds that service to TF6100 OPC UA. The AB Part III binds it to
EtherNet/IP/CIP plus the Fraktal gateway and `FRK_Manifest`, while allowing OPC
UA as an alternative projection. `HMI_CONTRACT.md` should rename OPC-UA-specific
transport wording where it is really a repository semantic, while retaining
OPC-UA-specific rules inside the OPC UA adapter section. The UI/domain contract
and the PLC authorization rules do not change.

---

## 5. What ports unchanged

Stated to keep the estimate honest — this is most of the standard:

- the **three-tier model** and the recursion (§3.1–§3.3);
- the **data contract** `ParCfg`/`ParCmd`/`OutCmd`/`OutImm` — UDTs compose;
- the **PLCopen handshake** (§6.1) — it is a state machine, not a language feature;
- the **diagnostic model**, first-out, alarm rings, rationalization (§8);
- **sequences** (§6.8) — Logix has ST, Ladder, **and** SFC; the step-table form
  ports directly and the generator work already done applies;
- **safety separation** (§9) — GuardLogix is a different certified system with
  the same read-only boundary;
- the **generic HMI domain and UI**. It binds `PlcRepository`, not PLC-platform
  objects. The AB gateway shall emit the same versioned repository contract, so
  **no station screen or module-type screen is added**. Any implementation edit
  is confined to generalizing the existing gateway/transport adapter, not the
  rendering or control model. That is the single most convincing demonstration
  this port could produce.

---

## 6. Unknowns to settle before committing (spikes)

These are time-boxed proofs, not implementation phases, and each can invalidate
the plan. **Do these first.** I do not have a Logix toolchain here, so every line
below is a question until Phase 0 records controller-backed evidence.

| # | Spike | Kills the plan if… |
|---|---|---|
| S1 | **EtherNet/IP/CIP data path** on the target controller/firmware: symbolic reads/writes, controller- and program-scoped tags, UDTs, arrays, strings, fragmentation, connection limits, and External Access rules | the standard contract cannot be moved reliably or within the required update budget |
| S2 | **AOI parameter rules** for the target firmware: UDT In/Out, string handling, InOut aliasing, nesting depth | contract cannot be passed → §3.1's `Ctx` design fails |
| S3 | **Scale**: instances, memory and scan cost for a realistic forest (say 60 modules), plus gateway read volume, update latency, and reconnect time | registry/rollup or the communication budget does not fit the application |
| S4 | **Source-control form**: L5X export fidelity — is it round-trip stable and diffable? | no text form → no lint, no generation, no gates (§2.5 is a *shall*) |
| S5 | **Unit-test framework**: what plays TcUnit's role on Logix | no runner → §5.7 per-type suites cannot be a shall |
| S6 | **Online change** semantics vs. the module registry | registry cannot be extended online → commissioning workflow changes |
| S7 | **Live manifest round trip**: generate `FRK_Manifest`, read it over CIP, reconstruct a multi-root tree, detect a revision, and reject a bad schema | runtime self-description cannot be made authoritative without per-station HMI configuration |
| S8 | **Security and deployment**: supported CIP Security capability, otherwise the exact cell-zone/conduit controls; gateway TLS, identity, role mapping, certificate and update lifecycle | writes cannot be protected to the §14 threat model |
| S9 | **Repository-semantic parity**: map Logix values to typed values, freshness/quality/timestamps, tiered subscriptions, acknowledged commands, disconnect behavior, and host-event traversal | the AB HMI behaves differently or can act on stale/ambiguous data |
| S10 | **Optional OPC UA projections**: embedded-server and commercial-gateway support, budgets, and licensing on candidate deployments | never kills the native AB path; it only determines which optional interoperability profiles can be claimed |

S1, S4, S7, S8, and S9 decide whether this is a conforming port. S10 no longer
decides whether the generic HMI is possible.

---

## 7. Execution order and exit evidence

Each phase ends in evidence, in the style of `FIRST_PROJECT_AGENT_GUIDE.md`.

Do not begin the full base or module library before the communication and
source-control risks are closed. Quality gates are added with the feature they
protect, not postponed until the end.

**Phase 0 — platform and communication spikes.** Run S1–S10 against named
controller, firmware, Studio 5000, gateway-host OS, and representative network
hardware. Capture L5X, packet/latency measurements, screenshots/logs, and a
repeatable test procedure. *Exit:* a written answer to every spike; S1/S4/S7/S8/
S9 have a conforming mechanism and quantified budget; explicit go/no-go.

**Phase 1 — Core decisions and amendments.** Restate §2.2, §3.14 and §5.5 so the
lifecycle obligation is neutral and `EXTENDS`/`SUPER^` are TC3 bindings. Define
the Fraktal Self-Description Service from §4.5, then re-audit Part I for both OOP
and OPC-UA mechanism leaks. Move TF6100/browse-node/session details to TC3 Part
II without weakening the existing TC3 conformance claim. *Exit:* Part I names
required behavior rather than a platform mechanism; TC3 Part II still binds
every moved requirement; the normative diff and objective impact are reviewed.

**Phase 2 — AB binding and gateway contract.** Write `Fraktal_AB_Part_III.md`, the
normative `FRK_Manifest` schema, the EtherNet/IP tag/external-access rules, the
gateway protocol mapping, security profile, supported-version matrix, and
performance budgets. Update the transport-specific portions of
`HMI_CONTRACT.md`. *Exit:* every Core `shall` has a named AB mechanism or a
recorded deviation; manifest and gateway schemas are versioned before code.

**Phase 3 — communication vertical slice.** Implement the smallest controller
fixture containing one root, one simulated CM, `FRK_Manifest`, registry/status,
and one acknowledged command. Implement the EtherNet/IP adapter in the Fraktal
gateway and feed the existing repository protocol. *Exit:* the existing generic
HMI discovers, renders, and commands the fixture with no station/type UI code;
schema mismatch, stale data, disconnect, rejected write, and reconnect tests all
fail closed; measured latency stays within the Phase 2 budget.

**Phase 4 — runtime base.** Implement `FRK_ModuleBase_Begin`/`_End`, the registry,
the handshake, diagnostic/event core, release/access enforcement, manifest
publication, and one provider seam. Add runnable base tests as each behavior
lands. *Exit:* a single hand-written CM satisfies the applicable Core lifecycle,
diagnostic, release, reset, abort, and communication tests against simulated I/O.

**Phase 5 — generator and structural gates.** Implement module-type generation
(**G2**) so composition boilerplate, manifest entries, numeric keys, and L5X
shape are generated from one source. Add AB lint/build checks for Begin/End
ordering, registry/manifest consistency, reason/key collisions, bounded indices,
and forbidden raw project coupling. *Exit:* a new type is generated, round-trips,
compiles, and passes; each deliberately broken invariant is rejected by a named
gate.

**Phase 6 — reusable module library.** Port the first representative set from
`Fraktal_Modules`—cylinder, clamp, digital input, power group, two-hand, and air
monitor—through the generator, each with its type-specific suite. *Exit:* all
base and per-type tests pass on the isolated AB runner, and a scan/network budget
report shows proportional scaling.

**Phase 7 — integration bench and generic HMI proof.** Compose an AB internal
feature-testing bench equivalent in coverage—not identity—to the press bench.
Exercise multi-root discovery, modes, sequences, diagnostics, release policy,
manual commands, recipe/changeover, I/O topology, events, access levels, and
fault recovery through EtherNet/IP and the gateway. *Exit:* the generic HMI
operates the Logix bench without station/type UI code; all PLC and gateway
integration suites pass; optional OPC UA projection, if claimed, resolves to the
same canonical identities.

**Phase 8 — full conformance and objective audit.** Audit implementation,
generator, gateway, HMI contract, AB Part III, and amended Core clause-by-clause
against O1–O9. Close gaps in the owning layer: implementation when behavior is
wrong, binding/specification when a platform mechanism leaked into Core, or a
new mechanism when neither satisfies the objective. Re-run security, scale,
failure-recovery, source-round-trip, and compatibility tests. *Exit:* no
unexplained deviations; evidence is reproducible; build/lint/test/conformance
gates run on every AB change; remaining limitations are explicit versioned
binding constraints rather than silent exceptions.

---

## 8. The dividend

Whether or not the port ships, Phase 0–2 pay for themselves:

1. **It falsifies or confirms O8.** Right now nothing does.
2. **It separates obligation from mechanism** in Part I. Any clause that cannot
   be restated without naming a TwinCAT construct is a clause that was never
   platform-neutral, and finding those is worth doing regardless.
3. **Two of the AB workarounds look like Core improvements** — the flat module
   registry (§3.2) and numeric keys (§3.4) would reduce published surface and
   discovery cost on TwinCAT too (O4).
4. **It proves transport neutrality at the repository boundary.** The same HMI
   domain and UI consume TC3/OPC UA and AB/EtherNet/IP gateway data without
   station/type code.
5. **It forces the generators.** The TC3 binding can survive on hand-written
   boilerplate because the compiler enforces the shape. The AB binding cannot,
   so G2 stops being a nice-to-have.

---

## 9. Honest estimate

Not a schedule — a shape. Phase 4 is the one that dominates, and Phase 0 is the
one that decides whether the rest happens.

| Phase | Relative size | Note |
|---|---|---|
| 0 spikes | small–medium | communication, source, security, and semantic-parity proof gates everything |
| 1 Core amendment | medium | OOP + self-description normative edit and re-audit |
| 2 binding/gateway contract | medium | binding document plus manifest, protocol, security, and budgets |
| 3 communication vertical slice | medium | new CIP adapter, but deliberately tiny PLC scope |
| 4 runtime base | **large** | the 309 Core methods do not disappear, they change shape |
| 5 generator + structural gates | medium | reuses the approach already proven for ladder/L5X generation |
| 6 library | medium | representative types, mechanical only after Phases 4–5 |
| 7 integration bench + HMI | medium | the UI is reusable; parity, scale, and failure cases are not free |
| 8 conformance audit | medium | clause/objective audit, gap closure, release gates, evidence |

The thing to resist is starting with the full runtime base because it is the
interesting part. Phase 0 answers whether the platform, transport, security, and
source form are viable; Phases 1–2 decide what the implementation is allowed to
look like; Phase 3 proves the complete communication boundary before the large
port begins.

**The total grew, and that is the right direction.** An earlier draft of this
plan had seven phases and treated OPC UA availability as the decisive risk. Two
phases were added — a communication vertical slice before the base, and a closing
conformance audit — and gates moved from a final phase into the phase that
introduces what they protect. Every one of those changes makes the plan longer
and the first failure cheaper. A plan that discovers in month six that the
transport cannot carry the contract is not a shorter plan; it is the same plan
with the bad news deferred.

---

## 10. Primary implementation references for the spikes

- Rockwell Automation, [*Logix 5000 Controllers Data Access Programming
  Manual*](https://support.rockwellautomation.com/ci/okcsFattach/get/1057724_5)
  (`1756-PM020`): EtherNet/IP/CIP access from external applications.
- Rockwell Automation, [*Studio 5000 Logix Designer — Configuring Message
  Instructions*](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/37-00/contents-ditamap/studio-5000-logix-designer/configuring-message-instructions.html):
  CIP Data Table Read/Write and symbolic program paths.
- Rockwell Automation, [*FactoryTalk Edge Gateway — Add a data source from
  Studio 5000 Logix Designer via
  EtherNet/IP*](https://www.rockwellautomation.com/en-us/docs/factorytalk-edge-gateway/distributed-1-00/ft-edge-gateway-help-ditamap/data-sources/data-source-configuration/add-ds-from-st5kld-via-ethip.html):
  vendor evidence for EtherNet/IP namespace acquisition and gateway use.
- ODVA, [*EtherNet/IP Technology
  Overview*](https://www.odva.org/publication_download/ethernet-ip-technology-overview/):
  explicit messaging, CIP object model, and HMI/client use; obtain the licensed
  current CIP Networks Library before implementing protocol details.

Record exact publication revisions and URLs in the Phase 0 evidence. Vendor
documentation and the licensed ODVA specification—not assumptions from a
third-party client library—are authoritative for supported services and wire
behavior.
