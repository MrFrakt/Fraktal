# Fraktal/AB — Allen-Bradley (Logix) Binding (Part III)
*Unified PLC Programming Standard · **Part III: the Allen-Bradley Logix binding of Fraktal Core***

**Status:** **Draft — R0 complete; spike-ready, not implementation-ready.** Part III of III (Part I: `Fraktal_Core_Part_I.md`; Part II: `Fraktal_TC3_Part_II.md`)
**Platform:** Rockwell Automation Logix (ControlLogix / CompactLogix / GuardLogix) · Studio 5000 Logix Designer · IEC 61131-3 subset **without** the OOP extensions

> Every clause in this Part **binds** a Core contract and cites it as **Core §x.y**; a binding clause carries the number of the Core clause it realizes. Nothing here introduces new normative model content — tiers, contracts, state machines, diagnostics and routing live in Part I. A port to another platform re-implements this document only (Core §1.1 O8).

---

## AB §0 — How to read this document

This Part was written **before** the Phase 0 spikes of
[`ALLEN_BRADLEY_PORT_PLAN.md`](ALLEN_BRADLEY_PORT_PLAN.md). That is deliberate:
a binding document with explicit holes drives a spike programme far better than
a spike list drives a document. But it means the two kinds of clause here must
never be confused.

| Marker | Meaning |
|---|---|
| *(unmarked)* | **Fraktal's decision to make.** Architecture, naming, structure, generation and gate rules. Normative now; changing it is a specification change. |
| **[PROVISIONAL Sn]** | **Depends on Rockwell platform behaviour not yet verified on a controller.** Reflects the current best understanding, is not a conformance claim, and is settled by spike `Sn`. |

**No `[PROVISIONAL]` clause may be cited as conformance evidence.** Phase 0
either confirms the clause, rewrites it, or escalates to a Core amendment.
AB §12 is the register of every one of them.

**Implementation-readiness rule.** Only disposable Phase 0 fixtures may be
written while this document is pre-spike. Runtime/library implementation shall
not begin until all of these gates are recorded as PASS:

| Gate | Status | Required evidence |
|---|---|---|
| R0 Core authority | **PASS** | OOP-neutral lifecycle and transport-neutral Self-Description Service accepted in Core, with TC3 re-audited; evidence: [`AB_R0_CORE_AUTHORITY_EVIDENCE.md`](AB_R0_CORE_AUTHORITY_EVIDENCE.md) |
| R1 platform baseline | **OPEN** | named controller catalogue, firmware, Studio 5000 edition/version, communication module, and gateway-host baseline |
| R2 executable shape | **OPEN** | S1/S2/S4/S11/S12 prove CIP, both sequence execution forms, L5X fidelity, scan ordering, restart behavior, and the physical type map |
| R3 frozen contracts | **OPEN** | versioned manifest, mailbox, registry, repository-handshake, quality/timestamp, and host-event schemas |
| R4 gates | **OPEN** | automated L5X regeneration/lint plus controller Verify/Build and import checks run from a clean checkout |
| R5 test execution | **OPEN** | a disposable reference AOI suite runs through the intended Logix Echo or named isolated-hardware CI path and emits machine-readable results; full base/type suites then grow with implementation |
| R6 security | **OPEN** | S8 records the controller zone/conduit, writable-tag allow-list, gateway identity/TLS/role model, secret handling, and update lifecycle |

A failed gate changes this binding or stops the port; it is not converted into
an undocumented implementation exception. Passing this documentation audit
means the spike programme is complete enough to start—not that these open gates
have already passed.

**R0 authority is settled.** Core §2.2/§3.14/§5.5 now defines the lifecycle
obligation independently of inheritance and permits a binding to discharge it
through machine-checked generated composition. Core §3.10/§4.8/§7.7/§11 now
defines the transport-neutral **Fraktal Self-Description Service** and
binding-qualified optional projections. Part II continues to bind that service
to TF6100 OPC UA; this Part binds it by default to EtherNet/IP explicit messaging
plus the Fraktal gateway, with OPC UA as an alternative. The exact amendments,
objective check and TC3 compatibility audit are recorded in
[`AB_R0_CORE_AUTHORITY_EVIDENCE.md`](AB_R0_CORE_AUTHORITY_EVIDENCE.md).

---

## AB §1 — Binding identity & technology baseline

*Binds Core §1.1 (technology baseline), §1.2 (scope), §1.6 (definitions).*

**Fraktal/AB** is the Allen-Bradley Logix binding of Fraktal Core. Conformance
claims compose as *"Fraktal Core + Fraktal/AB (+ profiles)"* (Core §1.1 O8).

**Technology baseline.** Logix controllers programmed in Studio 5000 Logix
Designer, using Add-On Instructions, UDTs and the IEC-subset languages Logix
provides (ST, Ladder, FBD, SFC); **EtherNet/IP (CIP)** for fieldbus and device
integration (AB §10); **GuardLogix / CIP Safety** for functional safety (AB §9);
**EtherNet/IP explicit messaging plus one Fraktal gateway is the default** for
connectivity and self-description (AB §3.10, AB §11); the same generic Flutter
HMI **domain and UI** consumes the same repository contract (Core §3.13). The
gateway and repository transport adapter require the neutral protocol work in
AB §11.3; “same HMI” never means “no transport implementation changes”.

**Alternative connectivity.** OPC UA remains a permitted alternative transport
or north-bound projection—embedded where the named controller/firmware supports
and proves it, or through a gateway (AB §11.7–§11.11). It is never a prerequisite
and does not replace EtherNet/IP as the Fraktal/AB default.

**Binding definitions** (extends the Core §1.6 table):

| Term | Meaning |
|---|---|
| AOI | Add-On Instruction — the Logix reusable code unit. No inheritance, methods, interfaces or dynamic dispatch. |
| UDT | User-Defined Type — the Logix structure type. Composition only. |
| L5X | The Studio 5000 XML export/import form (AB §2.5). |
| CIP / EtherNet/IP | Common Industrial Protocol / its Ethernet transport (AB §10, AB §11). |
| `FRK_Manifest` | The controller-resident live self-description record (AB §3.10). |
| `FRK_Registry` | The controller-scope array of module contract rows (AB §3.2). |
| Fraktal gateway | The host process translating CIP into the Fraktal repository protocol (AB §11.2). |

---

## AB §2 — Development & runtime environment

### AB §2.1 Toolchain & versions
*Binds Core §2 (pinned-toolchain rule).*

- The **exact** Studio 5000 Logix Designer version, controller catalogue number
  and firmware revision **shall** be pinned per project and recorded; every
  station on a line uses the same pinned versions.
- The framework requires **no** language extension beyond the Logix base
  instruction set and AOIs. Where Part II relies on OOP, this binding relies on
  **composition plus generation** (AB §3.14).

### AB §2.2 Library distribution
*Binds Core §2.2.*

- The framework ships as a **versioned set of AOI and UDT definitions** exported
  as L5X, plus the generator that emits per-type code (AB §5.2). A project
  imports a pinned release; it never copies and edits a framework AOI.
- AOI definitions carry a **Revision** and **Revision Note**; the Fraktal
  semantic version **shall** be recorded there and in the manifest, so a running
  controller can be asked which framework version it holds.
- **[PROVISIONAL S2]** Logix AOI *signature* changes are breaking for existing
  instances on import. The Core §1.5 rule — additive minor, breaking major —
  therefore binds more tightly here than on TC3: an added AOI parameter is
  expected to be a **major** step in this binding, not a minor one. Confirm the
  import/upgrade behaviour before fixing the rule.

### AB §2.4 Project & controller settings
*Binds Core §2 note; baseline in AB §4.1.*

- Controller firmware major revision and Logix Designer major version **shall
  match** and the tested minor/build pair shall be recorded in the binding
  evidence. A project may claim only controller families in that matrix.
- Required licensed components—Logix Designer edition, Logix Designer SDK,
  FactoryTalk Logix Echo, and the gateway's CIP stack—shall be named with their
  versions. “Available on a developer workstation” is not a CI baseline.
- Source protection shall not encode any generated AOI/routine needed by lint,
  regeneration, review, or conformance evidence. A delivered release may be
  signed/sealed only after its clear reviewed source and reproducible signature
  input are archived.

### AB §2.5 Source-control form
*Binds Core §2.5.* **The text-diffable storage form is L5X export.**

This is load-bearing far beyond source control. Every Fraktal gate — lint,
generation, manifest-consistency, structural checks — reads the exported text.
A binding whose source cannot be exported, diffed and re-imported faithfully
cannot be gated, and Core §1.5 makes a CI/lint gate a *shall*.

- The exported L5X **shall** be the reviewed artifact. Generated code is
  generated *into* L5X, never typed into the IDE and exported afterwards.
- **[PROVISIONAL S4]** L5X round-trip must be **stable** — export → import →
  export produces an equal document modulo a declared ignore-list (timestamps,
  edit metadata). If it is not stable, the gate compares a *canonicalised* form,
  and AB §5.3 defines that canonicalisation. If it is not faithful, the binding
   is not viable in its present shape and Phase 0 escalates.

