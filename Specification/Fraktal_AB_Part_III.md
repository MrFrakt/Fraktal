# Fraktal/AB — Allen-Bradley (Logix) Binding (Part III)
*Unified PLC Programming Standard · **Part III: the Allen-Bradley Logix binding of Fraktal Core***

**Status:** **Draft — pre-spike.** Part III of III (Part I: `Fraktal_Core_Part_I.md`; Part II: `Fraktal_TC3_Part_II.md`)
**Platform:** Rockwell Automation Logix (ControlLogix / CompactLogix / GuardLogix) · Studio 5000 Logix Designer · IEC 61131-3 subset **without** the OOP extensions

> Every clause in this Part **binds** a Core contract and cites it as **Core §x.y**; a binding clause carries the number of the Core clause it realizes. Nothing here introduces new normative model content — tiers, contracts, state machines, diagnostics and routing live in Part I. A port to another platform re-implements this document only (Core §1.1 O8).

---

## AB §0 — How to read this document

This Part is written **before** the Phase 0 spikes of
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

**Two Core amendments are prerequisites** (plan Phase 1). Until both land, this
Part describes a binding that Core does not yet permit:

1. **Core §2.2/§3.14/§5.5 are OOP-normative** — they require `EXTENDS` and
   `SUPER^`. Logix has neither. Core must state the *obligation* (behaviour is
   defined once and reused; a concrete type supplies device logic only) and
   leave inheritance to Part II as one way of discharging it.
2. **Core §3.10/§4.8/§7.7/§11 make OPC UA normative.** Core must define a
   transport-neutral **Fraktal Self-Description Service**; Part II binds it to
   TF6100, this Part binds it to CIP plus the Fraktal gateway.

---

## AB §1 — Binding identity & technology baseline

*Binds Core §1.1 (technology baseline), §1.2 (scope), §1.6 (definitions).*

**Fraktal/AB** is the Allen-Bradley Logix binding of Fraktal Core. Conformance
claims compose as *"Fraktal Core + Fraktal/AB (+ profiles)"* (Core §1.1 O8).

**Technology baseline.** Logix controllers programmed in Studio 5000 Logix
Designer, using Add-On Instructions, UDTs and the IEC-subset languages Logix
provides (ST, Ladder, FBD, SFC); **EtherNet/IP (CIP)** for fieldbus and device
integration (AB §10); **GuardLogix / CIP Safety** for functional safety (AB §9);
**EtherNet/IP explicit messaging plus one Fraktal gateway** for connectivity and
self-description (AB §3.10, AB §11); the same generic Flutter operator HMI,
unmodified, consuming the same repository contract (Core §3.13).

**What this binding does not assume.** It does not require an embedded OPC UA
server in the controller. OPC UA remains a permitted north-bound *projection*
(AB §11.5), never a prerequisite.

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

### AB §2.7 Time-synchronization mechanics
*Binds Core §2.7.*
**[PROVISIONAL S1]** Timestamps for the §8 diagnostic model come from the
controller wall clock, with CIP Sync (IEEE-1588) where the application requires
correlated multi-controller ordering. The Core requirement is unchanged: a
diagnostic carries the moment it became true, and whether that moment is
synchronized.

---

## AB §3 — Language & wiring mechanics

### AB §3.1 The module type form
*Binds Core §2.2, §3.1–§3.3, §3.12.*

A Fraktal module type is **one AOI plus one UDT**:

```
FRK_<Type>            AOI   — the behaviour
FRK_<Type>Ctx         UDT   — the whole contract for one instance
  Base : FRK_ModuleBase     — the common contract (Core §3.12), composed not inherited
  ParCfg : FRK_<Type>ParCfg
  ParCmd : FRK_<Type>ParCmd
  OutCmd : FRK_<Type>OutCmd
  OutImm : FRK_<Type>OutImm
  Priv   : FRK_<Type>Priv   — implementation state; never published (Core §3.2)
```

`FRK_ModuleBase` is a UDT, not a base class. **Tier is a declared field**
(`Base.Tier`), not a type relationship: `FRK_TIER_CM` / `_EM` / `_UNIT`. Core
§3.3's structural prohibition — no Unit inside an EquipmentModule — is therefore
not enforced by the compiler here and **shall** be enforced by a gate
(AB §5.3).

