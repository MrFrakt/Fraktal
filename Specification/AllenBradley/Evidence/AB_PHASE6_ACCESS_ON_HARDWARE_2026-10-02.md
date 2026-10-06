# Phase 6 item 3: controller access verified on press62

Date: 2026-10-02, America/Bogota (2026-10-03 UTC). Parent: `c1e8086`.
Target: `192.168.100.89`, serial `7036B510`.
Authorization: the owner said **“go on”** after the named build62 access
verification plan, covering the guarded fixture and its restoration/disarm.
The final access hardware gate passes **16/16**.

## Controller and channel

The serial guard and press fingerprint pass before each fixture. Before and
after the tests, the coherent 79,992-byte manifest matches every declaration
row: ContentHash `10AEDC3FFD6B5DC1`, ConfigRevision `1093340`, Fields 547/768,
Localization 544/768. S3 passes 6/6 both times; the stopped machine and anonymous
open-policy prerequisites pass 3/3. Gateway `/healthz` is ready with
`plcReady=true`.

The unchanged PLC source regenerates byte-identically to `C:\work\press62.L5X`,
SHA-256 `708D29CE0E7BEC5700DCC947938D3B641C8D1D64F504010BBD2888334F898E16`.
No new PLC build, compile or download is needed for these gateway/harness fixes.

## Two corrections found by the gate

The first attempt fails with `set response belongs to another sequence`.
The PLC correctly denies an OPERATOR save through CONFIG_SET=ADMIN before
dispatching the set routine. The broker then wrongly requires the old set
state to match that refused request. The correction preserves the authoritative,
matching mailbox refusal and permits no host mutation. Accepted operations
still require their own set state; denied loads cannot use an older request's
reject index. New regressions cover all six denied set kinds, unchanged host
documents, interrupted imports and refusal to use an unrelated accepted snapshot.

The second attempt passes 12/15 but its native denial and audit probes fail.
The fixture's gateway command seeds the shared native counter, then commits
the next sequence independently. The following native probe increments that
old counter to the already-consumed gateway sequence and reads its previous
successful acknowledgement. Those probes did not execute the intended command.
The fixture now seeds from the actual controller immediately before every
native transaction. A regression reproduces successful sequence 10 followed
by a newly consumed, denied native sequence 11.

The fixture also waits for its own completed login result sequence, rejects an
unconsumed LOGIN, records secret-free timings, explicitly checks logout and
requires the access-denied diagnostic for permission refusals. Its audit check
requires this run's native WRITE_CONFIG sequence and the actual OPERATOR actor,
decoded through the existing projection rather than a second decoder.
Both failed attempts restored all settings and disarmed all inputs. Neither
produced task overlaps or controller fault bits. Their results remain in JSON.

## Final hardware result

The final fixture passes 16/16, including the three read-only prerequisites:

- The correct admin, operator and technician PINs produce their registered
  controller levels. A wrong PIN gives generic failure and preserves the prior
  authenticated session.
- LOGOUT clears the user and level. A native WRITE_CONFIG claiming the admin
  name is denied while OPERATOR is active and leaves station.number unchanged.
- OPERATOR cannot save sets or lower locked access policy. TECHNICIAN can perform
  the configured DATA_WRITE, and station.number actually changes.
- An accepted operator action rearms idle timeout. Background release queries
  do not rearm it. After expiry, a claimed admin name cannot edit policy.
- The native denied-write audit identifies this request and its actual actor:
  `std.audit.accessDenied: phase6_op [kind=19, gate=1]`, sequence 89.

Five successful authentications settle in **524.964–542.011 ms**. The deliberate
wrong-PIN result settles in **498.886 ms**. These timings include the fixture's
in-process authenticated gateway transaction, CIP staging/acknowledgement and
correlated controller result read. They do not measure Chrome rendering or the
full native-PIN fallback. Maximum task scan is **5,218 microseconds** against
the **10,000-microsecond** period; task overlap count and major/minor fault bits
remain **zero**. No fault or timing counters were cleared.

All twelve policy thresholds return to NONE, timeout to 0, station.number to 1,
baseline to 950, mode and run style to 0. The session ends logged out.
Every restoration acknowledgement/readback passes; all ten fixture inputs are
disarmed. No existing parameter-set documents are touched: the denied save uses
an isolated temporary store. Local protected fixture PINs are consumed only by
the harness and are absent from evidence.

## Gates and remaining scope

The final AB suite passes **1,422 tests**; root consistency reports zero errors
and zero warnings; the root suite passes 33 tests. **Seven of seven** deliberate
broker/harness mutations are killed. No HMI source or PLC source changed.

The live gateway still has its previously imported broker and sequence state.
The owner must restart it to load the broker correction and synchronize after
the fixture's independent mailbox transactions. No gateway listener was started
or restarted by the agent, in accordance with the Phase 6 handover's standing
rule. No controller download, keyswitch/mode administration, fault/counter clear,
clock, firmware or network change was performed.

Item 3's access runtime gate is now accepted. Physical retention, data-class
permissions, alarm shelving and the full write-enabled S9 suite remain owed.
The v33 legacy zone-and-conduit bench remains write-enabled by its recorded
decision; this gate does not mark S9 or the overall security claim met.

All three attempts, pre/post read-only checks, timings, restoration and offline
gates are preserved in the [JSON](AB_PHASE6_ACCESS_ON_HARDWARE_2026-10-02.json).
