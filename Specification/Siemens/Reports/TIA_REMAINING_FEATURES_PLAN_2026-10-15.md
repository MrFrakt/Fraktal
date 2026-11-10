# Fraktal/TIA — remaining features and implementation plan (2026-10-15)

A census of what the Siemens binding still lacks against the TwinCAT reference,
taken after the press demo first ran end to end on the simulated CPU1516
([press evidence](../Evidence/TIA_PRESS_COMPLETE_2026-10-15.md)), and an ordered
plan to close it. The baseline census below is retained to explain the plan;
the dated implementation progress in section 5 records subsequent completion
and its measured limits.

Continuation, 2026-10-15: **P1 is in progress.** The shared typed line engine now
has native owner/mirror, atomic-image, staleness/event and image-reapplication
evidence. See [line engine evidence](../Evidence/TIA_LINE_ENGINE_2026-10-15.md).
Continuation, 2026-10-16: the isolated owner composition now shares its normal
mailbox/manifest and one LOAD_DB document across two roots. Native compile,
read-back and 54 live checks include an actual simulated power cycle after
corrupting the working cache. See [owner evidence](../Evidence/TIA_LINE_OWNER_2026-10-16.md).
Continuation, 2026-10-16: owner named line sets/current export now reuse the
ordinary root catalog, typed staging and LOAD_DB documents. A bound synthetic
mirror provider and offline mirror restore are implemented and measured; see
[sets/mirror evidence](../Evidence/TIA_LINE_SETS_MIRROR_2026-10-16.md).
Continuation, 2026-10-17: shifts, classes/capture and runtime model creation are
implemented. The wired press now includes a local Line owner, complete V3
calendar/targets, atomic Line sets and LOAD_DB recovery. Normal generation
admits complete owner/bound-mirror profiles; partial engine experiments retain
the workbench API. See [press integration evidence](../Evidence/TIA_LINE_PRESS_2026-10-17.md).
P12 OUC TCP and full HMI/conformance/physical qualification remain separate.

## 1. Method

- **Published Unit facets**: every published member of TC3 `FB_UnitBase`/
  `FB_ModuleBase` was checked against the generated TIA press Unit.
- **Operator requests**: each of the 39 `E_HmiRequestKind` members (Core DUT)
  was checked for a handler in the Siemens Core templates and generator.
- **Framework objects**: TC3 `Fraktal_Core`/`Fraktal_Modules` objects were
  compared with `Framework/Core` and `Framework/Modules` (plan §7.1/§7.2 rows).
- **Tooling/phases**: plan §6 phases and Part IV R-gates were checked for their
  named artifacts.

## 2. What already exists (baseline)

Lifecycle frame and command kernel; Units with modes, mailbox, release reports,
manual routing and decisions; access sessions with salted local users and policy
retention; alarms (AUTO/MANUAL reset, closed history, manual-reset recovery,
retained event delivery); station and model config with typed values, seeds,
named sets and JSON exchange; LOAD_DB persistence; sequence view, diagnostics,
recovery and cycle profiling (step stats); GRAPH AUTO/HOME and ST CHANGEOVER in
the press; cylinder, two-hand, digital-input and air-pressure CMs; simulated
plant; native HMI direct link (`s7web://`, entered login) and gateway transport.

## 3. Gap census

### 3.1 Line profile — baseline gaps (Core §3.8e, §8.5.2)

| Missing | TC3 reference | Effect today |
|---|---|---|
| `LINE_CFG` values (owner, read-only mirrors, revision, staleness) | `FB_LineData`, IMPL_NOTES §139/§145 | no shared line config; the HMI's Line data group is empty |
| Line sources (local owner, cross-controller) | `FB_LineLocalSource`, `FB_LineAdsSource` | — |
| Shift calendar, automatic shift close, bounded shift history, per-shift targets | `FB_ShiftSchedule`, `ST_ShiftCalendarV3`, IMPL_NOTES §140 | `CurrentShift`, `ShiftHistory*`, `ShiftProductionTarget` not published; shift facet empty |

