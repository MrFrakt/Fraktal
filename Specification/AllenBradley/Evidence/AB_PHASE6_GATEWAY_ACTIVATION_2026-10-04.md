# Phase 6 — AB gateway activation and D6 live readback

Date: 2026-10-04 (America/Bogota).
Result: **the concurrent AB handler is active and D6 live health readback passes
on press68. Parameter sets acceptance in Chrome still awaits the owner's result.**
This record supersedes the activation-pending status in the earlier
[configuration repair](AB_PHASE6_CONFIGURATION_REGRESSIONS_2026-10-04.md) and
[D6 implementation](AB_PHASE6_D6_HEALTH_WRITE_ACCESS_2026-10-03.md) evidence;
those observations remain unchanged.

The owner confirmed restarting the gateway with “done, whats next”. Read-only
process inspection found the loopback 8099 listener PID 16300 started at
2026-10-04T15:22:11.4834897Z, after the configuration fix commit 41c12f7.
The agent did not start or restart a gateway. Native reads used the existing
running gateway and its expected-serial guard for 7036B510 at 192.168.100.89.
No new writable session or native fixture was launched.

A read-only probe sent a snapshot and an unsupported inert method back to back
on the same WebSocket, three times, retaining only reply IDs, errors and timing.
Before the owner's restart, the inert replies waited behind the snapshots:
204.50, 207.59 and 204.13 ms. After restarting, those replies arrived first at
1.02, 1.46 and 1.95 ms while the snapshots completed at 211.00, 210.73 and
208.77 ms. This establishes that the running handler now multiplexes requests.
It does not execute LIST_CONFIG_SETS or establish browser dialog acceptance.
The focused fixtures separately check that a held mailbox command does not
block complete snapshots, and preserve command serialization, draining and
queued cancellation. All four fixtures pass in 0.408 seconds.

Immediately after fresh complete native reads, `/healthz`, `/livez` and `/readyz`
all returned HTTP 200 and `plcReady: true`. Every route returned the same block:

```json
{"writeAccess":{"enabled":true,"roots":["Press"],"allRootMailboxes":false}}
```

The last complete read reported by all three routes was
2026-10-04T15:27:43.858263+00:00. This closes D6's AB live readback for the approved
Press write scope on this bench. The block describes configured command access;
PLC permissions and freshness remain separate. No token or credential was
returned or recorded. An earlier idle health observation had expired complete
data; the fresh read restored readiness without changing expiry limits.
The generic TC3 gateway retains its prior compiled/fake-client evidence only.

Required commit gates pass: full AB discovery 1,541 tests, root consistency
0 errors / 0 warnings, and root suite 33 tests. No implementation source changed
in this verification. The prior deployed Web release remains unchanged; no new
HMI build or deployment was needed. PLC memory growth is zero. The loaded
press68 artifact remains SHA-256
`E2C20374F8FC7364672E425EBC3E55CC5F6D9F81ED4894BB32366E737BA586F7`;
no import or download is pending, and the four-user ceiling remains.

The owner has been asked to hard-refresh Chrome, open Configuration → Parameter
sets and leave it open for at least ten seconds. That result is pending. The
latest owner screenshot already showed the restored model dropdown, but this
read-only probe does not replace full browser acceptance. Configuration/set
physical retention, other account retention, the historical S1 clock probe and
TC3 native segmented transport remain separate work. Admin credential retention
keeps its prior owner-confirmed evidence.

No tag writes, native regression, download, power cycle, clock write, mode change,
fault clear or firmware/network operation was performed by the agent. The owner
restart confirmation authorizes none of those operations. This record does not
widen S9 beyond the already verified named press68 deployment.

The [machine-readable record](AB_PHASE6_GATEWAY_ACTIVATION_2026-10-04.json) binds
the sanitized before/after probes, health readback, process observation, source
files, gate logs and unchanged PLC image by SHA-256.
