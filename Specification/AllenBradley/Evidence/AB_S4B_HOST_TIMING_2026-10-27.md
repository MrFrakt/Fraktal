# S4b read-only host timing and packet support — 2026-10-27

**Diagnostic findings only. Canonical/desktop acceptance remains open.**
The [row-refill attempt](AB_S4B_REFILL_ATTEMPT_2026-10-27.md) passes 41 cases,
87 independent exact replays and 3,144 entirely Good observer samples. Desktop
still becomes STALE after overview at 1,428.145 ms. Genealogy, five original
documents, 31 baseline cases and final checks pass. Its authorization is consumed.

These subsequent probes only read the restored baseline on local Echo
601FC87B, 1756-L81E v38.011, 127.0.0.1 slot 0. Fresh service/listener/identity/
fault/keyswitch guards precede each probe; transports pin the serial. No tag
writes, mode changes, downloads, clears, clock/power/vendor-state operations or
Echo hard kills occur. Diagnostic isolate cleanup affects its worker only.

## Scalar/timer control

Each phase reads the public HealthProbe Samples DINT 160 times through four
serial-pinned connections, one outstanding request per socket, in a worker
isolate. Forty one-millisecond timers follow. Flutter uses the same fully-live
binding as qualification: first without widgets, then with the shipped simulator
UI. This simulator phase is rendering load only, not the live station UI.

| Host | Request median /p95 /max (us) | 1 ms timer median /max (us) |
|---|---|---|
| Dart CLI | 891.0 /1720 /4047 | 2490.0 /4774 |
| no widgets | 1120.0 /2821 /13073 | 2388.5 /3272 |
| simulator UI rendering only | 1276.5 /6974 /16290 | 2181.5 /3589 |

The observed Flutter request tails (13–16 ms) can exceed the 10 ms canonical
row-proof window. Medians remain near 1 ms. This does not isolate the precise
host/network/PLC cause of prior qualification failures. It does not justify
altering proofs, retry budgets, source timestamps or freshness limits.

## Multiple Service Packet support

[Rockwell's data-access manual](https://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm020_-en-p.pdf)
documents service 0x0A for grouping requests in one explicit message.
The fixed probes read Samples /TaskLastScanUs /Samples; every embedded operation
is a read. Python sends 20 packets/60 Read Tag services, with native headers,
counts, offsets, type and exact DINT lengths checked. Dart's new read-only
transport sends 20 packets/60 Read Tag Fragmented services with typed replies.
No credential-bearing tag is read. Native raw responses and request bytes are
retained for the Python probe.

Python packet time (us): `{'minimum': 498, 'median': 539.0, 'maximum': 732}`; equal sample counters **20/20**.

Dart packet time (us): `{'minimum': 763, 'median': 1006.0, 'maximum': 2646}`; equal sample counters **19/20**.

The changed-counter packet shows that an MSP is not a whole-scan atomic
transaction. The canonical reader must still prove equal-even published
counters and a window below the declared interval. HealthProbe Samples is not
that seqlock; these packets prove protocol support/timing only, not canonical
coherence, desktop acceptance or the performance of a full tree.

Next is offline validation of bounded row packets retaining every original
proof/freshness/read-only gate, then separately authorized canonical-image
qualification. No new controller-changing operation is authorized here.
The canonical image/Capacity and shipping V2 activation remain unchanged.
Nothing is committed or pushed. Credentials and binaries are excluded.
