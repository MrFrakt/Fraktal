# Phase 6 D6 — gateway health write-access reporting

Date: 2026-10-03 (America/Bogota).
Result: **software implemented and offline gates passed; owner restart and live
readback pending on the press68 bench.** The generic Dart gateway is compiled
and tested with fake clients, not deployed to a TwinCAT target by this run.

Both gateways now include the same additive `writeAccess` object on `/healthz`,
`/livez`, and `/readyz`. Its semantics are defined once in the
[transport contract](../../OPCUA_TRANSPORT.md). For the bench's approved `Press`
write scope, the expected post-restart block is:

```json
{"writeAccess":{"enabled":true,"roots":["Press"],"allRootMailboxes":false}}
```

This reports configured command access, separately from native availability and
PLC user permissions. AB requires its bearer, scope, and wired writer. The Dart
gateway continues to rely on the authenticated same-host proxy. Existing
authentication, command delivery, QUERY_CONFIG exception, health status codes,
PLC readiness and four-user ceiling are unchanged. No credentials are returned.

Validation:

- Full AB discovery: 1,537 tests, 205.995 seconds, PASS.
- Dart gateway HTTP/WebSocket suite: 29 tests, PASS. Tests compare health policy
  with actual fake-client write acceptance, default refusal, explicit scope and
  all-root precedence. All three endpoints are checked before a PLC read;
  readiness can subsequently change without changing configured write access.
- Six in-memory AB mutants killed: ignoring the token, writer, scope or all-root
  enablement; letting all-root scope override explicit roots; leaking a token.
  No repository source was changed by the mutation run.
- Root consistency: 0 errors, 0 warnings; root suite: 33 tests, PASS.
- HMI and gateway analyzers: no issues; Windows Dart gateway executable compiled
  successfully to `C:/work/press68_d6_gateway.exe`. It was not executed/deployed.

A read-only HTTP probe of the existing loopback gateway at
`http://127.0.0.1:8099` still found the old response schema on all three routes.
At that observation, `/healthz` and `/livez` returned 200, `/readyz` returned 503,
and `plcReady` was false. The probe performs no controller read and establishes
neither the cause nor subsequent PLC readiness. This is a baseline, not live
acceptance of the updated gateway. Its UTC timestamp falls on 2026-10-04, which
is still 2026-10-03 in the bench timezone.

The owner must restart the existing AB gateway with its approved configuration
and reopen the HMI. Read back all three endpoints to verify `writeAccess` and
current readiness. The handover assigns write-enabled gateway restarts to the
owner; the agent did not start/restart one. This reporting change does not widen
the write-enabled S9 claim or authorize controller changes.

No PLC source/declaration changed, no L5X was generated/downloaded, no controller
operation was performed, and PLC memory growth is zero. `C:/work/press68.L5X`
remains SHA-256 `E2C20374F8FC7364672E425EBC3E55CC5F6D9F81ED4894BB32366E737BA586F7`.
No Web HMI rebuild is needed. Configuration power-cycle retention, the historical
S1 clock probe and TC3 native segmented transport remain separate work.

The [machine-readable record](AB_PHASE6_D6_HEALTH_WRITE_ACCESS_2026-10-03.json)
binds source files, gate logs, binary and unchanged L5X by SHA-256, and preserves
the sanitized running-gateway baseline and mutation results.
