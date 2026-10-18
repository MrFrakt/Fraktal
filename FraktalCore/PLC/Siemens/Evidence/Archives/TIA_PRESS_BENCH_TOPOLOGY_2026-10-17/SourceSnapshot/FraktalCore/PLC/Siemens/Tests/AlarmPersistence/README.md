# Closed-event history persistence qualification

Generator 0.12 accepts an optional composition declaration:

```json
"alarm_history": {"scopes": ["StationA", "StationA.Satellite", "StationB"]}
```

Only distinct deployed Units with a runtime mode profile are accepted. Omission
allocates no history store. Each selected Unit gets one private LOCAL_RETAIN
image of the Core-sized closed ring; other Units retain the existing volatile
profile. The press opts in its actual root, PressDemo. Select scopes against the
controller's retained-memory budget, independently of its program/data memory.

[Core history services](../../Framework/Core/alarm_history.scl.in) own restore,
validation, append and overflow persistence. The generated Unit frame restores
before access/mailbox events; the owning close path writes an event before its
sink callback. There is no project scan or wiring method to remember. Idle scans
do not rewrite images. Shared CRC primitives derive from Core F_Crc32; the event
encoder derives every field from ST_AlarmEvent, including wide characters,
64-bit timestamps, duration, I/O identity and timestamp-quality flags. Storage
is keyed by canonical Unit identity and excludes pointers and external access.

Restore validates schema, identity, header/cursor bounds, event shape and CRCs
before publishing any row. A separate commissioned marker prevents a cleared
header from becoming a virgin image. Rejected history is discarded whole and
AlarmLog.Truncated stays TRUE across subsequent events/restarts. It represents
incomplete history, as it already does for ring overflow. Rejection does not
invent a live machine fault or block Start. Explicit test-only engineering clear
resets the ring and its retained image; it is not a new HMI mutation surface.

This profile retains closed events only. Active/WAIT_RESET alarms, control
latches, commands, sessions and monotonic clocks remain volatile and faults are
recomputed by their existing owners at startup. Retaining active manual-reset
latches across power loss is separate work. This is not complete durable audit,
historian delivery, file/card media, download/layout-loss or physical retention
qualification. Event callbacks are never replayed during history restore.

make_fixture.py extends the access/config-set/decision bench and selects two roots
and one nested Unit out of six Units. Test-only routines own stimuli and fault
injection. probe_web.py checks STOP/RUN, guarded power cycles, full-record equality,
Unicode including a full ring of 255-character records, real manual-reset duration,
wrap/overflow, isolation, idle generation, privacy, eight corruption forms and
explicit recovery. A retained counter after the full forest scan gates startup
observation. Unicode is constructed by a test-only PLC routine: this Web API
rejected the initial direct non-ASCII fixture write with -32602; raw attempts are
preserved. No production transport workaround is claimed.

Use the existing Tests/Access/with_credentials.ps1 DPAPI wrapper for prepare and
probe; use the owner-whitelisted candidate_structure_examples explicitly for
native plans. Current runtime is Alarm_Persistence_Runtime_20261012/FrkS12/FrkS12.ap20;
the wired press compiles separately in Alarm_Persistence_Press_Offline_20261012.
See [dated evidence](../../../../../Specification/Siemens/Evidence/TIA_ALARM_HISTORY_2026-10-12.md).
