# Generic control-module expansion — audit plan (TC3), 2026-11-03

**Status:** plan for an independent audit of everything branch `feature/generic-cm-phase0`
adds over `main` (merge base `a1163c7c7`): Phase 0 through L8 of
[the remaining-library plan](TC3_GENERIC_CM_LIBRARY_PLAN_2026-10-29.md) and the robot
completion that followed it. It is written to be executed by a session that did not write the
code. Nothing here is normative; Part I and the annexes stay the authority, and every check
below names the clause it judges against.

Paths are relative to the repository root; `TC3/` abbreviates `FraktalCore/PLC/TwinCAT/`.

---

## 0. Ground rules for the auditor

1. **Read-only first.** Phases A–I record findings; they change nothing. A finding that needs a
   code change becomes a follow-up item with its own gates and evidence, never an edit made
   in passing while auditing.
2. **Every finding is reproducible.** It cites `path:line` at a named commit, states the rule it
   breaks (spec clause, objective, AGENTS rule or plan item), and gives the observation that
   proves it — a command and its output, a test that fails, or a scenario traced through the
   code. "Looks wrong" is not a finding; it is a question for §11.
3. **Severity** (one per finding):

   | Level | Meaning | Examples |
   |---|---|---|
   | S1 | Fail-open or safety-adjacent: an output, motion or power can occur that the contract says cannot | a refused command still moves; power re-enabled after a safety loss; a withdrawn output re-energised |
   | S2 | Wrong behaviour under a reachable condition | a legal command faults; a fault carries the wrong reason or none; a timeout never fires |
   | S3 | Contract or specification drift | code and annex disagree; a published member nobody reads; a reason without rationalization |
   | S4 | Engineering-discipline defect (§1.1 O9) | duplicated logic, a second source of truth, a test that proves the wrong thing |
   | S5 | Documentation or evidence defect | a count, version or claim in a record that the artifacts do not support |

4. **Vendor-neutral.** Tracked files never name reference projects or vendors' packages;
   findings describe behaviour, not where an idea came from.
5. **Runtime rules.** TcUnit runs only on the designated isolated runtime (UmRT_Default,
   `192.168.1.6.1.1:851`), Autostart off, `-StartBootProjectWithAds`. No other controller is
   touched. The runtime licence is a trial that the owner renews interactively; if it has
   lapsed, stop and ask — never automate the renewal.
6. **Known flake.** `FraktalCore/HMI/test/opcua_freshness_test.dart` has wall-clock rows that
   fail in full runs under host load, on the baseline too. Protocol: re-run the file alone,
   run the full suite on the baseline, re-run the full suite with XAE idle; record every run.

---

## 1. Scope and inputs

| Commit | Package | Library step | Evidence | Notes |
|---|---|---|---|---|
| `2624e4d5f` | Phase 0: digital-input debounce, channel unit codes | Core 0.26.0.0 / Modules 0.12.0.0 | `2026-10-26_TC3_GenericCM_Phase0.md` | §164–§165 |
| `551984af7` | Phase 0 runtime gates | — | same | |
| `850b5cf4e` | Phase 1: `FB_CylinderCM` valve timing, `FB_ValveDrive` | Modules 0.13.0.0 | `2026-10-26_TC3_GenericCM_Phase1.md` | §166 |
| `27f52f1df` | TIA regeneration; HMI reads unit code NONE as no code | — | — | |
| `289630901` | NOK-part limit (`SetNokPolicy`, reason 2028) | Core 0.26.1.0 | `2026-10-27_TC3_GenericCM_NokPolicy.md` | §167 |
| `79701b157` | Remaining-work plan and handover | — | — | |
| `b2e6164c5` | L1 `FB_AnalogInputCM` | Modules 0.13.1.0 / Core 0.26.2.0 | `2026-10-30_TC3_GenericCM_AnalogInput.md` | §168 |
| `031c0ca83` | L2 `FB_AnalogOutputCM` | Modules 0.13.2.0 / Core 0.26.3.0 | `2026-10-30_TC3_GenericCM_AnalogOutput.md` | §169 |
| `229322079` | L3 axis depth | Modules 0.14.0.0 / Core 0.26.4.0 | `2026-11-02_TC3_GenericCM_AxisDepth.md` | §170 |
| `0bb7eff28` | L4 configurable-cylinder valve timing | Modules 0.15.0.0 | `2026-11-02_TC3_GenericCM_ConfigurableCylinderTiming.md` | §171 |
| `1e3815559` | L5 `FB_CurveMonitor` | Modules 0.15.1.0 / Core 0.26.5.0 | `2026-11-02_TC3_GenericCM_CurveMonitor.md` | §172 |
| `ab6081428` | L6 curve record and HMI Curve tab | Modules 0.15.2.0 + HMI | `2026-11-02_TC3_GenericCM_CurveRecord.md` | §173 |
| `bf79fdd78` | L8 paper audits | — | `Reports/TC3_CODE_READER_PARITY_AUDIT_2026-11-02.md`, `Reports/TC3_ROBOT_USER_CHANNEL_AUDIT_2026-11-02.md` | |
| (next) | Robot completion | Modules 0.16.0.0 / Core 0.26.6.0 | `2026-11-03_TC3_RobotCompletion.md` | §174 |