### AB §2.6 Simulation
*Binds Core §2.6, §5.7.*

Every reusable type runs against the same semantic HAL in real and simulated
projects. Simulation selects generated semantic HAL tags; it never writes module
I/O tags directly or compiles a second behavior path. The preferred isolated
runner is FactoryTalk Logix Echo because it accepts the production controller
project without simulation-only controller logic. **[PROVISIONAL S5]** pins the
supported Echo/SDK/controller matrix, licensing, clean-snapshot procedure, and
whether physical hardware is still required for I/O, safety, motion, or timing
evidence. No test controller or emulator image is a production boot/download
artifact.

### AB §2.7 Time-synchronization mechanics
*Binds Core §2.7.*
**[PROVISIONAL S1]** Timestamps for the §8 diagnostic model come from the
controller wall clock, with CIP Sync (IEEE-1588) where the application requires
correlated multi-controller ordering. The Core requirement is unchanged: a
diagnostic carries the moment it became true, and whether that moment is
synchronized.

### AB §2.8 Restart, download, and retention classes
*Binds Core §2.3, §3.14, §6.1, §8.3, §13.*

The generated application shall distinguish at least: prescan; first normal
scan after Program→Run; warm restart; power-cycle restart; and first scan after
download. On every path, command `Execute`/`Abort`, sequence transition latches,
mailbox in-flight state, manual requests, and force requests initialize safe and
cannot self-resume. Retained recipe/configuration, access policy, lifetime
counters, and closed-event history are explicitly declared and schema-versioned;
everything not declared retained is treated as volatile.

**[PROVISIONAL S11]** fixes the exact AOI prescan/first-scan implementation and
proves that a download or mode transition cannot energize an output, re-issue an
old command, or replay a committed HMI request. The generator and gate shall own
the retention list; project engineers do not mark individual generated members
ad hoc.

---

## AB §3 — Language & wiring mechanics

### AB §3.1 The module type form
*Binds Core §2.2, §3.1–§3.3, §3.12.*

A reusable Fraktal module type has **one public module AOI plus one context UDT
family**. The generator may emit private nested service/sequence AOIs, but a
project sees one module call and never wires those helpers itself:

```
FRK_<Type>            AOI   — the public behaviour entry point
FRK_<Type>Ctx         UDT   — the whole contract for one instance
  Base : FRK_ModuleBase     — the common contract (Core §3.12), composed not inherited
  ParCfg : FRK_<Type>ParCfg
  ParCmd : FRK_<Type>ParCmd
  OutCmd : FRK_<Type>OutCmd
  OutImm : FRK_<Type>OutImm
  Priv   : FRK_<Type>Priv   — implementation state; External Access None
```

`FRK_ModuleBase` is a UDT, not a base class. **Tier is a declared field**
(`Base.Tier`), not a type relationship: `FRK_TIER_CM` / `_EM` / `_UNIT`. Core
§3.3's structural prohibition — no Unit inside an EquipmentModule — is therefore
not enforced by the compiler here and **shall** be enforced by a gate
(AB §5.3).

> This is the first place the binding is genuinely weaker than Part II. On TC3
> the type system rejects the illegal composition; here a linter does. Say so
> rather than implying parity.

A deployed application owner that selects the native-SFC execution form in
AB §3.5 also has an owner-local chart instance scheduled by its root program's
generated runner. That runner is an application execution shell, not a second
module type or contract: the owner still has one public `Ctx`, one public module
AOI, one lifecycle owner, and one manifest row. The runner only reset-calls and
schedules the SFC; it is never hand-wired by a project engineer.

### AB §3.2 Capability query and module identity
*Binds Core §3.2, §3.7, §3.9.*

There is no interface and no upcast, so `__QUERYINTERFACE` has no analogue.
Capability is **declared data**:

- every module registers one row in the controller-scope
  `FRK_Registry : FRK_RegistryRow[FRK_MAX_MODULES]`;
- a module reference — Core's `I_Module`, the sequence `Awaits`, the rollup
  parent link — is a **`DINT` registry index**, not a pointer. Index `0` means
  "none";
- capability is a bitfield `Base.Capabilities`, set by the generator from the
  type declaration. A client tests a bit; it never infers capability from the
  presence of a tag.

Registry indices are generated deterministically from the application
declaration and are internal handles, never durable external identity. Index
`0` remains reserved; adding/reordering modules may change indices only together
with `ConfigRevision` and a regenerated manifest. Each manifest module/key ID is
an explicit stable declaration ID with a collision gate—not an array ordinal or
unchecked hash. Renaming a canonical module path is an identity/configuration
change and follows the HMI's deterministic remapping rules; it is never hidden
behind a stale ID.

Bounds are normative: every index **shall** be range-checked before use
(Core §5.6), and a registry overflow is a fail-closed startup fault, never a
silent truncation.

**Why this is not merely a workaround.** The registry is a flat bounded array
with static discovery cost (Core §1.1 O4), and it is exactly the shape the
gateway must mirror. Evaluate it as a Core improvement for Part II too
(plan §8).

### AB §3.3 Public contract parameter classes
*Binds Core §3.10(a′)/(a″), §3.12, §6.1.*

Rockwell's AOI contract restricts `Input`/`Output` to atomic types and requires
structures/arrays to use `InOut` (passed by reference). The binding is therefore:

- the whole contract travels as **one `InOut` parameter**, `Ctx`, of the type's
  `Ctx` UDT. Both base halves and the device logic see the same instance;
- `EnableIn`/`EnableOut` are **not** used as application logic. The module runs
  every scan (Core §2.2);
- an AOI `InOut` parameter is not itself externally addressable; access is
  controlled on the connected controller/program tag and its data-type members;
- `Priv`, every implementation-only AOI local tag, provider state, and scratch
  buffer **shall** be `External Access: None`;
- published contract members are `Read Only`; the root request/configuration
  mailbox in AB §7.7 is the **only** `Read/Write` Fraktal surface, and the PLC
  re-checks every committed request. The gateway never writes an individual
  module `Ctx` member even if a permissive engineering project would allow it.

The Core rule is unchanged and is what matters: a client may request through the
published request surface, and the PLC decides.

**[PROVISIONAL S2]** verifies the exact target's InOut count/size, nested-AOI
depth, member External Access behavior over CIP, local-tag visibility, and import
upgrade behavior. If private state cannot be excluded while the public contract
is readable, split `Ctx` into a read-only public UDT and an inaccessible private
state UDT; never publish private state as the workaround.

### AB §3.4, §3.6–§3.7 Mode, device, and cascade mechanics
*Binds Core §3.4–§3.7, §6.1, §6.3, §6.4.*

The state machines and ordinals port unchanged. Their Logix execution rules are:

- every deployed module AOI is invoked **unconditionally exactly once** in the
  generated periodic scan path. In Ladder its incoming rung is always true; in
  ST the call is unconditional. `EnableIn`/`EnableOut` never select Fraktal
  behavior. A conditional call is a `G-CYCLIC` failure because it skips edge,
  timeout, hold, abort, rollup, and Execute-drop handling;
- Unit mode, start/stop/reset, manual, decision, configuration, alarm, and power
  requests arrive only through the root mailbox in AB §7.7. Parent-to-child
  commands are internal `Ctx` data and are not separate external write targets;
- one generated owner writes each sequence token and one generated invocation
  owns each child AOI. Two routines/AOIs never command the same child in one
  scan;
- child Unit mode cascade and awaited-child rollup use validated registry
  indices. Index `0` means absent, never module zero; and
- `OperatorReset` closes the MANUAL_RESET event and recursively releases the
  Unit command plus every child command issued by the suspended chain. It clears
  latches, not live conditions, and therefore cannot bypass a release gate.

Mode-switch, graceful-exit, run-style, single-step, unsupported-command, abort,
hold, and Execute-drop semantics remain exactly Core §3.4/§6.1 behavior. The AB
test matrix in §5.7 proves the same observable transitions rather than defining
a Logix-specific variant.

### AB §3.5 Sequence binding
*Binds Core §3.5, §5.5, §6.2–§6.3, §6.8.*

Studio 5000 supports native SFC routines. The restriction is narrower: an AOI's
primary logic supports LD/FBD/ST, and an AOI cannot `JSR` a project routine.
Fraktal/AB therefore defines **two generated execution forms** over the same
`Seq : FRK_SequenceCtx` contract and the same observable Core semantics:

1. **AOI-contained ST/LD (reference form).** A multi-step sequence is a
   generated sequence AOI nested by its owning Unit or EM AOI. Its ST primary
   logic is the Core §6.8 `CASE Seq.Step OF` skeleton; generated Ladder is
   permitted on the same integer-state-machine rule. This form is reusable and
   available at every permitted owner tier.
2. **Program-owned native SFC (graphical form).** A generated program-level
   routine hosts the chart and the root program's generated main routine calls
   it as a subroutine. The initial claim covers application-owned Unit mode and
   EM command chains. Because Logix SFC step/action tags hold chart state, the
   generator emits one routine/tag set per deployed owner; it never calls one
   stateful chart concurrently for multiple instances. A reusable library AOI
   therefore retains the ST/LD form unless application generation deliberately
   materializes and proves an SFC instance from its single graph declaration.

