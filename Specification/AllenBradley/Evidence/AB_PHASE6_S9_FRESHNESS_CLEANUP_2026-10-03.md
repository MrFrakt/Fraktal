# Phase 6 S9 freshness — initial-connection cleanup

Date: 2026-10-03. Additive follow-up to the [freshness record](AB_PHASE6_S9_FRESHNESS_2026-10-03.md);
its historical source/test/deployment facts remain unchanged. The [JSON](AB_PHASE6_S9_FRESHNESS_CLEANUP_2026-10-03.json)
pins the two changed HMI files and final logs/build.

Final review found that rejecting an already old first sample could close the
transport while leaving the repository's expiry timer alive until its deadline.
Initial failure and normal disposal now share one cleanup path, cancelling both
timers and closing the client/streams. A widget-harness test rejects pending
timers at test exit and covers the failed first connection.

Final shared TC3/AB production contract suite: **71/71**. Full HMI: **459 passing,
7 expected environment/fixture skips**. Analyzer clean; release Web build passes.
One prior shared run completed 70/71 because the recovery fixture checked after
a fixed 70 ms sleep under concurrent build load. It now waits for the actual
LIVE stream event with a two-second bound. The expiry limits and all stalled-read
failure assertions are unchanged. The failed log is retained in the JSON.

All AB/gateway/PLC sources and budget values remain as tested in the first
record: 1,535 AB tests, 104 focused tests, five semantic mutants, read-only native
cost/S3 checks, byte-identical press68/template and **zero controller growth**.
This follow-up made no controller write and did not restart/start a gateway.

The final Web output is served from the actual Caddy root. Authenticated HTTPS
GETs of main JavaScript, bootstrap and index return 200 and match the tested
files, preserving hostname/SNI and TLS verification through loopback. Final
main JavaScript SHA-256: `54C6C3060000A4BD94A4C4B43F36C2873A7F0DDD289FE061CE1C20713D9154EB`.
The first freshness build is retained at `C:/work/press68_freshness_web_backup_02`;
the preceding client remains at backup 01. Proxy configuration/credentials are
unchanged.

**Full S9 remains open for live activation/verification.** The existing gateway
still predates the source. The owner restarts it and hard-refreshes Chrome,
then verifies the live freshness envelope read-only. No additional PLC import
or download is needed; physical retention and the previously identified
transport/time-probe debt remain separate.