### 3.2 Production statistics (Core §8.5.1, §8.11)

| Missing | Effect |
|---|---|
| OEE (`Oee`, `OeeTrend`, availability/performance/quality) and `RESET_OEE` | OEE card empty |
| Standardized `MachineState` (§8.11.3) | machine-state chip/OEE basis missing |
| Per-model ideal cycle / work baseline and `CYCLE_TIME_DEGRADED` watch (§8.11.4(d)) | no degradation alarm |

Counts (`GoodCount`/`NokCount`/`ReworkCount`), cycle profile and step stats exist.

### 3.3 Operator and engineering facets

| Missing | Core | Request kind(s) |
|---|---|---|
| Run styles, single step, hold-to-run | §3.4.2 | `SET_RUN_STYLE`, `STEP_REQUEST`, `SET_HOLD_RUN` |
| Hold-to-run manual commands | §7.6.1a | `MANUAL_HELD` |
| Alarm shelving | §8.10 | `SHELVE_ALARM`, `UNSHELVE_ALARM` |
| Signal tower and lamp test | §8.13 | `LAMP_TEST` |
| Data classes, per-value access levels | §3.8d | `SET_CLASS_LEVEL` |
| Runtime model creation | §3.8 | `CREATE_MODEL` |
| Capture current value into a set record (verify against the existing current-config export) | §3.8b | `CAPTURE_CONFIG` |
| Engineering-gate register and standing annunciation (`USE_SIMULATION` is a constant today but not declared) | §7.5 | — |
| System health and condition monitoring (CPU/cycle/clock, declared exclusions) | §2.7, §8.12 | — |
| Nameplate (asset identity) | §3.10.1 | — |
| Host events / MES transaction set | §11.6 | — |

### 3.4 I/O and fieldbus (Core §10.2.1, §10.5)

`FB_IoTopologyPublisher` equivalent, project I/O catalog (`IoTag`/`Address` on
channels and diagnostics), PROFINET bus health (plan C19 `FB_PnBusHealth`), the
fieldbus page and output forcing (`FORCE_CHANNEL`, needs the engineering gate).
None exist; the press sensor CMs therefore omit TC3's `IoTag` fields.

### 3.5 Modules (plan §7.2)

| Module | Status |
|---|---|
| `FB_ClampEM` (EM tier, rollup proof T6) | complete (Phase P9) |
| `FB_ConfigurableCylinderCM` + sim | complete (Phase P9) |
| `FB_SeparatorCM` | complete (Phase P9) |
| `FB_AxisCM` / press `PartFeed` | missing; blocked by S14 (technology objects); excluded by owner decision |
| Robot (`FB_RobotCM`, route planner, connectors) | missing; needs S13/S14 |
| Vision / code reader (`FB_Iv3VisionCM`, `FB_Matrix220CM`, `FB_AsciiDeviceCM`) | missing; needs S13 |
| Device connector base, ASCII link, TCP channel | missing; needs S13 (OUC TCP) |
| `FB_PowerGroupCM`, control domain, safety mirror | out of scope (D3) |

### 3.6 Sequences

- GRAPH renditions of CHANGEOVER and LoadPosition: complete with automated rendition gate (Phase P10).
- Two-hand start from READY (TC3 calls `Start()` on the armed edge); TIA starts from the HMI only.
- Decision audit text renders `option=+2` (TIA `INT_TO_STRING` sign).

### 3.7 Gates, tests and contracts