The SFC runner has this generated order:

```text
1. Call the root module AOI (owner + every nested module, exactly once).
2. For each generated application-owned chart instance:
   a. issue SFR on a declared reset/re-entry edge; then
   b. JSR the owner-local SFC only while that owner command is BUSY.
```

This order deliberately gives SFC-issued child intent to the module AOI on the
next periodic scan. It lets the owner finish lifecycle/rollup first and keeps
every module AOI unconditional. The one-scan latency and all terminal/error/reset
edges are part of the S11 parity proof, not an undocumented scheduling accident.

The graphical form has additional binding rules:

- every step has one non-Boolean **N (Non-Stored)** action containing generated
  ST; stored, delayed, timed and Boolean actions are outside the initial claim;
- the action records the Core step and may call `FRK_Seq_*` service AOIs or write
  generated sequence intent only. It shall not call a public module AOI, access
  raw I/O/HAL, or directly write a terminal module state/output;
- transitions read explicit generated `Seq` results. The controller setting is
  **Execute current active steps only**, so the chart returns to its caller
  after one active step/group instead of traversing an unbounded run of true
  transitions in one task scan;
- the generated wrapper uses `SFR` on fresh-command, mode-exit, abort/error,
  operator-reset and Program→Run initialization edges, targeting the declared
  initial step. Core owns command/step latches; Rockwell stored-action state or
  automatic postscan is never a second latch authority; and
- SFC step tags have explicit stable Core step numbers and branch numbers.
  Active actions call the normal step/publication service every active scan, so
  `CurrentStep`, `ActiveSteps`, profiling, diagnostics and the §3.13 table have
  the same contract as ST/LD. Simultaneous branches require one numbered
  `FRK_SequenceCtx` leg per Core branch.

The framework services Part II exposes as methods on `FB_SequenceBase` become
**AOI calls taking `Seq` as `InOut`**: `FRK_Seq_Step`, `FRK_Seq_Await`,
`FRK_Seq_TryIssue`, `FRK_Seq_Delay`, `FRK_Seq_Advance`, and the part / decision /
completion forwards. In the ST/LD form, `FRK_Seq_Advance` commits the transition;
in SFC, the chart runtime commits it and the generated transition result only
declares the edge. Branching, decisions, private sub-chains and parallel legs
retain the Core result/branch rules; no shared `RetVal` is written by two calls.

**[PROVISIONAL S4] [PROVISIONAL S11]** S4 proves that generated SFC routines, step/action tags,
transition expressions, qualifiers, execution settings, `SFR` targets and JSR
parameters round-trip canonically through L5X. S11 compiles and times both the
nested-AOI path and the program-owned SFC runner on the named target, including
prescan/Program→Run, first/final scan, reset/re-entry, concurrent branches,
command/result latency and watchdog behavior. Failure disables the SFC form;
it does not invalidate the ST/LD reference form or get hidden by hand editing.

### AB §3.8 Configuration, providers, and value-type binding
*Binds Core §3.8, §3.10.2, §5.6.*

Core duration semantics are integer milliseconds and retain wire ordinal **3** /
transport name `time`. Do not assume a native Logix `TIME` is absent or suitable:
controller families/revisions differ. S12 selects native `TIME`/`TIME32` where
their range/arithmetic/CIP encoding match the contract, otherwise a range-checked
`DINT`-milliseconds representation. The repository value is identical either
way; this is binding spelling, not a contract change.

**Enumerations.** Core enum members bind to generated integer constants in
`FRK_K`; the published ordinal remains the Core ordinal. Hand-written literals
for a Core enum value are a gate violation (AB §5.3). This avoids depending on a
controller/version-specific enum editor feature.

**Operator-facing strings and identities.** Long canonical paths and
localization keys are not carried cyclically in every row. The controller stores
stable module/key IDs; `FRK_Manifest` carries the bounded ID→name/path/key tables;
the gateway reconstructs the exact string keys and canonical paths required by
the repository/HMI contract. This is a physical binding representation, not a
change to Core identity. Names that must exist in the controller use a generated
Logix string type sized for their declared maximum.

**[PROVISIONAL S12]** freezes a complete Core→Logix→repository type table before
any public UDT is generated: signed/unsigned widths, bit strings, `REAL`/`LREAL`,
duration, timestamp plus synchronization quality, strings and UTF-8 policy,
arrays/lower bounds, enum ordinals, NaN/overflow behavior, and CIP UDT layout.
Unsupported target arithmetic shall use a range-checked representation or remove
that controller from the baseline; silent narrowing is forbidden. `SchemaVersion`
remains the first logical configuration member and migrate-or-fault still applies.

**Providers.** The logical `I_RecipeProvider`, `I_PartCarrier`, event-sink, and similar
capabilities bind to `(ProviderKind, ProviderIdx)` plus one generated dispatch AOI
per seam. Unknown kinds/indices fail closed. Recipe changeover remains fallible
`PrepareRecipe(Model, RecipeKey)` → recursive readiness → bounded infallible
`CommitRecipe()`; rejection invokes `AbortRecipe()`. Provider payloads are
validated before mutation, and commit performs no validation or I/O.

### AB §3.9 Feature selectability
*Binds Core §3.9, §1.1 O4.*

Optional features are generated capability bits and manifest/catalogue entries.
An absent feature has no cyclic tag family and no gateway polling demand; a
client never infers support from a guessed tag. Compile-time variants that
change public UDT layout change its schema/signature and are versioned as such.

### AB §3.10 Self-description exposure mechanics
*Binds Core §3.10 and AB §11; R0 authority recorded in `AB_R0_CORE_AUTHORITY_EVIDENCE.md`.*

Publication is the controller-resident **`FRK_Manifest`**, generated from the
same declaration as the AOIs, the registry indices and the constants. It carries
at minimum: protocol/schema version and a monotonic configuration revision; for
every deployed root and module its stable ID, parent ID, local name, canonical
qualified path, tier, type and capability flags; the registry location of its
contract data; the command / manual / decision / state / I/O catalogues by
numeric key; and declared limits and feature flags.

Three rules make it trustworthy:

1. **It is live.** A generated L5X on disk is an engineering artifact; the
   runtime source of truth is the manifest in the controller. A client that
   cannot read it does not proceed on assumption.
2. **It is generated, never hand-edited.** It necessarily restates what the AOIs
   and registry encode, which is a bounded, deliberate exception to Core §1.1 O9
   — admissible *only* because one declaration produces all of them.
3. **Agreement is gated.** Manifest ↔ registry ↔ AOI consistency is proven on
   every change (AB §5.3). Without that gate a hand-edited AOI leaves the
   manifest describing a machine that no longer exists.

The logical schema is fixed before physical UDT layout. Physical types and
capacities are named `FRK_MAX_*` constants settled by S3/S7/S12, never magic
numbers copied into the gateway:

| Manifest table | Required logical content |
|---|---|
| Header | magic, protocol/schema version, framework version, binding version, configuration revision, generated-content hash, controller identity, table counts/capacities, truncation/valid flags |
| Roots | stable root ID, module-table index, repository scope, access/mailbox identity, host-event identity |
| Modules | stable nonzero module ID, parent/root ID, registry index, tier, type ID, local-name key, canonical-path key, capability mask, public-contract symbolic address |
| Nameplates | module ID, manufacturer/product/model, serial, hardware/software revision, asset/device IDs and optional location keys required by Core §3.10.1 |
| Fields/facets | module/type ID, repository-relative path key, logical value type, dimensions/bounds, read tier, access class, quality/timestamp source, optional write-capability index |
| Commands/manual/decisions/config | numeric ID/key, target scope, parameter/result type, required gated action, min/max/enum/schema metadata, mailbox operation kind |
| Localization/rationalization | stable numeric key to portable string key; reason code to priority/category/action/consequence/shelvable metadata |
| Optional profiles | profile ID/version, capability and projection requirements |

Counts greater than capacity, duplicate IDs/paths/write keys, unknown types,
invalid parent/root links, hash disagreement, or `Valid = FALSE` invalidate the
whole manifest. Partial discovery is not a degraded conformance mode. The
gateway reports the exact validation reason and exposes no write surface.

**[PROVISIONAL S7]** Manifest size, read cost and revision-change detection over
CIP are unmeasured. If a single bounded manifest does not fit the budget, it is
split by root with a per-root revision, and this clause is rewritten.

### AB §3.11 Composition-root wiring
*Binds Core §3.11 (constructor injection).*

Logix has no constructor and no `FB_init`. Wiring binds to an explicit,
**generated** first-scan routine in the composition-root program:

```
FRK_<Type>_Setup(Ctx, Name, ParentIdx, HalIdx, RecipeProviderIdx, …)
```

Each declared instance is set up **exactly once**, before its first cyclic call,
and setup failure is a fail-closed startup fault (Core §5.6).

> **The honest cost.** Core §1.1 forbids requiring a project to remember a call
> for correctness, and this binding reintroduces exactly that. It is admissible
> only because the setup routine is **generated** from the instance declarations
> and a gate proves every declared instance is set up exactly once, in order
> (AB §5.3). Enforcement moves from the compiler to the gate, which is weaker.
> That trade is the price of a platform without constructors, and it should be
> stated in every project's binding record rather than discovered.

