# Fieldbus ADS Adapter — Contract Sketch (TC3 §10.6)

*How to replace the simulated fieldbus with **real EtherCAT data**. Binds Core §10.5.1. This is a sketch: the data contract and the building blocks are fixed; every TwinCAT index group, ADS port, and `Tc2_EtherCAT` FB signature named here **must be verified against the pinned TwinCAT / Beckhoff InfoSys** before you trust it — consistent with the whole project's "pin and verify" discipline.*

## What already exists (the fixed contract)

The **data model is done and platform-neutral** — you are only filling it, never redesigning it:

| Layer | Artifact | Where |
|---|---|---|
| PLC types | `ST_BusNode`, `ST_IoChannel`, `E_NodeState`, `E_ChannelDir`, `E_ChannelKind` | `FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/DUTs` |
| PLC seam | `I_FieldbusScanner` (interface) + `FB_EcFieldbusScanner` (skeleton) | `FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/{Interfaces,Connectivity}` |
| HMI model | `BusNode`, `IoChannel`, `NodeState` (ordinals aligned to the PLC enums) | `FraktalCore/HMI/lib/domain/fieldbus.dart` |
| HMI seam | `OpcUaRepository` + `OpcUaSnapshotMapper` | `FraktalCore/HMI/lib/data` |
| HMI view | `FieldbusTree` (node colouring + I/O panel + gated force) | `FraktalCore/HMI/lib/ui/fieldbus_tree.dart` |

The `E_NodeState` ordinals (`OFFLINE=0 … OPERATIONAL=4, FAULT=5`) are the wire contract between PLC and HMI and are already verified equal on both sides.

## Two implementation paths (pick one)

### Path A — PLC-published topology (recommended)

The PLC scans its own bus and **publishes the `ST_BusNode` table over OPC UA**; the HMI just reads OPC UA like everything else. This is the objective-aligned path: works on **all four platforms including Web** (no browser-TCP problem, O8), keeps fieldbus knowledge in one place (O1), and any bus that can fill the table works (O4).

```
EtherCAT master ──(Tc2_EtherCAT / ADS)──▶ FB_EcFieldbusScanner ──fills──▶ ST_BusNode[]
                                                                              │ (§3.10 pragma)
                                                                     TF6100 OPC UA server
                                                                              │
                              HMI fieldbus() ◀──OPC UA read── (desktop/mobile/Web via server)
```

**Steps:**
1. Reference `Tc2_EtherCAT`. Implement `FB_EcFieldbusScanner` (skeleton provided) — see "EtherCAT specifics" below.
2. Hold one `ST_BusNode` table (`ARRAY[1..MAX_BUS_NODES]`) in a system-level program; call `Scan()` slowly (~200 ms) and `RefreshValues()` every cycle.
3. Expose the table with the OPC UA pragma (`{attribute 'OPC.UA.DA'}`) so TF6100 publishes it (TC3 §3.10).
4. HMI: implement `fieldbus()` as an OPC UA read of that table → `List<BusNode>`. (This can live in the same OPC UA repository that serves the module tree.)

### Path B — direct client adapter (desktop/mobile only)

A thick client may speak to the master directly, but this duplicates bus
knowledge in the HMI. The shipped native repository instead reads the
PLC-published Path-A topology together with the module tree. Web uses the
versioned WebSocket gateway described in `OPCUA_TRANSPORT.md`.

## EtherCAT specifics (Path A scanner) — verify each against InfoSys

The `FB_EcFieldbusScanner` skeleton names these; here is what each must do.

