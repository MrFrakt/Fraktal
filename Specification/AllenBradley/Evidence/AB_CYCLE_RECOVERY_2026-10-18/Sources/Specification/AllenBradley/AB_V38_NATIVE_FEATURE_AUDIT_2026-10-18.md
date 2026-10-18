# Allen-Bradley v38: native-feature overlap audit

Non-normative source/documentation audit, 2026-10-18. Requested by the owner
before further port growth. This applies the same review as
[TIA remaining features, section 7](../Siemens/Reports/TIA_REMAINING_FEATURES_PLAN_2026-10-15.md).
It records replacement candidates, not newly accepted controller behavior.

## Target and decision boundary

Continuation: [native compiler/read-back evidence](Evidence/AB_V38_NATIVE_HEALTH_COMPILE_2026-10-18.md)
now qualifies N1/N4's L81E/v38 type and attribute spellings at offline scope.
The three positive groups pass both compiler targets; runtime and external I/O
qualification remain open. ForceStatus requires an empty instance, and the
accepted task attribute is MaxInterval. Production providers are unchanged.

The current Echo declaration is **1756-L81E, firmware 38.011**
(`fraktal_ab_press_echo38.application()`), with no physical I/O modules. The
accepted physical reference remains the separately qualified **1769-L24ER-QB1B,
v33**. The S12 **5069-L310ER/v38** type exploration is another target, not proof
for either controller. Studio application version, controller family, firmware,
Echo support, installed options and instruction language are separate facts.

Sources inspected: `fraktal_ab_generate.py`, `fraktal_ab_projection.py`,
`fraktal_ab_access.py`, `fraktal_ab_shelving.py`, `fraktal_ab_s12_type_probe.py`,
the press and Echo declarations, direct-CIP client, Part I/III and the dated
AB evidence they cite. Rockwell documentation was checked against the sources
on this date. A documentation match alone does not pass native acceptance.

**Decision:** reuse native acquisition/execution where its semantics match;
retain only the portable policy and projection the Core needs. Do not replace
a contract by a similarly named vendor feature, and do not assume v33's
restrictions apply to v38. No PLC program is changed by this audit.

## Existing native mechanisms to retain

| Current owner | Native mechanism already used | Assessment |
|---|---|---|
| Generator AOIs and scan services | AOI instances, UDT contexts, JSR program services | Composition implements the common lifecycle once. Native AOIs do not supply Fraktal's command semantics by themselves. Keep. |
| `chain_sfc_routine`, `sfc_runner_logic` | Native SFC graph and JSR/SFR restart | Already native execution; do not add another SFC scheduler. ST and LD are alternative declared renditions. The current press selects LD only. |
| Mailbox/frame sampling | CPS before validation, then Sequence commit | Native copy is already reused. Keep Fraktal's validation, ownership, permission and acknowledgement transaction. CPS alone is not the external transaction protocol. |
| `health_probe_logic`, `wall_clock_logic` | GSV TASK, FaultLog, TimeSynchronize and WallClockTime | Acquisition already native. Keep the shared publishers and unavailable-data semantics. Review only the redundant/unsafe derived timing below. |
| Gateway identity guard | CIP device identity and expected serial checks | Reuse this for future controller identity display; do not create a parallel station/controller identity authority. |

## Native overlap requiring a decision before new runtime code