| Missing | Plan / Part IV |
|---|---|
| Full R3 freeze beyond the implemented candidate subset (see progress below) | Phase 1, R3 |
| `Invoke-FraktalTiaGate.ps1` (lint → generate → import/compile → bench) and a fresh-clone gate | Phase 2, R4 |
| `FRK_Test*` framework, `fraktal_tia_test.py` runner/JUnit, `Tests/Fraktal_Tests_TIA`, `PressTests_TIA` | §7.4, R5 |
| Security record (zone/conduit, web users/rights, UMAC on V3.1+, PIN length policy) | R6 |
| Core module-band reasons in the generated rationalization table (today only `E_Reason` names) | §8.8 |

### 3.8 Deployment and targets

Gateway installer/tray do not offer `s7web://` instances; no physical S7-1500
(reference conformance needs one); S7-1200 constrained profile not cut; optional
OPC UA projection (S10) unproven; online-extension workflow (S6) and abrupt-loss,
endurance and full-download retention gates remain open.

## 4. Line profile — detailed design for Fraktal/TIA

Follow Core §3.8e/§8.5.2 and the TC3 decisions in IMPL_NOTES §139/§140/§145;
nothing below changes the Core contract or the HMI.

1. **Declaration.** A top-level `line` block in the station declaration:
   `{"id": "PRESS-LINE-1", "role": "OWNER"|"MIRROR", "roots": ["PressDemo"],
   "values": [...], "shifts": {"slots": N, "targets": true}, "stale_after_ms": …}`.
   Line values use the existing typed config field grammar; the generator
   refuses a `LINE_CFG` key that does not begin `line.` and any other kind that
   does (TC3 `M_RegisterConfigWrite` rule).
2. **Where it lives.** Generated beside the roots in the composition root (like
   the persistence and access stores), never a Unit child or registry row. The
   first referencing root hosts the per-scan tick and lends its alarm log for the
   staleness event; others only reference it.
3. **Owner.** Values are registered as `LINE_CFG` write capabilities through the
   existing typed config service, so `WRITE_CONFIG`, access classes, audit and
   sets need no new path. Every accepted write raises a persistent `Revision`;
   the line image is rebuilt only when the revision moves.
4. **Presentation.** Each referencing root's config manifest publishes the line
   values under its own scope with items prefixed `Line/`, and routes `line.*`
   writes to the line; every referencing root bumps `ConfigRev` on a revision
   change so clients re-read the manifest.
5. **Mirror.** A mirror applies a new revision whole or not at all (stage every
   record through its typed handler, then commit), publishes values with
   `Writable := FALSE`, refuses writes/captures/set records, and publishes
   `Stale`, `LastUpdate` (with clock quality) and `SourceError`, raising
   `std.error.lineDataStale` as LOW/SYSTEM AUTO_RESET. Every boot re-applies once.
6. **Sources.** Phase L1: local source (owner on the same CPU). Phase L2:
   cross-controller source. PUT/GET and S7CommPlus are rejected (Part IV §1);
   candidates are an Open User Communication TCP client polling the owner's
   published image (needs S13) or a host-mediated source in which the gateway
   copies the owner's image into the mirror's mailbox. **Owner decision needed.**
7. **Persistence.** The line image is a new LOAD_DB document (owner: values and
   revision; mirror: last applied revision and image), using the existing medium
   with read-back durability.
8. **Shifts.** Calendar keys `line.shift.utcOffsetMin`, `line.shift.<n>.startMin`,
   `line.shift.<n>.activeDays`, `line.shift.<n>.durationMin`,
   `line.shift.<n>.target` (V3 shape; slot count from the Core capacity). The
   Unit closes shifts on the synchronized clock, latches the closed record
   (counts, OEE, target snapshot) into a bounded `ShiftHistory`, and publishes
   `CurrentShift`, `ShiftStartedAt`, `ShiftProductionTarget`. Shift close is
   framework work; projects write nothing.
9. **Tests.** Generator unit tests (keys, manifest, refusal paths, capacity),
   a native bench `Tests/Line` (owner edit → revision; mirror whole apply,
   wrong-id/partial refusal, staleness raise/clear, restart re-apply; shift
   rollover with simulated clock; history bound), the live generic HMI Line
   group and shift facet, and the press declaring a one-station line.