Also in scope: every cross-binding artifact these commits touched (TIA generated packages,
AB census, Siemens port plan, `check_consistency.py`, `plc_lint.py`), the HMI changes (reason
catalog, Shifts card, Curve tab), and the documents (`AGENTS.md`, `TC3/README.md`,
`TWINCAT_XAE_WORKFLOW.md`, Part I §8.8 registry, Annexes G and I, `HMI_CONTRACT.md`).

Out of scope: Press bench behaviour beyond version pins (plan decision D1), L7 energy
metering (deferred, Q2), the Allen-Bradley and Siemens bindings' own behaviour (only their
census rows and hash regeneration are in scope).

Effort estimate: Phase A 0.5 d · B 0.5 d (plus runtime) · C 1 d · D 3 d · E 1 d · F 1.5 d ·
G 0.5 d · H 1 d · I 0.5 d · report 0.5 d — about 10 working days.

---

## 2. Phase A — evidence integrity

Goal: every evidence record says only what its artifacts prove.

- **A1 Receipts.** For each `Specification/Evidence/*GenericCM*.json` and the robot receipt:
  recompute SHA-256 of every file in `files` and compare. Then for every entry in
  `sourceSha256`/`sources`, compare with `git show <commit>:<path> | sha256sum` at the commit
  that added the receipt. A mismatch means the evidence was not taken on the committed source
  (S5, or S2 if behaviour differs).
- **A2 Counts.** For each record, parse its JUnit files and compare tests/suites/failures with
  the record's prose, with `ci.yml` (`--expected-tests/--expected-suites`) and with the
  `TWINCAT_XAE_WORKFLOW.md` inventory row **at that commit**. Recount `TEST('` occurrences per
  suite at that commit and check they sum to the claim.
- **A3 Raw logs.** Confirm each raw log names `PRG_TcUnitRunner`/`PRG_PressTestRunner`, the
  expected NetId and port, and contains no FAIL row. Confirm the six ObjectCheck logs each end in
  `Compile complete -- 0 errors, 0 warnings` (the benign "Unknown TMC file version" XAE row is
  allowed and should be the only Error List row).
- **A4 Incident honesty.** Each record that ran more than once must list the failed runs and
  include their logs (L3 first aggregate stalled at suite 33; L5 first install refused `ANY`;
  L6 read-surface failure and freshness flakes). Search the artifact folders named in the
  records for runs the records do not mention.
- **A5 "Not executed" lists.** Check each unproven claim is stated: no NC licence (L3 motion
  paths), no station consumer (D2 waiver), no real robot or emulator (robot), no live
  PLC-to-HMI read of a real `OutImm.Curve` (L6).

## 3. Phase B — gate re-run on the branch head

Run on a fresh worktree of the branch head, in this order, archiving every log:

1. `python TC3/tools/plc_lint.py` and `--profile 4024`.
2. `python -m unittest discover -s TC3/tools -t TC3/tools`.
3. `python tools/check_consistency.py --strict` and `python -m unittest tools.test_check_consistency
   tools.test_check_ab_spec tools.test_check_ab_contracts tools.test_check_tia_contracts`.
