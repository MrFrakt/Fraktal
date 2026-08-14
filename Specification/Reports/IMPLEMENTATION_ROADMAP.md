# Fraktal implementation roadmap

*Status: execution plan derived from the objective/coherence review of 2026-07-12. The normative requirements remain in `Fraktal_Core_Part_I.md`, the TwinCAT binding in Part II, and the HMI surface in `HMI_CONTRACT.md`. This document orders the work; it does not silently weaken a `shall`.*

*This roadmap is a plan, not a progress tracker — it is deliberately not edited as items land. For what is actually proven versus pending at any moment, read `OBJECTIVES_AUDIT.md` and the archived runs in `Evidence/`.*

## 1. Purpose and ordering rule

Fraktal already has the right central shape: one recursive module model, one inherited lifecycle, one diagnostic vocabulary, simulation through HAL seams, and a generic HMI. The next work shall make the existing promises compositionally true before adding more optional profiles.

Priority follows the objectives in Core §1.1:

1. remove application glue that the framework claims to inherit (O1);
2. make every failure and withheld action explain itself (O3);
3. make recursive operations atomic across a subtree (O4/O5);
4. prove one complete PLC→OPC UA→HMI path (O5/O6);
5. use that stable core to prove portability and external mappings (O8).

Each phase below has an exit gate. A phase is not complete because source files exist; its tests and stated integration evidence must pass.

---

## 2. Phase 0 — truthful executable baseline

### Goal

Produce one reference application whose runtime structure matches the specification exactly and which can be compiled against a pinned TwinCAT version.

### Work

- Implement `FB_StationUnit EXTENDS FB_UnitBase` from Annex C.
- Make `MAIN` host two real peer root Units, not EM stand-ins.
- Put the clamp EM and cylinder CMs below each root.
- Give each root its own model identity, access manager, alarm log, OEE state, nameplate, cycle profiler, and simulated HAL mapping.
- Resolve every current first-compile watch item against the pinned compiler. Record the accepted spelling/signature in Part II and remove it from the watch list.
- Add a repeatable build script or documented non-interactive build invocation for Core → Modules → Tests.

### Exit gate

- TwinCAT build is warning-clean.
- Both roots can run different models and modes concurrently.
- A forced CM fault rolls to exactly its owning root, not its peer.
- The root nameplates and browse names match their instance/schematic names.
- TcUnit executes in CI and publishes an unambiguous pass/fail artifact.

### Objectives advanced

O2, O3, O4, O6, O8. This is the integration fixture every later phase reuses.

---

## 3. Phase 1 — inherited composite behavior

### Goal

Make recursion a property of the base classes rather than a convention each EM/Unit author must remember.

### Work

#### 3.1 Child execution and summaries

- Move registered-child ticking into the composite base lifecycle.
- Override `GetFaultSummary` in the composite base to walk descendants automatically.
- Define two distinct semantics:
  - **recursive status summary** always reports a descendant first-out;
  - **command fault adoption** changes the parent command to ERROR only when that child participates in the active command/await.
- Reject duplicate registration and registration after initialization unless explicitly supported.
- Keep bounds checks and deterministic first-child ordering.

#### 3.2 Transactional mode cascade

- Add a pure `CanSetMode(Mode)`/`SupportsMode(Mode)` capability query.
- Preflight the entire child-Unit subtree before changing any mode.
- Return a complete rejection report naming every refusing path.
- Commit the mode only after every descendant accepts.
- Treat a commit-time disagreement as a diagnostic inconsistency, not a partial success.

#### 3.3 Containment enforcement

- Keep the static EM→Unit prohibition check.
- Add a runtime/setup assertion so an invalid capability cannot be registered into an EM unnoticed.

### Exit gate

- A new EM test type needs no custom `OnCyclic` merely to tick children.
- An idle child fault is visible in recursive status without falsely faulting an unrelated parent command.
- A nested Unit rejecting a mode leaves every Unit in its original mode.
- Duplicate and over-capacity registrations fail deterministically with diagnostics.

### Objectives advanced

O1, O3, O4.

---

## 4. Phase 2 — one physical data contract and atomic changeover

### Goal

Remove ambiguity between the normative four-structure contract and fields that merely serve the same conceptual role.

### Work

#### 4.1 Pin the contract

Every conforming module type shall physically publish:

- `ParCfg` — versioned model data;
- `ParCmd` — values latched on the Execute edge;
- `OutCmd` — terminal command result;
- `OutImm` — live status, including the diagnostic mirror.

If a module has no members for one role, it uses the framework empty structure rather than omitting the node. Generate or test the OPC UA browse shape so clients never infer aliases such as “field X is acting as OutImm.”

#### 4.2 Complete tier interfaces

- Make shipping CMs implement `I_ControlModule` and shipping EMs implement `I_EquipmentModule`, or explicitly remove those interfaces from Core conformance.
- Validate generic DINT commands against the same command catalog as the typed surface.
- Make the generic and typed paths enter the same PLCopen lifecycle.

