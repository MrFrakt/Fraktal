# Phase 6 command latency correction

**Date:** 2026-10-03, America/Bogota. **Parent:** `c533f54`.
**Scope:** gateway and generic HMI software only. No controller writes, mode
changes, downloads, provisioning, gateway starts or gateway restarts were made.
The corrected Web release is deployed. The running gateway still needs the
owner's restart, and complete browser mode-change timing remains unmeasured.

## Finding and limits

The owner reports mode changes increasing from under one second to roughly
three seconds. The gateway's three-leaf acknowledgement RPC used a full station
read, as did command preflight. A read-only probe of the running server measured
the acknowledgement RPC at **184.509, 183.669 and 187.012 ms**. A full snapshot
took 202.128 ms. The served JavaScript was still the press64 artifact, rather
than the prepared press68 client. These establish avoidable software overhead;
they do **not** establish a measured decomposition of the entire three seconds.
Chrome is unavailable to the browser tool in this session.

The controller's currently readable manifest matches press68:
`7A9B9A8B59EEFD16` / 8035226. The independent read-only S3 probe passes 6/6:
sampled last scans 644–866 µs, median 660.5 µs, native maximum 2,492 µs,
10,000 µs period, no overlaps or major/minor fault bits. This is a read-only
observation, not timing under a commanded mode transition or native S9 write
acceptance. The owner's Verify/completed-download confirmation is still owed
before the pending write fixture is run.

## Change and preserved checks

Command preflight and acknowledgement target reads now use four native reads:
leading manifest header, whole response structure, request Sequence, trailing
header. Both headers must match the already acquired manifest and the declared
build; the diagnostic resolves through that controller catalogue. Cold and
reconnected readers validate a complete station first. The request/ack pending
check, modular replay guard, sequence reservation before I/O, guarded primitive
writes and native acknowledgement wait remain in force. Partial reads cannot
replace complete snapshots, discovery paths, cached Good values or restore
full-station health. Failed reads invalidate cached Good data. Cancellation
retains the native lock until its worker finishes.

The validated `Kind=NONE` cleanup already performs no native write; it now avoids
opening a redundant native connection. Gateway authentication/scope checks
still run. A bulk-capable generic HMI requests one shared full refresh immediately
after an interactive request, so its mode indication follows the PLC's actual
state. It never substitutes the requested mode for the published mode. Existing
PLC access, mode-exit policy, graceful-stop and interlock decisions are unchanged.
A credential-free `mailbox-complete` log records total and queue time to support
the owner's subsequent full-command measurement.

The production read-cost harness now also measures mailbox preflight and the
gateway's acknowledgement target path, without a listener or write roots.
Three samples on serial `7036B510` give:

| Read | Median | Maximum | Native reads |
|---|---:|---:|---:|
| Mailbox preflight | 18.719 ms | 19.513 ms | 4 |
| Mailbox acknowledgement | 18.759 ms | 18.896 ms | 4 |
| Full steady station | 213.524 ms | 224.793 ms | 37 |
| Six viewers sharing a snapshot | 217.374 ms | 227.254 ms | 37 |

The previous running-server RPC and this non-listening production harness use
different envelopes; the raw timings are retained in the companion JSON. The
reduction is specific to the read path, not a claim of total mode-change time.
Neither benchmark declares an S9 freshness budget or a write-enabled claim.

## Validation and deployment

The final AB discovery passes **1519 tests in 305.074 s**.
Root consistency reports 0 errors/0 warnings; all 33 root tests pass. The shared
TC3/AB repository contract and related transport/repository checks pass 61 tests;
the full Flutter suite passes 449 with 7 skips. Flutter analysis has no issues,
and the release Web build succeeds. All **14 in-memory mutants** are detected,
including removal of either mailbox coherence header check, stale preflight and
reviving cached Good data after a mailbox failure. No filesystem mutants or
controller I/O are used by these tests.

Regeneration is byte-identical to `C:\work\press68.L5X`, SHA-256
`E2C20374F8FC7364672E425EBC3E55CC5F6D9F81ED4894BB32366E737BA586F7`. Controller data and generated logic growth are **zero**;
the four-user ceiling is retained. This software change requires no PLC download
and introduces no new ST to compile.

All 42 resources at Caddy's actual
`FraktalCore/HMI/build/web` root match `C:\work\press68_mode_hmi_web`.
Main JavaScript SHA-256 is `707FFF4E0732C352E0830D93A09C6F9D6712B12857103ACFD3AE383C212686D4`.
The previous release is retained at `C:\work\phase6_mode_hmi_https_backup_20261003_160427`.
Proxy configuration/authentication are unchanged; the unauthenticated HTTPS
request returns 401, and gateway health remains `ready`, `plcReady=true`.

## Owner continuation

Restart the existing gateway with its established launch configuration, then
hard-refresh Chrome at `https://press.localhost/` with Ctrl+Shift+R. Measure an
idle mode change and, if it still takes seconds, retain the gateway's
`mailbox-complete` elapsed/queue times. A running graceful mode change may still
wait for the current cycle by the PLC's policy. The standing handover reserves
write-enabled gateway restarts to the owner; this correction does not change
that rule or authorize the pending native write fixture. Native S9, declared
current-station freshness/poll budgets and physical retention remain owed.

Raw observations and gate counts: [companion JSON](AB_PHASE6_COMMAND_LATENCY_2026-10-03.json).
