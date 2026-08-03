# Fraktal objectives and conformance audit

Snapshot: **2026-08-02**. Scope: the Fraktal standard implementation against Part I,
the TwinCAT binding, and the normative HMI/transport contracts: Core/Modules
libraries, Flutter HMI, Web gateway, aggregate tests, CI, and repository state.
The Demo and Press Demo applications are inspected only as internal integration
fixtures for the reusable framework. Press Demo is a Fraktal feature-testing
bench, not a real machine project, production reference, conformance target, or
production-machine acceptance evidence.

This is an implementation audit, not a release certificate. Direct TwinCAT XAE
builds of Core `0.4.0.0`, Modules `0.3.0.0`, and Press Demo are current and clean.
After the externally completed Tests/Examples split, both isolated test projects
also pass fresh x64 `CheckAllObjects`: the Core/Modules runtime gate is **84/84
tests across 26 suites** and has been repeated cleanly on an isolated Windows 10
x64 VM runtime. The separate Press integration gate is also green: **8/8 tests
across 2 suites**, for a complete **92/92 tests across 28 suites**. The Press Demo
testing bench is currently running on the local runtime as an integration sanity
check. Live TMC/OPC UA capture, packaged gateway measurement,
and cabinet/site evidence remain release or deployment gates, not missing
framework behavior.

Status: ✅ objective substantially met · 🟡 material gap or unverified claim · 🔴
objective contradicted.

Work-package status (§5): **DONE** = implemented *and* its stated exit evidence
produced. **SOURCE-ONLY** = implementation complete and reviewed, but the exit
evidence (TwinCAT compile, TcUnit execution, live acceptance) has not been
produced yet. The distinction is deliberate: a second review found the
conformance linter marked DONE while it had never been executed against the
repository, and — once run — reported six violations. Source-complete is not
verified; the scoreboard must not conflate them.

## 1. Objective scorecard

| Objective | Status | Current verdict |
|---|---:|---|
| O1 Low development and maintenance effort | ✅ | Lifecycle, rollup, timing, release reports, HMI mailbox and four-structure contract are centralized. Passive monitor CMs now use the same physical contract instead of creating a status-only exception. |
| O2 Easy to learn | ✅ | PLCopen vocabulary, one tier model, application-owned ST sequences, and data-driven HMI remain coherent. The defensive-coding rule was clarified to require semantic fail-safe paths rather than empty `ELSE` boilerplate. |
| O3 Diagnosable by construction | ✅ | First-out, awaited-module/condition walk, qualified paths, alarm lifecycle, HELD, decision audit, controller/clock health, reusable tower status, live HMI alarm hydration, generated reason rationalization, and the fixed host-event projection are implemented. Target execution remains release evidence under G1, not a missing diagnostic contract. |
| O4 Reusable, recursive, scalable | ✅ | Recursive composition, active topology lengths, configuration manifest, direct/Web read tiers, bounded targeted reads, multi-client-safe gateway aggregation, and demand-gated diagnostics are implemented. A deterministic 4,000-path/four-client gateway test proves traffic follows the consumed surface; packaged native-transport measurement remains release evidence. |
| O5 Flexible data and connectivity | ✅ | Provider and transport seams, ADS, OPC UA, Web gateway, local recipe/carrier providers, and simulated byte channels are real. TF6310 TCP and remote providers are explicitly claimed optional deployment profiles, so their unqualified adapters do not reduce base conformance. |
| O6 Simulatable | ✅ | HAL separation, simulated repositories/plants/channels, and hardware-free suites are present. Physical and simulated press selection remain composition-root concerns. |
| O7 Safe | ✅ | Safety authority stays outside the standard PLC; release loss withdraws outputs, force is explicit/fail-closed/output-only, and no control self-resumes. The Core/Modules safety, two-hand, power-group and control-domain fixtures are included in the green 84-test runtime gate; the internal Press bench's 8 integration tests are also green. Neither result is physical-machine safety validation. |
| O8 Portable | ✅ | Platform-neutral Core and TC3 binding remain separated; transport/domain contracts do not depend on the Flutter platform. Only the TC3 binding is implemented, which is consistent with the stated scope. |
| O9 Engineering discipline | 🟡 | Version pins, conformance lint, XML/project ownership, generated contracts, and split test gates are coherent. The licensed CI stub is replaced by a real hidden-XAE object-check gate plus fail-closed TcUnit-summary/JUnit conversion; both projects pass it locally. A licensed self-hosted runner and isolated-runtime hook still need to be registered before this becomes a required hosted check. |
| O10 Industrial robustness | 🟡 | Bounded data, validate-before-load, fail-closed authorization, acknowledged writes, reconnect/no-replay, recovery reset, decision timeout, health/time supervision, bounded Web reads, and 84 green PLC tests are strong. The separate Press 8-test run, packaged real-transport measurement, and live OPC UA/deployment acceptance remain open. |

