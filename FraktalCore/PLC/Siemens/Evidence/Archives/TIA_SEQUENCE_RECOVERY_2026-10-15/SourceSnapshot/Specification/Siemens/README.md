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
| `Examples/PressDemo/` | Wired GRAPH/ST press demo with optional ST/LD sequence/release twins |
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


Latest config continuation: [named sets and JSON exchange](Evidence/TIA_CONFIG_SETS_2026-10-12.md).
The simulator image and the separately compiled press image are identified there.

Latest access continuation: [private users and root policy](Evidence/TIA_ACCESS_PERSISTENCE_2026-10-12.md).
The current simulator and separately compiled press images supersede the config-set images above.

Latest history continuation: [selected Unit closed rings](Evidence/TIA_ALARM_HISTORY_2026-10-12.md).
The runtime and separately compiled press images there supersede the access images above.

Latest alarm continuation: [selected manual-reset recovery](Evidence/TIA_ALARM_RECOVERY_2026-10-12.md).
The images there supersede the closed-history continuation while preserving its evidence.


Latest delivery continuation: [retained queue and SQLite sink](Evidence/TIA_EVENT_DELIVERY_2026-10-12.md).
Its runtime/offline press images supersede the recovery image without rewriting
previous evidence.

Latest persistence mechanism: [S16 load-memory transfers](Evidence/TIA_LOAD_MEMORY_2026-10-13.md).
The diagnostic runtime adds ordinary/UNLINKED storage gates to the unchanged
framework. Consumer media integration follows this instruction qualification.


Latest consumer persistence: [shared LOAD_DB documents](Evidence/TIA_PERSIST_MEDIUM_2026-10-13.md). Generator 0.15 connects configuration, named sets, private users and root policy to the measured instruction medium. Its runtime and separate offline press supersede the earlier current images; immutable older projects and evidence remain available.

Latest sequence continuation: [combined restore and HMI integration](Evidence/TIA_SEQUENCE_INTEGRATION_2026-10-14.md), generator 0.17. Current synthetic simulator image is Sequence_Integration_Runtime_20261014 with LOAD_DB; the separately compiled wired press is Sequence_Integration_Press_Offline_20261014. The [original view qualification](Evidence/TIA_SEQUENCE_VIEW_2026-10-13.md) and earlier document-medium evidence remain preserved.

Latest diagnostic continuation: [scoped first-out, stalls and HELD](Evidence/TIA_SEQUENCE_DIAGNOSTICS_2026-10-14.md),
generator 0.18. Current images are Sequence_Diagnostics_Runtime_20261014 and the
separate Sequence_Diagnostics_Press_Offline_20261014. Earlier reports and projects
remain preserved. Profiling, provider/line config, module/HAL expansion and
deployment acceptance remain open.

Latest profiling continuation: [shared cycle timing and native HMI](Evidence/TIA_CYCLE_PROFILE_2026-10-14.md),
generator0.19. Current images are Cycle_Profile_Runtime_20261014 and the separate
Cycle_Profile_Press_Offline_20261014. Full freeze/resume policy, baseline/reset/OEE
extensions, provider/line config, module/HAL expansion and deployment acceptance
remain open. Sealed evidence remains available for the 33 obsolete local
engineering copies retired with owner approval on October14.

Latest recovery continuation: [shared freeze/recovery and native GRAPH boundaries](Evidence/TIA_SEQUENCE_RECOVERY_2026-10-15.md),
generator0.20. Current images are Sequence_Recovery_Runtime_20261014 and the
separate Sequence_Recovery_Press_Offline_20261015. Selected native recovery,
shared diagnostics/view/profile regressions and offline press readback define
the gate. Provider/line config, baseline/reset/OEE, module/HAL expansion and
deployment/physical acceptance remain open. Earlier evidence is preserved.