## 5. Ordered roadmap

Each phase ends in evidence (dated report + archive) and leaves the press runnable.

| # | Phase | Contents | Depends on | Size |
|---|---|---|---|---|
| P1 | Line owner + local mirror | §4 items 1–5, 7; press declares a line | — | L |
| P2 | Shifts | §4 item 8; shift facet live | P1 | M |
| P3 | Machine state + OEE | `MachineState`, `Oee`/`OeeTrend`, `RESET_OEE`, per-shift OEE close | P2 | M |
| P4 | Baseline/degradation | per-model ideal/baseline (model seeds exist), `CYCLE_TIME_DEGRADED` | P3 | S |
| P5 | Engineering gates + system health + nameplate | declare `USE_SIMULATION`; health with declared exclusions | — | M |
| P6 | Operator facets | run style/step/hold-run, `MANUAL_HELD`, shelving, signal tower + lamp test | P5 (tower uses gates) | L |
| P7 | Data classes, model creation, capture | `SET_CLASS_LEVEL`, `CREATE_MODEL`, `CAPTURE_CONFIG` | P1 (line classes) | M |
| P8 | I/O topology + PROFINET health + forcing | catalog, `IoTag` on CMs/diagnostics, fieldbus page, `FORCE_CHANNEL` | P5 | L |
| P9 | Modules | `FB_ClampEM`, configurable cylinder, separator (complete) | — | M |
| P10 | GRAPH CHANGEOVER/LoadPosition | Phase 7 parity with rendition gate (complete) | — | M |
| P11 | Host events / MES | §11.6 fixed set over the existing delivery FIFO | P3 | M |
| P12 | Cross-controller line source | §4 item 6 (OUC TCP or host-mediated) | P1, S13 or gateway work | L |
| P13 | Contracts, gates, test runner | R3 frozen contracts, R4 gate script, R5 `FRK_Test*` + runner + suites | — (start early) | L |
| P14 | Deployment | installer/tray `s7web` instances, signed package, physical S7-1500, R6 record | P13 | L |
| P15 | Connectors, vision, robot, axis | S13/S14 spikes first | S13, S14 | XL |

Recommended start: P13's contract freeze in parallel with P1, because every
later phase adds published surface that the frozen contract must then cover.

### Implementation progress

**November 10 GRAPH CHANGEOVER & LoadPosition Renditions milestone — Phase P10.**
Phase P10 GRAPH rendition parity and automated gate are completed:
- `fraktal_tia_graph.py`:
  - `dump()` enhanced to trace connection topologies bidirectionally through `BranchRef` (`AltBegin`, `AltEnd`, `SimBegin`, `SimEnd`), resolving all exit transitions and destinations without unmapped nodes.
  - `scl_edges()` updated to parse both `"FRK_SeqRoute"` and `"FRK_Seq_Advance"` across arbitrary parameter ordering and multiple exits (`OnAdvance`, `OnJump1`), filtering disabled targets (`-1`).
  - `parity()` updated to filter dead-end terminal self-loops (`when: FALSE`) and support auxiliary wait step contraction (`auxiliary={...}`) for native simultaneous parallel joins.
  - CLI `parity` command extended with optional auxiliary step filter.
- Parity and mutation testing:
  - `test_fraktal_tia_graph.py` adds tests for multi-keyword argument order in `scl_edges()`, dead-end loop filtering, and auxiliary contraction.
  - `test_fraktal_tia_examples.py` adds `PressGraphRenditionGate` proving 100% parity across all 4 Siemens press sequences: `PressDemoChangeover` (6 steps, alternative jump 880->810 / advance 880->999), `PressDemoLoadPosition` (4 steps), `PressDemoHome` (4 steps), and `PressDemoAuto` (19 steps, simultaneous parallel branch contraction).
  - Explicit mutation tests verify that modifying any advance or jump target in `Changeover`, `LoadPosition`, or `Auto` is detected by the rendition gate with exact diff reporting.
