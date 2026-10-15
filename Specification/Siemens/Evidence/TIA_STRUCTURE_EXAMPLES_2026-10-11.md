# TIA program structure and unwired press examples - 2026-10-11

The owner requested implementation code outside the Siemens specification,
matching Fraktal program/type groups, a short root calling routine, and ST/LD
sequence and permissive examples. The owner will wire and runtime-test the
examples. This record measures relocation, native engineering and readback;
it does not establish the press runtime or full Core conformance.

## Results

| Gate | Recorded result |
|---|---|
| Historical relocation | 11,166 files preserved byte-for-byte; Specification/Siemens contains Markdown only |
| Historical SHA manifests | Access 3,360; config 4,487; state/alarm 3,179 bindings verify through the relocation map |
| Native grouped station | 244 blocks/types across ten Fraktal group paths; final compile 0 errors / 0 warnings |
| Baseline preservation | 190 sources unchanged; Main is the only changed baseline source; retained test DB preserved |
| Main extraction | Prepare -> GDB_FraktalMain -> Observe; original body reconstructed canonically |
| Example source replay | 68 derived sources replay exactly from their authorities |
| Native Ladder readback | 115 networks, 93 typed calls; operands, pins, returns, contacts, coils, order and wires agree |
| Native GRAPH readback | AUTO 13 steps; HOME 4 steps; actions, edges, conditions and settings agree |
| Native publication flags | Private device/intermediate storage, ten scalar GRAPH parameters and read-only inspection state retain their flags; attributes on 25 structured/FB InOut parameters are stripped and their runtime exclusion is unproven |
| Software gates | 140 Siemens tool tests, 35 consistency tests, zero lint/consistency findings; diff whitespace check clean |
| Preserved runtime | Fraktal CPU1516 RUN, zero physical mappings; four Units READY/MANUAL, no active alarms, config defaults intact; keeper PID1748 alive |

## Engineering state

The offline copy is
`%LOCALAPPDATA%\Fraktal\TiaStations\Organized_Runtime_20261011\FrkS12\FrkS12.ap20`.
It was copied and hash-checked from the owner's saved config station before
program changes. The baseline was natively exported before rebuilding groups.
The current running config image was not downloaded or replaced.

TIA program blocks and PLC data types use these matching paths:

- `Framework/Core`
- `Framework/Modules/ControlModules/Cylinder`
- `Tests/ConfigBench/00_System`, `DUTs`, `Fixtures`, `Modules`
- `Examples/PressDemo/01_PneumaticPress`, `DUTs`, `Release`, `Sequences`

Main delegates test setup/input preparation and observations to separate FCs,
with the existing forest scan between them. The fixture generator now emits
this form. Reconstructing the two native FC bodies around that forest call
matches the original Main body, including the Startup parameter substitution.

The grouped driver imports UDTs into type groups and code into block groups,
exports types recursively and records membership. Openness V20 has no public
move operation in the inspected API; this run uses an offline copy and an
export before deletion/import. Owner whitelisting was completed for SHA256
`ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74`.
Its build had zero errors/warnings. The previous approved driver was retained.

## Example scope and encapsulation

[The example guide](../../../FraktalCore/PLC/Siemens/Examples/PressDemo/README.md)
documents integration. One process declaration generates nominal AUTO/HOME in
ST, native LAD and GRAPH and generates ST/LAD release conditions. The cylinder's
catalog, HAL logic and semantic FC API belong to the reusable module. Sequence
authors call Extend/Retract operations on typed parameter instances; common
services own command grants, step-scoped issue storage, waits, timing and
Execute-low release. The device applies live permits after completion as well
as BUSY. Intermediate storage is externally excluded and inspection state is
read-only. TIA strips external attribute flags on structured/FB InOut parameters;
the post-wiring browse surface must still be verified. No alias-publication
runtime result is claimed by this offline gate.

There are no example instance DBs, new root registrations or calls from Main.
The station's existing Core and 24-module registry were retained when merging
the new types. The standalone generated package has its own four-module Core
fixture and must not overwrite an existing station's registry during integration.

Runtime recovery/scrap branches, traceability, complete sequence diagnostics and
frontier/annotations, and HMI flow-chart integration remain open. Compile and
native readback do not replace the owner's process wiring and runtime tests.

## Preserved artifacts

[Raw payload and final source/native exports](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_STRUCTURE_EXAMPLES_2026-10-11/)
contain the approved driver build log, import/compiler logs, baseline export,
final grouped source inventory, graph parity, Main preservation check, final
runtime witness and source/knowledge snapshots. `SHA256SUMS` binds their bytes.

The original evidence directories were moved to implementation `Evidence/Archives`.
Original report copies remain in `Evidence/HistoricalReports`. Active document
links were updated; old source snapshots and SHA files were not rewritten.
[relocation.json](../../../FraktalCore/PLC/Siemens/Evidence/relocation.json)
resolves their historical repository paths. Twelve older reports and eighteen
older manifests were already absent; this run does not reconstruct them.

Verification from the repository root:

```powershell
python FraktalCore/PLC/Siemens/tools/fraktal_tia_evidence.py verify
python FraktalCore/PLC/Siemens/tools/fraktal_tia_examples.py --verify FraktalCore/PLC/Siemens/Examples/PressDemo/generated
python FraktalCore/PLC/Siemens/tools/tia_lint.py
python -m unittest discover -s FraktalCore/PLC/Siemens/tools -t FraktalCore/PLC/Siemens/tools
python tools/check_consistency.py
```
