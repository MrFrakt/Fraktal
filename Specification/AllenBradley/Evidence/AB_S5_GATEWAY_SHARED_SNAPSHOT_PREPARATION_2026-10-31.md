# S5 shared in-flight snapshots: sealed preparation

Prepared 2026-10-31T15:44:04.536115+00:00 under standing O3 for dedicated Echo601FC87B,
L81E38.011, 127.0.0.1 slot0. Original guards and mandatory rollback remain.

The [atomic/queue attempt](AB_S5_GATEWAY_ATOMIC_QUEUE_RUNTIME_FAILURE_2026-10-31.md)
passed all12 command cases but still caught five non-LIVE transitions in the
two-client prerequisite, with69 secondary samples and unchanged ACK22. The
previous late-sample refusals did not recur during the probe, but LIVE cadence
was insufficient. Chrome never opened. Independent read/scan checks, genealogy/
five-document rollback,31 baseline cases and final checks passed before edits.

Retain corrected shared tier aggregation, atomic profiles and pre-read queue
accounting. Concurrent cyclic requests now share only an acquisition already
in progress under the same installed profile generation. A profile update
forces a separate acquisition; a completed result or failure is not cached.
Each caller gets only its own processing overlap with the conservative native
age boundary (native call start plus declared native processing). A caller
joining after that boundary gets zero processing allowance. No source/leaf age,
value, type, proof, retry, freshness limit or command write policy changes.

The new concurrent-call regression failed on the old server. Tests prove one
native read for concurrent matching profiles, separate reads across a profile
change, unchanged source ages, no inherited pre-request timing, shared failure
delivery without retry, and a fresh acquisition for a subsequent explicit
request. Existing pre-read queue and post-acquisition transit tests still pass.

Fresh gates:788 HMI passed/12 existing skips,43 focused gateway/HMI tests,
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
LIVE, at least20 secondary samples and unchanged native ACK. Every rejected link event also retains phase and monotonic elapsed time.
No write is added
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

Payload manifest SHA-256:FF74FF6A72531ABD8C01F8031C17F9F264BC256B8D108DF6638414EB63AED3B3. No credentials, ACD/L5X, binaries,
caches or browser profiles are archived. Native acceptance is pending.