4. `python tools/check_ab_spec.py`, `python tools/check_ab_contracts.py`,
   `python tools/check_tia_contracts.py` (plain and `--generated FraktalCore/PLC/Siemens/Examples/PressDemo/generated`).
5. Siemens: `tia_lint.py`; `fraktal_tia_generate.py --verify FraktalCore/PLC/Siemens/Tests/Generator/generated`;
   `fraktal_tia_examples.py --verify FraktalCore/PLC/Siemens/Examples/PressDemo/generated`;
   `fraktal_tia_io_bridge.py --verify FraktalCore/PLC/Siemens/Examples/PressIoBridge/generated/Physical`;
   `python -m unittest discover -s FraktalCore/PLC/Siemens/tools -t FraktalCore/PLC/Siemens/tools`.
6. `dart run tool/generate_reason_catalog.dart --check` (from `FraktalCore/HMI`).
7. Library install (32-bit PowerShell, `TcXaeShell.DTE.15.0`, `TwinCAT RT (x86)`), then
   `TC3/tools/Invoke-TwinCatBuild.ps1` (six solutions).
8. Aggregate and Press TcUnit gates (expected counts from `ci.yml`), each validated with
   `tcunit_to_junit.py`.
9. HMI: `flutter analyze --no-pub`, `flutter test --no-pub` (flake protocol §0.6); confirm
   `pubspec.lock` unchanged.

Any red gate is a finding of at least S2 unless traced to the environment (licence, host
load), in which case record the trace.

## 4. Phase C — objectives audit (Part I §1.1)

For each package, answer each question with evidence. A "no" is a finding.

| Objective | Questions |
|---|---|
| O1 trim the project | Does any behaviour a station must remember sit in project code that the library could own? Does a library type force a station to write wiring twice (e.g. robot user signals, NOK policy wiring)? |
| O3/O4 surface proportional to use | List every new published member (OutImm/OutCmd/StationCfg/ParCfg). For each: who reads it (PLC, HMI, MES, test)? An unread member is S3. Check the curve record is on demand and the robot `UserSignals` (8 × 5 leaves per robot) cost is acceptable on the live tier. |
| O6 simulation | Can every new type run against simulation unchanged (sim HAL, sim connector)? Are the injected faults the ones the reasons need? |
| O8 portable seam | Do new interfaces (`I_RobotConnector` members) name a platform API? Is the vendor protocol confined to the connector? |
| O9 one source | Search for duplicated logic: `FB_CylinderCM` vs `FB_ConfigurableCylinderCM` (valve timing must go through `FB_ValveDrive` in both); `FB_AxisCM` vs `FB_RobotCM` jog (same shape, documented differences only); repeated literals that should be `PL_` constants (e.g. HMI mapper clamps 256/32/4/2 vs `PL_Curve`). |
| O10 fail closed | Every new refusal: does it refuse before acting, with a reason? Every default: is it the safe one (robot `DefaultMode`, safety permit default TRUE — is that acceptable?, jog without opt-out)? Every timeout: bounded and tested? |

## 5. Phase D — package code review

Read each diff (`git show <commit>` / `git diff main..HEAD -- <path>`) against the checklist.
Each item is a question; record the answer and the evidence.

### D0 Phase 0 — debounce and unit codes
- `FB_DigitalInputCM` debounce at the source: a bad-quality input publishes invalid, never a
  stale good value; `ParCfg` v2 records stored before the upgrade are refused.
- `ST_IoChannel.UnitCode`: manifest-only; legacy `Unit` text derived from it; HMI treats 0
  (NONE) as "no code" — confirm the `27f52f1df` HMI fix covers every reader.
- `check_consistency` read-surface fix (AB_ABSENT topology): confirm the rule judges topology
  entries against topology reads and still catches a real omission (write a counterexample).

### D1 Phase 1 — `FB_CylinderCM` valve timing
- `FB_ValveDrive`: pulsing only from no end position; `MinTimeElapsed` counts from the first
  energised scan; `M_Coil(Steady := TRUE)` resets the period.
