# Siemens evidence payloads

Runtime model milestone (2026-10-17):
[qualification report](../../../../Specification/Siemens/Evidence/TIA_RUNTIME_MODELS_2026-10-17.md),
[sealed payload](Archives/TIA_RUNTIME_MODELS_2026-10-17/packaging.json).
Earlier archives remain immutable.

`Archives/` contains dated raw logs, generated/native sources and snapshots.
These files record past runs; they are excluded from active implementation
generation and shall not be imported as a runtime library.

The [report index](../../../../Specification/Siemens/README.md) remains in the
specification working set. The 2026-10-11 relocation preserved 11,166 original
files byte for byte. `HistoricalReports/` preserves the original dated reports
before current document copies received corrected links.

`relocation.json` records original paths and hashes. Historical SHA256SUMS files
remain unchanged; the verifier resolves each historical path through that map:

```powershell
python FraktalCore/PLC/Siemens/tools/fraktal_tia_evidence.py verify
```

New evidence belongs here with a corresponding Markdown report in
`Specification/Siemens/Evidence/`. Do not put code or payload files back there.

The [2026-10-16 data-class report](../../../../Specification/Siemens/Evidence/TIA_DATA_CLASSES_2026-10-16.md)
records root-scoped policy, atomic set admission and separate class/action
recovery. Its native/runtime/press payloads are sealed independently of the
earlier operations milestone.

The [2026-10-16 operations/GRAPH report](../../../../Specification/Siemens/Evidence/TIA_OPERATIONS_GRAPH_2026-10-16.md)
records generator0.22, isolated native assertions and live configuration/GRAPH
checks. Its archive preserves the actual generated/native bytes, source inputs
and completion/cleanup logs. The saved original Fraktal runtime is unchanged.


The [2026-10-12 config-set report](../../../../Specification/Siemens/Evidence/TIA_CONFIG_SETS_2026-10-12.md)
binds the new native set/retention/regression runs and live generic HMI screenshots.
Its archive is separate from the earlier GRAPH recovery/decision evidence; neither
archive changes the earlier relocation payloads.

The [2026-10-12 access-retention report](../../../../Specification/Siemens/Evidence/TIA_ACCESS_PERSISTENCE_2026-10-12.md)
binds private user/policy image validation, owner-preserving restart probes and
native runtime/press exports in its own immutable archive.

The [2026-10-12 history report](../../../../Specification/Siemens/Evidence/TIA_ALARM_HISTORY_2026-10-12.md)
binds selected Unit closed-ring retention, corruption/restart probes and native
runtime/press readback in a separate immutable archive.

The [2026-10-12 recovery report](../../../../Specification/Siemens/Evidence/TIA_ALARM_RECOVERY_2026-10-12.md)
binds manual-latch/timing/close-journal qualification and native runtime/press
readback in a separate immutable archive.


Latest event-delivery qualification: [report](../../../../Specification/Siemens/Evidence/TIA_EVENT_DELIVERY_2026-10-12.md)
and separate immutable archive TIA_EVENT_DELIVERY_2026-10-12.

Latest sequence integration: [report](../../../../Specification/Siemens/Evidence/TIA_SEQUENCE_INTEGRATION_2026-10-14.md)
and TIA_SEQUENCE_INTEGRATION_2026-10-14. This archive holds source/generated
artifacts, native exports/logs and the live generic-HMI chart evidence; native
engineering project caches remain in their recorded working locations.

Latest sequence diagnostics: [report](../../../../Specification/Siemens/Evidence/TIA_SEQUENCE_DIAGNOSTICS_2026-10-14.md)
and separate TIA_SEQUENCE_DIAGNOSTICS_2026-10-14 archive. Failed attempts and the
VM-restart/test-user repair are preserved alongside native compile/readback and
synthetic first-out/stall/HELD results.

Latest typed configuration/current-export qualification: [report](../../../../Specification/Siemens/Evidence/TIA_CONFIG_TYPES_2026-10-15.md)
and separate TIA_CONFIG_TYPES_2026-10-15 archive. It binds exact numeric witnesses,
typed/current and saved-set regressions, live generic HMI, final privacy/durability
checks and warning-clean runtime/offline press readback. Prior archives remain
unchanged; native projects and the private knowledge backup remain local.
