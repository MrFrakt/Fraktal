# Fraktal/AB S7 — Manifest size, read cost, and revision-change evidence

**Spike:** S7 manifest read budget

**Result:** **PASS — one bounded manifest fits comfortably. A 43,728-byte
manifest read completely and coherently in 293 ms at S1's conservative
500-byte connection and 62 ms at 4000 bytes. No per-root split is required.**

**Date:** 2026-08-14

## 1. The question

S7's register row assumes "one bounded manifest fits the read budget" and names
the consequence if it does not: **split per root with a per-root revision**.
That is an architectural fork, and it cannot be settled from estimated row
widths. It needs a manifest of realistic shape resident in the controller and
read over CIP.

## 2. What was measured

[`fraktal_ab_s7_manifest_fixture.py`](../../../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s7_manifest_fixture.py)
materialises the frozen R3 manifest contract as real Logix types — a header UDT
plus one array-of-UDT per table — at candidate capacities. Capacities are
generator parameters, not constants, so the cost curve is measurable rather
than extrapolated.

| Table | Capacity | Row | Bytes |
|---|---:|---:|---:|
| Roots | 4 | 20 | 80 |
| Modules | 128 | 40 | 5,120 |
| Nameplates | 128 | 36 | 4,608 |
| Fields | 512 | 32 | 16,384 |
| Operations | 128 | 32 | 4,096 |
| Localization | 256 | 40 | 10,240 |
| Rationalization | 128 | 24 | 3,072 |
| OptionalProfiles | 8 | 16 | 128 |
| Header | — | — | 172 |

Offline gate before download: SDK import `Warnings="0" Errors="0"`; Studio v33
**Verify Controller** `0 errors, 0 warnings`; canonical round trip identical
across both passes (`37673A77BB5D3D92885271862C6349EC986C512556E3EB62130DCA5AA5795494`);
construct census equivalent. Downloaded over USB with `0 error(s), 0 warning(s)`
and returned to Remote Run.

## 3. Read cost on the controller

The task ran at 50 ms throughout. Three repeats per connection size.

| Connection size | Manifest read | Median cold read | Effective rate | Header-only poll |
|---:|---:|---:|---:|---:|
| 500 B | 43,728 B | **292.9 ms** (317 / 293 / 293) | ~149 KB/s | 31.6 ms |
| 4000 B | 43,728 B | **61.6 ms** (85 / 60 / 62) | ~710 KB/s | 37.1 ms |

Per table, at 500 B and 4000 B respectively:

| Table | Bytes | 500 B | 4000 B |
|---|---:|---:|---:|
| Fields | 16,384 | 107.9 ms | 21.0 ms |
| Localization | 10,240 | 73.4 ms | 14.7 ms |
| Modules | 5,120 | 36.2 ms | 10.1 ms |
| Nameplates | 4,608 | 33.0 ms | 10.1 ms |
| Operations | 4,096 | 30.4 ms | 10.3 ms |
| Rationalization | 3,072 | 24.8 ms | 7.9 ms |
| OptionalProfiles | 128 | 6.4 ms | 6.1 ms |
| Roots | 80 | 4.7 ms | 4.7 ms |

The 43,728 bytes read is exactly the 43,900-byte estimate minus the 172-byte
header, which is read separately — every table came back complete.

Two shapes are visible in that data. There is a **per-request floor of roughly
4.7 ms** that the two smallest tables pay almost entirely, and above it a
throughput term that scales with connection size. A manifest split into many
small tables would pay the floor repeatedly; the eight-table shape the contract
already specifies is close to the efficient end.

### This is much faster than the S1 curve predicted

S1 measured a 4 KiB *fragmented single-tag* read at 266 ms with a 500-byte
connection. Projecting that rate, 44 KB should have taken about 2.9 s. It took
293 ms — roughly ten times better.

