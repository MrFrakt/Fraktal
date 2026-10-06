# Phase 6 S9 — native mailbox verification on press68

**Date:** 2026-10-03, America/Bogota. **Runtime source:** `95c42d0`;
the fixture-only timing correction's source hashes are in the JSON.
**Result:** the native write vector passes **17/17**, all eleven regression suites
pass, and independent restoration/readback passes. The **full write-enabled S9
claim remains open** for current-deployment freshness/poll declarations and
enforcement. Physical retention is a separate remaining requirement.
The [companion JSON](AB_PHASE6_S9_NATIVE_MAILBOX_2026-10-03.json) retains the
native rows, regressions, guards, failed attempts and corrective restoration.

## Authorization, artifact and memory baseline

The owner's “that was already downloaded” confirms the completed press68
download, satisfying the handover's current authorization for its verification
harnesses on serial `7036B510` at `192.168.100.89`. The HMI was requested to stay
idle during the exclusive vector. Every primitive write retains an immediate
exact-target check; the fixture is local and starts no gateway/listener.

The verified owner artifact is `C:\work\press68.L5X`, SHA-256
`E2C20374F8FC7364672E425EBC3E55CC5F6D9F81ED4894BB32366E737BA586F7`. Full native manifest readback is coherent and equal:
`7A9B9A8B59EEFD16` / revision 8035226, major 4, binding 2, 68,472 bytes,
Fields 565/640 and Localization 570/640. Native V3 behavior passes in addition
to the published identity; ContentHash alone does not identify emitted logic.

**Press68 is now the successful downloaded memory baseline.** Its already
recorded growth over press67 is +1,088 declared bytes, +4,119 ST source bytes
and +63 statement terminators; this verification adds **zero PLC memory**.
The four-user ceiling is unchanged. Generated sizes exclude native compiled
overhead/free memory. Owner download confirmation supplies the fit evidence;
the SDK's earlier “No valid license” refusal is not reclassified as an agent
compile. The station template remains offline-tested.

## Native request and replay results

The production writer uses a single 89-DINT / 356-byte frame at a 500-byte
connection, with 312 aggregate ASCII argument bytes, then Sequence as a
separate final commit. The native vector passes the five replay boundaries:
payload before commit, commit before acknowledgement, acknowledgement before
local completion, stale reconnect and full uint32 wrap. Burned requests do not
replay; fresh explicit requests recover. Signed-DINT storage crosses the sign
boundary and wraps through zero without changing uint32 semantics.

Premature commit refuses once; a late payload never self-executes. Reversed
argument segments execute only after the matching final commit. Consumed public
frame words are zero. CPS sampling, private-frame wiping, individual/aggregate
bounds, secret clearing and cancellation remain additionally covered by the
offline emitted-code/production-writer tests and prior 14 killed S9 mutants.
No TC3 hardware transport or separate rapidly-mutating coherence fixture was
run in this verification; their recorded scope is preserved.

The vector counts 27 directly injected guarded native writes. Production
login/rejoin/restoration use their own immediate serial guards outside that
counter. The original session was **anonymous**, with zero timeout; both are
restored and independently read back. No PIN, hash, salt or bearer is emitted.

## Regressions, failure handling and cleanup

| Suite | Result |
|---|---|
| Native S9 replay/frame vector | 17/17 |
| Shelving | 15/15 |
| Data classes | 18/18 |
| Access | 16/16 |
| Capture / read-only query | 10/10 |
| Parameter sets | 17/17 |
| ST/SFC/LD principles parity | 25/25 |
| Phases 1, 2, 3, 4, 5 | 7/7, 6/6, 8/8, 11/11, 25/25 |
| S3 before/after native vector and after regressions | 6/6 each |
| Independent final readback | 7/7 |

An initial external launcher referenced a nonexistent copied wrapper; no child
fixture ran, and session cleanup passed. The corrected launcher retained the
existing guard. The first Phase 5 invocation later stopped on a failed
`FRK_Press_HmiRequest.Frame.Words` write. No Sequence for that attempt was
committed or automatically retried. Its original exception did not include a
native status, so a network/controller cause is not inferred. Finally cleanup
stopped/disarmed the fixture, but left Mode different from the global original.
An explicit guarded mode restoration and independent readback passed before
the fresh Phase 5 run. That run completes 24/25: the downtime row sees 1,750 ms
while comparing against a one-second sleep and ignoring native read cost. Its
cleanup restores every original value. The fixture correction brackets the
actual native OEE acquisitions, reuses the owning projection for the card, and
checks DownMs against that measured interval with the existing 250 ms allowance.
Run/Idle growth, zero/half/double downtime rates and missing samples still refuse.
The corrected retry passes 25/25. Four focused fixture tests pass and both
in-memory mutants (fixed-sleep bounds and omitted rate validation) are killed.
Global mode/style/session restoration is also verified. All original failed
outputs remain in the JSON; PLC/gateway/HMI source was not changed and press68
regenerates byte-identically.

Across successful regression invocations, **3,712 primitive Write attempts**
have the same number of immediate exact target checks, with zero identity
blocks. Failed Phase 5 invocations have separate 196- and 1,055-check records.
Setup/restoration guards are outside the CLI counters. The external guard's
offline three-case check permits the intended target and refuses a changed
serial or wrong IP before delivery.

Independent final readback matches the original configuration, class/action
policy, timeout, AUTO/CONTINUOUS mode and anonymous session. The Unit is stopped
without Error, LoginBusy/LoginFailed are zero, all ten fixture inputs are zero,
no active shelf remains, request/ack sequences agree and the public frame is
wiped. The existing gateway reports `ready`, `plcReady=true`. Maximum task scan
is **7,754 µs** against **10,000 µs**, with zero overlaps and major/minor
fault bits. No timing/fault counters were cleared.

## Software gates and remaining S9 work

The full AB suite passes **1,521 tests in 211.191 s** with
a fresh unused bytecode prefix. Root consistency reports **0 errors / 0
warnings**, and all **33** root tests pass. The explicit shared repository /
reconnect / gateway / repository runner passes **61 tests**
using the real production AB projection with native fixtures; its command peer
is a fixture, so this is software contract parity, not a TC3 hardware claim.

The preceding read-only record measured ~193 ms steady reads and ~17 ms fresh
mailbox reads. Historical Phase 0 100/300 ms fast poll/freshness limits are not
transferred to this station. Current code has a 250 ms HMI poll/cache, a one-second
native slow heartbeat and a five-second RPC timeout, but successful-read costs
and immediate failure invalidation do not prove expiry while a read stalls.
The remaining S9 work must declare measured deployment budgets and test expiry,
quality and command suppression at those boundaries. It should require no
additional PLC storage. Further owner-deferred mode-latency tuning is not part
of this verification.

No agent download, gateway launch/restart, provisioning/PIN change, clock set,
firmware/network change or native fault/counter clear occurred. Authorized
fixed-vector requests and fixture/policy/session changes were restored. No new
import/download is needed for this verified artifact.
