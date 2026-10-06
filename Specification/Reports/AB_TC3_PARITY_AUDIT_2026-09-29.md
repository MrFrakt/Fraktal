# Fraktal/AB against Fraktal/TC3 — parity audit and implementation plan

**Date:** 2026-09-29 · **Revision audited:** `1c9854d` (press27)
**Scope:** everything the TwinCAT binding does that the Allen-Bradley binding
does not, measured against the TC3 press demo. That comparison matches the goal
the owner set for the AB bench: *"almost identical to the TC3 version, only
excluding power on."*

This is a report of what **is**. The decisions it asks for are listed in §7 and
are not taken here.

**Current assessment (2026-10-04):** main operating parity and the scoped
Phase 0-6 work are verified on press68; this is not a complete TC3 press port
except power. Part traceability, line/shifts, signal-tower/host integration and
optional profiles/probes remain absent/unclaimed. Press69 extends the port
with offline-tested inactive model creation/current export and Changeover
entry-permit scope. Owner Studio Verify then refused eight nested-array subscript
uses in press69; corrective press70 is prepared, with no extra declared storage
over press69, pending owner Verify/download/live acceptance. The owner's request
to finish the port now extends the prior phase scope: see the
[completion plan](../AllenBradley/AB_PORT_COMPLETION_PLAN_2026-10-04.md) and
[correction record](../AllenBradley/Evidence/AB_PHASE6_SUBSCRIPT_FIX_2026-10-04.md).
Read the
[current guide](../Guides/AB_NEW_PROJECT_GUIDE.md) and
[TC3 lessons handoff](../AllenBradley/AB_TO_TC3_HANDOVER_PROMPT_2026-10-04.md).
The September 29 counts and dated progress below are retained history.

---

## 1. Summary

| | Count |
|---|---|
| Paths the HMI reads that AB does not publish | **51**, under 10 recorded reasons |
| Mailbox commands AB refuses by name | **26** |
| TC3 press modules absent from the AB press | **4** (plus 1 deliberately excluded) |
| Defects found by this audit | **4**, two of them introduced today |

The headline is not the count. Three gaps change what an operator can safely
rely on, and they come first in the plan:

1. **A faulted AB press raises no alarm.** The HMI's global banner, alarm list
   and history read only `AlarmLog`. AB publishes each module's
   `Status/Diagnostic/ReasonCode`, which turns the module red in the tree and
   shows its diagnostic on its own card, and nothing else. An operator watching
   the banner does not see the fault.
2. **A blocked control cannot explain itself.** §7.6 act-or-explain depends on
   `RELEASE_START`/`RELEASE_MANUAL`/`RELEASE_ACTION`, and AB refuses all three.
3. **A stalled step cannot say what it is waiting for.** `CurrentStep/Conds`,
   the §6.5 pending step record, is deferred. The step is named, but not the
   condition it is waiting on.

One constraint governs the order of everything else. **Adding the four missing
press modules would overflow two manifest tables** (§5), so a manifest change
has to come before the module work.

## 2. How this was derived

Every row below traces to a source that can be re-read, so the audit can be
re-run rather than trusted.

| Source | What it gives |
|---|---|
| `tools/check_consistency.py` `AB_ABSENT` | Every path the HMI mapper reads that AB does not publish, each with its recorded reason |
| `fraktal_ab_mailbox.py` `refused_for(app)` | Every command the press refuses, with its refusal key |
| `FB_PressDemoUnit.TcPOU` module declarations | The eight modules TC3's press instantiates |
| `IMPLEMENTATION_NOTES.md` §1–§151 | TC3's feature history, to catch features with no HMI surface yet |
| Live reads from `7036B510` | What the loaded build actually publishes |

**Limitation.** The first two sources cover only what the HMI already reads or
sends. A TC3 feature that has no HMI surface yet cannot appear in either list.
The IMPLEMENTATION_NOTES pass exists to catch those, and it relies on reading
rather than on a machine check.

## 3. Already at parity

Built on AB and exercised on the bench. The last three rows are generated but
not yet compiled; see §4.

Manifest discovery with fail-closed ContentHash · module tree with type keys ·
mode control, Start/Stop, operator reset, manual jog · operator decisions ·
changeover across three models · fieldbus topology and §10.5.1 output forcing ·
§6.1 HELD with reason and severity · current step by name · ST/SFC/LD renditions
of AUTO, parity proved 17/17 · §3.8a StationCfg restore on `S:FS` · §3.8b
durability publication · editable configuration with controller-enforced bounds
· per-model stored data (**press27, not yet compiled**) · deployment-declared
access level.

## 4. Defects found by this audit

Fix these before any feature work. Two of them are in press27, which has not
been downloaded yet.

| # | Defect | Effect | Size |
|---|---|---|---|
| **D1** | The per-model restore handles `SchemaVersion = 0` and nothing else. An element with an unrecognized non-zero version is **kept and used as-is**. | Violates §3.8a: *"shall not be interpreted by field position … shall be annunciated."* A model image from a changed layout would drive the press silently. **Introduced today, in press27.** | S |
| **D2** | `ACK_CONFIG_RESTORE` is refused (`no_config_sets`). | The restore gate can raise `RestoreLost` and the durability banner offers **Acknowledge**, but AB refuses the acknowledgement. The annunciation can never be cleared. **Introduced today.** | S |
| **D3** | press27 has not been compiled. The SDK probe refuses with `No valid license`. press26 fails the same way in this session, so the cause is the environment and not the build. | It contains the first array-of-UDT tag and the first expression subscript (`Array[Tag - 1].Member`) this generator has emitted. | Needs the licensed desktop |
| **D4** | README line 45 still lists changeover, physical I/O and recipes as out of scope. | All three now exist, so the record contradicts the code. | S |

**Found after the audit, on the bench:**

| # | Defect | Effect | Size |
|---|---|---|---|
| **D5** | `QUERY_CONFIG` only reads, but it travels through the mailbox as a **write**, and both gateways refused every mailbox write in a read-only deployment. | Closed in Phase 6 item 1: only complete, inert page/model query batches acquire read authority, scoped to a readable root. Every mutation retains its gate, serialization and sequence checks. Press54 proves the no-bearer/no-write-root query and START refusal on the AB controller; TC3 has paired offline tests and mutations. [Hardware evidence](../AllenBradley/Evidence/AB_PHASE6_CAPTURE_ON_HARDWARE_2026-10-01.md). | M, both gateways; closed, AB on hardware / TC3 offline |
| **D6** | `/healthz`, `/livez` and `/readyz` do not say whether the write gate is on. | **Source fixed 2026-10-03 in both gateways:** the common `writeAccess` block reports configured mutation enablement and scope without credentials. Offline gates pass. **AB live readback passes 2026-10-04 after the owner's restart:** all three routes return HTTP 200, PLC ready and the expected Press scope. TC3 remains offline-tested. No PLC download or memory change. See [D6 implementation](../AllenBradley/Evidence/AB_PHASE6_D6_HEALTH_WRITE_ACCESS_2026-10-03.md) and [live activation](../AllenBradley/Evidence/AB_PHASE6_GATEWAY_ACTIVATION_2026-10-04.md). | S; closed, AB live / TC3 offline |
| **D9** | The gateway and the harnesses read the Unit and each module by member NAME, one DINT per name. press49 gave the cylinder its first arrays (5f command timing), and every member after them shifted. Found 2026-10-01 on press49: the gateway refused the station (degraded, PLC not ready), and the projection raised `TypeError` on the first shifted value. | Fail-closed held: nothing shifted was published. No fixture had packed a context as Logix lays it out. **Fixed in the reader, `582aded`, no download**: both read through the dimension-aware `read_layout`, and `test_fraktal_ab_readers` round-trips every structure as Logix lays it out (4 failures on the old reader). On the fixed reader every gate passes ([evidence](../AllenBradley/Evidence/AB_PHASE5F_COMMAND_TIMING_ON_HARDWARE_2026-10-01.md)). | S |
| **D8** | An OPERATOR_RESET restarted the press by itself. START raises `RunRequest`, a level; a fault stopped the chain but left it up; the reset only raised `ResetRequest`, so the run latch set `Running` again in the scan the fault cleared. Found 2026-10-01 on press42. | Against TC3's OperatorReset, which releases its own run command, and AGENTS' rule that a reset leaves the machine restartable, never restarted. Hidden until START refused a running Unit (`unitNotReady`). **Fixed in press43, on hardware 2026-10-01**: the reset lowers `RunRequest`; after it the press is stopped and START is accepted. | S |
| **D7** | The SFC rendition skipped a stroke whenever its module was still Done from its previous command. A commanding step's SFC transition read `Done` on its entry scan, and the SFC action never dropped `Execute` on completion. Found 2026-10-01 on press39, present since the SFC chart was first generated. | On every SFC cycle the door did not close at N180, the ram did not press at N200, and the slide did not go out at N244. Parity compared entry counts only, so it passed. The SFC cycle's 210 ms "speed" was the three skipped strokes. **Fixed in press40, on hardware 2026-10-01**: SFC 3/3, 3/3, 2/2 strokes in 976 ms. A whole-cycle model test and per-module command rows in the parity harness now cover it ([evidence](../AllenBradley/Evidence/AB_PRESS39_SFC_STALE_DONE_ON_HARDWARE_2026-10-01.md)). | S |

**Owed obligation (not a defect):** Part III's S9 row says *"no writable claim
until the contract suite passes"*, and the write-enabled mailbox matrix is still
owed. Writes were enabled today by explicit decision. The suite that would back
that decision does not exist yet.

## 5. The constraint that orders the plan

Every field path is interned as its own Localization key, per instance. The
three cylinders intern the same 32 member names three times, once under each
path.

| | Now | After adding the 4 press modules |
|---|---|---|
| Localization | 268 / 384 | **~404 / 384** |
| Fields | 161 / 192 | **~289 / 192** |

Fields can be raised: S7 measured it at 512 rows (16,384 B, 21.0 ms).
**Localization cannot be raised the same way.** 384 rows (15,360 B) is already
close to the largest table S7 actually read, and going past it would need a new
bench measurement before any claim.

The fix that scales is to make module-context field keys **relative to the
type rather than the instance**: one set of member keys per module type, shared
by every instance of it. That cuts the cylinders' 96 keys to 32 and makes each
further instance cost almost nothing, which is what §1.1 O4 asks of a published
surface. **This is prerequisite P0 below.**

## 6. Gap inventory

**Class:** **M** missing, should be built · **N** not claimed by recorded
decision · **X** not applicable to this bench · **D** deferred, recorded.
**Size:** S under a day · M one to three days · L more than three.
**⬇** means the item changes the ladder or tags, so it needs a download.

### 6.1 Operator safety and diagnosis

| Gap | TC3 | AB | Class | Size | ⬇ |
|---|---|---|---|---|---|
| Alarm log: active list, ring, come/gone, severity, source (§8.3) | yes | none; `AlarmLog` not projected | **M** | L | ⬇ |
| Alarm acknowledge | yes | none | **M** | M | ⬇ |
| Release reports / act-or-explain (§7.6), P2 | yes | refused `no_release_reports` | **M** | L | ⬇ |
| Pending step conditions, `CurrentStep/Conds` (§6.5) | yes | deferred | **M** | M | ⬇ |
| Diagnostic detail: `Since`, `IoTag`, `IoAddress` (§8 electrical-tag join) | yes | reason code only | **M** | M | ⬇ |
| `Blocked` / `Starved` state | yes | not projected | **M** | S | |

**The alarm log has to live on the controller**, not in the gateway. The same
principle stops §3.13 marks moving client-side: a gateway polling at a few Hz
cannot see a fault that clears in under one poll interval, so a gateway-built
log would lose exactly the transient faults it most needs to show.

### 6.2 Press module parity

| Module | TC3 type | AB today | Class | Size | ⬇ |
|---|---|---|---|---|---|
| TwoHand | `FB_TwoHandStartCM` | bare `TwoHand` sim tag | **M** | M | ⬇ |
| AirPressureMonitor | `FB_AirPressureMonitorCM` | bare `AirOk` sim tag | **M** | M | ⬇ |
| PartPresentSensor | `FB_DigitalInputCM` | bare `PartPresent` sim tag | **M** | S–M | ⬇ |
| PartFeed | `FB_AxisCM` | absent | **X**, no motion on this controller; see Phase 3 item 4 | — | |
| PneumaticPower | `FB_PowerGroupCM` | absent | **X**, excluded by the owner | — | |

AB's generator knows one module type, the cylinder. Each row is a new AOI
type, born in the reusable library that Phase 0 starts (§7, Q3). **All four
depend on P0 and on the library split.**

### 6.3 Sequence visibility

| Gap | AB today | Class | Size | ⬇ |
|---|---|---|---|---|
| §3.13 flow chart: `SequenceSteps`, `SequenceStepCount`, `ActiveSteps` | controller already holds `Visited[32]`, `LastMs[32]` and `EnterCount[32]`; the projection does not publish them | **M** | **S — projection only** | |
| `CurrentStep/ExpectedTime`, `TimeClass`, `AwaitingLabel`, `Class` | step timeouts are declared but not projected | **M** | S | |
| Per-row error/message marks and `SequenceAnnotations` | no marks on the controller | **M** | M | ⬇ |
| `SequenceViewEnabled` | not projected | **M** | S | |

This group has the best value for the effort in the audit. Most of the data is
already on the controller.

### 6.4 Production and operating modes

| Gap | AB today | Class | Size | ⬇ |
|---|---|---|---|---|
| OEE + trend + `RESET_OEE` (§8.5.1) | counts exist; no availability timing | **M** | M | ⬇ |
| Cycle-time profiler / `Timing` (§8.11) | `CurrentStepMs` and `LastMs` only | **M** | M | ⬇ |
| Derived state flags, `StateFlags` (§3.12) | none; derivable from module contexts | **M** | M | |
| `MachineState` (PackML) | not projected | **M** | M | |
| Run styles, `SET_RUN_STYLE` | refused | **M** | M | ⬇ |
| Step mode, `STEP_REQUEST` | refused | **M** | M | ⬇ |
| Hold-run, `SET_HOLD_RUN` | refused | **M** | S | ⬇ |
| Hold-to-run, `MANUAL_HELD` | refused by name | **X**: the only TC3 type with held commands is `FB_AxisCM` (jog ±), and the press's one axis is `PartFeed`, which this controller cannot host. No press module takes a held command on either binding; see Phase 5 | — | |
| `ReworkCount` | Good and Scrap only | **M** | S | ⬇ |
| Digital nameplate / AAS, `Nameplate` | not published; TC3's press sets none either | **N** for the press; a contract decision first, see Phase 5 | S | |
| Catalog, `CatalogCount` | not projected | **M** | S | |
| `SystemHealth`, time quality | publisher built over S3's subset (press52) | **M** | M | |
| Part traceability, `Part` (§3.16) | deferred | **D** | L | ⬇ |

### 6.5 Configuration completeness

| Gap | AB today | Class | Size | ⬇ |
|---|---|---|---|---|
| Parameter sets: save, load, list, export, import, delete | press55 verified on hardware, item 2 complete for station sets; model load refuses as TC3 until recipe-store integration | **M** | L | ⬇ |
| `CAPTURE_CONFIG` | press54 verified on hardware; item 1 complete | **M** | S | |
| Data classes with per-value access (§3.8d) | press67 hardware regression passes 18/18; class/minimum checks and atomic set permissions; full regressions/restoration pass; S9 and physical retention owed | **N**, write-profile | M | |

Part III already decides where sets live: *"the controller owns the values and
every validation, the gateway owns the document and the medium."* So this is
mostly gateway work, plus staging on the controller.

### 6.6 Access and security

| Gap | AB today | Class | Size |
|---|---|---|---|
| Per-user login, levels, session timeout, PINs as salted hashes (§7.7, §150) | press67 access regression passes 16/16 with bounded login latency and no task overlaps; original session restored and running gateway ready; S9 and physical retention owed | **M**, Q1 resolved | L |
| Write-enabled mailbox matrix / contract suite (S9) | press68 native vector 17/17, all eleven regressions/restoration and shared contract 75/75 pass; corrected live client passes 60 seconds, 121 updates, 224 detail batches, three new connections and S3 6/6; owner confirms browser stable; zero PLC growth | **PASS on the named press68 deployment**; other stations prove their own fit/budgets | M |
| Alarm shelving (§8.10) | **PASS** on press67: 15/15 hardware, identity/role and registry refusals, expiry after logout and history; all regressions/restoration pass; S9 remains owed | **M**, Phase 6 item 5 | M |

The gateway sees one bearer and cannot tell two people apart, and the mailbox
tag is externally writable, so a client that skips the gateway skips anything the
gateway enforces. Principals therefore live on the controller, PLC-authoritative,
as TC3 has them (§7, Q1).

### 6.7 Not claimed, by recorded decision or by the bench