- Native build and bench:
  - 286 replayed sources compiled cleanly in TIA Portal V20 with 0 errors and 0 warnings.
  - PLCSIM Advanced bench passes 93/93 live in-PLC assertions.
  - All 281 tool tests pass (`test_fraktal_tia_graph`, `test_fraktal_tia_examples`, `test_fraktal_tia_reusable_modules`, etc.).
  - `check_consistency.py --strict` passes with 0 errors and 0 warnings.
  - `tia_lint.py` passes with 0 findings.

**November 10 Core Reusable Modules milestone — Phase P9.**
Phase P9 reusable modules are implemented and verified:
`FB_ClampEM` (Equipment Module tier archetype managing child cylinders with parallel commands,
child fault/hold rollups, settle time verification, and derived `Clamped`/`Unclamped` state flags);
`FB_ConfigurableCylinderCM` (configurable single/dual solenoid cylinder CM with redundant 4-sensor
supervision, discrepancy timing, pulsing valve drive, settle time, plausibility check, and simulation block
`FB_ConfigurableCylinderSim`);
`FB_SeparatorCM` (parts singulation/escapement actuator CM with 5-phase SEPARATE sequence, OPEN_CLOSE command,
carrier arrival/clearance supervision, and optional open feedback).
Typed sequence APIs (`clamp_api.scl.in`, `configurable_cylinder_api.scl.in`, `separator_api.scl.in`) and
simulation models delivered under `Framework/Modules`. Layout generator routes them to their respective
program folders. Dedicated unit test suite `test_fraktal_tia_reusable_modules.py` added; all 274 engineering
tool tests pass. TIA Portal V20 native compilation builds 286 replayed sources with 0 errors and 0 warnings.
PLCSIM Advanced bench passes 93/93 live in-PLC assertions.
*Correction, 2026-11-10:* neither figure covered the P9 types (286 is the press replay; the 93
assertions are the Operations fixture). Their first native compile found two positional `SEL`
calls in `FB_ConfigurableCylinderCM`; both are fixed, lint rule T-FORMAL now rejects the form, and
the gate compiles a reusable-module fixture on every run. Compile/read-back only — no P9 type has
run natively. See [the native record](../Evidence/TIA_P9_MODULES_NATIVE_2026-11-10.md).
*Runtime, 2026-11-10:* a 46-assertion native suite mirroring the TC3 rows now runs in the gate.
Unfixed code failed 6 checks from three port defects (abort/timeout coil reactions overridden,
HELD consuming `MoveTimeout`, separator close delay without `CheckAfter`); fixed code passes 46/46.
See [the runtime record](../Evidence/TIA_P9_MODULES_RUNTIME_2026-11-10.md).

**October17 Line press milestone — generator 0.25.**
[Measured scope and evidence](../Evidence/TIA_LINE_PRESS_2026-10-17.md):
P1 local-owner/press integration and public complete-profile admission are
implemented. The press declares its Line beside station/model config through
one shared V3 calendar contract; Main gains no service wiring. The reserved
CPU1516 passes 37 Line and 64 wired-GRAPH checks, including atomic sets, target
latching, model coexistence and actual restart. Fresh-project native builds
pass both stages with zero errors/warnings; 617 canonical objects, 162 interfaces
and 71 DB interfaces match read-back. All 266 engineering tests pass. Complete
bound-mirror admission retains whole-image validation; the synthetic provider
does not implement P12. OUC TCP, MANUAL_HELD, I/O/modules, durable host delivery,
reusable connectors and remaining conformance/deployment gates stay open.

