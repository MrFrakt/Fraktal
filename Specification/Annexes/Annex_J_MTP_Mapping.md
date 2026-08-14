# Annex J — Interoperability Mapping: Module Type Package (MTP, VDI/VDE/NAMUR 2658 / IEC 63280)

*Companion to **Fraktal Core** (Part I); exercised through the **Fraktal/TC3** binding (Part II).*
*Core concepts projected: self-description (§3.10), command surface & handshake (§3.2, §6.1), modes (§3.4), recipe/config (§3.8), alarms (§8.3), PackML profile (§11.7 / Annex F).*
*Status: **conceptual mapping**, not an implemented exporter. **Fraktal has no dependency on MTP: this annex is an optional, strictly outbound projection** — nothing in Core or the TC3 binding requires it, and no MTP concept (flat topology, HMI-description model) is adopted inward. The 2658 sheets and the MTP 2.0 specification are licensed standards; every element name below (state names, DataAssembly classes, operation-mode fields) **must be verified against the purchased sheets** before an exporter is written. This annex fixes the mapping *shape* and flags the mismatches honestly.*

## J.1 Why this mapping exists

MTP (originated as VDI/VDE/NAMUR 2658 by NAMUR/ZVEI, now stewarded internationally by PROFIBUS & PROFINET International, with MTP 2.0 released 2026 and standardization on the IEC 63280 track) is the industry's answer to the same question Fraktal answers: a **manufacturer-neutral, self-describing module** integrated into an orchestration layer with no bespoke driver. Its vocabulary:

- **PEA** (Process Equipment Assembly) — the self-contained module with its own controller.
- **POL** (Process Orchestration Layer) — the higher-level system that imports module descriptions and orchestrates.
- **MTP file** — an AutomationML (IEC 62714) *interface description* shipped by the module vendor: communication (OPC UA nodes), HMI description, services, alarms. **The logic stays in the module's controller; the MTP describes, never contains, behaviour** — exactly Fraktal's §3.10(a′) stance that the HMI/orchestrator binds data, not code.
- Transport is **OPC UA** (2658 Part 5) — Fraktal's existing spine.

Mapping Fraktal onto MTP serves O1 (one self-description, many consumers), O4/O8 (a Fraktal station becomes consumable by *any* MTP-conformant DCS/POL, not only the Fraktal HMI), and protects the standard from ecosystem isolation.

## J.2 Concept map

