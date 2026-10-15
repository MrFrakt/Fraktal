# Declaration-driven frame and registry evidence

Scope: TIA V20, simulated1516 V3.0, Advanced7. Fraktal reference1500 work;
no physical CPU changes or1200 capacity policy. Evidence:
`C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_R4_FRAME_REGISTRY_2026-10-10.md`.

- **[measured]** `fraktal_tia_generate.py` emits24 source files from the one
  shared two-root declaration: three reusable FBs/eight instances, direct
  common contract fields, derived HAL bundles/calls and registry/setup. Core
  type widths/capacities/defaults/publication flags derive from DUTs. Registry
  indices/parents use DInt; row0 reserved;16 fixture slots, no strings in rows.
- **[measured]** Separate root IDBs expose direct Status and yield native names
  StationA/StationA.Cell/StationA.Cell.Clamp/... without a composition prefix.
  FB_FraktalMain owns their unconditional calls; it is not a module/super-root.
- **[measured]** Independent boundary probes pass103 PLC-side assertions:
  setup/identity/parent/type ids, begin/init/child ordering, matching begin/end,
  one-shot init, unconditional cyclic work while CMs take the quiet path, typed
  HAL values, overflow and out-of-range parent rejection without GET_ERR_ID.
  Guarded STOP/RUN rebuilds eight rows and passes again. These FCs are test
  probes, not the command lifecycle implementation.
- **[measured]** Native public reads and private exclusions pass with original
  pin, Api.Version5 and process-data-only rights. Full Unit modes/mailbox/Part,
  rendering/commands, retained classes, generic walks and GRAPH integration
  are not established by this fixture.
- **[measured]** Empty optional IF bodies are invalid SCL: all three initial
  FBs failed "Compound part of instruction expected". Omit empty reaction/
  dispatch blocks rather than adding a fake device statement.
- **[measured]** GenerateSource orders parameter sections and silently drops
  attributes on VAR_IN_OUT HAL aliases. Emit the canonical bare InOut member;
  hide owned HAL storage. Native HAL alias reads return200. Verify actual
  sections/types/flags and native code, not merely a successful import.
- **[measured]** Final package compiles0/0 and all36 blocks/19 interfaces compare
  canonically, including reimport/compile/re-export. No broad ignore rule was
  added for missing attributes. The source was corrected to match the compiler.
- **[measured]** Manifest replay rejects byte edits even if its hash is rewritten.
  Source-scoped containment/HAL/width/generated-region checks now run in lint;
  the broader generator facets retain pending scope.98 tool tests pass.
- **[measured]** Shared native_scalar mapping is used by the generator and S12;
  regenerating S12 yields270 byte-identical files (269 sources plus manifest).
- **[help]** WString length limit16382 and escape syntax are documented in
  [TIA V20 WSTRING](https://docs.tia.siemens.cloud/r/en-us/v20/data-types/character-strings/character-strings/wstring-s7-1200-s7-1500).

Saved image/project: `%LOCALAPPDATA%\Fraktal\TiaStations\R4_Frame_20261010\FrkS12\FrkS12.ap20`.
Original DTL and LDT stations/secrets/certificates remain. Approved enumeration
driver unchanged; no new whitelist. Next: shared Core lifecycle, full Unit
facets and Phase3 native HMI/mailbox, then modules/press without power control.