No objective is fundamentally contradicted, but the repository as a whole is **not
yet entitled to an unqualified Fraktal-conformant release claim** because several
Part I `shall`s and the release verification gate remain open.

## 2. Permissions and policy audit

### Verdict

The HMI mutation path is now source-level aligned with §7.7/§7.8: the Unit mailbox
is the single remote entry, the PLC is authoritative, denials fail closed and are
audited, accepted privileged mutations rearm the session and are audited without
secrets, and the UI either acts or explains. Direct writes to arbitrary PLC data
were not introduced.

| Surface | Authoritative gate/result |
|---|---|
| Config manifest/read | `DATA_READ`; polling is pure and never keeps a session alive |
| Config and OEE writes | `DATA_WRITE`; root ownership checked; concrete config resolver currently rejects by default |
| Manual commands and fieldbus force | `MANUAL`; selected root, MANUAL mode and idle Unit checked; force additionally needs explicit PLC `Forceable` capability |
| Model/changeover | `CHANGEOVER` |
| Mode | `MODE_CHANGE`, including the running-mode shield in the release explanation |
| Start/stop/run style/step/hold/decision | `START_STOP`; decision option and active prompt are revalidated |
| Alarm reset | `ALARM_RESET` |
| Shelve/unshelve | `ALARM_SHELVE`; event identity is `SourcePath + Description` and ambiguous matches reject |
| Access-policy/timeout edits | `ACCESS_POLICY`; invalid ordinals and >7-day timeouts reject; the policy cannot be raised above the active session and strand retained configuration |
| Control power | `POWER_CONTROL`; acknowledgement follows the PLC authorization result rather than an optimistic request pulse |

Additional corrections made by this pass:

- Source PIN literals were replaced by deployment-owned persistent, OPC-UA-hidden
  commissioning values. Empty values register no account.
- Idle timeout now means time since successful login or the last accepted
  authenticated mutation; reads and release polling do not rearm it.
- `ScopedPlcRepository` derives fieldbus ownership from the channel's exact
  `ModulePath`; it no longer falls back to the first visible root.
- Custom module controls now honor the panel's optional stricter manual/reset
  floors, matching the standard controls.
- HMI language/customization administration is ADMIN-only; policy editing is
  selected-root-specific and mailbox-serialized.

One deliberate boundary remains: ordinary OPC UA history values are published
data. `ALARM_HISTORY` controls HMI visibility, while OPC UA server roles are the
confidentiality boundary for a non-HMI client. If per-session PLC-side history
confidentiality is required, history must move behind a bounded paged mailbox
like the config manifest; a UI policy cannot secure a raw browse by itself.

## 3. Specification-to-implementation findings

### Conforming or substantially implemented

- Three-tier containment and root forest; no application super-root.
- Inherited PLCopen lifecycle and Execute-drop reset; concrete hook overrides
  inspected in this snapshot call `SUPER^` as required (with the documented
  `OnModeExit` exception).
- Qualified identity, deployed-root publication markers, implementation-reference
  exclusions, and generic `Status` discovery.