#### 4.3 Two-phase recipe transaction

The source now uses this transaction (TwinCAT compile and failure-injection verification remain exit gates):

1. `PrepareRecipe(ModelId)` — provider load, schema validation, migration, and type validation into staging data;
2. recursive readiness aggregation;
3. `CommitRecipe()` — infallible bounded swap at a defined scan boundary, with no validation or I/O;
4. `AbortRecipe()` — discard all staging data on any rejection.

Station configuration remains outside model transactions. The active `ModelId` changes only after commit.

### Exit gate

- OPC UA contract tests find the same four nodes under every module.
- A failure in the last descendant leaves every active `ParCfg` and the root `ModelId` unchanged.
- Generic and typed command tests produce identical state, timing, result, and diagnostic behavior.

### Objectives advanced

O1, O3, O4, O5, O8.

---

## 5. Phase 3 — one manual-release and write path

### Goal

Make every operator write act or explain through one PLC-authoritative predicate.

### Work

- Implement the normative `OnManRelease` hook in the module base.
- Represent common and per-function releases as published records with label, state, reason, bypassability, and required access level.
- Make `ManualCommand`, fieldbus force, jog/hold, config writes, mode change, reset, shelving, and changeover call their authoritative release predicate.
- Make each `ReleaseReport…` query enumerate the result of that same predicate; do not duplicate conditions in a reporting-only function.
- Require owning-Unit MANUAL mode for manual commands and force operations unless a separately named, rationalized commissioning action exists.
- Preserve the distinction between a defended module command and a raw process-image force.
- Implement generic child command registration/routing so a root Unit does not hand-code a string-path CASE for every manual target.

### Exit gate

- Every visible write control has tests for accepted, access-denied, mode-denied, interlock-denied, and stale-client cases.
- The set of release-report reasons exactly equals the failed gate inputs in property tests.
- No manual or force control ships while its PLC predicate is absent.
- Every accept and reject produces an audit event without leaking secrets.

### Objectives advanced

O1, O3, O7.

---

## 6. Phase 4 — trustworthy diagnostics and KPIs

### Goal

Ensure every displayed sentence and KPI has complete provenance and validity.

### Work

#### 6.1 OEE validity

- Keep Availability, Performance, and Quality independently valid.
- Set `OeeValid` only when all three factors are valid.
- Never label a partial product as OEE. If useful, expose it under a separate, explicitly non-standard name.
- Pin the KPI definition/version and scheduled-time assumptions; record any ISO 22400 mapping in an annex.

#### 6.2 Generated reason catalog

- **Source-complete for §8.8/§8.9:** the HMI generator reads the
  authoritative Core enum and registered type-band constants, rejects duplicate
  codes/symbols, and joins the symbol-keyed machine-readable rationalization
  registry without creating a second numeric authority. It emits the PLC lookup,
  manifest count, Dart localization keys/default English, priority/category,
  operator action, consequence, and shelvability. CI fails when any derived
  artifact is stale or the registry coverage is not exact.
- Fail CI on duplicate numbers, unregistered numeric assignments, missing fallback
  text/localization keys, and incomplete or conflicting rationalization metadata.
- Treat external/application reason registration as an extension seam: the PLC
  rejects attempts to override generated standard metadata and requires complete
  priority/category/action/consequence data before an external reason is shelvable.

#### 6.3 Alarm semantics

- Test recursive alarm ownership, shelving expiry, historian sink ordering, full-table behavior, and source-path stability.
- Define whether a full event table rejects the newest event or evicts by an explicit policy; always raise a visible system diagnostic for loss.
- Treat Core §8.10's long-window nuisance/flood KPIs as an explicitly selected
  Alarm-performance profile. Implement them once at the station/line historian or
  one owning aggregator, consume the complete event stream, and never suppress
  control, first-out, blocking, or retained history.

### Exit gate

- OEE is blank/invalid whenever any required factor is unavailable.
- No production reason exists outside the verified registry, and every alarmable
  reason has one rationalized metadata record.
- HMI tests render catalog text and fall back to the diagnostic description when localization is unavailable.
- A deployment claiming the Alarm-performance profile names one owner and proves
  alarm-rate, standing/stale counts, chatter handling, and flood drill-through.

### Objectives advanced

O3, O5, O7.

---

## 7. Phase 5 — production HMI transport and connection lifecycle

### Goal

Prove the zero-per-station HMI claim against a real namespace and make connection loss fail closed.

### Connection bootstrap (implemented in this milestone)

The HMI now owns an explicit pre-shell state machine:

```text
load settings
  ├─ none / never connected → connection wizard
  └─ saved + proven once    → connecting screen
                                  ├─ LIVE → interactive HMI
                                  └─ 30 s → show Edit connection settings

interactive HMI -- STALE/DOWN --> connecting screen (interaction removed immediately)
```