- Withdrawn outputs: no pulse re-energises a withdrawn coil; `RestoreOutputs` only.
- Timeout without `ResetOnTimeout` leaves the coil at its last pulse level (documented in §171
  for both types). Decide whether that is acceptable or an S2.

### D2 NOK-part limit
- `SetNokPolicy` wiring in the Press `MAIN` (owner decision Q1: kept). Reason 2028 rationalized,
  registry row, HMI catalog. Counter reset semantics on shift/mode change.

### D3 L1 analog input / L2 analog output
- L1: scaling divide-by-zero guarded by valid `ParCfg` only; two-point adjustment plausibility;
  tare; stability band and `MEASURE` timeout; editable values' bounds.
- L2: `SafeValue` behind every state nobody stands behind (before first SET, interlock, withdraw,
  abort); no self-resume after a lost interlock; band and safe value validated at prepare.

### D4 L3 axis depth (hotspot)
- `_M_MoveRel`: `_relDistance` latched once at step 10. **Unproven at runtime** (no NC licence):
  trace by hand that a move from 0 to 80 under `SoftMax` 100 never re-judges the target; check
  `STEP_POS/NEG` use `ManualStep` and refuse 0.
- `AND_THEN`/`OR_ELSE` guards around `_positionDeclared[...]`: confirm every array index in
  `FB_AxisCM` is guarded the same way (search all `[` indexing with a variable).
- Second retained image `ST_AxisTeachCfg`: restore-loss slot semantics (one slot per module);
  first boot after upgrade silent.
- `SetOverride` acts on `MC_Power.Override`, set-and-hold, no freshness fallback — is that the
  right policy when the owner stops calling?
- L3 files use "S" in place of "§" in comments (inherited from an earlier encoding problem);
  decide whether to normalise (S5).

### D5 L4 configurable cylinder
- Pulsing refused unless both positions are sensed (stricter than the plan): confirm the
  reasoning in §171 and that a sensorless cylinder cannot reach a pulsed move.
- `_recipePrepared := FALSE` at the start of `PrepareRecipe`: confirm `FB_CylinderCM` has the
  same guarantee (O9 parity) and every other CM with staged recipes does too (search all
  `PrepareRecipe` implementations for the pattern).
- Interlock loss still faults (no HELD path) — conformant with §6.1 for this type?

### D6 L5 curve monitor (hotspot)
- Entry/exit edge resolution: tie-breaking at exact corners; a segment that enters and exits
  between two samples (sparse sampling) — documented as a miss; is that acceptable for the
  intended sample rates?
- Envelope cursor with non-monotonic X (curve reverses): the bounded FOR loop moves the cursor
  both ways — test with a zig-zag curve by hand.
- `M_Finish` precedence incomplete > window > envelope; `DescriptionKey` added beyond the plan.
- `M_Validate` NaN behaviour: a NaN bound makes comparisons false — confirm it is refused, not
  accepted.
- Owner path not exercised (no owner type exists): is the "owner raises" contract testable as is?

### D7 L6 curve record and HMI (hotspot)
- `M_Record` refused while active; rows past `SampleCount` cleared; invalid spec recorded with
  an empty spec.
- HMI tiers: `Curve` on demand, `SampleCount` live via `liveLeaves`. `liveLeaves` matches the
  LAST segment name anywhere: search the whole published contract (TC3, AB projection, TIA) for
  any other leaf named `SampleCount` that would be promoted to live by accident.
- Mapper: reads use the binding idiom so the read-surface gate resolves them; clamps duplicate
  `PL_Curve` bounds (O9 question).
- Curve tab: geometry fractions, palette contrast proven in every theme; does the tab ever
  issue a write? (must not).
- Gateway/Web path: does the gateway use the same `OpcUaFieldTier`, so the on-demand rule holds
  for the Web HMI too?

### D8 robot completion (hotspot)
- **Mode request:** default requested at link-up and on loss of report. Can the default request
  occur while a command runs (loss of report mid-move) and, if refused, fault that command?
  Is that the intended behaviour? Is `DefaultMode := AUTO_REMOTE` (allowed for auto-only cells)
  consistent with "most restrictive the cell supports"?
