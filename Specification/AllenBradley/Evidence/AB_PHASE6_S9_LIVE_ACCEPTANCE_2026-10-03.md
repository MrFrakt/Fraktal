# Phase 6 S9 live acceptance — press68, 2026-10-03

After restarting the gateway and refreshing Chrome, the owner reports:
“done, looks fine now.” The reference press68 deployment's remaining live S9
verification passes. This supersedes the pending verification in the
[loop correction](AB_PHASE6_S9_FRESHNESS_LOOP_FIX_2026-10-03.md).

The exact-serial read guard confirms `7036B510`. The complete 68,472-byte
manifest is coherent and equal to the committed declaration. The deployed
release client is served through trusted HTTPS at `press.localhost`; its main
JavaScript SHA-256 remains
`0CD194DF08FD04EB7814B11FC596B12590DE2CD6C196C455E325E30FC1D99C86`.

## Live results

| Check | Result |
|---|---|
| Continuous production-repository monitoring | 60 seconds PASS |
| Complete forest updates | 121, every frame has one root |
| Detail batches | 224, bounded targeted reads |
| Link | LIVE throughout, no STALE/DOWN transition |
| Maximum update gap | 790 ms |
| Maximum snapshot round trip | 348.087 ms |
| Maximum complete sample age plus round trip | 537.647 ms, below 2,000 ms Good |
| Fresh sessions | 3/3, valid discovery and current complete samples |
| Health endpoints | healthz/livez/readyz all HTTP 200, plcReady true |
| S3 task/time/fault subset | 6/6, read-only |
| Write attempts in accepted probe | 0 |
| PLC memory growth | 0 bytes |

The probe uses the production IO WebSocket client and generic repository,
including discovery, read tiers, complete-sample polling, freshness watchdog,
mapper and background detail scheduling. Its read-only wrapper omits every
`/ConfigRev` scalar and matching metadata solely to suppress QUERY_CONFIG
mailbox hydration, and refuses all writes before transport. It does not replace
the measured values or quality. The actual Chrome UI is owner-confirmed; no
browser automation claim is made.

The first resumed probe preserved LIVE for 60 seconds but failed its own
zero-write-attempt assertion: its Status/ConfigRev-only filter missed the
root-level ConfigRev. QUERY_CONFIG was blocked by the wrapper, so no controller
write occurred. Its failed log and result are retained. The corrected filter
suppresses hydration at its trigger; the accepted retry has zero blocked write
attempts. The companion JSON embeds the final Dart probe source for reproduction.

## Qualified S9 acceptance

This closes **write-enabled S9 on the named press68 deployment**. It combines
the prior [native V3 vector 17/17 and all eleven regressions/restoration](AB_PHASE6_S9_NATIVE_MAILBOX_2026-10-03.md),
shared repository contract 75/75, the declared deployment budgets and
[expiry/quality/command-refusal tests](AB_PHASE6_S9_FRESHNESS_2026-10-03.md),
the [detail starvation correction](AB_PHASE6_S9_FRESHNESS_LOOP_FIX_2026-10-03.md),
and this live acceptance. Another station or mailbox profile still proves its
own memory fit, budgets and writable deployment; no blanket writable-binding
claim is made. Existing coherence and unsynchronized timestamp declarations
are retained. The separate historical S1 clock probe, physical retention,
TC3 native segmented transport and D6 health write-gate reporting remain separate
work. CPU/free-memory availability and other S3 platform limitations are unchanged.

No controller tag write, power cycle, download, mode change, provisioning,
clock set, fault clear, network/firmware change, gateway launch or armed regression
occurred in this verification. The owner restarted the existing gateway. Press68
remains the downloaded memory baseline, SHA-256
`E2C20374F8FC7364672E425EBC3E55CC5F6D9F81ED4894BB32366E737BA586F7`; no new import/download is needed and the four-user ceiling is retained.

The full AB suite passes 1,535 tests with a fresh bytecode prefix; root consistency
reports 0 errors/0 warnings and all 33 root tests pass. HMI, analyzer, release
build and shared contract are unchanged from the accepted source in the loop
correction record. The [JSON record](AB_PHASE6_S9_LIVE_ACCEPTANCE_2026-10-03.json) contains the complete live
timeline, sample costs/budgets, reconnect and HTTPS checks, guarded manifest,
S3 results, harness source and test-log hashes. Prior evidence is unchanged.