> This is the first place the binding is genuinely weaker than Part II. On TC3
> the type system rejects the illegal composition; here a linter does. Say so
> rather than implying parity.

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

Bounds are normative: every index **shall** be range-checked before use
(Core §5.6), and a registry overflow is a fail-closed startup fault, never a
silent truncation.

**Why this is not merely a workaround.** The registry is a flat bounded array
with static discovery cost (Core §1.1 O4), and it is exactly the shape the
gateway must mirror. Evaluate it as a Core improvement for Part II too
(plan §8).

### AB §3.3 Public contract parameter classes
*Binds Core §3.10(a′)/(a″), §3.12, §6.1.*

**[PROVISIONAL S2]** Logix AOI parameters are understood to be restricted:
`Input`/`Output` accept atomic types only; structures, arrays and strings must
be `InOut` (passed by reference). If that holds, the binding is:

- the whole contract travels as **one `InOut` parameter**, `Ctx`, of the type's
  `Ctx` UDT. Both base halves and the device logic see the same instance;
- `EnableIn`/`EnableOut` are **not** used as application logic. The module runs
  every scan (Core §2.2);
- external write access is controlled by the tag's **External Access** setting,
  not by parameter class. `Priv` members **shall** be `External Access: None`;
  published contract members are `Read Only` except the narrow request surface
  of Core §7.7, which is `Read/Write` and re-checked by the PLC.

The Core rule is unchanged and is what matters: a client may request through the
published request surface, and the PLC decides.

### AB §3.5 Sequence binding
*Binds Core §5.5, §6.2, §6.8.*

A multi-step sequence is a **Routine** (ST or SFC) owned by the module's
program, over an explicit `Seq : FRK_SequenceCtx` state record carrying `Step`,
`RetVal`, the step-scoped latches and the §3.13 publication rows.

- The reference form is the Core §6.8 skeleton as a **`CASE Seq.Step OF`** in
  Structured Text — plain reviewable text, same as Part II's preference and for
  the same reason.
- **Logix SFC is a permitted alternative** (Core §6.8) and, unlike TwinCAT's
  chart archive, is expected to be a first-class L5X citizen. **[PROVISIONAL S4]**
  Confirm SFC round-trips in L5X before recommending it for generated charts.
- Ladder is permitted for chains that suit it (Core §1.1 O2), on the same
  integer-state-machine rule Part II documents.
- The framework services Part II exposes as methods on `FB_SequenceBase` become
  **AOI calls taking `Seq` as `InOut`**: `FRK_Seq_Step`, `FRK_Seq_Await`,
  `FRK_Seq_TryIssue`, `FRK_Seq_Delay`, `FRK_Seq_Advance`, and the part /
  decision / completion forwards. One writer per step branch; `FRK_Seq_Advance`
  commits the transition and clears the step-scoped latches.

### AB §3.8 Configuration value-type binding
*Binds Core §3.8a, §3.10.2.*

Core `TIME` has no Logix analogue. It binds to **`DINT` milliseconds**, wire
ordinal unchanged (**3**), transport name unchanged (`time`). This is a binding
spelling, not a contract change — the same treatment Part II gives
`E_ConfigValueType.DURATION`.

**Enumerations.** Logix has no enumerated type. Core enum members bind to `DINT`
constants emitted into a controller-scope constant structure `FRK_K` by the
generator, from the same declaration that produces the manifest and the AOIs.
Hand-written literals for a Core enum value are a gate violation (AB §5.3).

### AB §3.10 Self-description exposure mechanics
*Binds Core §3.10 and AB §11.* **Prerequisite: the Core §3.10 amendment (AB §0).**

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

### AB §3.14 Lifecycle binding — `Begin` / `End`
*Binds Core §2.2, §3.14.* **Prerequisite: the Core §2.2/§3.14 amendment (AB §0).**

Template-method inheritance inverts. The **concrete AOI drives**:

```
FRK_CylinderCM (AOI)
  FRK_ModuleBase_Begin(Ctx)     ← edges, Execute latch, state entry, timing start,
                                   hook dispatch for OnInit / OnCommandStart
  <the device CASE — the only hand-written part of the type>
  FRK_ModuleBase_End(Ctx)       ← state mapping, Execute-drop reset, hold/rollup,
                                   publication, timing close, registry row update
```

