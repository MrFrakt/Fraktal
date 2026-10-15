# Shared Siemens command kernel

Selected sequence-view Units also use [shared cycle profiling](../../Tests/CycleProfile/README.md).
Their existing step records feed the main-line waterfall and statistics; cycle
completion is resolved after the command kernel. The frame owns collection,
withdrawal, readonly mirrors and wait classifications. Step and command timing
share the aggregation algorithm. Projects add no profiling scheduling call.

The [wired GRAPH/ST press demo and optional ST/LD examples](../../Examples/PressDemo/README.md) also use shared
[sequence services](sequence_services.scl.in) and
[permissive services](permissive_services.scl.in). Sequence begin/end, state
capture, command ownership, Execute-low release, wait reporting and paused delay
behavior are generated into each rendition from these common services. A project
step names its device action and exit; it does not repeat handshake bookkeeping.
These example services are a prototype seam, not the completed Core sequence
frontier/annotation/HMI implementation.

`command_kernel.scl.in` owns the command lifecycle once. Generate it with
`tools/fraktal_tia_generate.py <declaration> --out <new-directory> --shared-runtime`.
The writer derives state/reason/severity/category ordinals, timing capacity and
reason rationalization from the Core authorities. Manifest replay checks those
inputs and the complete generated kernel; project code cannot replace it by
rewriting a hash. This is the reference S7-1500 runtime prototype.

Optional `storage: "ST_<Type>Private"` emits a hidden Device member for state
owned by the device type. Authored code reads that state and publishes outputs;
reading the FB's own output parameters is rejected before import because TIA
warns that they might not be initialized. No extra storage is emitted if omitted.

Every runtime type declares `commands: [{"id": 1, "label": "Move"}]` and
`timeout: "Timeout"`, naming a TIME member of its ParCfg. The generator accepts
only positive, unique DInt command ids and bounded labels. Unsupported commands
fault with UNSUPPORTED_COMMAND; a nonpositive configured timeout faults with
RECIPE_INVALID. Both remain command terminal states until Execute drops.

The generated frame resets previously published command terminals, accepts an
Execute edge, calls Init once, latches ParCmd and applies command metadata before
CommandStart, runs Cyclic management and child calls, routes abort, dispatches
while BUSY, then resolves HELD/timeout/timing/status. Its final `cyclic` region
publishes derived values and applies device output permits every scan. `Cyclic`
is the management extension before abort; the spelling deliberately distinguishes
it from the older derived-value region. A CM with a management extension runs
the full lifecycle every scan. A CM without it retains the proven quiet guard;
composites remain unconditional. Omitted reactions add no empty IF block.

Device dispatch reads `Core.Command` and `LatchedParCmd`, then calls FRK_Complete,
FRK_Fault, FRK_AdoptFault, FRK_Hold, FRK_HoldDiag or FRK_Pending. It cannot write
lifecycle storage, latched parameters or invoke the assembly FCs. Hooks can use
Core.Step/HookResult for their own work. Outputs remain the device's responsibility:
the permit that causes a hold also withdraws its outputs.

Dropping Execute during BUSY does not cancel the command. A terminal reached
with Execute already low is published for one call, then reset on the next call.
Command faults reset on Execute drop. Background faults raised outside an accepted
command remain latched; a new Execute edge retries validation. Abort is a level
request while BUSY, so an already-high Abort cancels a newly accepted command.
The error-abort reaction is an edge of `Abort AND ERROR` and keeps ERROR latched.

HELD reasserts a LOW diagnostic and stays BUSY. A restored permit clears the hold
without reset. Its progress timeout excludes held intervals and the release
interval; wall-clock command timing includes them. Fault adoption preserves the
originating diagnostic verbatim. Pending-condition timeout preserves path, text,
I/O identity, timestamp and quality, applying the authoritative rationalization.
Timing closes once even for a command completed in its accepting scan; its bounded
rows find an existing id before allocating a free row. Positive TIME overflow
clamps and count saturates. Millisecond differences handle UDInt rollover.

