# Annex K — Interoperability Mapping: Asset Administration Shell (AAS, IEC 63278 / IDTA Submodels)

*Companion to **Fraktal Core** (Part I). Sibling of Annex J (MTP): MTP answers "how do I orchestrate this module"; AAS answers "what is this asset, across its whole lifecycle."*
*Core concepts projected: digital nameplate (§3.10.1), self-description (§3.10), model identity (§3.1b), alarms/history (§8.3), traceability (§8.11 / Annex E).*
*Status: **conceptual mapping + a shipped nameplate**. §3.10.1's field set is deliberately IDTA-02006-shaped so this projection is a serialization, not a redesign. Submodel element names below come from the published IDTA templates (admin-shell.io); verify against the exact template version chosen before export.*

## K.1 Why

The AAS (IEC 63278) is Industry 4.0's standardized digital representation of an asset — identity, documentation, technical data, service history — packaged as **submodels** with dictionary-referenced semantics (ECLASS / IEC CDD) and exchanged as **AASX** packages. Fraktal's runtime self-description (§3.10) covers behaviour; the AAS covers **identity and lifecycle**. §3.10.1 (the digital nameplate) is the bridge: it lives in the PLC, renders in the Fraktal HMI, and projects 1:1 onto the standard submodels.

## K.2 Submodel map

| Fraktal | AAS / IDTA submodel | Fit |
|---|---|---|
| `ST_Nameplate` (§3.10.1): ProductUri, ManufacturerName, ProductDesignation, SerialNumber, YearOfConstruction, HW/FW/SW versions, OrderCode | **Digital Nameplate** (IDTA 02006) — `URIOfTheProduct` (mandatory), `ManufacturerName` (multi-language property), `ManufacturerProductDesignation`, `SerialNumber`, `YearOfConstruction`, version fields | **Direct — by construction.** The §3.10.1 field set was chosen to match. Note 02006 models `ManufacturerName` as multi-language; Fraktal's single string exports as one language entry. |
| `DocumentationUrl` (§3.10.1) | **Handover Documentation** (IDTA 02004) | Partial-by-intent: Fraktal stores one link; 02004 models a classified document set (VDI 2770). The link points *at* the handover package rather than replicating its structure in the PLC. |
| Recipe/config schema (§3.8), timing parameters (§8.11) | **Generic Technical Data** (IDTA 02003) | Good. Exported as technical properties; live values stay on OPC UA (§3.10), not in the AAS. |
| Root model identity (§3.1b: ModelCode per root) | AAS **asset kind/type vs instance** distinction | Good. A Fraktal root Unit is an asset *instance*; its model is the *type*. |
| Module tree (§3.1 forest) | **Hierarchical Structures / BOM** (IDTA 02011) | Good. The same tree walk the HMI does emits the BOM hierarchy — a purchased CM (own nameplate, §3.10.1 cardinality rule) appears as a component asset. |
| Alarm/event history (§8.3), cycle stats (§8.11) | Time-series / service-record submodels | Deferred. These are operational data; exporting them into AAS is an historian concern (I_EventSink adapter), not a PLC one. |

## K.3 Export path

Like Annex J, an **engineering-time projection** of data the modules already publish:

1. Walk a root Unit (same walk as the HMI): collect `Nameplate` per module, the tree shape, and the config schema.
2. Emit an **AASX** package: one AAS for the root asset; Digital Nameplate submodel from `ST_Nameplate`; BOM submodel from the tree (child modules with their own nameplates become component assets); Technical Data from §3.8/§8.11 parameters; the Handover Documentation submodel referencing `DocumentationUrl`.
3. Semantic IDs come from the IDTA templates (ECLASS IRDIs) — the exporter carries them; the PLC does not (the PLC stores values, the template supplies semantics).

Open-source tooling (AASX Package Explorer, aas-core SDKs, BaSyx) consumes the result; no Fraktal-aware client is needed on the receiving side.

## K.4 Honest boundaries

- **The PLC ships the nameplate; the exporter is not implemented.** What exists today: `ST_Nameplate` + `SetNameplate` in the library, the §3.10.1 contract, sim data, and the HMI facet card. The AASX serializer is deployment work against the chosen IDTA template versions.
- **Single-language strings.** IDTA multi-language properties export with one language entry; a multilingual deployment extends the exporter, not the DUT.
- **Identity is not configuration.** The nameplate is deliberately read-only from the HMI and outside §3.8/§7.7 — the AAS side agrees (nameplate data is manufacturer-authored, not operator-edited).
- **AAS ≠ transport.** The AASX is a package, not a live channel; live data remains OPC UA (§3.10). Where a live AAS server (e.g. BaSyx) is wanted, it is a client of the same OPC UA surface.

## K.5 Checklist for an exporter

- [ ] Root Unit exports as one AAS instance with a valid Digital Nameplate submodel (02006 mandatory fields present; `URIOfTheProduct` globally unique).
- [ ] Modules with non-empty nameplates appear in the BOM submodel (02011) as component assets with their own nameplates.
- [ ] Technical Data submodel values match the §3.8 config schema; no live process values leak into the AASX.
- [ ] `DocumentationUrl` resolves and is referenced from the Handover Documentation submodel.
- [ ] The AASX validates in AASX Package Explorer against the pinned template versions.