### AB §3.13 HMI projection and snapshot coherence
*Binds Core §3.10, §3.13; `HMI_CONTRACT.md`.*

The gateway, not the Flutter UI, maps manifest/registry/contract data into the
existing repository paths and domain types. No station/type screen, Logix tag
name, registry index, or CIP type escapes that adapter boundary.

CIP reads across several tags are not assumed atomic. Every published root and
module row therefore carries a generated data revision or equivalent coherence
token. The gateway accepts a composite sample only when its pre/post token is
stable; otherwise it retries within a bounded budget and marks the value set
Uncertain/Bad rather than mixing scans. Static manifest data is cached until
`ConfigRevision` changes. Fast, slow, and on-demand data are polled at separately
budgeted rates; on-demand work cannot starve command acknowledgement or fast
state.

Quality/timestamp mapping is explicit:

- PLC-provided event/diagnostic timestamps remain the source timestamp and keep
  their synchronization-quality flag;
- the gateway stamps server/receipt time and never fabricates a controller
  source timestamp for a value that has none;
- a validated current sample inside its tier's freshness limit is Good; a
  coherent but late/partially supported sample is Uncertain with a reason; and a
  lost session, invalid manifest, decode/type error, or expired value is Bad;
- Bad/Uncertain data never enables a write and no cached value is promoted to
  Good after reconnect.

**[PROVISIONAL S9]** freezes coherence-token behavior, freshness thresholds,
poll budgets, reconnect discovery, quality codes, timestamp mapping, and the
repository parity test against the TC3 adapter before the gateway implementation
is accepted.

### AB §3.14 Lifecycle binding — generated `Begin` / `End` composition
*Binds Core §2.2, §3.14; R0 authority recorded in `AB_R0_CORE_AUTHORITY_EVIDENCE.md`.*

Logix has no template-method inheritance. The generator therefore emits the
**concrete AOI as one composed lifecycle**:

```
FRK_CylinderCM (AOI)
  FRK_ModuleBase_Begin(Ctx)     ← terminal reset when Execute-drop permits,
                                   new-edge acceptance, OnInit/OnCommandStart,
                                   OnCyclic, child/rollup and abort routing
  <generated call to the type's device/sequence dispatch, only while BUSY>
  FRK_ModuleBase_End(Ctx)       ← HELD resolution, timing, terminal outputs,
                                   diagnostics/status, registry publication,
                                   one-shot release for the next scan
```

Normative rules:

- **Both calls, in that order, exactly once per scan** per module instance, with
  the declared dispatch between them. A module body with one, neither, a duplicate,
  or them out of order is a gate violation.
- The device `CASE` **shall not** write any `Base.*` member that `Begin`/`End`
  own; it signals through the provided helpers (`FRK_Mod_Complete`,
  `FRK_Mod_Fault`, `FRK_Mod_Hold`) exactly as Part II's `_M_Complete` /
  `_M_Fault` / `_M_Hold`.
- Core §3.14 extensions (`OnInit`, `OnCyclic`, `OnCommandStart`, `OnAbort`,
  `OnModeExit`, `OnModeChanged`, `OnManRelease`) have no override mechanism.
  They bind as **optional generated call-outs**: the generator emits a call to
  `FRK_<Type>_On<Hook>` only where the type declares one, so an absent hook
  costs nothing and a present one cannot be forgotten.
- Core's framework-first extension order is generated inside `Begin`; a type
  cannot omit or reorder it. `OnModeExit` is the specified exception: its generated
  callout may hold the transition before the cancel phase, and returning consent
  runs that cancel/commit phase exactly once. `End` always remains last.

### AB §3.15 External connector and byte-transport binding
*Binds Core §3.15.*

Device modules still depend on a platform-neutral bounded byte-channel contract,
never on socket/serial instructions. On AB, `I_ByteChannel` binds to a provider
kind/index and generated adapter AOIs for the selected Ethernet socket, serial,
or vendor module. The adapter owns connection state, request IDs, timeouts,
buffer bounds, reconnect/backoff, stale-response rejection, and the Core link
diagnostic. A module may not contain `MSG`, socket-service, or serial-module
details directly.

**[PROVISIONAL S13]** selects and proves byte transports for each claimed
controller/communication module, including maximum payload, concurrency, socket
count, reconnect, and simulation. Until it passes, TCP/serial-derived reusable
modules are outside the initial library claim rather than silently stubbed.

### AB §3.16 Traceability and provider binding
*Binds Core §3.16, §8.3, §11.6.*

Every Unit context contains the same part context and bounded record set. A
carrier binds through `(ProviderKind, ProviderIdx)` and generated dispatch; no
carrier configured means traceability is explicitly off. The four canonical
received/started/processed/aborted events retain their order, part identity,
verdict, reason, synchronized timestamp, and carrier-write-before-event rule.
Carrier failure faults with the Core reason code and is never replaced by a
gateway-only error. The controller-resident HostEvents transport is specified in
AB §11.6.

### AB §3.17 Extension modes
*Binds Core §3.17.*

Additional modes are generated catalogue entries with stable numeric IDs and
repository keys. The fixed Core modes retain their ordinals. Unknown IDs are
rejected; extension modes participate in the same release, cascade, sequence,
stop, reset, and HMI discovery contracts and cannot introduce a parallel command
surface.

### AB §10.2.1 I/O integration placement
*Binds Core §10.2.1.*

Unchanged in intent: raw controller I/O tags are read and written by exactly one
project routine, which maps them to semantic HALs. `MAIN`'s analogue — the
composition-root program — performs setup, real/simulation selection and scan
order, never channel assignments.

---

## AB §4 — Project settings

### AB §4.1 Controller and task baseline
*Binds Core §2, §8.11.*

- One periodic task owns the Fraktal forest; its period is pinned and recorded.
  Its priority, watchdog, overlap behavior, and maximum execution budget are
  pinned. Scan-time headroom is measured (Core §8.11) and published (AB §8.11).
- Program structure follows the instance tree (Core §4.2): a composition-root
  program plus one program per root Unit, matching Part II's `00_System` /
  `0N_<UnitName>` layout.
- The task program schedule and every program's generated main routine are part
  of the reviewed L5X. The reference scan is: snapshot mapped inputs → system/
  domain services → root programs in declared order → publish/diagnostic close →
  map semantic outputs once. Raw module tags are touched only by the I/O driver.
- Controller continuous tasks, event tasks, periodic tasks, or gateway writes
  shall not be second writers of a Fraktal contract. Asynchronous I/O is sampled
  once at the boundary so a module sees one input image for its scan.
- **[PROVISIONAL S6]** Online-change semantics against the registry and manifest
  are unverified. If adding a module online cannot extend the registry safely,
  commissioning gains a documented download step and this clause says so.

**[PROVISIONAL S11]** proves the generated nested-AOI call graph and, when used,
the root program's owner-local SFC runners. The proof covers parent command issue, child
execution, child result/diagnostic rollup, concurrent branches, chart return,
reset/re-entry and output withdrawal. The SFC form's declared one-scan intent
latency is accepted only if Core-observable behavior remains equivalent; every
other accidental delay from program ordering is a failed design.

### AB §4.2 Startup and deployment state
*Binds Core §2.3, §4.1, §6.1, §13.*

The generated system routine owns `FirstScan`, manifest/registry validation,
provider validation, and transition from `STARTING` to `READY`. Root Units remain
not-startable and all command outputs remain withdrawn until that validation is
complete. Program→Run, power cycle, download, partial import, and controller
fault recovery all traverse this gate; none resumes AUTO or an HMI mutation.

Downloads to a production controller require the project MOC procedure,
controller identity check, force check, retained-data migration/backup decision,
post-download manifest hash check through the gateway, and explicit operator
restart. The implementation tooling shall never choose a production route by
discovery or make the AB test project a boot/download default.

### AB §4.3–§4.7 Naming and ownership binding
*Binds Core §4.2–§4.7.*

The generator enforces the Core semantic naming rules and the Logix component
limit. Public binding prefixes are `FRK_` for framework AOIs/UDTs/constants and
`PRG_` for generated programs; project instance tags retain their schematic
names without Hungarian prefixes. Generated helper names remain owner-local and
do not create manifest modules. Any identifier that exceeds the pinned Logix
limit, collides case-insensitively, contains `.`, or requires a lossy abbreviation
fails generation—there is no hidden name-mangling table that lets PLC and
schematic identities drift.

Application programs/routines follow the instance tree: system composition and
I/O first, then one program per root with owner-local mode/sub-sequence, release,
recipe and I/O routines. Reusable AOIs remain type-owned assets and are imported
once; they are not copied into every root program. A generated project sequence
AOI or native SFC routine belongs to its owning root; neither creates a manifest
module or a second command surface.

### AB §4.8 Browse-name source
*Binds Core §4.8.* A module's canonical qualified path comes from the manifest,
whose local name segment **shall** equal the instance's Logix tag name. `.` is
reserved as the path separator and is forbidden inside a local name — unchanged
from Core, and checkable in L5X.

