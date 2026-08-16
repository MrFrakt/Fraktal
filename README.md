# Fraktal

**A control and automation framework for machine builders — from the PLC to the
operator HMI.**

Compose the machine from tested module types. Write only the step sequences.
Do not build an HMI at all: the machine describes itself, and one generic HMI
discovers it.

> **Alpha pre-release.** The framework, the reference implementation and the
> toolchain are complete enough to build and run a station end-to-end, and are
> gated on every commit. They have not yet run a production line. §Status below
> says exactly what is proven and what is not — this project reports that
> honestly rather than aspirationally (O10).

---

## Concept

The goal is to bring a machine into service with **as little application
programming as possible**, and to make what remains the part that is actually
specific to your machine.

**Compose, don't write.** Equipment is assembled from reusable module *types* in
three recursive tiers — device (`FB_ControlModule`), bounded function
(`FB_EquipmentModule`), station (`FB_Unit`). A type is declared, wired once in
`Setup`, and it is finished: it ships with its own tests, its own reason codes,
and its own published contract.

**Inherit everything that is the same on every machine.** The PLCopen command
handshake, mode and state machines, first-out diagnostics, the alarm model,
recipe load and migration, part traceability, the OPC UA data contract, and the
HMI data mirror are written **once at the level that owns them** and inherited.
A concrete type overrides one method — its device logic — and nothing else.

**The HMI is not built, and not generated either.** The station publishes its
own module forest over OPC UA; a single generic HMI walks it at runtime and
renders the tree, the commands, the alarms and the §3.13 flow charts. Add a
module and it appears. There is no per-station screen code, and — unlike a
generator — **no generated artifact to regenerate, redeploy, or keep in sync**
when the machine changes.

**What is left for you to write is the step sequence.** The process itself: what
this machine does, in what order. In ST, SFC or Ladder — the choice is the
author's, and all three are the same chain against the same base class.

### What you write vs. what you inherit

| | Written per machine | Inherited / discovered |
|---|---|---|
| **Device logic** | one `CASE` in `_M_Dispatch` per *new* type | lifecycle, edges, state mapping, abort, reset |
| **Sequences** | the steps and their order | step records, stall diagnosis, timing, re-arm |
| **Interlocks** | the conditions, by name | first-out selection, release reports, HMI display |
| **Commands** | which child, which command | the entire §6.1 handshake |
| **Alarms** | a reason code from your band | ring buffer, rationalisation, shelving, audit |
| **Recipes** | the record layout | provider transport, migrate-or-fault, changeover |
| **HMI** | *nothing* | the whole operator interface |
| **I/O** | tags, addresses, polarity | bounds, health, duplicate and diagnostic joins |

### What Fraktal is not

Stated plainly, because the concept above invites the comparison:

- **There is no graphical machine configurator.** You compose in IEC 61131-3
  declarations, not in a wizard.
- **PLC code is not generated from a machine description.** The toolchain
  generates *bodies* — ladder rungs and chart steps from a declaration, module
  scaffolds — and mechanically checks the rest. It does not synthesise a station.
- **It is not a runtime you buy.** It is a standard, a reference implementation,
  and the gates that keep the two honest, under the MIT licence.

The full objective set (**O1–O10**, in priority order) is in
[`Specification/Fraktal_Core_Part_I.md` §1.1](Specification/Fraktal_Core_Part_I.md) —
including **O9 good coding and engineering practice** and **O10 industrial-grade
robustness**.

---

## Why it is built this way

Equipment software is usually rewritten per machine, per station, per screen.
Fraktal pays standardisation **once per reusable module *type***, not once per
step or per station:

- **Write less.** Issue a command, wait for `Done`. No per-step boilerplate; the
  lifecycle, state mapping, and HMI data mirror are inherited from base classes.
- **Diagnose for free.** When a sequence stalls, the operator gets a precise root
  cause — *"Step N stalled → awaiting `Module.Command` → reason"* — produced
  automatically from the contract, never hand-coded.
- **Render generically.** The HMI walks the self-describing module forest over
  OPC UA. Adding a module type adds HMI automatically; a station adds zero HMI code.
