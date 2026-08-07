# Allen-Bradley (Logix) port — implementation plan

Status: **plan, not a commitment**. Nothing in `FraktalCore/PLC/Allen-Bradley/`
exists yet; the directory is reserved. This document states what a second
binding has to deliver, the one architectural problem that makes it hard, three
ways through it with a recommendation, and the order to find out whether the
plan survives contact with the platform.

O8 says the normative model is platform-neutral and each platform is served by a
binding. **A second binding is the test of that claim, not a consequence of it.**
Until one exists, "platform-neutral" is a design intention that has never been
falsified.

---

## 1. What a binding must deliver

`Fraktal_TC3_Part_II.md` is the template. An Allen-Bradley Part II answers the
same questions, and the list is the scope definition:

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
| §11 connectivity | the OPC UA server, and the host-event path |

Plus the two things that are *not* Part II and must also be ported or replaced:
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
browsable array, which is exactly what an OPC UA client and a Logix tag browser
want anyway. It also bounds discovery cost statically (O4).

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

## 4. What ports unchanged

Stated to keep the estimate honest — this is most of the standard:

- the **three-tier model** and the recursion (§3.1–§3.3);
- the **data contract** `ParCfg`/`ParCmd`/`OutCmd`/`OutImm` — UDTs compose;
- the **PLCopen handshake** (§6.1) — it is a state machine, not a language feature;
- the **diagnostic model**, first-out, alarm rings, rationalization (§8);
- **sequences** (§6.8) — Logix has ST, Ladder, **and** SFC; the step-table form
  ports directly and the generator work already done applies;
- **safety separation** (§9) — GuardLogix is a different certified system with
  the same read-only boundary;
- the **HMI**. It binds published data over OPC UA and knows nothing about the
  PLC platform. If the AB binding publishes the same contract, **the existing
  Flutter HMI works against a Logix controller with no change at all** — and
  that is the single most convincing demonstration this port could produce.

---

## 5. Unknowns to settle before committing (spikes)

Each is a day or two and each can invalidate the plan. **Do these first.** I do
not have a Logix toolchain here, so every line below is a question, not a fact.

| # | Spike | Kills the plan if… |
|---|---|---|
| S1 | **OPC UA server**: which controllers/firmware embed one; tag-count and structure limits; whether UDT members browse as a tree | no viable server → self-description is gone and with it the generic HMI |
| S2 | **AOI parameter rules** for the target firmware: UDT In/Out, string handling, InOut aliasing, nesting depth | contract cannot be passed → §3.1's `Ctx` design fails |
| S3 | **Scale**: instances, memory and scan cost for a realistic forest (say 60 modules) | registry/rollup does not fit the scan |
| S4 | **Source-control form**: L5X export fidelity — is it round-trip stable and diffable? | no text form → no lint, no generation, no gates (§2.5 is a *shall*) |
| S5 | **Unit-test framework**: what plays TcUnit's role on Logix | no runner → §5.7 per-type suites cannot be a shall |
| S6 | **Online change** semantics vs. the module registry | registry cannot be extended online → commissioning workflow changes |

S1 and S4 are the two that decide whether this is a port or a rewrite.

---

## 6. Phases

Each phase ends in evidence, in the style of `FIRST_PROJECT_AGENT_GUIDE.md`.

**Phase 0 — spikes.** S1–S6. *Exit:* a written answer to each, and a go/no-go.

**Phase 1 — Core amendment (A).** Restate §2.2, §3.14 and §5.5 so the obligation
is neutral and `EXTENDS`/`SUPER^` are TC3 bindings. Re-audit Part I for the
untagged leaks already found — one `REFERENCE TO`, two `attribute '…'`, five
untagged `TwinCAT`, one `EtherCAT`, two `TcUnit`. *Exit:* Part I contains no
untagged platform construct; TC3 Part II gains the clauses that moved.

**Phase 2 — the binding document.** `Fraktal_AB_Part_II.md` answering §1's list.
*Exit:* every Core `shall` has a named AB mechanism or a recorded deviation.

**Phase 3 — the base.** `FRK_ModuleBase_Begin`/`_End`, the registry, the
handshake, the diagnostic core, one provider seam. *Exit:* a single hand-written
CM type runs the full §6.1 handshake against simulated I/O.

**Phase 4 — the generator.** Module-type generation (**G2**) so the composition
boilerplate is never typed, plus the AB lint rules that prove it. *Exit:* a new
type is generated, compiles, and the gate rejects a hand-broken one.

**Phase 5 — the library.** Port `Fraktal_Modules` — cylinder, clamp, digital
input, power group, two-hand, air monitor — each with its own suite. *Exit:*
per-type suites green on the AB runner.

**Phase 6 — a station + the HMI.** Compose the equivalent of the press bench;
point the **unmodified** Flutter HMI at the Logix OPC UA server. *Exit:* the
generic HMI renders and commands a Logix station with zero HMI changes. This is
the demonstration that O8 is real.

**Phase 7 — gates.** `plc_lint` rules for the AB form, a build gate, a test
gate, evidence records. *Exit:* the AB tree is gated on every commit like the
TC3 tree.

---

## 7. The dividend

Whether or not the port ships, Phase 0–2 pay for themselves:

1. **It falsifies or confirms O8.** Right now nothing does.
2. **It separates obligation from mechanism** in Part I. Any clause that cannot
   be restated without naming a TwinCAT construct is a clause that was never
   platform-neutral, and finding those is worth doing regardless.
3. **Two of the AB workarounds look like Core improvements** — the flat module
   registry (§3.2) and numeric keys (§3.4) would reduce published surface and
   discovery cost on TwinCAT too (O4).
4. **It forces the generators.** The TC3 binding can survive on hand-written
   boilerplate because the compiler enforces the shape. The AB binding cannot,
   so G2 stops being a nice-to-have.

---

## 8. Honest estimate

Not a schedule — a shape. Phase 3 is the one that dominates, and Phase 0 is the
one that decides whether the rest happens.

| Phase | Relative size | Note |
|---|---|---|
| 0 spikes | small | but gates everything |
| 1 Core amendment | small–medium | normative edit + re-audit |
| 2 binding doc | medium | mirrors an existing document |
| 3 the base | **large** | the 309 Core methods do not disappear, they change shape |
| 4 generator | medium | reuses the approach already proven for ladder |
| 5 library | medium | 12 types, mechanical once Phase 3 and 4 land |
| 6 station + HMI | small | if S1 passed, the HMI is free |
| 7 gates | medium | new lint rules, new runner integration |

The thing to resist is starting at Phase 3 because it is the interesting part.
Phase 0 answers whether Phase 3 is possible, and Phase 1 decides what it is
allowed to look like.
