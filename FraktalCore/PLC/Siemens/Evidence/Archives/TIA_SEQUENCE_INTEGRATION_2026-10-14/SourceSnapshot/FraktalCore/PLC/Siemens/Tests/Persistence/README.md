# Shared LOAD_DB persistence

Generator 0.15 selects a controller document medium through the application
declaration. Modules, configuration mailboxes and MAIN acquire it through their
existing generated paths; the application adds no scheduling call.

```json
"persistence": {
  "medium": "LOAD_DB",
  "minimum_write_ms": 1000,
  "queue_capacity": 4
}
```

The profile requires a runtime forest with registered configuration. Leaving it
unselected preserves the existing LOCAL_RETAIN implementation and allocates no
load banks, document buffers or medium queue. Other medium names are rejected.
The released Core enum is unchanged: `StoreKind` uses the controller-local
retention category, while readonly `FRK_PersistStatus.Medium` identifies the
actual adapter. This is a draft Siemens binding, not a new Core enum ordinal.

The generator derives one station document and one document per offered model
for each root, one root policy, one document per declared named-set slot, and
one shared confidential user document. Keys, capacities and ownership derive
from the declaration and existing Core types. Each key has two private,
optimized UNLINKED load-memory banks. Private typed images and working buffers
are caches; confirmed load-memory documents govern restoration. Retained
anchors record the confirmed generation and CRC through two selector-committed
banks. Typed caches may seed a virgin medium; this is not a claim of migration
across a full download or changed layout.

The medium checks its header, key, schema, size and CRC before returning bytes.
Consumers then deserialize into private candidates and validate all fields
before applying them. Configuration reserves every cache destination first.
User validation operates on the candidate without installing it. Policies and
named sets reuse their owning validators. A confirmed generation prevents a
damaged newest slot from silently restoring an older value.

Requests use bounded FIFO tickets and one buffer lease per document. Consumer
polling advances at most one medium stage per scan. CRC work is bounded, native
REQ pulses once, and the buffer stays stable through completion. A write becomes
durable only after native read-back validation and anchor commit. Repeated edits
coalesce without replacing an in-flight buffer; unchanged registered config values cause no flash
write. Individual edits and named-set apply use the same dirty hook.

The declared minimum interval applies globally to native writes, including a
fresh delay after startup. The published durability window derives from that
interval, the number of documents and the Core service allowance. Values are
accepted into live configuration before durability; `Pending` and `Failed`
announce that distinction. Failed writes retry. An unreadable boot keeps the
restore barrier, withdraws commands, sessions and derived outputs, and retries
without treating the outage as damaged content.

Rejected documents affect their owning domain. Configuration uses declared
defaults and requires ENGINEER acknowledgement before replacement; policy uses
a restrictive fallback. Users fail closed and require the trusted provider
repair seam. `RestoreLost` remains a historical fact in the existing contract;
`RestoreAcknowledged` makes an acknowledged loss nonblocking.

## Native fixture

`make_fixture.py` extends the existing config/set/access/recovery bench. It
declares 17 documents and a four-ticket queue. Its corruption and availability
controls are test-only, absent from generated application packages. The retained
availability flag permits an outage to survive STOP/RUN; its observer runs
before the restore barrier so the test can restore availability.

`probe_web.py` guards the exact owner Fraktal simulator before every mutation.
It exercises station and active/inactive model config, sets, users, policy,
poisoned caches, STOP/RUN, simulated power, retry, boot quiescence, damaged banks,
damaged anchors, privilege-gated acknowledgement and private symbol boundaries.
DPAPI credentials enter through `../Access/with_credentials.ps1`; no plaintext
credentials enter plans or logs. `probe_boot.py` provides a read-only RUN,
identity, readiness and durability witness.

The runtime project is `Persist_Medium_Runtime_20261013/FrkS12/FrkS12.ap20` under
the local TIA station directory. The separate press project is
`Persist_Medium_Press_Offline_20261013/FrkS12/FrkS12.ap20`; its GRAPH/ST application
is compiled offline. No physical press acceptance is claimed.

See [the dated evidence](../../../../../Specification/Siemens/Evidence/TIA_PERSIST_MEDIUM_2026-10-13.md)
for final counts and raw hashes. Physical flash endurance, arbitrary torn writes,
full-download preservation, card-file/external adapters and S7-1200 fit remain
separate gates.
