# Fraktal

**A platform-neutral standard — and reference implementation — for PLC equipment software.**

One recursive three-tier module model, one data contract, one PLCopen command
handshake, one diagnostic model. A station describes itself over OPC UA, so a
single **generic HMI renders and commands it with zero per-station screen code**.

Fraktal synthesises established industry practice — ISA-88/IEC 61512 (physical &
procedural model), PLCopen (command handshake, motion & safety FBs), ISA-18.2
alarm management, IEC 62443 security, and the OPC UA companion models — into one
coherent architecture, defined platform-neutrally and delivered first as a
**TwinCAT 3** binding with a **Flutter** operator HMI.

---

## Why

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

The full objective set (**O1–O10**, in priority order) is in
[`Specification/Fraktal_Core_Part_I.md` §1.1](Specification/Fraktal_Core_Part_I.md) —
including **O9 good coding and engineering practice** and **O10 industrial-grade
robustness**.

---

## Repository layout

```
Specification/     The standard.
  Fraktal_Core_Part_I.md    Part I — platform-neutral normative core (§1–14)
  Fraktal_TC3_Part_II.md    Part II — the TwinCAT 3 binding (Fraktal/TC3)
  HMI_CONTRACT.md           the symbol → widget bind table the HMI implements
  OPCUA_TRANSPORT.md        the OPC UA transport, config manifest & read tiers
  FIRST_PROJECT_AGENT_GUIDE.md   empty solution → deployed, HMI-commandable station
  OBJECTIVES_AUDIT.md       current audit against O1–O10 + improvement plan
  Annex_A … Annex_K         worked examples exercising every contract end-to-end

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
    Allen-Bradley/        reserved for a future binding
  HMI/     Generic operator HMI (Flutter, Material 3) — Windows/Linux/Android/Web
    lib/                  the app (data / domain / state / ui)
    native/opcua/         native OPC UA client (open62541 + Mbed TLS via dart:ffi)
    gateway/              headless WebSocket gateway for the Web transport

AGENTS.md          working briefing for AI coding agents editing this repo
```

## Documentation map — start here

| You want to… | Read |
|---|---|
| Understand the model | [`Fraktal_Core_Part_I.md`](Specification/Fraktal_Core_Part_I.md) (§1 foreword, §3 architecture) |
| Build your first module | [`Fraktal_QuickStart_and_Suite.md`](Specification/Fraktal_QuickStart_and_Suite.md) |
| Deploy a station & connect the HMI | [`FIRST_PROJECT_AGENT_GUIDE.md`](Specification/FIRST_PROJECT_AGENT_GUIDE.md) |
| Bring up the PLC (TwinCAT) | [`FraktalCore/PLC/TwinCAT/README.md`](FraktalCore/PLC/TwinCAT/README.md) |
| Run / build the HMI | [`FraktalCore/HMI/README.md`](FraktalCore/HMI/README.md) |
| See what's proven vs. pending | [`OBJECTIVES_AUDIT.md`](Specification/OBJECTIVES_AUDIT.md) |

---

## Status (2026-07-22)

- **HMI** — `flutter analyze` clean, full test suite green, `flutter build web`/`windows` succeed.
- **PLC** — compiles under **TwinCAT 4026**, loaded on a development runtime, and exercised
  end-to-end over TF6100: the internal Press bench cycles, publishes over OPC UA, and drives
  the generic HMI (config-manifest `QUERY_CONFIG`, `OPC.UA.DA` obscuring, live
  commanding — all confirmed against the development runtime). This is not a
  real-machine project or production acceptance result.
- **Pending** — a pinned-build **CI compile/test gate** (spec §1.5 makes it a
  *shall*), gateway read-tier parity for Web, and the remaining items tracked in
  [`OBJECTIVES_AUDIT.md`](Specification/OBJECTIVES_AUDIT.md).

This project reports status honestly (O10): it distinguishes what is proven from
what is deferred, and names the gaps rather than hiding them.

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
