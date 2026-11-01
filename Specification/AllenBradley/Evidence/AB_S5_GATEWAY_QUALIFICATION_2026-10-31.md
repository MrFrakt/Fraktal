# S5 packaged canonical CIP gateway: qualification passed

Recorded 2026-11-01T04:20:19.516894+00:00 (owner date
2026-10-31, America/Mexico_City), under standing O3. Echo 601FC87B, L81E
v38.011, 127.0.0.1 slot 0. Preparation:
[detail refresh](AB_S5_GATEWAY_DETAIL_REFRESH_PREPARATION_2026-10-31.md) and
[authorization separation](AB_S5_GATEWAY_DETAIL_REFRESH_PREPARATION_CLOSURE_2026-10-31.md).

Candidate ACD SHA-256:
95E1C514A31B06AEF528BDDC07F7D64C2336DDA6910B43663F1C01EBBA586012.
PLC source SHA-256:
979DD73CDFC0C0CBCD3348915CB6D804FCF2736DC780AEA196963E2F2105A162.
Manifest content hash:
BBA485936140CE9EE1C7693824BB06E935940A335D86A8EB2FBAD9AD35C847B6.
Exact-image Studio Capacity: 66%, 2,077,924 used / 1,067,804 available /
3,145,728 total Blocks. This image includes the two previously documented
write-revision assignment corrections, preserving the V6.10 wire contract.

The normal shipping Web/gateway package runs two instances: write-enabled
echo on port8080 and read-only echo-view on port8081. Discovery uses Symbols,
Templates and the PLC manifest, with no station declaration in the client or
gateway. Desktop unsecured CIP remains read-only. This is local Echo
commissioning evidence, not a physical-controller or CIP Security claim.

All 12 automated C1-C11/C13 cases pass: seven-module discovery and readiness;
successful login and matching authentication result; wrong-PIN refusal;
acknowledged AUTO/MANUAL transitions; native PartSlide extension and return;
configuration edit with advancing revision and exact restoration; four-bank
configuration reads; wrong-root, stale/duplicate and all 39 read-only command
refusals; gateway restart with STALE/DOWN/LIVE and no replay; final logout and
MANUAL/idle state. Both startup and delayed movement include 100-second idle
checks. The complete structured case results and refusal evidence are retained.

Two concurrent repository clients pass different detail/overview phases:
120 secondary samples, zero non-LIVE transitions, and native ACK22 unchanged.
Each client observes at least20 detail samples over20 seconds, retaining
27 history rows and two timing rows with zero row losses. This resolves the
previously recorded aging/clearing failure without extending any freshness,
source-age, proof, acquisition or retry limit. Due slow chunks now continue
between polls, each as its own bounded worker operation; controls and cyclic
samples retain the existing scheduler and fences. Failed reads are not retried.

Fresh owner Chrome C12 also passes. Exact owner reply:
"Performed now; all checks passed, logged out and tabs closed".
Native boundaries independently establish MANUAL/idle/logged out and ACK22
to ACK26, the four required login/mode/return/logout acknowledgements. The
owner additionally confirms the narrow timing card is compact and scrollable,
and history/timing remain populated for at least20 seconds without connection
flicker. Browser movement is owner-attested; the independent native movement/
return proof is automated C5. No UI action or successful checklist is fabricated.

Independent native gates pass:

- Exact oracle value/type equality on 5,264 occupied paths.
- Generic acquisition of the same 5,264 values across seven modules, with
  independent raw capture replay.
- Four configuration pages and 1,100 independent scalar comparisons.
- TASK cumulative maximum 7759 microseconds, zero overlaps,
  6261 post-download observations plus20 final samples.

Fresh offline gates pass:802 HMI tests,12 existing skips; analyzer and locked
dependencies;17 focused layout/pump/worker tests; gateway/installer tests;
74 root tests, ABspec/contracts and strict consistency; normal Web, Windows,
gateway and installer package; native profile and SDK builds; read-back,
workflow/authorization, browser, launch, read-gate and restoration checks.
Unchanged PLC inputs transfer the prior2,357 AB-suite and dual-v38 build/
read-back proofs by hash. Flutter3.47.5/Dart3.13.4 at
C:/work/fraktal-toolchains/flutter-3.47.5, RockwellSDK2.1.974.
ADS support is explicitly unavailable in this host's package because its
TwinCAT ADS SDK is absent. The12 HMI skips remain their existing hardware/live
fixture exclusions; they are not manufactured passes.

Genealogy recovery passes after one unchanged fixture retry. The SDK opens/downloads a hash-checked copy of genealogy pin
D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084;
the original is never SDK-opened. All five original host documents are restored
exactly. The first baseline fixture stops after28 completed rows at START
refused; it restores its inputs/policy and logs out. The original failed fixture
and session_result.json remain unchanged. No cause is established by the
available first-run evidence. After guarded MANUAL normalization, one unchanged
31-case retry passes with a read-only unit/access/ACK witness; all final checks,
preflight and baseline timing pass. No download, changed assertion or new
write vector is introduced by that retry. The inherited retry helper contains
session11's stale descriptive HOME-timeout/browser flags; a separate context
correction records the actual START refusal and current successful browser
gates without editing the originals. stage_exit_01.json consolidates the
successful native/owner gates and verified recovery, rather than rewriting
the initially failed session as a pass. The baseline START refusal remains an
unexplained harness follow-up for S6; no PLC/HMI cause is claimed.
Echo ends Run/not faulted, scanning, MANUAL/idle/logged out, not restoring,
with saved documents equal to live. No dumps, fault/TASK-counter clears,
clock changes, controller power/vendor-state operations or Echo hard kills.
Only the owned gateway/test/browser processes stop.

S5 exits at this Echo/package scope with the verified recovery above. Prior attempts and the original UI/data
findings remain sealed separately; none is overwritten by this success.
S6 legacy consumer migration, storage collapse, declaration-free host services,
retirement and V2 activation remain open. S7 physical/CIP Security acceptance
is deferred under O2; no hardware/production-security result is inferred.

Payload manifest SHA-256: 1EDF909CC02619EE49D2711C0707D5C8CC3D73ECAECE42C6AA4A118DDAE155F7.
No credentials, ACD/L5X, binaries, caches or browser profiles archived.
