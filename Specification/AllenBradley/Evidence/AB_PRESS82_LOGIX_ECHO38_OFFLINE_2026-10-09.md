# AB press82_echo38 — the press demo on Logix Echo, v38 (offline)

Recorded 2026-10-09 on the `SoftIndVM` workstation. The owner asked for a
**Studio 5000 v38 version of the press demo that runs under FactoryTalk Logix
Echo**, talking **CIP**, so the **Fraktal Windows desktop HMI** can be tested
against a simulated controller through the existing CIP gateway.

Logix Echo cannot emulate the bench's `1769-L24ER-QB1B` (5370/1769-L2x family
is absent from Echo's catalogue), so the station is retargeted to the
CompactLogix 5380 emulator profile: `5069-L310ER` at major revision 38 — the
same combination as the S12 v38 exploratory record
(`AB_S12_V38_STUDIO_EXPLORATORY_2026-08-29.md`), which verified 28+4 type
probes 0/0 in Studio v38.01. The Echo firmware package installed here is
CompactLogix 5380 emulator **38.011** (with `5069-L310ER` in its catalogue);
Logix Designer **v37 and v38** are installed; no v33 exists on this machine.

## Binding decisions recorded (asked, not defaulted)

1. **HMI target: the Fraktal Flutter Windows desktop HMI**, connected through
   `fraktal_ab_gateway.py` (pylogix EtherNet/IP/CIP → WebSocket
   `fraktal.opcua.gateway.v1`). No HMI code change is involved; the native
   build's `IoGatewayOpcUaClient` already serves `ws://`/`wss://` endpoints.
2. **Write surface: WRITE-ENABLED, token-gated.** The owner chose
   write-enabled for this test station. The gateway is started with a write
   token and a write root scoped to the press `HmiRequest` mailbox only; every
   write stays release-gated by the PLC (§7.6/§7.7). Core §14 obligations are
   armed with it: authenticated principals, no anonymous write. (The shipped
   AB default remains read-only; this decision is scoped to this test
   station and recorded here.)
3. **Download authorization: granted for the Logix Echo emulator on this
   workstation only**, after a clean Studio import. Studio import/Verify/
   download remain manual GUI steps by policy (S15); nothing automated them.

## What changed

- **`fraktal_ab_declaration.py`** — `Application` gains
  `controller_identity: str = ""`: the "catalog/series firmware" string
  stamped into the §3.10.2 manifest header. Empty keeps the pinned v33 bench
  default, so every existing declaration and recorded artifact is unaffected.
- **`fraktal_ab_generate.py`** — three additive changes:
  the manifest identity is now `app.controller_identity or CONTROLLER_IDENTITY`;
  every AOI's `SoftwareRevision` is derived from the declared major revision
  (`v<major>.00`; `33` keeps emitting `v33.00` byte-identically); the evidence
  dict reports `ControllerIdentity` and `EmbeddedIoModuleInSeed`.
- **Family finding, and the generator change it forced:** a fresh SDK-created
  `5069-L310ER` @ 38 seed carries **no `Discrete_IO` module entry** — the
  5380's discrete bank is part of the controller, unlike the L24ER whose fresh
  project carries the embedded module. The Inhibited flip is now conditional
  on the seed carrying the module. The guarantee it enforced is untouched:
  generated logic still references **no physical I/O operand** (asserted at
  generation, unchanged), so declared channels stay harness metadata —
  description, force mask, IoTag identity — on every family. On a 5380
  station the live channel words simply do not publish (the projection's
  `io_state` drops a module whose reads fail; every other surface is
  unaffected). `EmbeddedIoInhibited` is `null` when no module exists.
- **`fraktal_ab_press_echo38.py`** — the new committed declaration: a copy of
  the shipped press demo with `controller="5069-L310ER"`,
  `major_revision=38`, `controller_identity="5069-L310ER/A 38.011"` and
  updated comments. App name stays `Press`, so tag paths, module paths and
  the published contract are the press's. Selected with
  `FRAKTAL_AB_DECLARATION=fraktal_ab_press_echo38`.