The production clock uses RUNTIME once per composition call and retains fractional
milliseconds. Diagnostics use RD_SYS_T converted to LDT. TimeSynchronized stays
FALSE until a proven clock-quality service exists; a UTC reading alone cannot
assert synchronization.

The optional Unit profile now adds [mode/mailbox/local part services](UNIT_SERVICES.md)
and the [local hash/session prototype](../../Tests/Access/README.md). Generator0.7
owns cyclic session enforcement; a project module cannot write access authority
or add a cyclic assembly call. Provider and policy provisioning belong to the
composition root. The [state/alarm prototype](../../Tests/StateAlarm/README.md)
adds unconditional derived states, nearest-Unit fault capture, AUTO_RESET and
MANUAL_RESET event lifecycles, bounded active/closed rings and an optional event
callback. Access/part/unsupported-mode occurrences now use those event records;
History remains the separate diagnostic fault trace. Persistence, shelving,
runtime project metadata and a durable sink adapter remain open.
This kernel does not complete the Core port. Full Unit/capability
walks and rollup selection, recipe transactions,
retention and full sequence supervision remain subsequent
work. The Lifecycle fixture tests this kernel through generated module frames.

Generator0.8 adds [station config and model config](../../Tests/Config/README.md):
one per-type write definition, typed mailbox handlers, a consumed-size keyed
LOCAL_RETAIN pool, independent station/model restore and atomic local-model
prepare/commit/abort. The editable profile owns ParCfg as a read-only static;
its restore runs before Init. Named sets, other media, user/policy/alarm retention,
optional line config replication and broader config forms remain open.

## Generator0.9 decisions and sequence integration

[Root decisions](../../Tests/Decision/README.md) use one private slot per declared
root and readonly publication. Generated Unit management owns lifecycle withdrawal;
the same mailbox and access handlers accept an offered option. The separate
simulator fixture qualifies decisions without a physical press.

[The press demo](../../Examples/PressDemo/README.md) wires GRAPH AUTO/HOME and ST
permissives in an unconditional sequence hook. Command leases carry branch identity;
shared services own waits, transitions, handled messages and command release. Device
APIs own withdrawal and semantic commands. This is a prototype integration, not a
claim that the complete Core3.13 frontier or all decision/provider forms are done.


Generator 0.10 adds [named station/model config sets](../../Tests/ConfigSets/README.md).
Their bounded store and private transfer cursor are allocated per deployed root;
shared services own storage, JSON and mailbox lifecycle. Typed owner walks reuse
config definitions and parsing, stage every record and commit after all owners
accept. Projects declare capacity and config capabilities and schedule no extra
set handlers. Readonly set tables/documents are requested through the generic HMI.
The compiled press demo opts into a four-slot station config store.

Generator 0.11 adds [retained local users and root policy](../../Tests/AccessPersistence/README.md).
Private versioned LOCAL_RETAIN images are validated whole before use; a separate
commissioning marker distinguishes a virgin user store from a cleared header.
Only actual roots allocate policy images. Accepted mailbox edits commit before
acknowledgement, including idle timeout; live and pending sessions remain volatile.
Provider generation changes revoke old grants and pending credential attempts.
Corruption is reported through alarms and existing ConfigPersist status. A lost
policy uses ADMIN thresholds and blocks Start until explicit acknowledgement;
acknowledgement retains the restrictive policy rather than opening actions.
Other provider/media choices and alarm retention remain open.

Generator 0.12 adds optional [closed-event retention](../../Tests/AlarmPersistence/README.md).
The composition selects actual Unit scopes; no selection allocates no retained
history. Shared services validate a complete keyed image before restore, store
closed events and overflow state, preserve Truncated after rejection and never
replay sink callbacks. Canonical CRC primitives are shared by access/history
consumers. Active-alarm recovery and durable external sink delivery remain open.