- **Scale.** One model composes device → equipment module → unit → whole line;
  and the published/streamed surface stays proportional to what is consumed
  (config served on demand, live data tiered by cadence).

Fraktal synthesises established industry practice — ISA-88/IEC 61512 (physical &
procedural model), PLCopen (command handshake, motion & safety FBs), ISA-18.2
alarm management, IEC 62443 security, and the OPC UA companion models — into one
coherent architecture, defined platform-neutrally and delivered first as a
**TwinCAT 3** binding with a **Flutter** operator HMI.

---

## Repository layout

```
Specification/     The standard — and ONLY the standard, at this level.
  Fraktal_Core_Part_I.md    Part I — platform-neutral normative core (§1–14)
  Fraktal_TC3_Part_II.md    Part II — the TwinCAT 3 binding (Fraktal/TC3)
  Fraktal_AB_Part_III.md    Part III — the Allen-Bradley Logix binding (draft, pre-spike)
  HMI_CONTRACT.md           the symbol → widget bind table the HMI implements
  OPCUA_TRANSPORT.md        the OPC UA transport, config manifest & read tiers
  SAFETY_AND_CONTROL_POWER_PROFILE.md   the §9.8 profile
  LOCALIZATION_AND_MODULE_CONTENT.md    the localization/content contract
  reason_rationalization.json           the §8.9 registry (machine-read)
  Annexes/           worked examples A–K exercising every contract end-to-end
  Guides/            how to apply it: first project, XAE workflow, deployment
  Reports/           audits, status, plans, one-off analyses
  Evidence/          dated TwinCAT runtime evidence (append-only)
  AllenBradley/      the Fraktal/AB working set + its spike evidence
  README.md          what belongs at each level, and why

FraktalCore/
  PLC/     One directory per platform binding (§1.1 O8: the model is portable,
           each platform is served by its own binding)
    TwinCAT/              Fraktal/TC3 reference implementation (IEC 61131-3)
      Framework/          the reusable libraries — what a station consumes
        Fraktal_Core/       base classes, contracts, providers
        Fraktal_Modules/    reusable module library (cylinder CM, clamp EM, …)
      Examples/          executable internal fixtures, NOT conformance targets
        CoreDemo/           two-root generic demo application (sources only)
        PressDemo/          internal feature-testing bench + PressTests suite
      Tests/             isolated validation sources
        Fraktal_Tests.plcproj  the aggregate TcUnit manifest
        Fraktal_Tests/         Core + Modules suites (simulated HAL)
      scaffold/           copy-template for a new module type (ships SKELETON.md)
      tools/              the TwinCAT gates and generators (they ship inside the
                          binding they check — see below)
    Allen-Bradley/        binding drafted (Part III) + its own tools/ probe suite
  HMI/     Generic operator HMI (Flutter, Material 3) — Windows/Linux/Android/Web
    lib/                  the app (data / domain / state / ui)
    native/opcua/         native OPC UA client (open62541 + Mbed TLS via dart:ffi)
    gateway/              headless WebSocket gateway for the Web transport

FraktalCore/PLC/TwinCAT/tools/    The TwinCAT gates and generators. They live
           inside the binding they check, beside Allen-Bradley/tools/, so a
           binding carries its own toolchain and neither can silently drift.
  plc_lint.py             18 source rules, both build profiles
  ld_rung_gen.py          ladder rungs from a declaration; ld_dump / sfc_dump read them back
  Invoke-TwinCatBuild.ps1 CheckAllObjects on every solution
  Invoke-TwinCatTcUnitGate.ps1 / tcunit_to_junit.py   runtime gate + result validation

tools/     The repository-level gates — the ones that span more than one tree
  check_consistency.py    agreement BETWEEN artifacts (PLC ↔ HMI ↔ docs)
  check_ab_spec.py / check_ab_contracts.py   the Fraktal/AB specification gates

AGENTS.md          working briefing for AI coding agents editing this repo
```

## Documentation map — start here