**October17 runtime models milestone — generator 0.24.**
[Measured scope and evidence](../Evidence/TIA_RUNTIME_MODELS_2026-10-17.md):
P7 bounded root catalogs, model/set cloning, per-field read/write admission,
BUSY isolation and atomic LOAD_DB catalog/config recovery pass 31 PLC assertions
and 110 live checks. Existing indices and the running/prepared recipe remain
unchanged during creation. Model set loads now share cache reservation/commit
and active-model persistence; actual restart and missing-row repair pass.
The press opts into capacity 4 over its three seeds. Fresh-project native
read-back and the existing GRAPH/LD parity gates remain required. P7's three
software features (classes, creation and capture) are implemented; full Line
press integration/admission, MANUAL_HELD, OUC, I/O/modules, durable host delivery,
reusable connectors and the remaining conformance/deployment gates stay open.
Roadmap §7 is applied: Core owns typed catalog semantics and the existing
Siemens persistence instructions own the medium.

**October16 data classes milestone — generator0.23.**
[Measured scope and evidence](../Evidence/TIA_DATA_CLASSES_2026-10-16.md):
P7 root class policies, raise-only value minima, redacted manifests, typed
write/capture/set/export admission and independent LOAD_DB recovery pass16 PLC
assertions and97 live checks. Existing action-policy layouts and document
identities are preserved. The current press passes both native compile stages,
read-back and GRAPH/LD parity;254 tool tests pass. Runtime model creation and
full Line-profile press integration remain. Roadmap§7's native-first guidance
is applied: Fraktal owns class semantics; the native persistence medium is kept.

**October16 operations milestone — generator0.22.**
[Measured scope and evidence](../Evidence/TIA_OPERATIONS_GRAPH_2026-10-16.md):
P2/P3/P4 algorithms and two-root integration pass native/runtime checks;
P5 health/nameplates/build gates are implemented with explicit metric/time
exclusions. P6 pacing, shelving and signal tower/lamp test pass; MANUAL_HELD
remains. P7 typed capture passes; classes/model creation remain. P10 wired GRAPH
CHANGEOVER/LoadPosition, jumps and pacing pass native read-back/live checks.
P11 now has the fixed bounded host ring and central lifecycle producers; durable
FIFO/MES delivery remains. P13 now has the native assertion runner and fresh
project compile/read-back/download/cleanup gate (93 PLC assertions,248 tool
tests); this does not close the full contract/suite or physical R-gates.
The normal generator still refuses incomplete Line profiles. The original
Fraktal runtime and physical1214C remain unchanged.

**P13 started — candidate contract gate.** The immutable
[V1 subset](../../../FraktalCore/PLC/Siemens/Contracts/TIA_FROZEN_CONTRACTS_V1.json)
and [`check_tia_contracts.py`](../../../tools/check_tia_contracts.py) now compare
31 implemented Core records, 22 referenced enum domains, eight referenced
capacities, native type widths, sequence table dimensions and the HMI datatype
map. Full-profile package/native checks require every frozen UDT and verify
ordered fields and all three external-access flags. Part IV binds the baseline
hash; checks never rewrite it. Pre-commit and hosted CI run the gate; CI also
runs Siemens lint, tool tests and shipped-package replay.

This is the first P13 slice, not R3/R4/R5 completion. Coherence, clock quality,
optional OPC UA and S7-1200 remain provisional; the native orchestration script,
PLC test runner and broader suites remain open. P1's engine and shared-owner
workbench progress is recorded above; P12 transport decisions do not block it.

**P1 prerequisite complete:** station and model config capabilities now refuse
the reserved `line.*` namespace, with both cases tested. Owner/local mirror,
replication, persistence and Line presentation are now measured on the isolated
workbench. Owner sets/current export and a bound synthetic mirror source with
durable offline restore are also measured. Shifts (P2), classes/capture (P7),
press integration and complete-profile admission are now implemented, as
recorded above. Normal generation continues to refuse partial Line profiles.
P12 transport is separate and is not implemented by the synthetic source fixture.