| Gap | Class | Reason |
|---|---|---|
| Line data and shifts (§3.8e, §8.5.2) | **N** | The Line profile is not claimed, decided 2026-09-28 (G3 C) |
| Control power, `PowerGroup` | **X** | Excluded by the owner |
| Safety profile (§9.8) | **X** | No safety hardware on the bench |
| Signal tower, `LAMP_TEST` | **X** | The bench has none |
| Host events | **D** | MES-facing; low value on a bench |

## 7. Decisions: resolved by the owner's rule

The owner's rule governs all four: **the AB build shall be the same as the TC3
build.** Core O8 says what "the same" means across platforms: the normative
model is platform-neutral and *"each PLC platform is served by a binding that
maps the model onto that platform's language extensions and services."* So the
same contract and behaviour, mapped onto what Logix can do. None of these was
the owner's to answer. Each is recorded with what it costs.

| Q | Resolved as | Principle | What it costs on AB |
|---|---|---|---|
| **Q1** Per-user principals | **On the controller, PLC-authoritative, as TC3** (IMPLEMENTATION_NOTES §77) | O7, O10; HMI_CONTRACT: the PLC re-checks every mutation | `FRK_Press_HmiRequest` is `ExternalAccess="Read/Write"`, so any CIP client on the cell network can write the mailbox directly and bypass the gateway. Levels held only in the gateway protect nothing against it; only the controller can refuse. PINs are stored as salted, iterated SHA-256 (§150). v33 has no shift operator and no UDINT. Press61 failed its scan budget (32,136 µs, 771 overlaps). Press62 prepares a gateway-derived 256-hash prefix and one final hash compared on the PLC, with at most eight rounds per scan. Stored hashes and PLC role authority remain unchanged. State V3 correlates the result sequence. Press62 access and timing now pass the guarded hardware fixture; S9 remains owed. Part III's "enforces no per-user levels in the controller" is rewritten. `--access-level` becomes the pre-login level. Proxy basic_auth stays: §14 transport authentication and §7.7 per-user levels are two layers, as TC3 has OPC UA session authentication plus PLC levels. |
| **Q2** Type-relative field keys | **Build it (P0)** | O4 surface proportional to consumption; O9 one fact per type; O8 same contract | TC3 has no counterpart. OPC UA makes every field a native node, and no size-limited name table exists. So "the same" means the same **contract**: browse paths are byte-identical and only the manifest encoding changes. That needs a manifest schema version bump, and the projection, gateway and manifest reader change in one commit. It needs a download. There is **no HMI change**, because the HMI sees only resolved paths. Re-measuring S7 larger instead would buy one or two modules and then overflow again. |
| **Q3** Module library | **Start the reusable library now, as TC3's `Fraktal_Modules`** | O1: *"standardisation is paid once per reusable module type"*, and its trimming rule | Logix has no installable library. The equivalent is one AOI definition per type, with an AOI revision and signature, generated once and imported by every application (Part III Phase 6). Studio refuses a signature mismatch, so the platform enforces the versioning. The generator splits into "type library" and "application", and AOI names lose the application prefix. It has to come **before** the four modules, or they get written twice. |
| **Q4** Alarm log | **On the controller, at TC3's sizes** | O3 diagnosable by construction; O10 bounded rings | 16 active + a 64-entry ring per Unit, with 32 rationalization records (`PL_Fraktal` `MAX_ALARM_ACTIVE`/`MAX_ALARM_RING`/`MAX_ALARM_META`), taken from TC3 and not invented. It adds a per-scan edge check on each module's diagnostic, and acknowledgement travels through the mailbox. Each entry is DINTs plus numeric reason and source keys, which the gateway resolves to text as it already does for diagnostics. A gateway-built log is excluded: polling cannot see a fault that clears inside one poll. |

## 8. Implementation plan

Phases are ordered by dependency first and operator value second. Each phase
ends with a regenerate, the SDK import and Studio Verify, one download, and a
bench pass. Grouping the ladder changes this way keeps downloads, which are the
expensive step, to one per phase.

### Phase 0: foundations

**Status 2026-09-29: done.** D1 and D2 (`43f8f3f`), module-relative field keys
(`bb1eb5a`), the module library (`65999e7`) and the corrected records (D4) are
committed, at 847 AB tests. `press28.L5X` (`4D11673BCE65B2F2`) was compiled in
Studio v33 on the licensed desktop and downloaded, which closes D3. The SDK probe
on the bench workstation still refuses with `No valid license`. §146 parity was
re-run on press28 and passed 17 of 17, and the changeover commit and per-model
restore were read off the controller
([`Evidence/AB_PHASE0_ON_HARDWARE_2026-09-29.md`](../AllenBradley/Evidence/AB_PHASE0_ON_HARDWARE_2026-09-29.md)).

Two things the work turned up that the audit had not seen:

- The cylinder was generated once per **instance**, not per application. The
  three definitions differed only in a comment, and each read the context type,
  the task period and its reason codes from the application. The library fixes
  all of that.
- Fitting the manifest is bounded by the **whole** 43,728 bytes S7 read, not by
  any one table. Fields went to 384 and Localization down to 320. The build is
  36,200 bytes.

Closes §4 and puts every structural change before any feature is built on top
of it. **One download.**

1. **D1**: the model restore annunciates a rejected image and reinstalls
   defaults, the same gate as StationCfg.
2. **D2**: route `ACK_CONFIG_RESTORE` so it sets `RestoreAcknowledged`.
3. **P0 (Q2)**: type-relative field keys; raise Fields toward S7's measured 512.
4. **Type library (Q3)**: split the generator into a per-type AOI library, with
   AOI revision and signature, and an application that imports it. Move the
   cylinder into it first, so the four new types in Phase 3 are born in the
   library instead of migrating there later.
5. **D4**: correct the README and the Part III claim table.
6. **D3**: SDK import and Studio Verify of the result, on the licensed desktop.

### Phase 1: an operator can see and act on a fault

**Status 2026-09-30: done, on hardware.** press30 (`382A4E596132C0B0`) was
compiled in Studio v33 and downloaded; §146 parity re-passed 17 of 17, and
Phase 1's own features passed 7 of 7 on the controller
([`Evidence/AB_PHASE1_ON_HARDWARE_2026-09-30.md`](../AllenBradley/Evidence/AB_PHASE1_ON_HARDWARE_2026-09-30.md)).
The sensor a timeout names is not reachable through the harness write surface
and stays proved on the ST model.

**Status 2026-09-29: item 1 built offline, in `press29.L5X`
(`E659590E8F258906`), not yet imported or downloaded.** The controller keeps
`FRK_Press_AlarmActive` (16 slots, read every poll) and `FRK_Press_AlarmRing`
(64, a separate tag so a later gateway can re-read it only when `RingHead`
moves). The projection publishes both in the HMI's `AlarmLog/*` shape, plus the
§8.9 `AlarmLog/Meta[i]` rationalization from the manifest, so every alarm row
carries its operator action and consequence. `START` is refused with
`alarm_blocks_start` while a manual event is unreset (§8.3(b)).

Three things the work corrected:

- **Q4 said capture was a per-scan edge on each module's diagnostic. TC3 does
  not do that.** `FB_UnitBase` raises one MANUAL_RESET event on the Unit's own
  ERROR entry (`_faultEvt`), sourced to the module the rollup adopted, and marks
  it gone on exit. The binding does exactly that, because O8 asks for TC3's
  behaviour, not the audit's paraphrase of it.
- **TC3 logs more than faults.** Decisions, audited HMI commands, part events
  and maintenance are AUTO_RESET come+gone entries in the same log
  (`_M_LogDecision`, `_M_AuditHmiAccepted`, `_M_PartEvent`,
  `_M_RaiseMaintenance`). Not in this item; they arrive with the features that
  raise them.
- **Shelving was refused as `no_event_core`**, text "keeps no alarm history",
  which became false the moment the log existed. It is now `no_shelving`.

The log is the first routine tested by **running** it. `fraktal_ab_st_model.py`
executes the generated ST subset, strict where Logix is (an out-of-range
subscript is a major fault, so it raises), and `test_fraktal_ab_alarm_log.py`
drives it scan by scan. Thirteen deliberate mutations of the generated text,
from a ring modulus of 65 to a rounding millisecond, each fail at least one
test. First-compile risks the model cannot answer: `GSV(WallClockTime,…)` in
ST, `FOR`, and `MOD`, none of which this generator has emitted before.

**Item 2 needs no separate work.** TC3's `E_HmiRequestKind` has no acknowledge
kind: `OPERATOR_RESET` closing WAIT_RESET events *is* the acknowledgement, and
item 1 routes it. A per-alarm acknowledge would be surface TC3 does not have.

**Items 3 and 5 built offline, 2026-09-30.** Each condition a step waits on
carries a label in the declaration (TC3's own keys: AUTO N100 is
`partPresent`, `airPressureOk`, `twoHandStart`; N180 is
`twoHandHeldDuringDoorClose`) and its truth in `Chart.CondOk[0..7]`, written by
the step itself in all three renditions after it marks entry - TC3's
`M_Await`, where the step that decides also records. The gateway joins label to
truth only when `Chart.ActiveStepNumber` equals `Unit.Step`, so the scan after
a transition is never labelled with the next step's names. `AwaitingLabel`
(`PressRam.RETRACT`), `TimeClass` and `ExpectedTime` (0, as every TC3 press
step passes `T#0S`) come from the declaration, and `Starved`/`Blocked` are
derived as `FB_UnitBase` derives them: BUSY in a WAIT_UPSTREAM/WAIT_DOWNSTREAM
step. `E_TimeClass` and `MAX_STEP_CONDS` are pinned to the TwinCAT sources.

**Item 4 built offline, 2026-09-30. Phase 1 is complete offline, in
`press30.L5X` (`382A4E596132C0B0`), which supersedes press29; press29 was
never imported.** TC3's cylinder names the end sensor that did not report and
stamps when the fault began. Logix v33 ST cannot hold the tag (S12), so the
library type declares I/O roles (`retractedFb`, `extendedFb`), the AOI
publishes which it implicates as bits in `OutImm_IoRoles`, the application
binds each role to one channel (`IoChannel.role`), and the gateway joins them
- the numeric-to-text seam the mailbox already uses. `Since` is stamped on the
controller when a reason changes, because onset is history a poll cannot see.
Every module now also publishes `Diagnostic/Description`.

Three defects this item found and fixed:

- **A faulted module showed no message.** AB published only the reason code,
  and for its project codes the client has no text of its own, so the
  module's message was blank.
- **One report became the Unit's diagnostic for good.** The Unit published
  `HeldReason or ReportedReason`, and `ReportedReason` is never cleared. TC3's
  `M_SequenceWarn` leaves the Unit's diagnostic alone and puts the report in
  the ring as an AUTO_RESET occurrence. The controller now chooses the Unit's
  reason once (`DiagReason`: adopted fault, else held) and logs each report,
  with its source (`ReportedSource`, new in all three renditions), straight to
  the ring.
- **A fault adopted by AUTO was logged a scan late.** The log ran before the
  chain renditions, so by the time it saw the adoption the child had cleared
  its reason. The clock, the stamps and the log now run after dispatch, while
  the child still holds what caused the fault.

And one decision worth recording: the slide's `extendedFb` is `_101B301A`,
"feeder retracted", because the slide's logical extended end is *inside*
(`CX2030_PRESS_IO_MAPPING.md`, TC3 `FB_PressIoCatalog`). Binding by the
channel's description would have named the wrong sensor.

1. The §8.3 alarm log on the controller (Q4): active list and bounded ring at
   TC3's sizes, with come/gone scan stamps, severity, reason and source path.
2. Alarm acknowledge through the mailbox.
3. `CurrentStep/Conds`: what the step is waiting for.
4. Diagnostic detail: `Since`, and the electrical-tag join to the fieldbus
   channels that already exist.
5. `Blocked` / `Starved`.

### Phase 2: sequence visibility (mostly projection)

**Status 2026-09-30: done, on hardware.** press31 (`57824B57B4D694D5`) was
compiled in Studio v33 and downloaded; §146 parity re-passed 17 of 17 and the
flow chart passed 6 of 6 on the controller
([`Evidence/AB_PHASE2_ON_HARDWARE_2026-09-30.md`](../AllenBradley/Evidence/AB_PHASE2_ON_HARDWARE_2026-09-30.md)).
Item 2 shipped with Phase 1. Items 1 and 3 turned out to need
the controller, because the chart TC3 publishes is not the one AB was keeping:

- **Rows are discovered by visit and scoped to the mode.** TC3 numbers a row
  when its step is first entered and clears the table on a mode change, so each
  mode draws its own chart. AB's `Visited` was cumulative since the download
  and indexed by declaration. The chart now numbers rows on first entry
  (`RowOf`) within a mode session (`RowEpoch`). A mode change bumps the epoch
  rather than walking every array: O(1) on that scan, the same intent as TC3
  bounding its clear by the rows in use.
