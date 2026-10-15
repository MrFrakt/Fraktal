# Retained event delivery and SQLite collector

Generator 0.14 adds an optional sink adapter selected in the composition:

```json
"alarm_delivery": {
  "scopes": ["PressDemo"],
  "capacity": 32,
  "stream_id": "6c62c9b6-57d9-41b5-b689-e0540f642b31"
}
```

Scopes must be distinct deployed Units already selected for closed history.
Capacity is bounded by Core `MAX_ALARM_RING`. Use a new canonical UUID for each
controller/deployment; preserve it across restarts. Selected consumers allocate
private LOCAL_RETAIN FIFO images and independently checksummed identity anchors.
The example press selects its actual root. Projects add no cyclic, reset or
delivery scheduling call; the shared alarm lifecycle owns capture and startup.

Come and close snapshots receive monotonically allocated identities. The readonly
`FRK_EventDeliveryView` exposes one immutable head per selected consumer, with its
scope, stream, epoch, token, checksum, backlog, overflow and loss status. Record
fields derive from Core `ST_AlarmEvent`, including Unicode, nanosecond timestamps
and time-quality flags. Text is copied on a lifecycle change, never every scan.
An interrupted close is queued before the existing close journal/history commit.
The two qualified interruptions before/after history append preserve the delivery
record without replaying the ordinary callback at startup.

[The collector](../../tools/tia_event_collector.py) validates a bounded head snapshot
and its canonical Core-field checksum, commits it to a versioned SQLite database
using a full-synchronous rollback journal, then sends a receipt. The token is the
database primary key: a repeated identical record is accepted once; a different
or damaged record with the same identity is refused. A failed commit sends no
receipt. A lost reply starts a fresh head read after reconnection, with no replay
of the old mailbox sequence. This is idempotent storage of accepted queue records;
bounded capacity and the specified commissioning limits still apply.

Receipts use the adapter-owned `FRK_EventDeliveryReceipt` commit mailbox, with
one metadata slot per root that owns a selected consumer. Its arguments and replies
are independent of the operator `HmiRequest`/`HmiResponse`: concurrent collector
traffic cannot commit an operator command. The protocol has no motion vocabulary.
SchemaVersion is 1; Sequence is written last and AckSequence matches it. Requests
are sampled once and never replayed on reconnect. Internal operation identities,
minimum level and loss reason are declared in
[event_delivery.json](../../Framework/Core/event_delivery.json); released Core/HMI
enum ordinals and layouts are unchanged.

| Operation | Receipt fields | Result |
|---|---|---|
| Acknowledge | TargetPath = selected Unit; Token = exact head; Checksum = head CRC; DiscardLost = FALSE | Remove only that head after durable consumer commit |
| Discard rejected storage | TargetPath = selected Unit; Epoch = current epoch; StreamId = deployment UUID; DiscardLost = TRUE | Explicitly abandon a rejected queue and advance a validated identity epoch, preserving loss indication |

Both operations require the configured DATA_WRITE level and at least ENGINEER.
Peer roots, prefix aliases, unknown scopes, stale tokens and wrong checksums
are refused. Corrupt identity anchors cannot be discarded into reused IDs.
The collector never logs in/out of an application session or keeps its idle timer
alive. It currently consumes the existing root session's authority; independent
service authentication and unattended deployment remain adapter work. Its CLI is
limited to the qualified reference simulator and guards identity before writes:

```powershell
python FraktalCore\PLC\Siemens\tools\tia_event_collector.py --database C:\PlantData\press-events.sqlite --confirm-simulator Fraktal --slot 1
```

Provide Web API credentials through the established protected environment mechanism;
keep credentials out of arguments, files and logs. The database directory is an
explicit deployment choice and must already exist. The CLI processes one record.

Whole-image schema, owner, epoch, cursor, bounds, ordering, event shape and checksum
validation precedes publication. Rejected data remains private and produces a
localized LOW/SYSTEM AUTO_RESET message through the ordinary alarm log. Engineering
discard clears the condition; it does not hide the loss. Overflow preserves older
records, drops new ones, and retains `Overflow`/`Dropped` indicators. Sequence
exhaustion refuses further allocation rather than wrapping. No unbounded history,
arbitrary physical torn-write guarantee or full-download retention claim is made.
Receipt audit events remain in the local alarm log/callback; the outbox excludes
its own receipt audit to avoid a delivery feedback loop.

The fixture selects StationA, StationA.Satellite and StationB with eight slots each.
Native gates cover exact records, real SQLite commit/reopen, lost replies before
and after PLC acceptance, access, descendant routing, STOP/RUN, simulated power,
bounded overflow, interrupted closes, damaged images, epoch discard, anchor
rejection, peer isolation and private/readonly boundaries. The press remains
wired GRAPH AUTO/HOME plus ST permissives, with unwired ST/LAD twins and three
calls in Main, compiled offline. See the
[dated evidence](../../../../../Specification/Siemens/Evidence/TIA_EVENT_DELIVERY_2026-10-12.md).

The active-alarm private image advances to schema 2 in this continuation. A
full-table restart regression exposed a timer write interrupted between elapsed
and checksum. Two checkpoint banks now publish a selector only after the inactive
pair is complete. Startup validates the committed bank; deliberately damaged
committed values still reject the image. Schema 1 is rejected as a layout change,
not silently migrated. Changed-layout/full-download retention remains a separate
gate. The diagnosis and twelve full-table STOP/RUN repetitions are preserved.