- **LastResult contract (I.3):** every refusal in both connectors leaves a reason; every accept
  clears it; the user channel never touches it. Search both connectors for `:= FALSE` returns
  without a reason.
- **TCP connector queue:** depth one; `Abort` empties it first; on link loss and close it is
  cleared; the heartbeat cannot starve a queued command. Construct the sequences: speed+move;
  STA pending + move; move pending + abort; ERR reply while a request is queued.
- **Safety alias:** stop first, then power off on the falling edge and every 500 ms while power is
  reported; no re-enable path except `POWER_ON`; the default TRUE when no alias is supplied —
  is that acceptable for a robot (compare §9.8 and the axis)?
- **Held jog:** freshness timeout, enabling device always required, `NOT Busy`, interlocks and
  safety alias; started once, stopped with `Abort`. What does the TCP server do with a `JOG`
  that is never stopped if the PLC crashes? (Server-side watchdog is outside the PLC — record it.)
- **Abort:** `OnAbort` sends `Abort`; confirm the base calls it for every abort path, including
  abort in ERROR (`OnAbortInError`).
- **User channel:** kind checks (flag 0/1, integer integral and in range); direction; declared
  once; not writable from the HMI; values re-sent each poll after reconnect.
- **Path progress:** `PathIndex` semantics for `(-1,-1)`, for a sub-range, after a hold, after a
  protective stop. The simulation's ten-point list is synthetic — is that stated wherever it
  matters?
- **Wire format:** the appended STA fields are positional; a server sending fewer user inputs
  is fine, a server inserting a field before them is not — is the protocol versioned anywhere?
- **Annex I.15 route preview** ("the connector shall publish the resolved point sequence"):
  neither connector does. Confirm and record as S3 against the annex.

## 6. Phase E — specification conformance matrix

Fill one row per clause: implementing object(s) and line, proving test(s), verdict.

| Clause | Requirement | Where | Proof |
|---|---|---|---|
| Core §3.8 | migrate-or-fault; SchemaVersion first; stored old records refused | every ParCfg v2 (cylinder, configurable cylinder, axis, robot) | `Stored_v1_*` rows; robot has no provider — state it |
| Core §3.8 changeover | prepare fallible, commit infallible with no I/O | all PrepareRecipe/CommitRecipe added or changed | — |
| Core §3.8a/b | station data, retained images, restore-loss slot | axis teach image, analog output manual target | |
| Core §5.6 | validate before acting; defined ELSE on every CASE | every new `_M_Dispatch` and helper | |
| Core §6.1 | handshake, HELD vs fault, Execute-drop reset | analog output HELD, robot HELD | |
| Core §7.6.1 | manual catalog; held commands stop on silence | axis jog, robot jog | |
| Core §8.8/§8.9 | registry rows; rationalization both directions; operator text en/es | 10207–10209, 10701–10705, 10801–10802, 10901–10904, 10307, 10316, 2028 | `generate_reason_catalog --check` |
| Core §9 | safety read-only; no self-resume | robot safety alias, power group untouched | |
| Core §10.6 | robot facts (i)–(iii), HELD on path, payload should | `FB_RobotCM` | robot suites |
| Annex G | axis CM contract incl. positions, override | `FB_AxisCM` | |
| Annex I | I.2 registry, I.3 interface, I.4, I.4a, I.4b, I.5c, I.14, I.15 | robot types | |
| HMI_CONTRACT | curve record binding table | HMI mapper/tab | |
| Part II §2.2 | version step per change (minor/patch/revision) | every plcproj | Phase I |

## 7. Phase F — test adequacy (mutation probes)

On a scratch worktree, apply each mutation alone, compile, run the aggregate gate, and record
whether some row fails. A surviving mutation is a finding (S4, or S2 if it hides a real hazard).