| You want to… | Read |
|---|---|
| Understand the model | [`Fraktal_Core_Part_I.md`](Specification/Fraktal_Core_Part_I.md) (§1 foreword, §3 architecture) |
| Build your first module | [`Fraktal_QuickStart_and_Suite.md`](Specification/Guides/Fraktal_QuickStart_and_Suite.md) |
| Deploy a station & connect the HMI | [`FIRST_PROJECT_AGENT_GUIDE.md`](Specification/Guides/FIRST_PROJECT_AGENT_GUIDE.md) |
| Reproduce XAE compile, library install, and TcUnit runs | [`TWINCAT_XAE_WORKFLOW.md`](Specification/Guides/TWINCAT_XAE_WORKFLOW.md) |
| Bring up the PLC (TwinCAT) | [`FraktalCore/PLC/TwinCAT/README.md`](FraktalCore/PLC/TwinCAT/README.md) |
| Run / build the HMI | [`FraktalCore/HMI/README.md`](FraktalCore/HMI/README.md) |
| See what's proven vs. pending | [`OBJECTIVES_AUDIT.md`](Specification/Reports/OBJECTIVES_AUDIT.md) |
| Know what is generated, checked, or still hand-written | [`AI_DEVELOPMENT_AND_AUTOMATION.md`](Specification/Reports/AI_DEVELOPMENT_AND_AUTOMATION.md) |
| Enable output forcing for commissioning | [`Fraktal_Core_Part_I.md` §7.5](Specification/Fraktal_Core_Part_I.md) + [`Fraktal_TC3_Part_II.md` TC3 §7.5](Specification/Fraktal_TC3_Part_II.md) |
| Port Fraktal to another PLC platform | [`ALLEN_BRADLEY_PORT_PLAN.md`](Specification/AllenBradley/ALLEN_BRADLEY_PORT_PLAN.md) |
| Read the Allen-Bradley binding (draft, pre-spike) | [`Fraktal_AB_Part_III.md`](Specification/Fraktal_AB_Part_III.md) |

---

## Status (2026-08-16)

**Proven at this revision**

- **PLC compile** — `FraktalCore/PLC/TwinCAT/tools/Invoke-TwinCatBuild.ps1` runs
  `CheckAllObjects()` on
  **all five solutions** (Core, Modules, the Press bench, and both test
  projects) under **TwinCAT 4026**, green — re-run at this revision against
  Core **`0.5.0.0`** / Modules **`0.4.0.0`** after save-as-library and install,
  which is the step the applications need before they can resolve anything
  added to a library.
- **PLC runtime tests, Core + Modules** — **106/106 across 31 suites, 0 failures**
  on the development usermode runtime (2026-08-16). Every suite that had never
  executed now runs, including `ConfigWriteTests` and `FB_Engineering_Tests`.
  Evidence in [`Specification/Evidence/`](Specification/Evidence/).
  **Run by an operator following the §6.2 procedure, not by the gate** —
  `Invoke-TwinCatTcUnitGate.ps1` automates target selection and activation, but
  its PLC login does nothing (see *Open* below), so an earlier claim that it
  drove the run end-to-end has been withdrawn.
- **PLC runtime tests, Press bench** — **8/8 tests across 2 suites, 0 failures**
  on an isolated VM, validated by `FraktalCore/PLC/TwinCAT/tools/tcunit_to_junit.py`
  against the expected
  runner identity and counts. Log, JUnit and SHA-256s in
  [`Specification/Evidence/`](Specification/Evidence/).
- **Press AUTO chain in all three sequence languages** — the Ladder and SFC
  renditions have now **executed on the test-bench PLC** with the press demo
  (2026-08-16), alongside the ST twin that ships by default. This is what turns
  O2's three-language promise from graph equivalence into execution. No log is
  archived for this run yet, so by the §8 evidence rule it is a recorded
  observation rather than release evidence.
- **PLC source gate** — `plc_lint.py`: **294 files clean in both build profiles**
  (modern and the 4024 legacy profile).
- **Cross-artifact gate** — `check_consistency.py --strict`: **0 errors, 0
  warnings** across test inventory, localization and ST↔LD sequence-rendition
  parity. Runs hosted on every commit.