---

## AB §5 — Quality tooling

### AB §5.2 Generation
*Binds Core §1.1 O1, O9.*

The generator is **not optional infrastructure in this binding** — it is how the
Core "written once" obligation is discharged without inheritance. From one type
declaration it emits: the AOI skeleton with `Begin`/`End` and hook call-outs, the
`Ctx` UDT family, the constants in `FRK_K`, the manifest entry, the registry
registration, the setup/cyclic call in the composition root, and the RED test
suite. From application declarations it also emits deterministic registry IDs,
provider wiring, task/program schedule, mailboxes, manifest catalogues, project
sequence-AOI shells, and any native-SFC chart/runner/reset shell.

Hand-writing any generated artifact is a gate violation. The hand-written parts
are the declared device behavior/conditions and project sequence step logic
inside designated generator-owned regions; regeneration shall preserve those
regions and reproduce every other byte canonically.

### AB §5.3 Structural gates
*Binds Core §1.5, §5.5.*

Reading exported L5X (AB §2.5), and failing the build:

| Gate | Proves |
|---|---|
| G-BEGINEND | every module AOI calls `Begin` first and `End` last, exactly once |
| G-SETUP | every declared instance is set up exactly once, before first use |
| G-CYCLIC | every deployed module AOI is called unconditionally exactly once per periodic scan in generated order |
| G-TIER | no Unit composed inside an EquipmentModule (Core §3.3) |
| G-REGISTRY | manifest ↔ registry ↔ AOI agree; every index in range |
| G-KEYS | no hand-written literal where a `FRK_K` constant exists; no duplicate reason or key |
| G-NAMES | Core §4.3–§4.6 naming; no `.` inside a local module name |
| G-GENERATED | no hand-edit of a generated artifact (checked by regeneration, not by trust) |
| G-EXTACCESS | all private/local/provider/scratch data are `None`, all published data are `Read Only`, and only declared mailboxes are writable |
| G-MAILBOX | one writer/consumer per root; payload-before-commit order, sequence/ack fields, operation catalogue, and no arbitrary tag write |
| G-SEQUENCE | each chain has one owner/token writer; nesting within limits; every branch/join and nonterminal transition is complete |
| G-SFC | each native chart has one owner and one state/tag set, and is JSR-called only by its generated runner; N actions only; stable step/branch mapping; current-active-steps execution; generated SFR coverage; actions never call module AOIs or raw I/O |
| G-PROVIDER | every provider kind/index is declared, bounded, initialized, and handled with a fail-closed default |
| G-RETAIN | every retained member is declared/schema-versioned; no command/manual/force/mailbox transient is retained |
| G-SAFETY | standard logic never writes safety tags; safety/control-power published data are read-only |
| G-TYPES | public UDTs and manifest field descriptors match the frozen Core↔Logix↔repository type table |

These are the AB analogue of `plc_lint.py`'s rules and **shall** ship with the
feature each protects, not afterwards.

### AB §5.4 Verify, build, import, and CI
*Binds Core §1.5, §2.5, §5.5.*

Text lint is necessary but cannot prove that Studio 5000 accepts or verifies the
generated project. The automated gate shall, from a clean checkout and the
pinned toolchain: regenerate; compare clean; import the full L5X; Verify/Build
the controller; fail on every error; export/canonicalize/recompare; download to
the isolated target; run tests; and archive the exact logs, project hash,
controller/firmware identity, and JUnit result.

The reference automation seam is the licensed Logix Designer SDK plus
FactoryTalk Logix Echo SDK; manual IDE verification is acceptable only during
Phase 0 exploration, never as the release gate. **[PROVISIONAL S15]** proves the
SDK APIs, licensing, supported versions, unattended execution, diagnostic
extraction, timeout/cleanup, and runner isolation. If controller Verify/Build
cannot be automated reproducibly, the binding does not satisfy the Core CI gate
as drafted.

### AB §5.5–§5.6 Language and defensive coding
*Binds Core §5.5, §5.6.*

Framework/base and reusable module AOI primary logic is Structured Text;
generated Ladder is permitted for application chains whose parity/graph gates
are in place. Generated native SFC is permitted for the program-owned form in
AB §3.5 only after S4/S11 and G-SFC pass. No protected/encoded source is accepted
as conformance evidence. Every index, count, payload length, provider kind,
operation kind, command, mode, logical type and motion target is validated before
use. Every dispatcher has an explicit fail-closed `ELSE`/default. Integer overflow/
narrowing, array lower-bound translation, NaN, malformed Logix string length,
and unknown CIP decode are handled according to the frozen S12 type table; none
may become an implicit controller default or silent stalled state.

### AB §5.7 Unit-test framework & CI runner
*Binds Core §5.7.*

There is no TcUnit. The binding defines a controller-resident harness mirroring
its shape, because Core §5.7 requires per-type suites that run against the
simulated HAL:

- `FRK_TestSuite` AOI + a `FRK_TestRunner` program instantiating every suite;
- results published as a bounded UDT array with the same five summary fields
  TcUnit reports (suites, tests, successful, failed, duration);
- results harvested over CIP by the gateway or the CI host and converted to
  JUnit by an extension of the existing `tools/tcunit_to_junit.py`, so runner
  identity and expected counts are validated exactly as they are on TC3.
- Core's inheritance-free reality changes what is provable once: Part II proves
  T1/T4 once in the base suite because every type *is* a base. Here the base
  behaviour is proven once against a reference type, and **G-BEGINEND plus
  G-GENERATED** are what extend that proof to every other type. State this in
  the conformance record; it is an argument, not an inheritance guarantee.
- The base suite covers T1/T4 plus reset-release, hold/resume, timeout/first-out,
  unsupported command, registry bounds, manifest invalidity, mailbox torn/stale/
  duplicate requests, disconnect/no-replay, provider invalidity, and restart/
  prescan safety. Type suites add the applicable Core T2/T3/T5 rows; a Unit with
  mode-entry policy proves T10. Expected suites/tests are generated and the CI
  harvester fails if a suite is uninstantiated or a count silently falls.
- A chain carried in more than one language has one generated graph declaration
  and parity tests for steps, transitions, decisions, branches and terminal
  behavior. The native-SFC suite additionally proves initial-step reset,
  abort/error/reset re-entry, one active-step/group return per caller scan, and
  the declared one-scan command/result loop against the ST reference.
- Tests use a deterministic simulated plant/tick where wall-clock behavior is
  not the subject. Performance, CIP throughput, controller health, safety-tag
  read paths, and motion retain named hardware/Echo evidence where simulation
  cannot establish the claim.

**[PROVISIONAL S5]** The exact Logix Echo/SDK matrix and which suites require
physical hardware decide how Core §5.7's “runs in CI” is satisfied. Hardware may
be an isolated CI runner; an engineer manually pressing Run is not CI evidence.

---

## AB §6 — Command execution & sequencing binding

*Binds Core §6.*

The PLCopen handshake is stored in `FRK_ModuleBase` and implemented only by the
generated `FRK_ModuleBase_Begin`/`End` plus bounded helper AOIs. `Execute`,
`Busy`, `Done`, `Error`, `ErrorID`, `Abort`, `Aborted`, `Held`, derived `State`,
timing, and Execute-drop reset retain the Core meanings and ordinals. Concrete
device logic can request complete/fault/hold only through helpers; it cannot
write terminal state directly.

First-out, awaited-child error/hold rollup, pending-step diagnosis, warnings,
decision waits, sub-chains, jumps, and concurrent joins use validated registry
indices and `FRK_SequenceCtx` records. Every bounded table overflow has a named
fault or explicit truncation flag according to Core; it never overwrites an
unrelated row. A condition expected to recover remains HELD/BUSY and withdraws
outputs with the same permit; it is not promoted to a latched alarm.

The generated scan and sequence gates prove:

- one owner and one state writer per chain, branch, command, and child;
- one scan with a child `Execute` low where Core requires Execute-drop reset;
- no same-scan Reset-then-Set ordering that re-latches a terminal child;
- no transition outcome is discarded by a later nested AOI call; and
- every fault/reset/restart path reissues and retests a command rather than
  resuming mid-handshake unless Core explicitly defines resume.

The implementation test oracle is Core §6 plus the TC3 observable behavior, not
the internal shape of `FB_ModuleBase`. A difference in scan ordering that changes
an externally visible state/event/timestamp is a binding deviation and must be
resolved or specified before release.

---

## AB §7 — Permissives, interlocks, access, and mutation surface

*Binds Core §7, §14; `HMI_CONTRACT.md`.*

`FRK_PermIntlk`, release reports, manual catalogues, and access policy are
bounded UDT/AOI implementations of the Core records. Conditions are generated or
declared at the lowest semantic owner; parents append records with the owning
module ID and the gateway resolves its canonical path. Summaries such as
`AllOk`/`CommonManRelease` never replace the records.

Unit `Start` consumes the Boolean result of the one complete Start release
report after the access check. Manual release is common Unit conditions plus
only the selected target/direction conditions. Safety, muting, bridging, and
control-power state may explain a refusal but never become bypass bits in the
standard task.

