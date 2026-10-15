# Program groups and unwired press examples (2026-10-11)

Owner directive: move code out of Specification/Siemens, group FB/FC/DB/type
items by Fraktal folders, keep Main as the root calling routine, add ST/LD
examples but leave wiring and runtime process testing to the owner.

The new hash-approved driver `candidate_structure_examples` imports into nested
block/type groups, deletes both trees in an explicit offline rebuild, exports
types recursively and lists group membership. SHA256:
ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74.
The previous approved binary is retained. Do not rebuild a whitelisted binary
without repeating the owner's per-hash whitelist step.

Openness V20 has a GenerateBlocksFromSource overload for PlcTypeUserGroup and
one for PlcBlockUserGroup; UDTs must use the type overload. No public move API
was found. Copy the saved station and export the old program before grouped
delete/import. Never use this workflow against the running PLC.

Current offline copy: `%LOCALAPPDATA%/Fraktal/TiaStations/Organized_Runtime_20261011/FrkS12/FrkS12.ap20`.
Main calls F_ConfigBenchPrepare, GDB_FraktalMain, F_ConfigBenchObserve in that
order. Helpers extract the original test inputs/setup and observations.
The original Config_Runtime image still runs on Fraktal; no new download.

Examples: AUTO/HOME ST, native LAD and GRAPH, plus ST/LAD release conditions,
generated from press.json. Cylinder actions use typed semantic FCs; sequence
management and lease/Execute-low behavior are shared Core services. No example
DBs, root registration or Main calls. Nominal example scope does not establish
TC3 recovery/traceability/frontier/HMI parity.

Native gotchas: own FB outputs cannot be read reliably in LAD; put authoritative
state in static storage. FC return pins use Section=Return, not Output.
Native export reorders return and InOut pins; compare named typed connections.
GRAPH scalar datatypes are unquoted BOOL/TIME/DINT. Input values belong in Input,
not InOut. Compile/save chart types before importing owner adapters: compiling
an unsaved failed plan's previous baseline proves nothing about failed imports.

Reader gates compare all 115 native LAD networks (93 typed calls) and both
GRAPH charts (17 steps). Replay checks generated sources against their owners.
Source lint includes these examples. Dated evidence is the authoritative run
record at Specification/Siemens/Evidence/TIA_STRUCTURE_EXAMPLES_2026-10-11.md.

Specification/Siemens now contains Markdown only. 11,166 original files were
moved without byte edits to FraktalCore/PLC/Siemens/Evidence. Original reports
are in HistoricalReports; relocation.json resolves unchanged historical SHA
manifests. Use fraktal_tia_evidence.py verify; never regenerate old snapshots.
