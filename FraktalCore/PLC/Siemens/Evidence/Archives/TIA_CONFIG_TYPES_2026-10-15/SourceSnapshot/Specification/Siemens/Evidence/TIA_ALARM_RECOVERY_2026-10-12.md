# TIA selected Unit manual-reset recovery - 2026-10-12

Generator 0.13 qualifies opt-in ACTIVE/WAIT_RESET alarm recovery on the reference
simulated S7-1500. Manual latches survive restart while commands, step/control state,
outputs and login sessions restart inactive. The wired GRAPH/ST press compiles offline.
This extends the separately qualified closed-history profile without changing its
stored layout. External durable sink delivery and physical abrupt-loss acceptance
remain open.

## Images and framework ownership

Runtime: %LOCALAPPDATA%/Fraktal/TiaStations/Alarm_Recovery_Runtime_20261012/FrkS12/FrkS12.ap20.
Offline press: Alarm_Recovery_Press_Offline_20261012/FrkS12/FrkS12.ap20.
Owner Fraktal/CPU1516/TCPIP stays RUN, 169.254.212.49 + 192.168.1.1, physical mappings 0,
keeper PID 12728. The keeper remains in the earlier Access_Persistence work directory,
with no expiry/unregister cleanup. The owner-whitelisted candidate_structure_examples
is unchanged, SHA256 ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74.
No new whitelist or C# build was needed. Credentials use the existing DPAPI wrapper;
plaintext secrets are not logged or archived. Physical 1214C/press I/O are untouched.

alarm_recovery.scopes is a subset of alarm_history.scopes. Only selected deployed
Units allocate active images: StationA and StationA.Satellite in this 24-module,
six-Unit fixture, with StationB demonstrating the volatile active profile. The press
selects PressDemo. The composition prepares a conservative descendant readiness
fence before any root runs. Generated frames restore before mailbox management;
projects schedule no extra call. Parent Start cannot outrun selected child startup.

Captured faults reconcile against fresh module status; a gone fault becomes WAIT_RESET
and remains blocking. A live explicit owner reclaims its restored occurrence once
without duplicate come callbacks. An explicit manual event lacking a fresh owner
witness stays ACTIVE until Gone or deliberate reset. AUTO_RESET occurrences are
recomputed. One gated reset closes the latch and releases the existing command chain;
a live condition is re-raised by its owner and no output is restored by alarm recovery.

## Integrity, timing and interrupted close

Private SchemaVersion-first images hold keyed manual events, lifecycle checksums,
ownership, observed elapsed checkpoints and an authorized-close journal. A separate
commissioning marker rejects cleared headers. Native readback confirms Retain on
images/markers, NonRetain on runtime readiness, and all external exclusion flags.
Canonical event encoding/checksum primitives are shared with closed history/access.

Complete schema/identity/header/event/timing/journal validation precedes publication.
A bad image is rejected whole into one retained HIGH/SYSTEM MANUAL_RESET loss latch.
Start stays blocked until an explicit, access-gated operator reset. Peers and closed
history remain independent. This binding-owned prototype reason 11001 and its
rationalization/duration policy are declared once in Framework/Core/alarm_recovery.json;
released Core enum/layout remains unchanged. The ordinary readonly alarm surface
publishes std.error.alarmRestoreLost, with English/Spanish catalog entries.

Duration sums observed controller-running intervals across restart, excluding the
unobserved outage. Short timing checksums bind elapsed values to the event/slot;
event text is not rehashed and lifecycle generation does not advance per timer scan.
WAIT_RESET duration is frozen. No saved monotonic epoch or unsynchronized wall-clock
subtraction is used. This does not measure a total outage-inclusive wall duration.

A close journal commits the authorized closed occurrence and expected history
cursor/generation before changing either store. Restart completes a close interrupted
before history commit, or recognizes its already committed record before removing
the active latch. The two qualified interruption points produce one closed record
and no replayed sink callback. Durable sink acknowledgements, arbitrary physical
torn-write/power-loss behavior and changed-layout/full-download boundaries are
separate commissioning/media gates.

## Qualification

| Native suite | Result |
|---|---:|
| Manual alarm recovery | 341 passed |
| Closed history | 174 passed |
| Users and root policy | 419 passed |
| Named config sets | 198 passed |
| Station/model config | 120 passed |
| Access and sessions | 122 passed |
| State and alarm lifecycle | 100 passed |
| Operator decisions | 36 passed |

Successful native assertions: **1510**. Siemens tools 158,
cross-tree consistency 35, HMI 574 with 8 opt-in skips pass. Runtime download/compile,
the offline press initial two compile checkpoints/final update all have 0 errors and
0 warnings. TIA lint and consistency have 0 findings/errors/warnings.

The 341 new checks cover ACTIVE/WAIT_RESET across STOP/RUN/power, actual child fault
first-out, live cause reclaim/re-raise, inactive outputs/commands, one-reset
restartability, observed-duration continuity, frozen waits, descendant startup fencing,
both close interruption points, ten damaged-image forms, whole-image rejection,
persisted loss acknowledgement, peer isolation and private/public write boundaries.

Existing history and state/alarm probes receive the fixture's declared recovery
profile instead of asserting volatile state unconditionally. Config schema/set
capability derive from its generated manifest. Test timeout/scratch normalization
runs between access and state/alarm suites. The first ordinary config run followed
a set test that left an admin session active: its anonymous setup write therefore
changed the retained preset. Those interrupted runs are preserved. Explicit
logout and restoration of that test value through the normal authenticated config
mailbox establish the initial fixture before the successful regression.
The HMI change is localization only;
no new per-station widget/wiring was introduced.

The 110-source press replays exactly, with native GRAPH AUTO 19/HOME 4 and four LAD
examples matching 161 networks/155 calls. GRAPH/ST remains wired at the owning Unit,
optional ST/LAD twins remain uninstantiated, and Main keeps three calls. The press
was not downloaded or physically tested.

## Preserved findings and evidence

The first fixture hook landed in a provisioning routine without a Startup parameter;
the final hook runs before forest startup. A test-only live-condition expression
accessed active slot 0 and stopped the simulator; final bounds checks precede array
access, and the guarded corrected download restored RUN. The first corruption
selector was nonretained and reset before injection; the final test selector is
retained. Initial Stop qualification needed the bench's explicit FinishCycle pulse.
The mandatory CASE fallback was added and recompiled natively. Interrupted raw runs
are preserved, never edited into passing evidence.

[The immutable archive](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_ALARM_RECOVERY_2026-10-12/)
contains native imports/compiles/downloads/exports, fixtures, probes/JUnit, HMI/tool
logs, storage readback, graph parity and source snapshots.
[SHA256SUMS](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_ALARM_RECOVERY_2026-10-12/SHA256SUMS)
binds every archived byte. Earlier archives/relocation payloads are unchanged.
Next work is durable sink acknowledgement/delivery and project-selected media,
then remaining sequence/frontier/config/provider scope. Physical press acceptance
still requires the owner's bench.