Normative rules:

- **Both calls, in that order, exactly once per scan** per module instance.
  A module body with one, neither, or them out of order is a gate violation.
- The device `CASE` **shall not** write any `Base.*` member that `Begin`/`End`
  own; it signals through the provided helpers (`FRK_Mod_Complete`,
  `FRK_Mod_Fault`, `FRK_Mod_Hold`) exactly as Part II's `_M_Complete` /
  `_M_Fault` / `_M_Hold`.
- Core §3.14 hooks (`OnInit`, `OnCyclic`, `OnCommandStart`, `OnAbort`,
  `OnModeExit`, `OnModeChanged`, `OnManRelease`) have no override mechanism.
  They bind as **optional generated call-outs**: the generator emits a call to
  `FRK_<Type>_On<Hook>` only where the type declares one, so an absent hook
  costs nothing and a present one cannot be forgotten.
- Part II's "call `SUPER^` first" rule binds here as "`Begin` first, `End` last",
  and is checked by the same class of gate.

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
  Scan-time headroom is measured (Core §8.11) and published (AB §8.11).
- Program structure follows the instance tree (Core §4.2): a composition-root
  program plus one program per root Unit, matching Part II's `00_System` /
  `0N_<UnitName>` layout.
- **[PROVISIONAL S6]** Online-change semantics against the registry and manifest
  are unverified. If adding a module online cannot extend the registry safely,
  commissioning gains a documented download step and this clause says so.

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
registration, the setup call in the composition root, and the RED test suite.

Hand-writing any generated artifact is a gate violation. The **only** hand-written
part of a module type is its device `CASE` and its declared conditions.

### AB §5.3 Structural gates
*Binds Core §1.5, §5.5.*

Reading exported L5X (AB §2.5), and failing the build:

| Gate | Proves |
|---|---|
| G-BEGINEND | every module AOI calls `Begin` first and `End` last, exactly once |
| G-SETUP | every declared instance is set up exactly once, before first use |
| G-TIER | no Unit composed inside an EquipmentModule (Core §3.3) |
| G-REGISTRY | manifest ↔ registry ↔ AOI agree; every index in range |
| G-KEYS | no hand-written literal where a `FRK_K` constant exists; no duplicate reason or key |
| G-NAMES | Core §4.3–§4.6 naming; no `.` inside a local module name |
| G-GENERATED | no hand-edit of a generated artifact (checked by regeneration, not by trust) |
| G-EXTACCESS | `Priv` is External Access `None`; the request surface is the only writable published data |

These are the AB analogue of `plc_lint.py`'s rules and **shall** ship with the
feature each protects, not afterwards.

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

**[PROVISIONAL S5]** Whether the harness runs on an emulate/soft controller in
CI, or requires physical hardware, decides whether Core §5.7's "runs in CI" is
satisfiable. If it requires hardware, that is a deviation to record, not to hide.

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
  not strings (AB §3.8). This removes Logix's string-parameter restriction from
  the contract entirely and shrinks the published surface on both bindings — a
  Core improvement candidate, not an AB concession.

---

## AB §9 — Safety binding

*Binds Core §9.*

- Functional safety is **GuardLogix / CIP Safety**, in the safety task, and it is
  the sole authority for safe state, safe enable, unlock, muting and bridging.
- The standard Fraktal application consumes safety state **read-only**. The
  binding mechanism is **Safety Tag Mapping**, which is one-way
  safety → standard by construction — a closer structural fit to Core §9 than
  Part II's convention-plus-review, and it should be recorded as such.
- Fraktal code **shall not** write a safety tag, request a reset on behalf of an
  operator, or represent a bridged/muted state as anything but read-only status
  (Core §9.8).

---

## AB §10 — Fieldbus binding

*Binds Core §10.*

- **EtherNet/IP (CIP)** replaces EtherCAT. Device I/O appears as controller-scope
  module tags; the Core HAL boundary is unchanged — exactly one project routine
  touches them (AB §10.2.1).
- Connection health, module presence and configuration mismatch come from the
  module object and populate Core §10.6's topology and I/O diagnostics.
  **[PROVISIONAL S3]**
- Core's fieldbus-loss policy (§7.8, §11) is unchanged: a lost connection queues
  nothing and resumes cleanly rather than replaying stale actions.

---

## AB §11 — Connectivity binding