### AB §7.7 Root request mailbox

External mutations use one generated mailbox per root Unit. This is the only
Fraktal data with `External Access: Read/Write`; all target module/configuration
data are read-only. Its logical contract is versioned before physical layout:

| Request | Response |
|---|---|
| `SchemaVersion`, `CommitSeq`, operation kind, root/target module ID, command/mode/direction/write key, typed arguments, credential/secret slot | `SchemaVersion`, `AckSeq`, `Accepted`, refusal reason/key, resulting access/command state, PLC timestamp |

The gateway serializes at most one in-flight mutation per root. It writes the
payload first and commits it by writing the nonzero `CommitSeq` DINT last. The
PLC consumes only a new, complete, schema-valid sequence; copies it to private
storage; clears transported secrets; validates target/type/range/access/release;
acts at most once; and publishes `AckSeq` plus accepted/refused reason. Transport
write success is never command acceptance.

On timeout/reconnect the gateway reads `CommitSeq` and `AckSeq`; it never rewrites
or invents the prior request. An uncommitted local request is discarded. A
committed request is observed to acknowledgement/refusal before another request
is allowed. Sequence wrap skips zero and is permitted only when the previous
sequence is acknowledged. Download/prescan invalidates volatile in-flight state
without turning an old payload into a new commit.

The operation catalogue is generated from `HMI_CONTRACT.md` and the manifest:
module command/abort, Unit mode/start/stop/reset, manual command, decision,
configuration write, login/logout/access-policy edit, alarm shelve/unshelve,
field force, lamp test, and control-power operations. Each entry names its
`E_GatedAction`, target scope, argument type/range/schema, acknowledgement, and
release-report source. Unknown/free-form operations or paths are refused; the
gateway exposes no generic CIP tag-write endpoint.

**[PROVISIONAL S9]** proves the mailbox against partial/multi-service CIP writes,
duplicate/out-of-order sequences, gateway crash at every boundary, controller
scan races, DINT wrap, secret clearing/log redaction, PLC refusal, and reconnect.
If these atomicity assumptions fail, adopt a two-slot/seqlock mailbox before any
writable deployment; do not relax the one-write-surface rule.

### AB §7.8 Act-or-explain

Every refused action returns the same complete release/access explanation the
PLC evaluated. The gateway may pre-disable a control from the latest snapshot,
but it does not decide acceptance and it does not substitute a generic network
error for a PLC refusal. Accepted privileged actions and denied attempts enter
the Core §8.3 audit/event ring without credentials or secret payloads.

---

## AB §8 — Diagnostics & performance binding

*Binds Core §8.*

- The diagnostic model, first-out selection, alarm ring, rationalization and
  shelving are Core behaviour and port unchanged as `FRK_` AOIs over bounded
  UDT arrays. No Logix Alarm (ALMD/ALMA) instruction is used for the Fraktal
  alarm model: Core §8 owns the semantics, and mixing two alarm systems would
  give the operator two truths.
- **§8.11 timing.** Task scan time, headroom and jitter come from the controller
  `GSV` task object. **[PROVISIONAL S3]**
- **§8.12 system health.** Controller major/minor faults, memory, and module
  connection state come from `GSV` and the module object. **[PROVISIONAL S3]**
- Localization keys bind to **numeric key IDs** resolved in the HMI catalogue,
  not repeated cyclic strings (AB §3.8). The gateway projects the same portable
  string key expected by the repository. Applying numeric IDs to TC3 is a
  separate Core/Part II improvement decision, not something this binding changes.
- **§8.5/§8.11 OEE and profiling.** Counts, machine state, cycle markers, command
  timing, step timing, and concurrent-leg rows use the same bounded Core records.
  The task clock source and arithmetic range are fixed by S3/S12; overflow and
  synchronization degradation are explicit.
- **§8.9 rationalization.** Reason metadata and localization key IDs are generated
  into the manifest from the one registry. A Logix Tag-Based Alarm or ALMD/ALMA
  projection may integrate with plant tooling, but it is read-only/derived from
  the Core event state and never becomes a second latch/reset/shelving authority.
- **§8.13 signal tower.** The Core arbitration AOI writes semantic lamp/buzzer
  requests to the HAL. Only the project I/O driver maps them to module outputs.
  Lamp test is a gated mailbox operation and cannot override a safety-controlled
  indication or energize an undeclared output.

---

## AB §9 — Safety binding

*Binds Core §9.*

- Functional safety is **GuardLogix / CIP Safety**, in the safety task, and it is
  the sole authority for safe state, safe enable, unlock, muting and bridging.
- The standard Fraktal application consumes safety state **read-only**. The
  binding mechanism is a generated standard-task adapter that **reads
  controller-scoped safety tags directly** and projects the approved status into
  `FRK_SafetyStatus`. Logix permits standard routines to read, but not write,
  controller-scoped safety tags. **Safety Tag Mapping is not this path**: it maps
  standard tags into safety tags for use by safety logic and therefore shall not
  be described as a safety→standard publication mechanism.
- Fraktal code **shall not** write a safety tag, request a reset on behalf of an
  operator, or represent a bridged/muted state as anything but read-only status
  (Core §9.8).
- Safety reset/unlock/muting/bridge requests, if the certified safety design
  accepts any standard-origin input, are outside the ordinary Fraktal mailbox and
  remain governed by the validated safety application. Standard-origin data
  mapped into safety is untrusted and never grants a safety function by itself.
- The project evidence records safety signature/lock state, safety-task and
  standard-task boundaries, every safety tag read by the adapter, and proves
  `G-SAFETY`. GuardLogix absence means the optional safety/control-power profile
  is absent; it never means a standard emulation of safety authority.

---

## AB §10 — Fieldbus binding

*Binds Core §10.*

- **EtherNet/IP (CIP)** replaces EtherCAT. Device I/O appears as controller-scope
  module tags; the Core HAL boundary is unchanged — exactly one project routine
  touches them (AB §10.2.1).
- Connection health, module presence and configuration mismatch come from the
  module object and populate Core §10.5.1's topology and I/O diagnostics.
  **[PROVISIONAL S3]**
- Core's fieldbus-loss policy (§7.8, §11) is unchanged: a lost connection queues
  nothing and resumes cleanly rather than replaying stale actions.
- Each claimed module family has a generated/module-profile adapter that records
  identity, configured/actual state, connection/fault code, channel catalogue,
  and approved electrical tag. Unknown module/fault codes remain visible as raw
  code plus an explicit unknown description; no `CASE` falls through silently.

### AB §10.6 Motion binding
*Binds Core §10.6.*

Core motion semantics bind through a `FRK_AxisHAL`/provider seam. Application
Units and reusable motion modules command semantic operations; only the AB motion
adapter owns Rockwell axis types/instructions and maps their done/busy/error/
abort, limits, home state, safety permit, and diagnostics into the Core contract.
Motion object references are `InOut` provider parameters and never registry
integer casts.

**[PROVISIONAL S14]** selects the supported Integrated Motion controller/axis
families, instruction mappings, test-mode behavior, fault/reset semantics,
limits/units, update ordering, and Logix Echo versus hardware evidence. Until it
passes, motion is an unclaimed optional module family, not a generic stub.

### AB §10.7 Peer/controller data
*Binds Core §10.7, §11.9/§11.10 where claimed.*

Produced/Consumed tags or MSG-based peer exchange may implement a declared
profile, but they are adapters behind the same provider/HAL boundary and use
stable IDs/schema versions. They cannot bypass the root mailbox, invent a second
Unit command surface, or silently consume a mismatched structure. Peer
communication loss follows the same no-replay/rearm rule.

---

## AB §11 — Connectivity binding

*Binds Core §3.10, §11; R0 authority recorded in `AB_R0_CORE_AUTHORITY_EVIDENCE.md`.*

**Default and alternative.** The conforming Fraktal/AB default is EtherNet/IP
explicit messaging between the Logix controller and one Fraktal gateway, followed
by the versioned Fraktal repository protocol to clients. OPC UA is an alternative
transport/projection only when the named deployment proves it; no base Fraktal/AB
claim depends on OPC UA availability.

### AB §11.1 Topology

```
Logix controller — FRK_Manifest + FRK_Registry + contract tags
        │  EtherNet/IP explicit messaging (CIP symbolic access)
Fraktal gateway — discovery · decode · batching · freshness · write acknowledgement
        │  versioned Fraktal repository protocol over TLS
Generic Flutter HMI — existing PlcRepository boundary, no station or type screens
```

Direct CIP from the HMI is **not** the reference design: Flutter Web cannot open
raw industrial sockets, so a gateway is required for a shipped platform in any
case, and one gateway keeps CIP decoding, batching, reconnect and credentials out
of every operator client.

### AB §11.2 Gateway obligations
*Binds Core §11, §7.7, §14.*