- **`test_fraktal_ab_generate.py`** — new `Echo38TargetTests` (5 tests): the
  declaration validates clean; emission targets the emulator and stamps the
  v38 identity; AOIs carry `v38.00`; a 5380 seed needs no embedded module
  entry; the bench v33 evidence keys are unchanged.
- **Environment (this workstation):** `pylogix 1.1.5` + `websockets 17.1`
  installed from `requirements-gateway.txt`; 8 suite errors that predate this
  work (`ModuleNotFoundError: No module named 'pylogix'`) cleared by it.

## Generated artifact

`C:/work/press82_echo38.L5X`, SHA-256
`510854406AFC43F3DAC959917D4A3DC256011F0BE8194BEC95758E3093518644`,
generated twice byte-identically from the SDK-created seed
(`C:/work/echo38_seed.L5X`,
`121978864329C8748D7EF8138CA35D1590D4410A20934D67D77A38D7F8A70864`;
seed ACD `3211EE467EE70B13F32F6A9071EDDC4B036D900E5F869B2D4890C62DD661A840`).
Manifest `E5F914E06055CD3B / 15071508` — **equal to press80's recorded
manifest**: the published contract is unchanged by the retarget.

| Generated measure | press82_echo38 | press80 (recorded) |
| --- | ---: | ---: |
| ST source bytes | 294972 | 295085 |
| ST statement terminators | 3501 | 3502 |
| ST lines | 5594 | 5596 |
| RLL rungs | 20 | 20 |
| Declared data bytes (controller tags) | 110264 | 110264 |

The small ST deltas are press81's declared controller-metrics exclusion
(HEAD `7ba25cc`), not the retarget: the emitted application is **byte-identical
to a v33 generation of the shipped press** once the controller catalog, major
revision, AOI `SoftwareRevision`, manifest identity string and the embedded
module entry are normalised (verified by whole-file diff this session).
These are generated trends; **no Capacity Estimate exists for an Echo
emulator and none is claimed** — the press75 L24ER memory baseline is
untouched and unaffected.

## SDK licence finding

`AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md` §5 recorded
`CreateNewProjectAsync` and L5X→ACD conversion failing with
`OperationFailedException: No valid license` (no `LDSDK.EXE` feature) on the
engineering PC. **That refusal does not reproduce here.** With the local
activation present, `LogixProject.CreateNewProjectAsync` created the
`5069-L310ER` @ 38 seed and the probe converted the generated L5X to an ACD.
Versions on this workstation: Logix Designer SDK server shipped with Studio
**v38**; C# client package `RockwellAutomation.LogixDesigner.CSClient`
**2.1.974** (local feed); probe built `net8.0` / `win-x86` against the
installed x86 .NET 8 runtimes (8.0.20), client version overridden — the
csproj's recorded 2.2.1109/net10.0 pair is not what this workstation's feed
and runtimes carry. Seed creation, generation and conversion remain offline:
no upload, download, mode change or tag write exists in the probe.

## Validation

- Full AB suite: **1676 tests pass** (`press82_echo38_ab_tests_01.log`),
  including the 5 new Echo38 tests and the 56-test generator module.
- Rendition gate on press82_echo38: `Equal: true`
  (`press82_echo38_rendition_gate_01.json`) — the ladder AUTO graph equals the
  declared graph.
- `check_ab_contracts.py`: clean. `check_consistency.py`: 0 errors, 0
  warnings. `check_ab_spec.py`: the same 3 pre-existing errors recorded since
  press80 (readiness table shows R0–R5 PASS and §12 registers S16; doc drift,
  untouched here).