| Priority / area | What exists in Fraktal | Native counterpart and applicability | Decision and acceptance |
|---|---|---|---|
| N1 / first: module health | `read_io` reads declared words; `topology` infers node state from availability and channel fault bits. MODULE connection-state work remains provisional. | GSV MODULE `EntryStatus`, `FaultCode`, `FaultInfo`, `Mode`, `ForceStatus`, and `Path`; configured named module required. `EntryStatus`/`FaultCode` are INT, and the state comparison masks the lower 12 bits. [MODULE documentation](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-01/contents-ditamap/instruction-set/input-output-instructions/access-the-module-object.html). | **Use native state as authority in the future module-profile adapter.** Do not build a connection watchdog from channel bits. Preserve unknown raw codes and separate sample validity from module state. Echo's no-I/O declaration cannot qualify a physical module. Measure disconnect, inhibit, configuring, fault and recovery on the named hardware; version any published additions. |
| N2 / first: alarms | `alarm_log_logic` owns active/WAIT_RESET events, first-out, reset classes, bounded history; `fraktal_ab_shelving` owns shelf policy. | v38 supports tag-based alarms on 5380/5580/5590 families, including the Echo declaration's family; no such inference applies to the v33 5370. [Tag-based alarms](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-00/contents-ditamap/studio-5000-logix-designer/alarms/tag-based-alarms.html). ALMD also offers latching, acknowledgement, suppression and shelving. | **Real overlap: do not grow another alarm engine without a provider comparison.** First prove a native projection from authoritative Fraktal events; evaluate a native state provider separately. Keep first-out/source links, rationalization, history/overflow and command release. Compare all reset classes, timing, async evaluation, shelf persistence, no-shelve rules and reset of an ACTIVE condition before replacing owned state. |
| N3 / next: SFC timing and visits | Shared chart records compute elapsed/last duration and visits for all languages. | Native `SFC_STEP.T`, `PRE`, `DN`, `TMax`, `Count`, `AlarmHigh/Low`, entry/exit bits. [v38 Step](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-00/contents-ditamap/instruction-set/sfc-instructions/step.html). | **Use the native backing tags as candidate SFC timing inputs, not a second timer per SFC step.** Native T measures active wall duration; it does not by itself express Fraktal's held-time accounting or retained chart annotations. Preserve fast-step history and ST/LD parity. Current Echo AUTO is LD, so this yields no current deployed saving. |
| N4 / first: task interval and clock | `health_probe_logic` subtracts seconds/microseconds within a minute from WallClockTime and repairs negative differences with 60 seconds; command/step timers use declared scan increments. | Native TASK `MaxInterval`, `MinInterval`, `StartTime`, `LastScanTime`, `MaxScanTime`, `OverlapCount`; CST/time/date access also exists. [TASK documentation](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-00/contents-ditamap/instruction-set/input-output-instructions/access-the-task-object.html), [time/date GSV](https://www.rockwellautomation.com/en-gb/docs/studio-5000-logix-designer/38-03/contents-ditamap/instruction-set/time-and-date-data-types/gsv-ssv-support-time-date-data-types.html). | **Replace avoidable reconstruction after a target probe.** A wall-clock adjustment is not a task-period change; the current minute repair can disguise one. Native interval extrema do not automatically equal the current one-second window, and TASK StartTime is explicitly wall-clock based. Prove the selected elapsed-time source under adjustment, wrap, missed scans and Echo time scaling; retain only the required window aggregation. Do not rename native `MaxInterval` to the similarly named `MaximumInterval` in another help table without compiling the exact attribute. |
| N5 / next: timer storage and native duration | Private/public durations are broadly represented as DINT milliseconds under the accepted v33 type map. | v38 adds `TIMER_T` with TIME-valued ACC/PRE. TON supports it on 5380/5580/5590, but **TON is ladder-only**, not an ST call. [v38 features](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-00/releasenotesmainenu-ditamap/system/system-features.html), [TON operands/languages](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-01/contents-ditamap/instruction-set/timer-and-counter-instructions/timer-on-delay--ton-.html). | **Candidate private v38 timer provider, not a global ABI rewrite.** Existing S12 v38 TIME/LREAL results remain exploratory. Compare native timer memory/scan cost and pause/reset semantics with the compact shared-clock path. Do not place a TON in an ST AOI or add a native timer to every quiescent module merely because the type exists. |
| N6 / next: HMI transport | Supported Python CIP gateway plus limited Dart direct-CIP spike; the spike duplicates a subset of projection bindings and hardcodes press module type keys. | Eligible physical 5380/5580 controllers have embedded OPC UA. The OPC UA manual lists L81E with no nodes; Echo explicitly does not support OPC UA. [OPC UA controller manual](https://literature.rockwellautomation.com/idc/groups/literature/documents/um/1756-um023_-en-p.pdf), [Echo limitations](https://literature.rockwellautomation.com/idc/groups/literature/documents/gr/9310-gr001_-en-p.pdf). | **Evaluate the existing generic OPC UA client on an eligible physical target before expanding a second custom CIP projection.** Current Echo still needs CIP. Check exact catalog/firmware, node budget, native type/access behavior, writable mailbox and consumed read surface. An OPC UA tag server alone does not supply the validated Fraktal manifest, canonical hierarchy or release gates. Browser hosting remains a separate Web adapter. |
| N7 / integration: accounts and transport security | PLC salted-PIN provider, root-specific session/action policy, protected mailbox and gateway bearer policy. | FactoryTalk Security controls engineering/product/controller access. [Security application technique](https://literature.rockwellautomation.com/idc/groups/literature/documents/at/secure-at002_-en-p.pdf). | **Evaluate a real identity-provider adapter before adding more custom authentication.** Engineering login, CIP/OPC UA transport identity and an operator authorized for a particular root are different authorities. No reviewed source establishes a drop-in FactoryTalk API for the current generic HMI's LOGIN/PIN contract. Do not remove PLC action checks, change hashing policy or add a second account list as a substitute for that integration. |
| N8 / persistence | File-medium provider, JSON-line sets and staged PLC-validated live-document restore. | Native SD-card image/data storage and MSG-based file/recipe examples exist. [Rockwell nonvolatile-memory application guide](https://literature.rockwellautomation.com/idc/groups/literature/documents/ap/logix-ap007_-en-p.pdf). | **Medium replacement candidate behind the existing store seam.** The cited older family example is not acceptance on L81E/v38. A stored image is not a transactional per-model document store. Prove typed all-or-nothing restore, full banks, download/power-cycle behavior and latest-copy selection before replacing the gateway store. Keep generic JSON interchange and provider validation. |
| N9 / project-specific options | Custom Unit/mode/command state and HAL modules. | PhaseManager equipment phases and optional PlantPAx process instructions. [PhaseManager](https://www.rockwellautomation.com/en-us/docs/factorytalk-batch/17-00/factorytalk-batch-online-help-ditamap/-phm-.html), [PlantPAx requirements](https://compatibility.rockwellautomation.com/GeneratedReleaseNote.aspx?o=&pdf=0&v1=63590&v2=63590). | **Review when the project actually uses those products.** Do not assume an ordinary L81E is a process controller because Studio is v38, or make FactoryTalk Batch a new mandatory dependency. Any adapter still maps Fraktal recursive ownership, command/reset/HELD behavior, generic diagnostics and data contracts. |

N2 has a concrete semantic mismatch to test: native ALMD's latched reset is
ignored while its condition is true, whereas Core operator reset also closes
an ACTIVE MANUAL_RESET event and releases command latches without clearing the
underlying condition. Native acknowledgement is not equivalent to that reset.
Native alarm message strings also are not programmatically readable from an
ALMD tag, so generic localization cannot be assumed to come from that tag.
[ALMD configuration](https://www.rockwellautomation.com/en-gb/docs/studio-5000-logix-designer/38-00/contents-ditamap/studio-5000-logix-designer/alarms/instruction-based-alarms/analog-and-digital-alarm-properties-dialog-boxes/almd-properties-dialog-box---configuration-tab.html).
Tag-based attributes do support programmatic access; provider feasibility is
therefore worth measuring instead of being dismissed as inaccessible.
[Programmatic alarm access](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-00/contents-ditamap/studio-5000-logix-designer/alarms/tag-based-alarms/access-tag-based-alarms-in-logic.html).

## Additional duplication found in this checkout

- **Closed in source:** the v33 press and Echo declarations duplicated the application. A field-by-field
  dataclass comparison finds only seven differences: `controller`,
  `major_revision`, `comment`, `io_modules`, `access_users`,
  `controller_identity`, `simulation_mailbox_rw`. Echo now derives those seven
  deployment differences from the shared declaration. Both generated baseline
  projects remain byte-identical; simulation access stays isolated.
- Direct CIP contains its own partial flat projection and copied type keys;
  it is not the full gateway contract. Do not grow a second station-specific
  bind table. Select native OPC UA where supported, or derive transport bindings
  from the same manifest/declaration schema as the gateway.
- **Closed in source:** the Echo declaration's introductory comments described inhibited cabinet
  I/O and several deferred features that its final declaration no longer
  matches. The short derived variant now describes its actual `io_modules=()`
  target. Historical evidence is not rewritten to reconcile later changes.

Independent gap closure also adds optional manifest nameplates and a bounded
non-part host stream. Native reuse decision: the manifest remains the one asset
identity authority; native AOIs/UDTs provide storage/execution and CIP/GSV supply
acquisition/time. Only the portable Core event vocabulary, publication coherence
and sink acknowledgement/loss policy are added. No alarm engine, SFC scheduler,
native MODULE watchdog or second HMI bind table is introduced. Native alarm
provider feasibility and N1/N4 runtime qualification remain open. See
[compiler/read-back evidence](Evidence/AB_HOST_NAMEPLATE_2026-10-18.md).

## Required review for the next AB feature

The optional local BY_POSITION carrier now reuses native UDTs and one shared
AOI called by ST/SFC/LD, with required complex parameters passed by reference
as documented in the [v38 AOI parameter reference](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-00/contents-ditamap/studio-5000-logix-designer/add-on-instructions/edit-an-add-on-instruction/add-on-instruction-definition-editor---parameters.html).
The existing GSV clock/quality source is reused. Local serial identity, bounded
Core result records, write-before-event ordering, verdict ownership and
publication coherence remain Fraktal policy. This is an adapter over native
execution/storage, not a claim that Logix supplies the portable Core carrier
contract. Vendor RFID/MES transports are not reimplemented or claimed.
The measured S12 DINT mapping remains explicit: UID bytes and scaled measurement
integers; native STRING/LREAL support is not inferred for other catalogs.
No new alarm engine or sequencing runtime is introduced. See the
[local-carrier compiler/model evidence](Evidence/AB_LOCAL_CARRIER_2026-10-18.md).

Before adding an AB runtime service, record its Core obligation, current owner,
native instruction/service, exact target and language support, semantic gap,
and whether to reuse, adapt/project, or retain the current owner. Measure only
the selected implementation: generated size, Studio import/Verify/read-back,
runtime reset/HELD/history behavior and recovery, then generic HMI acceptance.
Published additions remain versioned; native private types need no gratuitous
public ABI change. Do not keep two authoritative state machines after migration.

Next native work is **N1/N4 runtime qualification** after the recorded clean
v38 compiler probes, followed by **N2 alarm-provider feasibility**. The optional
local carrier and host ring have separate offline scope and do not close those gates. OPC UA
qualification needs an eligible physical catalog; native external-module health
needs real configured hardware. Echo outcomes never stand in for those gates.

The TIA endpoint/quality follow-up already implemented is recorded separately in
[AB TIA follow-up](AB_TIA_FOLLOWUP_2026-10-18.md). This audit changes the work
order; native replacement deployment remains unclaimed. The dated native
compile evidence records exactly which provider/attribute probes compiled.