The gateway owns transport work only. It **shall**: supervise the CIP session;
read and validate the manifest before accepting data, rejecting incompatible
schema versions explicitly; batch and fragment reads within measured limits;
decode Logix types into the repository's typed values; carry explicit freshness,
quality and both timestamps, **never presenting stale data as live**; serve the
existing fast/slow/on-demand read tiers and aggregate demand across clients;
accept only the narrow Fraktal write vocabulary and wait for **PLC
acknowledgement** rather than treating transport success as acceptance; discard
pending writes on disconnect and require a fresh snapshot before writes resume;
and expose bounded observability.

EtherNet/IP explicit messaging is polled request/response here, not treated as a
subscription service. Poll rates and batch sizes come from the manifest read
tier plus the measured S1/S3/S9 budget. The gateway rate-limits retries and
writes independently so a slow on-demand topology read cannot starve command
acknowledgement or fast state.

**The gateway is not an authority.** Release policy, access level and command
acceptance are decided in the PLC and re-checked there (Core §7.6, §7.7). A
gateway that decides anything has moved a safety-relevant decision off the
controller.

**Availability, stated plainly.** On TC3 a native server lets any conforming
client reach the controller; here the gateway is the only path for every client.
The PLC never depends on it — the machine runs, releases hold, safety is
untouched — but the operator interface *including diagnostics* is unavailable
until it restarts. It is cell-local infrastructure with a supervised restart, and
that expectation belongs in the project's binding record.

One gateway process instance owns one PLC session; a host serving several PLCs
runs separate instances with separate configuration, listener/origin, health,
logs and restart state. There shall be one active write-owning instance per
controller/root. Multiple read observers are permitted. Redundant gateways
require an explicit single-writer lease/failover design proved against mailbox
sequence ownership; two independently configured writers are forbidden. Service
supervision, startup ordering, health endpoint, bounded local logs/metrics,
configuration backup, certificate renewal, and tested restore belong to the
deployment evidence, not only to an operations README.

**[PROVISIONAL S9]** proves discovery, typed decode, coherent reads, tier
fairness, acknowledgement, quality/timestamps, disconnect/reconnect, manifest
revision, and parity with the TC3 repository adapter. It is a conformance spike,
not merely a throughput benchmark.

### AB §11.2.1 Endpoint and conduit security
*Binds Core §11.2, §14.*

**[PROVISIONAL S8]** Plain CIP explicit messaging is not assumed to provide the
authenticated/encrypted session model required here. A deployment **shall**
either prove a supported CIP Security configuration, or place the controller
side in an IEC 62443-aligned zone with the gateway as the controlled conduit.
The client-facing side **shall** use authenticated TLS with least-privilege
roles. **Anonymous controller writes are not an acceptable baseline**, and
PLC-side re-checking is defence in depth, not a substitute for transport
security.

The controller-side allow-list is generated and audited: manifest/public data
read-only, root mailboxes read/write, everything else None. Engineering access
is a separate role/conduit. Gateway secrets and private keys are OS-protected,
never stored in L5X/customization exports, never logged, and rotated through a
documented process. The gateway authenticates clients before root discovery,
enforces assigned-root read/write scope, rate-limits mutation/login attempts,
and records security-relevant failures without credential values.

### AB §11.3 Protocol versioning
*Binds Core §1.5.*

The Fraktal repository protocol is **versioned with an explicit handshake**, and
both bindings speak it. The shipped gateway today carries a `protocol` field but
**no version handshake**, and two OPC-UA-named diagnostic fields; creating the
neutral versioned protocol is therefore work on the **TC3 side as well**, not an
AB-only cost. Incompatibility fails closed and is reported, never negotiated
down silently.

Before discovery or mutation, the client and gateway exchange: protocol name;
supported major and minor range; manifest/repository schema versions; capability
flags; client instance ID; and requested root scope. The gateway selects and
echoes one exact compatible version or returns a structured incompatibility and
closes the data session. Major mismatch is always fatal; optional minor features
are enabled only when explicitly negotiated. No legacy fallback may widen the
read scope or expose writes.

Every snapshot, manifest replacement, request acknowledgement, and error carries
the selected protocol version plus connection/discovery revision needed to
reject stale frames. Unknown fields are tolerated only under the declared
additive-minor rule; unknown operation kinds and logical value types fail closed.

### AB §11.4 Recipe/type transport
*Binds Core §11.4, §3.8.*

Controller-resident and host-backed recipes both enter through the provider seam
and root configuration mailbox. The manifest's write-capability entry supplies
scope, `WriteKey`, logical type, range/enum, schema and required gated action.
Large records use a versioned bounded staging area with payload hash, length,
chunk sequence and final commit; the PLC validates the completed immutable
payload before `PrepareRecipe`. A reconnect never commits a partial/stale stage.

### AB §11.5 Alarm, event, and historian projection
*Binds Core §11.5, §8.3.*

The controller event ring remains authoritative. The gateway may feed a
historian, Logix/FactoryTalk alarm projection, SQL/MES adapter, or other event
sink using event sequence and idempotency keys. Sink failure cannot block the
PLC ring or alter alarm state; overflow/wrap is explicit and alarms are never
acknowledged/shelved/reset merely because an external sink accepted a record.

### AB §11.6 Host-event binding
*Binds Core §11.6, §3.16.*

Each root publishes the fixed bounded `HostEvents` ring with monotonic event
sequence, head/count/capacity/wrapped state and the Core record fields. The
gateway reads head metadata before and after a batch, accepts only a coherent
view, and maintains a per-sink acknowledged cursor. Reconnect resumes by event
sequence; if the controller ring wrapped beyond the cursor, the gateway emits an
explicit data-loss record instead of pretending continuity.

Host-originated commands/results are never injected into this read-only ring.
They use the validated recipe/host provider or root mailbox. Optional outbound
sinks receive the same record and idempotency key; the PLC does not wait for
them unless a particular process step explicitly awaits a host transaction.

### AB §11.7–§11.11 Optional OPC UA and industry projections
*Binds Core §11.7–§11.11, Annexes F/J/K where claimed.*

OPC UA remains a permitted alternative north-bound projection—an embedded server
where the named controller/firmware supports it, or a commercial gateway—generated
from the same live model so it cannot create a competing identity or hierarchy.

Core §1.5 now makes companion/projection conformance binding-qualified. A base
claim is `Fraktal Core + Fraktal/AB`; a deployment may additionally claim, for
example, `Fraktal/AB + PackML/OPC UA` only when the complete projection is present
and verified. **[PROVISIONAL S10]** therefore gates the optional projection and
the additional claim only; it can no longer block the default EtherNet/IP path.

---

## AB §12 — Provisional-clause register

Every `[PROVISIONAL]` clause, its spike, and what it costs if the assumption
fails. This table is the Phase 0 work list.

| Clause | Spike | Assumption | If wrong |
|---|---|---|---|
| AB §2.2 | S2 | AOI signature change is breaking on import | version rule tightens: added parameter = major |
| AB §2.5 | S4 | L5X round-trips stably and faithfully | **binding not viable as drafted**; gates lose their input |
| AB §2.7 | S1 | controller clock + CIP Sync satisfy §2.7 | timestamp correlation limited; record as deviation |
| AB §3.3 | S2 | target limits and External Access support one public `Ctx` plus inaccessible `Priv` | split public/private context; if private data cannot be hidden, binding fails security gate |
| AB §3.10 | S7 | one bounded manifest fits the read budget | split per root with per-root revision |
| AB §4.1 | S6 | registry/manifest survive online change | commissioning gains a documented download step |
| AB §5.7 | S5 | the harness runs on Logix Echo or named isolated hardware CI | §5.7 remains unresolved; a manual run is not substituted |
| AB §8.11/§8.12, §10 | S3 | `GSV` and module objects supply health and timing | §8.11/§8.12/§10.5.1 reduce to a declared subset |
| AB §11.2.1 | S8 | CIP Security or a controlled zone/conduit is achievable | writes cannot meet §14; binding is read-only until fixed |
| AB §3.13, §7.7, §11.2 | S9 | CIP polling reproduces coherence, quality/timestamps, mailbox acknowledgement and no-replay | redesign snapshot/mailbox/gateway; no writable claim until parity passes |
| AB §11.7–§11.11 | S10 | optional OPC UA/companion projections are available where additionally claimed | omit or narrow that binding-qualified optional claim; the default EtherNet/IP base claim is unaffected |
| AB §2.5, §3.5 | S4 | ST/LD plus native SFC routines, actions, transitions, settings and reset targets round-trip canonically | disable native SFC; ST/LD remains the reference sequence form |
| AB §2.8, §3.5, §4.1 | S11 | nested AOIs and the program-owned SFC runner satisfy lifecycle/sequence order, one-scan intent latency and restart behavior | disable SFC or redesign the affected execution form before base implementation |
| AB §3.8 | S12 | a lossless bounded Core→Logix→repository type map exists on the target | restrict target baseline or amend representation; no silent narrowing |
| AB §3.15 | S13 | claimed socket/serial adapters meet byte-channel limits and reconnect semantics | exclude affected connector/module families from initial claim |
| AB §10.6 | S14 | Rockwell motion maps Core motion semantics and is testable | exclude motion family or define a narrower versioned profile |
| AB §5.4 | S15 | SDK can import, Verify/Build, export, download and capture diagnostics unattended | binding does not meet the automated build gate as drafted |