- **SDK import of the generated project: `ImportLog Warnings="0"
  Errors="0"`**, and the probe converted it to
  `C:/work/press82_echo38.ACD`
  (`453054EAFBFF73459EA9408A55B6033C521E276DF7BCFA4CC51A421E905432F8`),
  input unchanged by hash. This is the Studio-engine import proof available
  offline; it is not a Studio Verify.
- Mutation harness not re-run: the emitted logic is byte-identical to the
  shipped press's (whole-file diff above), so the press mutants exercise the
  same bytes.

## Owner steps (authorized; manual by policy)

1. **Echo chassis**: FactoryTalk Logix Echo Dashboard → new virtual chassis →
   add the CompactLogix 5380 emulator `5069-L310ER` @ **38.011**; set the
   emulator's EtherNet/IP address to `127.0.0.1` (port 44818) so the gateway
   and the HMI reach it on loopback. The Echo service and message broker are
   already Running on this workstation.
2. **Import**: open `C:/work/press82_echo38.ACD` in Logix Designer **v38**
   (or import `press82_echo38.L5X`), confirm the controller is
   `FraktalPhase0`, `5069-L310ER`, MajorRev 38.
3. **Verify**, then **download** to the Echo emulator and set **Run**.
   Record the run's serial number for the gateway's `--expect-serial` guard.
4. Hand back to the agent: CIP reachability probe, gateway on
   `ws(s)://127.0.0.1:<port>/fraktal` (write token + TLS for the write path),
   then the Windows HMI against the emulated press.

## Addendum 2 (same day, ~23:00–00:20 CSTM): v38 mnemonic dialect found; press86 compiles

The owner's Studio v38 Verify of press83 failed with hundreds of rung errors
("Update instruction to EQ/NE/GE/LT/GT/MOVE", "Referenced tag is undefined",
"Missing output instruction"). Root-caused empirically against the Logix Echo
compiler (5069/1756 v38.011 emulator at `127.0.0.1:44818`, serial
`601FC87B`), using a new offline SDK build mode added to
`Fraktal.Ab.OfflineProbe` (`--build <project> [target]`, targets
`DefaultTarget/EchoController/PhysicalController`; offline only, hash-guarded,
BuildAsync is a v37+ SDK operation):

1. **The v38.00 ladder compiler refuses the v33 compare/move mnemonics.**
   `EQU/NEQ/GEQ/LEQ/GRT/LES` must be spelled `EQ/NE/GE/LE/GT/LT` and `MOV`
   must be spelled `MOVE`; every other mnemonic tested (XIC, OTE, ADD, SUB,
   MUL) is unchanged. Proven both ways with minimal one-rung projects: EQ- and
   MOVE-spelled rungs build, EQU- and MOV-spelled rungs fail
   (`RxCMP_E_AUDIT_OUTPUTS`, and the "Update instruction" suggestions name the
   required spelling verbatim). Series outputs and comma-separated branch
   legs remain legal on v38. This is a Studio 5000 v38 dialect change the
   v33 emitter predates.
2. **`Generate → L5X → open/build` cannot gate ladder offline on v38.00.**
   Any project containing ladder fails `RxCMP_E_AUDIT_OUTPUTS` when the SDK
   opens the L5X directly — including an L5X SaveAs produced by Logix Designer
   itself from a compiling project. The reliable offline path is
   **partial-import of the L5X fragment into a fresh SDK-created ACD**
   (`PartialImportFromXmlFileAsync` at `/RSLogix5000Content/Controller`,
   system sections stripped) followed by `SaveAsync` and `--build` on the
   saved ACD. press86 was gated exactly that way.
3. **press82's first-cut also wrote `Local:1:O.Data`** (the §10.5.1 force
   apply). Legal on the L24ER bench (embedded I/O exists) and undefined on a
   5580 emulator → `RxSTX_E_TAG_NOT_FOUND`. Fixed by declaring the Echo
   station with `io_modules=()` — no I/O exists behind it, so no force words
   exist. The emitter's no-physical-operand assertion never caught this
   because its regex matched `Local:I`, not the real `Local:1:O` shape; the
   assertion regex is unchanged here (the declaration can no longer produce
   the operand) and is noted for a follow-up hardening.