- Four-structure contract on every shipping concrete CM/EM/Unit, including the
  passive digital-input and air-pressure types added in this pass. All 14
  `*ParCfg` records found by the source scan put `SchemaVersion : UINT` first.
- Transactional recipe provider, composite prepare/commit/abort, mode/model
  identity, release/report equivalence, first-out rollup, HELD and recovery reset.
- Application-owned Press mode chains extend `FB_SequenceBase`; the scan found
  `_step`, `_retVal`, and `M_Advance` usage in every shipped chain.
- HAL ownership: reusable Core/Modules code contains no Press raw-I/O reference;
  the project Hardware Driver is the sole authored POU that accesses
  `GVL_PressIO`.
- Generic HMI discovery, root scoping, quality-aware custom controls, narrow
  acknowledged mailbox writes, live alarm/OEE/nameplate/safety/health hydration,
  reconnect gate and no queued replay.
- Explicit fieldbus force capability defaults false. No application currently
  marks a channel forceable or supplies a force resolver, so the production HMI
  exposes no force button rather than advertising a non-functional/unsafe path.
- Library compatibility pins now use Core `0.4.0.0` and Modules `0.3.0.0`.
  Core's minor steps cover the append-only decision/configuration capability and
  rationalization/host-event contracts; observable changes no longer masquerade
  as rebuild revisions.

### Material open gaps

**G1 — Release proof is partial.** The complete split runtime program is green:
92/92 tests across 28 suites (Core/Modules 84/26 plus Press integration 8/2).
Both rearranged test solutions also
pass fresh x64 `CheckAllObjects`. The repository now contains an executable hidden-
XAE CI build gate and a fail-closed TcUnit-log→JUnit validator instead of a failing
placeholder, and both runtime results plus artifact hashes are archived. Remaining:
register the licensed self-hosted runner/runtime hook and make these implemented
checks required in hosted CI. Live transport and deployment-profile acceptance
remain separate release evidence.

There is no longer an open G4 implementation contradiction. The standard now
states the enforceable authority split already exercised by the internal Press bench:
runtime slave count/order/state/link and configured-identity mismatch come from
`FB_EcBusHealth`; approved channel/tag/scaling/module semantics come from the
project engineering catalog; live values come from the sole Hardware Driver/HAL;
and `FB_IoTopologyPublisher` validates the bounded join. Generic live CoE/PDO
channel inference is an optional vendor-specific adapter because it cannot infer
approved electrical tags or Fraktal ownership. `FB_EcFieldbusScanner` remains a
fail-closed compatibility skeleton, not the default base profile. Force remains
an explicit per-output project capability and no shipped fixture enables it.

### Test-fixture boundary

The Press Demo is not a real project and is not an additional framework gap. It
is an internal feature-testing bench for composition, sequencing, release
ownership, diagnostics, recovery, traceability, control domains, and HMI
discovery. Its simulated mechanisms and 8-test gate are framework integration
evidence only. Its illustrative physical-I/O and control-circuit data are
deliberately excluded from the objective score and must never be presented as
machine commissioning, SAT, safety validation, or a production reference.
Optional hardware-in-the-loop work is a separate adapter qualification.

## 4. Gaps closed during the audit

The following findings were corrected in implementation and/or specification and
are not part of the remaining G1–G10 backlog:

- Centralized and hardened PLC/HMI permission paths, persistent policy editing,
  idle semantics, accepted/denied audit, stable shelving identity, exact root
  scoping, and act-or-explain behavior.
- Added explicit fail-closed `Forceable` contract end to end.
- Removed source credential literals in favor of hidden deployment data.
- Restored the physical four-structure contract for passive monitor CMs and put
  air-switch qualification time in `ParCfg` with the existing 500 ms default.
- Added reusable model-preset coverage for `FB_Iv3VisionCM` and
  `FB_Matrix220CM`; subsequent decision/configuration/health/tower/host additions
  bring the aggregate source to 92 `TEST(...)` cases across 28 suite types.
