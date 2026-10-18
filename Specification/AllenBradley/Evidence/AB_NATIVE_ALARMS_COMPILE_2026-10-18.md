# Native v38 alarm feasibility and metadata read-back gate

2026-10-18, offline scope. Continues the [native overlap audit](../AB_V38_NATIVE_FEATURE_AUDIT_2026-10-18.md).
No controller download, mode change, clock change or tag write was performed.
The instrumented tower fixture remains loaded on local Echo `601FC87B`.

## Outcome

Native **ALMD in Structured Text compiles on both EchoController and
PhysicalController targets** for 1756-L81E/v38. Both also reject the deliberately
invalid ALMD member, with actual compiler diagnostics rather than an activation
or service failure. All four imports have zero warnings/errors and matching
source/export structure, executable content and authored initial values.
A subsequent native-export/re-import/build/export cycle also passes, including
the native alarm parameter record.

The shared read-back gate now checks native alarm conditions, alarm definitions,
ALMD/ALMA parameter records, localized messages, classes and associated identity
references. Previously, deleting an AlarmConditions subtree could leave every
tag, executable body and ordinary initial value unchanged and still pass.
Regression tests now reject that loss, changed metadata, extra alarms and
duplicate identities. Native default parameters added to an explicitly declared
ALMD/ALMA object are allowed; that exception does not apply to ordinary tags.

**Decision:** retain Fraktal's alarm lifecycle as authority. ALMD is a possible
derived integration mechanism, not a drop-in provider replacement. The separate
tag-based projection trials remain unaccepted because the tested XML forms are
refused by the importer. This is not evidence that v38 lacks tag-based alarms.

## Native comparison and remaining work

| Concern | Finding / decision |
|---|---|
| ACTIVE manual reset | Core §8.3(b) closes the event and releases command latches even from ACTIVE. Native latched reset requires the condition false. Keep the Core owner. |
| Acknowledgement | Native acknowledgement is a separate operation; it does not implement the Core command-release reset. |
| Native object access | The Read Only ALARM_DIGITAL trial is refused at import. Changing only that object to Read/Write permits import. This is not an approved Fraktal command surface. |
| ST Boolean operands | The TRUE/FALSE trial imports but fails compilation with undefined-tag diagnostics. Controlled replacement by 1/0 compiles. Final probes use native numeric Boolean operands. |
| Tag-based projection | Metadata-bearing, minimal, full-input-path, access, child-order and BOOL-owner trials are preserved. All are refused at import. No accepted native projection is claimed. |
| Alarm history / fast events | The Core ring remains authoritative. No async projection loss, queue backpressure or short-event replay has been qualified. |
| Shelving / safety / timestamps | No native runtime comparison, shelf expiry, operator-command isolation, unshelvable policy or synchronized event timestamp claim is made. |

The native reset distinction is documented in
[Rockwell's ALMD reference](https://www.rockwellautomation.com/en-ua/docs/studio-5000-logix-designer/38-02/contents-ditamap/instruction-set/alarm-instructions/digital-alarm---almd.html).
Native tag-based alarm operands and their syntax are documented separately in
[individual attribute access](https://www.rockwellautomation.com/en-il/docs/studio-5000-logix-designer/38-03/contents-ditamap/studio-5000-logix-designer/alarms/tag-based-alarms/access-tag-based-alarms-in-logic/access-individual-alarm-attributes.html).
The initial XML trials were based on the alarm structures in
[1756-RM014, chapter 7](https://literature.rockwellautomation.com/idc/groups/literature/documents/rm/1756-rm014_-en-p.pdf).
The failed importer returns `XMLSrv_E_IMPORT_ABORTED_NO_CHANGES` without a
detailed XML diagnostic through the tested SDK exception properties. No specific
unsupported attribute is inferred. A native-authored alarm export and its
successful read-back are still required before deploying a tag-based projection.

## Reproduction and validation

`fraktal_ab_native_alarm_probe.py` derives two inert fixtures from the guarded
empty L81E/v38 seed. Its 10 ms task disables output updates; stimulus tags are
read-only. The native ALARM_DIGITAL object explicitly retains its required
Read/Write setting. Generation and compilation tools have no online operation.
They do not enable a production feature or modify the current controller.

`fraktal_ab_native_alarm_gate.py` reuses the shared native compiler gate rather
than adding a second SDK runner. The shared gate now applies full executable,
initial-value and alarm-metadata read-back in addition to its existing model.
Existing health-probe schema/profile guards remain the default.

```powershell
python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_native_alarm_probe.py C:/work/echo38_5580_seed.L5X C:/work/alarms_new
python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_native_alarm_gate.py C:/work/alarms_new/generation.json C:/work/alarms_compiled_new
```

- Full AB suite: **1,814 pass**, 259.222 seconds. Final focused suites after
  the last metadata-default refinement: **26 pass**.
- Root suites: **74 pass**; AB spec, frozen-contract and strict consistency
  gates clean.
- Exact staged HMI port snapshot, isolated from concurrent demo/screenshot
  changes: **28 tests pass**, analyzer reports no issues in the nine changed
  files. The first isolated run lacked the PLC symbol catalog dependency;
  including that dependency from the staged tree resolves the one failure.
- SDK 2.1.974 / Studio 38.00: two accepted positive builds, two deliberate
  compiler rejections, all four source/export comparisons equal. One additional
  native canonical build/export passes with its alarm parameter record preserved.
- Mutating Severity in an actual native alarm export is detected by the new
  comparison, while tag inventory and executable code remain unchanged.
- Source regeneration reproduces both final L5X hashes. Input seed unchanged.
- Final exact-target read: Echo Run, MANUAL/idle, no fault and no active command.
  This turn's controller write count is zero.

The immutable [payload manifest](AB_NATIVE_ALARMS_COMPILE_2026-10-18/manifest.json)
binds final sources, accepted/rejected compiler logs, canonical comparison,
metadata mutation, failed XML trials and test logs. PhysicalController is an
offline compiler target; no physical or new alarm-runtime acceptance is claimed.
