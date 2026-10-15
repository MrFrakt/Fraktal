# Fraktal/TIA station config and model config - 2026-10-11

Generator 0.8 compiles warning-free and passes 120 native config checks on simulated
S7-1500 CPU1516 V3.0, plus 122 authentication and 96 state/alarm regressions on the
final V6 image. 190 authored blocks/52 interfaces survive native reimport; the
separate production compiler image has 183 blocks/52 interfaces, with no errors
or warnings. The live editor writes and independently verifies the PLC value.
This is a measured config/retention prototype, not complete Core conformance.

Raw/native/generated sources, logs, JUnit, HMI artifacts and source/knowledge
snapshots are in `../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_CONFIG_TRANSACTIONS_2026-10-11/`. SHA256SUMS binds this report
and every archived file using repository-relative paths, excluding itself. Frozen
evidence is append-only; the final checksum audit remains outside the archive.

## Consistent terminology

The owner's instruction is applied to the current Core/HMI contract and HMI
presentation: station config, line config and model config. English headings,
group/card labels and relevant descriptions use those names; Spanish labels use
the corresponding configuration terms. Serialized layout keys and normative
members/ordinals retain their existing identities. Historical evidence is unchanged.
The optional line config owner/mirror runtime is not implemented by this slice.

## Target and implementation

TIA V20, Advanced7/API5 compatibility DLL, owner Fraktal CPU1516 TCPIP on
169.254.212.49 plus configured192.168.1.1, three physical mappings zero. The saved
runtime is `%LOCALAPPDATA%/Fraktal/TiaStations/Config_Runtime_20261011/FrkS12/FrkS12.ap20`.
Config_Verify_20261011 is the separate reimport/production compiler project.
Both copies were hash-checked before mutation. The physical1214C was untouched;
the simulated reference retains full Core capacities and has no150KB limit.

The approved enumeration driver hash remains
`e455ee93e616c4788001b07830164da92b72e3817d6a90c90e03d98937026f33`.
No driver rebuild/whitelist, stage, commit or push occurred. Existing certificates,
TLS pin and DPAPI credentials are reused. Credentials enter only the existing
process wrapper and are cleared afterwards; they are never part of config records.

One per-type declaration generates manifest metadata and the typed handler.
Targets are exact ParCfg/StationCfg members; keys/revisions are bounded, unique
and nonzero. Records begin with a declared nonzero SchemaVersion UINT. Supports
BOOL, INT, DINT, UDINT, TIME and bounded STRING. Widths/capacities derive from Core;
the current Core set-record contract bounds canonical scope/value text at80.
Unsupported float/enum/array targets and wider text are rejected rather than
truncated. Only consuming types allocate staging/defaults; pool capacity derives
from registered fields and offered models (108 rows in this fixture).

Editable ParCfg is an externally read-only owned static. Passing the old input
parameter to a mutating FC produces Siemens access-right warnings; moving the
editable profile to owned storage resolves them. Own-frame services accept only
the components they use; no FB self pointer or project assembly call is required.
Generated restore precedes FRK_Begin/Init. Project logic cannot write config
authority/staging/model identity or invoke the assembly functions.

WRITE_CONFIG checks owner/key/revision, effective DATA_WRITE/minimum level,
readiness, native storage grammar and limits. Direct authority writes refuse205;
private staging/store reads refuse200. Root model config is model-scoped; inactive
edits leave the running config untouched and can proceed while BUSY. Naming the
active catalog index cannot bypass readiness. Child model config follows the active
model; station config refuses model indices. Manifest queries remain read-only.

The provider retains ST_ConfigRecord by (Scope, WriteKey, ModelCode) plus schema.
No aggregate instance DB image is restored. A live write publishes only after
the local-retain update succeeds. Failure preserves live values and is visible in
ConfigPersist. Pending is FALSE for the synchronous retained-value update; the
declared window derives from Core5000ms. Named-set StorePresent remains FALSE.
Retention is measured on this simulator; physical durability is not inferred.

Station config and model config restore separately. A rejected active record
defaults the affected owning record and publishes CONFIG_RESTORE_LOST, while
valid station config survives a model restore failure. A missing record after a
written image is a loss; first-use initialization is silent. ENGINEER-or-higher
acknowledges loss. The default LOW/AUTO occurrence is nonblocking; the declared
BLOCK_UNTIL_ACKNOWLEDGED policy participates in Start release. A separate 23-check
native gate proves withheld Start, its config-loss reason, and release after one
authorized acknowledgment. Complete loss
detection across download/reinitialization remains open.

SET_MODEL and its pure CHANGEOVER release share the current predicate. Every
participant loads/validates into private typed staging, and only after all accept
does an infallible bounded commit publish ParCfg and ModelId. A late child rejection
leaves all live values/identity unchanged, names the offending scope/key and faults
RECIPE_INVALID at its canonical source. Station config is outside that transaction.
Access activity/audit remains in the shared lifecycle. No full frontier release or
sequence/traceability integration claim is added.

## Measured gates