- Corrected TwinCAT semantic versioning and current pins to Core `0.4.0.0` and
  Modules `0.3.0.0`.
- Reconciled three specification/implementation mismatches: semantic fail-safe
  conditionals (guard returns are valid, empty `ELSE` noise is not required),
  one active decision slot per root instead of an unnecessary mandatory queue,
  and §7.1 interlock loss with §6.1's explicit HELD-versus-fault classification.
- Corrected the implementation note for concrete FB bodies: the enforceable TC3
  invariant is one inherited `Cyclic();` statement and no application logic.
- Closed G2 with a central one-slot decision resolver: idempotent requests,
  overlap rejection without ring flooding, validated operator/default choices,
  monotonic timeout, atomic clear and distinct domain audit events. Added TcUnit
  coverage for operator, timeout, overlap, invalid-default and withdrawal paths.
- Closed G3 with the §3.10.2 typed capability manifest. Missing/duplicate
  authority fails closed; the HMI re-resolves key/revision/type/domain/state
  before the acknowledged mailbox write; the PLC owning handler repeats the
  checks. Unit mode policy is the first framework-owned registered handler and
  now has versioned persistent backing. The follow-up audit also closed the
  manifest's missing static projection: nameplate, stall-time, alarm metadata,
  catalogs, model lists and mode policy are all actually exported.
- Closed G6 at source level with `ST_TimeQuality`, one PLC-wide quality authority,
  timestamp-adjacent quality flags, `FB_TcSystemHealthProbe`, and the reusable
  `FB_SystemHealthPublisher`. Fault-injection TcUnit source covers time-sync loss
  and auto-reset; live controller/DC/PTP evidence remains part of P0.
- Closed G7 at source level with the reusable machine-state/severity/decision
  mapping, semantic `SignalTower` output, MANUAL-gated append-only lamp-test
  mailbox request, bounded self-clear, and truth-table/TcUnit plus HMI tests.
  Physical output checkout is deliberately deployment evidence.
- Closed G9: the linter now checks the four-record/schema-first
  contract, enum parity, inheritance/body/hook-super invariants, semantic
  fail-safe `CASE ELSE`, sequence ownership, containment, reason collisions,
  compile-list coverage and deployed-root publication. Positive/negative fixtures
  are present. This delta adds parity bindings for `E_Category` and
  `E_HostEventKind`; the fresh real-tree run is clean in both profiles.
- Closed the live-facet projection gap found during the second audit. Sparse
  active alarms, newest-first history, rationalization data, timestamp quality,
  OEE/trends, part results, nameplate, safety and control-power now hydrate from
  transport-neutral snapshots. Cycle/OEE rings now preserve chronological order.
- Closed G5 at source level. The gateway now exposes revisioned discovery,
  compact-index read tiers and bounded targeted reads; read roots apply to every
  read surface and shared-session tiers use the conservative intersection of all
  connected clients. The IO/Web gateway clients chunk and merge bounded reads,
  and reconnect restores tier intent without replaying writes.
- Closed the §8.8/§8.9 reason projection with one deterministic generator over
  the authoritative Core enum, registered Core/Modules reason bands, and the
  symbol-keyed rationalization registry. Exact coverage, duplicate rejection,
  generated PLC/HMI freshness, English fallback, metadata authority, and
  preservation of unknown PLC diagnostic text are tested.
- Closed G8 at source level with the fixed ten-kind `ST_HostEvent` vocabulary,
  bounded per-Unit OPC UA ring, timestamp-quality/verdict/reason shape, inherited
  part/mode/changeover/NOK production, named tool/material seams, optional
  `I_HostEventSink`, HMI hydration, and source tests. External historian/MES
  delivery remains a deployment adapter, not a missing fixed framework surface.
  The final audit also unified carrier-backed and carrier-free NOK capture:
  `CountNok(Reason)` now refuses `NONE` and atomically emits the attributed fixed
  event, with an empty `PartUid` only when traceability is not configured.