Six are implementation blockers rather than incremental refinements: **S1**
(transport), **S2/S11** (type/call shape), **S4/S15** (source and executable
gate), and **S12** (public data contract). Run those first, then S7/S8/S9 before
any gateway/runtime-library implementation. S13/S14/S10 gate only the optional
families/profiles they name.

---

## AB §13 — Versioning and change management

*Binds Core §13, §1.5.*

One generated declaration set owns these independently versioned artifacts:
Core semantic version, AB binding version, generator version, public UDT/AOI
revision/signature, manifest schema, repository protocol, gateway build, and
project configuration hash. The manifest publishes the runtime-relevant set and
the CI evidence records all of it. A change classification table is frozen in
Phase 2:

| Change | Minimum treatment |
|---|---|
| implementation-only with identical public UDT/AOI/manifest behavior | patch plus full regression |
| additive optional field/capability understood by older peers | minor only if explicit negotiation/ignore rules prove compatibility |
| AOI parameter/public UDT layout, ordinal, mailbox, manifest major, or command meaning change | major plus migration and coordinated download/gateway/HMI update |
| recipe/configuration record change | new `SchemaVersion` and migrate-or-fault path |

An online edit, AOI import, generated L5X replacement, firmware/toolchain update,
controller-family addition, security-policy change, or gateway protocol change
is managed change. Release evidence includes clean regeneration/import/build,
test results, compatibility matrix, retained-data decision, rollback artifact,
and post-deployment manifest/hash verification. A generated component may be
sealed/signed only after these checks; the signature never replaces source
review or behavioral tests.

---

## AB §14 — Cybersecurity governance

*Binds Core §14; extends AB §11.2.1.*

Each deployment records the IEC 62443 zones/conduits, controller and gateway
asset identities, CIP/CIP Security capabilities, firewall/allow-list, engineering
path, browser/API endpoint, certificate authority/rotation, identities/roles,
backup/restore, patch/vulnerability process, logging/monitoring, incident
response and recovery test. Default controller/program/data-type External Access
is never trusted: `G-EXTACCESS` proves the generated allow-list from L5X.

The gateway runs least-privileged as a dedicated service identity, binds the PLC
endpoint and permitted root scope explicitly, rejects discovery-based production
target selection, exposes no arbitrary CIP service/tag proxy, and redacts
credentials/secrets. Dependency/SBOM and update-signing policy cover the CIP
library, gateway runtime and installer. Security regression includes malformed/
oversized manifest and mailbox inputs, authentication/rate limits, stale session,
scope escape, downgrade, certificate failure, log redaction and fail-closed
restart. Safety authority remains independent of every cybersecurity control.

---

## AB Annex A — What this binding does not claim

- It has **not** been compiled, downloaded or run. No clause here is evidence.
- R0's two Core authority amendments are complete and TC3 compatibility is
  recorded. R1–R6 remain open, so production runtime/library implementation is
  still unauthorized (AB §0).
- Where it is weaker than Part II, it says so: tier composition and lifecycle
  ordering are gate-enforced rather than compiler-enforced (AB §3.1, §3.11,
  §3.14), and per-type lifecycle correctness is an argument from generation
  rather than an inheritance guarantee (AB §5.7).
- Native SFC is a provisional **program-owned application sequence form**, not an
  AOI primary routine. Studio 5000 can execute it, but the initial claim depends
  on S4/S11 proving the generated JSR/SFR wrapper, L5X fidelity, scan latency and
  restart behavior. Application-owned Unit/EM charts get one generated stateful
  routine/tag set per deployed owner; reusable AOI-contained sequences retain
  ST/LD unless that materialization is separately proved (AB §3.5).
- Connectors, motion, optional OPC UA/companion projections, and any controller
  family absent from the tested matrix are not claimed merely because a Core
  interface or manifest capability exists.

The Core model — tiers, contracts, handshake, diagnostics, release, traceability
— is unchanged. That is the point: if this binding works, O8 is demonstrated
rather than asserted, and the same generic HMI domain/UI drives a Logix machine
without station/type screens; only the transport/gateway adapter changes.

---

## AB Annex B — Primary platform references and evidence rule

Phase 0 records exact document revision, product version and retrieved URL. The
licensed current Rockwell/ODVA specifications outrank this pre-spike draft where
they describe platform or wire behavior; a conflict rewrites the binding before
implementation.

- Rockwell Automation, [*Logix 5000 Controllers Add-On Instructions*
  (`1756-PM010N`, September 2025)](https://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm010_-en-p.pdf):
  atomic Input/Output, complex InOut, nested-AOI limits, AOI languages, scan
  modes, and the prohibition on `JSR` inside an AOI.
- Rockwell Automation, [*Logix 5000 Controllers Sequential Function Charts*
  (`1756-PM006L`, September 2024)](https://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm006_-en-p.pdf):
  SFC main/subroutine execution, actions and qualifiers, one-step/group return,
  simultaneous branches, initial-step restart, `SFR`, and execution settings.
- Rockwell Automation, [*Studio 5000 Logix Designer — About external
  access*](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-02/contents-ditamap/about_external_access.html):
  `Read/Write`/`Read Only`/`None` behavior.
- Rockwell Automation, [*GuardLogix — Safety
  Tags*](https://www.rockwellautomation.com/en-mde/docs/technical/logix5000/_online/1756-rm012/guardlogix-5580-and-compact-guardlogix-5580-safety/safety-programming-considerations/safety-tags.html):
  controller-scoped safety tags are readable but not writable by standard logic;
  external HMI writes are prohibited.
- Rockwell Automation, [*Standard Tags in Safety Routines (Tag
  Mapping)*](https://www.rockwellautomation.com/en-us/docs/technical/logix5000/_online/1756-um900/controllogix-5590-controller-user-manual-ditamap/develop-safety-applications/standard-tags-in-safety-routines--tag-mapping-.html):
  Safety Tag Mapping is the standard→safety path, not safety→standard publishing.
- Rockwell Automation, [*Industrial DevOps CI/CD for Logix Control Systems*
  (`LOGIX-AT002`)](https://literature.rockwellautomation.com/idc/groups/literature/documents/at/logix-at002_-en-p.pdf):
  Logix Designer SDK and Logix Echo SDK automation pattern.
- Rockwell Automation, [*FactoryTalk Logix
  Echo*](https://www.rockwellautomation.com/en-us/products/software/factorytalk/designsuite/logix-echo.html):
  supported virtual-controller families and SDK/test capabilities.
- The EtherNet/IP/CIP references in
  [`ALLEN_BRADLEY_PORT_PLAN.md`](ALLEN_BRADLEY_PORT_PLAN.md) apply to S1/S3/S7/S9;
  implementation requires the licensed current ODVA CIP Networks Library.

---

## AB Annex C — Core coverage crosswalk

This table is the completeness check for the binding document. “Unchanged” means
the Core behavior remains normative; the cited AB clause fixes only the platform
mechanism. A new Core clause shall update this table before AB implementation can
claim the corresponding feature.

| Core surface | AB binding mechanism | Pre-implementation evidence |
|---|---|---|
| §1 objectives, conformance, definitions | AB §0/§1/§12–§14 | R0 and named version/baseline |
| §2 environment, tasks, simulation, time | AB §2/§4.1–§4.2 | S1/S4/S5/S11/S15 |
| §3.1–§3.3 tiers/containment/catalogue | AB §3.1–§3.3 | S2; G-TIER/G-REGISTRY |
| §3.4–§3.7, §3.17 modes/commands/cascade/extensions | AB §3.4–§3.7/§3.17 | S11; base transition tests |
| §3.8 recipe/providers | AB §3.8/§11.4 | S12; provider and migrate-or-fault tests |
| §3.9–§3.14 selectability/contract/HMI/lifecycle | AB §3.9–§3.14 | S2/S7/S9/S11/S12; generated schemas/gates |
| §3.15 connectors | AB §3.15 | S13 for each claimed transport/family |
| §3.16 traceability | AB §3.16/§11.6 | carrier/HostEvents tests |
| §4 structure and naming | AB §4 | L5X naming/ownership/schedule gates |
| §5 language/defensive coding/testing | AB §5 | S4/S5/S12/S15; clean CI evidence |
| §6 handshake and sequencing | AB §3.5/§6 | S11; base/sequence/recovery tests |
| §7 release/access/manual | AB §7 | S8/S9; mailbox and act-or-explain tests |
| §8 diagnostics/OEE/health/signal tower | AB §8 | S3/S12; timing/rationalization/I/O tests |
| §9 safety/control power | AB §9/§14 | named GuardLogix safety-boundary evidence or profile absent |
| §10 I/O/fieldbus/HAL/motion/routing | AB §3.15/§10 | S3/S13/S14 for claimed families |
| §11 connectivity/host/projections | AB §11 | S1/S7–S10; frozen protocol/manifest/host schemas |
| §12 worked examples | port-plan Phase 3/7 fixtures | examples are evidence, never normative mechanisms |
| §13 versioning/MOC | AB §13 | compatibility/migration/rollback record |
| §14 cybersecurity | AB §11.2.1/§14 | R6/S8 plus security regression |
