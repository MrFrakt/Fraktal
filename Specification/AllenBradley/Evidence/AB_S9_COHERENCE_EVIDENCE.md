# Fraktal/AB S9 — Snapshot coherence evidence (partial)

**Spike:** S9 repository and mailbox conformance — coherence half

**Result:** **The coherence guard works and is fail-closed. Under concurrent
mutation it never once accepted a torn snapshot, it produced no false rejection
on a quiet controller, and retry-until-stable converges whenever the mutation
interval exceeds the guarded read window. S9 remains OPEN on its other
inputs.**

**Date:** 2026-08-14

## 1. The gap this closes

S7 reported every manifest snapshot coherent — but nothing was changing the
manifest during those reads, and that evidence said so explicitly. A detector
that never fires is indistinguishable from one that works, so "coherent" was
not yet a proven property of the guard; it was a property of the quiet.

AB §3.10/§11.2 specify the reader's obligation as retry-until-stable: read the
revision, read the payload, read the revision again, accept only if it did not
move. This record establishes whether that rule actually catches a torn read,
and whether retrying is a viable strategy or a busy loop.

## 2. Method

[`fraktal_ab_s9_coherence_fixture.py`](../../../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s9_coherence_fixture.py)
publishes a `DINT[1024]` (4 KiB) payload in which **every element carries the
current generation**, so a coherent snapshot is all-equal and a torn one names
the two generations it straddles. `FRK_S9_DataRevision` is published after the
payload it describes. The task runs at 10 ms and the whole payload moves inside
a single scan. The mutation period is a range-checked writable input, so the
rate can be swept.

Offline gate first: SDK import `Warnings="0" Errors="0"`, Studio v33 **Verify
Controller** `0 errors, 0 warnings`, canonical round trip identical
(`346E838782F8019E92E3F5A45CACD08A40965BD17C79F64B61B38A30BC4C197C` ACD), census
clean. Downloaded over USB with `0 error(s), 0 warning(s)`.

The experiment is deliberately ordered so a pass cannot be vacuous.

## 3. Control 1 — the guard does not reject a quiet controller

With the fixture frozen, three guarded reads:

| Revision before → after | Read | Generations observed |
|---|---|---|
| 320 → 320 | 8.5 ms | `[320]` |
| 320 → 320 | 7.1 ms | `[320]` |
| 320 → 320 | 6.9 ms | `[320]` |

All accepted, all internally consistent. A guard that rejected a still
controller would be useless, and this rules that out.

## 4. Control 2 — tearing is real, not theoretical

With mutation every 10 ms and **no guard**, five raw reads of the same array:

| Read | Consistent | Generations |
|---|---|---|
| 1 | yes | `[344]` |
| 2 | yes | `[345]` |
| 3 | **no** | `[345, 346]` |
| 4 | **no** | `[346, 347]` |
| 5 | yes | `[347]` |

Two of five reads straddled a generation boundary and returned a payload that
never existed as a coherent state. This is the failure mode the guard exists to
catch, observed directly rather than argued.

## 5. The measurement — does retry converge?

Ten guarded attempts at each mutation rate:

| Mutation interval | Accepted | Success rate | Median read | Accepted-but-torn |
|---:|---:|---:|---:|---:|
| 10 ms | 0 / 10 | **0 %** | 7.6 ms | **0** |
| 50 ms | 8 / 10 | 80 % | 6.9 ms | **0** |
| 200 ms | 10 / 10 | 100 % | 6.9 ms | **0** |
| 1000 ms | 10 / 10 | 100 % | 6.8 ms | **0** |

**The safety property held everywhere: not one accepted read was internally
inconsistent, at any rate.** The guard never laundered a torn payload as good —
which is the failure that would matter, because it would hand the HMI bad data
wearing a coherent label. Under impossible conditions the guard degrades to
refusing service, not to lying.

### The rule this establishes

Retry-until-stable converges when the **mutation interval exceeds the guarded
read window**. The window here is two revision reads bracketing a 4 KiB payload
read — roughly 12–15 ms including round trips — which is why 10 ms mutation
never converges and 50 ms mostly does.

Stated as a design rule for the generator and gateway:

> Any data set guarded by a coherence token **shall** have a mutation interval
> longer than its guarded read window, or it **shall** be double-buffered on the
> PLC side. Retry is not a substitute for either.

## 6. Why this vindicates the contract's shape

The rule maps cleanly onto what Fraktal actually guards, and that is not an
accident of this fixture:

- **The manifest** changes only on a configuration change, which is rare by
  construction — so retry converges trivially, and S7 already measured the read
  at 293 ms worst case.
- **The HostEvents ring** changes only when an event is appended, and the
  gateway brackets the record window with ring metadata.
- **Registry rows** carry a per-row `DataRevision` covering that row's fields.
  A row is small enough to read in a single request, so it is atomic on the
  wire and never needs a retry at all.

What retry cannot do is produce a coherent snapshot of a **whole forest of live
values changing every scan** — this measurement puts a number on that
impossibility. Core does not ask for one: coherence is specified per row, not
across the live surface. A future design that tried to snapshot the entire live
tier atomically would need double buffering, and would be departing from the
contract rather than implementing it.

## 7. What S9 still owes

The coherence half is done. Still open:

- **freshness thresholds and the poll budget** declared for a reference station
  (AB §3.13 makes these per-deployment, not per-binding);
- **quality codes and timestamp mapping** — the `GOOD`/`UNCERTAIN`/`BAD`
  transitions and their fail-closed defaults;
- **reconnect discovery** and configuration-revision change handling across a
  dropped session;
- **the shared repository contract suite**, which is how AB proves semantic
  parity without a Beckhoff rig
  ([decision record](AB_S8_S9_DECISION_RECORD.md)); and
- **the mailbox matrix** — duplicate/out-of-order sequences, the five
  replay-capable crash boundaries, DINT wrap, secret clearing, PLC refusal —
  owed when writes are enabled, since the initial claim is read-only.

The cross-binding commit-marker item recorded in AB §7.7 and TC3 §3.10 is also
still open and applies to both bindings.

## 8. Commands

```powershell
python fraktal_ab_s9_coherence_fixture.py <seed.L5X> <fixture.L5X>

# controller-changing; current explicit authorization only
python fraktal_ab_s9_execute.py 192.168.100.89 --expect-serial 7036B510 `
    --timeout 30 --sweep 1,5,20,100 --attempts 10 --execute-fixture
```

## 9. Handoff state

The controller retains the clean S9 coherence fixture in Remote Run with
`FRK_S9_Freeze` at zero and `FRK_S9_MutationPeriod` restored to its default of
10 scans; cleanup was verified. No firmware, fault-clear, clock,
controller-network or physical-I/O operation occurred.