**Generator changes:** `chain_ld_rungs` now maps the compare/move mnemonics
for `major_revision >= 38` (v33 output stays byte-identical); the rendition
gate reads both spellings back. press86_echo38: declaration unchanged from
the addendum-1 retarget plus `io_modules=()`.

**press86_echo38** — `C:/work/press86_echo38.L5X`
`FA76E84A9D5501DFE782A7958BE22190CDD88CE6AF0CD491BC177BA94DEACAE4`; delivered
as `C:/work/press86_echo38.acd`
(`E51B565C7EBC388408167BF59160D93B5AE44CC79E2C5AEFEFD9331A0361A9E4`),
created by fresh-ACD partial import (`ImportLog 0/0`) and **offline-compiled:
`Build succeeded` on BOTH `EchoController` and `PhysicalController`
targets**. Manifest still `E5F914E06055CD3B / 15071508` (contract unchanged).
Full AB suite 1676 OK (`press86_echo38_ab_tests_01.log`); rendition gate
`Equal: true` on press86 (v38 spellings) and on the v33 press (regression);
rendition tests OK.

Owner gate: open `press86_echo38.acd` in Studio v38, Verify (expected clean),
download to the Echo emulator, Remote Run — then the CIP gateway and the
Windows HMI test proceed.

## Not claimed

No controller fit, capacity or timing claim of any kind; no native-hardware
parity (the physical bench evidence stands separately); Echo's emulator
execution model is not the bench controller's. press75's measured memory
baseline is untouched. The write-enabled gateway decision is recorded above
and applies to this test station only. A Studio-side Verify of
`press86_echo38.acd` by the owner remains the final gate before download;
the offline `--build` compile is the same compiler family but was performed
through the SDK service.


## Addendum (same day, ~20:30 CSTM): retarget 5069-L310ER → 1756-L81E

The owner's Echo Dashboard "Add controller" Type list offers exactly
**ControlLogix 5580, ControlLogix 5590 and GuardLogix 5580** emulators —
**no CompactLogix 5380 type**, although 5380 firmware packages (incl. 38.011)
are installed under `Firmware Packages\`. press82's 5069-L310ER target is
therefore not creatable on this workstation's Dashboard, and the station was
retargeted to the **ControlLogix 5580 emulator: `1756-L81E` @ 38.011** — a
catalog the S12 v38 SDK enumeration also recorded. The declaration
(`fraktal_ab_press_echo38.py`), its tests and the identity were changed in
place (nothing committed at the time); generator code unchanged.

- Seed `C:/work/echo38_5580_seed.ACD`
  `4DC33503828F594C5629F740ADDDA396B9FDEE29F22A6185D591C5C20C51880A`;
  export L5X `FA96516C9E8D7F45874A825003756363C71DE528EDEDC0BD2766C19C1711C0C7`.
- **press83_echo38.L5X**
  `345E4F2A50E390C01FF0090C9F704DAE3E6DCDD6E6AEBE206B729ACE0458F8AA`,
  manifest `E5F914E06055CD3B / 15071508` (still press80's contract), identity
  `1756-L81E/A 38.011`. Rendition gate `Equal: true`; generator module 56
  tests OK.
- SDK import of press83: `ImportLog Summary Warnings="0" Errors="0"`
  (RSLogix 5000 v38.00 owner SoftIndVM); ACD
  `A8436C67CBC33A58461C010971BE672938A9820A91730EB130BB3C6050D7CC90`.
- press82_echo38 (5069-L310ER) remains recorded above as generated and
  importable, but has no creatable Echo chassis on this workstation.
- The emulated 5580 has **no local discrete I/O** (a 1756 chassis is
  populated with modules), so the press's declared channels have no hardware
  behind them on this station and no live channel words publish — the
  declaration docstring says so.

