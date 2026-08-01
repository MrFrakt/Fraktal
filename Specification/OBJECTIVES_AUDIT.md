# Fraktal objectives and conformance audit

Snapshot: **2026-07-31**. Scope: the Fraktal standard implementation against Part I,
the TwinCAT binding, and the normative HMI/transport contracts: Core/Modules
libraries, Flutter HMI, Web gateway, aggregate tests, CI, and repository state.
The Demo and Press Demo applications are inspected only as internal integration
and acceptance fixtures for the reusable framework; they are not conformance
targets or production-machine acceptance evidence.

This is a source-level audit, not a release certificate. A current TwinCAT build,
TcUnit execution, regenerated TMC, and adapter/integration-fixture execution are
still required before the changed PLC libraries may claim conformance. Cabinet,
wiring, and site commissioning evidence belongs to a later deployment, not this
framework audit.

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
| O3 Diagnosable by construction | 🟡 | First-out, awaited-module/condition walk, qualified paths, alarm lifecycle, HELD, decision audit, controller/clock health, reusable tower status, live HMI alarm hydration, and generated reason-code text are implemented. Generated alarm rationalization and the fixed host-event projection remain incomplete. |
| O4 Reusable, recursive, scalable | 🟡 | Recursive composition, configuration manifest, direct and Web-client read tiers, bounded targeted reads, multi-client-safe gateway aggregation, and on-demand diagnostics are strong. The generic EtherCAT scanner is a skeleton and topology bounds are library constants; representative large-forest measurements remain release evidence. |
| O5 Flexible data and connectivity | 🟡 | Provider and transport seams, ADS, OPC UA, Web gateway, local recipe/carrier providers and simulated byte channel are real. The default TC3 TCP byte channel and non-local recipe adapters remain integration skeletons/adapters rather than proven implementations. |
| O6 Simulatable | ✅ | HAL separation, simulated repositories/plants/channels, and hardware-free suites are present. Physical and simulated press selection remain composition-root concerns. |
| O7 Safe | 🟡 | Safety authority stays outside the standard PLC; release loss withdraws outputs, force is explicit/fail-closed/output-only, and no control self-resumes. Source-level boundaries are strong, but the changed PLC libraries are not yet compiled or executed against their safety/control-domain test fixtures. Press cabinet constants are fixture/deployment data, not framework-conformance evidence. |
| O8 Portable | ✅ | Platform-neutral Core and TC3 binding remain separated; transport/domain contracts do not depend on the Flutter platform. Only the TC3 binding is implemented, which is consistent with the stated scope. |
| O9 Engineering discipline | 🟡 | Version pins follow the documented semantic components, the conformance linter now implements its promised structural rules with positive/negative fixtures, XML is text-diffable, and CI exists. The linter **now runs clean in both profiles** after three rules were corrected (they had never been executed against the tree). The licensed PLC job is still a deliberate failing stub, and authored files remain untracked. |
| O10 Industrial robustness | 🟡 | Bounded data, validate-before-load, fail-closed authorization, command acknowledgement, reconnect/no-replay, recovery reset, decision timeout, health/time supervision, bounded Web reads, and focused tests are strong. PLC compile/TcUnit, target probe wiring, packaged performance, and live acceptance remain open. |

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
- Library compatibility pins now use Core `0.3.0.0` and Modules `0.2.0.0`.
  Core's minor step covers the append-only decision/configuration capability
  contract; observable changes no longer masquerade as rebuild revisions.

### Material open gaps

**G1 — Release proof is absent.** The CI `plc-compile` job contains explanatory
`echo` lines followed by `exit 1`; it is not a build implementation. The current
Core `0.3.0.0` / Modules `0.2.0.0` source has not been compiled in XAE and its TcUnit source
has not run. Source/XML plausibility is useful but cannot establish TwinCAT type,
visibility, library-resolution, stack, warning, or runtime behavior.

**G4 — Fieldbus auto-discovery/force integration is unfinished.** The Press fixture
has a real master-health reader plus a reviewed project catalog, but
`FB_EcFieldbusScanner.Scan`, `RefreshValues`, and `ForceChannel` are explicit
skeletons. This does not satisfy §10.5.1's generic runtime topology/channel
discovery. The new `Forceable` flag safely suppresses the unfinished force path;
it does not complete it.