**Physical bench companion added at the owner's request:** the
[1214C I/O bridge and matching simulator driver](../Evidence/TIA_PRESS_IO_BRIDGE_2026-10-15.md)
compile and pass native protocol/read-back gates. Its output commissioning
gates remain disabled. It supplies bench connectivity without claiming the
S7-1200 Fraktal profile or closing P8's generic topology/PN-health scope.

**P8 topology/bridge slice measured (October17):** the
[live bench report](../Evidence/TIA_PRESS_BENCH_TOPOLOGY_2026-10-17.md) records
3 generic topology nodes, 14 fresh inputs and 10 unconfirmed DQ channels, all
derived from the approved I/O catalog. A separate saved FraktalBench exchanges
OUC frames with the physical 1214C, with both streams initiated by the controller.
The staged generic HMI and bench power-loss/recovery checks pass. Output
commissioning gates remain FALSE; native PROFINET health/forcing, applied-output
feedback and physical motion/SAT acceptance remain open. This does not close
P8 as a whole or implement P12 Line transport.

**P8 output forcing (November 10):** [the forcing record](../Evidence/TIA_OUTPUT_FORCING_2026-11-10.md)
adds Core §10.5.1 forcing behind the framework `OUTPUT_FORCING` gate: absent from
the shipped press, generated into an engineering image with request, per-scan
idle-MANUAL permit, falling-edge withdrawal, driver apply and per-channel audit.
Both press images compile 0/0 with read-back; the Operations fixture adds 15
native forcing assertions. Still open in P8: native PROFINET node health (blocked
by the approved Openness driver, which cannot create an IO system), annunciating
the CPU's own force jobs, the live press force path over the Web API, applied-
output feedback and physical acceptance.

**P8 applied-output feedback (November 10):** [the feedback record](../Evidence/TIA_OUTPUT_FEEDBACK_2026-11-10.md)
(owner decision 4A): bridge wire version 2 returns the 1214C's applied outputs;
the topology publishes them per DQ tag with quality while the report is valid.
Both bridge sides compile 0/0 with native read-back; nothing is downloaded, and
both endpoints need the owner's download authorization.

**P8 PROFINET node health (November 10):** [the PROFINET record](../Evidence/TIA_PROFINET_HEALTH_2026-11-10.md)
(owner decision 2A): the approved, whitelisted driver build creates IO systems,
devices and modules; a topology node bound to a PROFINET device takes its link
and state from `DeviceStates` (sampled per IO system) with the device number from
`LOG2GEO`. The new `Tests/ProfinetHealth` suite compiles 0/0 with read-back in
the native gate; its runtime assertions and the force-job spike (3B) wait for
the PLCSIM manager to return to TCP/IP mode. Still open in P8: CPU force-job
annunciation, the live press force path, ModuleStates/OB event detail and
physical acceptance.

## 6. Decisions for the owner

1. **Cross-controller line transport** (P12): owner selected **OUC TCP between
   the PLCs** on October16. Single-controller lines need no external transport.
2. **Shift calendar version**: adopt V3 (per-shift targets, active days,
   duration) directly; V2 migration is not needed on TIA.
3. **Physical S7-1500** for reference conformance (plan §4.1), and whether the
   1214C constrained profile is still wanted.
4. **Scope of P15**: owner selected **reusable connector infrastructure** on
   October16. Device-specific robot, vision and axis ports remain deferred
   until their actual targets are specified.

## 7. Native S7-1500 first

Added 2026-10-16. Fraktal/TIA should not re-implement what the S7-1500 already
provides; where the Core contract requires its own behaviour it keeps it and,
where useful, also **projects** onto the native mechanism. Verdicts were checked
against the generated sources on 2026-10-16; Web API alarm methods (firmware
V3.x) and the LGF library come from Siemens documentation and are to be
confirmed for the target firmware before use.

### 7.1 Already native — keep