Settings are stored locally with Flutter/Dart SDK facilities only: a JSON configuration file on native platforms and browser local storage on Web. `everConnected` is written only after the repository reports `LIVE`; merely saving an endpoint does not prove it.

### Remaining transport work

- Implement the native OPC UA adapter behind `PlcRepository`.
- Implement the WebSocket/REST gateway protocol for Web.
- Define handshake/version negotiation before accepting `LIVE`:
  - transport authenticated;
  - namespace reachable;
  - Fraktal contract/schema version supported;
  - subscriptions established;
  - at least one valid root Unit discovered.
- Emit `STALE` on missed freshness deadlines and `DOWN` on session loss.
- Retry with bounded backoff while the blocking screen is visible.
- Never replay queued operator writes after reconnection.

### Contract-test namespace

Test the production adapter against a namespace containing:

- multiple roots;
- nested Units/EMs/CMs;
- unknown concrete types;
- optional/missing facets;
- reordered browse results;
- bad-quality and stale values;
- newer schema/enum values;
- disconnect/reconnect during a command.

### Exit gate

- First launch opens the wizard.
- A previously proven endpoint reconnects without exposing stale controls.
- Link loss removes the interactive shell in the same UI event turn.
- Edit settings remains hidden for the first 30 seconds and appears thereafter.
- The production namespace renders without station-specific Dart code.
- No write is buffered or replayed across a lost session.

### Objectives advanced

O3, O5, O7.

---

## 8. Phase 6 — machine-readable interoperability projections

### Goal

Keep Fraktal as the control model while making standard external views generated and testable.

### Work

- Generate a Fraktal OPC UA NodeSet and map its objects to OPC UA for Machinery building blocks.
- Pin and update the IDTA 02006 Digital Nameplate mapping.
- Add optional mappings for Machinery Job Management and Result Transfer.
- Keep PackML, AAS, MTP, Sparkplug, and UAFX as projections/profiles, never parallel PLC lifecycles.
- Generate enum ordinal tables and schema fingerprints consumed by PLC, HMI, gateway, and documentation.

### Exit gate

- NodeSet validation and companion-spec conformance tests pass.
- A generic Machinery client discovers roots/components without Fraktal-specific browse heuristics.
- Projection adapters contain no equipment-sequence logic.

### Objectives advanced

O2, O4, O5, O8.

---

## 9. Phase 7 — security profile and portability proof

### Goal

Turn security and portability from design intent into evidence.

### Work

- Define deployable security profiles: development, commissioning, and production.
- Production requires signed/encrypted transport, trusted application certificates, non-anonymous writes, least privilege, audit retention, secret handling, and documented recovery.
- Add threat modelling, dependency/SBOM production, vulnerability intake, and patch policy to the release process.
- Implement a deliberately small second PLC binding containing one Unit, one EM, one CM, recipe transaction, diagnostics, and the conformance suite.
- Feed every portability pain back into Core-versus-binding ownership before expanding the second binding.

### Exit gate

- Security configuration is machine-checkable and fails closed.
- The second binding passes the same behavioral contract tests without changing the Core model.
- All platform-specific clauses are isolated in their binding.

### Objectives advanced

O7 and O8, with direct evidence rather than aspiration.

---

## 10. Cross-phase engineering rules

- **One source per contract.** Generate duplicated enum, reason, schema, and mapping artifacts.
- **Pure query equals gate.** Release reports call the same predicate that authorizes the action.
- **Prepare before commit.** Any recursive mutation is preflighted and committed only after whole-subtree acceptance.
- **No hidden partial conformance.** Deferred mandatory behavior is a missing profile, not an implementation note that still claims full conformance.
- **No write replay.** A transport reconnection starts a new authority/session boundary.
- **Unknown data is not good data.** Invalid KPI factors, bad-quality values, unknown enum ordinals, and stale timestamps render explicitly unavailable.
- **Tests follow the objective.** Every framework feature has a failure-path test proving why the feature exists, not only a happy-path API test.

## 11. Suggested release milestones

| Milestone | Included phases | Release claim |
|---|---|---|
| R0 — Executable reference | 0 | TwinCAT reference forest, simulator, TcUnit |
| R1 — Compositional Core | 1–2 | Recursive modules + atomic mode/recipe behavior |
| R2 — Operator-safe writes | 3–4 | Manual/release/audit + trustworthy diagnostics/KPIs |
| R3 — Generic connected HMI | 5 | Real OPC UA/gateway discovery and fail-closed reconnect |
| R4 — Interoperability profiles | 6 | Generated NodeSet and standard projections |
| R5 — Portable secured release | 7 | Security evidence + second binding proof |

The recommended immediate sprint is Phase 0 followed by Phase 1. The HMI connection bootstrap is useful now, but it should not be mistaken for completion of Phase 5 until a repository can establish and validate a real PLC subscription.
