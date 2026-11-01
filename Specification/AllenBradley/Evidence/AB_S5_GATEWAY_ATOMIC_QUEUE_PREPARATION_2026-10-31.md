# S5 atomic profiles and gateway queue accounting: sealed preparation

Prepared 2026-10-31T15:16:04.541573+00:00 under standing O3 for dedicated Echo601FC87B,
L81E38.011, 127.0.0.1 slot0. Original guards and mandatory rollback remain.

The [shared-tier attempt](AB_S5_GATEWAY_TWO_CLIENT_TIMING_FAILURE_2026-10-31.md)
passed all12 command cases, but its new read-only two-client prerequisite
caught nine non-LIVE transitions, with68 secondary samples and unchanged ACK22.
Chrome never opened. Independent read/scan gates, genealogy/five-document
rollback,31 baseline cases and all final checks passed before new source edits.

The shared merge correction is retained. Two additional regressions fail on
the prior code and pass after correction: gateway clients publish both tier sets
in one existing setReadTiers RPC; the server uses the upstream atomic profile
operation when available. This removes intermediate live promotions during a
slow/excluded update. Invalid overlap refuses before publishing a new profile.

The gateway starts a monotonic stopwatch when each request arrives, before
the connection's serial queue. For snapshots it adds only the wait before the
upstream snapshot call to the existing responseProcessingMs. Source/leaf ages
and the upstream document stay unchanged. A separate test proves delay after
the native sample was acquired remains transit, rather than being hidden by
subtracting the upstream call's entire round trip. This corrects envelope
composition without increasing Good/expiry, proof, acquisition or retry limits.
Writes, ordering, serial pinning and no-replay policy are unchanged.

Fresh gates:785 HMI passed/12 existing skips,40 focused gateway/HMI tests,
gateway package tests, analyzer, locked dependencies,74root tests, AB
spec/contracts and strict consistency. Clean Web/Windows/gateway/installer
build, fresh SDK/profile builds, artifact/read-back, authorization/workflow,
launcher/browser/window/readiness and simulation/read-gate checks pass.
The host lacks the ADS SDK, explicitly excluded from its package.
Flutter3.47.5/Dart3.13.4; RockwellSDK2.1.974.

All385 unchanged PLC inputs retain2357 AB tests, dual-v38 build/read-back and
Capacity66% (2077924used /1067804available /3145728Blocks) by hashes.
Unchanged ACD95E1C514A31B06AEF528BDDC07F7D64C2336DDA6910B43663F1C01EBBA586012;
source979DD73CDFC0C0CBCD3348915CB6D804FCF2736DC780AEA196963E2F2105A162;
manifestBBA485936140CE9EE1C7693824BB06E935940A335D86A8EB2FBAD9AD35C847B6.

Scope: fresh guards/preflight/backup, guarded MANUAL if needed, Program/
download/Run, five-document restore and unchanged12 command cases, including
both100-second idle checks. Repeat the same read-only two-client prerequisite:
overview/detail demand alternates20seconds per view, both links must remain
LIVE, at least20 secondary samples and unchanged native ACK. No write is added
and no previously recorded link drop is ignored. Stop writers on first failure;
independent configuration/equivalence/acquisition/scan still run.

Only after those checks pass, capture a fresh nonce/native boundary and open
the normal packaged Web HMI in an owned Chrome profile. Existing read-only CDP
observation records public RPC timing/counters, connection-stage enums and
whitelisted freshness numbers, with no PIN/User/Text/error payloads or browser
profile archived. Twelve redaction/authorization tests and a real-Chrome stub
smoke pass without PLC access or UI actions. No click, login or command is
automated. The owner alone performs current two-tab C12.

The two-hour owner availability, forward ACK, MANUAL/idle/logout, source age,
quality and write guards remain. Finally restore only a hash-checked copy of
the protected genealogy pin, five original documents,31 baseline cases and
final checks/preflight/timing. No fault/TASK clears, clock changes, power/vendor
state edits or Echo hard kills. No native improvement, C12/S5 exit or physical/
CIP Security acceptance follows from preparation. All inputs are hash-bound.

Payload manifest SHA-256:96B38C0BF564582F051AF31E96649169042D4E2BB76C9EE56A2E2335DDE409E9. No credentials, ACD/L5X, binaries,
caches or browser profiles are archived. Native acceptance is pending.
