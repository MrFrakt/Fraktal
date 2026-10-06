# TC3 handover preparation — 2026-10-05

Status: **runtime acceptance pending**. This is preparation and failed-deployment
evidence, not a passing TcUnit result or a full AB/TC3 conformance claim.
Source baseline: `d8946a8997dbb8b3b40afc0830e56c8520efbe59` (latest pulled
AGPL tree plus licensing documentation). Work is isolated from the user's twelve
unchanged local files in `artifacts/tc3-handover`.

## Implementation under review

- Core 0.23.0.0 / Modules 0.11.0.0, with consumer placeholders pinned.
- Optional `I_RecipeCatalog` and provider-owned persistent created records;
  inactive append preserves live recipe storage and existing indices. The local
  provider has sixteen total recipe records including seed/fallback records,
  1024-byte payloads and 64-byte root model identities. Existing 80-byte seed
  registration is retained; unrepresentable catalog identities refuse creation.
  Creation is advertised only when the root's complete PAR_CFG projection belongs
  to its registered model region. Composite recipe banks need a provider-level
  multi-record transaction; they are refused, never partially cloned.
- Immutable current-value snapshots use no saved-set slot. TC3 continuations
  require the document token, PLC session generation and exact next line; every
  snapshot replacement and intervening operation cancels the old cursor.
- Saved-set overwrite stages privately before publication; loads freeze external
  records and compare complete identity/type/revision before apply. Model sets
  create inactive models; running-model set load remains refused.
- Additive V2/V3 calendar/record types, five weekly rows, whole-calendar validation
  and candidate transactions, V1/V2 migration, finite unscheduled boundaries,
  latched targets and immutable closed history. Targets use nonnegative DINT
  configuration storage; the published latched/history count is UDINT.
- The Press composition root selects `FB_LineDataV3`; its separate object check
  passes. Manual OEE reset preserves part counts and retires the factor epoch. Changeover
  removes only its air entry condition; device/directional pressure permits remain.
- Eighteen new IEC regression tests bring the aggregate expectation to 215 tests
  / 45 suites. PressTests remains 9 / 2 and now counts fresh completed strokes
  across repeated cycles. ST/SFC/LD runtime execution is still pending.

## Checks and measured limits

TwinCAT XAE Base file version: **3.1.4026.24**, Visual Studio DTE 18,
Debug / TwinCAT OS (x64). Library installation and the six object-check solutions
have passed during preparation. Final snapshot build logs are recorded separately;
an object check is not execution of the tests. One subsequent hidden XAE
instance stalled while loading Modules; that partial batch remained failed.
The Modules-only retry passed. Core was then installed after the final snapshot
guard, and the aggregate, demos and PressTests checks passed. Compiler logs and
the Core install log accompany this report.

Modern/4024 lint: 402 objects clean. TwinCAT tools: 79 tests, one skip;
root consistency tests: 33 pass. Strict consistency: zero errors and warnings.
Flutter 3.47.5 / Dart 3.13.4: analyzer clean; **533 tests pass, seven skips**;
release web build succeeds. `main.dart.js` SHA-256:
`5eb6e69f5f35947797203e6be9490eeeb4412111a5f972c47a198b87d9cb57b6`.
Export tests kill both omitted-token and missing-continuation mutants. Native
PLC guard mutants remain unexecuted until a real TcUnit application runs.

The first complete HMI run exposed a fixture that measured startup/JIT delay
instead of the warmed poll loop. The corrected fixture brackets completed reads
and the next start; production freshness deadlines are unchanged. The full
suite then passes. The seven pre-existing skips retain their original scope.

## Runtime deployment failure

User-named target: **192.168.1.6.1.1:851**, local **UmRT_Default**.
The pre-test Boot directory is backed up outside Git at
`artifacts/tc3-target-before-tests-2026-10-05/Boot` in the original checkout.
The initial configuration was the isolated Core library wrapper, with no machine
I/O. Both attempts checked the exact target and disabled test boot autostart.
Configuration activation, native code generation and TwinCAT Run succeeded;
license status was Valid(3). `ITcPlcOnline.Login` with flags 260, then visible
regular login flags 1, left `IsLoggedIn=False`, operation state 0. Neither run
executed any test. A subsequent independent ADS read saw state Invalid and no
TcUnit symbols. The failed raw logs are retained beside this report.

The visible attempt's compiler reports data-area size 347,674,272 bytes,
highest used address 289,728,536, largest contiguous gap 57,945,736; code-area
size 1,636,160, highest used address 1,258,584 and gap 377,576. These describe that
earlier aggregate artifact, not final runtime use or a production station.
Task stack, scan cost, overlaps and final runtime fit remain unmeasured.

The existing local access provider generates two TMC warnings: `hide` prevents
persistence of `_users` and `_n`. Beckhoff documents the same restriction for
`TcNoSymbol`. See Beckhoff's [hide](https://infosys.beckhoff.com/content/1031/tc3_plc_intro/2529654667.html)
and [TcNoSymbol](https://infosys.beckhoff.com/content/1033/tc3_plc_intro/3108007179.html)
documentation. Removing symbol exclusion would expose short-PIN hashes to offline
search, so no security weakening was made. IMPLEMENTATION_NOTES §150's prior
credential-retention claim is not supported by this compiler. Credential retention
needs a separate protected persistence design and native restart/download proof.
Model/catalog, saved-set and calendar physical retention are also unmeasured.

## Remaining acceptance and repository replacement

Manually select the aggregate test PLC as Active PLC Project in XAE, confirm the
target above, Login/download and Start with boot autostart off. Read its results
with `Read-TcUnitResults.ps1`, validating 215/45; then run separate PressTests
9/2 for each rendition and the native guard mutants. Browser/TF6100/gateway,
physical safety/I/O, mirror transport and upgrade/power retention are separate
evidence scopes and no pass is claimed for them here.

The requested fresh public AGPL repository replacement has **not** been executed.
It follows the handover, as requested. Historical MIT grants and third-party
notices must be preserved even when old commits cease to be publicly reachable.