- Resolved the previously untracked §8.10 scope mismatch in the specification.
  Shelving, rationalization, event retention and MOC remain base requirements;
  long-window chatter/flood KPIs are now an explicitly claimed
  Alarm-performance profile owned once per station/line or historian. This avoids
  duplicating rolling-window state under every root while preserving complete
  event history, control behavior, and a testable ISA-18.2 deployment gate.
- Repaired and then separated the rearranged test ownership. The Core/Modules
  manifest lives under `Tests/`; the two Press suites live beside the example in
  `Examples/PressDemo/PressTests.plcproj`. Every compile path is downward from its
  owning manifest, the Press sources are linked rather than copied, and both gates
  pass fresh x64 `CheckAllObjects` in separate hidden XAE processes.
- Closed the direct-interface drift found by the aggregate compiler:
  `FB_DeviceConnectorBase` now supplies the `M_ReleaseCommand` and `HoldActive`
  members inherited through `I_DeviceConnector EXTENDS I_Module`, with neutral
  connector semantics and a concrete-probe regression. Core and Modules rebuild
  cleanly in dependency order and aggregate object checking is clean.
- Closed G10 through the externally completed repository-baseline work recorded in
  commit `87cad29`: Git recognized 252 renames, ignored machine/build artifacts
  without hiding the application-owned `Release/` source folder, and a clean clone
  reproduced PLC lint/XML/compile-path plus HMI analysis/test results.
- Closed G4 by correcting an over-specified discovery mechanism rather than
  duplicating I/O authorities. The normative Core/TC3 profile now matches the
  working runtime-health + reviewed-catalog + Hardware-Driver/HAL composition;
  richer vendor-specific scanning remains an optional additive adapter.
- Closed the topology-active-length item: `ST_FieldbusTopology.NodeCount` and each
  node's `ChannelCount` already provide the compact active representation required
  to keep discovery and iteration proportional to configured content.
- Made both test wrappers serialize `BootProjectAutostart="false"` and added that
  assertion to the hidden-XAE gate. XAE reload confirms both values are false.

## 5. Gap-closing program

Ordered by safety/conformance risk and dependency.