| Gate | Result | Raw records |
|---|---|---|
| Retentive primitive/public/private storage |7/7; STOP/RUN and simulator power-cycle, hidden reads200 |02-04 |
| First config candidate |0 errors/6 warnings; owned-static correction follows |07 |
| V4 config candidate |compile/download0/0;190 authored sources/52 interfaces equal |10-12 |
| V4 native acceptance |103/103 after transport-expectation correction |17 |
| Refined V5 acceptance |120/120, independent restore/readiness/shared model release |19,22-24 |
| Deterministic V6 acceptance |120/120 |31,33,34,36 |
| Authentication regression on V6 |122/122 |37 |
| State/alarm regression on V6 |96/96 |38 |
| Native export/reimport/export |190 authored blocks/52 interfaces equal; compile0/0 |39,40,44 |
| Production compiler-only image |183 blocks/52 interfaces equal; compile0/0 |41,45 |
| Generator/tool suite |135 pass including independent hash-seed replay |35 |
| Full HMI suite |570 pass/1skip, exit0 |26 |
| Final full HMI suite after value-refresh fix |571 pass/8 opt-in skips, exit0 |70-71 |
| Focused mapper/repository refresh checks |32 pass |67 |
| Blocking restore policy |23/23; Start withheld then released after one acknowledgment |69 |
| Live authenticated HMI |PASS;24 modules/556 entries, manual fault/reset, typed config write/inactive isolation |72-73,hmi_verified |
| Focused config/HMI tests |18 pass |21 |
| Source analysis/lint/consistency |analysis clean; lint/consistency0; final35 consistency tests |25,47,48,52,77,79-81 |

The production image omits test DBs/event callback/provider and was not downloaded.
The original retained primitive probe remains an unused test block in the runtime
station; the authored-package comparison covers190 blocks, while the clean reimport
and production images omit it. Native test corruption/availability flags are test-only.

## Preserved failures and corrections

The initial generator trial failed on a Core default: application-record iteration
shadowed the parameter text before constant extraction. Defaults are now derived
before that iteration. Candidate V3 compiles with six access warnings from passing
ParCfg VAR_INPUT to mutating handlers; V4 owns editable ParCfg as a static and
compiles0/0. No warning-suppression policy was used.

13/15 preserve rejection of Unicode TextValue by the current Python JSON/simple
Web API path before mailbox commit (-32602).17 records that transport scope and
verifies the previous acknowledgment/value remain unchanged; it does not claim
PLC validation of a value that never arrived. Integer format/range and80/81-character
string boundary refusals are measured at the typed handler. Raw representation
exists in the [Siemens V20 PlcProgram.Write contract](https://docs.tia.siemens.cloud/r/simatic_s7_1500_et_200mp_manual_collection_itit_20/comprehensive-information/cpu-function-manuals/web-server/api-application-programming-interface/reading-and-writing-process-data/plcprogram.write),
but Unicode/raw write acceptance is not established here.

V5 separates restore by owning record so a model schema failure cannot erase valid
station config, adds shared model release, and preserves the rejected child's
diagnostic source. Replay then exposed unordered Python set iteration in generated
component signatures; V6 sorts that set, and the independent hash-seed test agrees.
The checked-in structural fixture refresh changes only0.7->0.8 headers/manifest,
with byte equality asserted after that substitution (46).

The live HMI trials28/43 preserve an assertion on the wrong tab: config fields
arrived, but the test looked for config cards on Overview. Trial51 reached that
tab with an Operator session; the normal configuration display policy requires
ENGINEER. The corrected test uses the fixture's actual Admin login.

Trial55 sent an accepted write: the independent native read in57 confirms Preset21,
but the editor kept its cached manifest value. Trial60 was stopped after identifying
that defect. The mapper now uses a valid live scalar reading for the field while
preserving the manifest's visibility, permissions, bounds and revision. Hidden
fields stay hidden; absent or invalid live readings retain the manifest value.
The focused32-test gate passes after the corrected Dart pattern syntax;65 preserves
the initial compiler error. The final full suite passes571 tests with8 opt-in skips.

Trial73 passes through the production gateway, repository and widgets. It renders
Model config/Station config, edits Preset21 from the actual input/save button,
observes the displayed value and independently reads PLC1/StationA/ParCfg/Preset21,
then queries MODEL_B and verifies it was not changed. It restores Preset10 and logs
out. Display refresh took6058ms on this process-guarded simulator bench; this is
not a production latency budget. The final live run takes3minutes.78 preserves the initial readsurface rejection
of the dynamic field name; the gate now resolves that exact capability loop to
its published Scope/Item/ValueText authority and still rejects unexplained dynamic
reads (35 tests). The retained
artifacts are [config editor](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_CONFIG_TRANSACTIONS_2026-10-11/hmi_verified/hmi-config.png),
[alarm](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_CONFIG_TRANSACTIONS_2026-10-11/hmi_verified/hmi-alarm.png), manual image
and forest JSON. The config image captures the focused input/keyboard; the naming
assertions are in the live test/log. Disposal-time background query messages after
client closure are preserved; the gate exits0.

## Final state and preservation

76 records owner Fraktal CPU1516 RUN with all physical mappings zero. Both roots
and exercised nested Units are READY/MANUAL, not running, with sessions NONE and
no active/blocking alarms. Request secrets are cleared. Both roots use MODEL_A,
Preset10 and station config bench/enabled; persistence has no pending/failure.
StationA retains the acknowledged historical restore-loss indication.

The gateway is closed; the owner's registration keeper1748 remains alive. It must
not be stopped as routine cleanup. The unchanged driver, certificate pin and
DPAPI files remain in their existing locations.61-63 verify3360 Access and3179
State/alarm SHA bindings plus134 available older files unchanged.12 referenced
older reports and18 older checksum manifests remain absent and were not recreated
or claimed reverified. The new snapshot/checksum audit verifies all captured bytes.

## Remaining work

Named station/model config sets, import/export, file/load-DB/external media,
user/policy/alarm persistence, optional line config replication and broader forms
(float/enum/array/capture/custom classes/collections) remain open. S16 is partial.
Also open: full diagnostic/action/frontier services, shelving/durable sinks,
concurrent writers and complete SCL/generated GRAPH sequences/modules/press without
power. This is not physical S7-1500 or S7-1200 config/retention evidence.
The retained pool is a bounded local provider; duplicate-row corruption/checksums,
schema migration hooks and untrusted document ingestion are not established here.