The difference is the access shape, not the transport. S1 forced one large
array through fragmented reads; the manifest is read as arrays of UDT rows,
which the client batches into far fewer round trips. That is a real validation
of the contract's table-of-rows design, and it means **the S1 4 KiB figure is a
worst case for a single monolithic tag, not the rate a manifest reader sees.**

## 4. Coherence and revision change

Coherence was checked the way a gateway must do it: read `ConfigRevision`, read
every table, read `ConfigRevision` again, and accept the snapshot only if it did
not move. All six snapshots (three per connection size) were stable and
complete.

Revision-change detection was measured rather than assumed. Writing the single
input `FRK_S7_BumpRevision` raised `ConfigRevision` from 0 to 1 exactly once,
the fixture's independent bump counter agreed, and the input was restored to
zero and verified.

The steady-state cost is the number that matters most: a gateway holding a valid
manifest polls the **header only**, at ~32 ms, and re-reads the whole manifest
only when `ConfigRevision` moves. The cold read is paid on connect and on
configuration change, not per cycle.

## 5. Capacities resolved

The eight symbols S7 owns are resolved in
[`AB_FROZEN_CONTRACTS_V1.json`](../AB_FROZEN_CONTRACTS_V1.json) at exactly the
values measured — not extrapolated, since the fixture materialised these table
sizes and the whole manifest was read at them:

`FRK_MAX_ROOTS` 4 · `FRK_MAX_MODULES` 128 · `FRK_MAX_FIELDS` 512 ·
`FRK_MAX_OPERATIONS` 128 · `FRK_MAX_LOCALIZATION_KEYS` 256 ·
`FRK_MAX_REASONS` 128 · `FRK_MAX_OPTIONAL_PROFILES` 8 ·
`FRK_MAX_HOSTEVENT_RECORDS` 64.

`FRK_MAX_MAILBOX_ARGUMENTS` remains S9's and is still unresolved.

**These numbers should be reviewed against a real station census before Phase 3.**
`FRK_MAX_FIELDS` is the first symbol a large station would exhaust — fifty
modules publishing ten fields each already reaches 500 of the 512. Raising it is
a cost-curve calculation against the table above, not a new spike: at the
measured 149 KB/s worst case, even tripling the manifest to ~130 KB stays under
a second at the conservative connection size.

## 6. What this does not settle

- **No budget number is normative.** The specification states no discovery or
  connect time budget, so this evidence supplies the measured cost and
  deliberately does not invent a threshold to declare it "within". The
  architectural conclusion — one manifest, no per-root split — holds under any
  budget that a 293 ms worst-case read can satisfy.
- **Torn-read detection is untested under a concurrent change.** Every snapshot
  was stable because nothing changed the manifest mid-read. That the coherence
  check *would* reject a torn read is untested; provoking a revision change
  during a large read is S9's coherence work, not this spike's.
- **One client's read strategy.** The rates are pylogix 1.1.5 batching array
  reads. A gateway using a different CIP strategy shall re-measure rather than
  inherit these numbers.
- **Single controller, single manifest.** A multi-root forest on one controller
  was not exercised beyond four root rows, and no second controller was read
  concurrently. S1's four-reader concurrency ceiling still stands.
- **Localization strings are sized, not populated.** Rows carry a 32-character
  key type; real portable key lengths may differ and would change that table's
  row width.

## 7. Commands

```powershell
python fraktal_ab_s7_manifest_fixture.py <seed.L5X> <fixture.L5X> `
    [--frk-max-fields 512] [--frk-max-modules 128] ...

# controller-changing; current explicit authorization only
python fraktal_ab_s7_execute.py 192.168.100.89 --expect-serial 7036B510 `
    --timeout 30 --connection-sizes 500,4000 --repeats 3 --execute-fixture
```

## 8. Handoff state

The controller retains the clean S7 manifest fixture in Remote Run with
`FRK_S7_BumpRevision` restored to zero and `ConfigRevision` at 1. No firmware,
fault-clear, clock, controller-network or physical-I/O operation occurred.
