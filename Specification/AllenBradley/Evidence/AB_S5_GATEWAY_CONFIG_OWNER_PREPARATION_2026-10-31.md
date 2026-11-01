# S5 configuration revision ownership and service scheduling: sealed preparation

Prepared 2026-11-01T03:07:50.521293+00:00 under standing O3 for dedicated Echo601FC87B,
L81E38.011, 127.0.0.1 slot0. Original guards and mandatory rollback remain.

The [native timing diagnostic](AB_S5_GATEWAY_NATIVE_TIMING_DIAGNOSTIC_RUNTIME_2026-10-31.md)
passed all12 command cases and reproduced three non-LIVE transitions,117
secondary samples, unchanged ACK22. Post-command snapshots took at most352ms
and slow chunks71ms;13 configuration-assembly calls and repeated hydration
appeared during detail activity. Independent reads/scan, genealogy/five-
document rollback,31 baseline cases and final checks passed. No owner Chrome
window ran in that diagnostic; its trace executable is not used here.

Two further defects are reproduced by failing regressions. The repository
used every /ConfigRev suffix as a module revision, including saved-set records.
It now uses revisions only at discovered module bases: canonical Status/ConfigRev
with the older direct ConfigRev fallback. Stored-record changes no longer
refetch the module manifest; real root and nested Unit changes still do.

A configuration-page RPC previously held later cyclic requests in the same
socket queue through all its upstream reads. It now uses a separate serial
configuration service queue. Prior controls still fence it; cyclic snapshots
and later controls can progress while the read-only page is pending. Writes
retain connection order and the global serializer. Decode/size/protocol/scope
checks retain one owner. No read-only or command validation is bypassed.
The76 focused tests cover both revision spellings, stored-record noise,
nested Unit invalidation, cyclic progress and prior/later control ordering.

Retain corrected shared tier aggregation, atomic profiles, conservative
per-caller queue accounting and in-flight snapshot sharing. No value/type,
source/leaf age, quality, proof, freshness/acquisition/retry or write-policy
limit changes. The normal shipping package is rebuilt without the diagnostic
native worker flag. Native improvement and owner C12 remain unproven.

Fresh gates:793 HMI passed/12 existing skips,76 focused repository/gateway tests,
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

Payload manifest SHA-256:C826D95E995C8F1FDD6F3F6835D07042740DA4E5C44217FD8C73D096E503E9C9. No credentials, ACD/L5X, binaries,
caches or browser profiles are archived. Native acceptance is pending.