Generator0.13 adds [manual-reset recovery](../../Tests/AlarmRecovery/README.md).
Only selected history consumers allocate active images. Framework startup restores
latches before command acceptance, checks descendant readiness independently of
registry construction and reconciles an interrupted authorized close. Event/timing
validation rejects whole images into a blocking, resettable loss occurrence.
Observed running intervals accumulate across restart; unobserved outages do not.
The binding-owned reason/duration facts live in alarm_recovery.json. External
media, durable event-sink delivery and physical abrupt-loss guarantees remain open.


Generator 0.14 adds optional selected-Unit event delivery. Shared
[event services](event_delivery.scl.in) own FIFO capture before callbacks/close
journaling, validation and startup; projects add no scheduling call. Private
retained images/identity anchors and a bounded readonly head view are allocated
only for selected consumers. A dedicated metadata mailbox isolates receipts from
the operator command channel. Receipts remove only the matching head and
require ENGINEER or the configured higher DATA_WRITE level. Corruption is
annunciated through the ordinary alarm log. Prototype kinds, minimum level and
restore-loss reason derive from [one policy](event_delivery.json); released Core
types are unchanged. The SQLite adapter commits before receipt and deduplicates
stable identities. Unattended service credentials and other media remain separate
adapter gates. See [qualification](../../Tests/EventDelivery/README.md).


The optional generator 0.15 persistence profile is owned by [persist_medium.scl.in](persist_medium.scl.in), [persistence.json](persistence.json) and [the document adapter](../../tools/fraktal_tia_persistence.py). Bounded consumer tickets drive private UNLINKED banks; configuration, named-set apply, policy and trusted user commits share owning dirty hooks. Boot restoration quiesces the forest through the same extracted device abort/cyclic hooks before permitting command processing. No application scheduling call is required. See [qualification and boundaries](../../Tests/Persistence/README.md).

Generator 0.16 adds consumed-size `sequence_view` Unit profiles. [Shared services](sequence_view.scl.in) own visited rows, clocks/frontier, bounded notes and manifest revisions. Private per-consumer storage avoids a GRAPH/root-FB compile cycle; frame-owned readonly mirrors expose the Core contract. [Synthetic native qualification](../../Tests/SequenceView/README.md) covers 122 checks. Complete diagnostic walks/profiling and combined LOAD_DB boot/HMI acceptance remain separate.

Generator 0.17 connects the selected LOAD_DB restore barrier to the owning
sequence view. `FRK_ViewWithdraw` clears all active cursors and the current-step
view without clearing same-mode definitions/history/notes. Normal frames and
quiesce publish through one generated mirror map. This prevents an interrupted
asynchronous restore from publishing stale active work; applications add no
scheduling call. Cold startup still clears the volatile chart. The combined
fixture and generic HMI qualification are recorded in [the integration report](../../../../../Specification/Siemens/Evidence/TIA_SEQUENCE_INTEGRATION_2026-10-14.md).

Generator 0.18 adds [shared sequence diagnostics](../../Tests/SequenceDiagnostics/README.md).
`diagnostic_services.scl.in` owns scoped first-out/HELD walks over private snapshots
allocated only beneath selected Units. Owning frames capture/withdraw them and
publish readonly Pending. Sequence command helpers pass target identity instead
of copying state/diagnostic inputs. The frame resolves the longest awaited guard,
names the first false condition, adopts unhandled faults and disarms generic
stalls while HELD. Generic leases now abort busy commands when released. These
services preserve released Core layouts and add no project scheduling call.
Later profiling and recovery qualification is recorded below.

Generator0.20 adds [shared sequence recovery](../../Tests/SequenceRecovery/README.md).
Private lifecycle epochs are allocated only for consumed sequence-view owners.
The existing generated frame captures fault/reset boundaries before sequences
and after the kernel resolves the scan. Helpers retain the failed step, release
issued child commands and rearm command/delay/event state when ERROR ends.
Start follows the project's resume-or-restart policy; the press explicitly
restarts. Native GRAPH preserves the preceding result through transition
evaluation and clears it at the current step action. Boot/mode/abort/restore
boundaries force chart restart. HELD retains its existing automatic permit
recovery. No project recovery scheduling call or released Core layout is added.