- **Toolchain** — **120 tests** over the tooling itself (72 in the TwinCAT
  binding's own `tools/`, 48 in the repository-level `tools/`).
- **HMI** — `flutter analyze` clean and **235 tests passing** (4 intentional
  live-environment skips) on the pinned Flutter 3.44.6, re-run at this revision.

**Not proven at this revision**

- **HMI builds** — `flutter build web`/`windows` succeeded as of **2026-08-02**
  and have not been re-run since; only analyze and the test suite were.
- **§7.5 commissioning gates and §10.5.1 output forcing** — the PLC half now
  executes: `FB_Engineering_Tests` is green in the Core + Modules run above, so
  the gate register, the standing annunciation and the fail-closed force gate
  are proven in execution rather than argued from source. **Forcing has still
  never driven a physical terminal.** Not implemented on Allen-Bradley
  (Part III), deliberately.
- **End-to-end over TF6100** — the Press bench has cycled on a *development*
  runtime, published over OPC UA and driven the generic HMI (config-manifest
  `QUERY_CONFIG`, `OPC.UA.DA` obscuring, live commanding). A development runtime
  is not a machine, and this is not a production acceptance result.

**Open**

- **The PLC compile job is armed; the TcUnit job is not.** A licensed
  self-hosted runner is registered with the `twincat` label and
  `HAS_TWINCAT_RUNNER` is set, so `ci.yml` compiles the PLC from now on.
  `HAS_TWINCAT_TEST_RUNTIME` stays unset deliberately — see the next item — and
  neither check can be made *required* while the host carries trial licences
  only, since renewal is an interactive captcha (§1.5 makes CI a *shall*).
- **The gate cannot log in to the PLC.** `ITcPlcOnline.Login()` returns without
  error, writes nothing to any DTE output pane, and leaves `IsLoggedIn` false
  indefinitely. Everything up to activation is verified. The eliminations, and
  why guide §9's "no hidden script logged in" now reads as a constraint rather
  than a preference, are recorded in
  [`TWINCAT_XAE_WORKFLOW.md`](Specification/Guides/TWINCAT_XAE_WORKFLOW.md) §9.1.
  Reading a result is solved — `Read-TcUnitResults.ps1` pulls TcUnit's own
  per-test results over ADS — but nothing can start the run for it to read.
- Gateway read-tier parity for Web, live-transport and deployment-profile
  acceptance, and the remaining items in
  [`OBJECTIVES_AUDIT.md`](Specification/Reports/OBJECTIVES_AUDIT.md).

This project reports status honestly (O10): it distinguishes what is proven from
what is deferred, and names the gaps rather than hiding them. A framework that
overstates its own maturity is not one you can trust with a machine.

---

## Quick start

**PLC (TwinCAT 3, 4024+/4026):** add each `.plcproj` to a TwinCAT XAE solution via
*PLC → Add Existing Item…* (do not open a `.plcproj` directly). Build & install
`Framework/Fraktal_Core`, then `Framework/Fraktal_Modules`, then the applications
under `Examples/`; run the aggregate TcUnit suite from its own `FraktalTests.slnx`. See
[`FraktalCore/PLC/TwinCAT/README.md`](FraktalCore/PLC/TwinCAT/README.md).

**HMI (Flutter):** from `FraktalCore/HMI/`
```
flutter pub get
flutter analyze
flutter test
flutter run -d windows   # or chrome (Web) / linux / android
```
Native OPC UA on Windows needs Developer Mode (Flutter plugin symlinks) and a
reachable `opc.tcp://` server. See [`FraktalCore/HMI/README.md`](FraktalCore/HMI/README.md).

---

## Contributing

- Read [`AGENTS.md`](AGENTS.md) — the working briefing on the model, the coding
  guardrails, and where things live. It applies to humans too.
- **Every `shall` in the spec is a requirement.** Machine-verifiable rules
  (naming, contract usage, step/condition records, per-type tests) are meant to
  be enforced by a CI/lint gate on every commit (§1.5, §5.5) — see the audit for
  the plan to add it.
- Reusable module **types** ship a TcUnit suite that runs against the simulated
  HAL and must be green before the type is released or changed (§5.7).
- Follow the idioms of the code around you (O9); keep changes to released types
  additive and versioned (§1.5).

## License

Fraktal is open-source software distributed under the [MIT License](LICENSE).
The current source of record is the `MrFrakt/Fraktal` monorepo.
