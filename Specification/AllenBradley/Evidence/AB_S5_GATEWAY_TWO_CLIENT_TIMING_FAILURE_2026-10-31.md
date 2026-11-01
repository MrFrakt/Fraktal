# S5 two-client timing failure caught before Chrome; genealogy restored

Recorded 2026-10-31T15:02:43.927264+00:00 under standing O3,
following [sealed preparation](AB_S5_GATEWAY_SHARED_TIER_PREPARATION_2026-10-31.md).
Echo 601FC87B, L81E v38.011, 127.0.0.1 slot 0. Unchanged candidate ACD
95E1C514A31B06AEF528BDDC07F7D64C2336DDA6910B43663F1C01EBBA586012, Capacity 66%.

All12 C1–C11/C13 cases passed, including both100-second idle checks,
PartSlide movement/return, four independent configuration pages/1100scalars,
refusals and restart/no replay. The shared tier merge correction is present.

The added read-only two-client prerequisite failed before Chrome opened.
It collected68 secondary samples over two20-second detail/overview phases,
with nine non-LIVE transitions across the two repositories. Native ACK stayed22;
no command was sent by this probe. The complete failed profile result is kept;
no owner C12 or browser trace ran and no pass is manufactured.

The existing application trace records four late-sample refusals: snapshot waits
of approximately1.96–2.11seconds, source ages0.18–0.21seconds, declared upstream
processing0.26–0.56seconds, and inferred transit1.45–1.83seconds. Shared tier
logs still expose intermediate profiles during separate slow/excluded updates.
The shared merge fix alone is insufficient. Investigate/verify atomic profile
installation and account for gateway queue time before native reads; source
ages, Good/expiry, acquisition proofs, retries and write policies stay fixed.

Independent reads passed: 5,238 occupied paths, seven-module acquisition and raw
capture replay, four configuration pages / 1,100 scalar comparisons. TASK
cumulative maximum was 7,759 µs, zero overlaps over 3277 monitored samples
and 20 final observations. These independent successes do not manufacture a
successful combined session: S5 remains open.

The automatic finally path downloaded a hash-checked copy of the genealogy
pin, restored all five original documents, passed 31/31 baseline cases and all
final checks, preflight and baseline timing. Echo ended Run/not faulted,
scanning, MANUAL/idle/logged out, not restoring, saved documents equal to live.
No dumps, fault/TASK clears, clock changes, power/vendor-state operations or
Echo hard kills. Only owned gateway/test/browser processes stopped.

Payload manifest SHA-256: 4BDB114DD681AFC1B3A929A9FDBE9C5DABFB0B9AAF5440847830D423A50C29BF.
No credentials, ACD/L5X, binaries, caches or browser profiles are archived.
