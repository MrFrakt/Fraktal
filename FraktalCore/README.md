# FraktalCore — reference implementation container

Holds the two reference implementations of the **Fraktal** standard (a platform-neutral,
recursive-module architecture for PLC equipment software — see `../Specification/Fraktal_Core_Part_I.md`).

```
FraktalCore/
├── PLC/        One directory per platform binding
│   ├── TwinCAT/       Fraktal/TC3 — IEC 61131-3 source + TcUnit suites
│   │   ├── Framework/          the reusable libraries a station consumes
│   │   ├── Examples/           demo + press fixtures (press ships PressTests)
│   │   ├── Tests/              aggregate Core/Modules TcUnit project
│   │   └── scaffold/           copy-template for a new module type
│   └── Allen-Bradley/ reserved for a future binding
└── HMI/        Generic operator HMI (Flutter, Material 3) — walks the module forest over OPC UA
```

## PLC/TwinCAT/ — Fraktal/TC3
TwinCAT PLC projects (add each `.plcproj` to TwinCAT XAE; pin your build per Core §2 / TC3 §2.1).
Paths below are relative to `PLC/TwinCAT/`. The split separates what a station
**consumes** (`Framework/`), what demonstrates it (`Examples/`), and what validates it (`Tests/`).
Run **both** TcUnit gates — the Press integration suites live with their internal
feature-testing bench:

| Project | Role | Core ref |
|---|---|---|
| `Framework/Fraktal_Core/` | Framework **library**: contract types, interfaces, `FB_PermIntlk`, the lifecycle base classes (`FB_ControlModuleBase` / `FB_EquipmentModuleBase` / `FB_UnitBase`), profiler, connector base, recipe/access providers. Distributed centrally, consumed by pinned version. | §2.2 |
| `Framework/Fraktal_Modules/` | Reusable module library (cylinder CMs, clamp EM, sim models, TCP device presets). | §5.7 |
| `Examples/CoreDemo/Fraktal_Demo/` | Executable two-root generic demonstration application. Sources only — it has no `.tsproj`, so add it to a solution to build. | §3.1a |
| `Examples/PressDemo/` | Executable internal Fraktal feature-testing bench using a simulated pneumatic press; not a real or production machine project. | §3.1 / §9.8 |
| `Tests/Fraktal_Tests.plcproj` | Aggregate Core + Modules TcUnit gate — excluded from deployed runtime. Self-contained: every Compile path is downward from `Tests/`. | §5.7 / §6.8 |
| `Examples/PressDemo/PressTests.plcproj` | The internal Press bench's integration gate. Separate because TwinCAT forbids `..` in a Compile path, so a manifest in `Tests/` cannot reach `Examples/`. | §5.7 |
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

> **Status (2026-08-02):** HMI verified — `flutter analyze` clean, **166 tests passing**
> (4 intentional live-environment skips) on the pinned Flutter 3.44.6;
> `flutter build web`/`windows` succeed. PLC source gate clean: **265 files in both
> build profiles**, 31 linter fixtures green. The split TcUnit program is green on an
> isolated runtime — **92/92 tests across 28 suites** (Core+Modules 84/26, internal
> Press bench 8/2), archived with artifact hashes in `../Specification/Evidence/`.
> PLC **compiles under TwinCAT 4026** and has been **loaded on a development runtime and
> exercised end-to-end** — the internal Press bench runs, publishes over TF6100, and drives
> the generic HMI (config-manifest `QUERY_CONFIG`, `OPC.UA.DA` obscuring, live commanding).
> This is framework-integration evidence, not a production-machine claim. Still pending:
> the PLC compile/TcUnit CI jobs exist but stay **skipped** until a licensed self-hosted
> TwinCAT runner is registered (§1.5), plus the improvement items in
> `../Specification/OBJECTIVES_AUDIT.md`. Add each `.plcproj`
> to a TwinCAT XAE solution via *PLC → Add Existing Item…* (see `PLC/TwinCAT/README.md` bring-up).
