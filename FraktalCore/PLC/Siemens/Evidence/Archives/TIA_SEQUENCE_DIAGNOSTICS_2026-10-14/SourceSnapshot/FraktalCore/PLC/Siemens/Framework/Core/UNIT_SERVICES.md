# Unit controls and local part services

Generator0.4 enables these services with a Unit-only declaration:

```json
"unit": {"modes": ["AUTO", "MANUAL", "HOME", "CHANGEOVER"],
         "initial": "MANUAL", "run_command": 1}
```

Mode names and ordinals derive from Core. The initial mode and run command must
be declared. The continuous run uses the common command lifecycle; it ends at
Stop rather than expiring the whole production run. Bounded child commands keep
their ordinary timeout. Mode exit uses the configured ParCfg timeout as its bound.
The full step-chain/stall service remains subsequent work.

The frame publishes ModeActivePublished, RunningPublished, StopPendingPublished,
SupportedModesPublished, HmiRequest/HmiResponse, Access, Part, History and counters.
Generator0.7 also publishes AlarmLog on Units and StateFlags/StateFlagCount only
on module types that declare derived-state producers. HmiRequest is a writable
static: passing a VAR_INPUT mailbox to a modifying FC
produces a TIA access warning. All other facets are read-only; Unit, ModePolicy,
Device and carrier storage are private. Native browse paths match the Core names.

The mailbox copies a new nonzero sequence to private storage and clears the
transported secret. Cyclic management refreshes release conditions before the
request is consumed through FRK_UnitOperation. The acknowledgement follows lifecycle
processing. Same/zero sequences do not execute. Startup consumes the current
boundary without executing it. Clients must serialize transactions and never
replay mutations after uncertain delivery; the mailbox is not a multi-writer lock.

FRK_UnitOperation is also the local PLC operation authority. Start, Stop, SetMode
and OperatorReset check the same Access policy. Default thresholds are NONE,
as Core specifies. Start queries and actions share the complete predicate for
the currently implemented state/mode/access/declared permit checks. Rejections
carry release reasons. Generator0.6 adds the [access/session prototype](../../Tests/Access/README.md):
composition-injected private Core-compatible salted hashes, independent sessions,
correlated asynchronous login results, idle logout and gated policy/timeout edits.
Provider injection is disabled by default. LOGIN acknowledges consumption; the
published result decides success. Failed credentials preserve a valid session.
Public secret fields clear when sampled/consumed; transient hash inputs remain private.
Policy/user persistence and the complete MESSAGE/alarm audit model remain open.

Mode policy belongs to the mode being left. Core defaults apply: AUTO uses
CONFIRM/GRACEFUL; HOME uses INTERRUPTIBLE/IMMEDIATE; CHANGEOVER/CALIBRATION are
blocked while running. CONFIRM is the HMI's prompt responsibility and introduces
no new mailbox argument. Graceful change requests Stop and waits for the cycle
boundary. Immediate change runs ModeExit before cancellation; a positive
HookResult defers it, bounded by timeout. ModeChanged follows commitment.

Reset releases the Unit run request and every generated descendant command
through FRK_ReleaseCommand. ReleasePending propagates through composites, activates
quiet CMs and clears after resolution. The Unit gates a new Start until descendants
are READY. Reset clears a latch; cyclic conditions and permits remain authoritative.
Generator0.7 derives alarm blocking from the Unit log and its registered nested
Units. Reset closes MANUAL_RESET events in ACTIVE or WAIT_RESET before releasing
commands. A still-live condition can raise again; shelving/retention remain open.

Part is published with traceability disabled until the composition explicitly
calls FRK_UnitSetLocalCarrier. The current provider is BY_POSITION only, indexed
within the project registry capacity. It produces local serials, writes results
before publishing the processed event, validates identity and NOK reasons,
increments verdict counters once and publishes the four canonical part events
through AlarmLog AUTO_RESET occurrences. Read/write/identity failures fault with the Core reasons;
Unit error/abort closes a present part with the aborted event. UTC stamps are LDT,
with quality FALSE. Local serial durability/uniqueness across a restart and
RFID/DataMatrix/host adapters are not established by this prototype.

The optional Unit `Release` region supplies one pure HAL predicate through
FRK_UnitSetPermit. The generator writes its function once and refreshes it before
local/mailbox checks and nested manual routing. Lifecycle `Cyclic` work keeps
fault reactions and other management. Function-specific `ManRelease` regions
declare unconditional FRK_ManualCondition calls with unique bounded literal
slots and command values (zero means common). The report appends Unit common
reasons before the selected target and direction's conditions. Other commands
do not inherit unrelated directional conditions.