**G8 — Host-event and alarm-rationalization projections are incomplete.** Part
lifecycle events, bounded records, `I_EventSink`, and a generated §8.8
reason-code/localization-text lookup now exist. There is still no complete fixed
ISA-95 host-event projection, and §8.9 rationalization metadata is not yet derived
and checked from one machine-readable registry. Historian adapters are explicitly
deployment-deferred; the fixed host-event surface and complete generated
rationalization remain open `shall`s.

**G10 — Source-control state is not releaseable.** The reorganized
`PLC/TwinCAT/{Framework,Tests and Examples}` tree currently appears as deletion of
the former paths plus a new untracked tree, and additional authored HMI/tests/tools
also remain untracked. Staging and committing are user-owned actions; until that
move and every new compile/test input are reviewed and recorded, a clean clone
cannot reproduce this snapshot. The rearrangement also invalidated all 40 relative
compile paths in the aggregate test project; those paths are now corrected and the
repository scan resolves all 260 compile items, but only a clean-clone XAE build
can prove the move is recorded completely.

### Test-fixture boundary

The Press Demo is not an additional framework gap. It is the richest internal
acceptance fixture for composition, sequencing, release ownership, diagnostics,
recovery, traceability, control domains, and HMI discovery. Its physical-I/O and
control-circuit constants are deliberately excluded from the objective score:
they become commissioning/MOC evidence only if someone deploys that fixture to a
real cabinet. Framework CI should exercise its deterministic simulation profile;
optional hardware-in-the-loop evidence is a separate adapter qualification.

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
  `FB_Matrix220CM`; subsequent decision/configuration/health/tower additions bring
  the aggregate source to 89 `TEST(...)` cases across 28 suite types.
- Corrected TwinCAT semantic versioning and current pins to Core `0.3.0.0` and
  Modules `0.2.0.0`.
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
- Closed G9 at source level: the linter now checks the four-record/schema-first
  contract, enum parity, inheritance/body/hook-super invariants, semantic
  fail-safe `CASE ELSE`, sequence ownership, containment, reason collisions,
  compile-list coverage and deployed-root publication. Positive/negative fixtures
  are present; execution awaits a Python-equipped CI/workstation.
- Closed the live-facet projection gap found during the second audit. Sparse
  active alarms, newest-first history, rationalization data, timestamp quality,
  OEE/trends, part results, nameplate, safety and control-power now hydrate from
  transport-neutral snapshots. Cycle/OEE rings now preserve chronological order.
- Closed G5 at source level. The gateway now exposes revisioned discovery,
  compact-index read tiers and bounded targeted reads; read roots apply to every
  read surface and shared-session tiers use the conservative intersection of all
  connected clients. The IO/Web gateway clients chunk and merge bounded reads,
  and reconnect restores tier intent without replaying writes.
- Closed the §8.8 reason-text projection with a deterministic generator over the
  authoritative Core enum and registered Core/Modules reason bands. CI freshness,
  duplicate rejection, generated-key lookup, English fallback, and preservation
  of unknown PLC diagnostic text are tested. §8.9 rationalization generation is
  deliberately tracked separately under G8.
- Repaired the rearranged aggregate-test manifest: 40 stale relative includes now
  resolve from the new project directory. All 260 repository compile items resolve
  in the source check.

## 5. Gap-closing program

Ordered by safety/conformance risk and dependency.

