# FraktalCore — reference implementation container

Holds the two reference implementations of the **Fraktal** standard (a platform-neutral,
recursive-module architecture for PLC equipment software — see `../Specification/Fraktal_Core_Part_I.md`).

```
FraktalCore/
├── PLC/        One directory per platform binding
│   ├── TwinCAT/       Fraktal/TC3 — IEC 61131-3 source + TcUnit suites
│   │   ├── Framework/          the reusable libraries a station consumes
│   │   ├── Tests and Examples/ internal fixtures (demo, press, aggregate tests)
│   │   └── scaffold/           copy-template for a new module type
│   └── Allen-Bradley/ reserved for a future binding
└── HMI/        Generic operator HMI (Flutter, Material 3) — walks the module forest over OPC UA
```

## PLC/TwinCAT/ — Fraktal/TC3
TwinCAT PLC projects (add each `.plcproj` to TwinCAT XAE; pin your build per Core §2 / TC3 §2.1).
Paths below are relative to `PLC/TwinCAT/`. The split separates what a station
**consumes** (`Framework/`) from what only exercises it (`Tests and Examples/`):

| Project | Role | Core ref |
|---|---|---|
| `Framework/Fraktal_Core/` | Framework **library**: contract types, interfaces, `FB_PermIntlk`, the lifecycle base classes (`FB_ControlModuleBase` / `FB_EquipmentModuleBase` / `FB_UnitBase`), profiler, connector base, recipe/access providers. Distributed centrally, consumed by pinned version. | §2.2 |
| `Framework/Fraktal_Modules/` | Reusable module library (cylinder CMs, clamp EM, sim models, TCP device presets). | §5.7 |
| `Tests and Examples/Fraktal_Demo/` | Executable two-root generic demonstration application. | §3.1a |
| `Tests and Examples/Fraktal_Press_Demo/` | Executable pneumatic-press virtual-commissioning example with safety aliases, collision interlocks, Control On/Off, and model recipes. | §3.1 / §9.8 |
| `Tests and Examples/Fraktal_Tests/` | Aggregate Core + Modules + Press Demo TcUnit manifest and sources — excluded from deployed runtime. The manifest sits beside the applications it links so all sources use import-safe downward paths. | §5.7 / §6.8 |
| `scaffold/FB_TemplateCM/` | Copy-template for a new module type (not compiled). Born RED; ships `SKELETON.md`. | Quick-start §2 |

See `PLC/TwinCAT/README.md` for bring-up and `PLC/TwinCAT/IMPLEMENTATION_NOTES.md` for every reconciliation vs. the spec drafts.

## HMI/ — generic operator client
One Flutter codebase for Windows/Linux/Android/Web. **Generic**: it walks the self-describing module
forest and renders it — a station adds zero HMI code. Binds only `PlcRepository`; ships `SimRepository`
(live demo), a native OPC UA adapter, and the Windows/Linux WebSocket gateway.
The packaged gateway also serves the matched compiled Web HMI; Windows includes
a tray/startup installer and Linux includes a systemd unit. See `HMI/README.md`,
`../Specification/HMI_CONTRACT.md`, and
`../Specification/WEB_HMI_GATEWAY_DEPLOYMENT.md`.

> **Status (2026-07-22):** HMI verified — `flutter analyze` clean, full test suite green,
> `flutter build web`/`windows` succeed. PLC **compiles under TwinCAT 4026** and has been
> **deployed to a runtime and exercised end-to-end** — the press demo runs, publishes over TF6100,
> and drives the generic HMI (config-manifest `QUERY_CONFIG`, `OPC.UA.DA` obscuring, live
> commanding all confirmed against real hardware). Still pending: a **pinned-build CI compile**
> (§1.5) and the improvement items in `../Specification/OBJECTIVES_AUDIT.md`. Add each `.plcproj`
> to a TwinCAT XAE solution via *PLC → Add Existing Item…* (see `PLC/TwinCAT/README.md` bring-up).
