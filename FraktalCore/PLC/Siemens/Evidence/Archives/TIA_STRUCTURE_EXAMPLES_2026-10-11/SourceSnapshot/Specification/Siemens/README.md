# Fraktal/TIA specification working set

The normative binding is [Part IV](../Fraktal_TIA_Part_IV.md), read with the
[Core](../Fraktal_Core_Part_I.md). The [port plan](SIEMENS_PORT_PLAN.md) records
implementation order and measured scope. [Evidence reports](Evidence/) describe
dated runs; this directory contains documents only.

Code belongs in [the Siemens implementation](../../FraktalCore/PLC/Siemens/):

| Location | Purpose |
|---|---|
| `Framework/Core/` | Shared lifecycle and sequence services |
| `Framework/Modules/` | Reusable device types and their semantic command APIs |
| `Examples/PressDemo/` | Unwired ST, LD and generated GRAPH sequence/release examples |
| `tools/` | Generators, engineering driver, readers and gates |
| `Tests/`, `Spikes/` | Test applications and mechanism probes |
| `Evidence/Archives/` | Immutable raw runs, native exports and source snapshots |

The owner requested relocation of code out of the specification on 2026-10-11.
Payloads moved without byte changes. Original report copies are preserved in
`Evidence/HistoricalReports/`; current report links point to the new locations.
[The relocation map](../../FraktalCore/PLC/Siemens/Evidence/relocation.json) resolves
original repository paths, including paths inside untouched SHA256SUMS files.
Run `python FraktalCore/PLC/Siemens/tools/fraktal_tia_evidence.py verify` from the
repository root to verify relocated bytes and historical checksums.

Keep normative text here, implementation outside it, and dated evidence immutable.
