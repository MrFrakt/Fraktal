# Fieldbus diagnostics adapter — Fraktal/TC3 profile (TC3 §10.6)

*How Fraktal/TC3 combines real EtherCAT health, reviewed engineering identity,
and live HAL values without creating a second I/O authority. Binds Core §10.5.1.*

The base profile is implemented: `FB_EcBusHealth` reads the master, the project
catalog owns electrical/channel semantics, and `FB_IoTopologyPublisher` validates
and publishes the join. `I_FieldbusScanner` remains an optional compatibility
seam for deployments that genuinely need richer vendor-specific discovery; its
fail-closed skeleton is not the default and is not a base-conformance gap.

## Fixed contract

| Layer | Artifact | Where |
|---|---|---|
| PLC types | `ST_FieldbusTopology`, `ST_BusNode`, `ST_IoChannel`, `E_NodeState`, `E_ChannelDir`, `E_ChannelKind` | `Fraktal_Core/DUTs` |
| Runtime health | `FB_EcBusHealth` (`FB_EcGetAllSlaveStates`) | `Fraktal_Core/Connectivity` |
| Catalog/join | project `FB_<Project>IoCatalog` + `FB_IoTopologyPublisher` | application + `Fraktal_Core/Connectivity` |
| Optional extension | `I_FieldbusScanner` + fail-closed `FB_EcFieldbusScanner` skeleton | `Fraktal_Core/{Interfaces,Connectivity}` |
| HMI model/view | `BusNode`, `IoChannel`, `FieldbusTree` | `FraktalCore/HMI/lib` |

`E_NodeState` ordinals (`OFFLINE=0` … `OPERATIONAL=4`, `FAULT=5`) are the PLC/HMI
wire contract. `NodeCount` and each `ChannelCount` define the active bounded
surface; unused array capacity is not discovered or streamed.

## Base profile — one validated composition

```text
EtherCAT master ──Tc2_EtherCAT──▶ FB_EcBusHealth ─┐
XAE/ESI/TMC + electrical list ──▶ project catalog ├─▶ FB_IoTopologyPublisher
Hardware Driver / HAL values ─────────────────────┘              │
                                                         ST_FieldbusTopology
                                                                  │
                                                       ADS / OPC UA / gateway
```

This is the objective-aligned path: it works on every HMI platform, keeps bus
knowledge out of the UI, and preserves the sole project Hardware Driver as the
live-value authority.

1. Reference `Tc2_EtherCAT`; instantiate `FB_EcBusHealth` once per master.
2. Import/generate one project I/O catalog from reviewed XAE/ESI/TMC and
   electrical/I/O-list data. Do not repeat those literals in `MAIN` or CMs.
3. Configure `FB_IoTopologyPublisher`, then map the master's ordered slaves to
   catalog nodes. A count/order/identity mismatch is visible and keeps mapping
   invalid; it is never guessed away.
4. The sole project Hardware Driver copies live values from its HAL/process-image
   symbols into the publisher.
5. Publish the single topology variable with the standalone OPC UA marker. ADS,
   native OPC UA, and Web gateway clients consume the same model.

## EtherCAT runtime health

**Master identity.** `FB_EcBusHealth` accepts an explicit EtherCAT-master
`AmsNetId` and otherwise derives the conventional local master NetId from the
local runtime NetId. Multi-master or remote deployments shall configure it
explicitly.

**Topology and state.** `FB_EcGetAllSlaveStates` performs one asynchronous bulk
read. Its `nSlaves` output validates the catalog count and its zero-based
`ST_EcSlaveState` buffer supplies `deviceState` and `linkState` in master order.
The low state values map to `INIT`/`PREOP`/`SAFEOP`/`OPERATIONAL`; any high
diagnostic flag, including configured vendor/product/revision/serial mismatch,
maps to `FAULT`. An ADS/read failure marks the mapped segment offline. The first
scan is unconditional for control-health validity; later diagnostic refreshes may
be demand-gated while retaining the last published state.

**Channels and scaling.** Channel identity, direction, kind, unit, approved tag,
physical address, and owning module come from the configured PDO/XAE/ESI/TMC plus
the electrical I/O list—not from a generic live read. Live values come from the
same process-image/HAL fields consumed by control logic. Analog scaling comes
from the engineering configuration or the owning CM's `ParCfg`. CoE reads may
enrich an optional vendor-specific adapter, but cannot replace the reviewed
catalog.

**Mapping.** `FB_IoTopologyPublisher` rejects invalid bounds, duplicate paths,
duplicate tags/addresses, missing module ownership, or unresolved diagnostic
tags. Failures set `MappingValid=FALSE` with a diagnostic instead of silently
guessing a relationship.

## Force — output-only, opt-in, and project-resolved

- `Forceable` defaults false. A project enables it only for a reviewed mapped
  output and supplies the resolver in its output-authority layer.
- The PLC checks Core §7.6/§7.7 and logs the §8.3 event. The resolver repeats
  path/direction/capability validation and rejects unknown, input, and safety
  channels.
- The resolver writes the mapped application output—never a raw master/process-
  image force. It cannot lie to input logic or reach TwinSAFE/FSoE.
- A running module may reassert its output. A runtime force is effective only in
  the documented stopped/MANUAL conditions; this is intentional.

The Press reference enables no force capability and supplies no resolver, so the
HMI correctly exposes no force button.

## Optional richer-scanner extension

`I_FieldbusScanner` and `FB_EcFieldbusScanner` are retained for compatibility and
additive extension. A deployment may complete them when it needs vendor-specific
runtime identity or channel enrichment unavailable in the base profile. It shall
still validate against the project catalog, source live values from the Hardware
Driver/HAL, and use the project force resolver. Until qualified, the skeleton's
`Scan=0`, `RefreshValues=FALSE`, and `ForceChannel=FALSE` are deliberate
fail-closed behavior—not a partially enabled feature.

## HMI projection

The HMI reads `ST_FieldbusTopology` through the selected repository:

- node state uses the aligned `E_NodeState` ordinal;
- digital and analog values retain quality, unit, exact `Path`, and `ModulePath`;
- module↔fieldbus navigation uses the qualified module path and exact I/O tag;
- `forceChannel()` always uses the PLC mailbox and never writes a fieldbus or
  process-image address directly.

## Acceptance checklist

- [ ] Unplug a slave: its node becomes `FAULT`/`OFFLINE`, ancestors tint, and the
  same source raises a System alarm.
- [ ] Fit the wrong configured terminal: identity mismatch becomes `FAULT` and
  `MappingValid` is false.
- [ ] Digital inputs toggle; analog inputs retain quality, scaling, and unit.
- [ ] Every channel resolves to the owning module and approved I/O-list tag.
- [ ] If a project opts into output force, MANUAL/access/capability checks and
  audit logging pass; input and safety channels remain unreachable.
- [ ] Native and Web clients render the same published topology.

## Honest boundary

The base adapter and Press composition compile, and the Press fixture has run on
the local runtime. Unplug/mismatch/DC-loss behavior and any explicitly enabled
force resolver remain deployment acceptance evidence for the selected master,
terminals, wiring, and pinned `Tc2_EtherCAT` version. No generic runtime scanner
can infer approved electrical tags, engineering scaling, or Fraktal module
ownership; those facts remain generated/imported project engineering data.
