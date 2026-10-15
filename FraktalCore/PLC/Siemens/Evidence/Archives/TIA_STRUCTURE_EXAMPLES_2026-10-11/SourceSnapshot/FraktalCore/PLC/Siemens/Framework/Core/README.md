# Shared Siemens command kernel

The [unwired press examples](../../Examples/PressDemo/README.md) also use shared
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
