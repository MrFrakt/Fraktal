# Selected Unit manual alarm recovery - measured 2026-10-12

**[measured]** Generator 0.13 opts deployed Units into private LOCAL_RETAIN
ACTIVE/WAIT_RESET recovery through alarm_recovery.scopes, a subset of
alarm_history.scopes. The qualification selects StationA and StationA.Satellite;
StationB retains closed history with volatile active events. Only selected Units
allocate recovery images. The press selects PressDemo. Stored images/commissioning
markers are Retain; runtime readiness is NonRetain; native exports prove external
exclusion. Private reads/writes return 200 and published authority writes 205.

**[measured]** The composition prepares a conservative readiness fence before any
root runs. Frames restore before management and recursively block parent Start
while a selected descendant is unready. No application scheduling call is added.
Manual alarm latches survive; commands, step/control state, outputs and sessions
restart inactive. Captured gone faults enter WAIT_RESET without self-closing; a
fresh live explicit owner claims its restored occurrence once without duplicate
come. Explicit occurrences without a fresh owner witness remain ACTIVE. One
ordinary gated reset closes the latch and releases commands. A live cause is
re-raised by its owner; reset never erases the condition.

**[measured]** Whole-image validation covers schema, canonical scope, generation,
header/event checksums, event shape, elapsed checkpoints and authorized-close
journal. Cleared commissioned headers cannot become virgin storage. Invalid
active state rejects whole into one retained HIGH/SYSTEM/MANUAL_RESET loss event,
while preserving closed history and peers. The single prototype reason authority
is Framework/Core/alarm_recovery.json: code 11001, std.error.alarmRestoreLost.
This does not add a released Core enum member.

**[measured]** Duration sums observed controller-running intervals across restart,
excluding the unobserved outage. WAIT_RESET freezes Duration. Elapsed values use
short slot/event-bound checksums; event text is not hashed and lifecycle generation
is not incremented every timer scan. Saved monotonic epochs and unsynchronized
wall-clock subtraction are not used. This profile does not measure outage-inclusive
wall duration.

**[measured]** An authorized-close journal is committed before history append.
At startup, the exact closed record is appended if needed or recognized by
expected cursor/generation/checksum before removing the active latch. Forced
interruptions immediately before and after history commit yield one closed record
and no replayed sink callbacks. These two measured points do not qualify external
durable sink acknowledgement or arbitrary physical torn writes/power loss.

**[measured]** Native fixture lessons: startup injection must run in a routine
that actually receives Startup; its selection must be retained across restart.
Always guard slot bounds before array indexing: a test-only zero-index expression
stopped the CPU. STOP completion requires the fixture FinishCycle pulse. Await
the complete-forest retained StartupCount after RUN; the API mode response alone
does not prove restore finished. Do not hide retained test policy by reseeding:
normalize the access timeout/session between suites. An interrupted config test
changed the retained preset while an admin session was left by the set suite;
restore that test baseline through authenticated WRITE_CONFIG and logout.

**[measured]** 341 new recovery checks and 1510 native assertions across
all successful suites; tools 158, consistency 35, HMI 574 with 8 opt-in skips.
Runtime and wired press compile with zero errors/warnings. The press replays
110 sources, GRAPH AUTO 19/HOME 4 and four optional LAD examples 161 networks/
155 calls. MAIN remains three calls. The press is compiled offline; physical
press acceptance and changed-layout/full-download retention are separate gates.

Current projects: Alarm_Recovery_Runtime_20261012/FrkS12/FrkS12.ap20 and
Alarm_Recovery_Press_Offline_20261012/FrkS12/FrkS12.ap20 under local TiaStations.
Owner Fraktal/CPU1516/TCPIP/RUN, 169.254.212.49 + 192.168.1.1, physical mappings 0.
Keeper PID 12728 remains in Access_Persistence_20261012, without expiry/unregister
cleanup. Preserve it. The whitelisted candidate_structure_examples driver is
unchanged, SHA256 ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74;
pass --driver explicitly. DPAPI credentials remain private.

Evidence: C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_ALARM_RECOVERY_2026-10-12.md.
The separate immutable archive preserves interrupted attempts, successful logs,
source snapshots and SHA256SUMS. Previous dated records remain unchanged.
Next work: durable event delivery/acknowledgement and selected persistence media,
then remaining sequence frontier, config/provider and module scope.