| Function | Native mechanism in use |
|---|---|
| Monotonic clock / UTC time | `RUNTIME`, `RD_SYS_T` |
| Module identity | `GetInstancePath` |
| Persistence medium | `WRIT_DBL`/`READ_DBL`, UNLINKED load-memory DBs, `Serialize` |
| Cycle statistics (health) | `RT_INFO` |
| PLC-to-PLC links (I/O bridge; P12 line transport by owner decision) | Open User Communication `TCON`/`TSEND_C`/`TRCV_C` |
| Self-description transport | licence-free Web API |

### 7.2 Contract-required — keep, add a native projection

| Fraktal service | Native counterpart | Why Fraktal keeps its own | Action |
|---|---|---|---|
| Alarm log (first-out, reset classes, history, recovery, delivery) | `Program_Alarm`/ProDiag, CPU alarm display, Web API `Alarms.Browse`/`Acknowledge` | §8 alarm model must match TC3/AB; native alarms lack first-out SourcePath, reset classes and the §6.9 walk | **N1**: optionally raise every Fraktal event as a `Program_Alarm` with the same text key and severity, so TIA, the web server, a display and WinCC see it; acknowledgement stays in the Fraktal path |
| Sequence step record, stall diagnostics, step timing | GRAPH step times, supervision/interlocks, ProDiag criteria analysis | identical behaviour for ST and LD chains, which have no GRAPH supervision | **N2**: for GRAPH-only stations, evaluate feeding GRAPH supervision into the stall record instead of computing it twice; keep the ST/LD path |
| Operator users with salted PINs (Core §14) | UMAC (FW V3.1+), web-server users (FW V3.0) | per-root levels and audit; the reference CPU is V3.0 | **N3**: on V3.1+ targets, offer a UMAC-backed login provider; the in-SCL SHA-256 then becomes the fallback provider only |

### 7.3 Duplication to review

| Fraktal code | Alternative | Verdict |
|---|---|---|
| SHA-256 in SCL (`FRK_Sha256Pin`) | none native; UMAC provider (N3) avoids hashing on the PLC | keep for V3.0 targets |
| CRC-32 in SCL (persistence integrity) | Siemens LGF library `LGF_CalcCRC32` | keep (one owned, tested implementation) unless LGF becomes an accepted dependency |
| Named config sets as JSON | `RecipeExport`/`RecipeImport` (CSV on the card, served by the web server), `DataLog*` | **N4**: keep JSON for the generic HMI; optionally also export sets as native recipe CSV for maintenance |
| Own millisecond timers on the shared clock | IEC `TON` | keep: needed for idle-module quiescence and HELD timeout suspension; `TON` per module costs more |
| Hand-entered nameplate records | I&M data (`Get_IM_Data`) of the CPU and modules | **N5**: fill CPU/module nameplates from I&M at startup; keep declared fields only for what I&M cannot hold |

### 7.4 Rules for the open phases

- **P5 health**: take PROFINET and module health from `DeviceStates`/`ModuleStates`
  and the CPU's own diagnostic status; declare anything the CPU cannot supply
  as an exclusion (as AB does for controller metrics) instead of synthesizing it.
- **P8 I/O topology and fieldbus**: build on `DeviceStates`/`ModuleStates`,
  `Get_Diag`, `RALRM` and the diagnostic/rack-failure OBs (OB82/OB86) and the
  configured PROFINET topology. Do **not** port TC3's EtherCAT scanner; the CPU
  already reports device health.
- **P8 forcing**: native forcing exists only in TIA Portal (no runtime API), so
  the HMI forcing path stays Fraktal's; it must honour the CPU's own force state
  and annunciate it.
- **P11 MES**: deliver host events through the existing FIFO and, where the
  OPC UA licence is present, map them onto OPC UA Alarms & Conditions rather
  than a second transport.
- **Review question for every new SCL service**: name the native S7-1500
  instruction or system function it replaces, or state why the Core contract
  needs its own (record the answer in the evidence report).
