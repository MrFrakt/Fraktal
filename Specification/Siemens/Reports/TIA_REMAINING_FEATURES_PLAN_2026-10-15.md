# Fraktal/TIA — remaining features and implementation plan (2026-10-15)

A census of what the Siemens binding still lacks against the TwinCAT reference,
taken after the press demo first ran end to end on the simulated CPU1516
([press evidence](../Evidence/TIA_PRESS_COMPLETE_2026-10-15.md)), and an ordered
plan to close it. Line configuration is planned in detail because it is the
largest functional gap an operator meets. This is a plan, not a claim: every
item below is **not implemented** unless the census says otherwise.

Continuation, 2026-10-15: **P1 is in progress.** The shared typed line engine now
has native owner/mirror, atomic-image, staleness/event and image-reapplication
evidence. See [line engine evidence](../Evidence/TIA_LINE_ENGINE_2026-10-15.md).
Continuation, 2026-10-16: the isolated owner composition now shares its normal
mailbox/manifest and one LOAD_DB document across two roots. Native compile,
read-back and 54 live checks include an actual simulated power cycle after
corrupting the working cache. See [owner evidence](../Evidence/TIA_LINE_OWNER_2026-10-16.md).
Named line sets, a bound mirror source, shifts and press integration remain.
Normal generation refuses the partial profile (Core 1.5); the explicit workbench
API is for isolated tests only. The census below continues to describe the
shipped press; the Line profile is not closed.

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

### 3.1 Line profile — not implemented (Core §3.8e, §8.5.2)

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
| `FB_ClampEM` (EM tier, rollup proof T6) | missing |
| `FB_ConfigurableCylinderCM` + sim | missing |
| `FB_SeparatorCM` | missing |
| `FB_AxisCM` / press `PartFeed` | missing; blocked by S14 (technology objects); excluded by owner decision |
| Robot (`FB_RobotCM`, route planner, connectors) | missing; needs S13/S14 |
| Vision / code reader (`FB_Iv3VisionCM`, `FB_Matrix220CM`, `FB_AsciiDeviceCM`) | missing; needs S13 |
| Device connector base, ASCII link, TCP channel | missing; needs S13 (OUC TCP) |
| `FB_PowerGroupCM`, control domain, safety mirror | out of scope (D3) |

### 3.6 Sequences

- GRAPH renditions of CHANGEOVER and LoadPosition (Phase 7); CHANGEOVER is ST only.
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
| P9 | Modules | `FB_ClampEM`, configurable cylinder, separator; two-hand start from READY | — | M |
| P10 | GRAPH CHANGEOVER/LoadPosition | Phase 7 parity with rendition gate | — | M |
| P11 | Host events / MES | §11.6 fixed set over the existing delivery FIFO | P3 | M |
| P12 | Cross-controller line source | §4 item 6 (OUC TCP or host-mediated) | P1, S13 or gateway work | L |
| P13 | Contracts, gates, test runner | R3 frozen contracts, R4 gate script, R5 `FRK_Test*` + runner + suites | — (start early) | L |
| P14 | Deployment | installer/tray `s7web` instances, signed package, physical S7-1500, R6 record | P13 | L |
| P15 | Connectors, vision, robot, axis | S13/S14 spikes first | S13, S14 | XL |

Recommended start: P13's contract freeze in parallel with P1, because every
later phase adds published surface that the frozen contract must then cover.

### Implementation progress

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
replication, persistence and Line presentation remain open.

**Physical bench companion added at the owner's request:** the
[1214C I/O bridge and matching simulator driver](../Evidence/TIA_PRESS_IO_BRIDGE_2026-10-15.md)
compile and pass native protocol/read-back gates. Its output commissioning
gates remain disabled. It supplies bench connectivity without claiming the
S7-1200 Fraktal profile or closing P8's generic topology/PN-health scope.

## 6. Decisions for the owner

1. **Cross-controller line transport** (P12): OUC TCP client on the mirror PLC,
   or host-mediated through the gateway. Single-controller lines need neither.
2. **Shift calendar version**: adopt V3 (per-shift targets, active days,
   duration) directly; V2 migration is not needed on TIA.
3. **Physical S7-1500** for reference conformance (plan §4.1), and whether the
   1214C constrained profile is still wanted.
4. **Scope of P15** (robot, vision, axis): keep excluded until the press is
   physically accepted, or schedule the S13/S14 spikes now.