*Binds Core §3.10, §11.* **Prerequisite: the Core §11 amendment (AB §0).**

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

### AB §11.3 Protocol versioning
*Binds Core §1.5.*

The Fraktal repository protocol is **versioned with an explicit handshake**, and
both bindings speak it. The shipped gateway today carries a `protocol` field but
**no version handshake**, and two OPC-UA-named diagnostic fields; creating the
neutral versioned protocol is therefore work on the **TC3 side as well**, not an
AB-only cost. Incompatibility fails closed and is reported, never negotiated
down silently.

### AB §11.4 Security
*Binds Core §14.*

**[PROVISIONAL S8]** CIP explicit messaging carries no equivalent of the OPC UA
security model. A deployment **shall** either prove a supported CIP Security
configuration, or place the controller side in an IEC 62443-aligned zone with
the gateway as the controlled conduit. The client-facing side **shall** use
authenticated TLS with least-privilege roles. **Anonymous controller writes are
not an acceptable baseline**, and PLC-side re-checking is defence in depth, not
a substitute for transport security.

### AB §11.5 Optional OPC UA projection
*Binds Core §11.7, Annexes F/J/K.*

OPC UA remains a permitted north-bound projection — embedded server where
supported, or a commercial gateway — generated from the same live model so it
cannot create a competing identity or hierarchy.

**Consequence for conformance, which Core must settle.** §11.7 and Annexes F/J/K
define PackML, Machinery and AAS/MTP *as OPC UA companion mappings*. If AB serves
them only through an optional projection, then *"Fraktal Core + PackML"* is
unconditional on TC3 and **conditional on the deployment** on AB, while Core §1.5
treats profile conformance as binding-independent. Either the projections are
restated against the neutral service, or §1.5 gains a per-binding qualifier.
**[PROVISIONAL S10]**

---

## AB §12 — Provisional-clause register

Every `[PROVISIONAL]` clause, its spike, and what it costs if the assumption
fails. This table is the Phase 0 work list.

| Clause | Spike | Assumption | If wrong |
|---|---|---|---|
| AB §2.2 | S2 | AOI signature change is breaking on import | version rule tightens: added parameter = major |
| AB §2.5 | S4 | L5X round-trips stably and faithfully | **binding not viable as drafted**; gates lose their input |
| AB §2.7 | S1 | controller clock + CIP Sync satisfy §2.7 | timestamp correlation limited; record as deviation |
| AB §3.3 | S2 | `InOut` carries structures; atomics only for In/Out | the single-`Ctx` design fails; contract must be decomposed |
| AB §3.5 | S4 | Logix SFC round-trips in L5X | generated charts drop to ST only |
| AB §3.10 | S7 | one bounded manifest fits the read budget | split per root with per-root revision |
| AB §4.1 | S6 | registry/manifest survive online change | commissioning gains a documented download step |
| AB §5.7 | S5 | the harness runs on an emulator in CI | §5.7 "runs in CI" becomes a recorded deviation |
| AB §8.11/§8.12, §10 | S3 | `GSV` and module objects supply health and timing | §8.11/§8.12/§10.6 reduce to a declared subset |
| AB §11.4 | S8 | CIP Security or a zone/conduit is achievable | writes cannot meet §14; binding is read-only until fixed |
| AB §11.5 | S10 | projections available where claimed | profile conformance becomes explicitly per-binding |

Two of these are structural rather than incremental: **S4** decides whether this
is a port or a rewrite, and **S2** decides whether AB §3.1's whole type shape
survives. Run those first.

---

## AB §13 — What this binding does not claim

- It has **not** been compiled, downloaded or run. No clause here is evidence.
- It requires **two Core amendments** that do not exist yet (AB §0). Until they
  land, a conforming Fraktal implementation cannot be written this way.
- Where it is weaker than Part II, it says so: tier composition and lifecycle
  ordering are gate-enforced rather than compiler-enforced (AB §3.1, §3.11,
  §3.14), and per-type lifecycle correctness is an argument from generation
  rather than an inheritance guarantee (AB §5.7).

The Core model — tiers, contracts, handshake, diagnostics, release, traceability
— is unchanged. That is the point: if this binding works, O8 is demonstrated
rather than asserted, and the same generic HMI drives a Logix machine with no
HMI change at all.
