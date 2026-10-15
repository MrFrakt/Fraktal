# Manual-reset alarm recovery

Generator 0.13 accepts alarm_recovery.scopes, a subset of alarm_history.scopes.
Only selected deployed Units allocate a private LOCAL_RETAIN active image. Closed
history keeps its previous layout and schema in a separate image. Recovery is
opt-in; unselected Units keep the volatile active-alarm profile.

[Shared recovery services](../../Framework/Core/alarm_recovery.scl.in) restore
ACTIVE and WAIT_RESET manual-reset occurrences before management accepts commands.
Commands, step pointers, outputs and login sessions remain volatile. Captured
faults are reconciled against fresh module status: a gone fault enters WAIT_RESET
and stays blocking until an operator reset. A live explicit owner reclaims its
restored occurrence once, avoiding duplicate come events. Explicit manual events
with no fresh owner witness remain ACTIVE until Gone or a deliberate reset.
AUTO_RESET occurrences are recomputed rather than retained. Reset never clears
the physical condition; the ordinary owner re-raises a live condition.

The composition path prepares a conservative readiness fence for every selected
Unit before any root runs. A parent checks selected descendants even before their
registry rows/frames finish startup. The existing frame owns all calls; a project
adds no scheduling or reset methods. The press opts in its actual root PressDemo.

Versioned identity/header/event checksums validate each complete active image.
Elapsed checkpoints have a short checksum bound to their event and slot; active
timers update without rehashing event text or advancing the lifecycle generation.
Duration sums observed controller-running intervals across restart, excluding the
unobserved outage. WAIT_RESET durations remain frozen. No saved monotonic epoch is
restored and no unsynchronized wall clock is substituted for duration.

A close journal records the authorized closed occurrence and expected history
cursor/generation before either store changes. Startup completes an interrupted
close or recognizes an already committed closed record, then removes its active
latch. Restored/reconciled entries never replay event-sink callbacks. Durable sink
acknowledgement and arbitrary physical torn-write guarantees remain separate work.

Invalid schema, identity, event/header/timing/journal checks reject the whole active
image. Closed history stays independent. A HIGH/SYSTEM MANUAL_RESET loss occurrence
blocks Start until one gated operator reset; its latch itself survives another
restart. The binding-owned prototype reason and duration policy are declared once
in [alarm_recovery.json](../../Framework/Core/alarm_recovery.json); reason 11001 is
an extension in the Core module-type band, not a new released Core enum member.
The ordinary readonly alarm surface and localized description expose the cause.

make_fixture.py extends the history/config/set/decision bench and selects StationA
and StationA.Satellite; StationB demonstrates the volatile active profile. Tests
cover both states, duration continuity, fresh actual faults, a live re-raising
condition, parent startup readiness, both interrupted-close points, ten damaged
image forms, peer isolation, privacy and reset/restartability. Test-only fault
injection runs before startup restore; the complete-forest retained counter gates
observation. The first test-only live-condition routine used an unchecked zero
index; the final fixture guards bounds before any array access.

Current runtime project is Alarm_Recovery_Runtime_20261012/FrkS12/FrkS12.ap20.
The wired press compiles offline in Alarm_Recovery_Press_Offline_20261012. Use the
existing DPAPI wrapper and explicitly owner-whitelisted driver for native gates.
Physical press acceptance and abrupt-loss commissioning still require the owner's
bench. See [dated evidence](../../../../../Specification/Siemens/Evidence/TIA_ALARM_RECOVERY_2026-10-12.md).