| Fraktal | MTP (2658) | Fit |
|---|---|---|
| Root **Unit** (a station) | **PEA** | Strong. A Fraktal root Unit with its OPC UA server is precisely a PEA: autonomous logic, published interface. |
| External line controller / DCS | **POL** | Strong. Today Annex F serves this role via PackML; MTP is the richer, discovery-capable equivalent. |
| Parent Unit orchestrating child EMs/CMs | *(internal)* POL-like role | **Mismatch, by design**: MTP's world is a *flat* set of PEAs under one POL; Fraktal is a recursive forest (§3.1). The mapping exports **root Units as PEAs** and keeps the internal hierarchy invisible to the POL — children are implementation detail, exactly as a PEA's internals are. |
| Command surface + `E_ExecState` handshake (§3.2, §6.1) | **Service** with procedures + the 2658-4 **service state machine** | Good via Annex F: the 2658-4 state machine is PackML-shaped (idle/starting/execute/completing/… plus held/paused branches). Fraktal already projects `ExecState` onto PackML (§11.7); the same projection drives the MTP service states. States Fraktal doesn't natively distinguish (e.g. paused vs held) follow the Annex F mapping rules. |
| Mode-selected sequences (§3.4): one `_M_<Mode>Chain` per mode | Service **procedures** (one service, selectable procedures) | Good. A Unit's runnable modes export as procedures of its main service; `_M_Supports` (§3.7) decides which procedures exist. |
| Recipe/config parameters (§3.8) | **OperationElements / ServParams** (service parameters) | Good. Typed, per-module, write-gated — both sides agree. Fraktal's §7.7 write gating remains PLC-enforced (MTP does not weaken it). |
| Status mirror (§3.10): states, counters, diagnostics | **IndicatorElements** (`AnaView`/`BinView`/`DIntView`/`StringView` DataAssemblies) | Strong. The Status mirror fields enumerate 1:1 onto indicator DataAssemblies. |
| CM actuators/HAL (§3.6) | **ActiveElements** (valve/drive/PID DataAssemblies) | Partial. Fraktal deliberately hides the HAL behind the module; exporting ActiveElements is **optional** and read-only by default (§10.5.1's output-force gating is a Fraktal extension MTP does not model). |
| Alarm log & states (§8.3, ISA-18.2 map) | MTP **alarm management** aspect | Good. Come/gone/reset-class semantics carry over; verify field names against the sheet. |
| HMI tree + facets (§3.13) | 2658-2 **HMI description** (P&ID-style visual instructions) | **Partial, different philosophies**: MTP describes a *picture* (P&ID topology with linked faceplates); Fraktal describes *data* and lets the client render. An exporter can emit a minimal 2658-2 description (one faceplate per module), but Fraktal's tree/facet HMI is richer for discrete machinery and is not replaced. |
| §7.8 release reporting, §7.6.1 manual catalog, §7.7 access levels | *(no MTP equivalent)* | **Fraktal extensions.** Exported, if at all, as vendor-specific OPC UA nodes; they keep working for Fraktal-aware clients alongside MTP consumers. |
| Safety (§9, TwinSAFE/FSoE) | Out of MTP's transfer scope | Agreement: both standards keep safety on the safety system; an MTP never conveys safety functions. |

## J.3 The export path (engineering-time, not runtime)

Because every Fraktal module already self-describes (§3.10: Status mirror, command catalog §7.6.1, config schema §3.8, alarm metadata §8.3), an **MTP exporter is a projection, not new instrumentation**:

1. Walk a root Unit's published structure (the same walk the HMI does).
2. Emit the AML manifest: OPC UA server endpoint + NodeIds for each mapped DataAssembly; one service per Unit with a procedure per supported runnable mode; ServParams from the config schema; the alarm aspect from §8.3 metadata.
3. Ship the `.mtp`/`.aml` file with the machine; the customer's POL imports it and orchestrates the station with zero bespoke integration.

**[TC3] path:** Beckhoff ships MTP engineering/runtime support in TwinCAT (TE8400 / TF8400), which generates the module structure and OPC UA exposure from an MTP model. A TC3 deployment can either (a) hand-write the exporter against this annex, or (b) model the exported subset in TwinCAT MTP and bind it to the Fraktal Status mirror — evaluate both against the pinned TwinCAT version; this annex does not prescribe which.

## J.4 Honest mismatches (read before implementing)

- **Process vs discrete orientation.** MTP grew in process industries (skids, batch); Fraktal is discrete-manufacturing-flavoured (stations, cycles, parts). The service/procedure model fits, but MTP has no native notion of Fraktal's per-cycle traceability (§8.11, Annex E) — that remains on Fraktal's own OPC UA surface.
- **Granularity of orchestration.** MTP orchestrates *services* of whole PEAs; it does not reach inside to command a child CM. That is correct: the Fraktal boundary (§3.2 — parents command children, externals command the root) is preserved, not violated, by MTP.
- **State-machine richness.** 2658-4's service states exceed `E_ExecState`; the PackML projection (Annex F) is the normative bridge, and its mapping decisions (e.g. what reports as HELD) apply unchanged here.
- **No nesting — a projection choice, not a design constraint.** Fraktal keeps its recursive hierarchy unchanged; MTP simply never sees it. Any subtree root *could* serve as the export boundary (the contract is identical at every tier), but **one physical asset shall export as exactly one PEA**: never expose a module *and* one of its ancestors as sibling PEAs, or the POL and the parent become two masters of the same child — violating §3.2. A multi-root forest exports as multiple PEAs; the forest itself is not an MTP concept.
- **Licensed source of truth.** Element names in this annex come from public secondary literature; the purchased 2658 sheets / MTP 2.0 spec override this annex wherever they differ.

## J.5 Conformance checklist for an exporter

- [ ] Each root Unit exports as one PEA with a valid AML manifest importable by a conformant POL.
- [ ] Every Status-mirror field appears as the correct IndicatorElement class with a resolvable NodeId.
- [ ] Each supported runnable mode appears as a procedure; commanding it from the POL drives the real Unit through §6.1 (verify against a POL, not just schema validation).
- [ ] Service states track the PackML projection rules of Annex F.
- [ ] §8.3 alarms surface in the MTP alarm aspect with come/gone consistency.
- [ ] §7.7 gating still holds for every write reachable via MTP (POL writes are clients like any other; the PLC re-checks).
- [ ] Fraktal-specific surfaces (§7.8 release reports, §7.6.1 manual catalog, fieldbus topology §10.5.1) remain available to Fraktal-aware clients and do not leak as unguarded MTP writes.
