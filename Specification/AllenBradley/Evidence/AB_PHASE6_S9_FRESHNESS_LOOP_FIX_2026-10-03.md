# Phase 6 S9 freshness detail-read loop correction — 2026-10-03

The owner reported repeated HMI LIVE/STALE transitions after freshness activation.
Read-only requests through the existing serial-guarded gateway reproduced the
cause: the complete samples were Good, but the generic repository awaited all
2,621 view-gated leaves before accepting each sample. Six sequential targeted
batches took 1.95–2.42 seconds. Adding
the complete sample's age crossed the unchanged 2 s Good deadline, withdrawing
the shell while subsequent samples restored it.

The repository now accepts and publishes complete station samples independently
of detail work. It serves active scopes through one bounded background RPC at a
time, so the transport can service complete polls and acknowledgements between
batches. Each detail batch retains its own monotonic read-start age and inferred
logical scalar type; current station samples cannot renew it. Late/expired detail
is withheld from the Good-only value map while its quality remains explicit.
Scope/discovery changes, station withdrawal and disposal invalidate pending
detail replies. Older transports retain their existing behavior.

The new regression fails against baseline `0db0a18` with the same late-sample
failure, and passes with the correction. Additional tests cover closing a scope
during a blocked read, independent per-batch expiry, and refusal to keep a stalled
station live from fresh detail traffic. The four additions bring HMI tests to
463 (7 expected skips) and the shared TC3/AB repository suite to 75. AB discovery
passes 1,535 tests; root consistency reports 0 errors/0 warnings and its 33 tests
pass. Analyzer and release Web build pass. A captured 3,835-value gateway document
also passes the production mapper/freshness checks in compiled JavaScript,
including preservation of native Bad status. The Flutter Chrome harness did not
reach test execution and was cancelled; this replay does not claim browser UI
acceptance.

The final release client is deployed in Caddy's existing root. Authenticated HTTPS
GETs validate the `press.localhost` TLS hostname and return byte-identical
`main.dart.js`, bootstrap and index. Main JavaScript SHA-256:
`0CD194DF08FD04EB7814B11FC596B12590DE2CD6C196C455E325E30FC1D99C86`. The prior client is backed up at
`C:/work/press68_loop_web_backup_02` (the original freshness client is backup 01).
No Caddy, credential, gateway process, controller configuration or tag was changed
by this correction. The deployment remains write-enabled through the existing
owner-started gateway; no new writable claim is made.

Press68 remains the downloaded memory baseline, with L5X SHA-256
`E2C20374F8FC7364672E425EBC3E55CC5F6D9F81ED4894BB32366E737BA586F7`. There is zero PLC memory growth and no import/download requirement.
The four-user ceiling and declared freshness budgets are unchanged.

Corrected live verification is pending. Port 8099 had stopped before the
read-only production-repository probe, which failed with connection refused.
The owner was asked to restart with the existing launch command and hard-refresh
Chrome. The handover reserves write-enabled gateway restart for the owner, so
the agent did not start it. **Full write-enabled S9 remains open** until corrected
live verification passes. Physical retention and the separate S1 time probe
remain separate; owner-deferred mode-latency tuning is not resumed.

The companion [JSON record](AB_PHASE6_S9_FRESHNESS_LOOP_FIX_2026-10-03.json) contains all 24 snapshot summaries,
12 measured detail cycles, regression result, final deployment checks, test-log
hashes, and the pending live-verification status. Failed baseline-proof attempt
`C:/work/press68_loop_baseline.log` is retained separately: the test caught the
unbounded call, but its fixture initially modeled only one RPC's duration. The
second attempt models every chunk, fails with the causal late-sample error,
and removes its temporary baseline source.
