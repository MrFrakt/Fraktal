# Native alarm runtime fixture prepared — 2026-10-18

The next N2 comparison image is compiled and backed up for local Echo
`601FC87B`. This record establishes **offline preparation only**. No download,
mode change, controller write, clock change or runtime acceptance occurred in
this preparation run. Deployment requires the separate current authorization
mandated by AGENTS.md §3a.

## Exact artifacts

| Item | Value |
|---|---|
| Target | loopback `127.0.0.1`, slot 0, Emulate 5580, serial `601FC87B`, firmware 38.011 |
| Controller GUID | `91dec7d6-8ac3-45c9-ab2e-0d039c7006fd` |
| Declaration / manifest | `fraktal_ab_tower_demo`, major 5, `EA7BCE24FDA311EB`, config revision 15367118 |
| Unchanged timing fixture SHA-256 | `27C9781FD6FC740B09A13B3F81C7E34C9FF6DAC78A6A027E8100A12ABB923CFF` |
| New alarm fixture L5X SHA-256 | `928E4E81444933E0F70958244F5B0B7B93A5B75F96A2083841B278CDB1A0D2ED` |
| Prepared ACD SHA-256 | `01B95D595C5B54EC4F2963593EDE2E3D457BDADB263B26136D70ADFED1C11360` |
| Current uploaded backup SHA-256 | `1AF4F2E7B9C29E8E2B02819828C744D234A14F29421CD4DDA4A20CBFD3A56D33` |

ACDs remain outside the repository in
`C:/work/fraktal-ab-alarm-runtime-20261018/`. The upload completes successfully
after approximately 160 seconds; its 43 executable bodies equal the current
timing fixture. Its runtime values naturally differ from authored defaults.
The final exact-target preflight sees Run, no fault, MANUAL/idle, no active
command, inactive lamp test, original access policy, logged-out session and
zero simulation stimuli. All five saved station/line/model documents match
the live configuration and reopen from the normal local medium.

## Bounded comparison, not a production provider

The generator starts with the existing timing/tower/Part fixture. One final
JSR and private storage are added; the original routines, initializers,
manifest, mailbox, HAL and periodic task settings are retained. External I/O
is absent and task output updates remain disabled.

The private ALMD and tag-based alarm share one stimulus policy. Native alarm
processing owns their behavior; the fixture does not implement a replacement
alarm engine. Core remains the production event/latch/reset/shelving owner.
The ALARM_DIGITAL object retains its measured required Read/Write access;
other added tags and the observer record are Read Only. None is added to the
gateway command or discovery contract.

Fourteen phases total **104 PLC seconds**, timed from the already sampled
native CST source:

| Phase | Duration | Purpose |
|---|---:|---|
| baseline | 3 s | Capture the native starting state/counts. |
| short pulse | 3 s | One task-scan pulse; compare retained native counts. |
| sustained / gone | 3 s each | Observe ordinary activation and return to normal. |
| latched active / acknowledge live | 3 s each | Observe acknowledgement without releasing the latch. |
| reset live / latched gone / reset gone | 3 s each | Compare reset refusal while active, retained latch and subsequent reset. |
| suppressed / unsuppressed | 3 s each | Observe native programmatic suppression controls. |
| operator shelve | 3 s | Attempt the measured `OperShelve` compiler/documentation discriminator. |
| shelf expiry | 65 s | Observe native one-minute expiry, if shelving took effect. |
| cleanup | 3 s | Clear private input, latch, suppression, shelving and command stimuli. |

The 880-byte record retains per-phase final/seen flags, counts, native status
and seen-status faults, actual elapsed time and completion. Rows freeze when
done, so host polling cannot erase fast observations. A revision brackets
publication; the collector checks exact identity/schema, coherent acquisition,
phase completion, minimum durations and run restart. It only reads.

Short-pulse capture and operator shelving/expiry remain observations, not
assumed successes. A completed fixture cannot by itself grant production
projection or operator isolation acceptance. The 31 existing tower/Part checks
and configuration/session/input restoration are separately required after an
authorized deployment. Clock adjustment/scaling, native subscriber delivery,
external operator security and physical apparatus remain outside this proof.

## Compiler lessons and validation

The first large fixture is rejected with
`RxSTX_E_ALARM_OPERAND_NOTSUPPORTED`. The corrected fixture transfers native
attribute reads and controls through scalar intermediate values before
compound/indexed operations. It passes both v38 targets. Rockwell documents
the restricted
[native alarm attribute expressions](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-00/contents-ditamap/studio-5000-logix-designer/alarms/tag-based-alarms/access-tag-based-alarms-in-logic/access-individual-alarm-attributes.html).

The shared ST formatter now preserves native `.@Alarms` operand tokens.
It remains a layout pass; native compilation validates the syntax. Shared
fixture insertion and coherent sampling replace duplicated observer wiring.
The old timing fixture regenerates byte-for-byte after that refactor.

- **1,828 AB tests pass**, 308.019 seconds; focused observer/formatter suites:
  **29 pass**. **74 root tests pass**; spec, frozen-contract and strict
  consistency gates are clean.
- Studio 38.00 / SDK 2.1.974: EchoController and PhysicalController builds
  pass; prepared ACD reopens/builds. Import summaries are clean.
- Native read-back preserves **44 executable bodies, 20,449 authored initial
  values, 21 SFC steps and two native alarm records**.
- Backup upload, source preservation, configuration reopen and exact-target
  preflight pass. Controller write count in this preparation run: **zero**.

The [payload manifest](AB_NATIVE_ALARM_OBSERVER_PREPARED_2026-10-18/manifest.json)
binds source, generated/read-back artifacts, the rejected compiler run,
successful compiler/backup logs and preflight. Future runtime evidence is a
separate append-only record.