| Priority | Work package | Change type | Exit evidence |
|---|---|---|---|
| P0 | Review/stage authored framework and fixture files; exclude `.dart-*`, `Dependancies`, XAE `.~u`, build output and credentials. Establish a clean-clone baseline before treating any later result as evidence. | Repository hygiene | Clean clone contains every compile/test input and reproduces HMI analysis/tests |
| P0 | Build/install Core `0.3.0.0` and Modules `0.2.0.0`; reload applications; compile warning-clean; run all TcUnit suites; regenerate TMC; archive results. Replace the CI stub with Automation Interface build plus JUnit publication on a licensed self-hosted runner. | Infrastructure + code | Green XAE builds, green TcUnit/JUnit, CI required check, versioned artifacts/hashes |
| P0 | Formalize Demo and Press Demo as internal acceptance fixtures: a deterministic simulation profile exercises discovery, mode/command/recovery, diagnostics, recipes, traceability and multi-root behavior; keep optional ADS/OPC-UA and hardware-in-the-loop profiles separate. | Test architecture + application fixtures | Repeatable integration report with no cabinet assumptions; failures trace to a Core/Modules/HMI contract |
| SOURCE-ONLY | Central decision resolver: idempotent active request, reject/log overlap, monotonic timeout, validated safe default, operator/timeout distinction and atomic clear. | Core implementation | Source-complete with TcUnit coverage; XAE execution remains part of P0 |
| SOURCE-ONLY | **Capability-driven write manifest** with stable key/revision, type, writable/state flags, bounds/domain and owning typed handler; no arbitrary-tag fallback. | Novel contract + PLC/HMI | HMI analyzer and manifest/repository tests green; PLC TcUnit source added, execution remains part of P0 |
| DONE | Extend `plc_lint.py` into the promised conformance gate. | Tooling | **Executed 2026-07-31**: 255 files clean in both profiles; 16 fixtures green, including a guard that runs the linter against the real tree. Three rules (D1/C5/S1) were corrected first — see `OBJECTIVES_AUDIT_REVIEW.md` §R0 |
| SOURCE-ONLY | Implement `FB_SystemHealthPublisher`, time-quality records/flags, and the TC3 probe seam. | Core contract + TC3 adapter | Source and fault-injection suite complete; live task/DC/PTP evidence remains P0 |
| SOURCE-ONLY | Implement reusable signal-tower mapping and bounded mailbox lamp test. | Core + HMI | Truth-table/source and HMI tests complete; physical I/O checkout is deployment evidence |
| SOURCE-ONLY | Add gateway protocol capabilities `discoverPaths`, `setReadTiers`, and bounded `readValues`; enforce read-root/path/count limits server-side, aggregate shared-client tiers conservatively, and retain commit-last writes. | Gateway/HMI | Source, reconnect, authorization and protocol tests green; representative large-forest traffic/latency measurement is the following P1 acceptance item |
| P1 | Exercise the packaged gateway with a representative large forest and multiple browser clients; measure steady-state bytes, poll latency, reconnect and discovery-revision behavior against the transport budgets. | Release acceptance | Archived measurements demonstrate traffic proportional to each client's consumed surface and no shared-session starvation |
| P2 | Complete or explicitly de-scope `FB_EcFieldbusScanner`: runtime identity/state/channel discovery, deterministic catalog join, quality, mapping errors and optional force resolver. Keep all force capabilities false until each mapped output is reviewed. | TC3 adapter + application data | Simulated scanner tests, disconnected/mismatch tests, live EtherCAT acceptance |
| P2 | Qualify the optional TC3 production connectivity profile when demanded: implement `FB_TcpChannelTc3` against a pinned TF6310 API/license/server combination and qualify any selected remote recipe/carrier adapter without changing the portable interfaces. | TC3/deployment adapters | Simulated fault tests plus live open/send/receive/reconnect evidence; adapter profile and prerequisites documented |
| SOURCE-ONLY | Generate the §8.8 reason/localization text lookup from the Core enum + registered type bands, with duplicate and freshness checks and unknown-code fallback. | Generation | Collision-free generated artifact, CI `--check`, mapping and fallback tests |
| P2 | Put §8.9 alarm rationalization in one machine-readable registry and generate/verify its PLC/HMI projections; add the fixed §11.6 host-event surface and feed it through `I_EventSink`. Keep historian/MES transport adapters deployment-profile work. | Contract generation + Core | Metadata completeness/collision tests and end-to-end part/mode/changeover/tool/material/NOK event capture |
| P3 | Convert topology limits to a true TC3 Parameter List or add a compact active-length representation, only after the P0 compiler gate exists. | Binding/optimization | Project override build and bounded memory/traffic measurement |

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
- The full Flutter suite is fresh and green: **161 passed**, with **4 intentional
  live-environment skips**.
- The generated reason catalog `--check` is green and covers 50 registered codes.
- All 264 PLC XML/project/source documents parsed without error. All 260
  `<Compile Include>` paths resolve after correcting the rearranged aggregate
  manifest.
- Source scans: 14 `ParCfg` records, no schema-first violation; **27** TcUnit suite
  declarations; **86** `TEST(...)` calls (all 27 suites registered in
  `PRG_TcUnitRunner`, none orphaned); concrete hook overrides inspected for base
  calls.
- **PLC lint: executed.** An earlier revision of this section claimed "no Python
  runtime available". That was wrong — Python 3.14.6 is present. When run, the
  linter reported six violations, all false positives in rules authored during
  this audit. The rules were corrected and the gate now reports **255 files clean
  in both profiles**, with a fixture that runs it against the real tree so the
  same blind spot cannot recur. See `OBJECTIVES_AUDIT_REVIEW.md`.
- Not performed here: TwinCAT compile, TcUnit execution, live PLC/OPC UA/gateway
  acceptance, electrical or safety validation.