| # | Mutation | Expected to fail |
|---|---|---|
| F1 | `FB_ValveDrive.M_Coil`: drop the `Steady` reset of the period | cylinder pulsing rows |
| F2 | `FB_ConfigurableCylinderCM.PrepareRecipe`: remove `_recipePrepared := FALSE` | `Invalid_timing_refused_CYL_CFG_INVALID` |
| F3 | `FB_AxisCM._M_MoveRel`: judge `ActPos + Distance` every scan again | none (unprovable without NC) — record as a known gap |
| F4 | `FB_AxisCM`: `AND_THEN` back to `AND` in index resolution | probably none — record; consider an out-of-range index row |
| F5 | `FB_CurveMonitor._M_EntryEdge`: pick the smallest parameter instead of the largest | entry-edge rows |
| F6 | `FB_CurveMonitor.M_Finish`: swap window and envelope precedence | precedence row |
| F7 | `FB_CurveMonitor.M_Record`: allow recording while active | record row |
| F8 | `FB_RobotCM`: delete `OnAbort` | `Aborting_a_command_stops_the_arm` |
| F9 | `FB_RobotCM`: compare `LastResult` with a start snapshot again | repeated-refusal row |
| F10 | TCP connector: remove the queue | `Speed_then_move_in_one_scan_both_reach_the_wire` |
| F11 | `FB_RobotCM._M_SafetyCyclic`: power off before the stop | none expected — evaluate whether a row should catch it |
| F12 | `FB_RobotCM._M_JogCyclic`: drop `_jogEnabled` from the gate | jog row (enabling device) |
| F13 | `FB_RobotCM.M_WriteUserSignal`: accept a fraction for an integer | user-signal row |
| F14 | HMI `OpcUaFieldTier`: drop `Curve` from on-demand | field-tier row |
| F15 | HMI `_curve`: read inputs from the wrong field index | mapper row |

## 8. Phase G — cross-binding

- TIA: each package that changed `PL_ModuleReasons` or Core DUTs regenerated the PressDemo
  package; verify the `12_CommandKernel.scl` severity/category rows match the rationalization
  for every new code (severity LOW=0, MED=1, HIGH=2; category PROCESS=0, SAFETY=1, SYSTEM=2).
- AB census rows (`AB_MISSING_FEATURES_HANDOVER_2026-10-06.md`) for every package; wording
  accurate about what AB has; no row claims AB parity it lacks.
- `check_consistency.AB_ABSENT` entries added (`OutImm/Curve`): justified and not hiding a read
  that AB could serve.
- Siemens port plan rows M1, M2, M6, M8, M9, M12–M14 accurate.

## 9. Phase H — HMI

- Reason catalog regenerated in each package; Spanish text present for every new key;
  `reason_catalog_test` count matches the generator (94 at the robot step).
- Shifts card overflow fix (`facet_cards.dart`): verify at narrow widths in every theme.
- Curve tab: open it against the simulator in the Windows build and in Chrome against a gateway
  (if available); confirm the demand set goes to `{Curve}` and back to empty when the tab closes.
- Robot: the held jog appears in the manual catalog as press-and-hold; confirm the HMI routes it
  through the held path with the enabling-device status (§7.6.1), never as a one-shot command.

## 10. Phase I — documentation and versioning

- Version steps per Part II §2.2: each minor (axis 0.14, configurable cylinder 0.15, robot 0.16)
  is a persistent-layout or contract change; each patch additive; Core patches carry only the
  regenerated catalog. Pins in every consumer plcproj agree.
- `AGENTS.md` "current Core/Modules" and "newest steps" sentences; `TC3/README.md` head; the
  workflow inventory row; `ci.yml` counts — all equal at every commit (check with
  `git show <commit>:<file>`).
- IMPLEMENTATION_NOTES §164–§174 contiguous; each states upgrade cost and tests; §170 records
  the four review defects; §174 the three robot defects.
- Annex I and Annex G agree with the shipped code (Phase E) — the I.14 suite description lists
  more rows than exist; decide whether that list is "target" text (as it says) or drift.

## 11. Questions the implementer flags (answer each)

1. Robot safety permit defaults TRUE when no alias is supplied (SetAreaSafe idiom). Should a
   robot instead fail closed until an alias is supplied once?
2. Robot user channel: 8 slots, all published live. Should it move to an on-demand container?
3. TCP connector: the status poll carries user outputs every period — is a write latency of one
   `StatusPeriod` acceptable for every intended signal?
4. `FB_CylinderCM`/`FB_ConfigurableCylinderCM`: timeout without `ResetOnTimeout` leaves a pulsed
   coil at its last level. Keep, or drive steady/withdraw?
