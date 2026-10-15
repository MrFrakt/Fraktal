# Fraktal/TIA access/session prototype - 2026-10-11

The reference S7-1500 candidate compiles warning-free, passes 122 native access
checks and 120 current routing regressions, and accepts a real application login
through the generic HMI. The rendered Instant button increments the independently
read native command counter exactly once. This is a prototype slice, not complete
Core conformance. Raw runs, including failures, are preserved in
[TIA_ACCESS_SESSIONS_2026-10-11/](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_ACCESS_SESSIONS_2026-10-11).

## Scope and target

- TIA Portal V20, S7-PLCSIM Advanced7 with its API5 compatibility library.
- Owner-created instance Fraktal adopted from stopped CPU1500_Unspecified,
  Softbus/192.168.0.1 into isolated TCPIP/169.254.212.49. Physical mappings remain
  zero. Download establishes CPU1516; the second configured CPU interface is
  192.168.1.1 with no physical mapping. The instance is preserved and left RUN.
- VM memory was raised by the owner to16GB. Headless TIA operations completed;
  neither a Visual Studio repair nor memory as the crash cause is established.
- Approved driver remains candidate_s11_enumeration, SHA256
  e455ee93e616c4788001b07830164da92b72e3817d6a90c90e03d98937026f33.
  No rebuild/whitelist, physical-controller change, staging, commit or push.
- Existing station certificate/pin and process-data Web API principal fraktal,
  mask24, remain separate from the test application principals. PINs are random,
  DPAPI-protected on the workstation and provided only by environment names.
  PLC fixture sources contain salt/hash bytes; no PIN is embedded or logged.

## Implemented behavior

Generator0.6 owns access cyclic/finish calls and blocks authored module writes
or assembly calls to the authority. One private local user table has Core
MAX_USERS capacity. Core ST_UserRecord fields, SHA constants/initial state and
PIN_HASH_ROUNDS are authority inputs bound into generation. Native SHA vectors
for empty, abc,32-byte and48-byte inputs match Python hashlib. The Core-compatible
hash is SHA256(salt16 || PIN), then256 SHA256(previous32 || salt16) compressions.
One subsequent compression runs per active scan. Candidate storage has no secret.

LOGIN acknowledges consumption, then publishes LoginBusy, LoginResultSequence,
CurrentUser, CurrentLevel and LoginFailed. Invalid credentials preserve a valid
prior session. Root sessions are independent. Explicit logout/startup cancel
pending checks; deterministic cancellation and supersession prevent a stale grant.
Idle expiry drops the old session without discarding a new credential attempt.
Release/config queries and background reads do not refresh activity. Accepted
authenticated mutations do. Session generation and manifest revision update at
session/policy boundaries so clients can refresh their projection.

Policy edits consume the same pure ACCESS_POLICY release predicate. Levels/gate
indices are validated, ACCESS_POLICY cannot be raised above the active level,
and idle timeout is bounded to seven days. Private hashes/salts/candidates refuse
native reads200; published authority/policy writes refuse205. Secret-clearing
checks record only booleans. Access traces contain action, active user and canonical
path; manual records retain the selected target. They use the existing bounded
ST_Diagnostic trace, not the full MESSAGE/alarm history contract.

## Measured gates

| Gate | Result | Raw record |
|---|---|---|
| Preserved-image recovery | software/hardware0 errors0 warnings, download and RUN |04,05 |
| First authentication pass |116/116 |12 |
| Current native authentication |122/122, including restart, cancellation/supersession |29_access_native |
| Current routing regression |120/120 |19,20 |
| Auth fixture native export |129 blocks/42 interfaces canonical and access flags equal |25,28 |
| Native export/reimport/export |129 sources equal; compile0/0 |31,35 |
| Production compiler-only image |125 blocks/42 interfaces equal; compile0/0 |32,37 |
| Generator/tool suite |122 tests pass |27_tools |
| Source lint and consistency |0 findings;33 consistency tests pass |33 |
| HMI suite |569 pass,1 skip, exit0; captured console result in preservation metadata |39 |
| HMI analysis |no issues |38 |
| Native HMI widget |pass; real operator login, wrong-PIN rejection, peer isolation,492 entries/24 modules, button counter delta1 |34,36, hmi-forest.json, hmi-manual.png |

The authenticated HMI gate uses the normal OPERATOR operations display policy.
The older manifest-only test retains its opt-in NONE preference for its original
fixture. Production gateway/session/repository/widgets are used; the transport
wraps every native write in an exact isolated-target guard. During disposal,
a pending read-only manifest query is cancelled when the client closes; the test
completes with no widget exception. The gateway is stopped after the run.

## Preserved failures and corrections

02 fails the original CPU1516 guard on the empty unspecified instance.03 refuses
TLS trust because the runner's top-level flag did not reach the download step.
The corrected runner injects explicitly requested trust only into the guarded
in-memory download substitution;04 succeeds. The bootstrap exception is explicit,
limited to stopped owner Fraktal on the exact virtual target. Later guards require1516.

06 reports three declaration errors: FC constant array and width-qualified string
inputs.07 rejects CASE over a string.08 rejects untyped character literals compared
with WString. The corrected source uses generated TEMP constants, generic string
inputs with PIN bounds, equality branches and explicit WSTRING literals.09 compiles0/0.
The first canonical check catches TIA expanding grouped declarations; final source
emits separate declarations and compares exactly. The first repo lint catches a
stale version in the checked-in structural example; regeneration changes only its
three version comments and manifest, proved byte-equal after that substitution.
Failed log27_lint is preserved;33_lint is the passing result.

## Evidence availability and remaining work

At continuation, this checkout has five older reports and129 older raw files (134 files total),
but twelve newer reports referenced by the handover/docs and all18 previously
reported SHA manifests are absent.22 records that inventory and current hashes.
The earlier work directory still records a previous21986-binding audit; this run
cannot independently reverify absent files. Missing records are not reconstructed
or represented as verified. The remaining older files are preserved unchanged.

User-table/policy persistence, local user CRUD/provider substitution, data-class
policy, full MESSAGE/alarm lifecycle and sinks, concurrent mailbox writers,
configuration/recipe/retention, state/diagnostic services, complete action/frontier
releases, full sequence/GRAPH integration and the press without power remain open.
The current application test table is volatile, provisioned from private hashed
fixture data at Initial_Call. Production generation ships fully open thresholds
and provider disabled. No S7-1200 authentication or physical S7-1500 result is claimed.
The shared command-kernel bytes remain unchanged; the earlier238/55 lifecycle
assertions are historical scope, not rerun as a native gate here.

Current runtime project/image:
`%LOCALAPPDATA%/Fraktal/TiaStations/Access_Runtime_20261011/FrkS12/FrkS12.ap20`.
`Access_Verify_20261011` holds the separate production compiler image.
The owner Fraktal instance remains RUN, application sessions logged out, no pending
login. The source/evidence/KB updates are available for review.
