# Local HostEvents collector recovery — 2026-10-18

The existing PLC event ring and acknowledged cursor now recover from a local
collector process crash on Windows. An optional SQLite sink commits each event
or loss notice before acknowledgement and accepts identical replay without
adding another row. This closes local collector recovery, not the AB port or
native alarm subscriber integration.

All **1,839 AB tests**, **45 focused host-delivery tests** and **74 root gate
tests** pass. Specification, frozen-contract and strict consistency gates are
clean. A read-only live Echo capture and local crash replay pass **24 checks**.
No controller writes, mode changes, download, clock adjustment, gateway restart
or configuration changes occurred.

## Implementation and reuse

The prior cursor used exclusive sentinel files. Process termination could leave
`.lock` or `.pending` behind and prevent a restart. The cursor now holds a
nonblocking OS lock for the complete delivery transaction and refreshes its
acknowledgement under that lock. The persistent `.guard` file is never unlinked;
unique cursor temporaries prevent a crash orphan from blocking a later commit.
Only the acknowledgement file is authoritative.

Windows uses the standard-library
[`msvcrt.locking`](https://docs.python.org/3/library/msvcrt.html#msvcrt.locking)
byte-range lock. The Unix path uses
[`fcntl.flock`](https://docs.python.org/3/library/fcntl.html#fcntl.flock);
native process acceptance in this record is Windows only. Legacy `.lock`
sentinels remain refused. Stop older collectors before upgrading and confirm
they have stopped before removing a legacy sentinel; never remove `.guard`
while a collector may be running.

`--sqlite-output` uses Python's
[`sqlite3`](https://docs.python.org/3/library/sqlite3.html) transactions and a
unique event-key constraint, with `synchronous=FULL` and immediate, nonblocking
write transactions. SQLite supplies journal/transaction handling; there is no
new custom journal, package dependency, PLC history or alarm engine. Event and
loss envelopes both have stable idempotency keys. Identical key/content replay
is accepted; conflicting content, different station/controller/build identity,
foreign database, busy writer and write/commit failures cannot acknowledge an
event. The database is a dedicated local sink, independent of the configuration
medium. It stores complete envelopes in `Events.Record`, ordered by `Events.Id`.

The existing JSONL option remains available with at-least-once append semantics.
Use a dedicated cursor/database pair; changing the sink behind an acknowledged
cursor is not a recovery procedure. Full disk/power-loss and network filesystem
acceptance are outside this record.

## Measured scope

| Item | Measured value |
| --- | --- |
| Target | `127.0.0.1`, slot 0, serial `601FC87B`, Emulate 5580 v38.011, product 288 |
| Declaration / manifest | `fraktal_ab_tower_demo`, `EA7BCE24FDA311EB` |
| Host ring | Schema 2, capacity/count 16, newest sequence 115, wrapped, epoch `[600793502, 205875]` |
| Live capture | Events 100–115 plus explicit overwrite notice for 1–99: 17 stored envelopes |
| Reopen | Read-only CLI reconnect adds zero rows |
| Local crash replay | Exit after sink acceptance and exit after cursor flush/before replace; each restarts with exactly 17 rows and cursor sequence 115 |
| Controller state | MANUAL, idle, no error/run/reset request; cycle/good/scrap counts remain 13/9/4 |
| Host runtime | CPython 3.14.7, SQLite 3.50.4, Windows |

The local crash cases replay the coherently captured live batch. Its first
accepted record is the overwrite notice, proving that replay also deduplicates
loss. Focused subprocess tests additionally terminate after accepting an event,
after a prior acknowledgement, and during replacement; cover publisher epoch
change and overwrite notices; kill an active writer and recover without manual
unlock; refuse a competing/reentrant writer; and retain the old acknowledgement
after sink refusal, busy database, write failure or a real commit-lock failure.
SQLite integrity checks pass on the reopened evidence databases.

The generated tower L5X is byte-identical using the committed and changed host
adapter: **2,224,742 bytes**, SHA-256
`03BE7A3D4F16118E328673F096EA06C250D2D64FC14027BE043B824F535A99ED`.
This batch adds no PLC storage, executable code or public ABI fields. The seed
hash and reproduction script are retained in the payload. The existing loaded
private alarm comparison image remains unchanged.

## Artifacts and remaining work

The immutable [payload manifest](AB_HOST_RECOVERY_2026-10-18/manifest.json) binds
the live batch, recovery records, SQLite files, cursor files, test/gate logs,
reproduction scripts and authored delivery source snapshots. Baseline commit:
`a29a5282cf21fcba3764ee0b4d6a8dbca14ed3c0`.

Gateway service recovery, network sinks, publisher restart identity/clock replay,
power/download/upgrade retention, physical acceptance and Unix native process
acceptance remain separate. Native alarm subscriber identity/order/backpressure,
shelf mapping and external operator isolation remain open; HostEvents delivery
does not qualify that different stream. The current consolidated list is the
completion plan's [remaining-work section](../AB_PORT_COMPLETION_PLAN_2026-10-04.md#remaining-work-after-the-2026-10-18-host-recovery-checks).