- **A report marks its row.** `WarnReason`/`WarnSource`, written by the REPORT
  step in all three renditions and cleared when the step is re-entered ("this
  visit starts clean"), become `WarningActive` and a §6.9 annotation naming
  the reporting module.
- **`ErrorActive` is always false, and that is TC3's rule, not a gap.** TC3
  marks a row only for a §6.9(d) raise; an awaited child adopted by rollup is
  not marked, and AB's step vocabulary has no raise.

The gateway joins that record to the declaration's static half of each row
(`StepName`, `AwaitingLabel`, `AwaitsPath`, `TimeClass`), publishes a fixed 16
slots (the longest chain) so the path set never moves, and drives the cursor
only while the chain runs the step the chart itself names. Tested by walking
the generated AUTO chain on the ST model against an instant plant: the rows
come out in exactly the order the chain entered its steps.

1. Publish the §3.13 flow chart from the chart data already on the controller.
2. `CurrentStep` timing and class fields.
3. Per-row marks and annotations (this step needs the download).

This phase can run in parallel with Phase 1, because it touches different files.

### Phase 3: press module parity

**Status 2026-09-30: the reason scheme is settled, and on hardware.**
`press33.L5X` (`C1A5A2B177022CDD`) was compiled and downloaded. Parity passed
17/17, Phase 1 7/7, Phase 2 6/6, and the reasons, watchdog and rollup 4/4
([`Evidence/AB_PHASE3_REASONS_ON_HARDWARE_2026-09-30.md`](../AllenBradley/Evidence/AB_PHASE3_REASONS_ON_HARDWARE_2026-09-30.md)). press32 (`7C4B542BF51F10EB`)
carried the scheme alone and was superseded before download by the §6.9
watchdog below. The rule is the registry's: a
registered reason keeps its registered code, priority, category, shelving and
TC3's `std.reason.<code>` texts on every binding, and a project's own codes
live in a band at or above 10000. `fraktal_ab_reasons.py` is the one place
that resolves a reason's rationale; the numbers are pinned to TwinCAT's
`E_Reason`, `PL_ModuleReasons` and `PL_PressReasons` by test.

- **The cylinder raises TC3's codes.** It holds on `INTERLOCK_DROPPED` (2003,
  TC3's `FB_PermIntlk` conditions), times out as `CYL_NOT_EXTENDED` or
  `CYL_NOT_RETRACTED` (10101/10102) by the end that did not report, and
  refuses to run without a task period as `CYL_CFG_INVALID` (10115).
- **A simulated device fault is a cylinder that does not move.** TC3 has no
  cylinder "device fault"; a stuck cylinder is found by its timeout. So the
  harness's fault injection now holds the plant still, and the timeout, with
  the sensor it names, becomes reachable on the controller. That closes the
  gap Phase 1 recorded.
- **The press's own codes moved into TC3's press band.** `TWO_HAND_RELEASED` is
  12001, TC3's `PRESS_TWO_HAND_RELEASED`; the generator's `WAIT_*` stall
  reasons are 12010-12012 and `PART_NOT_PRESENT` 12020. `STEP_STALLED` is
  Core's 2005.

Three defects the move found:

- **Two names meant two numbers.** AB declared `TIMEOUT` as 6103 and
  `STEP_STALLED` as 6120, and the registry defines both (2001, 2005).
- **Every press wait was published as a SAFETY alarm.** Rationalization rows
  used category 1 for waits and 2 for faults; Core `E_Category` is PROCESS 0,
  SAFETY 1, SYSTEM 2. Now pinned.
- **Three reasons were registered and never raised** (`ABORT_REQUEST`,
  `AIR_NOT_READY`, `SLIDE_FAULT`). Removed with their texts; the air monitor
  will bring its own code.

**The §6.9 stall watchdog and hold rollup, TC3's, in the same build.** The
gateway published `CurrentStepTimedOut` whenever the chart held a pending
reason, which meant every delay, every operator wait and every decision showed
as timed out. TC3's is `_tStall`: while the Unit is busy with nothing held, a
step that runs past `StallTime` (30 s) is timed out and the Unit publishes a
LOW pending `STEP_STALLED`; a step change restarts it. The controller now does
exactly that (`StallMs`/`StepTimedOut`), and the Unit's diagnostic follows
TC3's order: an adopted fault, its own hold, the first held child
(`_M_RollupHold`, which AB lacked, so a held cylinder left the press saying
nothing), then a stall.

**First, reserve the library's reason bands.** AGENTS.md: *"Reserve a band before
writing a type."* The cylinder raises 6101–6103, codes the press registered as
fixture-scoped, because they were the press's before the cylinder was a type.
§8.8 gives a type its own band (≥10000), and TC3's cylinder raises the
framework's `TIMEOUT` (2001) through its base class. Settle the scheme, then move
the cylinder, before four more types are born into it. Moving the cylinder's
codes changes what a client sees on a fault, so it is its own commit and not
part of a refactor.

Depends on Phase 0's type keys and type library.

**Item 1 done, on hardware, 2026-09-30.** press34 (`F95302D66EC858DD`)
compiled and was downloaded. Parity 17/17, Phases 1-3 7/7, 6/6, 5/5
([`Evidence/AB_PHASE3_SENSOR_ON_HARDWARE_2026-09-30.md`](../AllenBradley/Evidence/AB_PHASE3_SENSOR_ON_HARDWARE_2026-09-30.md)). The second library type, `std.moduleType.digitalInput`, is
TC3's `FB_DigitalInputCM`. It publishes Value and Quality as its source
presents them and refuses any command with `UNSUPPORTED_COMMAND` (2008). The
press's `PartPresentSensor` is an instance of it, fed each scan from the
part-present stimulus the harness already drives, and N100 waits on its Value
AND Quality, TC3's condition, in all three renditions.

What proving the path took:

- **A context per type.** Every module had shared one cylinder-shaped UDT. It
  is now TC3's `FB_ModuleBase` as a common base plus each type's own members,
  in `FRK_T_<Type>Ctx`. A type declares whether it is `passive` (fed from a
  source, never commanded) and which simulation injections it takes. The
  sensor takes none, so it has no fault or hold tag.
- **A step may wait on a module's state** (`decl.ModuleState`), not only on a
  bare tag. One `Names.terms` renders it for ST, SFC and LD, including the
  §6.9(b) condition records.
- **One test premise was wrong since Phase 0.** A module's type key selects its
  library type, so renaming it changes the controller. Only the Unit's key is
  presentation.

1. `PartPresentSensor` (digital input), the simplest and the one that proves
   the new-type path.
2. `TwoHand`, which also retires the bare sim tag the parity harness drives.

   **Done, on hardware, 2026-09-30.** press35 (`2D6DF2306FB4F5CF`) compiled
   and was downloaded. Parity passed 17/17 and Phases 1-3 7/7, 6/6, 6/6,
   including a press before the part not starting the stroke
   ([`Evidence/AB_PHASE3_TWO_HAND_ON_HARDWARE_2026-09-30.md`](../AllenBradley/Evidence/AB_PHASE3_TWO_HAND_ON_HARDWARE_2026-09-30.md)). `std.moduleType.twoHand` is TC3's `FB_TwoHandStartCM`: a
   start *edge* from a certified two-hand result. It arms only on a release
   between starts, and a SafeActive rising edge while armed is one
   `StartPulse`. The press uses it the way `FB_PressDemoUnit` does:

   - a pulse in AUTO starts the press from ready, through `start_predicate`,
     the one start rule the mailbox's START now reads too;
   - `StartLatched` is set only when the part and air are already there, so a
     press made before the part was loaded never starts the stroke when it
     arrives. N100 waits on the latch, not on the buttons held; the cycle end,
     abort, reset and a mode change clear it;
   - N180 holds on the module's `SafeActive`.

   The harness now releases, sends START, then presses (`px.start_cycle`),
   because a two-hand held high is no longer a start.

   **Then open, built since:** TC3's N220 dwell holds while the two-hand is
   released (`twoHandHeldDuringPress`); AB's was a plain delay. See item 4.
3. `AirPressureMonitor`: move air loss from a sim tag to a module whose own
   condition HOLDS, which is §146 P8 exactly as TC3 does it.

   **Done, on hardware, 2026-10-01.** press37 (`3819172B1682B27F`) compiled
   and was downloaded. Parity passed 17/17 and Phases 1-3 7/7, 6/6, 7/7,
   including air lost under the door's close
   ([`Evidence/AB_PHASE3_AIR_ON_HARDWARE_2026-10-01.md`](../AllenBradley/Evidence/AB_PHASE3_AIR_ON_HARDWARE_2026-10-01.md)).
   press36 carried the same contract and failed to compile: its
   stall watchdog chained one `OR` per module, and the sixth module made six
   (see the platform rules below). `std.moduleType.airPressure` is TC3's
   `FB_AirPressureMonitorCM`:

   - **PressureOk:** the operating switch on, the low switch off, and the
     reading trusted.
   - **Conflict:** both switches on becomes `AIR_SWITCH_CONFLICT` (10601,
     MED) only once it has persisted for `ConflictTime`. It names both
     switches (`_000MB085A_2 / _000MB085A_4`) and stays latched until an
     operator reset finds the switches agreeing.
   - **ConflictTime:** station data under TC3's `airPressure.conflictTime` and
     its label, bound into the module each scan (`Module.config`). StationCfg
     goes to schema 2.
   - **Air is each cylinder's interlock**, TC3's `SetAreaSafe`
     (`Module.area_safe`). Lost mid-stroke, the cylinder holds on
     `INTERLOCK_DROPPED` with no fault and no timeout, resumes by itself, and
     the Unit rolls the hold up. Passive modules now run before commanded
     ones, so the interlock is this scan's.
   - N100 and the start latch wait on `PressureOk`.

   One base change: a passive type's command fault now clears on the *drop*
   of Execute, not while Execute is low. The level form would have cleared
   the latched conflict on every idle scan.

   **Budget:** the manifest is at Fields 331/384 and Localization 298/320.
   `PartFeed` will need the capacities raised, within S7's measured 43,728
   bytes; today's build is 36,200.
4. `PartFeed` (axis), the largest.

   **Not built, by TC3's own rule. Reclassified X, 2026-10-01.** TC3 declares
   `PartFeed` but arms it only when a real NC axis is linked
   (`ConfigurePartFeedAxis` refuses `AxisId 0`). Without a linked axis it is
   never registered, so it is outside the rollup, the configuration walk and
   every parameter set: *"Absent hardware is absent, not silently
   pretended."* The drive it stands for is a bench XENAX Xvi on a second
   EtherCAT device, not press hardware, and it is not in the AUTO chain.
   The AB bench has no axis, and its controller cannot have one: Integrated
   Motion, virtual axes included, needs an M or P catalogue number, and the
   bench is a `1769-L24ER-QB1B`. AB §10.6 also says motion is *"an unclaimed
   optional module family, not a generic stub"* until S14 passes, and S14
   cannot be measured here. So TC3's behaviour on this bench is the
   behaviour AB already has, an absent axis. Building one would mean either a
   stub Part III forbids or a simulated axis TC3 refuses to arm. It would
   also spend manifest capacity on a device nobody can consume (O4). It
   comes back with S14, on a controller that has motion.

   **The N220 dwell pause: done, on hardware, 2026-10-01.** press38
   (`9BD371752899748A`) was downloaded. Parity passed 22/22, and Phases 1-3
   passed 7/7, 6/6 and 8/8. In the new Phase 3 row the dwell was released at
   10 ms of 300, stood still for 1.5 s, and served 290 ms more once pressed again
   ([`Evidence/AB_PHASE3_DWELL_ON_HARDWARE_2026-10-01.md`](../AllenBradley/Evidence/AB_PHASE3_DWELL_ON_HARDWARE_2026-10-01.md)).
   This was the open item from item 2. TC3's N220 is a named wait,
   `twoHandHeldDuringPress`, and neither a hold nor a fault. Releasing the
   two-hand stops the dwell, and pressing again finishes the time that
   remained. AB's delay used to read the step clock, which counts a pause. A
   delay now keeps its own clock (`Chart.DelayMs`), zeroed on entry and
   advanced only on scans its conditions hold. A plain delay is the same
   clock with nothing to wait for, so there is one delay, not two. N170's
   settle times exactly as before. The step's own duration still counts the
   pause.

   - A delay may now declare conditions (`decl.DELAY`). They are §6.9(b)
     records, so N220 publishes `CondOk[0]` and its label like any wait.
   - Paused, the step publishes `WAIT_CONDITION` (12011) and leaves `Held`
     and `Error` alone, as TC3's `M_Await` does.
   - AB's cylinder simulates position, not a valve. TC3's
     `WithdrawOutputs`/`RestoreOutputs` of the ram's force therefore has
     nothing to act on here.
   - The ladder is tested by behaviour for the first time.
     `fraktal_ab_ld_model` runs the rungs the generator emits, and
     `test_fraktal_ab_dwell` scans the ST, SFC and LD renditions of the real
     chain and requires identical traces. Nine mutants of the new code are all
     killed.
   - The parity harness gains a dwell walk per rendition (22 rows, was 17).
     It releases inside the dwell for 1.5 s and requires `DelayMs` to have
     stood still. It then requires exactly the declared dwell to have been
     served once the buttons are pressed again.

   Manifest: Fields 332/384, Localization 299/320.

   **Found while building it, recorded and not fixed here:**

   - **TC3's own dwell may not pause.** Its comment says the timer *"freezes
     where it is because M_Delay is not called"*. But `M_Delay` is a `TON`,
     and TwinCAT's `TON` measures from a timestamp. PressTests relies on
     that: *"a TON never advances inside a scan"*. So not calling it does not
     stop the clock. After a release longer than the remaining dwell, TC3
     would finish the dwell on the first scan after the re-press, crediting
     the part with time it spent unpressed. No PressTests row advances time
     through a release, so nothing catches it. AB implements the behaviour
     the TC3 comment states. TC3 owes an accumulating dwell and a test that
     advances time.
   - **The stall watchdog's limit.** TC3 arms `_tStall` at a step's
     `ExpectedTime` when it declares one (N170, N220), else `StallTime`.
     AB uses `StallTime`, 30 s, for every step. A released dwell is
     therefore reported as stalled after about the dwell on TC3, and after
     30 s on AB.
   - **`RequireTwoHandStart` is declared and read by nothing.** TC3's N100,
     N180 and N220 all honour it. On AB it is an orphan field.
   - **N180 still diverges** (the press demo docstring records it). TC3
     treats a release during the door close as an operator abort: a
     §6.9(e) warning, then reopen, slide out and return to the two-hand
     wait. AB holds. The held form was the S16 mission's. It is no longer
     the only hold the bench can show, because air lost under a moving
     cylinder holds since item 3.

   **The last three: done, on hardware, 2026-10-01, on press40
   (`57BE3FF0681AF466`).** Parity passed 25/25 and Phases 1-3 passed 7/7, 6/6
   and 8/8 ([`Evidence/AB_PRESS40_ON_HARDWARE_2026-10-01.md`](../AllenBradley/Evidence/AB_PRESS40_ON_HARDWARE_2026-10-01.md)).
   Before that, press39 ran them in ST and LD only. This closes the AUTO
   chain's divergences from TC3, except TC3's own dwell defect above. On
   press39, Phases 1-3 passed 7/7, 6/6 and 8/8, and ST and LD passed every
   parity row. SFC failed the new abandon row. That exposed defect D7: the
   SFC chart had never commanded a module that was still Done from its
   previous command
   ([`Evidence/AB_PRESS39_SFC_STALE_DONE_ON_HARDWARE_2026-10-01.md`](../AllenBradley/Evidence/AB_PRESS39_SFC_STALE_DONE_ON_HARDWARE_2026-10-01.md)).
   press40 carries the same contract and hash, with the SFC rendition fixed.

   - **N180 is TC3's.** It is a guarded command (`decl.GUARDED`): a command
     wanted only while its guard holds. A release during the close drops
     it and raises `TWO_HAND_RELEASED` (12001) once, as a §6.9(e) warning
     from the Unit itself. The warning is LOW, PROCESS, and marked on N180's
     §3.13 row. The chain then jumps to the new N185 (reopen the door) and
     N190 (slide the part out). N190's completion drops the start latch, as
     a completion mark, so the cycle waits at N100 for a fresh press.
     Completion wins if the door finished in the same scan.
   - **The chain's own hold is gone.** `HELD_AWAIT` and the Unit's
     `Held`/`HeldReason`/`HeldSeverity` had one user, the old N180. A held
     cylinder still rolls up into the Unit's diagnostic, and still disarms
     the watchdog.
   - **`RequireTwoHandStart` is the cell's policy, where TC3 keeps it.** It
     moved from the ParCfg (schema 2) to the StationCfg (schema 3), and is
     editable under TC3's `press.requireTwoHandStart` and its label. Lost,
     it comes back TRUE. N100's latch, N180's guard and N220's dwell condition
     count only while it is set (`decl.RequiredBy`): TC3's `SafeActive OR NOT
     RequireTwoHandStart`, rendered through one ST and one LD renderer that
     every step kind now shares.
   - **The watchdog uses a step's expected time.** A delay expects its
     duration (`decl.expected_member`; TC3's N170 and N220 pass the same
     value), read from the live recipe. The Unit publishes it as
     `StepExpectedMs`, which the projection serves as `CurrentStep/ExpectedTime`
     and on each §3.13 row. A step that takes exactly that time finishes one
     scan later, so the limit allows that scan. Any other step keeps
     `StallTime`.
   - **Tests.** Every rendition is scanned through N180, N185 and N190
     (`test_fraktal_ab_guarded`), and through the policy-off case. All 17
     mutants of the new code are killed. The parity harness's hold walk
     becomes an abandon walk, still 22 rows. A dwell released for 1.5 s must
     now also be reported stalled.

   Manifest: Fields 330/384, Localization 301/320, write capabilities 7/64.
   The chart holds 31 of its 32 steps.

   **Still open:** TC3's station also carries `press.stallGuardMs`, the
   editable StallTime. On AB, StallTime is a declared constant.

Each module replaces a bare sim tag, so the parity harness's write surface
changes with it and the §146 parity pass has to be re-run.

### Phase 4: act-or-explain

1. Release reports: `RELEASE_START`, `RELEASE_MANUAL`, `RELEASE_ACTION`, with
   condition records and owning source paths (§7.6). This moves §146 P2 from
   not claimed to bound.

It is placed after Phase 3 because most of the conditions it explains live in
the modules Phase 3 adds.

**Found when starting it: a manual report needs manual commands, and AB had
none of TC3's.** TC3's `releaseReportManual(unit, target, value)` explains
why one module's command in one direction is blocked. AB's MANUAL was a jog
chain that moved the part slide out and back on an unaddressed request. The
HMI's addressed commands were refused (`target_not_addressable`), and no
module published a command catalogue, so the HMI showed no manual buttons
for AB at all. The cylinder had no directional permits either. TC3's press
uses those to stop the door closing over the slide, and AB's cylinder
ordinals were TC3's swapped (EXTEND 2, RETRACT 1). Phase 4 is therefore two
builds.

**4a: done, on hardware, 2026-10-01, on `press41.L5X` (`9C54A2F97E1ACFC9`).**
Phase 4a passed 7/7, parity 25/25, and Phases 1-3 7/7, 6/6 and 8/8
([`Evidence/AB_PHASE4A_MANUAL_ON_HARDWARE_2026-10-01.md`](../AllenBradley/Evidence/AB_PHASE4A_MANUAL_ON_HARDWARE_2026-10-01.md)):

- **Ordinals.** The cylinder's are TC3's: EXTEND 1, RETRACT 2, in catalogue
  order.
- **Command catalogue.** Every cylinder publishes TC3's catalogue
  (`CatalogCount`, `Catalog[i]/{Value, Label, Style}`, labelled
  `std.command.extend`/`retract`). A sensor publishes an empty one.
- **No MANUAL chain** (`decl.Application.manual_mode`). MANUAL is a mode with
  no sequence, as TC3's is. START is refused there by TC3's
  `std.release.manualHasNoAutoSequence`.
- **Manual commands, TC3's `ManualCommandTo`.** The gateway resolves the
  module identity in `TargetPath` to its ordinal, the same seam
  `FORCE_CHANNEL` uses. The controller accepts the command only in MANUAL,
  only to a module with a catalogue, only a catalogue value, and only while
  the module is not busy, and refuses each by name otherwise. The mode owner
  runs the command through the module's handshake and drops `Execute` when it
  is done. A command that faults keeps `Execute` up, so the fault stays
  visible until the next command, a reset, a stop or a mode change releases
  it.
- **Directional permits, TC3's `SetDirectionalPermits`**
  (`decl.Module.permits`), evaluated by the routine for the commanded
  direction each scan:
  - the door closes only over a slide that is inside and settled;
  - the slide moves only with the door open and settled;
  - the ram presses only with air, the guard closed, the slide inside, both
    healthy and the two-hand held. It is named first-out in that order.

  A missing permit holds the cylinder on `INTERLOCK_DROPPED` in AUTO and
  MANUAL alike, and the module's diagnostic carries the permit's own TC3 key.
  The area interlock is named first, as TC3's `PermIntlk` orders it.
- **End sensors.** The cylinder publishes `OutImm_Extended`/`Retracted` from
  its position, which is what the permits read.
- **Tests.**
  - 21 behavioural tests run the generated mailbox, module layer and mode
    owner in routine order (`test_fraktal_ab_manual`). 13 mutants of the new
    code are all killed.
  - The whole-cycle test now runs with the permits active. All three
    renditions still take 97 scans.
  - A new controller harness, `fraktal_ab_phase4_execute.py`, has 7 rows.
  - The parity dwell walk now releases only once the dwell has begun, because
    a release during the stroke holds the ram on its permit.

Manifest: Fields 345/384, Localization 314/320. 4b's report keys will need
the Localization table raised.

**Gaps 4a leaves, recorded:**

- **Control power.** TC3's ram permit's first condition is the pneumatic power
  group (excluded on this bench).
- **Manual audit events.** TC3 records `std.audit.manualCommand*` in the
  §8.3 ring; AB's ring carries reason codes, not audit texts.
- **The Unit names a held child by reason only.** It does not use the child's
  interlock text, where TC3's rollup copies the child's diagnostic verbatim.
- **A module fault outside a chain is not rolled up into the Unit.**

**4b, the release reports: on hardware, 2026-10-01, on `press42.L5X`
(`B8A2BE7BB9D19ECB`).** Phase 4 passed 11/11, parity 25/25, and Phases 2-3
6/6 and 8/8
([`Evidence/AB_PHASE4B_RELEASE_ON_HARDWARE_2026-10-01.md`](../AllenBradley/Evidence/AB_PHASE4B_RELEASE_ON_HARDWARE_2026-10-01.md)).
Phase 1 passed 6/7, and its failure is defect D8 below: an operator reset
restarted the press by itself. **It is fixed in press43 and on hardware,
2026-10-01:** Phases 1-4 7/7, 6/6, 8/8 and 11/11, and parity 25/25
([`Evidence/AB_PHASE4_COMPLETE_ON_HARDWARE_2026-10-01.md`](../AllenBradley/Evidence/AB_PHASE4_COMPLETE_ON_HARDWARE_2026-10-01.md)).
Phase 4 is complete.

- **Start: TC3's `ReleaseReportStart`, computed every scan** into
  `FRK_Press_StartRelease`. It lists the manual mode, a Unit not ready
  (running, faulted, complete or aborted), an unreset alarm, and each declared
  start permit. TC3's `ModeStart`, air pressure OK, is reported as
  `PERMISSIVE_NOT_MET` (2002) under its key, now registered. START, a
  physical two-hand start and the HMI's query all read that one result
  (`start_predicate`), so the rule and its explanation cannot drift. A
  refused START names the first reason and answers with the full report, as
  TC3's Start fills `HmiResponse.Report`. An aborted Unit used to take START
  and then not run, a silent dead button; it is now refused as
  `unitNotReady`.
- **Manual: TC3's `ReleaseReportManual`,** built on request from the same
  tests MANUAL_COMMAND gates on (mode, target, catalogue, busy) plus the
  requested direction's first missing permit. That permit is what the module
  would hold on, through the same `permit_chain` the routine uses. Each
  reason names its owning module.
- **Action: TC3's `ReleaseReportAction`,** as far as this binding's gates go.
  A reset with nothing blocking says `noBlockingAlarm`. Access levels (Phase 6)
  are not held by this controller. A mode switch is never refused here. And a
  model is chosen while CHANGEOVER runs, because AB's changeover waits for it
  at N700, where TC3 selects the model before Start and refuses
  `changeoverRunning`. That difference is recorded rather than reported.
- **Published as TC3's `HmiResponse/Report`.** The projection publishes all
  24 of TC3's slots in TF6100's naming (`Reasons/Reasons[i]`), because the
  HMI re-reads exactly those after an acknowledgement and refuses the whole
  read if one is missing. Texts resolve through this controller's own
  catalogue; owners are qualified identities.
- **Capacity.** The controller report holds 8 reasons, which is the most this
  press can produce. The Localization table is raised to 352 rows; the
  manifest is now 37,992 of S7's measured 43,728 bytes. The scope fence's
  `ReleaseReport` term is lifted, and recorded, as `Manifest` and `Mailbox`
  were.
- **Tests.** 19 behavioural tests run the generated routine and mailbox
  together (`test_fraktal_ab_release`), including that every MANUAL_COMMAND
  refusal is the first entry of the report for the same request. 14 mutants
  are all killed. The Phase 4 controller harness gains 4 rows (11 in total),
  and Phase 1's start-refusal row now reads the report.

Manifest: Fields 351/384, Localization 324/352.

**Found and recorded, not changed here:**

- **The restore policy.** TC3's press declares `BLOCK_UNTIL_ACKNOWLEDGED`;
  AB's is fixed at defaults-and-annunciate. So TC3's
  `configRestoreUnacknowledged` start reason cannot arise on AB and is not
  emitted.
- **Changeover gating,** as above.

### Phase 5: production features

OEE with trend and reset · cycle-time profiler · derived state flags · PackML
machine state · run styles · step mode · hold-run · hold-to-run · rework count ·
nameplate · catalog · system health.

These are independent of one another. Order them by what the bench is used to
demonstrate.

**5a, run styles (TC3 §3.4.2): done, on hardware, 2026-10-01, on
`press44.L5X` (`F1200055EB9C8388`).** Phase 5 passed 10/10 in all three
renditions, with parity 25/25 and Phases 1-4 7/7, 6/6, 8/8 and 11/11
([`Evidence/AB_PHASE5A_RUN_STYLES_ON_HARDWARE_2026-10-01.md`](../AllenBradley/Evidence/AB_PHASE5A_RUN_STYLES_ON_HARDWARE_2026-10-01.md)).
On the bench, a single-stepped cycle takes one command per Step, `[0, 1 x 8]`,
in each language. `SET_RUN_STYLE`, `STEP_REQUEST` and `SET_HOLD_RUN` are
routed. The Unit publishes `RunStyle` and `SupportedRunStylesPublished`, and
the press offers all three styles, as TC3's press does (`_M_SupportsRunStyle`).

- **TC3's `M_TryIssue`, in all three renditions.** Every commanding step
  (issue, guarded, adopt, report) is a stop point, as each of TC3's press
  commands is (`Steppable := TRUE`). A step declared `steppable=False` runs
  straight through, which is TC3's `Steppable := FALSE`. The mode owner
  computes the permit once per scan before any chain runs (TC3's
  `_M_StepGate`): always in CONTINUOUS, a pending Step in SINGLE_STEP, the
  held button in HOLD_TO_RUN. A step issues once the permit allows and then
  stays issued for its visit, so **the issue is paced, not the motion**: a
  command once issued runs to Done whatever the button does next, exactly as
  in TC3. A Step given during a motion stays pending for the next stop point,
  as TC3's does. Pacing is NON-SAFETY and never a dead-man; the modules'
  interlocks decide whether anything moves in every style.
- **Refusals by name.** A style outside `E_RunStyle` is refused with TC3's own
  `std.error.unsupportedRunStyleRequest`. TC3 refuses an in-range style the
  Unit does not offer with no text at all; AB uses the same key for both, so
  neither is a silent no. A Step outside a running SINGLE_STEP and a hold
  outside a running HOLD_TO_RUN are refused by name (TC3 refuses both without
  a text). Releasing the hold is always accepted.
- **One deliberate difference, stricter than TC3.** A Unit that is not running
  holds no Step request and no hold, and changing the style forgets both. TC3
  keeps `_holdRun` across a stop and a mode change, so a release lost with the
  HMI link would let the next START run unheld in HOLD_TO_RUN. That breaks
  TC3's own rule that a hold cannot stick. In AB one line in the pacer covers
  a stop, a fault, a reset, an abort and a mode change. This is recorded as a
  TC3 finding, not changed in TC3 here.
- **Tests.** 24 behavioural tests (`test_fraktal_ab_run_styles`) run the
  generated module layer, the pacer and each rendition over whole AUTO cycles.
  They prove: one command per Step for the whole cycle and nothing before the
  first; a release mid-motion finishes the motion and stops at the door close;
  CONTINUOUS is scan-for-scan unchanged. 17 mutants are all killed. A new
  controller harness, `fraktal_ab_phase5_execute.py`, has 10 rows: the stepped
  and held cycles in each rendition, counted by module commands as D7 taught.
  The harnesses' idle step now returns the press to CONTINUOUS, so no later
  harness inherits a paced press.

Manifest: Fields 356/384, Localization 332/352, 40,824 of S7's measured 43,728
bytes.

**Gaps 5a leaves, recorded:**

- **Access gates.** TC3 gates the style on `MODE_CHANGE` and Step and hold on
  `START_STOP`. AB holds no access levels until Phase 6.
- **A held button over a lost link.** While the Unit runs, a hold whose
  release never arrives stays in force until a stop, on both bindings. There
  is no heartbeat; pacing is NON-SAFETY by contract.
- **`MANUAL_HELD`** (hold-to-run for a manual command) is not a gap here; it
  is reclassified X below.
- **Capacity.** The rest of Phase 5 adds fields and keys. Fields has 28 rows
  left and Localization 20, and the manifest is within 3 KB of S7's
  measurement. The next item raises the tables and re-measures S7 before it
  adds anything.

**5b, room for Phases 5-6: done, on hardware, 2026-10-01, on `press45.L5X`.**
The 51,064-byte manifest read back whole and coherently in 141.8 ms (press44's
40,824 took 130.2 ms), and parity 25/25 and Phases 1-5 7/7, 6/6, 8/8, 11/11 and
10/10 all pass
([`Evidence/AB_PHASE5B_MANIFEST_CAPACITY_ON_HARDWARE_2026-10-01.md`](../AllenBradley/Evidence/AB_PHASE5B_MANIFEST_CAPACITY_ON_HARDWARE_2026-10-01.md)).
The whole manifest, never one table, was always the binding limit, held at S7's
43,728 bytes.

- **The raise.** Fields goes 384 → 512, S7's own Fields table and the frozen
  `FRK_MAX_FIELDS`. Localization goes 352 → 448. Remaining work is about
  100-150 fields and 80-90 keys. The manifest goes from 40,824 to 51,064
  bytes, inside a declared `MANIFEST_BUDGET_BYTES` of 53,248, now the one
  source both size tests read.
- **Why that is allowed without a spike.** Part III makes a raise "a
  cost-curve calculation against S7". At S7's rates, 52 KiB costs ~357 ms at
  500 bytes and ~75 ms at 4000. That is paid on connect and on a revision
  change only; the live-tier header poll does not grow. The press's manifest
  is a build constant, so S8/S9's guard window (no mutation faster than once
  per read) cannot be approached at runtime. The real press44 manifest read
  whole in 130 ms (Localization's 22.5 KB in 26 ms). The raise is confirmed
  the same way, read back from the controller, before anything is built on
  it.
- **A hole the raise exposed.** `ContentHash` covers what is published, not
  the room it is stored in, so press45 has press44's hash. A gateway built
  from this declaration against press44 would have passed the hash check and
  read 512 Fields rows out of a 384-row tag (and 448 Localization rows out of
  352), falling back to ~740 per-element requests and projecting anyway. The header already published each table's
  capacity; nothing compared it. Now the projection refuses a table sized for
  another build by name, before any table is read, and the evidence reader
  reports it as a finding. Both checks are tested, and both mutants are
  killed.
- **The frozen capacities.** `AB_FROZEN_CONTRACTS_V1.json` still lists
  `FRK_MAX_LOCALIZATION_KEYS` 256, S7's candidate size. This binding has
  published more than 256 keys since the editable-configuration work. The
  bound that was enforced was the whole manifest's bytes, and that is
  unchanged here: recorded, not reopened.

**`MANUAL_HELD`: reclassified X.** TC3's held manual command
(`ManualHeldTo`, with its 750 ms refresh deadline) reaches a module only
through `RequestHeldCommand`. The only type that implements it is
`FB_AxisCM` (jog ±), and the press's only axis is `PartFeed`, which this
controller cannot host. On TC3's own press no cylinder takes a held command
either. AB refuses `MANUAL_HELD` with "This station has no hold-to-run
control for manual commands", which is true of this press on both bindings.
It is built the day an AB axis type exists.

**5c, OEE (Core §8.5.1): done, on hardware, 2026-10-01, on `press46.L5X`
(`C6F4216F214A6BA5`).** Phase 5 passed 15/15, with parity 25/25 and Phases 1-4
7/7, 6/6, 8/8 and 11/11
([`Evidence/AB_PHASE5C_OEE_ON_HARDWARE_2026-10-01.md`](../AllenBradley/Evidence/AB_PHASE5C_OEE_ON_HARDWARE_2026-10-01.md)).
On the bench, run time tracked the wall clock (1,520 against 1,571 ms), down
time grew only while faulted, and the first sample landed 60.005 s after the
reset. `RESET_OEE` is routed. The Unit publishes TC3's `Oee`
card and its 60-sample `OeeTrend`, where the HMI's OEE card reads them.

- **TC3's accounting, on the controller.** Each scan lands in exactly one
  bucket, tested in TC3's order: run while the Unit is BUSY, down on ERROR or
  a blocking alarm, idle otherwise. The clock is the task period, like every
  other duration in the routine. A sample is pushed every 60 s into a
  60-slot ring (TC3's `OEE_SAMPLE_MS`, `MAX_OEE_SAMPLES`; the HMI walks
  exactly 60). It all lives in one new structure, `FRK_Press_Oee`; the
  Unit's AOI is unchanged.
- **Seconds plus a millisecond remainder.** A DINT of milliseconds wraps after
  24.8 days, and an availability computed across a wrap is a confident lie.
  TC3's UDINT wraps at 49.7 days; AB's seconds last 68 years.
- **The factors are derived once, in the projection.** UDTs are DINT-only on
  v33, and putting division on the controller would have meant factors in
  basis points: a second formula, and Logix integer-division semantics as a
  new hardware risk. So the controller keeps the accounting, a sample keeps
  the accounting too, and one function (`oee_factors`, TC3's
  `_M_OeeCompute`) derives the live figure and every sample alike. A sample
  can therefore never disagree with the live formula. Every factor carries
  its validity flag; an invalid factor is left out of the product and never
  shown as 100 % (O7).
- **The ideal cycle is per-model config, as in TC3.** `IdealCycleMs` is in
  ParCfg (schema 2 → 3), editable under TC3's `press.recipe.idealCycleMs` key
  and label, 0-600,000 ms. Per model it is 950 / 1,350 / 750 ms, the bench's
  measured M-100 cycle (966-979 ms) moved by each model's dwell and settle. An
  ideal above the real cycle would cap Performance at a flattering 100 %.
- **The reset is an epoch, like the §3.13 chart's.** `RESET_OEE` zeroes the
  buckets and bumps an epoch. Samples from another epoch are no longer shown,
  so the ring clears in one scan with no loop over 60 slots.

**Deliberate differences from TC3:**

- **A TC3 finding: after `RESET_OEE`, its Performance saturates.** TC3's
  `ResetOee` zeroes the time but not `GoodCount`/`NokCount`, which Core
  §8.11.2 resets only on their own logged action (a shift close). So every
  part since the last shift is divided by the run time since the reset:
  Performance caps at 100 % and Quality is the shift's, not the window's.
  That is O7's flattering number. AB's reset takes a count baseline instead,
  so time and parts cover the same window, and the counts themselves stay
  untouched, as §8.11.2 requires. A test shows both figures.
- **Not published: a sample's own A, P and Q, and `Oee.IdealCycleMs`.**
  Nothing reads the first (the HMI's sparkline is OEE alone): they would be
  180 paths in every snapshot, and the ring keeps what they derive from, so
  they are three lines away the day a reader appears (O4). The second is
  already published once, as the model's editable value (O9). The run, down
  and idle buckets, which no HMI reads either, are published, because
  §8.5.1 names their reader: a deployment that re-derives A. The consistency
  gate now has `AB_PUBLISHED_FOR_HOSTS` for exactly that case, each entry
  with its clause, reported stale if the projection drops it.
- **Not built: the `RESET_OEE` gate and audit.** TC3 gates the reset on
  `DATA_WRITE` and logs `std.audit.oeeReset`. AB has no access levels
  (Phase 6), and its ring carries reason codes, not audit texts: the same
  gap as the manual-command audit.

**Tests.** 24 tests (`test_fraktal_ab_oee`): the factors case by case against
TC3's formula; the accounting and the ring on the ST model, including a
30 ms period that does not divide a second; the reset through the real
mailbox; the projection. 16 mutants, all killed (the 16th survived until the
30 ms test). The Phase 5 controller harness gains 5 rows, 15 in total. They
time run and down against the wall clock, check that the first sample lands
60 s after the reset, and check that a second reset retires it and leaves
`GoodCount` alone.

Manifest: Fields 377/512, Localization 354/448, 51,064 bytes (unchanged;
capacity, not content, sets it).

**5d, machine state and rework count (Core §8.11.3, §8.11.2): done, on
hardware, 2026-10-01, on `press47.L5X` (`FF92FDD44C16C06E`).** Phase 5 passed
17/17, with parity 25/25 and Phases 1-4 7/7, 6/6, 8/8 and 11/11
([`Evidence/AB_PHASE5D_MACHINE_STATE_ON_HARDWARE_2026-10-01.md`](../AllenBradley/Evidence/AB_PHASE5D_MACHINE_STATE_ON_HARDWARE_2026-10-01.md)).
On the bench the press walked IDLE, CHANGEOVER, PRODUCING, STOPPED, IDLE, DOWN
and IDLE, as TC3 classifies each.

- **`MachineState`, TC3's classification, derived by the gateway.** It takes
  the first that holds, in TC3's priority: DOWN on a fault or a blocking
  alarm, CHANGEOVER in that mode, BLOCKED and STARVED from the step's time
  class, PRODUCING while BUSY, STOPPED, then IDLE. It is computed from what
  the Unit already publishes, every poll, as AB's `Starved` and `Blocked`
  already were. Those two now share one function with it, so the published
  flags and the state cannot disagree. Nothing on the controller is latched
  for it, and it is not published when the alarm log did not read: DOWN
  depends on the log.
- **TC3's STOPPED is AB's `Aborted`.** TC3 classes `_stopReq OR ABORTED`. Its
  Stop is graceful, so `_stopReq` is only up while the Unit is still BUSY,
  where PRODUCING wins, and STOPPED is in effect ABORTED. On AB that is the
  state a STOP leaves until the reset.
- **`ReworkCount` is a counter on the controller.** It is a Unit member a
  chain counts with a mark, as it counts good and scrap. TC3's press never
  calls `CountRework`, and AB's declares no rework verdict, so both publish 0.
  It is published from the controller rather than as a projected constant, so
  a station that does rework is counted by the same path.
- **STARVED and BLOCKED cannot occur on the bench.** No step of either
  binding's press is an upstream or downstream wait. They are tested on the
  model with a step reclassified.

**A finding in the standard, recorded and not changed: OEE and the machine
state classify time differently.** Core §8.11.3 calls its state set the one
"from which Availability / Performance / Quality follow directly", while
§8.5.1 buckets OEE time by BUSY, ERROR or blocking alarm, and the rest. TC3
implements both literally, and they disagree in corners:

- a Unit running in CHANGEOVER is OEE run time but a planned state;
- a starved or blocked Unit is run time but an external loss;
- a blocking alarm while BUSY is run time (OEE tests BUSY first) but DOWN
  (the machine state tests the alarm first).

AB mirrors TC3 in both, so the two bindings agree. Which clause governs the
OEE buckets is a Core decision.

**Tests.** 15 tests (`test_fraktal_ab_machine_state`): the enum and the
CHANGEOVER ordinal pinned to TC3's DUTs, every state and every priority, and
the published paths. 9 mutants, all killed: the 9th, STOPPED tested before
PRODUCING, needs a Unit both running and aborted, which AB never holds, so
TC3's order is pinned by a test that says so. The Phase 5 controller harness
gains 2 rows (17). One walks the press through every state the bench can
reach, as the gateway publishes it.

**A defect in the mutation tooling, found here and fixed.** A mutant that
swapped two digits left its compiled `.pyc` behind. The restore landed in the
same second with the same file size, so CPython kept serving the mutant, and
the next full run failed on correct source. The scripts now run without
bytecode (`python -B`) and the cache is cleared before a gate or an L5X. No
earlier build was affected: every earlier mutant changed the file's size, and
each build passed its full suite and the bench.

Manifest: Fields 378/512, Localization 355/448.

**5e, the cycle-time profile (Core §8.11.4(b)/(f)): done, on hardware,
2026-10-01, on `press48.L5X` (`E526206F016FC47C`).** Phase 5 passed 19/19, with
parity 25/25 and Phases 1-4 7/7, 6/6, 8/8 and 11/11
([`Evidence/AB_PHASE5E_PROFILER_ON_HARDWARE_2026-10-01.md`](../AllenBradley/Evidence/AB_PHASE5E_PROFILER_ON_HARDWARE_2026-10-01.md)).
On the bench a START's first cycle profiled as the model's: 1,010 ms, 970 of
it work, and the two delays 210 and 310 ms against 200 and 300 expected. The Unit publishes TC3's
`Profiler` where the HMI's cycle view reads it: the last cycle's waterfall,
`LastCycleTime`, `MinCycleTime`, per-step `StepStats`, and the 60-cycle
`History` with each cycle's time by class.

- **Fed from the step record, by one observer, for every rendition.** TC3
  calls `StepChanged` from `M_Step` and `CycleComplete` at the finish step. AB
  has one observer at the end of the routine that reads what each step
  already writes on entry: `StepScan` equals the scan exactly when a step was
  entered, and the chart names the step and its row.
  - An entry closes the step before it.
  - The finish marker, the Unit's `CycleCount` that each rendition counts,
    closes the open step and the cycle, as `CycleComplete` does.
  - A step entered and left in one scan is still recorded, as is the same
    step entered twice.
  - My first version watched `Unit.Step` instead. It missed exactly those
    steps: the init step and a start already latched. The model showed it, in
    a different way in each rendition, before any hardware did.
  - The model now produces the same waterfall in ST, SFC and LD, to the scan:
    `0, 100, 110, … 244, 999` from a START.
- **TC3's arithmetic.** Each step keeps Count, Last, Minimum, Maximum and Avg,
  with Avg as TC3's `F_TimingUpdate` integer running mean,
  `avg += (d - avg) / count`. Time is split by `E_TimeClass`: WORK time, the
  real cycle time, is published beside the total, and the waits beside it.
  Bounds are TC3's: 32 steps a cycle (`Truncated` past that, with the total
  still exact), 60 cycles of trend, durations saturating rather than wrapping.
- **No copies.** The waterfall is double-buffered: a finished cycle becomes
  LastCycle by flipping a half. Statistics are indexed by the step's chart
  row, which its own entry sets, so there is no search.

**Deliberate differences from TC3:**

- **A cycle stood down part-way is abandoned, whatever stood it down.** TC3
  abandons only a stop accepted between cycles. After a fault it carries the
  cycle on through the restart, so the downtime lands in the faulted step's
  Maximum and Avg and in that cycle's total. AB applies `CycleAbandon` to a
  stop, a fault, an abort and a mode change alike: a production cycle is one
  that finished. Steps closed before the stop still count. This is recorded
  as a TC3 finding.
- **A finish step lasts one scan.** TC3 closes N999 in the call that opened
  it (about 0 ms). AB's observer sees its entry and the finish marker in the
  same scan, so N999 shows one task period, 10 ms.
- **Not published, because nothing reads them:** TC3's live `Current` cycle,
  a step row's Last and Minimum (the HMI reads Avg and Maximum; the module
  command rows of 5f publish theirs, which it does read), and the Truncated
  flags. All stay on the controller, described by the manifest.
- **Not built here:** the module command timing of §8.11.4(a) and the
  degradation watch of (d). They are 5f.

**Tests.** 19 tests (`test_fraktal_ab_profiler`): whole cycles in ST, SFC and
LD with identical waterfalls, totals and splits; a second cycle; the running
mean against TC3's integer formula; expected time recorded as a step opens;
truncation; saturation; re-entry; abandon; the published paths, which never
move with a cycle's length. 17 mutants, all killed (the 17th survived until
a second cycle's own split was checked). The Phase 5 controller harness gains
2 rows (19). One profiles a START's first cycle and checks the two delays
against the recipe they expected: 200 and 300 ms took 210 and 310, a delay
being seen to finish one scan late, as the stall watchdog already allows.

Manifest: Fields 413/512, Localization 390/448. Localization has 58 rows
left; the rest of Phase 5 and Phase 6 are sized against that before they are
built.

**5f, command timing and the degradation watch (Core §8.11.4(a), (d)): done, on
hardware, 2026-10-01, on `press49.L5X` (`E54508813767DDD1`)**, after reader
defect D9 was fixed. Phase 5 passed 21/21, with parity 25/25 and Phases 1-4
7/7, 6/6, 8/8 and 11/11
([`Evidence/AB_PHASE5F_COMMAND_TIMING_ON_HARDWARE_2026-10-01.md`](../AllenBradley/Evidence/AB_PHASE5F_COMMAND_TIMING_ON_HARDWARE_2026-10-01.md)).
On the bench:
- the slide's strokes timed at 40 ms, and the door sent open while open at
  10 ms, the command TC3 never times;
- a 300 ms baseline raised exactly one 2007 maintenance event over two cycles;
- the baseline went back to 950.

**A finding for both bindings: paced time counts as WORK.** A SINGLE_STEP
or HOLD_TO_RUN pause falls inside the step it paces, which is a WORK step. So
a stepped cycle reads as a slow one in the profile and trips the degradation
watch; it did on the bench. TC3 classes it the same way. The Core should
decide whether paced time is `WAIT_OPERATOR`, or the watch should stand down
outside CONTINUOUS.

- **Command timing, written once, in the library type.** Every command a
  cylinder runs is timed from acceptance to its end (DONE, ERROR or ABORTED),
  holds included, as TC3 measures it. Each command ordinal 1..8 (TC3's
  `MAX_CMD_STATS`) keeps Count, Last, Minimum, Maximum and TC3's running mean.
  Every cylinder in every application gets it, with nothing written per
  instance. Published as TC3's `Timing/Rows`, where the HMI's command table
  reads it.
- **A TC3 finding: it never times a command that ends where it starts.** TC3
  closes a row on the BUSY to not-BUSY edge between two of its cycles. A
  command accepted and finished in one cycle, such as a cylinder sent to the
  end it is already at, leaves no edge, though §8.11.4(a) says every command.
  AB closes a row whenever the module's Done, Error or Abort count moves, so
  that command is timed at one scan.
- **The degradation watch, at cycle close.** It compares WORK time against
  the running model's `BaselineWorkMs`, now in ParCfg (schema 3 → 4) under
  TC3's `press.recipe.baselineWorkMs` key and range, seeded as TC3 seeds it:
  equal to the model's ideal cycle.
  - Past the baseline by more than TC3's 20 %, it latches once per excursion.
  - A cycle back inside the band re-arms it, and so does a new baseline (TC3's
    `M_SetBaselineWork`).
  - The integer test `work > base + base x 20 / 100` is exactly TC3's
    `work x 100 > base x 120` for whole milliseconds.
- **One maintenance occurrence per excursion.** Each excursion becomes one
  closed ring entry: `CYCLE_TIME_DEGRADED` (2007, now registered on AB), LOW
  as the registry rates it, AUTO_RESET, sourced to the Unit. It is data,
  never downtime, and it can never block a start. The ring write that a
  reported step already used is now one helper shared by both.
- **Differences from TC3:**
  - TC3 attaches its text `std.maintenance.cycleTimeDegraded`. AB's ring
    carries reason codes, so the entry reads as `std.reason.2007`, like every
    registered reason: the same gap as the audit texts.
  - The entry is logged one scan after the cycle closes, because the alarm
    log runs before the profiler in the routine.
  - TC3's `LastCmdTime` and `Truncated` stay on the controller, because
    nothing reads them.

**Tests.** 18 tests (`test_fraktal_ab_command_timing`) cover:
- the cylinder alone: a stroke, a command already at its end, a hold, a
  timeout, an abort, the running mean, an ordinal past the rows;
- every cylinder over a whole cycle;
- the published rows;
- the watch: the latch, the band edge, waits not counted, re-arming, off at 0,
  and the ring entry from the real alarm log.

There were 18 mutants. 17 were killed. The 18th showed a guard that could not
decide anything, because a passive type carries no timing, so the guard was
removed. The Phase 5 controller harness gains 2 rows (21):
- one times manual commands, including the door sent open while open;
- one writes the running model's baseline down to 300 ms, expects exactly one
  maintenance event over two cycles, and always writes it back.

Manifest: Fields 446/512, Localization 409/448. That leaves 39 Localization
rows: enough for the rest of Phase 5, not for Phase 6, which raises the table
and re-measures first.

**5g, derived state flags (Core §3.12): done, on hardware, 2026-10-01, on
`press50.L5X` (`1C7043DB55AC904B`).** Phase 5 passed 23/23, with parity 25/25 and
Phases 1-4 7/7, 6/6, 8/8 and 11/11, and the gateway, restarted onto the D9 fix,
ready throughout
([`Evidence/AB_PHASE5G_STATE_FLAGS_ON_HARDWARE_2026-10-01.md`](../AllenBradley/Evidence/AB_PHASE5G_STATE_FLAGS_ON_HARDWARE_2026-10-01.md)).
On the bench the load-position flag cleared the moment a MANUAL command moved
the slide, and set again when it came back, each change stamped later. The Unit publishes TC3's
`StateFlags` table and `StateFlagCount` where the HMI reads them. Each flag
carries its key, its value, the moment it last changed and `Stale`.

- **TC3's two press flags, under its keys and in its order:**
  - `pressAtLoadPosition`: TC3's `OutImm.Homed`. Every cylinder retracted and
    none extended.
  - `pressTwoHandStartReady`: the two-hand armed, a part present with good
    quality, and air.

  They are declared like a permit, from module states, and validated the
  same way.
- **Derived on the controller, every scan, never latched.** One generated `IF`
  per condition keeps each expression inside Studio's five-operator limit.
  `Since` is stamped from the controller clock on the first scan and on every
  change, and only then. So a jog off the load position in MANUAL clears the
  flag at once, which is the reason TC3 made `Homed` a flag and not a command
  result.
- **`Stale` is always false, and truthfully.** TC3's `Stale` catches a
  `_M_State` call left behind an `IF` that stopped running. AB's flags are
  declared and emitted unconditionally, so none can stop being computed.
- **One difference from TC3.** TC3's start-ready flag also needs
  `ControlDomain.ReadyForStart`. This bench has no control-power domain, and
  TC3 treats an absent domain as no start gate, so the term is omitted rather
  than faked.

**Tests.** 17 tests (`test_fraktal_ab_state_flags`): each flag against every
condition on the ST model, never latched, `Since` stamped at first (a flag
false from the start included) and on change only, the declaration rules, the
published table, and the operator limit. 12 mutants, all killed (two survived
until a flag false from the start and a false flag's `Stale` were checked). The
Phase 5 controller harness gains 2 rows (23):
- the press walked off its load position and back in MANUAL;
- the start-ready flag followed the part sensor.

Manifest: Fields 451/512, Localization 414/448.

**5h, system health: S3 first, now measured on hardware, 2026-10-01, on
`press51.L5X` (`2429AD8014904A38`).** Studio accepted every GSV attribute. The
read-only measurement gave:
- execution 545-882 µs against the 10 ms period, peaking at 1,190 µs under the
  full harness load;
- jitter at most 198 µs, with no overrun;
- no PTP and no fault bits;
- regression unchanged: parity 25/25, Phases 1-5 7/7, 6/6, 8/8, 11/11 and 23/23.

S3 is **PARTIAL**: task timing, time quality and controller faults settled;
module connection state still owed
([`Evidence/AB_S3_HEALTH_AND_TIMING_2026-10-01.md`](../AllenBradley/Evidence/AB_S3_HEALTH_AND_TIMING_2026-10-01.md)). Part III marks §8.11 task timing and
§8.12 system health **PROVISIONAL S3**: "GSV and module objects supply health
and timing", reduced to a declared subset. TC3's publisher evaluates 11
conditions against a ParCfg and raises a LOW/SYSTEM/AUTO_RESET event for each,
over a probe of the platform. Most of that probe has no Logix source: no CPU
load or free memory through GSV, no IPC temperature or fan, no EtherCAT or DC.
Building the publisher on attributes this controller has never answered for
would be guessing, and one wrong GSV name fails the whole import. So S3 runs
first.

- **The probe.** A read-only `FRK_Press_HealthProbe`, AB's `ST_SystemHealthInput`:
  - TASK `LastScanTime`, `MaxScanTime` and `OverlapCount`;
  - TimeSynchronize `IsSynchronized` and `PTPEnable`;
  - FaultLog `MajorFaultBits` and `MinorFaultBits`;
  - the task's real period and jitter, from the wall clock between scans, as
    TC3's probe takes them from its monotonic clock, published per one-second
    window.

  Every attribute is DINT-typed. Nothing depends on the probe yet.
- **The measurement.** `fraktal_ab_s3_execute.py` is read-only: it writes no
  tag and issues no command. The import passing is the first answer. Its
  samples are the second, and they decide §8.12's declared subset. The
  publisher, its ParCfg and its events are then built on what the controller
  really reports. A group with no source stays `Available = FALSE`, as TC3's
  own press publishes its controller and time groups outside simulation.
- **Tests.** 8 tests (`test_fraktal_ab_health_probe`) cover the exact GSV
  set, the period and jitter (minute wrap included), the window, and the
  probe's place after the clock read. 8 mutants, all killed.

**Nameplate: a contract decision before any build.** TC3's press sets no
nameplate value, so the HMI shows none on either binding. Building the path
for a press that declares nothing would be surface nobody pays for. There is
also a real obstacle: the frozen v1 manifest `Nameplates` table carries
Manufacturer, Product, Model and Serial keys plus two numeric revisions. The
HMI reads TC3's IDTA fields, which include `ProductUri`, `YearOfConstruction`,
`FirmwareVersion`, `OrderCode` and `DocumentationUrl`, and the table cannot
carry them. That is an additive contract change (v1.x columns) to decide
first. It is recorded as **N** for the press until a station declares a
nameplate.

Manifest: Fields 471/512, **Localization 434/448**. The next build raises
Localization before it adds anything; the health publisher needs room, and so
does Phase 6.

**5h, the system-health publisher (Core §8.12): done, on hardware,
2026-10-02, on `press52.L5X` (`4FD8961CE0AA3E17`).** Phase 5 passed 25/25. The
55,160-byte manifest read back whole in 147 ms. S3, parity and Phases 1-4 all
pass, Phase 3 after a harness fix: one row had taken the first open alarm slot
to be the fault, and the standing health event now holds it
([`Evidence/AB_PHASE5H_SYSTEM_HEALTH_ON_HARDWARE_2026-10-02.md`](../AllenBradley/Evidence/AB_PHASE5H_SYSTEM_HEALTH_ON_HARDWARE_2026-10-02.md)).
On the bench:
- the task measured 10,167 µs with 167 µs of jitter;
- one standing CONTROLLER_METRICS_UNAVAILABLE event, not blocking;
- `Healthy` false by construction. TC3's `FB_SystemHealthPublisher`,
over S3's measured subset. The Unit publishes `SystemHealth` where the HMI's
health facet reads it.

- **The thresholds** are TC3's `ST_SystemHealthParCfg`, schema-first (schema
  1, as TC3), reduced to what this controller reports:
  - the maximum task period, 20 ms, twice the 10 ms period;
  - the maximum jitter, 2 ms, ten times S3's worst;
  - whether time sync, a fieldbus or a distributed clock is required.

  TC3's press requires its EtherCAT and its time sync. This bench has local
  I/O and runs without PTP by design (S1, S9, S3), so it requires neither: a
  requirement it could never meet would be a standing false alarm.
- **The evaluation follows TC3's.** Nothing is judged on the probe's first
  sample, as TC3's MAIN skips it, so a download raises no false overrun and
  nothing claims healthy before it has been judged.
  - An overrun is `OverlapCount` moving, or a real period over the threshold.
  - Jitter is judged against its own threshold.
  - A required clock that is not synchronized is bad.
- **CONTROLLER_METRICS_UNAVAILABLE is TC3's own rule, kept.** CPU load and
  free memory have no GSV source (S3), so the station says so, as one standing
  LOW event, as TC3's own press does outside simulation. `Healthy` is therefore
  false on this bench by construction. That is `Present=TRUE, Healthy=FALSE`,
  which Core §8.12 defines as "a required probe is unavailable".
- **Each condition is an AUTO_RESET event while it lasts.** It is raised once
  into the active list and closed into the ring when it clears. It never
  blocks a start, and an operator reset does not close one that is still
  true.
  - The registry rates the events: TASK_OVERRUN is MED and
    FIELDBUS_MASTER_FAULT is HIGH, where TC3's publisher proposes LOW. A
    registered reason's rationalization wins.
  - The six are registered under TC3's System-band codes (10, 11, 15, 16, 17,
    21) and pinned to TC3's `E_Reason` by test.
  - The alarm log's raise and close-into-ring code is now one pair of helpers,
    shared by the fault event, the operator reset and these.
- **Unmeasurable groups are published unavailable, never healthy:** CPU,
  memory, IPC, fan, storage, fieldbus and distributed clock. Time quality is
  the controller's: available, and synchronized only if PTP says so.
- **Room.** Localization goes 448 → 512 and the manifest budget to 56 KiB
  (57,344 bytes), by the same cost-curve rule. press52's manifest is 55,160
  bytes. Like every raise, it is confirmed by reading it back from the
  controller.

**Tests.** 20 tests (`test_fraktal_ab_system_health`): every condition, the
first-sample rule, invalid thresholds, the events from the real alarm log, and
the published facet. 16 mutants, all killed (one survived until the first
scan's published overrun flag was checked). The Phase 5 controller harness
gains 2 rows (25): the facet as published, and the one standing event.

Manifest: Fields 485/512, Localization 460/512, Rationalization 20/32.

**After Phase 5: a new station starts with all of it (2026-10-01).** The
features above are only parity if a project can use them. Until now, the
generic tools were bound to the press: the generator, the projection, the
manifest reader and the gateway's hash check all imported its declaration.
- **One selector.** `fraktal_ab_station.py` reads `FRAKTAL_AB_DECLARATION`, and
  the press is the default. Every generic tool reads it, so a new station is
  selected in one place. The press harnesses stay the press's.
- **A template with everything on.** `fraktal_ab_station_template.py` is the
  smallest station that uses every Phase 0-5 feature. The opt-in features stay
  opt-in, as in TC3, because each is a claim only the project can make. The
  template makes all of them, so a copied project removes rather than
  discovers.
- **Helpers carry TC3's values:** `decl.ideal_cycle_ms`,
  `decl.baseline_work_ms` and `decl.SystemHealth.for_task`. The press now uses
  them and still emits byte-identical to press52, so the controller is current.
- **The guide** is `Specification/Guides/AB_NEW_PROJECT_GUIDE.md`.

Building the template found three defects that the press had masked.
1. **The ST and SFC emitters needed `WAIT_CONDITION` for every DELAY step.** The
   validator requires it only where a condition can pause the delay, so a
   station without it validated and then could not be generated. The press
   registers it anyway. It is now looked up only where it is used, as the LD
   emitter already did.
2. **The projection still declared `Oee/*` absent.** Phase 5c published OEE,
   so the `absent` list told every client something false. The test written to
   catch exactly that built its document without OEE state. It now builds every
   facet, and it failed on the stale entry before the fix.
3. **The localization gate skipped some keys.** It never collected type keys,
   model names, state-flag keys or decision prompts. The press passed only
   because TC3 had catalogued those keys already, so a new station would have
   shipped them raw with the gate green. The gate now collects them, from the
   selected station. The read-surface check stays on the press, because it
   measures the binding.

Mutation: each fix has a test that fails without it, four mutants in all.

### Phase 6: configuration completeness and access

**Item 0 complete on hardware, 2026-10-01.**
`press53.L5X` raises Fields and Localization to 768 rows each, with 485 and 460
used respectively. The manifest is 79,736 bytes; the budget is 96 KiB to allow
the same capacities with keys up to 80 characters. S7's cost curve projects
534 ms at a 500-byte connection and 112 ms at 4000 bytes for this build;
full controller readback measured 177.236 ms, coherent, with every row equal
and both raised capacities confirmed.

The pressure tests cross the old 512-row bounds on both the press and the
station template. They also found that the generator reported its byte budget
but never enforced it: an oversized or truncated manifest could become a
downloadable project. It now rejects either overflow before writing output.
The old 512-row controller is refused even with the matching contract hash.
Only the manifest header and the two enlarged array tags differ from press52;
all other project elements are equal. Build evidence:
[`AB_PHASE6_ROOM_BUILD_2026-10-01.md`](../AllenBradley/Evidence/AB_PHASE6_ROOM_BUILD_2026-10-01.md).

The owner downloaded press53 and restarted the gateway. S3 passed 6/6,
parity 25/25, and Phases 1-5 passed 7/7, 6/6, 8/8, 11/11 and 25/25 on serial
`7036B510`. Every writing fixture disarmed; the gateway stayed ready. The AB
suite passed 1292 tests, consistency 32, with 0 errors and 0 warnings.
[Hardware evidence](../AllenBradley/Evidence/AB_PHASE6_ROOM_ON_HARDWARE_2026-10-01.md).
This item adds no write routes; the write-enabled claim remains owed until S9.

**Item 1 complete on the bench, 2026-10-01.**
Press54 registers the root's published `Profiler.LastWork` as the source for
editable `BaselineWorkMs`, on both the press and station template. Capture
samples that source and rejoins typed-write validation/storage. It checks the
capability revision, manual setup mode, declared release permissives and root
readiness, and refuses unregistered/foreign/stale captures by name. Accepted
typed writes and captures share a bounded 16-entry controller audit recording
value, field, model, source, revision, timestamp and the request's claimed actor.
That actor is not authenticated on the controller until item 3; `DATA_WRITE`
and S9 remain owed. The audit is read on demand rather than streamed by the HMI.

D5's paired positives and negatives pass in both gateways. A viewer may issue
only a complete, inert `QUERY_CONFIG` batch to its readable root; missing or
nonempty unused arguments, nested members, other roots and mutation kinds do
not obtain that exception. AB now serializes shared-mailbox transactions across
viewers and operators, as TC3 does. No AB screen was added.

The new WriteCapabilities row is versioned V3 and the manifest major is 3;
the owner downloaded press54 and restarted the gateway. It is 79,992 bytes with
Fields 499/768 and Localization 477/768 on the press (template: 313 and 388).
The 100 KiB generation bound preserves the 98,472-byte envelope for 80-character
keys. The press and template reproduce byte-for-byte, with unchanged module
AOIs, I/O, task configuration and AUTO graph. Only the mailbox behavior changes;
Main's changed numbers are interned diagnostic keys.

Offline gates: AB 1324, HMI 428 passed/6 skipped, gateway 24/24, Flutter analysis
clean, consistency 32 with 0 errors and 0 warnings. Mutations: Python 18/18 and
TC3 gateway 4/4 killed. [Build evidence](../AllenBradley/Evidence/AB_PHASE6_CAPTURE_BUILD_2026-10-01.md).

On serial `7036B510`, both manifest reads were coherent and every row matched;
the repeat read completed in 180.092 ms. The guarded Phase 6 suite passed 10/10:
the read-only query was accepted while START was refused before any write;
capture sampled, stored and audited 970 ms WORK from a completed cycle, ignoring
the client's candidate. Stale/foreign/unregistered requests, AUTO mode and missing
air were refused. Baseline 950, AUTO mode and CONTINUOUS style were restored and
read back. S3 passed 6/6, parity 25/25, Phases 1–5 passed 7/7, 6/6, 8/8, 11/11
and 25/25; all ten fixture inputs cleared after every writing harness. The gateway
remained ready. AB 1324 and consistency 32 passed again before the evidence commit,
with 0 errors and 0 warnings. [Hardware evidence](../AllenBradley/Evidence/AB_PHASE6_CAPTURE_ON_HARDWARE_2026-10-01.md).
The template and TC3 gateway retain their offline evidence; this run measures the
AB press. Controller access and the write-enabled S9 claim remain owed.

**Item 2 complete on the bench, 2026-10-02.**
Press55 and the station template enable the six parameter-set kinds. The
controller takes an immutable CPS copy, validates the complete station load
against the declaration's capability schema, and commits only after every
record passes. No child WRITE_CONFIG transactions or partial application are
used. Root READY, foreign root, schema/revisions, duplicate and unknown keys,
types and ranges are controller checks. Model save/export works; model load
explicitly refuses until recipe-store integration, matching TC3.

The gateway owns four named portable JSON-line documents, with 480-character
lines, 255-character fragments and atomic replacement. Import never applies
values. Catalog/export/rejection answers are connection-local and excluded
from cyclic HMI streaming when the read profile requests it. The controller's
16-entry audit records accepted/refused requests and their claimed User.
Save/delete/final import expose a five-second Pending/Failed store-receipt
window; physical controller retention remains provisional. ACK_CONFIG_RESTORE
retains its existing loss gate. The offline build made no controller-changing
operation; the owner's subsequent `done` armed the named verification fixtures.

The manifest remains major 3, 79,992 bytes under the 100 KiB budget, with
Fields 526/768 and Localization 514/768 (template: 340 and 425).
Press and template reproduce byte-for-byte. Against press54, module AOIs, I/O,
tasks and native SFC/LD are unchanged; only Main and the mailbox routine change.
Offline gates: AB 1363, HMI 429 passed/6 skipped, consistency 32 with 0 errors
and 0 warnings, Flutter analysis clean. Mutations: Python 23/23 and HMI 2/2
killed. The new `--sets` fixture restores every station value and only its
four named documents in an isolated directory; the parent also restores
mode/run style/baseline and disarms all ten fixture inputs. The
[build evidence](../AllenBradley/Evidence/AB_PHASE6_SETS_BUILD_2026-10-02.md)
records the artifact hashes and original owner handoff. This widens writes to whole
station sets; controller per-user enforcement and the write-enabled S9 claim
remain owed.

The owner downloaded press55 and restarted the gateway. Its 79,992-byte manifest
read back coherent and equal twice, in 199.605 and 171.329 ms. The set fixture
passed 17/17: save/reopen/list/export, changed values restored by load, import
without application, complete imported load, unknown/invalid/stale/foreign
refusals with exact identity, model-load refusal, root READY, unauthenticated
viewer, restore-ack refusal and deletion. All five station values were restored,
the isolated stores emptied, and baseline 950, AUTO/CONTINUOUS and all ten
fixture inputs restored. Controller readback has Pending 0, Failed 0 and a full
16-entry set audit containing accepted and refused requests.

The first attempt failed with `stale mailbox sequence: expected 56, got 57`:
direct fixture helpers had advanced the controller outside the fixture gateway.
Controller values and inputs restored; the four remaining fixture documents
were then deleted through a fresh serial-guarded client. The shared idle helper
now accepts a command callback and every set-fixture mailbox command uses its
own gateway. The READY check also tests the returned unit rather than the wait
tuple. These are harness fixes only: press55 still reproduces byte-for-byte.
The failure, cleanup and successful rerun are all preserved in the
[hardware evidence](../AllenBradley/Evidence/AB_PHASE6_SETS_ON_HARDWARE_2026-10-02.md).

Capture passed 10/10, S3 6/6, parity 25/25 and Phases 1–5 passed 7/7, 6/6,
8/8, 11/11 and 25/25. Every writing harness disarmed; the gateway remained ready.
Final task maximum scan was 1,710 µs against the 10,000 µs period, with zero
overlap and fault bits. Before the evidence commit, AB 1364 and consistency 32
passed with 0 errors and 0 warnings; three new harness mutations were killed.
The template and HMI retain their offline evidence. The physical retention
matrix, controller per-user access and the write-enabled S9 claim remain owed.

**Item 3 built offline — controller per-user access (press56, 2026-10-02).**
The declaration now owns private salted registrations and generates the same
initial SHA-256 plus 256 rounds as TC3. LOGIN consumes and wipes the secret,
then completes in the background while the mailbox remains available. The
generic HMI waits for the PLC outcome. All mutations, including native CIP,
check controller levels; policy, idle timeout, logout cancellation and the
ENGINEER restore-acknowledgement check are controller-owned. Configuration and
set audits use the authenticated session actor. Access events share the existing
64-slot closed-event ring and contain no PIN.

Press56 and the empty-user template reproduce byte-for-byte. Manifest bytes
remain 79,992; press Fields 544/768 and Localization 541/768; template 358/768
and 452/768. The press ContentHash is `0FC1A37DB998B41C`, revision 1032611.
The offline SDK could not open press56: **No valid license**. Owner Studio v33
Verify/download and the guarded `--access --execute-fixture` proof are pending,
including native spoof rejection, plant mutation, idle expiry and task cost.
The v33 legacy bench remains write-enabled by the 2026-09-29 decision; this item
widens writes to login and policy, while **S9 remains owed**. Physical retention,
model-load integration, data classes and shelving also remain owed. See the
[build evidence](../AllenBradley/Evidence/AB_PHASE6_ACCESS_BUILD_2026-10-02.md).

Order follows the Phase 6 handover:

Owner Studio v33 Verify of press56 subsequently reported 54 undefined-tag
errors for TRUE. Press57 corrects the shared BTDT EnableIn assignment to `1`;
the generated project otherwise matches press56 exactly, and the manifest is
unchanged. The ST model and platform gate now catch the literal-name mistake.
Press57 was the next owner Verify/download artifact. The original offline
record is preserved; see the [correction evidence](../AllenBradley/Evidence/AB_PHASE6_ACCESS_BOOLEAN_FIX_2026-10-02.md).

Owner Verify of press57 then reported **Out of memory in the controller**,
one error and zero warnings. Press58 allocates private user rows from the
declaration and versions the audit as V2 with packed actor bytes. It retains
at that point the sixteen-user ceiling, all 64 events, full names and the TC3
authentication semantics. Rotates and audit writes are generated once; SHA finalization uses
loops and its round constants are a private constant table. The press saves
10,112 declared data bytes and the template saves 10,768; SHA plus rotate ST
drops from 724 to 222 lines. No compiled-memory figure or fit is inferred from
these counts. ContentHash is now `D90151DAB7A1FC1B`, revision 14221649;
the 79,992-byte manifest and row counts are unchanged. AB 1404 and root 33
tests pass, consistency has zero errors/warnings, and 33/33 mutations are
killed. The SDK again refuses **No valid license**. Press58 is the pending
owner Verify/download artifact; hardware task cost, physical retention and
S9 remain owed. See the
[memory correction evidence](../AllenBradley/Evidence/AB_PHASE6_ACCESS_MEMORY_FIX_2026-10-02.md).

The owner then requested a four-user ceiling. Registrations now stop at four;
a fifth is rejected before output generation. Press58 already allocates only
three user rows, and the template has one inert row, so regenerated artifacts
are byte-identical to those recorded above. The owner now reports press58
downloaded; guarded controller proof is next. No replacement download is
introduced by this ceiling change. See the
[four-user limit record](../AllenBradley/Evidence/AB_PHASE6_ACCESS_FOUR_USER_LIMIT_2026-10-02.md).

**Item 3 controller gate failed (press58, 2026-10-02).** The manifest is
coherent and equal on serial 7036B510: 79,992 bytes, hash `D90151DAB7A1FC1B`,
revision 14221649, read in 175.597 ms. The gateway is ready. The first S3
sample passed 6/6 with maximum scan 1,166 µs, zero overlap and zero fault bits.
The armed access fixture failed with `controller login result did not settle`
at its six-second wait. The controller audit later recorded a successful admin
login. Hash work raised maximum scan to 31,065 µs against the 10,000 µs period,
overlap to 606 and minor fault bits to 64; major bits remain zero. S3 passes
6/6 during the subsequent idle sample because overlaps are then steady; this
does not validate the hash workload.

Policy, timeout, station.number, baseline, mode and style finished restored,
and all ten inputs disarmed. Intermediate admin-login and immediate timeout-
disable cleanup acknowledgements failed, so no fixture pass is claimed.
No controller fault or task counters were cleared. Other writing regressions
stopped. The next correction must divide or optimize the hash workload within
the task budget and keep the generic provider wait consistent with measured
latency, preserving all 257 hashes and mailbox availability. S9 remains owed.
See the [failed hardware evidence](../AllenBradley/Evidence/AB_PHASE6_ACCESS_HARDWARE_FAILURE_2026-10-02.md).

**Item 3 runtime correction prepared (press59, 2026-10-02).** The owner
requested rotating the bench admin PIN and testing login. The declaration
contains its fresh salted hash and the protected local fixture matches it.
The real emitted SHA authenticates that account in the offline execution model.
Hashing now advances through a private phase/cursor: at most eight rounds per
scan, including only the schedule words those rounds need. One block takes ten
scans; 257 blocks take 2,570 task periods. The read-only V2 session appends
`LoginTimeoutMs`, derived from that bound plus 10 seconds of client margin.
The HMI waits for the provider budget rather than a fixed six seconds. On this
bench the nominal scheduling is 25.70 seconds and the client wait is 35.70.
Neither is a measured controller cost. The new owner artifact is
`C:\work\press59.L5X`; updated HMI, owner Verify/download and guarded runtime
proof remain pending. No controller write, download, gateway startup or fault
clear was made while preparing this correction. S9 remains owed.
See the [runtime correction evidence](../AllenBradley/Evidence/AB_PHASE6_ACCESS_RUNTIME_FIX_2026-10-02.md).

**Item 3 performance correction prepared (press61, 2026-10-02).** The owner
reported early HMI failure and eventual login after retries. Serial-guarded
reads confirm the press59 contract and a successful admin audit; later requests
were refused as LOGIN_BUSY. A single native LOGIN using the protected matching
fixture was consumed in 112.94 ms and authenticated in 25,776.784 ms. Task
overlaps stayed zero, maximum scan stayed 6,388 us, and major/minor bits stayed
zero. This is a login-only result, not the full item 3 regression gate.

Press61 removes the compression's native bit-distribution and per-round
subroutine calls, and computes modular sums with signed high limbs. Exact
masked division avoids Logix rounding and all intermediates remain DINT.
One block per task scan retains all 257 hashes and the same registrations:
2.57 seconds of nominal scheduling, 12.57 seconds of client budget. Actual
controller scan cost is pending. Private work is V4; unused native bit scratch
and rotate routine are removed. Public ContentHash remains unchanged because
logic/private storage/provider initial values are outside that hash. The HMI
uses a monotonic deadline, bounds stalled reads and distinguishes unavailable
results from incorrect credentials. Owner Verify/download of
`C:\work\press61.L5X`, updated HMI deployment and the full hardware matrix
remain pending. No policy, plant input, mode, timeout or fault/counter writes
were made for this correction; only the explicitly requested login was tested.
See the [performance evidence](../AllenBradley/Evidence/AB_PHASE6_ACCESS_PERFORMANCE_FIX_2026-10-02.md).

0. Manifest room, with the raise confirmed by full controller readback.
1. `CAPTURE_CONFIG`, with D5's read-only configuration query fixed in both gateways.
2. Parameter sets, with the gateway as the store and the controller staging and
   validating, including `ACK_CONFIG_RESTORE`.
3. Per-user access on the controller (Q1): user table, PINs as salted hashes,
   LOGIN/LOGOUT, levels and session timeout, re-checked on every mutation.
4. Data classes (§3.8d), once access is enforced.
5. Alarm shelving (§8.10), once Phase 1's event core exists.
6. **The write-enabled contract suite (S9).** It has to land before the
   write-enabled claim can be recorded as anything but owed.

### Deliberately not planned

Line profile, control power, safety profile, signal tower, host events (§6.7).
Each is either decided or impossible on this bench. Revisit them only if that
changes.

## 9. Platform rules every item must respect

These come from Logix v33 and from measurements already recorded. Each one has
already cost a defect in this binding.

- **ST cannot assign a string literal.** Any text shown to an operator is
  interned at emission and referenced by a numeric key.
- **A public UDT carries no BOOL** (S12). Everything is a DINT.
- **An AOI cannot reach controller scope.** A chain raises a request and the
  main routine does the work, as the model commit now does.
- **Table capacities are measured, not chosen.** Localization is at the edge of
  S7's envelope; see §5.
- **Anything a client must not miss is recorded on the controller.** Polling
  loses transients. This applies to alarms (§6.1) and to §3.13 marks.
- **An expression takes at most five operators of one kind.** Studio v33
  rejected press36 with "Too many 'OR' operators in expression with enough
  parentheses" on a line with six `OR`s; press35 had compiled the same line
  with five. A chain that grows with the application is therefore written as
  one `IF` per term, never as one operator per term, and
  `test_fraktal_ab_platform_limits` holds every generated ST line to five,
  including for an application with twelve more modules. `AND` is held to the
  same five, the most yet compiled.
- **A download needs a gateway restart.** The gateway loads the declaration at
  start and fails closed on a hash mismatch. This happened three times on
  2026-09-29 and once more on 2026-09-30, seen each time as "commands do
  nothing". Since 2026-09-30 the gateway compares the controller's hash with
  the declaration as the files say *now* (a fresh interpreter, cached per
  controller build) and names the fix: restart, download, or both. The text is
  logged once and published in `/healthz` as `controllerRefusal`.


**Item 3 split login prepared (press62, 2026-10-02).** A serial-guarded
read of the owner's loaded build found the 12,570 ms budget, authenticated admin,
32,136 µs historical maximum scan, 771 overlaps, major fault bits 0 and minor
fault bits 64. Press61's offline estimate did not hold on the controller.
No login writes or counter/fault clears were issued after that observation.
Press62 moves only the KDF prefix to the gateway. It retains the same
registrations and full 257-hash derivation; the PLC verifies the last hash and
chooses the private registered level. Profile 1 is a preimage, not the stored
hash. The fast path is ten bounded controller phases; native PIN clients retain
the full path. The generic HMI checks the optional completed-result sequence
and never calls an unsettled empty/old session a credential rejection.
Owner Verify/download, gateway restart, updated HMI deployment and timing proof
remain pending. The licensed SDK still refuses compilation on this host.
See [evidence](../AllenBradley/Evidence/AB_PHASE6_ACCESS_SPLIT_FIX_2026-10-02.md).

**Item 3 served HMI correction (2026-10-02).** The owner reports acceptable
login latency but a failure message before the session appears. Read-only
controller and gateway observations match the press62 public contract and show
a successful admin result with healthy task metrics. The running Flutter web
server still serves the old repository module: it reads the session once after
mailbox consumption, without the pending/result-sequence checks already in the
committed source. Restarting that HMI server from current source changes the
served module and includes those checks. Chrome must reload the application.
No controller writes, download or gateway restart were performed. This records
a served-client correction, not the full access regression or S9. See
[evidence](../AllenBradley/Evidence/AB_PHASE6_HMI_STALE_CLIENT_FIX_2026-10-02.md).

**Item 3 access gate passed (press62, 2026-10-02).** The final guarded
fixture passes 16/16, and all settings and fixture inputs are restored.
The first attempt exposed a broker error when access rejects a set command
before set dispatch. Its old set-state sequence is irrelevant to the matching
mailbox refusal; accepted operations still require their own set state before
host I/O. The second attempt exposed native probes replaying the preceding
gateway command's sequence. The fixture now seeds from the controller before
each native request, correlates login results and audits the probe's own actor
and sequence. The final run proves the PLC's access refusal and actual accepted
write independently of mailbox consumption. No PLC source changed; press62
regenerates byte-identically. The owner must restart the running gateway to
load the broker fix. Item 4 data classes is next; S9 and physical retention
remain owed. See
[evidence](../AllenBradley/Evidence/AB_PHASE6_ACCESS_ON_HARDWARE_2026-10-02.md).

**Item 3 actual HTTPS release corrected (2026-10-02).** The owner identified
the Chrome URL as `https://press.localhost/` after again seeing a failure dialog
over a successful session. The earlier served-client correction only updated
the Flutter development server on port 5555. Caddy's actual static root still
contained the September 29 release without pending-login or result-sequence
handling. The tested final Web artifact is now deployed into that root; all
42 resource hashes match and the prior directory is retained as a backup.
The site's authentication requirement remains in place. No PLC source, download,
controller write, gateway restart or proxy configuration change was made.
Chrome must hard-refresh; owner confirmation of the visible dialog remains
pending. This does not advance S9. See
[deployment evidence](../AllenBradley/Evidence/AB_PHASE6_HMI_HTTPS_DEPLOYMENT_FIX_2026-10-02.md).

**Item 4 data classes prepared (press64, 2026-10-02).** The owner confirmed
the corrected HTTPS login now works. The press and station template declare
`public` and `commissioning`; the PLC resolves class levels and immutable value
minimums once for every operation. Station number uses `public`; pressure
calibration has an ENGINEER write minimum. QUERY_CONFIG keeps metadata visible
and blanks unreadable values. Typed writes/captures check the value; set load
checks every record before any commit, and export checks every record before
returning even the header, naming the first inaccessible record. SAVE/DELETE
remain CONFIG_SET-only. SET_CLASS_LEVEL is ACCESS_POLICY-gated, including
native clients. Policy has a separate retained tag and startup keeps edits;
unknown classes and corrupt levels require ADMIN. The gateway projects PLC
levels and the existing HMI renders the class editor without an AB screen.

Manifest major 4 appends class/minimum metadata; AccessAudit V3 preserves the
V2 prefix and appends refused-value/required-level metadata. AccessState V3,
registrations, module AOIs, I/O and tasks are unchanged. The 80,760-byte artifact
reproduces byte-for-byte; its hash is `7E0EC4F58C126852`, revision 8261316.
Offline semantic and mutation gates pass; the SDK cannot open it because
there is **No valid license**. Owner Studio Verify/download, gateway restart
and guarded `--data-classes` hardware verification are pending. No controller
write, download or gateway restart was performed for this build. The tested
HMI release is deployed at `https://press.localhost/`, with its prior directory
retained. Physical retention and the write-enabled S9 claim remain owed.
See [build evidence](../AllenBradley/Evidence/AB_PHASE6_DATA_CLASSES_BUILD_2026-10-02.md).

**Item 4 data-class gate passed (press64, 2026-10-02).** The owner reported
deployment complete. On serial 7036B510 the entire 80,760-byte major-4 manifest
is coherent and equal; repeat readback takes 171.458 ms. The guarded fixture
passes 18/18, proving actual public/calibration writes, immutable ENGINEER
minimums, native impersonation refusal, hidden values with retained metadata,
ACCESS_POLICY-gated class edits, and set load/export refusal before any commit
or header disclosure. Save remains CONFIG_SET-only, and the denial audit names
the actual technician, value and required level.

The read-only preflight initially refused because the owner had already logged
in as admin; it performed no writes. A serial/fingerprint-guarded logout prepared
the anonymous role-test baseline. Values and policies were restored afterward,
and the owner's original admin session was restored after all regressions.
Access passes 16/16, capture 10/10, sets 17/17, S3 6/6, parity 25/25 and
Phases 1–5 7/7, 6/6, 8/8, 11/11 and 25/25. The positive set fixture runs under
admin to satisfy the new calibration minimum; no policy is relaxed for it.
Maximum task scan is 5,259 microseconds, overlaps and fault bits zero. All ten
fixture inputs are cleared and the gateway remains ready. Offline AB 1,448 and
consistency 33 pass, with zero consistency errors/warnings. No PLC source,
HMI source, download or gateway restart was changed by the agent for this
verification. Item 5 alarm shelving is next; physical retention and the full
write-enabled S9 suite remain owed. See
[hardware evidence](../AllenBradley/Evidence/AB_PHASE6_DATA_CLASSES_ON_HARDWARE_2026-10-02.md).

**Item 5 shelving prepared (press65, 2026-10-03).** One generated alarm-log
mechanism serves press and template through the existing generic HMI.
Source+description must identify exactly one non-closed event. The controller
checks ALARM_SHELVE and the same registry rationale that emits the manifest;
safety, unknown reasons and non-shelvable flags refuse. Whole-second duration
refuses zero/subsecond values and caps at TC3's eight hours. Task-duration
countdown is independent of calendar changes. Shelve, unshelve and automatic
expiry are LOW AUTO_RESET events in the existing ring, with the actual actor
for operator requests and no claimed actor for expiry. Shelving never clears
blocking, command state, interlocks or release rows. Slot reuse clears the shelf.

AlarmActive/Ring V2 preserve the V1 prefix and append Shelved, which the HMI
already reads; countdown remains private. AccessState V3, AccessAudit V3 and
private registrations are unchanged; AccessWork becomes private V6. No new
manifest row layout is needed: major 4 remains, but the content hash changes to
`832DD0D0F260872B`, revision 8596944. The 80,760-byte manifest uses Fields
565/768 and Localization 570/768. Press65 and the template reproduce exactly,
and module AOIs, chains, I/O and tasks remain unchanged. Nine in-memory
mutations are killed. Owner Studio Verify/download and guarded `--shelving`
verification remain pending: the SDK refuses **No valid license**. The harness
restores a known original session, gate policy and timeout independently, with
parent mode/style/value restoration and disarm even on error. No live writes,
download or gateway restart were performed for this build. The last confirmed
controller is press64; physical retention and S9 remain owed. See
[build evidence](../AllenBradley/Evidence/AB_PHASE6_SHELVING_BUILD_2026-10-03.md).

**Item 5 memory correction prepared (press66, 2026-10-03).** Owner Studio
Verify of press65 reported one **Out of memory in the controller** error in
`FRK_PressProgram - FRK_PressHmiMailbox`. Expanded native character comparisons
are replaced by bounded lookups into the existing controller manifest and one
shared request routine. Permission is read from the same Rationalization row;
native lengths, indices and counts are guarded. Mailbox statement terminators
fall from 2,727 to 1,529; total generated ST falls from 5,778 to 4,651. The
request helper adds 71 terminators. Tag/type storage, the four-user ceiling, public
contract and manifest hash remain unchanged from press65. AOIs, chains, I/O
and tasks compare equal. Both press66 and the template reproduce byte-for-byte.
The generator now reports code/data growth for each remaining implementation,
against the last owner-verified artifact. These are trends, not compiled memory.
All 1,479 AB tests, 33 consistency tests and 12 in-memory mutations pass;
consistency reports zero errors/warnings. Studio Verify/fit and hardware
verification remain pending because the SDK refuses **No valid license**.
Press64 remains the last confirmed loaded build; no live operation or gateway
restart was performed. See
[memory correction evidence](../AllenBradley/Evidence/AB_PHASE6_SHELVING_MEMORY_FIX_2026-10-03.md).

**Item 5 link-memory correction prepared (press67, 2026-10-03).** The owner's
press66 output progressed through compilation and linking, then reported
**Out of memory in the controller**, cancelled the download and ended with one
error. Verify alone therefore does not establish fit. Press64 is the last
confirmed successful download; current controller state after cancellation
is unverified, and no live operation was performed for this correction.

Press67 shares configuration audit and Start release routines at their original
call points, preserving per-request policy rechecks and all audit metadata.
Fields/Localization allocations now follow each declaration plus 64 rows of
growth reserve, rounded to 64-row blocks and capped at the existing 768-row
ceilings. Press67's 640/640 allocations save 12,288 declared bytes from press66;
235 ST statement terminators and 18,455 source bytes are also removed. Total
data/source trends are below successful press64, but they do not measure native
compiled memory. Four users remain the ceiling; alarm/history capacities,
public record layouts, native guards and writable tag names remain unchanged.

The press's 68,472-byte major-4 manifest has Fields 565/640 and Localization
570/640; content/hash and revision stay `832DD0D0F260872B` / 8596944. The template
uses 58,232 bytes, Fields 379/448 and Localization 481/576. Both artifacts
reproduce byte-for-byte against final source. All 1,484 AB tests, 33 consistency
tests and 21 in-memory mutations pass; consistency reports zero errors/warnings.
The SDK still refuses **No valid license** before opening. Owner Verify and a
completed link/download, gateway restart, full manifest readback and guarded
shelving/regression verification remain pending. Future growth comparisons use
the last successfully downloaded artifact. Physical retention and S9 remain
owed. See [link memory correction evidence](../AllenBradley/Evidence/AB_PHASE6_SHELVING_LINK_MEMORY_FIX_2026-10-03.md).

**Item 5 shelving on hardware (press67, 2026-10-03).** After the read-only
readiness snapshot, the owner explicitly authorized the shelving/regression
fixtures with “go ahead.” Shelving passes **15/15** on exact serial 7036B510.
Shelf/unshelf change annunciation; native claimed-admin requests remain refused
under the operator's actual role, foreign identity and zero duration refuse,
and a three-second shelf expires after logout in 3.833 seconds with history.
The registry-unshelvable cylinder defect refuses shelving and still blocks Start.
Exact cap, duplicate identity, slot reuse and shelved blocking-event behavior
retain the additional offline proof; an eight-hour hardware wait is not claimed.

All regressions pass: data 18/18, access 16/16, capture 10/10, sets 17/17,
parity 25/25 and Phases 1–5 7/7 · 6/6 · 8/8 · 11/11 · 25/25. S3 passes
6/6 before and after; maximum scan is **5,279 µs** against 10,000 µs,
with zero overlaps and fault bits. The full **68,472-byte** major-4 manifest
is coherent and equal; the final repeat takes 154.664 ms, with Fields
565/640 and Localization 570/640. Original configuration, policy, timeout,
mode/style, ten fixture inputs and level-4 admin session are restored; no active
shelf remains and the gateway is ready. Every primitive fixture write has an
immediate exact target check. No agent download, gateway restart, provisioning,
clock set or fault/timing-counter clear was performed during this verification.

All **1,486 AB tests** and **33 consistency tests** pass, with zero consistency
errors/warnings. PLC/HMI/gateway source is unchanged from the link-memory
correction; its 21 killed mutations remain offline evidence. The first Phase 5
run failed four timing rows because guarded argument staging missed a brief
motion and was counted before START. The corrected fixture uses a declared
recoverable motion hold, restores it in finally, and measures acknowledgement
boundaries with the same 250 ms tolerance; the retry passes all 25 rows. Its
two slow-client/cleanup tests and two in-memory mutants pass. Press67 is now the
verified loaded memory baseline; its reduced declared/source counts are trends,
not a native free-memory measurement. The template remains offline-tested.
**Item 6, the write-enabled S9 contract suite, is next.** Physical retention
also remains owed. See [hardware evidence](../AllenBradley/Evidence/AB_PHASE6_SHELVING_ON_HARDWARE_2026-10-03.md).

**Item 6 S9 prepared offline (press68, 2026-10-03).** The generated native
mailbox appends an 89-DINT frame with 312 aggregate ASCII argument bytes,
derived at the pinned serializer's conservative 500-byte connection size. One
payload write precedes Sequence; CPS privately samples it, validates schema,
matching sequence and bounds, then wipes both copies before acknowledgement.
The shared TC3 public paths/ordinals stay; large ConfigSet payloads stay staged.
The native profile participates in ContentHash and BindingVersion advances to 2,
refusing an incompatible downloaded build. Part III's earlier nonzero/skip-zero
wording is aligned with TC3's full uint32 range and signed native bit storage.

Both gateways reserve sequences before I/O and refuse duplicates/backward
sequences; a fresh explicit request may skip burned attempts. The HMI seeds from
the committed input across wrap, and explicit metadata without quality is Bad.
The AB reader caches only coherent manifests, applies shared viewer tier
intersections to bounded native groups, and forces targeted reads. Native record
granularity still keeps any group with a fast leaf cyclic; the alarm ring remains
cyclic because it also supplies active/global diagnostics. Missing reads never
revive cached Good values, and gateway acquisition timestamps are not represented
as controller UTC.

Press68 reproduces byte-for-byte: SHA-256
`E2C20374F8FC7364672E425EBC3E55CC5F6D9F81ED4894BB32366E737BA586F7`,
manifest `7A9B9A8B59EEFD16` / 8035226, still 68,472 bytes. Four-user ceiling,
private registrations, access defaults, AOIs, tasks and module configuration
remain. Growth over loaded press67 is +1,088 declared bytes, +4,119 source bytes
and +63 statement terminators. These do not measure compiled/free memory.
Studio Verify and a completed link/download are required; the SDK refuses
"No valid license" before opening. The template is reproduced offline as well.

The same repository contract suite runs on TC3-style fixture paths and an actual
AB production adapter document; its command client is a fixture, not a TC3 rig.
Separate Python tests execute the generated native decoder and production AB
gateway. The new native fixture tests the five replay boundaries, premature and
reversed staging, and restores a known session and timeout. A read-only vector
prepares measurement of current-station native cost and six shared viewers.
No controller I/O, download, gateway restart or client deployment was performed.
**The write-enabled S9 claim, current-station freshness/poll budgets, native fit
and physical retention remain owed.** See [offline evidence](../AllenBradley/Evidence/AB_PHASE6_S9_OFFLINE_2026-10-03.md).

**S9 read-only preflight (press68, 2026-10-03): PASS within its read-only scope.**
The complete native manifest, stopped fixture readiness and original-session
restorability pass. The running gateway passes 13 discovery, quality, acquisition
timestamp and reconnect checks; S3 passes 6/6. Current-code steady reads have a
192.702 ms median and fresh mailbox acknowledgement reads a 16.884 ms median.
No controller changes or additional PLC memory occur. The owner reports minimal
mode-change improvement and defers further latency work. The native write
fixture is prepared but awaits current completed-download confirmation and an
idle HMI. S9's write-enabled claim, deployment freshness/poll declarations and
physical retention stay open. See the
[read-only preflight evidence](../AllenBradley/Evidence/AB_PHASE6_S9_READ_ONLY_PREFLIGHT_2026-10-03.md).

**S9 native mailbox on hardware (press68, 2026-10-03).** The owner's “that
was already downloaded” confirms the completed download and authorizes its
Phase 6 verification fixtures. The native vector passes 17/17 on serial
7036B510: five replay boundaries, signed-DINT/uint32 wrap, partial/premature
commit, reversed segments and frame wiping. Shelving 15/15, data classes 18/18,
access 16/16, capture 10/10, sets 17/17, parity 25/25 and Phases 1–5
7/7 · 6/6 · 8/8 · 11/11 · 25/25 pass. S3 is 6/6 before and after, with no
overlaps/fault bits; independent readback confirms original configuration,
policy, timeout, AUTO/CONTINUOUS, anonymous session and ten cleared inputs.
There is no pending request or active shelf, and the public frame is wiped.

The first Phase 5 invocation stops on a failed frame Write before commit. A
fresh run is 24/25: a downtime row uses a fixed sleep rather than actual native
acquisition time. The fixture correction brackets native samples, reuses the
owning projection and retains the 250 ms timing allowance. The corrected retry
is 25/25; focused tests and both in-memory mutants pass. All failed outputs and
guarded corrective restoration are preserved. Runtime source remains unchanged,
and press68 regenerates byte-identically. The shared repository contract is
61/61. Press68 becomes the successful downloaded memory baseline; this work
adds zero PLC memory and needs no new import/download. Four users remain the
ceiling. **Full write-enabled S9 stays open** for current-deployment freshness/
poll declarations and expiry enforcement during stalled reads. Physical
retention is separately owed; owner-deferred mode-latency tuning is not resumed.
See [native hardware evidence](../AllenBradley/Evidence/AB_PHASE6_S9_NATIVE_MAILBOX_2026-10-03.md).


**S9 freshness source and read-only budget (press68, 2026-10-03).** The application
now owns 500 ms polls, 250 ms cache, 1,000 ms slow heartbeat, 2,000 ms Good /
3,000 ms expiry and a 4,000-byte read connection. Gateway and generic HMI expire
cached samples during blocked RPCs; partial Ack reads cannot renew the complete
station, and delivery checks freshness again. The shared TC3/AB suite passes
71/71, AB discovery 1,535 tests, HMI 459 tests (7 expected skips), analyzer clean,
five semantic mutants killed. Read-only native steady/six-viewer maxima are
199.521/224.933 ms and S3 remains 6/6. Press68 and template regenerate identically;
there is zero PLC growth and no new download. The release Web client is served
and authenticated HTTPS hash-verified. **Full S9 remains open for live gateway
activation and verification after the owner's restart.** Physical retention
remains separate. See [freshness evidence](../AllenBradley/Evidence/AB_PHASE6_S9_FRESHNESS_2026-10-03.md) and [final HMI follow-up](../AllenBradley/Evidence/AB_PHASE6_S9_FRESHNESS_CLEANUP_2026-10-03.md).

**S9 detail-read loop correction (press68, 2026-10-03).** Freshness was observed
active in the running gateway. The new HMI waited for all 2,621 detail leaves
before accepting the current full sample: six native targeted RPCs took
1.95–2.42 s, exceeding the 2 s Good limit once sample age was included. Complete
samples now publish independently of bounded background detail reads. Each
batch ages separately; closing/changing its scope or losing the station discards
pending data. The previous client fails the new regression; the correction
passes HMI 463 tests (7 expected skips), shared contract 75/75, analyzer, release
build, and compiled-JavaScript quality replay of the actual gateway document.
Full AB remains 1,535 tests. Freshness budgets and the downloaded press68 are
unchanged. The corrected Web client is HTTPS hash-verified. The gateway stopped
before the corrected live repository probe, so **full S9 remains open** for that
verification after the owner's restart. See
[loop correction](../AllenBradley/Evidence/AB_PHASE6_S9_FRESHNESS_LOOP_FIX_2026-10-03.md).

**S9 live acceptance (press68, 2026-10-03).** The owner restarted the gateway,
hard-refreshed Chrome and confirms the reconnect loop is gone. Exact-serial
manifest readback remains coherent/equal at 68,472 bytes. The read-only
production-repository probe passes 60 seconds with 121 complete updates and 224
detail batches, no STALE/DOWN transition or empty forest, and maximum update gap
790 ms. Three fresh sessions, HTTPS client hash and S3 6/6 pass. The probe omits
only ConfigRev-triggered mailbox hydration, so it performs no controller write.
The previous probe's incorrect Status/ConfigRev-only filter was caught by its
write blocker; no attempted QUERY_CONFIG reached the controller. Failed output
is preserved, and the corrected probe has zero blocked write attempts.

This closes write-enabled **S9 on the named press68 deployment**, combining the
prior native vector 17/17 and eleven regressions/restoration with shared contract
75/75, source expiry/quality/command tests and corrected live acceptance. It adds
zero PLC memory and needs no download. It does not close physical retention,
the separate historical S1 clock probe, TC3 native segmented transport or D6,
and does not grant a writable claim to another station or mailbox profile.
See [live acceptance](../AllenBradley/Evidence/AB_PHASE6_S9_LIVE_ACCEPTANCE_2026-10-03.md).

**Configuration regressions repaired in software (2026-10-04).** Opening
Parameter sets could block complete snapshots behind its native command on the
same AB connection. Bounded request multiplexing preserves current reads,
mailbox serialization, queued-command cancellation and active native draining.
The model selector disappeared because the generic HMI excluded published
metadata before receiving exact replacements from the manifest. Exclusion now
depends on hydrated paths and re-runs when that set changes; unconsumed sequence
definitions stay excluded. The prior code fails both regression fixtures.
Full AB 1,541, HMI 478 (7 expected skips), shared TC3/AB 79 and root 33 tests pass;
analyzer and release build pass. HTTPS serves the corrected Web bytes. Native
dialog/model acceptance and D6 readback remain pending the owner's one gateway
restart. No PLC memory growth or download; four users and freshness limits are
unchanged. See the
[configuration evidence](../AllenBradley/Evidence/AB_PHASE6_CONFIGURATION_REGRESSIONS_2026-10-04.md).


**Gateway activation and D6 live readback (press68, 2026-10-04).** The owner
restarted the gateway, superseding the pending activation above. A read-only
same-socket probe now receives inert replies in 1.02–1.95 ms while native
snapshots continue at 208.77–211.00 ms; before restarting, those replies waited
204.13–207.59 ms behind the snapshots. The concurrent handler is active. All
three health routes return HTTP 200, PLC ready, and the same credential-free
`writeAccess` block: enabled, roots [Press], allRootMailboxes false. This closes
D6's AB live readback; TC3 remains offline-tested. Full AB 1,541, focused
concurrency 4 and root 33 tests pass; consistency has 0 errors / 0 warnings.
Parameter sets acceptance in Chrome awaits the owner's result. No controller
writes, gateway restart by the agent, PLC memory growth or download occurred.
Configuration/set and other account physical retention, historical S1 clock and
TC3 native segmented transport remain separate work. See the
[activation record](../AllenBradley/Evidence/AB_PHASE6_GATEWAY_ACTIVATION_2026-10-04.md).


**Parameter sets browser acceptance (2026-10-04).** The owner answers “Yes — it
stays open” after the requested Chrome hard refresh and at least ten-second
dialog check. This closes the pending browser acceptance above. The handler
activation and D6 AB readback retain their separate verified evidence. Full AB
1,541 and root 33 tests pass; consistency has 0 errors / 0 warnings. A read-only
exact-serial preflight confirms the press stopped in AUTO, without Error or
persistence Pending/Failed/RestoreLost. Configuration/set physical retention is
next: a plan preserves current values, changes only station.number 1 → 2, and
restores through one temporary named Station set after an owner-performed power
cycle. That plan awaits current authorization; no controller writes or cycle
have occurred. No memory growth or download. See the
[browser acceptance](../AllenBradley/Evidence/AB_PHASE6_CONFIGURATION_OWNER_ACCEPTANCE_2026-10-04.md)
and [retention plan](../AllenBradley/AB_PHASE6_RETENTION_CHECK_PLAN_2026-10-04.md).


**Owner parameter-retention observation and model workflow (2026-10-04).** The
owner reports editing minimum air pressure 450 → 451 about nine hours earlier,
power-cycling the PLC and confirming 451 persists. Prior exact-serial readback
also shows 451. This adds owner-confirmed retention for that parameter; the
proposed Station number test was not authorized/executed and is redundant for
another representative parameter observation. Saved-set survival, other values/
accounts and download/upgrade retention remain separate. Loaded press68 has
no runtime Add model action: catalog entries come from its declaration, whereas
the HMI edits existing models. Model sets name snapshots; save/export works, and
model-set load is deliberately refused until atomic recipe/changeover integration
in both AB and TC3. Full AB 1,541 and root 33 tests pass; consistency has 0 errors /
0 warnings. No implementation/PLC memory change, I/O, download or agent cycle
occurred in this turn. See the
[owner record](../AllenBradley/Evidence/AB_PHASE6_OWNER_AIR_PRESSURE_RETENTION_2026-10-04.md)
and [model workflow](../Guides/AB_NEW_PROJECT_GUIDE.md#adding-a-model-to-the-current-ab-application).


**Runtime model catalog and current file export (2026-10-04): offline PASS,
press69 owner deployment pending.** The generic HMI and AB press now support
inactive model cloning, creation from complete saved Model sets and direct
current-value `.jsonl` export. Activation still uses Changeover. The bounded
native catalog has eight total slots and immutable appended indices; four users
remain. The press-demo air Start permit is scoped to AUTO/HOME, while cylinder
pressure permits remain in every mode. Press69 adds 2,700 declared bytes and
5,085 ST source bytes over successfully loaded press68. Native fit, the new
write-enabled profile, browser operation and retained created models are not
claimed before owner deployment and live acceptance. TC3 reserves kinds 37/38,
without publishing either optional runtime capability; native compiler checks
stopped at host solution-configuration/COM failures before compilation. See the
[dated implementation record](../AllenBradley/Evidence/AB_PHASE6_MODEL_CATALOG_EXPORT_2026-10-04.md).

## Press70 native acceptance - 2026-10-04

Owner-confirmed full download establishes press70 as the memory baseline. Eleven
restored native suites pass 159 rows, S3 passes 6/6, M-101 current export and the
production HMI repository read pass. The Phase 4 fixture now derives mode-scoped
air-entry reports from the declaration; its first legacy failure is preserved.
Chrome/model physical retention and the new profile's full S9 closure remain
separate. See [the append-only native record](../AllenBradley/Evidence/AB_PHASE6_PRESS70_NATIVE_ACCEPTANCE_2026-10-04.md).
Expanded catalog boot-image tests preserve all four model banks without layout
growth; fresh capture is required before the next feature artifact. Next: line
data with versioned weekday/duration shifts. No remaining port gap is closed by
this acceptance alone.