CM/EM `Catalog` and `CatalogCount` derive from the same command ids/labels as the
timing table. Typed route FCs derive from the containment tree; they accept only
an exact canonical target within the addressed root. Manual execution uses the
existing Execute/Command lifecycle and checks both the addressed Unit and nested
owning Units. Generated parent calls drop completed manual Execute inputs; an
automatic command is untouched. Leaving MANUAL releases outstanding commands.
Accepted/rejected manual attempts enter AlarmLog as AUTO_RESET occurrences.
History remains diagnostic fault history. Access traces add the action, active user and
canonical target; release queries never audit or refresh the session.

Start/Stop/SetMode/reset cascade through declared child Units. Internal cascade
calls are trusted only for access; support/state/release checks still apply.
Unsupported child modes request Stop and report the child's canonical path.
Core names EVENT_CHILD_MODE_UNSUPPORTED but currently assigns no E_Reason value:
the prototype records UNSUPPORTED_COMMAND with std.event.childModeUnsupported.
Incoming cascade pulses survive release of the old command. Reset cancels pending
mode/start work and invokes active nested reset reactions once. Exit timeout also
releases nested runs. Nested mailboxes remain read-only beneath a child-instance
boundary; independent nested control from an HMI needs future root routing.

RELEASE_START, RELEASE_MANUAL and RELEASE_ACTION are side-effect-free queries.
The latter covers START_STOP (Stop), MODE_CHANGE (general admission), ALARM_RESET
MANUAL and ACCESS_POLICY at this prototype scope. Specific SetMode additionally checks the
requested mode; specific manual commands use RELEASE_MANUAL. Unsupported actions
remain withheld. Reset with no current latch/active work is withheld. The complete
alarm/control-domain/frontier/configuration action set remains open.

Shelving, runtime project metadata, durable alarm sinks, recipes/retention,
full sequence frontier/GRAPH conformance remain open.
Tests/UnitRouting exercises 24 instances, two roots and two nested
Unit levels through the native Web API. Its writable stimulus DB is test-only.


Generator0.5 adds the Core3.10.2 static manifest. Typed FCs walk the same declared
containment tree; the shared pager counts all entries and stores only one16-entry
window. Catalogs are private, while ConfigRev and the root response are published.
Restart seeds the opaque revision from CPU-clock milliseconds; this is not a UTC
quality claim. QUERY_CONFIG is pure, model indices other than0 are unavailable,
and DATA_READ serves metadata without values below the root's required level.
Counts, command values/labels/styles and mode policies are manifest-only facets.
Those generator0.5 manifest-only results do not claim editable config.

Tests/Manifest passes241 native checks and120 routing regressions. The native HMI
maps two roots/24 modules, hydrates492 entries and commands the rendered Instant
button. Its memory-only operations display policy is NONE because this prototype
has no login provider; the PLC still checks its own release/access gate. The HMI
excludes ConfigPage/Report from cyclic polling and captures each acknowledged
release reply before another snapshot can replace it. See the dated manifest
and HMI evidence; complete Core conformance remains open.

Generator0.8 adds the [config transaction bench](../../Tests/Config/README.md).
Station config, model config and line config are the consistent category names;
the optional line runtime remains open. Explicit definitions generate both
manifest capabilities and typed handlers. The live local-retain provider stores
keyed values, restores each owner record before Init and publishes ConfigPersist.
Model selection stages every ParCfg in the addressed root, then commits and
publishes ModelId only after all participants accept. CHANGEOVER action/query
share release; inactive root-model edits can proceed while BUSY. Named sets and
broader medium/config forms remain subsequent work.

Generator0.9 adds the Core6.11 root decision service. A private pool is sized by
the declared roots, not registry capacity. Requests are idempotent by full value;
an overlapping request is rejected once without replacing the first. A finite
timeout requires an offered default, while timeout0 waits indefinitely. Operator
answers win expiry in the same scan. DECISION_ANSWER uses START_STOP access and
live Unit permit checks; only the root accepts an answer, and only its raising
module consumes it. Generated management owns withdrawal and readonly publication.
Tests/Decision records native service cases and publication/privacy checks.

The generated Sequences hook runs after children and before End even while idle,
so adapters automatically release/restart their owned chains. The press demo uses
this hook for GRAPH AUTO/HOME and shared ST policy; native parallel contexts and
command leases carry a branch identity. The complete Core3.13 four-table frontier
is still open, separately from these prototype inspection rows and chart services.

Generator0.18 adds scoped awaited diagnostic adoption and main-line Pending at
the owning frame's view boundary. Consumed private snapshots preserve canonical
first-out across composite levels; typed sequence APIs pass target identity.
EMs adopt descendant faults while Units preserve sequence-owned recovery choices.
Generic lease release aborts a busy command without additional Unit glue.
See [diagnostic qualification](../../Tests/SequenceDiagnostics/README.md) for
measured scope and the remaining profiling/freeze-resume policy gates.