| Priority | Work package | Change type | Exit evidence |
|---|---|---|---|
| DONE | Review/stage authored framework and fixture files; exclude `.dart-*`, `Dependancies`, XAE `.~u`, build output and credentials. Establish a clean-clone baseline before treating any later result as evidence. | Repository hygiene | Completed by `87cad29`; clean clone reproduced PLC lint/XML/compile paths and HMI analysis/tests |
| DONE | Build/install Core `0.4.0.0` and Modules `0.3.0.0`, reload Press Demo, compile all three PLC projects warning-clean, and regenerate their TMC files. | Infrastructure + code | **Freshly executed 2026-08-01:** all three direct nested XAE builds returned `LastBuildInfo=0` and an empty Error List for ARMV7-A; current TMC artifacts were emitted |
| DONE | Run both TcUnit gates and archive results/artifact hashes. | Infrastructure + runtime | Core/Modules **84/84 across 26 suites green**, including an independent Windows 10 x64 VM repeat; Press integration bench **8/8 across 2 suites green** on 2026-08-02; combined 92/92 across 28 suites, with runner identities and hashes archived |
| SOURCE-ONLY | Register the licensed self-hosted runner and isolated-runtime hook, then make the implemented hidden-XAE + TcUnit/JUnit jobs required. | CI infrastructure | Both local `CheckAllObjects` gates green; hosted JUnit check and retained artifacts/hashes still pending |
| DONE | Formalize Demo and Press Demo as internal feature-testing fixtures: deterministic simulation covers mode/command/recovery, diagnostics, recipes, traceability and multi-root behavior; optional ADS/OPC-UA and HIL profiles stay separate. | Test architecture + internal fixtures | Press source/build and 8-test runtime integration gate green; explicitly not a real project or machine-acceptance claim |
| DONE | Central decision resolver: idempotent active request, reject/log overlap, monotonic timeout, validated safe default, operator/timeout distinction and atomic clear. | Core implementation | XAE clean; green runtime `DecisionTests` included in the 84-test gate |
| DONE | **Capability-driven write manifest** with stable key/revision, type, writable/state flags, bounds/domain and owning typed handler; no arbitrary-tag fallback. | Novel contract + PLC/HMI | XAE/HMI validation clean; green runtime `HmiTests` includes typed fail-closed capability coverage |
| DONE | Extend `plc_lint.py` into the promised conformance gate. | Tooling | **Freshly executed 2026-08-01**: 265 files clean in both profiles; 21 linter fixtures green, including rejection of reserved enum members, string `CASE` labels, duplicate XAE source ownership and TwinCAT-invalid `..` includes, ownership-root resolution, and a guard that runs the linter against the real tree. Three earlier rules (D1/C5/S1) were corrected first — see `OBJECTIVES_AUDIT_REVIEW.md` §R0 |
| DONE | Implement `FB_SystemHealthPublisher`, time-quality records/flags, and the TC3 probe seam. | Core contract + TC3 adapter | XAE clean; green fault-edge/quality runtime test. Live task/DC/PTP is deployment adapter acceptance |
| DONE | Implement reusable signal-tower mapping and bounded mailbox lamp test. | Core + HMI | Green runtime truth-table/bounded test; physical I/O checkout is deployment evidence |
| DONE | Add gateway `discoverPaths`, `setReadTiers`, and bounded `readValues`; enforce roots/counts, conservative shared-client tiers, and commit-last writes. | Gateway/HMI | Protocol/reconnect/auth tests plus 4,000-path/four-client proportional-traffic test green |
| P1/release | Exercise the packaged gateway against a representative real ADS/OPC-UA forest and multiple browser clients; archive bytes, poll latency, reconnect, and discovery-revision measurements. | Release acceptance | Deterministic algorithmic test is green; selected IPC/runtime transport evidence remains |
| DONE | Reconcile fieldbus discovery to runtime health + reviewed catalog + HAL values; keep richer `I_FieldbusScanner` discovery optional and force fail-closed until reviewed. | Specification + TC3 adapter + application data | Internal Press-bench composition, publisher validation tests, x64 compiler gate; unplug/mismatch/force are separate deployment acceptance |
| P2/profile | When demanded, qualify `FB_TcpChannelTc3` against a pinned TF6310 API/license/server and any selected remote recipe/carrier adapter without changing portable interfaces. | Optional TC3/deployment profile | Simulated fault tests plus live open/send/receive/reconnect evidence for the claimed profile |
| DONE | Generate the §8.8 reason/localization text lookup from the Core enum + registered type bands, with duplicate/freshness checks and unknown fallback. | Generation | Collision-free artifacts/checks plus green generated-metadata runtime test |
| DONE | Generate §8.9 rationalization from one registry; add the fixed §11.6 host-event surface and optional sink. | Contract generation + Core | Generated checks and green `HostEventTests`; external historian/MES remains a deployment profile |
| P2/profile | Implement and qualify the optional §8.10 Alarm-performance profile once per selected station/line or historian; do not duplicate it per root. | Deployment analytics + acceptance | Named owner; alarm-rate/standing/stale KPIs; chatter/flood drill-through; proof that control/history are unsuppressed |
| DONE | Use compact active topology lengths without duplicating the library bounds. | Binding/optimization | `NodeCount`/`ChannelCount` bound discovery, joins and iteration; gateway excludes unused capacity |

**Standing rule (added after the second review).** A tool, gate, or generator may
not be marked DONE until it has been executed against the **real repository**, not
only against its own fixtures. The linter passed nine synthetic fixtures while
producing six false positives on the shipped tree, and one of its checks turned out
never to have fired at all. Fixtures prove a rule *can* fire; only a real run proves
it encodes the intended invariant.

