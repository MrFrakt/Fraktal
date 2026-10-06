# Phase 6 S9 — deployment freshness on press68

Date: 2026-10-03. Source base: `c3757b1071e7f92c52df16f6cc56cbf909442d17` with the source hashes
in the [JSON record](AB_PHASE6_S9_FRESHNESS_2026-10-03.json). This supersedes the
previously owed freshness software leg, without rewriting earlier evidence.

The owner already completed press68's download. Its [17-row native mailbox
vector and all eleven regressions/restoration](AB_PHASE6_S9_NATIVE_MAILBOX_2026-10-03.md)
remain the native write evidence. This work made **no controller write**, did
not run an armed regression, and did not start/restart a write-enabled gateway.

## Declared reference budget and measured cost

`fraktal_ab_press_demo.application().read_budget` is the authoritative source.

| Limit | Declaration |
|---|---:|
| Fast poll | 500 ms |
| Shared cache | 250 ms |
| Slow heartbeat | 1,000 ms |
| Fast/slow Good limit | 2,000 ms |
| Fast/slow expiry | 3,000 ms |
| Native read connection | 4,000 bytes |

Fast Good/expiry allow four/six poll periods; slow Good/expiry allow two/three
heartbeats. These are deployment limits against press68's actual cost, not
Phase 0's 100/300 ms figures and not a guarantee for another station. The
template declares candidate limits with a conservative 500-byte reader and
requires its own measurements. Writers retain the already verified bounded
500-byte native frame profile.

The serial-guarded read-only vector on `192.168.100.89`, serial `7036B510`,
`1769-L24ER-QB1B/A` v33.14, passes. Cold read: 465.979 ms / 46 native reads;
steady: median 198.041 ms, maximum 199.521 ms / 37 reads. Fresh mailbox preflight
maximum 16.936 ms / four reads; Ack maximum 17.395 ms / four reads. Six viewers
share one complete read: maximum 224.933 ms / 37 reads. Exclusion removes a
native group; targeted demand renews it; slow heartbeat refreshes it when due.
The cost check enforces steady/six-viewer maximum below the poll period and
twice cold cost below the Good limit, including the HMI's conservative RPC
allowance. These are measured maxima over five cycles, not a worst-case bound.

S3 remains **6/6**, maximum task scan **7,754 µs** under the 10,000 µs period,
zero task overlaps and controller fault bits. PTP/time synchronization remain
false; no source UTC clock or cross-controller ordering is invented.

## Enforced behavior

Gateway/cache ages use a monotonic clock starting before native I/O. Cache hits
preserve acquisition timestamps and advance ages. At the Good limit, a retained
value becomes Uncertain with `read-late`; at expiry it becomes Bad with
`read-expired`. The flat values surface drops non-Good data, retaining its
DataValue metadata. A previously Bad/Uncertain value is never promoted by aging.
The whole station's healthy/readiness flag expires during a blocked worker.
Partial fresh Ack traffic cannot restore it. A mutation requires a current
complete sample and checks again inside the native worker immediately before
delivery. Read-only configuration pages cannot revive old data.

The generic repository consumes the optional version-1 freshness envelope from
`OPCUA_TRANSPORT.md`. It adds RPC elapsed time to server age, then advances with
a local Stopwatch; UTC clock corrections do not renew freshness. A timer
independent of a pending RPC withdraws the interactive shell/cached Good data
at STALE and reports DOWN at expiry. It also checks age before writes and queued
requests, so a delayed browser timer cannot authorize an expired command.
Only a fresh complete snapshot returns LIVE. Polling continues during initial
manifest hydration and long interactive work once a valid tree exists. A
delayed complete reply cannot become fresh just because it arrived. Unknown
budgets fail closed; invalid leaf metadata is Bad. Legacy transports without
the envelope preserve existing behavior and do not inherit this verification.

## Validation and unchanged controller memory

- AB discovery: **1,535 tests**, 220.649 s; focused gateway/tier tests **104**.
- Shared production TC3/AB repository/reconnect/gateway/freshness suite: **70/70**,
  with the AB fixture emitted by the production gateway using the actual budget.
- Full Flutter suite: **458 passing, 7 expected environment/fixture skips**;
  analyzer clean; release Web build succeeds.
- Root consistency: **0 errors / 0 warnings**; root tests **33**.
- Five semantic mutants killed: ignored health age, completion-time renewal,
  retained expired payload, delivery without expiry check, and a fixed heartbeat
  overriding the deployment. Final mutation run has zero harness errors; the
  initial exception-class mismatch is retained in the JSON.

Both generated L5X artifacts are byte-identical. Added controller data/ST is
**zero**, the four-user ceiling stays, and press68 remains the successfully
downloaded memory baseline:

- Press SHA-256 `E2C20374F8FC7364672E425EBC3E55CC5F6D9F81ED4894BB32366E737BA586F7`.
- Template SHA-256 `95BAE8768BB240E625D54BA5D31706FD733E012B098D1CC728BAA1F48C2C43E2` (still offline only).

No new import/download or new PLC compile is required for these identical
artifacts. This does not claim that the template was deployed or that new ST
was compiled on the bench.

## Deployment and remaining gate

Release Web output is copied to the actual Caddy root
`FraktalCore/HMI/build/web`, with the prior complete folder retained at
`C:/work/press68_freshness_web_backup_01`. Main JavaScript SHA-256:
`A00D83AC9AC7369E449A1B01CF250C22859919AC8473396AC3914C15527FC1A6`.

Authenticated HTTPS GETs of main JavaScript, bootstrap and index return 200 and
match the tested files. The first verification failed because the Windows OS
resolver does not resolve `press.localhost`; Chrome handles the localhost name.
The successful check routes to 127.0.0.1:443 while preserving Host/SNI and fully
validating TLS for `press.localhost`. No proxy credentials or configuration
were changed.

**Full write-enabled S9 remains open.** The gateway process predates this source
(PIDs 18120/9612, creation 2026-10-03 15:36:46 local). The owner must restart the
existing gateway and hard-refresh Chrome; then verify the live freshness
envelope read-only. Serving updated assets and passing source tests cannot prove
that the running gateway loaded them. Physical retention is separate debt;
the historical separate S1 time probe and TC3 native segmented transport were
not newly exercised here. Further mode-latency tuning remains owner-deferred.