**Master identity.** Address the EtherCAT master by its **AmsNetId** (from the master's ADS tab in the project). The master ADS port for diagnostics is version-specific — confirm it.

**Topology & state (`Scan`).**
- `FB_EcGetSlaveCount` → number of slaves (0 ⇒ master down ⇒ return 0, node table empty, HMI shows the whole bus offline).
- `FB_EcGetAllSlaveStates` → the AL-state word per slave (bulk, one ADS call). Map with `_M_MapState()`:
  - AL-state low nibble: `0x01 INIT`, `0x02 PREOP`, `0x03 BOOTSTRAP`, `0x04 SAFEOP`, `0x08 OP`; error/fault bit `0x10`. **Confirm these constants** — they are the EtherCAT AL-status values and are stable, but verify against your `Tc2_EtherCAT`.
- `FB_EcGetSlaveIdentity` (or `FB_EcGetSlaveAddrs` + `FB_EcGetSlaveIdentity`) → vendor/product/revision → `ST_BusNode.TypeId`; the topological/auto-increment address → `ST_BusNode.Address`; the slave's order gives you `ParentIdx` (couplers are parents of their terminals).

**Channels & scaling.**
- Channel *identity* (names, direction, digital/analog, unit) comes from the **configured PDO mapping / ESI / TMC**, not from a live read. The cleanest source is the project's own I/O mapping — the terminals are already linked to PLC variables.
- Channel *live values*: read from the **PLC process image** (the variables the terminals are linked to), **not** by re-reading the master. The recommended pattern in `RefreshValues()` is that the application hands the scanner a reference to each owning module's HAL struct (§3.6) — which already mirrors the terminal — so no raw process-image address math and the "channel ↔ owning module" link (browse path, §4.8) is exact by construction.
- Analog raw→engineering scaling (raw `INT` → `REAL` + `Unit`) comes from the ESI/TMC or the owning CM's `ParCfg`.
- CoE object dictionary reads (`FB_CoeSdoReadEx`, AoE) are available if you need device-reported names/objects for devices without a configured mapping — heavier, use sparingly.

**Force (`ForceChannel`) — output-only, by rule (Core §10.5.1).**
- The caller (`FB_UnitBase`/HMI) has **already** checked §7.6+§7.7 and will log the §8.3 event. The scanner only performs the write. **Do not re-gate; do not skip the log.**
- **The method writes the mapped *output* variable through the application — nothing else.** It rejects input channels and unknown paths (returns `FALSE`). This is intentionally **not** a raw process-image force: it cannot force inputs, cannot lie to the logic to bypass an interlock, and cannot touch safety I/O (that lives on TwinSAFE/FSoE, §9, unreachable here).
- Consequence to understand and document for operators: because the write goes through the application, a **running module reasserts its own output** — a force is only *effective* when the owning module is stopped or in `MANUAL` (§3.4). That is the intended safety behaviour, not a limitation to engineer around. If a true process-image force (inputs included) is ever genuinely required, that is a **commissioning act with the engineering tool** under separate authority — explicitly outside this runtime surface.

**Diagnostics stay unified.** Master/slave state changes must *also* continue to raise the System alarms of TC3 §10.5 — the topology view and the alarm list are two views of one source (Core §10.5.1). Don't let the scanner become a silent side-channel.

## HMI adapter (Path B or the OPC UA read of Path A)

Implement `fieldbus()` to emit `List<BusNode>`:
- Node `state` ← `E_NodeState` ordinal (already aligned — no mapping table needed).
- Channels ← `ST_IoChannel` fields; digital → `boolValue`, analog → `analogValue`+`unit`; carry `path` (the browse path) so the HMI's cross-view "jump to owning module" works.
- `forceChannel()` ← call the PLC's gated force method; **never** force from the client directly (the PLC owns the gate and the audit).
- Emit on every value refresh; the tree re-renders and node colouring follows subtree-worst automatically.

## Acceptance checklist

- [ ] Unplug a slave → its node goes `FAULT`/`OFFLINE`, its coupler `SAFEOP`, ancestors tint (subtree-worst) — matching a raised System alarm (TC3 §10.5).
- [ ] Digital inputs toggle live; analog inputs show scaled value + unit.
- [ ] A channel's browse path resolves to the owning module in the module tree (cross-view).
- [ ] **Output** force requires MANUAL level (§7.7), writes the mapped output through the PLC, appears as `FORCED`, and lands in the §8.3 ring; below MANUAL the control is a lock; **input** channels expose no force control at all.
- [ ] Web client works via the gateway (Path A) — no raw-TCP dependency.

## Honest boundaries

Nothing here has run against a real master. The AL-state constants and the `Tc2_EtherCAT` FB *names* are reliable; the **ADS ports, index groups, and the force-write index group are the items to verify first**. The process-image-reference pattern for `RefreshValues` is the recommended design but assumes the application wires HAL references — a scanner that instead reads raw process-image addresses is possible but more brittle and is not sketched here.