The preferred pattern across these packages is **capability-driven and generated**:
the PLC publishes only a reviewed capability, one owning handler enforces it, the
HMI derives its control, and CI derives parity checks from the same contract. That
approach advances O1/O4/O7/O9 together and avoids fixing gaps by adding a second
authority.

## 6. Verification performed in this snapshot

- Static analysis is clean for the Flutter HMI, gateway, and shared OPC UA client
  package.
- The full Flutter suite is fresh and green: **166 passed**, with **4 intentional
  live-environment skips**.
- The generated reason catalog `--check` is green and covers 51 registered codes
  across four deterministic PLC/HMI artifacts.
- All 285 XML-based PLC source/project/solution documents parsed without error. All 270
  `<Compile Include>` paths resolve after correcting the rearranged aggregate
  manifest.
- Source scans: 14 `ParCfg` records, no schema-first violation; **28** TcUnit suite
  declarations and **92** `TEST(...)` calls. The split Core/Modules runner owns
  26 suites/84 tests; `PRG_PressTestRunner` owns 2 suites/8 tests; none are orphaned.
- **PLC lint: freshly executed.** The present tree reports **265 files clean in
  both profiles** and all 21 positive/negative fixtures green. The first run
  correctly rejected the new reserved identifier `At`; the transport field was
  renamed `Stamp` across PLC/HMI/tests before the clean rerun. The earlier
  reconciled baseline and rule corrections remain recorded in
  `OBJECTIVES_AUDIT_REVIEW.md`.
- **TwinCAT compile: freshly executed.** Core `0.4.0.0`, Modules `0.3.0.0`, and
  Press Demo each returned `LastBuildInfo=0` with an empty Error List under
  `Debug|TwinCAT OS (ARMV7-A)` and regenerated their TMC files. All Press EtherCAT mappings resolve. The full
  system-project CLI path remains target-blocked at `Check config` while its
  saved remote target is unavailable. After reconciling the aggregate-test
  compiler findings, Core and Modules again returned `LastBuildInfo=0`/zero
  errors under `Debug|TwinCAT OS (x64)`. After the folder/gate split, the new
  `Invoke-TwinCatBuild.ps1` opened each wrapper in a separate hidden Visual Studio
  TwinCAT host, selected x64, asserted boot autostart false, and returned
  `CheckAllObjects=TRUE` for both `FraktalTests` and `PressTests`. No configuration
  was activated or downloaded.
- **TcUnit runtime: complete for the split source test program.** User-supplied fresh XAE output records
  **84 successful, 0 failed, 84 total, 26 suites** for the Core/Modules gate. The
  new fail-closed parser independently accepted the summary and runner identity
  and emitted JUnit;
  `Evidence/2026-08-01_Core_Modules_TcUnit.md` records the summary and SHA-256
  snapshot. A second user-supplied run on the isolated Windows 10 x64 VM on
  2026-08-02 produced the same 84/84 and 26-suite identity; the parser accepted
  it and the evidence record binds its raw log hash. Because that output is
  rooted at `PRG_TcUnitRunner`, it is a Core/Modules repeat. A subsequent isolated
  VM run is rooted at `PRG_PressTestRunner` and reports **8 successful, 0 failed,
  8 total, 2 suites**. The same validator accepted its runner and counts;
  `Evidence/2026-08-02_Press_TcUnit.md` records the result and artifact hashes.
  Combined runtime result: **92/92 tests across 28 suites**.
- **Gateway scalability:** the targeted server suite is green with 19 tests,
  including 4,000 paths, four WebSocket clients, a 120-path cyclic surface,
  bounded 512-value drill-down chunks, reconnect, and conservative shared tiers.
- XAE reload confirms `BootProjectAutostart=False` for both test wrappers.
- Not performed here: live TMC import and OPC UA or packaged real-transport
  acceptance, electrical checkout, or safety validation. The internal Press bench
  does not substitute for any of those deployment gates.