5. L3: the override has no freshness fallback (a silent owner leaves the last value). Keep?
6. L6: is one live leaf per curve-publishing module acceptable on a station with many?

## 12. Robot improvement backlog (ideas reviewed 2026-11-03)

A commercial robot-integration package was reviewed for ideas. Disposition of each:

| # | Idea | Disposition | Owner / shape |
|---|---|---|---|
| R1 | Path progress after an abort, for a deliberate continue | **adopted** (§174) | `PathIndex` on connector and CM |
| R2 | Runtime capability discovery (which functions the connected controller supports; units and limits) | proposed | `ST_RobotCapabilities` from the connector, published read-only; the CM refuses unsupported commands before issuing; the HMI hides them |
| R3 | Brake test and safe reference run requested by the controller | proposed | connector facts (`BrakeTestDue`, `SafeRefDue`) published as state flags; commands `BRAKE_TEST`, `SAFE_REFERENCE`; maintenance event via the owning Unit |
| R4 | Fast-input position latch (record the pose when a robot input switches) | proposed, on first consumer | optional connector capability group; result in `OutCmd` |
| R5 | Refuse a never-taught point instead of driving to a zero pose | proposed | connector contract: `ROBOT_POINT_UNKNOWN` (10302, registered) |
| R6 | Tool/frame consistency check after link-up | proposed, depends on geometry held as Fraktal configuration | `ROBOT_TOOL_FRAME_CONFLICT` (10306, registered) |
| R7 | Declared manual moves (a few one-press moves to taught positions) | proposed | `M_DeclareManualMove(Slot, PointId, LabelKey)` into the manual catalog, release-gated, area-resolved |
| R8 | Controller identity (vendor, model, firmware) | proposed | read-only controller facts; NOT the static §3.10.1 nameplate, which is set at Setup |
| R9 | Teach of frames (3-point / current position), pallets and areas | proposed (Annex I.15 already specifies it) | bounded collection capabilities with capture |
| R10 | Route preview of generated moves | **required by Annex I.15, not built** | connector publishes the resolved point sequence for the pending move |
| R11 | Additional axes | proposed with R2 | capability count; data only |
| R12 | Maximum override lowered in manual by the application | already covered better | per-mode ceilings derived from the reported mode (I.4a(b)) — no project code |
| R13 | Continuous/streaming motion, TCP-relative moves, PLC-side kinematics | **not adopted** | puts coordinates into PLC code (I.1) |
| R14 | Run an opaque internal robot program | not adopted as such | `RUN_PATH` by ID covers the ID-addressed case |

## 13. Deliverables

1. `Specification/Reports/TC3_GENERIC_CM_AUDIT_REPORT_<date>.md`: summary, findings table
   (id, severity, package, `path:line`@commit, rule, observation, proposed fix, effort),
   conformance matrix (Phase E), mutation results (Phase F), answers to §11, and a go/no-go
   recommendation for merging the branch.
2. `Specification/Evidence/<date>_TC3_GenericCM_Audit.md` + SHA-256 receipt for every log the
   audit produced (gate re-runs, mutation runs).
3. A follow-up list ordered S1 → S5, each item sized and assigned to a package.

## 14. Handover prompt for the executing session

> You are auditing branch `feature/generic-cm-phase0` of the Fraktal repository against
> `Specification/Reports/TC3_GENERIC_CM_AUDIT_PLAN_2026-11-03.md`. Read `AGENTS.md`, the plan,
> the remaining-library plan and IMPLEMENTATION_NOTES §164–§174 first. Work phase by phase
> (A → I), read-only: record findings with severity, `path:line` at a commit, the rule broken
> and the reproducing observation; do not fix anything during the audit. Use only the isolated
> UmRT runtime `192.168.1.6.1.1:851` for TcUnit, Autostart off, `-StartBootProjectWithAds`; if
> the trial licence has lapsed, stop and ask the owner. Follow the HMI freshness-flake protocol
> in §0.6. Keep tracked files vendor-neutral. Deliver the report, the evidence record with its
> receipt and the ordered follow-up list (§13), commit them on a new branch, and push.
