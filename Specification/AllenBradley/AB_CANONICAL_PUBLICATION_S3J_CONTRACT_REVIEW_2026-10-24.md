# S3j fieldbus topology contract review — 2026-10-24

**Owner-approved for offline implementation on 2026-10-24** (chat reply “all of them approved”): D-1 to D-5 as proposed, and D-6 acceptance vehicle (a) now, with (b) at S3 final. No controller operation is authorized by this approval. This review is offline. It
used no controller access and changed no production source. The approved
[remaining-S3 review](AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md)
names S3j "fieldbus as its own data product" but enumerates no path for it.
The frozen genealogy capture has zero fieldbus paths. The
[source-derived inventory](AB_CANONICAL_PUBLICATION_S3J_INVENTORY_2026-10-24.json)
lists every legacy path, Core member, type and finding below.

## 1. What exists today

The AB fieldbus view is assembled in Python, not published by the PLC.
Identity comes from the station declaration. State comes from the gateway
reading each module's raw input, output and fault words, and the force words.
The canonical architecture needs the PLC to publish it, as TC3 publishes
`GVL_<Project>Fieldbus.Topology`, with a generic reader that knows no station.

The Core target is TC3's `ST_FieldbusTopology` (NodeCount, Nodes, MappingValid,
MappingDiagnostic), `ST_BusNode` and `ST_IoChannel`, bounded by
`PL_Fraktal.MAX_BUS_NODES = 64` and `MAX_NODE_CHANNELS = 16`.

| Fact | Count |
|---|---:|
| Declarations with I/O | 1: the press, one embedded node `Discrete_IO` at `Local:1` |
| Legacy topology paths (press) | 311 |
| Paths whose type changes | 23: `AnalogValue` Int32→Float ×20, `NodeCount`, `ParentIdx`, `ChannelCount` Int32→Int16 |
| Members TC3 serves through the manifest / cyclically | 186 / 125 path rows |
| Lower-bound bytes per channel / per node (excluding channels) | 1,152 / 388 |
| Lower-bound bytes at full Core bounds (64 × 16) | 1,204,480 |

## 2. Blocking findings

1. **No acceptance vehicle exists.** Genealogy, the only v37+ Echo fixture,
   declares no I/O. The press declares I/O but targets the 1769-L24ER at v33,
   which canonical publication refuses. Echo emulates the controller, not I/O
   modules: whether it can supply module data or fault words is unverified,
   and would need a read-only probe.
2. **The press node exceeds the Core bound.** `Discrete_IO` carries 20
   channels: 12 inputs on `Local:1:I.Data`, 8 outputs on `Local:1:O.Data`.
   Core allows 16 per node.
3. **Core bounds do not fit at Core widths.** About 1.2 MB is more than three
   times the 382,216 Blocks free after S3i, before the migration frame copies
   it. That is a lower bound, not a fit estimate.
4. **A topology root is not a module.** It has no top-level `Status`, so
   today's root discovery cannot find it. The generic reader needs a
   PLC-declared data-product binding.

## 3. Proposal

- **D-1 Arrays sized to the declaration.** Publish `Nodes` and `Channels` at
  the declared counts, never above the Core bounds, and state each extent in
  the manifest (D2's lower-bound/element-count rule). This is the same rule
  already applied to the four result rows, two parent slots and sixteen event
  slots: a consumed project bound, not a new D2 exception. Core bounds remain
  the ceiling, and generation refuses a declaration above them.
- **D-2 Split over-bound nodes by process-image word.** Publish a module as a
  parent node (no channels) plus one child node per word (`ParentIdx` = the
  parent), each at most 16 channels. The press becomes `Discrete_IO`,
  `Discrete_IO.I` (12 inputs) and `Discrete_IO.O` (8 outputs). Channel
  `Name`, `Path`, `ModulePath` and `Address` stay exact. Only the node index
  in each channel path changes, as an enumerated correspondence. The
  alternative, raising Core's bound, would change TC3 and is not proposed.
- **D-3 Data-product discovery.** Add a manifest `DataProducts` table naming
  the Symbol, its Core type (`ST_FieldbusTopology`) and its canonical root
  (`<App>Fieldbus/Topology`). This is a V6 minor version step. The generic
  reader discovers the product from that table, never from a name pattern.
- **D-4 PLC-owned identity and state.** Identity is initialized in the PLC
  from the declaration, like nameplates. State comes from the generated
  owner: `State`, `LinkOk`, per-channel `BoolValue`, `Quality` (requires a
  sampled word for that direction plus the fault word), `FaultActive`,
  `Forced` and `Forceable`. These keep the existing §10.5.1 forcing gate and
  mailbox path; `Forceable` stays false without the commissioning gate.
  `MappingValid`/`MappingDiagnostic` come from a PLC-side mapping check.
  `ForcesEnabled`, `ForceBool` and `ForceAnalog` stay private, as in TC3.
- **D-5 Tiers.** Identity is on-demand and `BoolValue`/`AnalogValue` are
  live, per `HMI_CONTRACT.md` §Fieldbus channel state. S4 reads node and
  channel rows per row or group, not as one whole-tree snapshot.
- **D-6 Acceptance vehicle (owner choice).**
  - **(a) Recommended.** A genealogy S3j fixture variant on Echo declares
    one simulated I/O node whose data, output and fault words are controller
    tags driven by the existing fixture. It exercises every state path the
    PLC owner derives (operational, fault, offline, inhibited, partial
    sample, forcing gate) through the observation frame and an independent
    oracle. It is labelled a fixture and never ships as a station posture.
  - **(b) Later, with S3 final.** Retarget the press to the v37+ reference
    profile with real module definitions. On Echo this proves identity and
    the fail-closed offline path only. Live electrical state belongs to S7
    hardware.
  - Choosing (b) alone leaves S3j's live-state paths unproven until S7.

Every implementation step keeps exact value/type comparison, Core widths with
over-width refusal, the measured Capacity gate and separate current approval
for each native session. No tolerance, ignored path or truncation is proposed.

## Owner decision requested

Approve D-1 to D-5 and choose the acceptance vehicle in D-6. The
recommendation is (a) now and (b) at S3 final. Approval authorizes offline
implementation only. Native sessions keep their own exact-image and current
authorization gates.
