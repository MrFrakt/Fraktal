# Phase 6 S9 — read-only preflight on press68

**Date:** 2026-10-03, America/Bogota. **Source:** `ca056b0`.
**Result:** read-only preflight passes; **native S9 writes have not run and the
write-enabled claim remains open**. The owner reports minimal improvement in
mode-change response and asks to move on; further latency work is deferred.
No controller write, mode change, download, provisioning, gateway restart,
listener or fault/network/clock operation occurred in this work. The raw record
is [the companion JSON](AB_PHASE6_S9_READ_ONLY_PREFLIGHT_2026-10-03.json).

## Native identity, readiness and memory boundary

Exact serial `7036B510` at `192.168.100.89` matches. The manifest read passes:
all rows match, leading/trailing headers are coherent, 68,472 bytes, major 4,
binding 2, `7A9B9A8B59EEFD16` / revision 8035226. Fields are 565/640 and
Localization 570/640. The write tool's read-only mode reports `ready=true`,
with a passing fingerprint and the Unit stopped and free of execution error.

Independent restoration preflight confirms that the three local fixture
registrations match the private declaration, the current session can be
restored, LoginBusy is false, session timeout is zero and request Sequence
equals acknowledgement. PINs, salts, hashes and gateway credentials are not
emitted. Those facts establish fixture readiness; they do not authorize writes.

The artifact remains `C:\work\press68.L5X`, SHA-256 `E2C20374F8FC7364672E425EBC3E55CC5F6D9F81ED4894BB32366E737BA586F7`.
This work changes no PLC data or generated logic: **zero memory growth**.
Press67 remains the owner-confirmed successful memory baseline until the owner
confirms press68 completed Verify **and** link/download. The earlier prepared
press68 growth of 1,088 declared bytes is not charged again. The four-user
ceiling is unchanged. A readable manifest does not identify every emitted
instruction or prove the licensed compile gate; no native-fit claim is inferred.

## Read contract and runtime observations

The running gateway passes **13 read-only checks** across two WebSocket
sessions: complete discovery of 3,835 paths; three acknowledgement leaves with
Good quality and gateway acquisition UTC; no invented source timestamp; value
and DataValue agreement; targeted reads; stale-revision refusal; stable full
rediscovery; and the same contract after reconnect. No `write` or `writeBatch`
method is invoked. These observations establish the successful read path, not
failure injection, mailbox acceptance or the entire quality-transition matrix.
The offline shared contract and failure/mutation checks remain the evidence for
those additional software semantics.

The current-code production read harness, without a listener, passes cold,
steady, native profiler tiers, target promotion and six viewers sharing one
reader. Five cycles give:

| Read | Median | Maximum | Native reads |
|---|---:|---:|---:|
| Cold station | 480.995 ms | 480.995 ms | 46 |
| Steady station | 192.702 ms | 202.178 ms | 37 |
| Mailbox preflight | 15.911 ms | 17.426 ms | 4 |
| Mailbox acknowledgement | 16.884 ms | 17.331 ms | 4 |
| Profiler excluded | 192.165 ms | 196.500 ms | 36 |
| Profiler targeted | 196.649 ms | 196.649 ms | 37 |
| Profiler slow | 189.155 ms | 192.607 ms | 36 |
| Six-viewer shared snapshot | 198.050 ms | 202.284 ms | 37 |

The live gateway's acknowledgement reads immediately following a snapshot
were cache hits (0.532/0.508 ms). They cannot substitute for the fresh-control
read benchmark above or for full browser mode-change timing. This record does
not establish that the running gateway has imported every source correction.

The independent serial-guarded S3 probe passes **6/6**, with the 10 ms task,
native maximum scan 2,492 µs, no overlap and no major/minor fault bits. Detailed
timing windows remain in the JSON. Current-station freshness thresholds/poll
budgets and enforcement still need a declaration against these measurements;
the old 100 ms Phase 0 profile is not inherited.

## Gates and authorized continuation

Full AB tool discovery passes **1519 tests in 207.987 s**
with a fresh unused bytecode prefix. Root consistency reports 0 errors and
0 warnings; all 33 root tests pass.

The concrete next operation is the prepared, exclusive
`fraktal_ab_s9_write_execute.py --execute-fixture` on serial `7036B510`. It
tests payload/commit/ack interruption, stale reconnect, signed/uint32 wrap,
partial and reordered frames and wiping. It changes session/timeout and bounded
mailbox fields, checks exact target before each primitive write, and restores
the original known session and timeout independently in finally. It requests
no movement, force, clock, fault or mode write. Keep the HMI idle so its mailbox
requests cannot compete with the fixture.

[AGENTS.md §3a](../../../AGENTS.md) requires current explicit authorization for
controller-changing operations. The [Phase 6 handover](../AB_PHASE6_HANDOVER_PROMPT.md)
defines the owner reply “done” after completed Verify/download as authorization
for verification harness tag writes. That confirmation was requested and is
pending; the armed fixture was therefore not run. The S9 write-enabled claim,
native fit, deployment freshness/poll declarations/enforcement and physical
retention remain owed.
