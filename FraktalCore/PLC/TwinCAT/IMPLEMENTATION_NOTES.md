# Fraktal Core — Implementation Notes (Milestone 1, 2026-07-02)

*Scope: `Fraktal_Core` library + aggregate `Fraktal_Tests` gate + scaffold, implementing Core §2.2 (base classes), §3.2 (interfaces), §3.8/§3.15/§3.16 (provider/connector/carrier contracts), §6.1 (lifecycle), §6.5/§6.9(b)/§6.11 (step/condition/decision records), §7.2 (`FB_PermIntlk`), §8.2 (rollup), §8.8 (`E_Reason`). Source drafts: `Fraktal_Core_BaseClasses.md`, `Fraktal_QuickStart_and_Suite.md`. Status: **compiles under TwinCAT 3.1.4024.75** (0 errors, 0 warnings) and has been deployed to a runtime and exercised end-to-end from the HMI over ADS. A **pinned compile in CI is still pending** — it needs a self-hosted Windows runner with licensed TwinCAT XAE; the source-level rules (naming, §4.4 prefixes, 4024 compatibility, contract usage) do run on every commit via `tools/plc_lint.py`. See "Bring-up" in README and `Specification/Reports/OBJECTIVES_AUDIT.md` (O10 G7).*

## 1. Draft pseudocode fixed in the implementation

| Draft construct | Problem | Implemented as |
|---|---|---|
| `_exec IN (E_ExecState.DONE, …)` | no set-membership operator in IEC ST | explicit `OR` chain in the Execute-drop reset |
| `SysTime()` | not a TwinCAT function | `F_Now()` — [TC3] wrapper over `Tc2_Utilities.F_GetSystemTime()` (UTC, 1601-epoch FILETIME → DT); one clock feeds all timestamps (Core §2.7) |
| `CONCAT3/4/5` (Annex C drafts) | Tc2_Standard `CONCAT` is 2-arg | not needed in M1; the M2 stall walk will chain 2-arg `CONCAT` (noted for the Unit base) |
| `_M_OnAbort` (base-classes draft) | §3.14 names the hook `OnAbort` | hook named `OnAbort`/`OnCyclic` per the §3.14 catalogue, with the call-`SUPER^`-first contract in the method headers |
| bare `FOR i := 1 TO _nChild` rollup | no null/bounds guards (Core §5.6) | `_M_Register` bounds-checked; rollup/tick guard `<> 0` with `AND_THEN` (Core §5.3 short-circuit rule) |

## 2. Contract reconciliations against Core §3.2 — **folded back into Core on 2026-07-02**

These compile-driven deviations are now normative: Core §3.2 (interface surfaces + rationale), §2.2 (hooks = the §3.14 family; bases implement `I_Module`), §5.7 (inherited rows proven once), and §8.8 (band-extensibility rule) were amended accordingly, each clause stating the §1.1 objective it serves. The list below is the original record:

- **`I_Module` has no `ErrorID` property.** Every module already exposes `ErrorID` as a PLCopen `VAR_OUTPUT` (§6.1); an identically-named interface property on the same FB does not compile. Callers use `GetFaultSummary().ReasonCode` (richer anyway). `FaultActive`/`State` remain.
- **`GetFaultSummary` returns `ST_Diagnostic`,** not the §3.2 text's `ST_FaultSummary` — the §8.8 record is the one every other clause (rollup §8.2, stall walk §6.9, PermIntlk §7.2) uses; a second summary type would duplicate it.
- **Recipe changeover is transactional.** `I_Module` exposes `PrepareRecipe(Model)`/`CommitRecipe()`/`AbortRecipe()`; types stage validated `ParCfg`, and composites recurse before the Unit publishes its new `Model`.
- **Generic command ids are `DINT`.** Per-type command enums cannot appear in a common interface. Both command-bearing tiers use `ExecuteCommand(Command : DINT)` and `AbortCommand()`; the typed PLCopen `Command`/`Execute` surface remains primary.
- **`FB_ModuleBase` implements `I_Module`; tier wrappers implement their tier interfaces.** `FB_CompositeModuleBase` owns child registration, recipe recursion, and rollup without implying that a Unit is an Equipment Module.
- **Published status is `ST_ModuleStatus`.** The abandoned tier-specific `ST_CmStatus` duplicate was removed.

## 3. `E_Reason` extensibility

IEC enums cannot be extended across libraries, but Core §8.8's model is "one number space, per-type bands." Implementation: `E_Reason` declares the **framework bands only** and deliberately omits `{attribute 'strict'}`, so a module type declares its band codes (10000+) as `DINT` constants in its own library and assigns them into `ST_Diagnostic.ReasonCode` / `_M_Fault` directly. The §8.8 registry remains the single collision authority; the generated catalog (§8.8) is built from the union of the framework enum and the registered type bands.

## 4. Numbers newly pinned (Core §8.8 registry updated accordingly)

`TIMEOUT`=2001 · `PERMISSIVE_NOT_MET`=2002 · `INTERLOCK_DROPPED`=2003 · `RECIPE_INVALID`=2004 · `STEP_STALLED`=2005 (already pinned) · `RETRY_EXHAUSTED`=2006 (was named but unnumbered) · new sub-range **2900–2909 framework self-test** with `TEST_FAULT`=2901 (used only by the base suite; never raised in production). These match the values Annex A already declared (2001–2004), so docs, annexes, and code now agree.

## 5. Design decisions

- **Body = one inherited `Cyclic()` call.** Calling a module as `inst()` and through
  `inst.Cyclic()` (the `I_Module` path a parent uses) must execute the same lifecycle.
  TwinCAT source objects for concrete types therefore keep the generated FB body as the
  single statement `Cyclic();`; they put no application logic there. Per-scan extension
  work goes in an `OnCyclic` override (base first, per §3.14.2), and device logic stays in
  `_M_Dispatch`. This is the enforceable invariant; “concrete types do not write a body”
  was inaccurate for the shipped XAE objects.
- **`_M_Complete` / `_M_Fault` / `_M_FaultDiag` / `_M_ClearDiag` / `_M_SetName`** are the whole protected toolkit a type needs; `_M_Fault` stamps `SourcePath`/`Since` (`F_Now`), `_M_FaultDiag` adopts a diagnostic *verbatim* (rollup/connector, §8.2 — the child's `SourcePath` survives).
- **`FB_PermIntlk`** implements the full §7.2 canonical surface; `Since` is stamped only when the first-out *changes*; `SourcePath` is left for the owner to set when copying `Diagnostic` up (per the §7.2 usage contract). Bypass honors §7.3 (only `Bypassable`, always flagged via `AnyBypassed`).
- **The EM base extends the CM base** (per the draft): it *adds* `_M_Register`/`_M_TickChildren`/`_M_RollupFault` and overrides `ModuleType`.
- **Test coverage:** `FB_Base_Tests` proves **T1, T2, T4** once for every inheriting type, plus the **rollup (T6 at base level)** via `FB_ProbeEM` — asserting the child's `SourcePath` (`Test.EM.ChildB`) survives adoption verbatim. `FB_PermIntlk_Tests` proves first-out ordering (a later FALSE never masks an earlier one) and the bypass rules. Concrete types remain responsible for T2/T3/T5 with *their* reasons (scaffold) and tier rows per §5.7.
- **Scaffold is born RED** (Quick-start §2): `FB_TemplateCM_Tests` ships with failing T2/T3/T5 placeholders (`16#FFFF_FFFF` expected values, `AssertTrue(FALSE)`) so the §5.7 checklist drives development; T1/T4 are inherited and not repeated.
- **`OPC.UA.DA` pragmas [TC3] (superseded by §67):** the first implementation placed these on base classes and also marked every root Unit instance. Live TF6100 evidence later showed definition-level publication projecting implementation references as duplicate browse trees; §67 replaces this with deployed-root-only publication.

## 6. Known M1 limits → Milestone plan

- **M2 — `FB_UnitBase`:** mode model (§3.4, `_M_Supports`, graceful cascade §3.7 via `__QUERYINTERFACE` [TC3]), the step-chain base with `_M_SetStep`/`_M_Await` condition records, the §6.9(c) stall walk (2-arg `CONCAT` chains), `OnInit`/`OnCommandStart`/`OnModeChanged`/`OnModeExit` hooks, decision queue (§6.11).
- **M3 — providers & connectors:** `FB_LocalRecipeProvider` with SchemaVersion migrate-or-fault (§3.8), an `FB_DeviceConnectorBase` (heartbeat, `LinkTimeout`, HOLD/ABORT/MODE_STOP reaction, bounded backoff, no self-resume — §3.15).
- **M4 — first shipping type:** `FB_CylinderCM` + `FB_ClampEM` from Annexes A/B against a sim plant model (`FB_CylinderSim`, §5.7 should-clause), turning the Annex H suite into real CI.
- The **`SimForceInterlock` SIM-only hook** (§5.7) is deferred to M4 with the first HAL-bound type; the scaffold marks where it belongs.

## 7. Timing capture & time classification (Core §8.11.4) — M1.x, 2026-07-02

Implements the cycle-time-profile amendment, including clause (f) time classification. Design points:
- **Two clocks, deliberately (§8.11.4(e) / TC3 §8.11):** durations from the monotonic ms clock (`TIME()` differenced as `DWORD`, wrap-safe across the ~49-day rollover); wall-clock `Started`/stamps from `F_Now()` so profiles align across stations (§2.7). Never mix the two.
- **`F_TimingUpdate` is a pure function** (running mean `avg += (x−avg)/n`) so the aggregate math is unit-tested with exact values (100/200/300 → avg 200 in `FB_Timing_Tests`).
- **Base-class capture is transition-driven:** the row closes on `BUSY → DONE/ERROR/ABORTED` via `_prevExec`, so faulted/aborted commands are measured too. A type contributes only `_M_TagCommand(TO_DINT(Command), '<label>')` — one idempotent line, in the scaffold; untagged types still get `LastCmdTime` and an id-0 row.
- **Classification is opt-in per wait step (§8.11.4(f)):** `StepChanged(…, TimeClass := E_TimeClass.WAIT_UPSTREAM)` — default `WORK`, so non-wait steps cost nothing. The profiler accumulates `ByClass[TO_INT(time class)]` and publishes `WorkTime` (**the real cycle time**) and `WaitTime` at `CycleComplete`; the suite asserts `Total = WorkTime + WaitTime` and that classes survive into both the waterfall and the per-step aggregates. `WAIT_UPSTREAM`/`WAIT_DOWNSTREAM` are the per-step attribution of §8.11.3 Starved/Blocked; M2's chain base may auto-attribute them from the Unit's Starved/Blocked conditions (explicit class wins).
- **Find-or-allocate rows, fixed arrays:** `Count = 0` marks a free slot; overflow sets `Truncated`/`StatsTruncated` rather than growing — capture never allocates at runtime.
- **`FB_CycleProfiler` is event-driven** (`StepChanged`/`CycleComplete`, no cyclic body): a refreshed same-step call is a no-op (but may re-declare the class), the first step opens the cycle (§8.11.1 start marker), `ResetStats` exists but the *caller* must log the reset (§8.11.2).
- **M2 wiring:** the Unit/step-chain base will call `StepChanged` inside `_M_SetStep` (forwarding the step record's class) and `CycleComplete` at `N999` — step timing and classification become zero-effort by construction; until then a Unit adds the two calls once (Annex C §C.6 note).
- **HMI:** `Timing`, `Current`, `LastCycle`, `StepStats` are fixed framework DUTs under the base-class pragmas — the §3.13 waterfall (coloured by class, Total/Work/waits header) and Pareto bind to them with no per-type wiring.

## 8. M2–M4: the lifecycle family completed (2026-07-02)

**M2 — `FB_UnitBase`** (now extends `FB_CompositeModuleBase`, implements `I_Unit`): modes reject unsupported requests gracefully; Start/Stop reuse the §6.1 lifecycle; step records power pending diagnostics, rollup, Starved/Blocked, and profiling. A non-graceful mode change performs an **immediate non-safety software abort**; `OnModeExit` stages graceful stopping. The one-slot decision and cycle profiler remain inherited services.

**M3 — `FB_DeviceConnectorBase`** (§3.15): abstract transport quartet `_M_Open/_M_Close/_M_HbStart/_M_HbPoll : E_HbResult`; heartbeat, `LinkTimeout` loss confirm, `DEVICE_PROTOCOL_ERROR` vs `LINK_TIMEOUT` first-outs, bounded exponential backoff (DINT-ms doubling capped at `BackoffMax`), session drop on loss, **no self-resume** (the fronting CM owns `Reaction`). Row **T7 proven once** (§5.7 amendment). **`FB_LocalRecipeProvider`** (§3.8): generic validation via the new **SchemaVersion-first-member rule** (spec amendment) — stored first-`UINT` vs target's initialized first-`UINT`; unknown id, size mismatch, or schema mismatch → `Load = FALSE`, caller faults `RECIPE_INVALID`; `MEMCPY` only after full validation (never partial).

**M4 — `Fraktal_Modules`** (separate reusable-module library, own §8.8 band constants `PL_ModuleReasons`): `FB_CylinderCM` provides interlock-first device logic and direction-specific diagnostics; `FB_ClampEM` provides parallel fork/join, partner abort, settle/confirm, and transactional recipe recursion; `FB_CylinderSim` is the §5.7 plant model.

**Suites** (all in one open-ended gate, §6.8/H.6): `FB_Unit_Tests` (stall text asserted verbatim: `'Step 100 StepA stalled'`; Starved from wait class; stop-after-cycle; 2-step profile published; E-stop-by-default mode change), `FB_Connector_Tests` (T7: healthy beat links; protocol FAIL and silent LINK_TIMEOUT paths, `SourcePath` asserted), `FB_CylinderCM_Tests` (T2/T3/T5 with the type's own reasons + functional completion against the sim; deterministic timing via `T#0S` timeouts), `FB_ClampEM_Tests` (H.5 rollup: `ClampStation.CylB` verbatim). T1/T4 are not repeated per type (§5.7).

**Compile-plausibility caveats to watch at first build:** `SEL` on `STRING` operands in `FB_CylinderCM` (replace with IF if the pinned compiler objects), `DINT_TO_TIME`/`TIME_TO_DINT` availability, and interface `= 0` comparisons.

## 9. Pre-HMI gap closure (M5, 2026-07-02)

The pre-HMI review found that the HMI-facing surface was accidentally accessor-shaped: `Name`/`State`/`FaultActive` were properties and the diagnostic only reachable via `GetFaultSummary()` — **none of which appear in the OPC UA namespace** (TF6100 publishes symbols, not accessors). That also made the base non-conformant with §6.9(a)'s "publish the diagnostic each scan". Closed by: **`ST_ModuleStatus` data mirror** refreshed every scan in `FB_ControlModuleBase` (name set in `_M_SetName`; on Units the live `Pending` stall surfaces on the mirror whenever no fault is active); **§6.9(a) ring buffer** (`History`, fixed size, newest at `HistoryHead`, pushed on the ERROR rising edge); **§8.11 counters** (`GoodCount`/`NokCount` + public `CountGood`/`CountNok`). Spec: new **§3.10(a′)** ("the HMI contract is data, not accessors") and a **§3.13 discovery-and-binding bullet** (module marker = the `Status` member; narrow write surface). `HMI_CONTRACT.md` is the bind table the HMI phase builds against. Deliberately deferred to the HMI phase, recorded there: §7.6 manual-function release gating (item #1, blocks any HMI write of `Command`/`Execute`), §8.3 alarm ack workflow, §8.8 text catalog. Proven in `FB_Hmi_Tests` (mirror fields, pending-on-mirror, counters).

## 10. Pre-HMI regression fix (2026-07-04)

Audit before starting the HMI found one **compile-blocking regression**: the `Model : ST_ModelId` member declaration in `FB_UnitBase` had been dropped during a later edit to that FB's `VAR` block (which added the HMI data-mirror members `Status`/`History`/`GoodCount`/`NokCount`). The `SetModel` method (`Model := Id`) and `ModelCode` property (`Model.ModelCode`) both reference it, so the type would not have compiled. **Restored** the declaration between `StallTime` and `GoodCount`. Verified: `Model`, `Status`, `History`, `HistoryHead`, `GoodCount`, `NokCount`, `Pending`, `Profiler`, `CurrentStep` all resolve in `FB_UnitBase` through the inheritance chain; all 80 files pass XML/lint/VAR-balance/project-list gates.

Also confirmed sound (not regressions): the HMI-prep additions from the prior session — `ST_ModuleStatus` data mirror refreshed each scan by `FB_ControlModuleBase` (+ `Pending` overlay in `FB_UnitBase`), the §6.9(a) `History` ring via `_M_PushHistory`, `CountGood`/`CountNok`, `HMI_CONTRACT.md`, and `FB_Hmi_Tests` — are internally consistent, wired into the runner, and present in the project compile lists. There is correctly **no `FB_Hmi` POU**: per §3.10(a′) the HMI binds published *data*, not a PLC-side HMI object.

## 11. Alarm & event history — §8.3 implemented (2026-07-04)

Spec: §8.3 rewritten from a two-line promise into the full contract — (a) `ST_AlarmEvent` record with `Duration` (monotonic come→gone per the two-clock rule) and synchronized `ComeAt/GoneAt/ResetAt`; (b) `E_ResetClass`: **AUTO_RESET** closes when the condition re-establishes, **MANUAL_RESET** stays blocking (`WAIT_RESET`) until a deliberate, release-gated operator reset — never self-closing (§9.3 principle), and the Unit **refuses `Start`** while any such event is open; (c) automatic capture: `FB_UnitBase` raises an ERROR/MANUAL_RESET event from the rolled-up first-out on ERROR entry and marks it gone on exit — the event IS the diagnostic plus lifecycle, nothing double-authored (O1/O3); (d) per-Unit `Active[]` + closed `Ring[]` browsable over OPC UA; **`I_EventSink`** invoked at come and close so a DB/historian adapter subscribes later without touching the log — interface normative now, adapters deferred by design (exactly the user's "we don't have to code this now"); (e) ISA-18.2 state mapping, reset doubles as acknowledge.

Code: `E_Severity`/`E_ResetClass`/`E_AlarmState`/`ST_AlarmEvent`, `I_EventSink`, `FB_AlarmLog` (Raise/RaiseDiag/Gone/OperatorReset/SetSink, fixed arrays, `Blocking`), UnitBase wiring (`AlarmLog`, `_faultEvt`, Start gate, public `OperatorReset`). Severity is the sole presentation/priority axis. Suite `FB_AlarmLog_Tests`: AUTO closes with Duration into the ring; MANUAL survives condition-gone and unblocks only on OperatorReset; Unit refuses Start while blocking.

**Honest gap:** the third test asserts Start-blocking by raising through the log directly; the *automatic* ERROR-entry capture path in `OnCyclic` is wired but not yet asserted by a test (FB_ProbeUnit has no easy fault injection). Add a `SimFaultStep` input to the probe and assert `AlarmLog.NActive = 1` after a forced fault — small item for the next pass or first compile session.

## 12. User access levels — §7.7 implemented (2026-07-04)

New Core §7.7: access level as the **who** dimension of release, ANDed with §7.2–§7.6's machine dimensions. Ordinal `E_AccessLevel` (NONE<OPERATOR<TECHNICIAN<ENGINEER<ADMIN); nine `E_GatedAction`s covering exactly the user's list (data read/write, manual — with per-function override via §7.6 —, changeover, mode change, start/stop, alarm history, alarm reset, policy edit). **Per-station policy** = persistent station config (§3.8a); **shipped default fully open** (every threshold NONE ⇒ no login needed — the deliberate-decision principle: locking down is a commissioning choice per §14 checklist, never silent). `I_AccessProvider` + `FB_LocalAccessProvider` default (persistent user/PIN table) mirror the provider pattern; `FB_AccessManager` per root: data-driven login per §3.10(a′) (methods are invisible to OPC UA), secret cleared after every attempt, idle auto-logout, audit via §8.3 MESSAGE events. Gated in `FB_UnitBase`: `SetMode`/`SetModel`/`Start`/`Stop`/`OperatorReset`. Cascade safety: thresholds enforce at the root the HMI addresses; framework-internal calls are trusted (documented in §7.7(c)) — with fully-open child defaults the cascade is unaffected in every configuration. Suite `FB_Access_Tests`: open-by-default; threshold denial audited; wrong-PIN rejected; login grants; secret cleared; logout re-denies. Deferred to their owning phases: `DATA_WRITE` enforcement in the generic editor and per-function `MANUAL` in the §7.6 implementation (both spec'd now). Security caveat, stated honestly: the local PIN travels the OPC UA write path — pair with server-side encryption/auth (§7.7(d), TC3 §11.1) for anything beyond shop-floor-trust deployments.

## 13. Configurable cylinder Control Module — FB_ConfigurableCylinderCM (2026-07-04)

A production-grade reusable cylinder CM alongside the Annex-A/B teaching `FB_CylinderCM`. Answers the brief (2 optional home/work sensors, 5 s default max move time) and adds what a real cylinder CM needs, each justified by an objective:
- **Optional AND redundant sensors (0..N per position).** `Cfg.HomeSensorCount`/`WorkSensorCount` (0 = sensorless/time-based; N up to `PL_Fraktal.MAX_POS_SENSORS`, default 2, raise for 2oo3). HAL carries sensor **arrays** `HomeFb[]`/`WorkFb[]`. **Arrival = ALL wired sensors TRUE** (`_M_PosArrived`, AND-combine — the safest rule for safety cylinders). One type serves sensorless, single-sensor, and duplex/redundant actuators (O4/O1).
- **Your timing.** `MoveTimeout := T#5S` default; `SettleTime` debounce so a chattering reed switch can't false-complete; `TravelTime` for the sensorless path (must be `< MoveTimeout`, checked).
- **Plausibility & integrity faults** (own §8.8 band 10200s): `CYL_WORK/HOME_NOT_REACHED` (timeout), `CYL_DISCREPANCY` (redundant sensors for one position disagree longer than `DiscrepancyTime` — dual-channel monitoring, like a safety-gate discrepancy timer; checked continuously in OnCyclic), `CYL_BOTH_SENSORS` (home+work both confirmed — implausible), `CYL_SENSOR_LOST` (reserved), `CYL_CFG_INVALID` (count out of range or bad travel/timeout — bad config faults, never runs wrong; O3/O7).
- **Single- or double-acting** (`SingleActing`: spring return drives home with no solenoid), **fail-safe abort** (`DeenergizeOnAbort` default, or drive to `SafePosOnAbort`) per §3.14.2, **startup position resolve** (`Position`/`AtPos` from whatever sensors exist, §3.12).
- Inherits the whole lifecycle: edge/handshake, ErrorID, per-command timing (§8.11.4 `TO_HOME`/`TO_WORK` tags), abort routing. `FB_ConfigurableCylinderSim` (per-sensor stuck-mask to inject faults) + `FB_ConfigurableCylinderCM_Tests` (duplex AND-arrival, discrepancy, sensorless, and timeout cases). SIM force hook for interlock (§5.7).

## 14. Fieldbus ADS adapter — contract sketch (2026-07-04)

Deliverable so an integrator can wire real EtherCAT data. Not runnable against a master here — a *seam + guide*, honest about what needs InfoSys verification.
- **PLC seam:** `I_FieldbusScanner` (Scan / RefreshValues / ForceChannel) + `FB_EcFieldbusScanner` skeleton naming the real `Tc2_EtherCAT` building blocks (`FB_EcGetSlaveCount`/`GetAllSlaveStates`/`GetSlaveIdentity`, `FB_CoeSdoReadEx`) with TODO bodies and a working AL-state→`E_NodeState` map (`_M_MapState`, low-nibble 0x01/0x02/0x04/0x08 + 0x10 error bit). Flat node table (`MAX_BUS_NODES`).
- **HMI seam (historical):** this pass originally added an `EtherCatGatewayRepository` stub; §41 supersedes it with the native OPC UA repository and versioned Web gateway client.
- **Doc:** `fraktal-tc3/FIELDBUS_ADS_ADAPTER.md` — two deployment paths (A: PLC-published `ST_BusNode` over OPC UA, works on all 4 platforms incl. Web; B: direct client, no Web without a gateway), the channel-value design (read the process image via HAL references, not raw addresses — keeps the channel↔module link exact), the honestly-flagged force path (write mapped output vs true ADS force), and an acceptance checklist. TC3 §10.6 points to it.
- **Objectives:** O4/O8 (any bus fills the same table; neutral node state), O1 (fieldbus knowledge in one place, Path A), O3 (topology + alarms are one source, not a side-channel). The force path re-uses §7.6/§7.7 gating + §8.3 audit — the caller gates and logs, the scanner only writes.

## 15. Manual command surface — §7.6.1 (2026-07-04)

Single manual path (MANUAL-mode-only, no override). Each command-bearing module publishes a self-describing `{value,label}` catalog. `FB_ModuleBase` owns the generic request latch, and `FB_UnitBase.ManualCommandTo` is the mode/access/release gate. `FB_ConfigurableCylinderCM` demonstrates that the HMI, generic interface, and typed PLCopen path all reach the same validated dispatch and interlocks. `FB_ManualCmd_Tests` covers publication, rejection outside MANUAL, and acceptance in MANUAL.

## 16. Mode control bar + switch policy + run styles — §3.4.1/§3.4.2 (2026-07-04)

*(Refinements: `_M_StepGate` gained a per-step `Steppable` input — a step passed as FALSE runs through even in SINGLE_STEP/HOLD_TO_RUN, both styles honouring it identically. `StopPending` property (TRUE while stop requested + still BUSY) drives a blinking stop button in the HMI. On the pinned 4024 binding every method input is explicit; optional method inputs require 4026+.)*


Resolved the tension in the brief (immediate-interrupt vs safe-finish vs disabled-per-mode) with the rule **Stop is graceful, mode-change is the interrupt**, and made the interrupt behaviour per-mode policy. Spec §3.4.1: two orthogonal axes — `E_ModeSwitchShield` (INTERRUPTIBLE/CONFIRM/BLOCKED_WHILE_RUNNING) × `E_ModeSwitchStyle` (GRACEFUL/IMMEDIATE) — as `ST_ModePolicy[E_Mode]`, station config with safety defaults (AUTO=CONFIRM+GRACEFUL, CHANGEOVER/CALIBRATION=BLOCKED, HOME=INTERRUPTIBLE+IMMEDIATE). The policy of the mode being LEFT governs. §3.4.2: `E_RunStyle` (CONTINUOUS/SINGLE_STEP/HOLD_TO_RUN), optional per mode via `_M_SupportsRunStyle`, consulted by the sequence author through `_M_StepGate` at step boundaries. **HOLD_TO_RUN over HMI is explicitly NON-SAFETY** (no dead-man; interlocks still apply) — spec callout + code comments.
Code (FB_UnitBase): `ModePolicy[]`, `RunStyle`, shield check in `SetMode` (BLOCKED returns FALSE while BUSY — graceful rejection, not a fault), style applied in the pending-mode path (GRACEFUL sets `_stopReq` to finish the cycle; IMMEDIATE keeps the OnModeExit/OnAbort path), `_M_InitModePolicy`, `SetRunStyle`/`_M_SupportsRunStyle`, `StepRequest`, `SetHoldRun`, `_M_StepGate`. 116 PLC files pass.
HMI: `ModeBar` on the right (mode icon + selector top, play/stop bottom, step toggle), reads `running`/`runStyle`/`supportedModes`/`supportedRunStyles`/`modePolicy`; prompts/blocks per policy; MANUAL hides run controls; hold-to-run is press-and-hold labelled non-safety. Repo methods `setRunStyle`/`stepRequest`/`setHoldRun` on both impls. 19 Dart files pass.

## 17. Show-why-blocked release transparency — §7.6.0 (2026-07-04)

Rule: pressing any not-released control shows why. Full rollup (user's choice), persistent bottom panel (user's choice). Spec §7.6.0: every gated action publishes, on demand, the complete set of withholding reasons (not first-out) across mode/access/alarm/interlock sources; live; read-only (never bypasses). Code: `ST_ReleaseReason` DUT; `FB_PermIntlk.AppendFailed` (enumerates every defined+FALSE+non-bypassed condition into a caller list); `FB_UnitBase.WhyBlocked(action, list)` assembles framework reasons (access via Access.Permits, mode-pending, AlarmLog.Blocking, not-READY, not-MANUAL) + delegates child interlocks to overridable `_M_AppendModuleReasons`; probe Unit demonstrates the override via `Cyl.Intlk.AppendFailed`. 117 PLC files pass. HMI: `ReleaseReason` + `ModuleNode.blockReasons` (per GatedAction), `whyBlocked` on both repos, `WhyBlockedPanel` at the bottom of the module view (auto-updates, shows 'released' when free), blocked Start (amber, reveals why) + blocked manual buttons (reveal panel) — pressing a blocked control shows reasons instead of no-op. 20 Dart files pass. Objective O3 (diagnosability) applied pre-action, not just post-fault.

## 18. Release panel wiring fix — blocked buttons now actually open it (2026-07-04)

### 18.1 Extended to all gated controls (2026-07-04)
Applied the same act-or-explain rule to the remaining controls. PLC: `FB_UnitBase.WhyBlockedAction(E_GatedAction)` — a general rollup (access + per-action state: CHANGEOVER not-while-running, ALARM_RESET needs a blocking alarm, MODE_CHANGE not-while-pending) using the same predicate as the gates; Start keeps its richer `WhyBlockedStart` (interlocks), manual keeps `WhyBlockedManual` (target). HMI: generic `whyBlockedAction`/`showWhyBlockedAction`; mode-bar **step** and module-detail **Stop**, **operator-reset**, **changeover** now explain-when-blocked via the release panel (changeover made always-visible instead of hidden below access). **Force** (fieldbus, channel-scoped not Unit-scoped) explains inline via a snackbar rather than the Unit panel — routing a channel concern through the Unit release report would be a category error. Every gated control is now pressable and either acts or explains; no silent dead buttons remain. 20 Dart + PLC gates pass.


Audit prompted by 'are the buttons ready to open it when not released?' found the honest answer was NO/inconsistent: (1) the mode-bar Start used `onPressed: permits && !stopPending ? .. : null` — a null onPressed can't fire, so the access-denied case was a DEAD button that couldn't open the panel; (2) two parallel release mechanisms had accreted across turns — `blockReasons`(node map)+`showWhyBlocked`+`why_blocked_panel.dart` vs this turn's PLC-query `releaseReport`+`showWhyBlockedStart/Manual`+`release_panel.dart` — with the mode bar mixing them; (3) module_detail had a duplicate Start/Stop (`: null` when blocked, never explained); (4) the dead sim `_blockReasonsA` built `ReleaseReason(str, str)` — a signature that no longer matched the domain (`description, kind`) and would not compile. Fix: consolidated on the PLC-query path, deleted `why_blocked_panel.dart` + `blockReasons` + `blockPanel*` + dead `whyBlocked(singular)`; made every blocked-press (mode-bar Start, module_detail Start, manual buttons) stay pressable and call `showWhyBlockedStart/Manual` (act-or-explain); sim `whyBlockedStart` returns reasons for all four causes so the panel is never empty. Rule now uniform: a blocked control is pressable and either acts or explains — never a silent dead button. 20 Dart files pass.

## 19. Rename WhyBlocked → ReleaseReport (2026-07-04)

Renamed the live release-query API for consistency with `ST_ReleaseReport` / the release panel: PLC `WhyBlockedStart/Manual/Action` → `ReleaseReportStart/Manual/Action`; HMI `whyBlocked*` → `releaseReport*`, `showWhyBlocked*` → `showReleaseReport*`. The rename also flushed out **orphaned dead code** from the earlier (list-based) release iteration that the prior consolidation had missed: `FB_UnitBase.WhyBlocked : INT` and its `_M_AppendModuleReasons` hook (uncalled) were deleted, and stale `WhyBlocked`/`why_blocked_panel` references in the spec §7.8 and HMI_CONTRACT were updated (a stale contract paragraph removed). Historical change-log entries in this file (§17/§18) intentionally retain the old names — they record what the code was called at the time. 120 PLC + 20 Dart files pass; reference audit clean.

## 20. AAS / digital nameplate — verification & completion (2026-07-11)

Follow-up to the trends gap analysis (item 2). Found a prior session had already built most of it: §3.10.1 spec, `ST_Nameplate` (IDTA-02006-shaped), `SetNameplate` on `FB_ControlModuleBase` (inherits everywhere), HMI `Nameplate` domain + `NameplateCard` + sim data, and **Annex K** (AAS/IEC 63278 mapping, sibling of Annex J). This session verified and completed rather than duplicated:
- **Fixed compile-blocking literal `\n` bugs**: `SetNameplate`'s body (prior session) and `FB_ProbeUnitManual`'s `SetAir`/`_M_AppendInterlocks` (this conversation's own earlier edit) contained literal backslash-n instead of newlines — XML-valid, VAR-balanced, invisible to the structural gates, but not compilable ST. Fixed both files (8 occurrences); added a literal-`\n` scan to the gate run.
- **Example now honours the §3.10.1 'shall'**: `MAIN` publishes nameplates for both root Units at the instantiation site (per-serial identity, shared type data), demonstrating that identity belongs to the machine builder, not the type.
- **`Nameplate_roundtrip` test** added to `FB_Hmi_Tests` (nameplate is part of the HMI contract); first version referenced a nonexistent `_probe`, caught and corrected to `_p` before delivery.
- Audit extended to annex letters A–K; HMI_CONTRACT gained the nameplate section. 121 PLC files + Dart pass.

## 21. OEE + trend HMI — §8.5.1 (2026-07-11)

Trends gap item 3. OEE is a derivation from existing contracts (GoodCount/NokCount §8.11, ExecState §6.1, Blocking §8.3) — only time accounting added. Spec §8.5.1: run/down/idle buckets per scan (idle excluded from A — no demand ≠ downtime; buckets published so deployments re-derive); A×P×Q with per-factor validity, invalid factors OMITTED from the product (never 100%, O7); Performance only with a configured per-model ideal cycle (§3.8), capped at 1.0; bounded trend ring (60 × 1 min defaults), long-horizon = historian; ResetOee DATA_WRITE-gated + §8.3-audited.
Code: ST_Oee/ST_OeeSample; FB_UnitBase `_M_OeeUpdate` (F_Now deltas, UDINT-ms wrap-safe subtraction) split from pure `_M_OeeCompute` (testable without clock control), SetIdealCycle, ResetOee. Tests FB_Oee_Tests via probe driver: Q from counters, A from buckets, invalid-P omitted (OEE=A×Q proves no fake 100%), P cap at 1.0. Time *accumulation* is runtime-verified, stated in the suite header. 124 PLC files pass.
HMI: OeeSnapshot domain, OeeCard (exception colouring vs 0.85 target, per-factor bars, '—' for invalid, CustomPaint sparkline — zero packages), resetOee on all repos, act-or-explain reset via the release panel. Sim: quality live from counters, availability dips on the CylB fault, 24-sample trend. 20 Dart files pass.
Watch items for first compile: TIME_TO_UDINT (recurring), REAL comparisons in TcUnit (AssertEquals_REAL Delta signature).

## 22. Alarm shelving + rationalization — §8.9/§8.10 (2026-07-12)

Roadmap closer. Spec already governed shelving (§8.10); added the hard rule: **shelving suppresses annunciation, never control** (shelved blocking alarm still blocks; interlocks/release reports untouched; SAFETY never shelvable; unrationalized reasons not shelvable — rationalize first).
Code: E_GatedAction += ALARM_SHELVE=9 (ordinal-safe append; ST_AccessPolicy widened 0..9); ST_AlarmEvent += Shelved/ShelvedUntil (appended, mirror-safe); ST_AlarmMeta + FB_AlarmLog.RegisterMeta/Meta catalog; FB_AlarmLog.Shelve/Unshelve (SAFETY+meta checks, capped at MAX_SHELF_S, self-logging) + Cyclic auto-expiry countdown (F_Now deltas), ticked from FB_UnitBase; gated ShelveAlarm/UnshelveAlarm on the Unit. MAIN registers example rationalization (discrepancy non-shelvable, work-timeout shelvable). Tests FB_Shelve_Tests: unrationalized refused, SAFETY refused, **shelved-still-blocks (the O7 test)**; expiry timing runtime-verified.
**Collisions found & fixed while wiring:** (1) `CYL_BOTH_SENSORS` declared TWICE in PL_ModuleReasons (10103 + 10203) — duplicate-identifier compile error; production one renamed CYL_POS_IMPLAUSIBLE. (2) The basic-cylinder band 10201–10206 **squatted on the axis CM's registered band 10201–10204** (§8.8 registry = one number space) — renumbered to 10110–10116 inside the cylinder CM 100-block and registered. Audit extended: GVL duplicate scan + band-squat check now run every pass.
HMI: GatedAction.alarmShelve (ordinal 9 verified), AlarmEvent += reasonCode+shelved, AlarmMeta joined onto rows ('→ operator action'), shelved rows de-emphasized + banner-excluded (never hidden), shelve/unshelve buttons with act-or-explain. 126 PLC + 20 Dart pass.

## 23. Release implementation audit — hidden issues found & fixed (2026-07-12)

User-requested audit of §7.8 (PLC + HMI). Verified clean: FB_PermIntlk.AppendFailed member usage (_conds/.Defined/.Description/.Reason/.Bypassable, _bypass, Cond — all exist as used); AlarmLog.Raise call-site parameter names (Kind/Reason/Text/Source/Severity/Category/ResetClass match); E_Reason.NONE exists; module-detail Start/Stop are Unit-only; ReleaseReason ctor usage matches the domain.
Three real issues found and fixed:
1. **Sim query≠gate drift (O7 violation):** `releaseReportStart`'s mode reason was gated on `!_convWarn` — a ConveyorB flag unrelated to StationA — so a blocked-by-mode Start could report Released=TRUE. Also sim `start()` ignored mode entirely while the query reported a mode reason. Fixed both: reason condition is `_modeA != auto`; `start()` gate is now the same predicate the query reports.
2. **Stale release panel:** nothing re-ran the query while visible, so "stays while blocked / clears when released" and the panel's green 'Now released' state could never occur. Fixed: app-state stores the active query closure and re-runs it on every forest update (re-entrancy-guarded); clearRelease drops it. The panel is now live, matching §7.8's contract.
3. **ReleaseReportManual originally ignored its exact target and command:** the selected child's §7.6 conditions couldn't be appended, and a directional device could not distinguish extend from retract. The query and hook now carry `(TargetPath, Value, Report)`; the base preserves its Unit-level fallback while concrete Units may delegate to the selected child's pure release query.
Known remaining (unchanged, cosmetic): mode-bar Stop-while-running-without-access falls back to releaseReportStart. All gates pass.

## 24. Full-codebase semantic audit — both PLC and HMI (2026-07-12)

New checks beyond the structural gates: (1) named-parameter call sites vs actual METHOD signatures across all POUs; (2) every `PL_*.<CONST>` reference exists in its GVL; (3) every `E_*.<MEMBER>` reference exists in its enum (proper parser incl. single-line enums); (4) method calls on typed FB instances resolve through inheritance; (5) orphaned-public-method scan; (6) full HMI↔PLC enum-ordinal matrix (15 pairs); (7) both repositories implement all 20 contract methods; (8) all `app.<x>` UI references exist in app_state.

**Compile-blocking bugs found & fixed (root cause: `if X not in file` idempotency guards silently no-op'ing when an OLD artifact already carried the name):**
1. `FB_PermIntlk.AppendFailed` was still the OLD §7.6.0 list-based signature (`List/Count/Source`) — the §7.8 guard skipped writing the Report-based one; every current call site targeted a nonexistent signature. Replaced (verified single, Report-based).
2. Four `PL_Fraktal` constants never landed (`MAX_OEE_SAMPLES`, `OEE_SAMPLE_MS`, `MAX_ALARM_META`, `MAX_SHELF_S`): `MAX_RELEASE_REASONS` already existed at 24 (not the expected 16), so the OEE anchor missed and each later constant chained on the previous missing one — a silent cascade. All four added with post-verification.
3. Invalid event-kind members in `FB_Shelve_Tests` exposed a duplicate taxonomy. Alarm presentation now uses the single `E_Severity` axis.
4. Orphaned `_M_AppendModuleReasons` override in FB_ProbeUnitManual (base counterpart deleted in the rename turn) calling the old AppendFailed signature — deleted.
**HMI:** all contract enum ordinals match; repositories are complete and UI→state references are clean. Fixed `_Blink` running its ticker permanently (now animates only while active). `E_Severity` is mirrored as Dart `Severity`; event kind is no longer a second priority axis. Remaining orphan-scan hits are intentional HMI/OPC-UA entry points and adapter seams.
**Process change:** idempotency guards are retired in favour of anchored edits with post-assertions; the combined semantic gate (checks 1–4) joins the standard gate run.

## 25. TCP/IP device CMs — byte-transport seam + ASCII device base (2026-07-12)

Answering "do we have a base for TCP/IP devices (Keyence IV3, Datalogic Matrix 220)?": we had the *upper* half (FB_DeviceConnectorBase §3.15 link supervision, transport-agnostic) but no transport seam and no request/response CM base. Added, spec-first (Core §3.15.1a + TC3 §3.15):
- **`I_ByteChannel`** — THE porting seam (O4/O8): non-blocking Open/Close/Send/Poll/State/Tick, cyclic-poll semantics. TC3 binds via Tc2_TcpIp (TF6310); CODESYS SysSocket/NBS; Siemens TSEND_C — device CMs never name a socket API and port unmodified.
- **`FB_AsciiDeviceCM`** (CM base): configurable terminator framing, one-outstanding-request state machine, response timeout ⇒ fault, RX-overflow guard, bounded-backoff reconnect, LinkState published (Annex D facet — zero new HMI code). Reason band **10401–10406** (`PL_TcpDevReasons`, registered §8.8).
- **`FB_SimByteChannel`** — scripted channel: device CMs TcUnit-test end-to-end with no socket/hardware. `FB_TcpDev_Tests`: request→scripted reply→parse (terminator stripped, judgement set); SwallowNext→**10402 timeout** (cyclic test, runtime TON).
- **`FB_TcpChannelTc3`** skeleton naming FB_SocketConnect/Close/Send/Receive with TODO bodies — verify signatures/TF6310 license/TcpIpServer against InfoSys.
- **Profiles** `FB_Iv3VisionCM` / `FB_Matrix220CM` (`Fraktal_Modules`): publish 'Trigger' (§7.6.1), Execute path completes on parsed response, IV3 OK/NG judgement, Matrix decoded-code/NOREAD. **Protocol strings are Setup-visible parameters explicitly marked VERIFY-vs-vendor-manual — typical forms, not confirmed facts.**
132 PLC files pass the combined gate. Watch items: `TIME * INT` backoff doubling, `FIND/DELETE` string semantics, `'$R'` terminator escape — first-compile checks.

## 26. Device-category CMs — configure first, extend second (2026-07-12)

User correctly flagged a philosophy inconsistency in §25: the CM layer is function-first (`FB_ConfigurableCylinderCM`, not `FB_FestoCylinderCM`), yet the TCP layer jumped to vendor-model CMs. Restructured to match the standard's own philosophy:
- **`FB_TcpVisionCM`** and **`FB_TcpCodeReaderCM`** (new `DeviceCMs/` in the Core library, non-abstract): CATEGORY CMs directly usable for most devices via configuration alone — protocol strings are §3.8-able parameters (TriggerCmd, Ok/NgPrefix + ResultSep payload extraction; NoReadText + optional MatchCode verification). Both publish Trigger (§7.6.1), complete Execute on the parsed response, fault DEV_PROTOCOL on garbage.
- **Model FBs became thin presets**: FB_Iv3VisionCM / FB_Matrix220CM now EXTEND the category CMs and contain only preconfigured strings in Setup — demonstrating the extension seam ("override _M_OnResponse only for genuinely special formats"). Chain: preset → category → FB_AsciiDeviceCM → FB_ControlModuleBase.
- **Tests retargeted to the category level**: the vision CM is CONFIGURED (not subclassed) for an IV3-style dialect in the test itself — proving the configure-first claim; reader test covers decoded-code + NOREAD + match verification; timeout test unchanged.
- Spec §3.15.1a amended with the category layer and its honest boundary: covers ASCII request/response; binary/unsolicited-streaming protocols need a different base (deferred until demanded).
134 PLC files pass. Watch item added: MID(str, len, pos) argument order in the payload extraction.

## 27. Cross-runtime latent-defect audit (2026-07-12)

Confirmed defects fixed at their shared seams: the Unit pending diagnostic now overlays `Status` only after the common mirror refresh; OEE and shelf expiry use the monotonic `TIME()` clock rather than assigning wall-clock `DT`; alarm-slot reuse clears shelving state and zero-duration shelves are refused; manual commands validate the published catalog and enter the inherited PLCopen lifecycle; typed cylinder/clamp dispatch rejects unsupported command values with registered reason 2008; failed `SetModel` restores the prior published identity; Step/Hold writes are PLC-gated; terminal Unit runs can be released by `Stop`; common-base `OnInit` and edge-triggered `OnAbortInError` now cover every module tier, and Unit initialization no longer erases an injected access provider. The HMI access-policy mirror now covers all ten gated actions and fails closed on a stale short array, configuration writes use the repository instead of a placeholder snackbar, multi-root simulation keeps independent sessions, and duplicated detail controls no longer bypass the mode bar's switch policy. Regression coverage was added for the status overlay, automatic Unit fault capture, manual actuation, shelf reuse/zero duration, and HMI policy cardinality.

## 28. HMI connection bootstrap and execution roadmap (2026-07-12)

Added `Specification/Reports/IMPLEMENTATION_ROADMAP.md`, converting the objective/coherence review into ordered phases with explicit exit gates: executable root-Unit forest; inherited composite behavior; physical four-structure contract and transactional recipes; authoritative manual release; trustworthy diagnostics/KPIs; production HMI transport; generated interoperability projections; security and a second binding.

The HMI now starts behind `ConnectionBootstrap`. First use or an endpoint never proven `LIVE` opens a wizard; previously proven settings reconnect behind a full-screen interaction lock. `STALE`/`DOWN` removes the shell immediately, no writes are queued, and connection editing appears only after 30 seconds without `LIVE`. `everConnected` is persisted only after a repository reports `LIVE`. SDK-only persistence keeps the zero-package policy (native JSON file / Web local storage). Widget tests prove first-use, 30-second timeout, and live-link-loss behavior. The production OPC UA/gateway repository remains deployment work and therefore fails closed rather than presenting an empty interactive HMI.

## 29. Reusable-module library identity (2026-07-12)

Renamed the former example-oriented project to `Fraktal_Modules`. The project contains reusable shipping module types, simulation models, and configured device presets; calling it “Examples” understated its supported-library role and encouraged copy/paste use. The physical directory and `.plcproj`, TwinCAT project name/title/default namespace/placeholder, dependent test-library reference, documentation, and `PL_ModuleReasons` symbol now share one identity. Object and project GUIDs were deliberately preserved so the rename does not manufacture new TwinCAT objects.

## 30. Aggregate test-gate identity (2026-07-12)

Renamed the aggregate PLC test project to `Fraktal_Tests`. Its single TcUnit runner covers both `Fraktal_Core` framework behavior and `Fraktal_Modules` reusable types, so a Core-only name misrepresented the gate. The directory, `.plcproj`, TwinCAT name/title/default namespace, normative binding text, and working documentation now agree. It is an executable test application and therefore deliberately has no library placeholder metadata. Project and object GUIDs remain unchanged. If independent release trains later justify separate gates, split this aggregate into per-library Core and Modules test applications; until then, one aggregate name matches the existing one-gate architecture.

## 31. Contract vocabulary and ownership cleanup (2026-07-12)

Resolved the semantic conflicts found by the whole-standard review. A root Unit tree is one **station**; a PLC/cell scope may host a forest of stations. `FB_ModuleBase` now owns the common PLCopen lifecycle, `FB_CompositeModuleBase` owns recursive child behavior, and the CM/EM/Unit bases are tier wrappers—so Unit no longer inherits an Equipment-Module identity. CM and EM interfaces share `ExecuteCommand`/`AbortCommand`; the duplicate `ST_CmStatus` was removed.

Recipe lookup now uses `(ModelCode, RecipeKey)`, and Unit changeover prepares and validates the complete subtree before commit. The shipping Cylinder and Clamp modules publish physical `ParCfg`/`ParCmd`/`OutCmd`/`OutImm` structures. `FB_BasicCylinder` was renamed `FB_ConfigurableCylinderCM` to express capability and tier. Alarm priority now has one axis, `E_Severity`; the redundant event-kind axis was removed from PLC and HMI. `E_Mode` remains an append-only Core/HMI ordinal contract until a generated identifier mapping replaces ordinals.

The TcUnit runner was also corrected to instantiate every compiled suite; previously nine compiled suites were silently absent from execution. Source/XML/project-list and Flutter gates are rerun after this migration. TwinCAT compilation remains required before declaring the draft binding release-ready.

## 32. First pinned TwinCAT compiler feedback (2026-07-12)

The first build log from TwinCAT 3.1.4024 reduced 514 reported errors to a few parser root causes. Fixed across all projects: TwinCAT does not accept `VAR PROTECTED`; `VAR_TEMP` is not allowed in methods; keywords are case-insensitive and cannot be identifiers (`Action`, `Log`, `Min`, `Max`, `S`, `R`, `DT`); and an apostrophe inside a STRING uses `$'`, not doubled SQL-style quotes. Public timing fields are now `Minimum`/`Maximum`, access arguments use `Gate`, audit locals use `AuditSlot`, and elapsed-time locals use `CurrentTime`/`DeltaMs`. A reserved-keyword scan is now part of the structural gate.

The same log exposed packaging conflicts: the reusable `Fraktal_Modules` library contained `MAIN` and `PlcTask`, and `Fraktal_Tests` contained `PlcTask` while still carrying library placeholder metadata. TwinCAT correctly refused those runtime objects as library content. Demo application objects now live in `Fraktal_Demo`, and the placeholder was removed from the executable test project. The demo hosts two real `FB_ClampStationUnit` roots rather than presenting Equipment Modules as root Units. `Fraktal_Core` and `Fraktal_Modules` are libraries; `Fraktal_Demo` and `Fraktal_Tests` are applications.

## 33. Second pinned TwinCAT compiler feedback (2026-07-12)

The next 4024.12 compile removed the parser cascade and exposed binding-level assumptions. Beckhoff added optional method inputs only in 3.1.4026, so all default-valued method inputs were removed and every 4024 call now supplies every argument. TwinCAT also enforces IEC encapsulation: another POU can access only a function block's `VAR_INPUT`/`VAR_OUTPUT`, not its local `VAR`. The four-structure contract and common published data are now mapped accordingly; private lifecycle state remains local. Test-only mutation of Unit OEE internals was replaced by a probe method, and access-policy setup uses a bounded configuration method.

`I_Module` now extends `__System.IQueryInterface`, satisfying `__QUERYINTERFACE` for Unit capability cascade. `Fraktal_Demo` directly references `Tc3_Module`, resolving the generated task FB's `IecTaskModule`, `S_OK`, and `fb_init` dependencies. The test application remains non-library in the canonical project; any repeated “Object not added to library” message identifies a stale copied `.plcproj`.

## 34. Third pinned TwinCAT compiler feedback (2026-07-12)

The third 4024.12 compile reduced the binding to eleven test-only access errors. A child function block exposed through a parent's `VAR_OUTPUT` is readable, and its public methods are callable, but TwinCAT does not permit a caller to assign that nested child's `VAR_INPUT` through the parent output. Access tests now use `FB_AccessManager.RequestLogin`/`RequestLogout`; the EM and manual-command probes own their fault/abort injection methods. These seams preserve encapsulation and leave the OPC UA request-symbol contract unchanged. Login/logout request bits are now consumed directly and self-cleared; the former `R_TRIG` implementation cleared the bit only after sampling it, so the trigger never observed a low scan and could ignore a consecutive request.

The compile log still referenced a separate copied solution under `FraktalAutomation\FraktalAutomation`. The canonical `Fraktal_Tests.plcproj` has no library placeholder metadata; a repeated “Object not added to library” message for `PlcTask.TcTTO` therefore comes from the stale copied project and requires replacing or refreshing that project in the XAE solution.

## 35. Safety and control-power foundation (2026-07-13)

Added the optional Core §9.8 profile and `SAFETY_AND_CONTROL_POWER_PROFILE.md`. Every module now inherits hidden-by-default `Safety : ST_SafetyStatus` and `ControlPower : ST_ControlPowerStatus` facets. The records cover device kind/state, demand, reset, muting, keyed bridge, affected power groups, group request/feedback, safety permit, fieldbus health/reaction, and deliberate rearm. `POWER_CONTROL=10` was appended to the access-policy ordinal contract; existing ordinals are unchanged.

`FB_PowerGroupCM` is the first basic reusable implementation. It owns an ordinary functional-enable request, never a safety output; it withdraws that request when its safety permit drops or a configured fieldbus-loss reaction requires power removal, latches rearm, and never self-energizes when health returns. Its reserved reason band is 10500–10599. The HMI renders both facets generically and the simulation demonstrates a door, light curtain, safety valve, and two valve-island zones. Certified door locking, muting/override, bridge, FSoE safe output mapping, and risk validation remain in TwinSAFE by design.

The ownership model was corrected before coordinator implementation: safety/control power is an optional cell-scope **control domain**, not inherently Unit-owned. `ST_ControlDomainStatus` carries a stable ID, readiness, safety/power aggregates, and member root paths. `FB_UnitBase.ControlDomain` accepts zero or one domain; several Units may consume the same record. That application-fed input is explicitly excluded from OPC UA. `Start` gates only an assigned domain's `ReadyForStart`; `Present=FALSE` deliberately adds no gate. The Unit republishes read-only `Domain`, `Status.ControlDomainId`, and facet mirrors for discovery. The domain coordinator itself remains deployment/application infrastructure rather than a fourth module tier.

The HMI connection settings schema is now v2. After the endpoint reaches LIVE, the wizard requires a root-Unit assignment. `ScopedPlcRepository` filters discovery and rejects reads/writes outside the saved assignment; legacy v1 settings migrate to an incomplete selection and therefore reopen step 2. Missing paths fail closed. ADMIN can reopen the assignment editor after login.

## 36. Catalog-owned HMI language and module content (2026-07-13)

Operator-facing PLC strings were converted to stable `std.*`/`project.*` localization keys, including command catalogs, diagnostics, interlocks, release reports, steps, audits, hardware, and I/O descriptions. Structured identity/protocol data remains untranslated. `ST_CommandInfo.Label`, timing/step/condition labels, and hardware description fields were widened or added for keys. The HMI now owns runtime standard/project catalogs, first-run language selection, locale switching, validated CSV import/export, module descriptions, PDF upload/viewing, and per-module section access policies. `file_picker`, `pdfrx`, and the Flutter-published `cupertino_icons` asset are the reviewed package exceptions. Local content storage is the shipped commissioning implementation; the `ContentStore` seam is the production shared-store boundary. See `Specification/LOCALIZATION_AND_MODULE_CONTENT.md`.

## 37. Pneumatic press worked application and two contract repairs (2026-07-13)

Added `Fraktal_Press_Demo`, an executable one-root virtual-commissioning application, and reusable
`FB_PneumaticPressUnit` / `FB_TwoHandStartCM` types in `Fraktal_Modules`. Three ordinary cylinder CMs
implement ram, door, and part slide; `FB_PowerGroupCM` supplies the functional pneumatic request. AUTO,
HOME, MANUAL, transactional ALUMINUM/PLASTIC/STEEL recipes, collision prevention, localization keys,
nameplate, alarm rationalization, control-domain facets, and TcUnit coverage use the existing contracts.
The two-hand CM consumes a certified result and only produces a release-before-rearm functional edge;
it explicitly does not calculate simultaneity or anti-tie-down. `E_SafetyDeviceKind.TWO_HAND_CONTROL`
was appended without disturbing existing ordinals.

Building the example exposed two shared seams. First, the HMI already offered Control On/Off but the
PLC had no published write endpoint. `FB_UnitBase` now owns edge-consumed `ReqControlOn/ReqControlOff`,
applies `POWER_CONTROL`, gives Off priority, and publishes one-scan coordinator requests. Power groups
no longer publish equivalent MANUAL commands. Second, cylinder collision rules were previously either
application-only or a generic forced interlock. `FB_CylinderCM.SetDirectionalPermits` now applies exact
extend/retract conditions to typed and manual execution. The manual release query now includes the
command value and delegates to `AppendDirectionalRelease`, so act-or-explain evaluates the same
directional permit as dispatch instead of reporting only the target.

The simulation also moved safe-output filtering to final output authority. Ordinary Unit logic runs
first; simulated certified logic then removes all requests on power loss and independently removes
ram-down without guard plus evaluated two-hand permission. This fixes a one-scan overwrite hazard in
the first draft and documents the required TwinSAFE/FSoE replacement. See
`Specification/Reports/PNEUMATIC_PRESS_EXAMPLE.md`.

## 38. CX2030 training-station physical I/O binding (2026-07-13)

Integrated the supplied `TrainningStation_IOs_V2.xlsx` map into the press application without leaking
terminal details into reusable modules. `GVL_PressIO` declares wildcard process-image symbols for the
EL1809/EL2809 channels; `MAIN` alone maps them into the cylinder, two-hand, power, part-presence, and
air-pressure HALs. The physical feeder retracts inside and extends outside, so that application mapping
deliberately inverts the generic slide position names. AUTO now requires part presence plus the valid
high-air/low-air combination before accepting the evaluated two-hand edge.

Simulation remains the default and explicitly clears every mapped output. Physical mode is fail-closed:
`GVL_PressSafety` input aliases default false until linked to evaluated safety results, and the ambiguous
`SwitchControlOn`/`EnableControlOn` pair remains off until its electrical behavior is confirmed. The
worksheet lists the E-stop and two-hand buttons only on ordinary EL1809 inputs and provides no safe
guard, safe pneumatic output/feedback, or evaluated two-hand result; these channels are therefore raw
diagnostic mirrors, not a safety implementation. It also calls reserved output channel 9 `EL2810`
while the other outputs are `EL2809`, and lists no physical Control On/Off input buttons. These items
are tracked in `Specification/Reports/CX2030_PRESS_IO_MAPPING.md` rather than guessed in code.

## 39. Electrical-tag diagnostic join (2026-07-13)

`ST_Diagnostic` now carries optional `IoTag` and `IoAddress` structured identity. The cylinder CM can
be configured with application sensor/output tags without importing terminal knowledge into reusable
device behavior; its position timeout and sensor-conflict first-outs attach the exact approved tag.
`FB_AlarmLog.RaiseDiag` preserves both fields through the active alarm and closed-event lifecycle;
the ordinary `Raise` API remains source-compatible and supplies empty channel context.
`ST_IoChannel` now separates exact `Name`, localized `DescriptionKey`, physical `Address`, unique
force/audit `Path`, and owning `ModulePath`, plus fault-highlight fields.

The press application publishes its supplied EL1809/EL2809 list as a bounded OPC UA fieldbus table.
The HMI renders tags verbatim, descriptions in the active language, cross-navigates to the module, and
highlights a channel whose tag matches a live first-out. The application publisher currently consumes
the aggregate standard-I/O health alias; it is a label/value adapter, not a replacement for the
deployment-deferred EtherCAT scanner/master diagnostic integration required by Core §10.5.1.

## 40. I/O responsibility distribution made normative (2026-07-13)

The first press fieldbus implementation proved the data contract but placed project metadata, live
process-image copying, topology validation, health propagation, and diagnostic correlation in one
application FB while `MAIN` also performed raw channel mapping. That shape contradicted the intended
“basic reusable mechanism + thin composition” architecture even though it was functionally correct.

Core §10.2.1 now defines mandatory ownership. `FB_IoTopologyPublisher` is reusable infrastructure for
bounded registration, validation, health and exact-tag diagnostic joins over `ST_FieldbusTopology`.
`FB_PressIoCatalog` is static project engineering data and injects `ST_CylinderIoIdentity` role records.
`FB_PressIoDriver` alone accesses `GVL_PressIO`, maps semantic HALs, writes physical outputs and refreshes
live topology values. `FB_PressSimulationDriver`, `FB_PressControlDomain`, and
`FB_PressOutputAuthority` isolate simulation plant behavior, domain aggregation, and final functional
withdrawal respectively. `MAIN` selects paths and orders calls without individual channel assignments
or domain-device construction. The project-specific catalog remains intentionally explicit until
generated from the approved I/O workbook; reusable algorithms no longer live beside those rows.

## 41. Native OPC UA repository and acknowledged HMI mailbox (2026-07-13)

The original connection wizard exposed `opc.tcp` while its external repository
was a throwing placeholder. Windows now builds a native `fraktal_opcua` DLL from
pinned open62541 1.4.12 and Mbed TLS 3.6.6. Dart FFI calls run exclusively in a
worker isolate; a generic flat snapshot mapper discovers modules only through
`Status : ST_ModuleStatus`. Web compiles a client for the same snapshot/write
contract over the versioned Fraktal WebSocket gateway protocol.

The integration audit also exposed that several HMI operations existed only as
IEC methods, which OPC UA cannot call. `FB_UnitBase` now publishes
`ST_HmiRequest`/`ST_HmiResponse`: arguments first, changing Sequence last,
AckSequence last after processing. The base routes supported requests through
the existing gated methods and publishes property-only mode/running/stop state
as data. Type/project-specific configuration writes and fieldbus output force
remain fail-closed override hooks; identity-based alarm shelving is explicitly
refused until its slot-resolution adapter is supplied.

## 42. Explicit press mode sequences and discoverable recipes (2026-07-13)

Pinned TwinCAT feedback found an undefined `_airPressureOk` symbol in the press ram permit; the Unit
now consumes `AirPressureMonitor.OutImm.PressureOk` directly. The review also confirmed a visibility
problem: AUTO and HOME were step-number regions inside one large dispatcher, CHANGEOVER was not
supported, the project recipes were anonymous declarations in `MAIN`, and the native OPC UA mapper
did not project `CurrentStep` or `Decision`. The PLC contained behavior that the real HMI could not
show.

`FB_PneumaticPressUnit` now has a thin `_M_Dispatch` and separately reviewable
`_M_SequenceAuto`, `_M_SequenceHome`, and `_M_SequenceChangeover` methods. CHANGEOVER establishes the
load-safe position and waits for deliberate tooling/material confirmation. `FB_PressRecipeCatalog`
owns the ALUMINUM/PLASTIC/STEEL engineering records and feeds the generic local provider. Units may
publish a bounded available-model catalog; the HMI renders it as a selector, performs the
mode→transactional model→Start flow, and projects live step conditions and decision prompts over the
same generic OPC UA mapper. `_M_TakeDecision` now consumes and clears the answer, preventing a stale
answer from automatically satisfying a later prompt.

## 43. TF6100 filtered root publication fix (2026-07-14)

A live CX2030 trace separated transport failure from address-space failure: TCP port 4840 accepted
the connection, open62541 opened a SecureChannel and activated an anonymous session, TF6100 loaded
`Port_854.tmc` successfully (`loadSymbols ret=0`) and kept ADS health checks alive, but browsing
`Objects` returned only namespace-zero `Server`. The retained rotated importer logs begin midway
through the 18-second import, so they cannot prove whether the earlier direct root record was parsed.

The trace proves the immediate blocker is TF6100 authorization/publication rather than networking:
the anonymous identity is activated but cannot browse the configured PLC Data Access object. Both
executable examples now also mark every root Unit declaration in `MAIN`, making the intended forest
explicit in addition to the then-supported type-level inheritance. Part I, Part II, the transport guide,
and `AGENTS.md` record the rule. The HMI's empty-forest diagnostic names the instance marker, TMC
reload, and OPC UA namespace authorization as distinct checks. The endpoint hostname returned by
`FindServers` was not the cause—the redirected session reached `Activated` before the empty browse.

The audit also corrected an overstatement in `OPCUA_TRANSPORT.md`: username support exists in the
native ABI but is not yet surfaced by connection settings. The current wizard connects anonymously;
persisting a server password in its JSON or sending one over `SecurityPolicy=None` would be an unsafe
shortcut. Temporary anonymous namespace rights are therefore commissioning-only; certificate trust,
secure credential handling, and authenticated least-privilege writes remain the Phase 7 production
security exit gate.

Because the copied server trace was older than the next HMI attempt and the active TF6100 files live
only on the remote PLC, the native snapshot now also reads the standard OPC UA
`Server/NamespaceArray`. An empty-forest error reports those URIs beside `Objects` children: a PLC
namespace present there but absent from `Objects` proves identity permissions are filtering browse;
an absent PLC namespace proves the remote Data Access NodeManager/TMC was not loaded. This diagnostic
is read remotely and does not assume TF6100 is installed on the HMI PC.

The subsequent synchronized client/server capture made the authorization diagnosis conclusive. The
client read `urn:BeckhoffAutomation:Ua:PLC1` from `NamespaceArray`, while the matching TF6100 trace
accepted an `AnonymousIdentityToken` and printed `Roles assigned to session` with no following role
entries. The same session received only `Server` when it browsed `Objects`. The HMI now recognizes
this combination and reports an access-filtering error directly instead of also suggesting a missing
TMC or root publication marker. The remote TF6100 user/group mapping and recursive PLC1 browse/read
rights must be corrected; anonymous access remains commissioning-only.

## 44. Authorized large-tree browse and HMI mailbox starvation fix (2026-07-14)

After assigning the commissioning identity to TF6100's Users role, discovery
advanced to `LIVE` and the HMI rendered `PneumaticPress`. Mode controls still
appeared inert and the Dart debugger repeatedly reported that it was waiting for
the `fraktal-opcua` isolate. This separated a PLC mode/enum problem from a client
scheduling defect: the native snapshot recursively browsed and individually
read up to 20,000 nodes every 500 ms. The single worker isolate therefore spent
nearly all of its time in snapshot FFI; mailbox writes queued behind it, while a
concurrent repository refresh could return early and test stale acknowledgement
data. Depth-first discovery could also consume the cap inside an implementation
subtree before reaching shallow `HmiRequest` leaves.

The native bridge now discovers breadth-first in bounded multi-node Browse
services, caches path-to-NodeId discovery for the session, and reads cached
variables with bounded multi-node Read services. Snapshots report `truncated`.
The Dart repository shares an in-flight refresh instead of skipping it, so a
mailbox request observes fresh acknowledgement data. Request start, individual
write/commit failure, acknowledgement with PLC diagnostic, and timeout are
logged without transported secrets. The request-kind and mode ordinals already
matched the PLC DUTs; no wire-contract ordinal change was required.

The resulting bring-up lessons are consolidated in
`Specification/Guides/FIRST_PROJECT_AGENT_GUIDE.md`, referenced by `AGENTS.md`. Part I
now requires layer-specific client status and acknowledged command success;
Part II records the TF6100 host, authorization, namespace, root, and mailbox
acceptance ladder.

## 45. TF6100 reference aliases projected as duplicate stations (2026-07-14)

The first cached/batched live browse exposed three root projections named
`PneumaticPress`; Flutter's station dropdown correctly asserted because three
items carried the same Fraktal path. The PLC application declares only one root,
but several infrastructure FBs retain `UnitRef` references. TF6100 can expose
those reference/owner paths with the referenced Unit's `Status`, and the flat
mapper previously treated any parentless `Status : ST_ModuleStatus` Unit as a
deployed root.

The first correction compared a candidate's local browse segment with the whole
`Status.Name`. The next live run proved nested modules intentionally publish
qualified identities such as `PneumaticPress.PressRam`, so that comparison
removed every legitimate child while retaining the root. The final mapper
compares the local browse segment with the **final dotted identity segment**,
deduplicates every module by the full `Status.Name`, constructs parentage from
the dotted prefix, and chooses the shallowest OPC UA path for each identity.
`UnitRef`-shaped aliases are discarded; direct children remain. Discarded paths
are logged once per changed alias set. `AppState` also removes duplicate root
paths defensively so an invalid repository payload cannot crash a station
selector. Regression fixtures prove the direct root and qualified child survive
both alias forms. Part I §4.8 and the HMI/transport contracts now state the
local-browse versus qualified-identity distinction explicitly. No
station-specific UI rule was added.

## 46. Login-result feedback and release-query feedback loop (2026-07-14)

Live commissioning exposed two HMI contract errors. First, the Unit mailbox acknowledges LOGIN when
`FB_AccessManager.RequestLogin` queues the attempt; the access provider evaluates it later in the same
PLC scan. Treating `HmiResponse.Accepted` as authentication success therefore displayed a false
success for a bad PIN. The OPC UA repository now uses the post-attempt `Access.LoginFailed`,
`CurrentUser`, and `CurrentLevel` snapshot as the authoritative result. The login dialog remains open,
clears the PIN, and gives localized generic feedback on failure.

Second, `AppState` refreshed an open release panel on every forest snapshot. Each release mailbox query
causes a fresh snapshot, so one rejected Start created an unbounded RELEASE_START loop. The panel now
appears immediately in a checking state, performs one query, and uses a controlled non-overlapping
two-second refresh while open. Empty rejected reports render an explicit publication/contract message.
Regression tests cover mailbox-consumed versus authenticated login, inline failure feedback, immediate
release visibility, and absence of snapshot-driven request recursion. No PLC wire ordinal changed.

## 47. §6.1 reset provenance, post-dispatch stall views, first-connect backoff (2026-07-14)

Running the full TcUnit gate against the live build exposed five Core defects that the press
example depends on; all were fixed at the base so every module type inherits the corrections.

**Execute-drop reset (§6.1) ran after output mapping and consumed non-command faults.**
`FB_ModuleBase.Cyclic` reset a terminal state at the bottom of the scan, so the scan in which
`Execute` dropped still published stale `Done`/`Error`/`Aborted` (T1/T4 red), and any fault raised
OUTSIDE a command — the §3.8 migrate-or-fault at Setup, cyclic condition monitors — was silently
consumed one scan later because `Execute` was low (T5 red). The reset now runs at the TOP of the
scan and is gated on command provenance (`_cmdArmed`, armed at the accepted rising edge): a
command-produced terminal state resets before this scan's mapping; a non-command fault latches. A
fresh command edge may retry from a latched non-command ERROR — the edge clears the diagnostic and
re-runs validation, which re-faults immediately if the cause remains. HOME/AUTO therefore recover a
CM whose idle condition fault has cleared; a bad recipe stays visible until remedied.

**`Starved`/`Blocked` were derived in `OnCyclic`, one scan before dispatch updated the step.**
The §8.11.4(f)/§8.11.3 views are now derived in `FB_UnitBase._M_PublishStatus`, which the base
calls after `_M_Dispatch`, so the wait class reflects the step record set THIS scan.

**`FB_AsciiDeviceCM` delayed the FIRST connect by the retry backoff and rejected same-scan sends.**
The CLOSED branch armed the 500 ms backoff before the first `Open()`, so every request in the
first half-second faulted `DEV_NOT_CONNECTED` (10404) instead of reaching the device — the TcUnit
suites saw exactly that. Backoff now spaces RE-tries only; the first `Open()` is immediate, and
`SendRequest` checks the live channel state instead of the one-scan-old `LinkState` cache.

**`FB_ConfigurableCylinderCM_Tests` looped a TON-based sim inside one scan.** TwinCAT task time is
frozen within a scan, so 20 ms travel/30 ms settle could never elapse; the three time-based tests
now use the standard multi-scan TcUnit pattern (one iteration per cycle, assert + `TEST_FINISHED`
on the terminal state or a 100-scan budget). The sims stay time-based — they are shared with
virtual commissioning (§5.7); `Timeout_faults` (PT=0) was already scan-exact and is unchanged.

## 48. Press example feature completion: run styles, §3.16 traceability, rationalization, users (2026-07-14)

A spec-coverage review of the press example found four normative capabilities the Core already
promised but the example (and in one case the Core) did not exercise.

**Run styles (§3.4.2).** `FB_UnitBase` had the full pacing machinery (`StepRequest`, `SetHoldRun`,
`_M_StepGate`) but no shipped Unit ever declared support. `FB_PneumaticPressUnit` now advertises
SINGLE_STEP and HOLD_TO_RUN and passes every motion boundary in AUTO/HOME/CHANGEOVER through
`_M_StepGate(Steppable := TRUE)` — the step record is set first so the HMI shows where the sequence
is paused. Settle/dwell timers are process steps and are deliberately not gated. CONTINUOUS is the
default; existing tests are unaffected because the gate returns TRUE there.

**Traceability (§3.16).** The contract existed as types only (`I_PartCarrier`, `ST_PartContext`,
reasons 2020–2023) with no implementation, no Unit wiring, and no lifecycle events. Added: the four
`EVENT_PART_*` reason codes (2024–2027, MESSAGE ring entries via the instant come+gone pattern);
`FB_LocalPartCarrier` in `Connectivity/` (BY_POSITION serials from a configured prefix, bounded
produced-results ring — joins the local provider family); `FB_UnitBase` publishes
`Part : ST_PartContext` and gains `SetPartCarrier` plus the protected helpers `_M_PartReceived`,
`_M_PartStarted`, `_M_PartRecord`, `_M_PartProcessed`, `_M_PartAborted`. ERROR entry raises
PROCESSING_ABORTED automatically next to the §8.3 fault capture. The press AUTO chain raises all
four events and records the applied dwell; `MAIN` injects the carrier. With no carrier injected
every helper is a no-op, so traceability stays a selectable feature (§3.9). `FB_PartTrace_Tests`
proves the carrier scan-exactly. The HMI part facet (§3.16.4) is a follow-up — the data is now
published for the generic mapper.

**Rationalization (§8.9) and access (§7.7).** The press registers operator-action/consequence
metadata for its main reasons (interlock, air pressure, recipe, cylinder position timeouts) and a
commissioning user table (operator/tech/admin). `FB_LocalAccessProvider.Register` is now idempotent
by user name — the table is PERSISTENT, so per-boot registration previously duplicated entries.

Deliberately NOT added: CAPABILITY/ADJUSTMENT modes (§3.17 — no press process behind them yet),
signal tower mapping (§8.13 — the training station has no tower and the HMI has no facet), and a
scripted vision/reader child (§3.15.1a — worthwhile, but it needs its own review of the AUTO
chain's quality path: NOK counting, REWORK routing, and the §3.16 verdict source).

## 49. Nexeed reference comparison: sub-sequence extraction and §4.2 folders (2026-07-16)

A Bosch Nexeed reference export (`NexeedReferenceOnly/REF1_Plc.xml`, ~140k lines) was reviewed for
code grouping and distribution. Its architecture maps almost one-to-one onto Fraktal contracts
(the map is recorded in `AGENTS.md`), which validated two things Fraktal already prescribes and
exposed two places the reference implementation did not practice them.

**Adopted 1 — shared sub-sequences (Nexeed `SqS_*` ≈ new `_M_Seq<Name>` methods).** The press
triplicated the ram-up→door-open→slide-outside motion chain across HOME and CHANGEOVER. It is now
ONE reviewable `_M_SeqEstablishLoadPosition(BaseStepNo)` sub-sequence with a private `_seqStep`,
called from both mode chains; the `BaseStepNo` window keeps per-mode step identity for the §6.9 walk
and the §8.11.4 profiler, and the changeover's "repeat position" decision resets the sub-step. The
HOME/CHANGEOVER step labels merged into shared `project.step.pressSafePosition*` keys. Behavior,
scan counts (±1), and the press suite's assertions are unchanged.

**Adopted 2 — §4.2 folder tree in the press application.** The demo was flat; Nexeed's per-location
folders are exactly the spec's instance-tree layout. The project now ships `00_System/` (MAIN, raw
I/O + safety GVLs, hardware driver, domain coordinator, output authority, sim plant) and
`01_PneumaticPress/` (recipe catalog, approved I/O catalog, fieldbus publication GVL); the plcproj
includes were repointed. Library projects keep their artifact-type folders — §4.2 governs
applications, where the instance tree exists.

**Noted, not adopted:** Nexeed's `Unit`+`Extension` pairs and `*Addon` plugins are composition-over-
inheritance seams; Fraktal deliberately uses base-class inheritance + §3.14 hooks + `I_EventSink`
(§2.2 single-sourced lifecycle) — no change. Nexeed models TWO workpiece contexts per station
(`...Wp1/Wp2` part-event addons); Fraktal's Unit publishes one `Part : ST_PartContext`. Multi-
workpiece stations are recorded as an open Part I §3.16 consideration, not silently bolted on.

## 50. Native OPC UA online-change resilience (2026-07-16)

The native client did not survive a TwinCAT PLC online change. Two gaps, both in
`fraktal_opcua_bridge.cpp`:

The discovery cache was permanent — `discoveryComplete` was set once after the
first browse and never invalidated except on a full connect/disconnect. So an
online change that added/removed/renamed symbols or shifted NodeIds was never
re-read: new symbols stayed invisible, removed ones lingered, and writes could
land on stale NodeIds. Reads of gone NodeIds were silently dropped (filtered on
`status != GOOD`), hiding the structural change.

There was also no reconnect path. A PLC online change usually reloads the TF6100
namespace and tears the OPC UA session down, and open62541 only auto-reconnects
when its event loop is pumped — this client is driven by explicit service calls.
So a dropped session left the HMI in `STALE`/`DOWN` indefinitely.

Fix (fully native; the Dart repository already marks link `STALE`/`DOWN` on
snapshot failure and returns to `LIVE` when snapshots succeed again, so no Dart
change was needed): `connect` now caches the endpoint/credentials; a `reconnect`
helper re-establishes the session with them and always clears the NodeId map;
`ensureSession` checks the live `UA_Client_getState` (connect status + activated
session) before every snapshot and reconnects when it degraded — making session
loss transparent. Reads count NodeIds that no longer resolve
(`BadNodeIdUnknown`/`BadNodeIdInvalid`); a surge (>=20% of cached variables)
invalidates the cache so the next snapshot re-browses the fresh structure. Any
service-level read failure reconnects and returns no document rather than a
stale/empty tree. Writes during the reconnect window are rejected, not queued
(§14); reconnect attempts are self-throttled by the connect timeout and the
shared in-flight refresh. `OPCUA_TRANSPORT.md` documents the contract.

## 51. Mode-change default is immediate abort, not graceful (§3.14.4) (2026-07-16)

`Unit_mode_change_is_estop_by_default` was the last red gate (64/65). Root cause: `_M_InitModePolicy`
defaulted `E_ModeSwitchStyle` to GRACEFUL (loop default and AUTO), so a mode change requested while a
sequence ran set `_stopReq` and waited for the cycle to finish. A stalled cycle (the probe waiting on
SimA/SimB) never finishes, so the Unit stayed BUSY and the mode never committed — the opposite of the
test's premise and of spec §3.14.4: "By framework default, a mode change performs an immediate software
abort." GRACEFUL completion is the opt-in (a Unit overrides OnModeExit to stop-after-cycle, or station
config sets Style := GRACEFUL for a mode).

Fix: the framework default Style is now IMMEDIATE for every mode (the OnCyclic mode block then calls
OnAbort on a BUSY mode change, completing the abort→Execute-drop reset→commit sequence in three scans).
Shield defaults are unchanged (CONFIRM, with CHANGEOVER/CALIBRATION BLOCKED_WHILE_RUNNING and
HOME/MANUAL INTERRUPTIBLE). No test or Unit opted into GRACEFUL, so nothing else moved. This is purely
a framework-default alignment to the spec; a station that wants finish-before-switch still gets it via
ModePolicy station config (§3.8a) or an OnModeExit override.

## 52. §8.11 cycle-time capture completed + HMI cycle-time analysis charts (2026-07-16)

Audit verdict: §8.11.4(a)/(b)/(e)/(f) were fully implemented (command timing in the module base,
the step-fed profiler with time classes, fixed arrays, Starved/Blocked derivation); the HMI had a
waterfall and step Pareto. Missing: §8.11.1 throughput markers, §8.11.2 verdict-driven counts and
ReworkCount, §8.11.3 machine-state classification, §8.11.4(c) guard-vs-actual and command-timing
drill-through in the HMI, §8.11.4(d) degradation events, and any per-model ideal cycle in the press.

**Core.** `FB_CycleProfiler` now publishes `LastCycleTime`/`MinCycleTime` (§8.11.1) and a bounded
`History` ring of `ST_CycleSummary` (per-cycle work/wait-class totals — the data that EXPLAINS a
cycle-time increase), plus a WORK-time degradation watch: `BaselineWorkMs`/`DegradedBandPct` with a
one-shot `DegradedTrig` per excursion; `FB_UnitBase` turns the trigger into a Low maintenance event
(`CYCLE_TIME_DEGRADED`, §8.11.4(d)) via the new `_M_RaiseMaintenance`. `ST_StepTiming` carries the
step's declared `Expected` guard so the HMI can draw guard-vs-actual (§8.11.4(c)); `_M_SetStep`
forwards it. `FB_UnitBase` adds `ReworkCount`+`CountRework`, `NokReason`, and `MachineState`
(new `E_MachineState`, §8.11.3 classification each scan: DOWN > CHANGEOVER > BLOCKED/STARVED >
PRODUCING > STOPPED > IDLE). §8.11.2 counters now increment inside `_M_PartProcessed` from the part
verdict (single source; an NOK stores its first-out reason). The public Count* methods remain for
carrier-less applications.

**Press.** `ST_PneumaticPressParCfg` v2 adds `IdealCycleMs` (OEE Performance denominator, §8.5.1)
and `BaselineWorkMs`; `CommitRecipe` forwards both, so the references follow the model. The catalog
carries per-model design cycles (5.7–6.8 s). The AUTO finish step now counts through the part
verdict; direct `CountGood()` remains only as the no-carrier fallback.

**HMI (user-requested: extensive cycle-time cause analysis).** New `cycle_trend_view.dart`:
`CycleTrendView` — stacked per-cycle columns split by time class with the MinCycleTime dashed
reference, hover/tap tooltip, dimming, and a legend (a grown green share = the process slowed; a
grown wait share NAMES the external cause), and `CommandTimingView` — the §8.11.4(c) drill-through
table (Count/Last/Min/Avg/Max + bar with Max marker) rendered per child module. The waterfall now
draws the Expected guard tick and outlines overruns in the error color. Unit chips add machine
state, rework, and last/best cycle time. The mapper projects `Profiler/LastCycle|StepStats|History|
LastCycleTime|MinCycleTime`, module `Timing/Rows`, `MachineState`, `ReworkCount`. The analysis
chain reads: trend (why did it move) -> waterfall (which step) -> Pareto (which step, over time) ->
command timing (which module command). Time-class palette re-validated with the dataviz six-checks
(blocked purple -> #AD1457 magenta, external teal -> #0097A7); identity is never color-alone (direct
labels + tables). `flutter analyze`/`flutter test` green; sim repository extended so the demo shows
a work-drift plus one starved excursion.

`FB_Timing_Tests` extends to the new markers/ring and the published Expected guard.

## 53. Ownership/sequence/release refinement from the Nexeed comparison (2026-07-16)

The deeper review of `NexeedReferenceOnly/REF1_Plc.xml` separated reusable architecture ideas from
vendor-specific implementation form. Part I §4.2 now makes ownership primary and distinguishes an
application instance tree from a reusable type library. §6.7 defines three chain roles—Unit mode,
module command, and owner-private sub-sequence—with one owner/step writer, an acyclic call graph, a
promotion rule to EM, and a requirement that private-chain progress stay in the caller's step record.
§7.2.1/§7.8 preserve condition provenance through common + mode/function-specific layering and keep
future step waits out of the Start frontier. The non-normative decision record is
`Specification/Reports/NEXEED_REFERENCE_INSIGHTS.md`.

One Core defect became visible under that rule: `ReleaseReportStart()` appended a concrete Unit's
`_M_AppendInterlocks`, while `Start()` independently checked only framework state. A Unit could thus
tell the HMI it was blocked and still start. `Start()` now performs the audited access check and then
consumes the report's authoritative `Released` value. Core conformance row T10 and
`FB_Release_Tests.Start_gate_matches_release_report` lock that equivalence.
`ST_ReleaseReason` also now carries the qualified owning `SourcePath`; `FB_PermIntlk`, framework
reasons, and directional cylinder releases populate it, and the HMI shows the owner plus numeric
reason. Aggregated same-text child conditions are therefore no longer ambiguous.

The press demonstrates the result. Its operating-air condition is an owner-local `FB_PermIntlk`
mode-entry record, appended by `_M_AppendInterlocks`; low air is both reported and enforced. Part
presence/two-hand remain AUTO step-100 waits. AUTO's duplicated return-to-load-position steps were
replaced by the same `_M_SeqEstablishLoadPosition` already used by HOME/CHANGEOVER, preserving the
230–280 step window and traceability record. Application engineering data is further grouped into
`01_PneumaticPress/Recipes` and `01_PneumaticPress/Io`. Published PLC instance names and OPC UA paths
did not change.

Deliberately not adopted: Nexeed Unit+Extension duplication, per-step wrappers, opaque summed release
booleans, direct raw-global coupling, PLC-authored HMI visibility, and ordinary-PLC safety
bridge/muting authority. Those conflict with Fraktal O1/O3/O7 and remain owned by base hooks, condition
records, the generic HMI, and certified safety respectively.

## 54. Compile-driven profiler ownership and TF6100 pointer exclusion (2026-07-16)

The pinned 4024 compiler rejected `Profiler.BaselineWorkMs := ...` in
`FB_PneumaticPressUnit.CommitRecipe`: `BaselineWorkMs` is a published output of the child
`FB_CycleProfiler`, not an assignable input. This is the same nested-FB ownership rule recorded in
Part II §3.3. `FB_CycleProfiler.M_SetBaselineWork(WorkMs)` now owns the mutation and rearms the
degradation excursion latch; the press recipe commit calls that API. The press TcUnit suite gives
the fast/slow records distinct baselines and asserts that each transactional model commit updates
the published profiler reference.

TF6100 also reported `RecipeCatalog.Provider._ptr` as unsupported `UXINT`. Skipping the pointer leaf
did not break discovery, but publishing provider storage was unnecessary and noisy. The provider
instance and its `PVOID` array now explicitly opt out with `OPC.UA.DA := 0`; neither is HMI contract
data. `TwinCAT_SystemInfoVarList._AppInfo.TComSrvPtr` is Beckhoff-owned system metadata and remains a
benign skipped leaf if the server scans that namespace. Part II §3.10 and the commissioning guides
now distinguish an application-owned exclusion defect from that system diagnostic.

## 55. Pinned `0.1.0.1` build set after unresolved Modules cascade (2026-07-16)

A dependent-build report contained more than 500 errors in `Fraktal_Press_Demo` and
`Fraktal_Tests`, but no error row owned by `Fraktal_Core` or `Fraktal_Modules`. The first errors were
unknown `FB_PneumaticPressUnit`, `FB_CylinderCM`, `ST_CylinderHal`, and every other Modules-owned
type; all invalid members/calls and even "type X is not equal to type X" were downstream compiler
recovery noise. The applications were resolving a missing/stale Modules artifact through `*`.

All five projects now identify the source set as `0.1.0.1`. `Fraktal_Modules` pins
`Fraktal_Core, 0.1.0.1`; Demo, Press Demo, and Tests pin both Core and Modules `0.1.0.1`. This makes
the required install order explicit and prevents XAE from silently selecting an older local-library
revision. The recovery is: build/install Core, resolve/build/install Modules, reload application
placeholders, then build applications. No individual Press/Test POU change is justified until that
dependency gate is green.

This section records the then-current recovery. Section 58 supersedes the current pin for Modules
(`0.1.0.2`) and makes `FB_PressDemoUnit` application-owned rather than a Modules-owned type.

## 56. Runtime stack overflow: release reports changed to in-place fill (2026-07-16)

Activating `Fraktal_Tests` exposed a PLC task stack overflow. The first runtime fault named the Tests
application/`PlcTask`; TwinCAT's later PREOP→OP and ADS 1804 messages were fallout from the crashed
PLC server. The immediate regression was the T10 Start change: `Start()` held an
`ST_ReleaseReport`, called `ReleaseReportStart()` whose implementation held another report, and
received the roughly 12.5 KiB record by value. TwinCAT 4024 can materialize additional return and
assignment temporaries, exhausting a bounded task stack.

`ReleaseReportStart`, `ReleaseReportManual`, and `ReleaseReportAction` now fill caller-owned
`VAR_IN_OUT Report` storage and return only the `Released` Boolean. `Start()` builds directly into
the already-published `HmiResponse.Report`; the mailbox and TcUnit callers also use in-place fill.
This preserves the authoritative gate/report predicate and wire data while removing the large nested
stack copies. The TC3 binding and agent guide now prohibit large contract returns by value.

Separately, `Fraktal_Tests` is an executable validation application but not a deployable machine
application. It may run manually on an isolated test runtime or CI worker; Autostart Boot Project
shall remain disabled. If mistakenly booted, recover in Config mode and remove/disable the Tests boot
project before returning the actual machine application to Run.

## 57. Press mode chains converted from ST token ownership to native SFC+ST (2026-07-16)

The press already had explicit HOME, CHANGEOVER, and AUTO behavior, but all three mode tokens lived in
`CASE _step OF` ST chains. Core §5.5/§6.2/§6.8 permits that representation, yet names SFC as the
default/recommended representation for multi-step machine sequences. The reference application should
demonstrate the default, not only the permitted fallback.

`FB_PressDemoHomeSfc`, `FB_PressDemoChangeoverSfc`, and `FB_PressDemoAutoSfc` own native TwinCAT SFC tokens.
Their non-stored ST actions publish `ActiveStep`; `FB_PressDemoUnit._M_Sequence*` remains the ST
Fraktal action adapter that populates `_M_SetStep`/`_M_Await`, drives child PLCopen handshakes, records
traceability, and invokes inherited completion/fault handling. The Unit's `_step` now selects only the
base lifecycle reset/run phases, not individual production transitions. Each reset is asserted and the
chart is called once before `M_Run` clears `SFCReset`, avoiding a reset flag that is set and cleared
without ever being consumed by the SFC runtime.

The reused ram-up/door-open/slide-outside chain remains the single private ST
`_M_SeqEstablishLoadPosition` sub-sequence, invoked as one composite SFC step with a caller-supplied
step-number window. This preserves one implementation across HOME, CHANGEOVER, and AUTO while retaining
detailed HMI progress. `Examples/Fraktal_Press_Demo/01_PneumaticPress/Sequences/New-PressModeSfc.ps1`
deterministically regenerates the native TwinCAT
SFC XmlArchive files; static validation checks XML, archive IDs, step/action links, and project includes.
The next pinned-XAE build remains the authority for editor/compiler acceptance of the generated graphical
archives because this workstation does not have the TwinCAT XAE compiler installed.

## 58. Concrete Unit sequences and release policy moved to the application branch (2026-07-16)

The first SFC conversion incorrectly compiled the press Unit and its HOME/AUTO/CHANGEOVER charts into
`Fraktal_Modules`. That made station behavior look reusable and hid the normal project extension point.
The Nexeed reference and Core §4.2 both point to ownership-first application engineering instead.

`FB_PressDemoUnit`, its three native SFCs, their deterministic generator, and
`FB_PressDemoRelease` now live under `Examples/Fraktal_Press_Demo/01_PneumaticPress`. The Release component
contains the project cross-device collision rules, named mode-entry condition state, and Start/manual
report appenders. Reusable `FB_CylinderCM`, input, two-hand, pressure, and power-group mechanisms stay
in `Fraktal_Modules`; that library no longer compiles or exports the press Unit or its SFCs. The
aggregate test project links the deployed project sources rather than copying them.

Removing the application Unit from the reusable library is a breaking library-surface correction, so
`Fraktal_Modules` advances to `0.1.0.2`; application/test placeholders are pinned to that version.

## 59. Press physical XTI reconciled into declarative I/O links and HAL (2026-07-16)

The supplied `=000+S-A610-A1 (EtherCAT).xti` is preserved under the press application's
`00_System/Hardware` folder. It establishes the deployed order and names as EK1200-5000 coupler,
EL1809 inputs, EL2809 outputs, EL6001 RS232, and EL9011 end terminal. It also resolves the worksheet's
EL2810/EL2809 ambiguity: the installed output terminal is EL2809 and its channel 9 is Reserve.

Every one of the 23 active `GVL_PressIO` Boolean process-image symbols now carries a `TcLinkTo`
attribute with the exact XTI box, physical channel, and PDO-entry name. Wildcard `%I*`/`%Q*` storage
remains intentional; the declarative link, not a guessed byte offset, owns the physical association.
`FB_PressIoDriver` remains the sole process-image consumer and maps those raw values to the project HAL.
The fieldbus catalog now publishes all five EtherCAT boxes below the CX2030/master node and uses the
exact box/channel address for diagnostic joins. The EL6001 has no HAL consumer because no serial device
or protocol was supplied; inventing one would violate the project-HAL boundary.

The XTI contains System Manager hardware configuration, not PLC application configuration. A deployer
must import it under the XAE solution's I/O Devices tree, preserve the box names, build to resolve all
23 links, activate the configuration, and complete dry-I/O validation. The ordinary EL1809 E-stop and
two-hand signals remain diagnostic/function inputs only. The fail-closed `GVL_PressSafety` aliases still
require evaluated results from TwinSAFE or another validated safety system, and the two control-coil
outputs remain disabled until their electrical sequencing is independently confirmed. The application
version advances to `0.1.0.3` for this physical-deployment mapping.

## 60. Press SFC actions now own their actual step logic (2026-07-16)

Section 57's first SFC conversion made the chart the sole token owner but left every generated action as
only `ActiveStep := N`; `FB_PressDemoUnit._M_Sequence*` still selected and executed the whole chain through
`CASE ActiveStep OF`. That avoided two competing tokens but failed the more important reviewability intent
of the SFC default: an engineer opening a step could not see what that step actually did. This section
supersedes that distribution.

`FB_PressDemoHomeSfc`, `FB_PressDemoChangeoverSfc`, `FB_PressDemoAutoSfc`, and the shared
`FB_PressDemoLoadPositionSfc` now contain the real application behavior in each named action: Fraktal
step/condition records, child PLCopen command/wait,
timers, decisions, traceability/result work, and a step-local transition Boolean. Exit actions clear each
step's transition latch, preventing a completed predecessor from skipping a newly active step. The Unit's
three `_M_Sequence*` methods now contain only the inherited lifecycle's reset/run handshake and no
`ActiveStep` selector or production-state `CASE`.

The project-private `I_PressDemoSequenceHost` bridges only protected Unit services that a separate SFC POU
cannot call directly. The SFCs receive owner-bound references to the child FBs and contract records during
`Setup`, so their actions visibly issue the child commands without illegally writing through the parent's
published child output. Those aliases and the SFC instances opt out of TF6100 publication. The coherent
ram-up/door-open/slide-outside operation is now the shared `FB_PressDemoLoadPositionSfc`, invoked as an
explicit composite parent step. Its own named actions contain the three child command/wait pairs, and its
caller-supplied step-number window projects detailed progress through the normal Fraktal step record. No
project mode or shared motion chain remains an ST state machine; the generator deterministically emits the
complete step-owned SFC set.

Core §5.5/§6.8, Part II TC3 §3.5, the Nexeed insight note, the press documentation, and `AGENTS.md` now
state that a token-only SFC plus external `CASE ActiveStep` is not a conforming claimed SFC implementation.
The press application advances to `0.1.0.4`; the aggregate Tests project advances to `0.1.0.3` because it
links the changed application sequence interface and charts.

## 61. Core FB_SequenceBase: the provided step-chain base + shared transition result (2026-07-17)

Section 60 made every press SFC action own its real step logic, but each generated chart still carried
its own host-interface copy, eleven per-step transition Booleans, per-step exit actions, and one
`I_PressDemoSequenceHost` that existed only because the framework had no sequence base. The Nexeed
reference does this once in `OpconSfcChain` (`_retVal := OK` + `ExecuteUnit(...)`), and Part I §6.8(a)
already PROMISED a provided shared step-chain base. This section delivers it.

Core additions: `E_StepResult` (NONE/ADVANCE/JUMP1..3 — the Fraktal spelling of Nexeed's OK/JUMPx,
integrated with §6.10 branch rules), `I_SequenceHost` (the once-per-framework bridge to protected Unit
services; `FB_UnitBase` implements it, replacing the press-private interface verbatim, plus
`M_SequenceStopPending`/`M_SequenceStopNow`), and `FB_SequenceBase`: `M_Attach`, `M_Step` (step record +
ActiveStep mirror), `M_Await`, `M_Gate`, `M_TryIssue` (one-shot gated issue latch — the §6.1 issue/await
pair collapses into ONE reviewable step; the child's typed Command/Execute stays visible in the action),
`M_Delay` (declared process waits), part/decision/completion/fault forwards, and the shared
`_retVal : E_StepResult` transition with `M_ClearTransition()` as the single shared exit action.
Charts now declare zero transition variables and one transition expression
(`_retVal = E_StepResult.ADVANCE`); a completed predecessor cannot skip a fresh step because the exit
action clears the shared result (same guarantee §60's per-step Booleans provided, at 1/N the state).

Stop honesty fix: AUTO's between-cycles wait previously rode out a full phantom cycle when Stop arrived
while waiting for a part. The wait step now polls `M_StopPending()` and calls `M_StopNow()`, which
abandons the OPEN profiler cycle via the new `FB_CycleProfiler.CycleAbandon()` (a wait-only fragment
is not a production cycle — it would poison MinCycleTime and the trend) and completes the chain.

The press generator now emits charts that EXTEND the base: issue+await merged into single drive steps
(LoadPosition 7→4 steps, AUTO 17→12), the private host interface deleted from the project and the
aggregate tests, and the Unit's Setup passes `THIS^` as `I_SequenceHost`. Generator self-checks verify
`EXTENDS FB_SequenceBase`, genuine step logic, and the `M_ClearTransition` exit per step. Step numbers
keep their §6.5 spacing; step-name keys unchanged except the merged drive steps
(`pressRamUp`/`pressDoorOpen`/`pressSlideInside`/`pressDoorClose`/`pressRamDown`).

Declined from Nexeed, deliberately: raw `BinIo` access inside sequence actions (violates §10.2.1 —
Fraktal actions still drive children only through the §6.1 handshake), `OpconSetTimeout/CheckTimeout`
step pairs (Fraktal timeouts live in the module's ParCfg per §6.1, and stall detection is the §6.9
walk), and per-step `IndexInfoLine` enum juggling (the step record + condition records already name the
wait for the HMI, localized).

Fraktal_Core advances to 0.1.0.2 (new public base + interface + enum; UnitBase implements
I_SequenceHost). The press application and aggregate tests re-pin accordingly.

## 62. Aggregate test manifest moved to the PLC common ancestor (2026-07-17)

The `0.1.0.4` aggregate project linked the deployed Press Demo Unit, release evaluator, and four SFCs
from a sibling directory with raw `Compile Include="..\Fraktal_Press_Demo\..."` paths. Although each
entry supplied a valid virtual `Link`, TwinCAT XAE's **PLC → Add Existing Item** importer inspected the
raw path first, attempted to create a project-tree folder named `..`, and stopped with
"'..' is not a valid folder name." The XML was valid MSBuild but not importable by TwinCAT.

`Fraktal_Tests.plcproj` lives at the nearest common ancestor of
`Tests/Fraktal_Tests/` and `Examples/Fraktal_Press_Demo/` (currently `TwinCAT/`). All compiled objects use downward repository-relative
paths; the Press sources remain single-source links and are not copied into the test directory. The
nested `Fraktal_Tests/Fraktal_Tests.plcproj` is removed so there is only one selectable manifest.
The aggregate test application advances to `0.1.0.5`; no PLC runtime contract changed.

During the same import audit, `FB_SequenceBase.M_TryIssue` was found with a default-valued method input.
That optional-input syntax is a TwinCAT 3.1.4026+ feature and violates the pinned 4024 binding rule.
The default was removed; every generated press action already supplies `Steppable := TRUE` explicitly,
so behavior and the effective call contract are unchanged.

## 63. Generated SFC charts: arity + optional-input fixes; IecSfc is NOT a dependency (2026-07-17)

The first pinned-XAE compile of the externally generated press charts produced 254 primary
`Unknown type: 'SFCStepType'` messages followed by hundreds of `.x`/`._x`/`.t`/`._t`, assignment, and
transition-BOOL errors. An interim change (from an external agent) added an
`IecSfc, 3.4.2.0 (System)` placeholder to the Press Demo and aggregate Tests manifests on the theory
that the SFC system library was missing. **That diagnosis was wrong and the reference was removed.**
Native TwinCAT SFC support is provided by the compiler for any POU whose implementation is an `<SFC>`
body; it needs no `.plcproj` library reference. The `IecSfc` string that appears in a generated chart
is the SFC `ObjectProperties` **title block** every chart carries — object structure, not a project
dependency. An `SFCStepType` cascade on a generated chart means that POU's SFC
`ObjectProperties`/`XmlArchive` block is malformed (regenerate it); it is not a missing library. The SFC
layer is Fraktal Core's own `FB_SequenceBase` plus native chart bodies — there is no external SFC base.

Two errors in that build were real and their fixes are kept:
- `FB_PressDemoLoadPositionSfc.M_Reset` requires `BaseStepNo`, while the shared generated restart branch
  called it with no inputs. The generator now preserves and passes `_baseStepNo` on that branch; the
  other three charts keep their zero-input reset.
- `FB_SequenceBase.M_TryIssue` had a default-valued method input (`Steppable : BOOL := TRUE`). Optional
  method inputs are a TwinCAT 3.1.4026+ feature and violate the pinned 4024 binding rule. The default was
  removed; every generated press action already passes `Steppable := TRUE` explicitly, so the call
  contract is unchanged.

The same build reported duplicate GUID warnings for Core interface methods. Those arise when a solution
loads the Core source project while an application in that solution also consumes the installed Core
library. Source object GUIDs shall not be randomized to hide the duplicate. Build/install libraries in
a library solution, then unload/remove those source projects (or use a separate application solution)
before compiling consumers.

## 64. Press sequences converted from unparseable native-SFC XML to the ST skeleton (2026-07-18)

Sections 57-63 rebuilt the press mode sequences as "native TwinCAT SFC" via a PowerShell generator that
hand-emitted the SFC `XmlArchive`. That was the wrong call: TwinCAT's SFC serialization is a proprietary
format whose step/transition WIRING (connection graph + layout) the compiler needs to synthesize the
implicit `SFCStepType` and its `.x`/`._x`/`.t` members. The generator emitted step and transition
ELEMENTS but zero connection elements, so a pinned-XAE build produced hundreds of
`Unknown type: 'SFCStepType'` + `'Nxxx._t' is no valid assignment target` errors. This is not fixable by
editing the blob (the format is not documented or reliably hand-authorable), and it was never an `IecSfc`
library problem (see §63 — that reference was a wrong diagnosis and was removed).

Resolution, per Core §6.8 (an ST `CASE StepNo OF` skeleton is a first-class equivalent to native SFC with
identical diagnostics): the four sequences are now plain ST on the SAME `FB_SequenceBase`. Everything the
base contributes is retained — `M_Step`, `M_Await`, `M_Gate`, one-shot `M_TryIssue`, `M_Delay`, the
part/decision/completion forwards, `I_SequenceHost` (still implemented once in `FB_UnitBase`), the shared
`_retVal : E_StepResult`, `CycleAbandon`, and the between-cycles `M_StopNow`. Two base additions make the
pure-ST body work: the `_step` token moved into the base, and `M_Advance(OnAdvance, OnJump1..3)` commits
`_retVal` at the end of each `CASE` branch — advancing to the mapped step and clearing the step-scoped
latches (the guarantee the SFC exit action gave). The generator, the four `*Sfc.TcPOU` files, and the
`SFCReset` two-scan reset handshake are gone; the files are `FB_PressDemoAuto/Home/Changeover/LoadPosition`
and the Unit adapters do a plain reset-then-run. HOME/CHANGEOVER Setup signatures narrowed to the children
they actually use. `M_TryIssue`'s `Steppable` input carries no default (4024 rule). Both manifests and all
four POUs parse; every `M_*` call resolves against the base.

Native graphical SFC remains a permitted §6.8 option, but only when drawn in the XAE SFC editor — a
machine-generated chart is prohibited. Part I §6.8, Part II TC3 §3.5, AGENTS.md, and the press README now
say the shipped reference is the ST skeleton on `FB_SequenceBase`, not a generated chart.

## 65. Headless Windows/Linux Web gateway delivered (2026-07-21)

The browser client and `fraktal.opcua.gateway.v1` contract existed, but the
gateway process itself was deployment-deferred. A standalone Dart AOT service
now owns one isolate-backed native OPC UA session and serves the exact snapshot
and typed-write protocol over WebSocket. It validates protocol/id/type/value
shape and request size, enforces browser origin policy, and restricts writes to
configured root Unit `HmiRequest` subtrees (read-only by default, with an
explicit all-root commissioning override). It globally serializes writes and
never retries them. Socket tests use an injected fake OPC
UA session and prove snapshot parity, serialization, scope refusal, version
refusal, and origin enforcement.

The OPC UA client moved into a local headless Dart package shared by the Flutter
HMI and gateway. This keeps Flutter/PDF plugin build hooks out of the service
AOT artifact. The native bridge is now a portable CMake subproject: Windows
produces `fraktal_opcua.dll`; Linux produces `libfraktal_opcua.so`, both from
the same pinned open62541/Mbed TLS sources. One cross-platform build tool emits
the matching executable, native library, launch helper, and Linux systemd
template.

The service deliberately binds only to loopback. Same-host Chrome is the local
commissioning profile. Remote Web HMI traffic shall pass through an
authenticated TLS reverse proxy on the gateway host; exact Origin checking is
retained as a second boundary and is not treated as authentication. This avoids
persisting a parallel gateway secret in browser settings. The OPC UA
commissioning endpoint observed here still selects anonymous
`SecurityPolicy=None`; production certificate trust and authenticated encrypted
TF6100 remain the existing Phase 7 exit gate.

## 66. Explicit OPC UA security profiles and native gateway transport (2026-07-21)

Section 65 delivered the transport but left its production OPC UA identity as
an exit gate. The shared C ABI now accepts an explicit security profile,
security-policy URI, certificate/private-key pair, client ApplicationURI,
optional encrypted-key password, server/CA trust list, and optional CRLs.
Secure profiles configure open62541 for
`SignAndEncrypt`; session recovery reuses the same configuration and never
downgrades. Production additionally requires a dedicated TF6100 username and
password supplied through the service environment. Private-key input bytes and
cached passwords are cleared when their lifetime ends.

The gateway defines four auditable profiles: `production` (the fail-closed
default), `secure-anonymous`, time-limited `commissioning-anonymous`, and
explicit permanent `isolated-anonymous`. The last profile exists for a single
physically isolated/unrouted old-school PLC/HMI cell; it is not considered
equivalent to production security. Both None/Anonymous profiles print a loud
startup warning, and the commissioning form auto-stops after a bounded TTL.
There is no automatic fallback between profiles.

The HMI's native platform adapter now implements the same `ws`/`wss` gateway
protocol as Web, using the platform TLS trust store. Thus a Windows/Linux/Android
HMI can use the secured gateway path without packaging the OPC UA private key or
PLC credential into the operator application. A device may authenticate to the
WSS reverse proxy with an environment-provisioned mTLS identity or bearer token;
these are accepted only over WSS and are not stored in HMI settings. Direct Windows `opc.tcp` remains
as a logged Anonymous/None commissioning/troubleshooting/isolated exception.
The Windows wrapper and hardened Linux systemd template default to production
and accept provisioned security material; remote WSS authentication remains the
same-host reverse proxy's deployment responsibility.

## 67. TF6100 publication-root and bounded-topology repair (2026-07-21)

A live local TF6100 snapshot reached the native 20,000-node guardrail with
`truncated=true`: 6,876 scalar values were below `_unit` aliases and 75 below
`_hal` aliases. This was finite breadth-first expansion, not an IEC recursive
datatype or an infinite client loop. Definition-level `DA=1` markers made every
instance eligible for publication, while persistent implementation references
allowed TF6100 to project the same Unit/HAL graph through infrastructure paths.

Publication now starts only at explicit deployed root Unit instances and
standalone data variables. Core/Modules FB type markers were removed; every
persistent pointer, interface, and `REFERENCE TO` implementation field carries
an immediate `DA=0`. The Press topology marker moved from the GVL header to the
`Topology` variable itself, matching TF6100 attribute placement. Core is
`0.1.0.4`, Modules is `0.1.0.3`, and downstream applications are repinned. The
source audit `PLC/TwinCAT/Tests/tools/Test-OpcUaPublication.ps1` prevents reintroduction.

The fieldbus contract remains a bounded flat IEC table, but a naive OPC UA walk
would expand all 64 x 16 fixed slots. Native discovery now reads `NodeCount` and
each active `ChannelCount` before enqueueing array elements, so unused slots do
not consume the snapshot budget. The HMI repository and Web gateway share a
fail-closed completeness validator: a truncated snapshot is never mapped or
reported ready, and gateway `/readyz` remains degraded. Increasing the node cap
alone is explicitly not an acceptance fix.

## 68. Config manifest: activation-static data obscured from OPC UA, served via QUERY_CONFIG (2026-07-22)

A live browse of the deployed press demo measured ~33.7k published value nodes,
~two-thirds of them activation-static identity (fieldbus tags/wiring, command
catalogs, model lists, mode policy, nameplate, alarm rationalization) re-read by
every client refresh and each costing the server an ADS handle
(`GetHandlesByNameViaSumReq ... 0x710` floods during handle-pool growth). Core
now excludes those members from the cyclic tree with `OPC.UA.DA := '0'` and
serves them on demand through the existing request mailbox (Core §3.10.2):

- `E_HmiRequestKind.QUERY_CONFIG := 23` (append-only ordinal contract);
  `ST_HmiResponse.ConfigPage : ST_ConfigPage` — a bounded window of
  `{Scope, Item, ValueText}` entries (`PL_Fraktal.MAX_CONFIG_PAGE := 16`).
- `I_ConfigSource.M_AppendConfig(Pager)` — implemented once in `FB_ModuleBase`
  (catalog), recursed over children by `FB_CompositeModuleBase` via
  `__QUERYINTERFACE`, extended by `FB_UnitBase` (models, mode policy). Projects
  append project-owned data: `FB_PressDemoUnit` exports
  `GVL_PressFieldbus.Topology` identity via the reusable
  `F_AppendTopologyConfig`. `FB_ConfigPager` counts the deterministic walk and
  stores only the requested window — no full manifest buffer exists in PLC
  memory; the walk order alone defines the paging.
- `FB_UnitBase.ConfigRev : UDINT` is seeded `DT_TO_UDINT(F_Now())` in `OnInit`
  (a plain counter would repeat after reboot and leave an HMI holding a stale
  manifest undetected) and incremented on accepted `WRITE_CONFIG`, `SetModel`,
  and `RegisterAvailableModel`.
- Obscured members: `FB_ModuleBase` Nameplate/Catalog/CatalogCount;
  `FB_UnitBase` AvailableModels(+Count)/ModePolicy/StallTime; `FB_AlarmLog`
  Meta/MetaCount; `ST_BusNode` and `ST_IoChannel` identity members (live
  State/LinkOk/values/Forced/Quality/FaultActive/Diagnostic stay published).
  Deliberately NOT obscured: `Status/*` (the HMI discovers modules by browsing
  `Status/Name`), `ParCfg`/`StationCfg` (config-editor field discovery and
  custom-tab bindings; small), `SupportedModes/RunStylesPublished` (mode bar).
- HMI: the OPC UA repository fetches all pages when the `ConfigRev` signature
  is new, synthesizes the exact flat browse-path keys (the server's
  `Member/Member[i]` array naming), and overlays them under the live snapshot
  before mapping — mapper/facets/views unchanged, works identically over the
  Web gateway. No published `ConfigRev` = pre-manifest library = fully
  published, never queried.

Verification pending a pinned XAE compile: attribute filtering on struct
members in TMC-Filtered mode, `DT_TO_UDINT`, and `TO_STRING` arity are the
watch items. After deploy, re-measure the live tree (expect roughly 33.7k →
low-20k value nodes for the press demo; the remaining bulk is the 64x16 empty
topology-slot LIVE members, addressed separately by right-sizing
`MAX_BUS_NODES`/`MAX_NODE_CHANNELS` per deployment).

## 69. Regressed defaulted method inputs on FB_SequenceBase broke the 4024 build (2026-07-23)

A 4024.x XAE compile of `Fraktal_Press_Demo` reported ~30 `Function 'M_Advance'
requires exactly '4' inputs` errors across all four ST sequence POUs
(`FB_PressDemoAuto/Changeover/Home/LoadPosition`). Cause: `FB_SequenceBase.
M_Advance(OnAdvance, OnJump1..3)` had been reintroduced with defaulted jump
inputs (`OnJump1..3 : INT := -1`), and every caller passed only `OnAdvance`.
Optional/defaulted method inputs are a TwinCAT 3.1.4026+ feature and violate the
pinned-4024 binding rule already established for `M_TryIssue` (§62) and
`M_ResetBase` (§64): **every method input must be explicit on 4024**. The same
audit found `M_ResetBase(FirstStep : INT := 0)` still carrying a default,
though all four callers already passed `FirstStep := 0`.

Fix (the §62/§64 pattern): the defaults were removed from both `M_Advance` and
`M_ResetBase`, and all 22 `M_Advance` call sites now pass every argument —
unused jumps are `-1` (`M_Advance(OnAdvance := N, OnJump1 := -1, OnJump2 := -1,
OnJump3 := -1)`); the one changeover retry keeps `OnJump1 := 810`. The effective
call contract and runtime behavior are unchanged (a caller that omitted a jump
was already relying on the `-1 = not used` default). The installed `Fraktal_Core`
library already exports `M_Advance` with four inputs, so the corrected sources
compile against it directly; the canonical `Fraktal_Core` source is updated to
match for the next library rebuild. A defaulted-method-input scan over every
`VAR_INPUT` block is now the enforcement gate — this is exactly the drift a
pinned-build CI compile (§1.5) would have caught at commit time.

## 70. Hardware Control-On adapter for a relay-safety machine (no TwinSAFE) (2026-07-23)

The physical press deployment turned out to have **no safety controller**: safety
is a hardwired Bosch/Nexeed N54 D2 "Control On" relay chain (Pilz-style). But
`FB_PressIoDriver.M_ReadInputs` read the six safety-status values straight from
the `GVL_PressSafety` `AT %I*` aliases, which were designed to be **linked to
evaluated TwinSAFE results**. With no TwinSAFE to write them, they stayed FALSE,
and the fail-closed cascade faulted *every* device on the HMI the moment
`UseSimulation := FALSE` (StandardIoHealthy FALSE → bad input quality; the safety
permits FALSE → all interlocks drop). Simulation had hidden this because
`FB_PressSimulationDriver` *derived* the six signals from ordinary inputs; the
real driver did not.

Fix: `FB_PressControlOnCircuit` (new, in `00_System`) reconstructs the six
read-only status mirrors from the **raw relay/sensor process image** —
`_000K910A` E-stop mirror, `_101B201A` door-closed, `_101S101/102` two-hand,
and crucially `_000K911_Y32` (the relay-chain **Control On feedback**) as the
`SafePneumaticPermit`. Per N54 D2, the Main/Safety-Valve and Safety-Door add-ons
already reset `EnableControlOn` on air/guard errors, so K911_Y32 subsumes air +
guard monitoring; the adapter only ANDs in the E-stop mirror + bus-valid for
defense in depth. `FB_PressIoDriver` owns the adapter (it remains the sole
`GVL_PressIO` consumer) and gained a `BusOk` input; `MAIN` supplies it from a new
`RealBusOk` flag (link to the EtherCAT master DevState/WcState; **default FALSE**
= fail-closed until linked, forced TRUE only on a validated isolated bench).

This is explicitly **not** a safety function: the relay chain remains the safety
authority, matching §9's "read-only aliases to results produced outside the
standard PLC" — here the external source is the relay circuit, not TwinSAFE. The
functional `EnableControlOn`/`SwitchControlOn` outputs are unchanged and still
gated by `ControlCircuitMappingConfirmed`. `GVL_PressSafety` is retained (unused)
as the documented TwinSAFE alternative for a machine that does have a safety
controller. Synced to both the canonical and `x32` build trees; 4024-clean (no
defaulted method inputs).

## 71. Fieldbus node state reads the real EtherCAT master; bus detection moved into the library (2026-07-24)

Two problems, per user report + objectives: (a) the HMI marked every fieldbus
node FAULT while XAE showed them OPERATIONAL, because node state was driven by
`FB_IoTopologyPublisher.M_SetAllHealth(StandardIoHealthy)` — an all-or-nothing
verdict tied to Control-On (via `RealBusOk`/the §70 adapter); (b) `RealBusOk` and
bus-validity were declared/wired in the *project*, violating the objective that
the **library detect the most it can from hardware with the least project wiring**.

New library FB **`FB_EcBusHealth`** (`Framework/Fraktal_Core/Connectivity`) reads the REAL,
live EtherCAT slave states directly from the master via `Tc2_EtherCAT.
FB_EcGetAllSlaveStates` (+ `FB_EcGetMasterState`), maps each device-state nibble
(`EC_DEVICE_STATE_INIT/PREOP/SAFEOP/OP/ERROR`) to the neutral `E_NodeState`, and
publishes it per node through the new `FB_IoTopologyPublisher.M_SetNodeState`
(node `State`/`LinkOk` + channel `Quality`). It also exposes `M_BusOk` (all mapped
slaves OP) — the **library-detected** replacement for the project's `RealBusOk`.
A non-blocking `CASE`/timer refresh keeps the async ADS reads off the task; a
master read error marks the segment OFFLINE (fail-visible, not silently OP).

Project wiring now minimal: `FB_PressIoDriver` owns one `FB_EcBusHealth`, calls
`Setup(MasterNetId := '', FirstSlaveNode := 2, SlaveCount := 5, MasterNodeIndex
:= 1)` (the ONLY project input — how its 6 catalog nodes line up with the
master's slave scan order) and `M_Refresh()` each scan; `MAIN.RealBusOk` and the
`BusOk`/`StandardIoHealthy` args to the fieldbus refresh are **removed** — the
Control-On adapter's `busOk` now comes from `FB_EcBusHealth.M_BusOk()`. Node state
is therefore **decoupled from Control-On**: fieldbus reflects the real bus.

`M_SetAllHealth` is retained as a documented legacy/fallback (transports/projects
with no fieldbus master). `Tc2_EtherCAT` added as a `PlaceholderReference` to
`Fraktal_Core.plcproj`; `FB_EcBusHealth.TcPOU` added to the Connectivity compile
list. The pre-existing `FB_EcFieldbusScanner` (an *unimplemented* `I_FieldbusScanner`
skeleton, not used by the press demo) remains the future full-auto-discovery path;
`FB_EcBusHealth` is the focused, working state-refresh now.

**Build/verify (cannot compile in this environment — pin-and-verify):**
- The split `FraktalPressDemo.sln`/`.tsproj` now builds the **canonical**
  `Fraktal_Press_Demo.plcproj` directly (the old `x32` duplicate tree is gone —
  no more two-tree sync). The press demo consumes `Fraktal_Core` as an **installed
  library** (`PlaceholderReference Fraktal_Core, *`), so `FB_EcBusHealth` +
  `M_SetNodeState` must be picked up by **rebuilding and reinstalling the
  Fraktal_Core library** before the press demo will resolve them.
- Verify against the pinned `Tc2_EtherCAT`: `FB_EcGetAllSlaveStates` I/O names
  (`sNetId`/`nSlave`/`pStateBuf`/`cbBufLen`/`bExecute`/`bBusy`/`bError`),
  `ST_EcSlaveState` layout (`nState`,`nLinkState` bytes), and the
  `EC_DEVICE_STATE_*`/`EC_LINK_STATE_OK`/`EC_DEVICE_STATE_MASK` constants (all
  confirmed present in the installed 3.6.3/3.7.x library on this machine).
- Verify the node↔slave mapping after an XAE I/O scan: master AmsNetId (`''` =
  local), that catalog node 1 = master, nodes 2..6 = the 5 slaves in scan order.
4024-clean (no defaulted method inputs).

**First XAE compile fixes (2026-07-24):**
- 13 parser errors cascaded from ONE reserved-keyword collision: a local
  `st : E_NodeState;` in `M_Refresh` — **`ST` is reserved** (Structured Text /
  the CDATA `<ST>` tag), so the declaration desynced the parser for the whole
  POU (the "Unknown type '_stateBuf[i].nState'" etc. were all downstream noise).
  Renamed `st`→`mapped` and `link`→`linkOk`. This is the same reserved-identifier
  class as §37 (`S`,`R`,`DT`,`Log`,`Min`,`Max`,`Action`); scan new locals against it.
- Dropped the `FB_EcGetMasterState` read (its `Get`-FB output member name is
  version-sensitive and unverifiable from the compiled library): the master
  topology node's state is now **inferred from the slave-states read outcome**
  (it answered ADS ⇒ OPERATIONAL; read error ⇒ OFFLINE with the segment). One
  fewer version-sensitive surface; `FB_EcGetAllSlaveStates` is the only
  Tc2_EtherCAT FB called.

## 72. TwinCAT 4024 becomes a guarded legacy profile, not the ceiling (2026-07-26)

**Policy inversion.** The library previously held every developer to 3.1.4024's
restrictions, so the *default* experience paid for the *legacy* target — most
visibly at `FB_SequenceBase.M_Advance`, whose 21 of 22 call sites had to repeat
`OnJump1 := -1, OnJump2 := -1, OnJump3 := -1`. That trade is now reversed:
**modern TwinCAT (>= 3.1.4026) is the default target and 4024 is a supported
legacy profile**, selected by one compiler define, `FRAKTAL_TC3_4024`, with
modern-only constructs wrapped in a conditional pragma:

```
{IF defined (FRAKTAL_TC3_4024)}
FirstStep : INT;          // legacy: caller must pass it
{ELSE}
FirstStep : INT := 0;     // modern: defaulted
{END_IF}
```

**Two Beckhoff facts made this safe** (InfoSys, *Conditional pragmas*):
conditional pragmas are valid in the **declaration part from 3.1.4024 onward**,
so the guard mechanism itself compiles on the legacy target; and there is **no
built-in compiler/TwinCAT version symbol** — `defined()`/`hasvalue()` only test
user-defined defines — so the switch has to be an explicit define rather than an
inferred version test.

**Changed**
- `Params/PL_FraktalCompat.TcGVL` (new) — the authoritative statement of the
  policy: what is guarded, how to build legacy, and the rule for adding the next
  guarded feature. Exposes `LEGACY_TC3_4024 : BOOL` and
  `COMPAT_PROFILE : STRING` so a deployed binary self-identifies without
  inspecting project settings.
- `FB_SequenceBase.M_Advance` — `OnJump1..3` default to `-1`;
  `.M_ResetBase` — `FirstStep` defaults to `0` (all four call sites passed `0`).
- 25 call sites simplified: `M_Advance(OnAdvance := 100)` and `M_ResetBase()`.
  The one real jump site keeps only what it uses:
  `M_Advance(OnAdvance := 999, OnJump1 := 810)`.

**Enforcement replaces remembering.** This defect class regressed four times
(§62, §64, §69, and once more found by the lint itself), so it is now checked
rather than recalled. `tools/plc_lint.py` rule C1: a defaulted METHOD input is
allowed **only** inside the `{ELSE}` of the legacy guard; `--profile 4024`
additionally rejects any *unguarded* modern construct. CI runs both profiles as a
matrix, so breaking the legacy build fails the gate. Self-tested against a
planted unguarded default and a planted wrongly-guarded one; 233 files clean in
both profiles.

**Caveat:** the define must be added to **every** PLC project in the solution
(library *and* application) — a conditional pragma is evaluated per compiled
project, so defining it only on the application would leave the library compiled
in modern form. Not compile-verified here (no XAE in this environment); the
source-level rules are gated, the pinned compile is still §1.5 pending work.

## 73. §5.7 tier conformance rows filled for the EM and Unit types (2026-07-26)

**What the audit had wrong.** A first read of §5.7 counted "eight rows missing"
for the Unit tier. §5.7 actually says the opposite for most of them: **T1/T4 and
the T2/T6/T7/T10 *mechanisms* are proven once in the framework base suite** and a
type **"shall not re-test inherited rows"** — verification is paid at the level
that owns the behaviour (O1), exactly like the code. `FB_Base_Tests` already
proves T1/T2/T4/T6. So the real shortfall was narrower: a type owes its
applicable rows re-proven with **its own** reasons, paths, modes and actions.

**Added — EM tier** (`FB_ClampEM_Tests`, 1 → 3 tests)
- **T3**: a dropped permissive on `CylA` must withhold the physical output and
  surface `INTERLOCK_DROPPED` through the EM naming `ClampIntlk.CylA`. The
  base-suite mechanism test cannot assert this: the value under test is the
  *composite tier's* path/reason pairing.
- **T5**: a stored `ST_ClampParCfg` with `SchemaVersion := 2` against an expected
  1 must fault `RECIPE_INVALID` at `Setup`, **and** a subsequent command must not
  drive the actuator ("never mis-runs", §3.8) — the second assertion is the one
  that matters, since faulting alone would still permit a mis-run.

**Added — Unit tier** (`FB_ClampStationUnit_Tests`, 1 → 4 tests)
- **T8**: the type does not override `_M_Supports`, so its set is the baseline
  AUTO+MANUAL. `SetMode(CALIBRATION)` must return FALSE, leave `ModeActive`
  unchanged, and **not** raise an error — a rejected request is not a fault
  (§3.7). Also asserts a supported mode still commits afterwards, so the
  rejection cannot have wedged the mode machine.
- **T10**: `Start()` accepts **iff** `ReleaseReportStart` reports `Released`,
  asserted in *both* directions. One direction would let the report drift from
  the gate it is supposed to describe (§7.8).
- **T6+T9**: the root adopts the deepest child's first-out **verbatim across two
  tiers** (`Stall.Station.Clamp.CylB`), and must not name itself. The two-hop walk
  is precisely what the Unit adds over the EM's single hop.

**Wiring**: both suites were already instantiated in `PRG_TcUnitRunner` and
registered in `Fraktal_Tests.plcproj`, so the new cases run with no further
plumbing. Totals 67 → 72 tests across 24 suites.

**Also corrected**: Annex H claimed T4/T5 were "left as the reader's exercise".
Stale — `FB_CylinderCM_Tests` covers T1–T5. Fixed there and in the audit.

**Status honesty**: these tests are written against the real APIs (every
identifier, member and visibility checked statically — `ModeActive` is a PROPERTY,
`CylA`/`CylB` are `VAR_OUTPUT`, `Start`/`Stop`/`SetMode` are public) but are **not
compiled or run** — no XAE here. They become a conformance *claim* only once green
in a run, which is the pending §1.5 CI compile.

## 74. Command-start lifecycle closes the mode-adapter reset gap (2026-07-27)

The Press Unit's `_M_SequenceHome`, `_M_SequenceChangeover`, and
`_M_SequenceAuto` methods still contained identical two-state reset/run machines.
That made an adapter look like a second sequence and tied the Unit's inherited
`_step` token to plumbing that belongs to the lifecycle. Moving reset only to
`OnModeChanged` would be incorrect: a finite HOME or CHANGEOVER command can be
started again without another mode change.

`FB_ModuleBase` now calls the additive protected `OnCommandStart` hook exactly
once for every accepted `Execute` edge, after the one-shot `OnInit` callback and
before `OnCyclic`/`_M_Dispatch`. This is the single command-local reset/latch
extension point; it does not replace the sequence's N000 process initialization
or N999 completion. `FB_Base_Tests` observes the hook across held Execute,
Execute-drop reset, and a second command edge.

`FB_UnitBase`'s existing transition hooks now match the normative signatures:
`OnModeChanged(NewMode, OldMode)` receives the committed transition and
`OnModeExit(FirstCall, RequestedMode)` receives a one-shot entry marker plus the
pending target. Repeated `SetMode` calls for the same pending target do not
re-arm `FirstCall`. The Press Unit implements `OnInit`, `OnCommandStart`,
`OnModeChanged`, `OnAbort`, and `OnAbortInError`; all reset/safe-withdraw wiring
is centralized in protected helpers. `OnCommandStart` resets only the chains:
it deliberately preserves a physical start pulse latched by `OnCyclic` on the
scan before the inherited Execute edge is consumed. Init, mode entry, and both
abort paths also clear that cross-mode input state. Its three sequence adapters are now
one-line `M_Run()` calls, while the application behavior remains solely in the
three `FB_SequenceBase` POUs. A Press TcUnit case starts HOME twice in the same
mode to guard the finite-chain restart behavior.

This is the deliberate Fraktal distillation of the useful Nexeed transition
idea, not an import of `Unit+Extension`, `OnInitHierarchy`, or a second
mode-release Boolean. Composition stays in `Setup`, first-scan work stays in
`OnInit`, mode release remains the authoritative `ST_ReleaseReport`, and mode
entry/exit remain the inherited Unit hooks.

Versioning: Core advances to `0.1.0.5`; Modules is rebuilt and repinned as
`0.1.0.4`; Demo advances to `0.1.0.3`; Press Demo and aggregate Tests advance to
`0.1.0.9`. Source/XML/lint validation is run here; the pinned XAE compile and
TcUnit execution remain required before release.

## 74. Fieldbus: fail-open on unreported slaves, and §10.5.1 demand gating (2026-07-26)

**Reported symptom:** the HMI showed K010B1/K010C1 in INIT while XAE showed OP.

**The HMI was not at fault.** Probing the PLC directly showed it *publishing*
`State = 1` for those nodes, so the tree rendered faithfully. Two real defects
sat underneath, both in this library.

**(a) Fail-open decode of unreported slaves.** `FB_EcGetAllSlaveStates` fills only
the first `nSlaves` buffer entries; the rest keep their previous/zero content. The
decode looped over the *declared* `_slaveCount` regardless, and a zeroed entry has
`linkState = 0`, which the nibble test reads as **link OK**. Live evidence:
`SlavesReported = 3` against 5 declared, and nodes 5/6 published
`State = OFFLINE` **with `LinkOk = TRUE`** — a slave that is not on the bus was
reported as healthy. Fixed: decode only the first `nSlaves` entries; publish the
surplus as `OFFLINE` + `LinkOk = FALSE` (fail-closed); `M_BusOk()` now also
returns FALSE when the master reports fewer slaves than the topology declares —
missing declared hardware is not a valid bus. New `CountMismatch` output makes the
"master reports N, project declares M" case visible instead of inferable, per
§10.5.1 ("unmatched mappings are commissioning errors, never silently guessed").

**(b) The bus was polled continuously.** §10.5.1 defines the topology as a
**diagnostic** surface, and the HMI already demand-gates *reading* it (read tiers,
`fieldbusScope`). The PLC nevertheless scanned the master every 250 ms forever, so
half the saving was fictional: ADS traffic and PLC time were spent maintaining
data nobody was reading. Added `FB_EcBusHealth.M_RequestScan(Active)`;
`M_RefreshFieldbus(BusViewActive)` and `MAIN.FieldbusViewActive` thread it, and
`OpcUaRepository.setFieldbusViewActive` now writes that flag so the gate is
end-to-end. Deliberate details: the **first** scan after Setup always runs (so
`M_BusOk()`, which feeds control logic rather than a view, is never based on
unread hardware); a rising request re-arms the poll timer immediately so opening
the view does not wait out the 250 ms; released gating **holds** the last states
rather than invalidating them (a stale-but-true picture beats a fabricated one);
and the HMI write is best-effort — a PLC without the flag keeps its own cadence.

**Not a defect — the INIT states are real.** The dev runtime's EtherCAT master is
bound to a **Null Adapter** in a usermode runtime ("running in the user mode
runtime" in the TCOM log) and the downloaded boot config contains *only* the
master (`=000+S-A610`), with zero mentions of EK1200/EL1809/EL2809/EL6001/EL9011.
With no NIC there are no EtherCAT frames, so slaves cannot leave INIT. XAE showing
OP is XAE's own configuration view, not the runtime's AL state. To see OP at
runtime, bind the real NIC (clear `SimulationMode`) and re-activate so the
terminals are actually downloaded.

## 75. Windows installer owns a secure remote-Web adapter (2026-07-28)

The loopback-only gateway boundary from §65 remains unchanged. Remote Windows
browser access is now a concrete installer option rather than only a deployment
instruction: `FraktalSetup.exe` bundles Caddy 2.11.4 from its official Windows
amd64 release, verifies the pinned SHA-512 before packaging, and ships its
Apache-2.0 license/readme. The gateway tray starts, stops, and restart-supervises
both the Dart gateway and Caddy; Caddy is present but inert unless a site
`proxy/Caddyfile` exists.

The wizard collects one exact `https://<host>[:port]` public origin, a constrained
username, and a minimum-12-character password. The password moves to the child
only through its process environment and is piped to `caddy hash-password`; only
the Argon2id hash enters the Caddyfile. Caddy terminates TLS, authenticates both
the static HMI and WebSocket upgrade, actively checks loopback `/livez`, keeps
WebSocket streams through reload churn, and proxies only to
`127.0.0.1:8080`. Its admin endpoint and config persistence are disabled. The
generated internal CA uses a site-owned persistent storage directory; only its
public root is copied to the obvious client-distribution path. The private CA
key is never exported.

Installation now treats `--port`, `--web-root`, the selected
`--plc-endpoint`, and the selected `--allow-origin` as structured
option/value pairs. Duplicate installer-owned options collapse to one value, and
`--port` is always normalized to `8080`; this repairs the observed deployed
`8080\` value that made Dart fail with `Invalid radix-10 number` before binding.
The optional elevated firewall helper permits only the Caddy program/HTTPS port
from `LocalSubnet` on Domain/Private profiles; port 8080 remains unreachable
remotely by construction.

Upgrades replace Caddy but preserve an existing validated Caddyfile, password
hash, CA, origin, and firewall rule when no new password is supplied. Supplying
a new password is the explicit reconfiguration edge and publishes the new file
only after Caddy formats and validates an atomic `.next` candidate. Linux/site
SSO and managed mTLS proxy policies remain deployment adapters; the bundled
Windows profile is the plug-and-produce LAN/basic-auth option, not a universal
identity provider.

## 76. The fault hard-lock: reset that recovers, and HELD for a lost permissive (2026-07-29)

An AUTO cycle on the CX2030 press reached N200 (`ram down`) and the operator
released the two-hand button mid-stroke. The machine hard-locked: no action at the
panel cleared it, and HOME — the sequence that exists to recover the machine — was
blocked by the fault it would have recovered from.

Read off the live PLC (`ads://5.132.128.188.1.1:851`) before changing anything:

```
PneumaticPress/Execute       = true        <- run command STILL asserted
PneumaticPress/Status/State  = 3 (ERROR)   Busy = false
PressRam/Execute             = true        <- child command STILL asserted
PressRam/Status/State        = 3 (ERROR)   ErrorID = 2003
CurrentStep/StepNo           = 200         awaiting PressRam.EXTEND
AlarmLog/Active[1]           = ACTIVE, MANUAL_RESET, 2003
AlarmLog/Blocking            = true        ControlDomain/ReadyForStart = true
Safety Devices[1..4]/State   = 2 (healthy) — nothing was actually unsafe
```

Three defects compounded, and the decisive one was **not** in the alarm log.

**(a) Stranded `Execute` latches.** `FB_ModuleBase.Cyclic`'s Execute-drop reset is
the only exit from a latched terminal state and it requires `Execute` low. A Unit
that is not `BUSY` never calls `_M_Dispatch` again, so the §6.8 step holding
`PressRam.Execute := TRUE` could never run to clear it, and nothing else in the
system owns that variable. The next HOME then re-issued an already-TRUE input: no
rising edge, so the ram never restarted, and the Unit re-adopted its fault through
the §8.2 rollup the moment it went BUSY. Even the `Stop` -> reset -> `Start`
sequence that `FB_AlarmLog_Tests` proves could not recover the *machine*, only the
event. `OnAbortInError` was the one path that dropped child commands, and it is
unreachable from an HMI: `E_HmiRequestKind` has no `ABORT`.

`OperatorReset` therefore now performs the control-state half of a reset
(`FB_UnitBase._M_RecoverState`): the new §3.14 `OnOperatorReset` hook, then
`_M_ReleaseChildCommands()`, then release of its own run command. `M_ReleaseCommand`
is new on `I_Module`/`FB_ModuleBase` (recursive in `FB_CompositeModuleBase`) and
cancels a command still `BUSY` through `AbortCommand()` before dropping `Execute` —
`BUSY` is not terminal, so un-asserting alone would leave the module unable to
accept any later edge. It deliberately never writes `_exec`: `Cyclic` keeps that
ownership (§47), so a live cause re-faults on the next edge instead of vanishing.

**(b) `OperatorReset` skipped `ACTIVE`.** It closed only `WAIT_RESET`, while
`Blocking` counts `ACTIVE` too — a guaranteed no-op for exactly the events that
block restart. Reaching `WAIT_RESET` needs the condition re-established, and
"two-hand held during a stroke" can only be re-established by starting, which the
event forbids. It now closes a `MANUAL_RESET` event from `ACTIVE` as well, stamping
`GoneAt`/`Duration` for one that never received a `Gone` so the ring entry keeps a
real duration. **Core §8.3(b) was amended** rather than diverged from: its two
`shall`s (never self-close; `Start` refused while `ACTIVE`/`WAIT_RESET`) are both
intact — an operator reset is not a self-close — but its lifecycle prose described
reset only from `WAIT_RESET`. The amendment also makes the control-state release and
the reachability of recovery modes normative.

**(c) A lost permissive was classified as a fault.** Releasing two-hand is expected
operator behaviour; ABORTED/STOPPED has one exit (Reset -> IDLE) and that exit was
the circle above. `FB_ModuleBase` gained `_M_Hold`/`_M_HoldDiag` and a published
`Held` flag (ISA-88 HELD, new Core §6.1 clause): `BUSY`, outputs withdrawn, reason
published at `LOW`, no alarm, and resolution is **level-based** — the base clears the
hold as soon as a scan stops re-asserting it, so no type can forget to. `Held` is
**not** an `E_ExecState` ordinal: that enum is transport contract and the HMI mirrors
its ordinals. `FB_CylinderCM` holds instead of faulting on a lost interlock and
rewinds to N010, so the resume re-energizes the direction output and re-arms
`MoveTimeout` with a full window instead of silently consuming travel time it was
not moving for. `FB_CompositeModuleBase._M_RollupHold` is the hold analogue of
`_M_RollupFault`, used by `FB_ClampEM` and by `FB_UnitBase`'s hold branch.

**(c′) The Unit's hold rollup was documented but never wired.** This paragraph used
to claim `_M_RollupHold` was "used by `FB_ClampEM` and by `FB_UnitBase`'s
awaited-module branch". `FB_ClampEM` did call it; `FB_UnitBase` never did — its
awaited branch called `_M_HoldDiag(_awaits.GetFaultSummary())` directly, so
`_M_RollupHold` had exactly one call site repository-wide and the Unit could only
report a hold on the module a step happened to name in `Awaits`. Press AUTO `N200`
passes `Awaits := 0` on purpose (§6.9: the step owns the ram's *not-reached*
disposition so the chain can offer scrap/return), and the two facts combined into a
silent defect: with the ram correctly `Held`, the Unit stayed `BUSY` with `Held`
FALSE and an empty `Status.Diagnostic`, which is what
`Two_hand_release_mid_stroke_holds_the_ram` had been failing on. It is pre-existing —
both the `Awaits := 0` and the missing call are unchanged since `4e47f37`.

The fix is in `FB_UnitBase.OnCyclic`, not in the project (§1.1 O1 — forgetting a call
must not be able to produce a wrong result). The hold branch now prefers the awaited
module when a step named one and otherwise falls back to `_M_RollupHold()` over the
registered children, so a hold rolls up whether or not the step awaits the child.
`Awaits := 0` scopes **fault** disposition only: a hold is recoverable information
that clears itself level-based and never blocks a restart, so there is nothing for a
step to "own" by staying silent about it. The two calls are deliberately exclusive
rather than OR-ed — TwinCAT does not short-circuit, so evaluating both would let a
second held child overwrite the named one.

The **fault** rollup stays explicit and is not made automatic here. That asymmetry is
the point of §6.9: adopting an awaited child's Error sets `_exec := ERROR` and
`_step := 0` before `_M_Dispatch` runs, so an automatic fault rollup would remove the
chain's ability to disposition a failure at all — `N200`'s scrap/return decision, and
`FB_ProbeUnitRaise`, both depend on it not firing.

Nothing was weakened to achieve this. The output is still withheld in the same
place by the same permit; the reset clears the **latch**, never the **condition**;
and `FB_FaultRecovery_Tests.Reset_never_bypasses_a_live_condition` pins that by
resetting with the air still missing and asserting `Start` stays refused, the live
condition is still named, and no output is restored. The press safety authority
remains the hardwired Bosch/Nexeed N54 D2 relay chain (§9.8,
`SAFETY_AND_CONTROL_POWER_PROFILE.md`); the standard PLC is not a safety function.

Deliberate non-changes, recorded so they are not "fixed" blindly:

- `ReleaseReportStart` still adds `std.release.unitNotReady` for a non-`READY`
  Unit. Letting `Start` run over a latched ERROR would be the symptom-hiding fix;
  the defect was that no operator action could make `_exec` leave ERROR. After one
  reset the Unit is `READY` and HOME starts (proven in the suite).
- `E_MachineState` gained no `HELD` member and `_M_OeeUpdate` still books a held
  Unit as run time, exactly as it already does for `BLOCKED`/`STARVED` waits. Both
  are transport/§8.5.1 contracts and neither was needed for recoverability.
- `ST_ModuleStatus` gained no member, so `HMI_CONTRACT.md` is unchanged. The
  operator sees a hold through `Status.Diagnostic`, which the HMI already renders.
- A hold has no upper time bound. It is visible (`Held`, the LOW first-out, the
  §6.9 pending walk) but it is not escalated to a fault after N seconds; that would
  be site alarm policy (§8.9), and on this press it would re-fault the machine for
  the ordinary act of pausing with the button released.

**Two-hand release inside the dwell (N220)** needed one project-level addition. The
press force during the dwell is the valve latched by the EXTEND that N200 already
completed, so withdrawing it leaves nothing to re-energize on resume:
`FB_CylinderCM.RestoreOutputs` is the symmetric counterpart to `WithdrawOutputs`
and re-asserts only the last commanded direction and only while that direction's own
permit holds — the caller asks, the module still decides.

**Universal fault clear.** `FB_UnitBase.RequestLocalReset` is an application seam for
an ordinary hardwired reset/acknowledge pushbutton, mirroring `RequestLocalControl`
(§9.8): a method rather than OPC UA data, so remote clients still go through the
access-gated `OPERATOR_RESET` request. A cabinet button is its own authorization
(physical presence), so it carries no §7.7 session check, but it is audited as a §8.3
event and recovers exactly the same state — never more. It is deliberately **per
Unit**: the composition root calls it once per root Unit a given input should clear,
so one physical button can serve one Unit or several without the framework choosing.
No press input was wired to it — `GVL_PressIO` channels 1..15 are fully assigned and
inventing an electrical tag is not an agent's call (§10.2.1) — so the seam ships
unwired on this project. The HMI half is `ui/global_reset_button.dart`, a fixed
corner control that fans out to the roots **this HMI shows**: §3.1a is a forest of
peers with no shared super-root, so there is nothing to "reset globally" in the PLC
and the fan-out belongs to the client. `ScopedPlcRepository` re-clamps every call to
the assigned scope and the PLC re-checks §7.7 per root.

Not verified here: **nothing was compiled.** There is no TwinCAT compiler in this
environment, so `plc_lint.py` (both profiles) plus XML well-formedness are the only
machine checks that ran on the ST; first real verification is the XAE build,
`Fraktal_Tests` run, and download. At the time of this change Core was `0.1.0.6`
and Modules `0.1.0.5` (additive `I_Module` growth: `M_ReleaseCommand`,
`HoldActive`). Section 77 supersedes those pins after the wider contract audit.

## 77. PLC-authoritative permissions and objective conformance audit (2026-07-31)

The permissions audit closed several authority splits rather than adding HMI-side
exceptions. `FB_UnitBase` remains the single remote mutation entry: access-policy
and session-timeout changes, control-power requests, decisions, configuration
writes, shelving and fieldbus force now use the acknowledged mailbox and are
checked by the PLC. Invalid access ordinals, corrupt policy values, invalid gates,
out-of-range timeouts and ambiguous alarm identities fail closed. Accepted
authenticated mutations rearm the idle timer and write an audit record containing
request kind, user and target; polling, release queries and denied attempts do not
keep a session alive. Source PIN literals were replaced with persistent,
OPC-UA-hidden, deployment-owned commissioning values; an empty value registers no
account.

Fieldbus force is now an explicit capability. `ST_IoChannel.Forceable` is
append-only and defaults `FALSE`; the topology/config projection carries it to the
HMI, which requires exact `ModulePath` ownership and does not render a force action
without that PLC capability. The Core route and the application resolver both
default to rejection. This deliberately leaves all current production channels
non-forceable until a mapped output and resolver have been individually reviewed.

The audit also restored the four-structure physical contract on the passive
digital-input and air-pressure CMs. Their `ParCfg` records begin with
`SchemaVersion`; air-switch conflict qualification moved into configuration with
the existing 500 ms default. The existing Modules test suite gained model-preset
coverage for IV3 and Matrix220. Three normative mismatches were resolved in favor
of the objectives: defensive coding now requires a semantic fail-safe path rather
than meaningless empty `ELSE` branches; the decision contract uses one active slot
per root (matching one step-state writer), with overlap rejection instead of a
mandatory queue; and §7.1 now makes immediate output withdrawal invariant while
§6.1 classifies the stopped command as HELD or fault. The decision slot still
needs its timeout/default/resolution implementation and tests.

Core and Modules are now `0.2.0.0`, and all downstream placeholders are pinned to
those versions. This is a minor-version change because the observable access,
force and recovery contracts grew; the TwinCAT fourth component remains reserved
for contract-neutral rebuilds as required by Part II.

The complete objective scorecard, open findings and ordered gap-closing program
are in `Specification/Reports/OBJECTIVES_AUDIT.md`. Highest priority is a licensed XAE
build plus TcUnit/CI evidence, followed by decision lifecycle completion, a typed
capability-driven write manifest, stronger conformance lint, controller/time
health and a reusable signal-tower contract. A capability-driven/generated design
is preferred: the PLC publishes a reviewed capability, one owning handler enforces
it, the HMI derives its control, and CI derives parity checks from the same source.

No TwinCAT compile or TcUnit execution was possible in this environment. The
Press Demo is an internal framework acceptance fixture, so its cabinet/electrical
state is not a Core/Modules conformance finding. If that fixture is ever deployed
to real equipment, the commissioning guide still applies; this change did not set
or clear `CONTROL_CIRCUIT_MAPPING_CONFIRMED`.

## 78. Decision resolver and capability-driven configuration writes (2026-07-31)

The two P1 authority gaps from §77 are now source-complete. `FB_UnitBase` owns the
entire §6.11 one-slot decision lifecycle: repeated identical requests are
idempotent; a different overlapping request is rejected and logged once; request
shape/default are validated before publication; operator input wins a same-scan
race with the monotonic timeout; timeout applies only a validated safe default;
operator/timeout/withdrawal/rejection events are distinct; and consumption clears
the whole slot atomically. `FB_Decision_Tests` covers operator, timeout, overlap,
invalid-default and withdrawal behavior. This supersedes §77's statement that the
resolver remained open.

Configuration editing no longer infers authority from a browse path. The
append-only `ST_ConfigEntry` tail publishes `WriteKey`, `WriteRevision`,
`E_ConfigKind`, `E_ConfigValueType`, `Writable`, `RequiresReady`, bounds,
engineering unit/label, and an exact enum domain. `FB_ConfigPager.M_Append` clears
that tail on every ordinary read-only entry so a reused page slot cannot retain
authority; `M_AppendCapability` is the only framework helper that populates it.
The HMI rejects missing, malformed and duplicate capabilities, maps them separately
from read-value hydration, re-resolves the current key/revision before every write,
and sends it through the same acknowledged mailbox. Custom inputs must match the
capability's full `Item`; manufacturing a key from a scalar tag is gone.

The first framework-owned typed handler is Unit `ModePolicy`: stable keys
`unit.modePolicy.<ordinal>.shield|style`, capability revision 1, exact enum
domains, root-owner check, and `READY`-only mutation. Unknown keys, stale revisions,
foreign targets and out-of-domain values reject without mutation. Project/type
handlers remain an extension seam but must append and recheck their own capability;
the framework-owned handler is separate so an override cannot hide it. HMI manifest
and repository tests prove fail-closed mapping and exact key/revision transport;
`FB_Unit_Tests` contains the corresponding PLC source assertions.

The mode-policy authority is persistent, not merely a mutable output mirror.
`_modePolicyVersion` and `_modePolicyStored[]` are `VAR PERSISTENT`; an unknown
version initializes the safe defaults once, subsequent activations restore the
stored records, and every accepted typed write updates both the public record and
its persistent backing before `ConfigRev` advances. The first activation after
this schema addition intentionally initializes version 1 rather than guessing at
an older memory layout.

Because the observable Core manifest contract grew, Core advances to `0.3.0.0`.
Modules remains `0.2.0.0` and is repinned to Core `0.3.0.0`; Demo, Press Demo and
Tests pin that same pair. The new `PLC/TwinCAT/{Framework,Tests,Examples}`
layout is retained, documentation paths are updated, and generated-directory
ignore rules now work at any depth. A licensed XAE build/TcUnit run and regenerated
TMC remain mandatory before this source can be called release-proven.

## 79. System health, time quality, signal tower, and live-facet closure (2026-07-31)

Core §2.7/§8.12 now has a concrete bounded implementation. `ST_TimeQuality`
separates availability, synchronization, source, offset and observation stamps;
`GVL_FraktalTime.Current` is the hidden PLC-wide quality authority and
`F_TimeSynchronized()` stamps quality beside diagnostics, alarm lifecycle edges,
part results and cycle/step wall-clock records. `FB_TcSystemHealthProbe` owns the
monotonic task-cycle/jitter measurement and accepts target metrics explicitly.
`FB_SystemHealthPublisher` owns validation, the small public status copy, and
Low/System/AUTO_RESET come/gone edges for task, controller, IPC, fieldbus/DC and
clock failures. Unsupported target metrics remain unavailable rather than healthy
zero. The Press fixture supplies honest synthetic values only in simulation; its
real profile stays conspicuously unavailable until target APIs and a documented
sync source are wired.

Core §8.13 is implemented once by `FB_SignalTower`. The Unit base derives it from
`MachineState`, the maximum severity in the authoritative active-alarm table, and
the active decision slot; it publishes semantic outputs only. Site choices are
schema-first `ST_SignalTowerParCfg`. Mailbox kind `LAMP_TEST := 26` is append-only,
MANUAL-gated, refused while BUSY, audited, acknowledged, clamped to 30 seconds and
self-clearing. No physical Press output was invented: the acceptance fixture tests
and publishes the semantic mapping, while a reviewed project Hardware Driver must
own any future electrical map.

The re-audit also found that several static/live HMI facets existed in types but
were not transported end to end. `M_AppendConfig` now actually exports hidden
nameplate, stall-time, model/catalog, mode-policy and alarm-rationalization fields;
manifest typing includes meta counts/reasons/shelvability. The generic snapshot
mapper now hydrates sparse active alarms, newest-first closed history, timestamp
quality, rationalization records, OEE/trend, part results, nameplate, safety and
control-power facets. It also corrected the cycle/OEE ring traversal to produce
oldest-to-newest trends. Mapper tests cover the real named-array shape and both
TwinCAT-DT and OPC-UA time normalization paths.

`tools/plc_lint.py` now checks the previously promised structural rules: the
four-record/schema-first contract, enum parity, inheritance/body/hook-super
invariants, semantic `CASE ELSE`, sequence ownership, EM-to-Unit containment,
reason collisions, project compile coverage, and deployed-root publication. Its
fixture suite is committed, but Python is absent from this workstation, so neither
the linter nor its fixture suite ran here. XML parsing, Dart analysis and focused
Flutter tests did run; a licensed XAE build and TcUnit remain the P0 release gate.

## 80. Shared-session Web read tiers (2026-07-31)

The Web gateway now implements the direct-client scalability contract instead of
relaying the complete published surface every cycle. `discoverPaths` returns one
revisioned path vector; `setReadTiers` carries compact indices into that vector;
and `readValues` accepts bounded batches which the Web/native gateway clients
chunk and merge. The repository remains the only tier classifier. After tier
installation, cyclic snapshots omit the static path vector and the native PLC
session excludes view-gated rings/topology until their owning view requests them.

The gateway deliberately does not let one browser mutate the shared native read
profile independently. It applies the intersection of all connected profiles:
a path becomes slow or excluded only when every browser agrees, and an
unconfigured/new client temporarily restores the full surface. Discovery changes
invalidate all profiles. This is the conservative multi-client rule that keeps
one HMI from starving another while retaining single-client O4 scaling.

Optional repeatable `--read-root` scopes are enforced consistently over snapshot
values/DataValues, discovery, tier indices and targeted reads. With no configured
read root, the upstream OPC UA/ADS identity remains the browse boundary for
backward-compatible commissioning; write authority remains separately fail-closed
behind `--write-root` and the PLC mailbox policy. Static analysis and focused
gateway/reconnect/repository tests passed; representative packaged large-forest
traffic and latency remain release acceptance evidence, not a source claim.

## 81. Generated reason text and rearranged aggregate manifest (2026-07-31)

`HMI/tool/generate_reason_catalog.dart` now derives the §8.8 code-to-message
projection from the authoritative Core `E_Reason` definition plus the registered
Core/Modules type-reason parameter lists. It rejects duplicate numbers and
symbols, emits deterministic Dart localization keys and English fallback text,
and has a CI `--check` gate. Snapshot hydration prefers that catalog for registered
diagnostic, alarm, part-result and control-power codes; an unknown external or
application reason preserves the PLC diagnostic text. Release-report descriptions
remain condition-specific rather than being replaced by a generic reason sentence,
which preserves §7.8 act-or-explain detail. This closes the §8.8 projection, not
§8.9's remaining generated rationalization-metadata work.

Moving the aggregate test sources into their dedicated owner folder initially
changed the `.plcproj`'s relative base and left 40 unresolved compile items.
Merely resolving those paths through sibling parent-relative Press references was insufficient: TwinCAT PLC
Control rejects `..` lexically before evaluating `Link` metadata (see §62). The
manifest therefore remains at `TwinCAT/`, with all `Tests/` and `Examples/`
includes expressed as downward paths from that common ancestor.
The repository-wide check resolves every compile item and the manifest stays
importable through **PLC → Add Existing Item**.

## 82. Generated rationalization and fixed host events (2026-07-31)

The §8.8 text generator now joins the numeric authorities (`E_Reason` plus the
registered Core/Modules type bands) to
`Specification/reason_rationalization.json`, which is keyed by symbol and
therefore does not duplicate reason numbers. It rejects incomplete/unknown
coverage, duplicate symbols/numbers, shelvable events, and shelvable Safety
records. One run derives four artifacts: the Dart localization/metadata lookup,
`PL_ReasonCatalog`, `F_ReasonMetaByIndex`, and `F_ReasonMeta`. CI `--check`
therefore covers PLC and HMI projections together. The shipped registry currently
contains 51 complete records, including the formerly missed final enum member
`TEST_FAULT`.

`FB_AlarmLog` now enforces the generated priority/category/shelvability for every
standard reason, so a caller cannot reclassify one alarm on one surface. The Unit
configuration manifest pages the complete generated catalog and any validated
external/application records. `RegisterMetaFull` is the extension seam for those
nonstandard bands; it rejects standard overrides, event-only alarm records, and
shelvable Safety records. `F_RationalizeDiagnostic` applies the same generated
priority/category at the first-out source, so `Status.Diagnostic`, the Unit alarm
log, HMI, and injected sinks cannot disagree for a standard reason. The HMI
hydrates the same fields and uses its generated copy as a deterministic fallback
during a partial server rollout. Events with no operator action stay logged but
do not render a blank action prompt.

Core §11.6 is projected by `FB_HostEventPublisher` and `ST_HostEvent`: each root
publishes a bounded 32-record read-only ring with sequence, fixed kind, station
path, optional part/subject/value, timestamp quality, verdict, reason, and an
explicit wrap flag. `FB_UnitBase` is the single producer for part lifecycle,
NOK, mode, and changeover events; `CHANGEOVER_STARTED` is tied to the accepted
CHANGEOVER Start edge and `CHANGEOVER_DONE` to successful sequence completion,
not merely mode selection or recipe commit. Named methods cover project-owned
tool/material changes. Optional push delivery is injected through
`I_HostEventSink`; its implementation storage is hidden from OPC UA and the ring
remains authoritative when no adapter exists.

The closing audit found one carrier-optional edge in that projection: the legacy
`CountNok()` counter could be called without emitting an attributed host event.
Core `0.4.0.0` now requires `CountNok(Reason)` with a non-`NONE` reason and makes
the counter increment plus fixed `NOK` event one operation. `_M_PartProcessed`
uses that same path, while a no-carrier sequence publishes an empty `PartUid`.
An unattributed reject is refused before carrier write and raises
`RESULT_RECORD_REJECTED` rather than creating unanalysable scrap data.

The HMI enum/domain/mapper mirrors the append-only event vocabulary and hydrates
the ring newest-first on demand. PLC source suites cover invalid events, all ten
fixed kinds, required fields, bounded wrapping, base mode emission, and generated
metadata authority. Core advances to `0.4.0.0`; Modules advances to `0.3.0.0` and
all downstream placeholders are repinned. These are source-level changes until a
licensed XAE build, aggregate TcUnit run, and regenerated TMC prove the binding.

## 83. Aggregate manifest repair after the TwinCAT tree rearrangement (2026-08-01)

The rearrangement accidentally moved `Fraktal_Tests.plcproj` inside its source
folder and converted the six Press fixture links to `..\Fraktal_Press_Demo\...`.
That made every file resolvable to ordinary filesystem tooling but reintroduced
the exact TwinCAT PLC Control import failure documented in §62: `..` is parsed as
an invalid PLC folder before `Link` metadata is evaluated. The manifest is again
at the `TwinCAT/` common ancestor, all 41 compile inputs are downward paths, the
tracked XAE project reference follows it, and the source-owned TMC remains under
`Tests/Fraktal_Tests/`.

P1 lint ownership now recognizes the same-named source directory beside a
common-ancestor aggregate manifest. It still resolves every explicit linked
input, while sibling applications remain accountable to their own manifests;
it also rejects any raw `..` compile segment before filesystem resolution can
mask the TwinCAT incompatibility. Regression fixtures cover both arrangements;
the suite now contains 18 tests.

## 84. Press and aggregate tests separated by GUID ownership (2026-08-01)

`PressDemoX32.tsproj` loaded both `Fraktal_Press_Demo.plcproj` and the aggregate
`Fraktal_Tests.plcproj`. Because the aggregate links the deployed Press Unit,
release evaluator, and four sequence POUs, PLC Control saw each physical object
twice in one XAE solution. A load produced 1,029 duplicate-object warnings and
repeatedly rewrote every shared POU/method GUID plus line-ID metadata. The six
files' declarations and implementations were verified identical to Git before
their original metadata was restored.

The Press system project now contains only the deployable Press application.
Aggregate tests run from a separate XAE solution/ADS port as §5.7 requires. P1
lint now resolves the PLC projects referenced by each `.tsproj` and rejects any
physical source intersection, preventing the same GUID churn from returning.
The linter suite contains 21 tests.

## 85. Compiler-cascade and Press system-project repair (2026-08-01)

The first licensed 4026 compile exposed three independent source defects whose
parser fallout appeared as a much longer error list. `FB_UnitBase` used a
TwinCAT-invalid `CASE` over `HmiRequest.TextValue`; it now uses `IF`/`ELSIF`
string comparisons. `FB_AlarmLog._M_Raise` declared local `meta` beside the
published `Meta[]` member; TwinCAT identifiers are case-insensitive, so the local
shadow made `Meta[i].ReasonCode` parse as a type expression. The local is now
`generatedMeta`. Finally, `E_ConfigValueType.TIME` used the reserved IEC type
keyword; the TC3 binding spells ordinal 3 `DURATION` while Core/HMI retain the
portable `time` vocabulary. No ordinal or observable schema changed.

The rearranged `PressDemo.tsproj` also contained only the PLC instance: its
EtherCAT device and all symbolic mappings were absent. Those were restored from
the existing Press system authority. EL1809 channels 9 and 13 were still named
`Reserve` in the XTI while the approved PLC tags were `_000BS901` and
`_000BS902`; the XTI names now match those exact electrical tags. A subsequent
XAE load resolved every mapping without the former `not linked` warnings.
`CONTROL_CIRCUIT_MAPPING_CONFIRMED` and `USE_SIMULATION` were not changed.

The corrected draft libraries were built and installed in dependency order:
Core `0.4.0.0`, then Modules `0.3.0.0`, followed by a fresh Press application
reload. Direct nested XAE builds for all three returned `LastBuildInfo=0` with an
empty Error List under `Debug|TwinCAT OS (ARMV7-A)`. The full system-project CLI
build still stops at `Check config` while the saved remote target is unavailable;
that is a target/configuration checkpoint, not a PLC compiler failure. The builds
regenerated Core, Modules, and Press TMC files; TcUnit, live TMC/OPC UA import,
and target acceptance remain open release evidence.

Lint now rejects reserved enum members (C2) and quoted/string `CASE` labels (C6)
so these two parser defects cannot recur silently. The suite contains 21 tests
and the real tree passes both modern and legacy-4024 profiles.

The aggregate test application now has its own 4026 wrapper,
`Tests/FraktalTests.slnx` / `FraktalTests.tsproj`, on ADS port 854.
It references the common-ancestor `Fraktal_Tests.plcproj` and loads without the
Press project, so the two applications cannot present the linked Press sources
to XAE twice. No target route is stored in this test wrapper by design. Its full
system build therefore stops at `Check config` until an isolated test runtime is
selected; aggregate test compilation and TcUnit execution remain open evidence.

## 86. Aggregate-test first compile reconciliation (2026-08-01)

The first interactive aggregate compile exposed an incomplete reserved-word
binding migration. Core already used `TimeClass` because TwinCAT reserves
`CLASS`, but four `FB_ClampStationUnit` calls, the Unit probe, and the profiler
tests still used the old named input/member `Class`. All PLC callers and test
assertions now use `TimeClass`. `HMI_CONTRACT.md` binds the deployed
`TimeClass` symbol, while the generic mapper accepts both `TimeClass` and the
legacy draft `Class` path during migration. C2 now reserves `CLASS` and its
existing parameterized regression fixture exercises both `TIME` and `CLASS`.

The moved aggregate manifest also linked `FB_PressDemoUnit` without its
application-owned `GVL_PressFieldbus`; that GVL and its owner-local `Io` folder
are now explicit downward links. The isolated `FraktalTests.tsproj` contains no
EtherCAT device and keeps ADS port 854; test execution cannot address the Press
hardware mapping accidentally.

Modules rebuilt with `LastBuildInfo=0` and zero errors, then the corrected
`0.3.0.0` library was installed. TwinCAT `CheckAllObjects` on the reloaded
aggregate project reported zero Error List entries. A full system-project build
still stops at `Check config` until an isolated test target is selected; TcUnit
execution remains the next acceptance checkpoint.

## 87. Connector completion of the extended I_Module contract (2026-08-01)

The next interactive aggregate build exposed a separate interface-completeness
gap. `FB_DeviceConnectorBase` implements `I_DeviceConnector` directly, and
`I_DeviceConnector` extends `I_Module`; unlike the three ordinary module tiers,
the connector deliberately does not inherit `FB_ModuleBase`. When `I_Module`
gained `M_ReleaseCommand` and `HoldActive`, the direct connector implementation
was not updated. The abstract Core type could still be packaged, but the
aggregate project's concrete `FB_ProbeConnector` correctly failed with the two
missing-implementation diagnostics.

The connector now implements both members at the correct ownership boundary.
`M_ReleaseCommand()` is a successful bounded no-op because a connector owns no
PLCopen `Execute` latch; the fronting Control Module owns and releases the
dependent command. Calling `Disconnect()` here would be wrong because Core
§3.15.2 requires the connector to retain bounded automatic reconnect. Likewise,
`HoldActive` is always `FALSE`: the connector publishes link state and its
diagnostic, while the fronting Control Module interprets `Reaction := HOLD` and
owns ISA-88 HELD lifecycle state. `FB_Connector_Tests` now exercises both
members on the concrete probe, so future interface drift reaches the aggregate
compiler seam.

Core `0.4.0.0` and Modules `0.3.0.0` were rebuilt and installed in dependency
order under `Debug|TwinCAT OS (x64)`; both returned `LastBuildInfo=0` with zero
Error List entries. The reloaded aggregate wrapper and its direct nested-project
build command also returned `LastBuildInfo=0`/zero errors, and `CheckAllObjects`
reported zero errors. The aggregate TMC/compile-info timestamp did not advance in
headless automation, so this evidence closes the reported source/compiler gap
but does not replace the still-open isolated-runtime TcUnit execution and fresh
test-TMC acceptance gate.

## 88. Runtime-test contract corrections after the first aggregate execution (2026-08-01)

The first isolated-runtime execution after the PLC-folder migration compiled and
ran all 27 suites, then exposed five failing test cases. A clause-by-clause audit
found no reason to relax production behavior:

- `FB_CycleProfiler` correctly derives elapsed time from `TIME()`. The profiler
  test opened and completed both cycles within one PLC scan, so its own measured
  minimum was legitimately zero. The test now keeps each cycle open across a
  task scan before asserting the Core §8.11 throughput markers.
- Core §3.10.2 defines the configuration manifest as a bounded page window. The
  Unit test assumed a stable write key remained on page zero after new base and
  generated entries were added. It now follows the advertised `PageCount` and
  searches every page while preserving the exact typed-write assertions.
- Core §6.1 maps `Error` from the owning lifecycle during `Cyclic()`. The invalid
  decision test faulted the private execution state through a protected probe
  and read the public output before that mapping pass. It now performs the next
  cyclic call before asserting the public fault and non-publication contract.
- The Press release policy is intentionally fail-safe. Child modules tick before
  the application-owned Unit release policy reevaluates their permits, so a
  restored two-hand input needs one scan to refresh the condition and one scan
  for the ram to consume it. Both restore assertions now observe that bounded
  propagation instead of requiring same-scan re-energization.
- The shared Press fixture tried to escape an open 500 ms AUTO dwell by issuing
  `Stop()` and several function-block calls inside one task scan. Those calls do
  not advance a TON, and stop-after-cycle correctly left the chain at N220. The
  cleanup now requests interruptible HOME, lets the normal Core §3.14.4 immediate
  mode-exit/Execute-drop handshake settle, homes the simulated devices, releases
  the terminal command, and commits AUTO before the next case.

The runtime warning that old persistent symbols such as `MAIN.AccessUsers` could
not be restored is independent: it is stale retained-runtime metadata after the
symbol rearrangement, not a command/release/test failure. Clearing or migrating
that retained data is a commissioning choice and was deliberately not automated.

The four changed TcUnit POUs parse as TwinCAT XML, `git diff --check` is clean,
the isolated wrapper build returns `LastBuildInfo=0` with an empty Error List,
and the nested `Fraktal_Tests Project` `CheckAllObjects()` call returns `TRUE`
with zero diagnostics. That compiler pass refreshed the aggregate wrapper's
common-ancestor `Fraktal_Tests.tmc`; no runtime configuration was activated or
downloaded. The acceptance gate remains a fresh isolated-runtime TcUnit run of
these sources.
That commissioning pass shall also clear **Autostart Boot Project** on the selected
test target: the XAE automation view reported it enabled, while §5.7 requires the
aggregate to remain non-autostart. Beckhoff defines this as a target-transferred
setting, so it was not guessed into the repository `.tsproj` or changed remotely
during a source audit.

## 89. Repeatable access-policy mailbox fixture (2026-08-01)

The next isolated-runtime run proved 91 of 92 tests, including every timing,
configuration-paging, decision, and Press recovery correction from §88. Its only
failure was `Mailbox_policy_is_self_gated_and_power_ack_is_authoritative`: the
fixture expected the `ACCESS_POLICY` threshold to begin at `NONE`, but TwinCAT
correctly restored `ADMIN` from the preceding successful run.

This is required production behavior, not a policy defect. Core §7.7(b) makes the
per-root policy persistent station configuration; “shipped default fully open”
describes a new/uncommissioned deployment, not a value to overwrite at every
restart. The test itself raises `ACCESS_POLICY` to `ADMIN` while authenticated,
so assuming that value disappears on the next execution contradicted the
contract it was testing.

`FB_Hmi_Tests` now commissions `ACCESS_POLICY` and `DATA_WRITE` to `NONE` through
the existing `ConfigureRequired` startup seam when its policy fixture initializes,
then sets `POWER_CONTROL` to `ADMIN` as before. The runtime mailbox remains the
only self-gated edit path under test; no production authorization or persistence
logic changed. The POU parses as TwinCAT XML, `git diff --check` is clean, and the
nested aggregate `CheckAllObjects()` returns `TRUE` with zero errors and warnings.
A fresh isolated-runtime execution remains the final acceptance step.

## 90. Tests and examples directory split (2026-08-01)

The former combined container mixed acceptance infrastructure,
generated test-runtime artifacts, reusable examples, and the physical Press
fixture in one ownership boundary. It is now split into `Tests/` and
`Examples/`: the aggregate TcUnit sources, test wrapper, dependencies, audit
tooling, and test-runtime artifacts live under `Tests/`; the generic demo,
Press demo, application wrappers, I/O configuration, and example runtime
artifacts live under `Examples/`.

`Fraktal_Tests.plcproj` deliberately remains directly under `TwinCAT/`, the
common ancestor of both branches. TwinCAT rejects parent-relative source links
in a PLC manifest, so the aggregate now uses only downward
`Tests\Fraktal_Tests\...` and `Examples\Fraktal_Press_Demo\...` compile paths.
The test XAE wrapper may reference that manifest as
`..\Fraktal_Tests.plcproj`; the no-parent rule applies to the PLC manifest's
compiled source links, not to the wrapper's project reference. The OPC UA
publication audit now defaults to the `TwinCAT/` root and resolves the Press
topology through `Examples/`.

Migration validation parsed 284 authored TwinCAT XML files, resolved all 270
compile includes across five PLC manifests, found no missing or
parent-relative compile source, and found no remaining authored reference to
the combined folder name. The publication audit passed. Isolated XAE loads of
`Tests/FraktalTests.tsproj` and `Examples/PressDemo.tsproj` each returned
`CheckAllObjects=TRUE` with zero real diagnostics; neither project was
activated or downloaded. This structural/compiler check does not replace the
separate isolated-runtime TcUnit acceptance gate described in §5.7.

## 91. Aggregate gate split in two; test manifest returned to `Tests/` (2026-08-01)

§62 hoisted `Fraktal_Tests.plcproj` to the `TwinCAT/` common ancestor so it could
link both `Tests/Fraktal_Tests/` and the Press example with downward-only paths.
That satisfied the `..` constraint but put a project manifest in the binding root —
the directory that has to stay free for further platform projects — and it proved
fragile: two folder re-layouts in succession left the manifest orphaned from its
sources, the second time with all 44 links dead and `FB_PressDemoUnit` undefined
across ~200 cascading compiler errors.

The manifest now lives at `Tests/Fraktal_Tests.plcproj` and owns only
`Tests/Fraktal_Tests/`. The two press-dependent suites — `FB_PressDemoUnit_Tests`
and `FB_FaultRecovery_Tests` — moved to a new
`Examples/PressDemo/PressTests.plcproj` (own solution, own `PRG_PressTestRunner`),
which reaches `Fraktal_Press_Demo/01_PneumaticPress/...` downward. Both gates must
be run; neither is a subset of the other. The press objects are still **linked, not
copied**, so that gate exercises the objects that deploy. `PressTests` must never
share a solution with `Fraktal_Press_Demo` (same source objects, duplicate GUIDs —
P1 rejects it). Only 2 of 34 suites were press-dependent, and both were
self-contained, so the split cost no shared fixtures.

Two rules learned the hard way, now enforced and documented:

- **`<Folder Include>` must mirror the `Compile Include` directories, never the
  `<Link>` paths.** XAE materializes those entries as real directories on disk
  relative to the manifest. Deriving the list from `<Link>` created phantom
  `Tests/Tests/`, `Tests/Examples/` and `Tests/PressDemo/{Io,Release,Sequences}`
  folders and left the source tree nested a level deeper.
- **`plc_lint.py` P1 must locate a project's ownership root, not assume a depth.**
  It computed `<manifest dir>/<stem>`; with the manifest one level up from
  `Tests/Fraktal_Tests/` that missed, fell back to the manifest's own directory,
  and claimed every sibling source in the tree — 226 false violations, with the
  fixture that described the correct behaviour already present and failing. The
  rule now searches for the same-named source directory beneath the manifest.

Not verified here: no TwinCAT compiler in this environment. Structural checks only
— every include resolves, no `..` segments, all project XML well-formed, both lint
profiles clean over 265 files, 21 linter fixtures green, and all 28 suites wired
into a runner. The next XAE build remains the authority.

## 92. Post-split compiler/runtime evidence and fieldbus profile reconciliation (2026-08-01)

The post-split authority checks are now real rather than inferred. A fresh local
TcUnit run of `Tests/Fraktal_Tests.plcproj` reports **84 successful, 0 failed, 84
total tests across 26 suites**. The two Press-owned suites are intentionally absent
from that result: `Examples/PressDemo/PressTests.plcproj` owns the remaining 8 tests
across 2 suites and still requires its own isolated-runtime run. The deployed Press
Demo remained running during all source/compiler work; no test configuration was
activated or downloaded.

The licensed CI placeholder was replaced with `tools/Invoke-TwinCatBuild.ps1`.
It opens each solution in a separate hidden Visual Studio/TwinCAT process, selects
`Debug|TwinCAT OS (x64)`, locates the hidden IEC project, and calls
`CheckAllObjects()` directly so an unavailable saved target cannot turn a PLC
compiler result into a system-level `Check config failed`. Both `FraktalTests` and
`PressTests` returned `TRUE`. `tools/tcunit_to_junit.py` validates all five TcUnit
summary fields, expected counts, zero failures, and total consistency before
emitting JUnit; its fixture tests and the supplied 84-test log are green. Hosted
runtime execution remains runner-owned because target selection/activation must be
isolated from any machine runtime.

XAE inspection also corrected §88's assumption that boot autostart could not be
represented in source. Both test `.tsproj` files now serialize
`BootProjectAutostart="false"`; XAE reload reports `False`, and the compiler gate
fails if either wrapper enables it. This is source configuration only and does not
alter an already activated target; the operator must still confirm the selected
test runtime before download.

The objective audit's former G4 was an over-specified mechanism, not a missing
diagnostic outcome. The normative base profile now matches the working ownership
split: `FB_EcBusHealth` supplies master-reported slave count/order/state/link and
configured-identity mismatch flags; the project I/O catalog supplies approved
tags, addresses, scaling and module ownership; the sole Hardware Driver supplies
live HAL/process-image values; and `FB_IoTopologyPublisher` validates/publishes the
join. Generic live CoE/PDO inference cannot author approved electrical identity or
Fraktal ownership, so `I_FieldbusScanner`/`FB_EcFieldbusScanner` remain an optional
fail-closed extension rather than a base-conformance requirement. `NodeCount` and
per-node `ChannelCount` already provide the compact active-length representation.

Finally, the gateway suite now includes a deterministic 4,000-path/four-WebSocket-
client acceptance case. After one-time discovery, each client's cyclic reply
contains only 120 consumed values and no repeated path vector; shared upstream
exclusions use the conservative client intersection, and a 600-value drill-down is
split into requests of at most 512. This closes the algorithmic scalability gap;
packaged real ADS/OPC-UA traffic/latency remains release evidence for the chosen
IPC and transport.

## 93. Runtime gate identity is runner plus count (2026-08-02)

An isolated Windows 10 x64 VM run supplied as the next test deployment completed
cleanly with 84 tests across 26 suites, but every reported suite was rooted at
`PRG_TcUnitRunner`. It therefore repeated the Core/Modules gate rather than
executing the intended two-suite Press gate, whose task calls
`PRG_PressTestRunner` and whose expected summary is 8 tests across 2 suites.

The discrepancy is deployment identity, not a test-source defect: the committed
`PressTests/PlcTask.TcTTO` calls `PRG_PressTestRunner`, and its manifest owns only
the two Press suites. The operating rule now requires matching both runner path
and expected counts before accepting runtime evidence. If a Press deployment
reports the Core runner, inspect the selected solution/application and stale boot
data on that isolated target. `BootProjectAutostart="false"` in the source wrapper
prevents a new autostart choice; it cannot erase a boot application previously
created on the runtime. The JUnit converter now requires `--expected-runner` and
fails on missing, mixed, or unexpected runner paths in addition to count/summary
failures. The VM result is archived as an independent Core/Modules repeat, while
the 8-test Press gate remains open.

The same check found post-rearrangement source drift in the Core wrapper:
`Tests/FraktalTests.tsproj` no longer serialized `BootProjectAutostart="false"`,
although the Press wrapper still did. The explicit false value is restored. This
protects future activations but still does not remove boot data already written
to the VM.

## 94. Complete split runtime gate and Press fixture boundary (2026-08-02)

The correctly selected `PRG_PressTestRunner` subsequently completed on the
isolated Windows 10 x64 VM: 8 successful, 0 failed, 8 total tests across the two
intended suites (`PressDemoTests` and `FaultRecoveryTests`). The fail-closed
runner/count validator accepted the archived raw output. Together with the
Core/Modules result, the split program is 92/92 tests across 28 suites. Evidence
and source/TMC hashes are recorded in
`Specification/Evidence/2026-08-02_Press_TcUnit.md`.

The preceding `PRG_TcUnitRunner.*` persistent-symbol restoration warning is stale
test-runtime metadata after replacing the Core application on ADS port 851, not
a Press failure. The old symbols were skipped and the correct Press runner then
completed. The VM USB-support warning is likewise non-blocking for this simulated
fixture.

Press Demo's scope is now stated without ambiguity: it is an internal Fraktal
feature-testing bench, not a real machine project, production reference,
conformance target, SAT, or safety-validation artifact. Its sequences, release
policy, simulated plant, illustrative I/O data, and 8-test gate exercise framework
integration. Any real project must own its engineering and independently satisfy
the deployment, electrical, risk-assessment, and certified-safety gates.

## 92. Short-circuit guard defects and lint rule C7 (2026-08-02)

A deep hunt across the PLC and HMI trees before publishing found two real PLC
defects, both of the same class and both on ordinary not-found paths — which is
why a green 92/92 TcUnit run could not have caught either.

IEC 61131-3 does not mandate short-circuit evaluation of `AND`/`OR`, and
TwinCAT's compile option for it is off by default. The protected operand of a
guard is therefore evaluated regardless:

- `FB_AsciiDeviceCM.SendRequest` used
  `IF _chan = 0 OR (_chan.State() <> OPEN)`, calling a method on a **null
  interface** whenever no channel is injected — a runtime fault, not a bad value.
  `OnCyclic` in the same file already guarded correctly with a separate
  statement, which is what identifies this as an oversight rather than a choice.
- `FB_LocalRecipeProvider.Load` used
  `IF (hit = 0) OR ... OR (_size[hit] <> Size)`, reading `_size[0]` of an
  `ARRAY[1..MAX_RECIPES]` whenever a recipe key is not found. The branch outcome
  is still correct, so it is silent today and becomes a bounds violation the
  moment a project enables the implicit `CheckBounds` POU.

Both are now separate statements; behavior is unchanged.

`plc_lint` gains **C7**: a guard may not dereference or index the symbol it is
testing against 0 within the same condition. Three fixtures cover the null-call
form, the 1-based-index form, and the split guard that must stay clean. The rule
was validated against the **real pre-fix sources from HEAD**, not only its own
fixtures — it reports exactly those two files at the right lines and nothing
else. That check exists because an earlier rule (D1) had been validated only
against fixtures and encoded the wrong invariant (see `OBJECTIVES_AUDIT_REVIEW.md`
§R0).

Swept and found clean in the same pass: ring-index math in every publisher (all
use the correct `(x MOD n) + 1` for 1-based arrays), sentinel-index guards in
`FB_AlarmLog`/`FB_CycleProfiler`/`FB_PermIntlk` (early-`RETURN` guarded),
division by a named operand in shipped sources (none), HMI ordinal-to-enum
conversions from PLC data (all range-checked or via the bounds-checked
`_enumAt`), the fieldbus topology recursion (a single `parent` field makes any
cycle unreachable from the `parent = 0` roots), and null assertions in the
PLC-facing Dart layer.

Not verified here: no TwinCAT compiler in this environment. Both edits are
structural only; the next XAE build remains the authority.

## 93. `_retVal` is a one-scan signal; `M_BeginScan` for chart languages (2026-08-03)

Building the SFC rendition of the AUTO chart surfaced a real gap: `M_Advance`
clears `_retVal` as part of committing the transition, which is correct when
`M_Advance` *is* the transition (ST), but leaves nothing to clear it when the
SFC/LD/FBD runtime owns the transition. The Nexeed reference drives its charts
exactly this way — step actions assign `_retVal := OK` / `JUMP1` /
`CheckUnitDone(...)`, and transitions are expressions such as `_retVal = OK` and
`(_retVal = OK) AND (_retVal2 = OK)`.

`FB_SequenceBase` gains **`M_BeginScan()`**, which clears `_retVal` and nothing
else. The owner calls it once per PLC cycle immediately before executing the
chart. Clearing at the top of a scan is equivalent to clearing after the previous
scan's transitions, and it additionally forces every step action to re-assert its
own result each scan — which is what makes a stale `ADVANCE` impossible rather
than merely unlikely.

The method deliberately does **not** touch `_driveIssued` or `_delay`. Those are
step-scoped: resetting them every scan would make `M_TryIssue` re-issue a child
command every cycle and stop `M_Delay` ever elapsing. They re-arm on step change
through `M_ClearTransition`, whose role is now documented as the shared *step
exit* action — the SFC exit action runs after the transition was evaluated, so a
chart may use it instead of `M_BeginScan`. `M_Advance` is unchanged, so the four
shipped ST charts and the 92-test runtime result are unaffected.

Two linter defects were found in the same pass, both of the "rule silently does
not apply" class:

- `POU_DECL` tolerated only the `ABSTRACT` qualifier, so
  `FUNCTION_BLOCK INTERNAL FB_SFC_PressDemoAuto EXTENDS FB_SequenceBase` parsed
  as name `INTERNAL` with no base. The object was registered under the wrong name
  and **every inheritance-keyed rule (D1/H1/A1/S1) skipped it**. The regex now
  accepts any combination of FB qualifiers, and `abstract` is derived from the
  qualifier list rather than from "was there a qualifier". Verified by reverting
  the fix: the new fixture fails with `'S1' not found in set()`.
- **S1 demanded the ST skeleton of every** `FB_SequenceBase` descendant. A chart
  body has no `CASE _step OF` and no `M_Advance`, so a legitimate SFC chart could
  only pass by pretending to be ST. S1 now recognises `<SFC>`/`<LD>`/`<FBD>`
  bodies and applies the chart contract instead: carry `_retVal`, record steps via
  `M_Step(`, and clear the result once per scan via `M_BeginScan(` or
  `M_ClearTransition(`.

`Sequences/AlterLanguages/` is declared **not built** (`NOT_BUILT_PARTS`): it holds
alternative-language renditions kept beside the shipped chart for comparison. Such
files are still linted for source rules but are neither conformance targets (S1)
nor compile-list omissions (P1). Before this, the in-progress SFC chart tripped P1
for being absent from every `.plcproj` — correctly, but for a file that is not
meant to be in one.

Not verified here: no TwinCAT compiler in this environment. The new method is
three lines of ST and the rest is tooling; the next XAE build remains the
authority.

## 94. SFC AUTO chart moved into the project and given the ST chart's behavior (2026-08-03)

`FB_SFC_PressDemoAuto` moved from `Sequences/AlterLanguages/` to `Sequences/` and
is now a compile input of `Fraktal_Press_Demo.plcproj`. Its declaration matches
`FB_PressDemoAuto` (same child references, `Setup`, `M_Reset`), and each
`CASE _step OF` branch of the ST chart became one ST method:

    A000_Initialize   A100_AwaitTwoHand  A110_RamUp      A130_DoorOpen
    A150_SlideInside  A170_TransferSettle A180_DoorClose A200_RamDown
    A220_PressDwell   A230_RecordResult  A240_ReturnToLoadPosition
    A999_CycleComplete

Each body is the ST branch verbatim with the trailing `M_Advance(...)` removed:
in a chart language the runtime owns the transition, so a step action only
produces `_retVal`. The N220 dwell keeps its hold-not-fault behavior (§ hard-lock
fix) unchanged.

**The chart graph itself is not generated.** A TwinCAT SFC body is a serialized
object graph (`SFCImplementationObject` → `SFCSegment` → typed nodes with
`Id`/`IdParent` identities and attribute GUIDs), and the only example available
in this repository contains one step, one transition, one jump and **zero**
`SFCAction` objects — there is no `<Action>` element anywhere in the tree either.
Synthesising twelve action-bearing steps from that would mean inventing the
majority of the schema with no compiler available to check it, and a malformed
archive is worse than none because it looks finished. The graph is therefore
drawn in XAE, where the work is mechanical: each step's action is one call
(`A200_RamDown();`) and each transition is `_retVal = E_StepResult.ADVANCE`. The
`N999 → N100` loop is the chart's back edge.

The owner must call `M_BeginScan()` once per PLC cycle before executing the chart
(§6.8). `FB_PressDemoUnit` still drives the ST twin; switching modes over is a
deliberate separate change, not a side effect of adding the chart.

S1's chart branch was relaxed to require only what a chart object can prove about
itself — `_retVal` and `M_Step(`. The per-scan clear is the owner's call or an
editor-wired exit action, neither visible in the chart file, so demanding the
token there produced a false positive on a correct chart.

The `NOT_BUILT_PARTS` / `AlterLanguages` exemption added in §93 was removed: the
folder no longer exists, and an unused, fixture-free exemption inside a gate is a
hole rather than a policy. Restoring it is six lines if language variants return.

## 95. The per-scan chain reset moved into FB_UnitBase (O1) (2026-08-03)

§93 introduced `M_BeginScan()` and §6.8 made calling it the *owner's* obligation.
That was the wrong side of the line for O1: a project adding an SFC chart would
have had to remember one call, and forgetting it produces an intermittent fault —
a transition firing on a result its step never produced — which is exactly the
class of defect the framework exists to make impossible.

The reset is now framework-driven and costs a project nothing:

- new `I_Sequence` interface exposes `M_BeginScan()` — the sliver of a chain its
  owner needs, the reverse of the `I_SequenceHost` bridge the chain receives;
- `FB_SequenceBase IMPLEMENTS I_Sequence` and announces itself from `M_Attach`,
  which every chain already calls at `Setup`;
- `I_SequenceHost` gains `M_SequenceRegister`; `FB_UnitBase` keeps a bounded
  `ARRAY[1..PL_Fraktal.MAX_SEQUENCES] OF I_Sequence` with idempotent registration
  (Setup may run more than once) and refuses rather than silently drops on
  overflow;
- `FB_UnitBase.OnCyclic` calls `_M_BeginSequenceScan()` immediately after
  `SUPER^.OnCyclic()`. `FB_ModuleBase.Cyclic` runs `OnCyclic()` before
  `_M_Dispatch()`, so the reset is guaranteed to land before any step action of
  the same scan.

Sizing: the press Unit attaches seven chains — three top-level plus the shared
`FB_PressDemoLoadPosition` nested in each of Home, Changeover, Auto and the SFC
Auto — so a bound of 16 leaves headroom. The null check before
`_sequences[i].M_BeginScan()` is a separate statement, per rule C7.

Project-side effect: **none required**. `FB_PressDemoUnit` is unchanged and
`FB_SFC_PressDemoAuto` needs no wiring; both simply inherit the guarantee. Core
§6.8 was corrected to state that the framework performs the reset rather than the
owner.

Not verified here: no TwinCAT compiler in this environment.

## 96. Composite sub-chains: M_RunSub, and the O1 trimming rule (2026-08-03)

Four charts repeated the same eight lines to run a sub-chain as one step — a
`_running` latch, a reset carrying the composite step number, the run call, a
`Done` test clearing the latch. `FB_SequenceBase` now owns all of it:

    _retVal := M_RunSub(Sub := _loadPosition, BaseStepNo := 240);

- `M_ChainRun` is a virtual no-op on the base. An ST sub-chain overrides it (this
  is the old `M_Run`); a chart-language POU leaves it alone, because its body *is*
  the chart and the runtime executes it. Only a chain used compositely overrides.
- `M_ChainReset(BaseStepNo)` is concrete on the base: `_baseStepNo` moved there,
  since offsetting a sub-chain's step records by its composite step number (§6.5)
  is a framework concept, not an application one. `OnChainReset` is the virtual
  hook for application state and is empty by default.
- `_subRunning` joins `_driveIssued` and `_delay` as step-scoped state cleared by
  `M_ClearTransition`.

That last point removed a real hazard rather than just lines. The Changeover
chart's `JUMP1` back to its composite step used to need an explicit
`_loadPositionRunning := FALSE;` to make the sub-chain restart; miss it and the
chain silently never runs again. A jump is a step change, so the base now clears
the latch on the framework's own path and the manual reset is gone.

Project code: **10 insertions, 73 deletions** across the five sequence files, and
`FB_PressDemoLoadPosition` lost its `_baseStepNo` and its whole `M_Reset`.

Core §1.1 gained the **O1 trimming rule** normatively, and AGENTS.md §3 leads with
it: repetition in more than one project object is a framework defect to absorb, a
project shall never be required to remember a call for correctness, and the
threshold is measured (more than once) rather than judged. §95's per-scan reset
and this change are its two worked examples.

Not verified here: no TwinCAT compiler in this environment. Note for the first
build — an ST chart used as a composite sub-chain must now override `M_ChainRun`
rather than `M_Run`; `FB_PressDemoLoadPosition` is the only such chain today and
has been renamed. Top-level chains keep `M_Run`, called by the Unit's adapters.

## 97. `Sub` is reserved; C2's word list completed (2026-08-03)

`M_RunSub`'s input was named `Sub`. `SUB` is the IEC 61131-3 subtraction
function, so the declaration parsed as an operator and the compiler emitted about
forty cascading syntax errors pointing at innocent lines — the exact failure mode
rule C2 exists to prevent. The input is now `Chain`.

C2 did not catch it because its word list was incomplete and inconsistently so:
`MOD`, `MAX` and `MIN` were present while `ADD`, `SUB` and `DIV` were not. The 43
missing IEC standard functions and operators are now listed.

They live in a **separate** `RESERVED_FUNCTIONS` set applied to variable
identifiers only, not to enumeration members. The shipped `E_CylinderPosition`
has a member `MID` and compiles: `{attribute 'qualified_only'}` keeps a member
clear of the `MID()` string function, so folding these words into the keyword set
would have produced a false positive on correct, working code. Both directions
now have fixtures — the four-keyword rejection and the qualified-enum acceptance.

One test-harness note worth recording: the suite's `_rules()` helper calls
`lint_repository`, which runs repository-scope rules only. Per-file rules (C1-C7)
must be asserted through `lint_file`, as the pre-existing C2 enum test already
did. `main()` runs both passes, so the CLI and CI were never affected — but a
fixture written against `_rules()` for a per-file rule silently passes nothing.

Not verified here: no TwinCAT compiler in this environment. The rename is
mechanical and lint-clean; the user's build is the authority.

## 98. SFC steps bound to their step bodies (2026-08-03)

The chart was drawn in XAE — twelve steps `A000`..`A999`, twelve transitions all
reading `_retVal = E_StepResult.ADVANCE`, and the `A999 -> A100` jump — leaving
only the step-to-body binding.

§94 declined to synthesise the SFC graph because the archive had no example of an
action-bearing step. With the drawn chart in hand that guesswork disappeared: the
archive carries its **own descriptor table**, mapping each attribute GUID to an
identifier and a description. It states outright that
`{700a583f-b4d4-43e4-8c14-629c7cd3bec8}` is `MainAction`, *"Name of the action to
be called if the step is active"*, alongside `EntryAction`, `ExitAction`,
`MinTime`, `MaxTime`, `InitStep` and the rest. Every step's ten attributes were
resolved from that table rather than inferred from position.

Two consequences decided the implementation:

- **MainAction, not EntryAction.** The bodies poll child `Done` flags and timers,
  so they must run every scan the step is active. An entry action runs once on
  activation and the chain would stall forever at the first step — a failure that
  looks like a hung machine, not a wiring mistake. Picking the wrong empty string
  attribute out of the five was the single real risk here, and the descriptor
  table removed it.
- **Actions, not methods.** `MainAction` resolves to an ACTION of the POU. The
  twelve generated METHODs are therefore now ACTIONs of the same names; each body
  is unchanged, with the documentation comment moved into the action body since an
  action has no declaration. `Setup` and `M_Reset` remain methods.

Verified structurally: XML parses, twelve `<Action>` objects exist, and every one
of the twelve steps names an action that is defined in the file. 267 files clean
in both profiles, 36 fixtures green.

Not verified here: no TwinCAT compiler in this environment. First build should
confirm that XAE resolves each `MainAction` name to its action and that the chart
advances past `A000` — if it stalls on the first step, the binding landed on the
wrong attribute despite the descriptor table.

## 99. Press-not-reached disposition path — a worked §6.10 jump (2026-08-03)

`FB_PressDemoAuto` gains a branch for the ram failing to reach the extended
position, as the reference example of a §6.10 jump:

    N200 --JUMP1--> N250 (operator confirms the failure)
                 -> N260 (part dispositioned NOK)
                 -> N240 (rejoin the existing return-to-start-position step)

**N200 no longer awaits the ram, and that is the whole design.** An *awaited*
child fault is adopted by `FB_UnitBase.OnCyclic`
(`IF (_awaits <> 0) AND_THEN _awaits.FaultActive THEN _M_FaultDiag(...)`), and
`_M_FaultDiag` sets `_exec := ERROR` and `_step := 0`. `FB_ModuleBase.Cyclic`
runs `OnCyclic()` before `_M_Dispatch()`, so the Unit is already in ERROR in the
same scan and the chain never gets a dispatch in which to offer the operator
anything. A chart that wants to own a child's failure must therefore stop handing
that child to the §6.9 auto-rollup; the wait stays named through `M_Await`
(§6.9(b)) and the cylinder still raises its own `CYL_NOT_EXTENDED` alarm, so
nothing is lost from the operator's view.

The trade is explicit and worth stating: during N200 the Unit will no longer
adopt a ram fault automatically. That is the point — the chain dispositions the
part instead of stopping — but it means any *other* ram failure in that step is
also the chart's responsibility now.

Two smaller decisions:

- N250 publishes the decision every scan. §6.11 specifies an idempotent active
  request, so ask-and-await collapse into the one step the operator sees, rather
  than the Changeover chart's split ask/await pair.
- `Default := 0` and `Timeout := T#0S`: scrapping a part is deliberate, so there
  is no silent timeout disposition.
- N999 checks `_partDispositioned` so a part already scrapped at N260 is not also
  counted good. `M_Reset` clears the flag.

The SFC twin gains `A250_ConfirmPressFailure` and `A260_ScrapPart`, and
`A200_RamDown`/`A999_CycleComplete` were refreshed from the ST bodies. The chart's
step and jump structure is drawn in XAE by hand; the JUMP1 branch out of `A200`
is the transition `_retVal = E_StepResult.JUMP1`.

Not verified here: no TwinCAT compiler in this environment.

## 100. Two-hand release during door close; failure branch renumbered (2026-08-03)

**Renumbered** the press-not-reached branch from N250/N260 to **N210/N215** to
match the steps drawn in the SFC (`A210`, `A215`). The numbers now follow process
position rather than insertion order, and the ST `CASE` was reassembled in numeric
order — §99 had left 250/260 sitting between 220 and 230, which read as if the
branch belonged there.

**New two-hand abort path.** Releasing a two-hand button while the door is closing
is operator intent, not a fault, so N180 gains a second jump:

    N180 --JUMP1--> N185 (door back up) -> N190 (slide out) -> N100 (two-hand wait)

- Completion wins the race: `IF _door.Done` is tested before the release, so a
  door that finished in the same scan the button was released still advances.
- The release is a named wait (§6.9(b)), so the stall walk can say *why* the step
  left, and `_door.Execute := FALSE` releases the close through the §6.1
  Execute-drop reset rather than aborting the child.
- N190 drops `_startLatched`, so the cycle cannot resume without a fresh two-hand
  press — returning to N100 alone would otherwise re-arm on the stale latch.

The SFC twin gains `A185_DoorReopen` and `A190_SlideOutsideAfterAbort`, and
`A180_DoorClose`/`A200_RamDown`/`A210`/`A215` were re-synced from the renumbered ST
branches. All fourteen drawn steps are bound to a defined action; `A185`/`A190`
are waiting on their steps.

**Open question for the next pass, deliberately not decided here:** the abort path
leaves the part lifecycle open. N100 called `M_PartReceived` and N150 called
`M_PartStarted`, but the abort returns to N100 without a `M_PartProcessed`, so the
part is neither dispositioned nor re-received cleanly. Whether an aborted part
should be scrapped, re-received, or tracked as the same part is a process
decision, not a framework one.

Not verified here: no TwinCAT compiler in this environment.

## 101. The two-hand abort keeps the same part; M_Reset actually clears now (2026-08-03)

Closing §100's open question, per the process decision: an aborted part is the
**same part**, because nothing was processed. N100 therefore receives a physical
part **once**:

    IF NOT _partInMachine THEN
        _traceAccepted := M_PartReceived();
        _partInMachine := TRUE;
    END_IF

`_partInMachine` is released where the part actually leaves — N215 on scrap and
N999 on completion — so the abort path can return to N100 as many times as the
operator likes without opening a duplicate §3.16.3 record for one physical part.

`M_PartStarted` (N150) is deliberately **not** guarded. Each pass is a genuine
processing attempt on that part, and collapsing them would hide a part that was
attempted three times before it succeeded.

**A defect this uncovered.** `M_Reset` never cleared `_partDispositioned` either —
the edit in §99 silently did nothing, because a `.TcPOU` method keeps its
declaration and implementation in *separate* CDATA blocks and the replacement was
written against the two concatenated. `M_Reset` was still just `M_ResetBase(0);`.
Left alone, a chart reset after a scrap would have carried `_partDispositioned =
TRUE` into the next cycle and skipped counting a good part. Both trackers are now
cleared there, in both charts.

The general lesson is worth stating because it will recur: text edits against
`.TcPOU` files must target one CDATA section. Matching across the boundary
produces a silent no-op, not an error — the same failure shape as a lint rule that
does not apply.

Not verified here: no TwinCAT compiler in this environment.

## 102. SFC abort branch bound; the two charts are at parity (2026-08-03)

`A185` and `A190` were drawn and are now bound to `A185_DoorReopen` and
`A190_SlideOutsideAfterAbort`. The chart is complete: **16 steps, 18 transitions,
2 jumps, every step bound to a defined action and no orphan actions.**

The two renditions are at parity. Both carry the same step numbers —
0, 100, 110, 130, 150, 170, 180, 185, 190, 200, 210, 215, 220, 230, 240, 999 —
and the same two branch points:

    N180 --JUMP1--> N185   (advance -> N200)
    N200 --JUMP1--> N210   (advance -> N220)

N240 is the one step with no `M_Step` call of its own: it delegates to the
sub-chain through `M_RunSub(Chain := _loadPosition, BaseStepNo := 240)`, which
offsets the sub-chain's own step records by 240 so the stall walk still reports
one continuous chain (§6.5). A parity check that greps for `M_Step(StepNo :=` will
therefore always show 240 as missing from the chart side; that is correct, not a
gap.

Not verified here: no TwinCAT compiler in this environment. The chart now has two
jump branches to exercise on the first run — release a two-hand button mid
door-close, and let the ram time out extending.

## 103. Sequence-language guide: ST vs SFC vs LD (2026-08-03)

`README.md` gains § "Writing a sequence: ST, SFC or LD" and AGENTS.md §3 gains the
operational form, so the SFC work is repeatable instead of folklore.

The organising idea is that only **who evaluates the transition** differs — ST's
`M_Advance`, the SFC runtime, or LD's rungs — and everything else follows: whether
the step body calls `M_Advance`, what a transition condition looks like, whether
`M_ChainRun` is overridden, and who clears `_retVal`.

Recorded because each cost real time to learn:

- The archive carries its **own descriptor table**. A step has ten attributes and
  five are empty strings; `MainAction` is
  `{700a583f-b4d4-43e4-8c14-629c7cd3bec8}` and the full GUID table is in the
  README. Binding `EntryAction` by mistake stalls the chain at its first step
  forever — a failure that reads as a hung machine.
- `MainAction` resolves to an **ACTION**, never a method.
- A `.TcPOU` edit must target **one** CDATA section; matching across the
  declaration/implementation boundary is a silent no-op that reports success.
- To own a child's failure a step must stop awaiting it, because the awaited-fault
  rollup runs before `_M_Dispatch`.
- The `FB_SFC_` prefix is **not a convention** — it exists only so two renditions
  of one chain can coexist in the demo. This is now stated in both documents.

**LD is specified but not yet implemented.** The README describes the
integer-state-machine form — one rung per state, `[EQ(_step, N)]──(A<N>_Action)`,
with the action keeping its `M_Advance` because the rungs do not evaluate
transitions. `FB_LD_PressDemoAuto` is not created here: an `<LD>` body is a
serialized object graph and there is **no LD example anywhere** to derive it from —
none in this repository and none in the Nexeed reference, which is entirely ST and
SFC. Synthesising one would be inventing a whole schema with no compiler to check
it. The SFC arrived the same way: the empty chart shell was created in XAE first,
after which filling and binding it was mechanical.

## 104. Ladder rendition: FB_LD_PressDemoAuto, and S1's `<LADDER>` blind spot (2026-08-03)

`FB_LD_PressDemoAuto` now carries its declaration, `Setup`/`M_Reset` and all
sixteen rung actions over the empty network TwinCAT created. Each action is the ST
branch **including** its `M_Advance` call: ladder rungs dispatch on `_step` but do
not evaluate transitions, so the action still commits its own result and the
`OnJump1..3` mapping keeps both jump branches declarative. The rung table is in
the README; every rung has the same shape, `[EQ(_step, N)]──(A<N>_Action)`.

**A ladder body is nothing like an SFC body.** Where SFC is a serialized object
graph, ladder is a single `ModelJson` attribute holding a JSON document:

    <o t="LadderImplementationObject">
      <v n="ModelJson">"{ "$type": "LadderDataModel", "Networks": [ … ] }"</v>

That is far more amenable to generation — `$type`-discriminated JSON rather than
`Id`/`IdParent` object identities. The remaining unknown is only the element
vocabulary (contact, box, connection), which **one drawn rung would supply**; the
other fifteen are then mechanical.

**S1 had a blind spot.** Its chart-body detection matched `<SFC>`, `<LD>` and
`<FBD>`, but TwinCAT writes a ladder body as **`<LADDER>`** — so the moment a real
ladder POU appeared, S1 demanded the ST skeleton of it and reported five missing
tokens. The rule applied, but to the wrong contract, which is the same failure
shape as a rule that does not apply at all. It now recognises
`<SFC>`/`<LADDER>`/`<LD>`/`<FBD>`/`<CFC>`, and distinguishes them: a `<LADDER>`
chain must carry `M_Advance(` because its rungs do not transition, while an
`<SFC>` chart must not need it. Two fixtures cover both directions.

Not verified here: no TwinCAT compiler in this environment. The rungs are not
drawn, so the POU compiles as a chain whose body does nothing until they exist —
the actions themselves are complete.

## 105. The ladder face is a base class: FB_SequenceBaseLd (2026-08-03)

§104 was wrong about how a ladder chain calls the framework. A rung has no
statement context — a box runs because **power reaches it** — so a method cannot
simply be "called from a rung"; it needs a boolean input to wire that power to.
The user's `FB_SequenceBaseLd` establishes the pattern: re-expose the step
vocabulary with `Run : BOOL` as the FIRST input and delegate to `SUPER^` when it
is TRUE. Nineteen further methods now follow those two, so the whole vocabulary is
wireable: awaits, gate/issue, delay, part lifecycle, decisions, stop/end-of-cycle,
fault, sub-chain and the shared exit action. A call with `Run = FALSE` is a no-op
and a value-returning one yields its fail-closed default.

The worked rung (N000) shows the shape: `EQ(_step, 0)` gates the rung, and the
boxes chain left to right through `InputItems` so power flows
`MOVE(_retVal := ADVANCE)` → `M_Step` → `M_Advance`, with a `BoxTreeAssign`
writing the three `_outCmd` flags. Rungs dispatch but do not evaluate transitions,
so each still ends in `M_Advance`.

**S1 had three blind spots, all found by this one file:**

- **`<NWL>`.** A ladder body is a *network list* — the `<LADDER>`/`ModelJson`
  form seen in the empty shell is not what TwinCAT writes once the POU has
  content. §104's fix matched `<LADDER>` and missed the real thing.
- **Direct-inheritance test.** S1 compared the base name for equality, so every
  chain behind `FB_SequenceBaseLd` was skipped entirely — the ladder POU was never
  checked. It now walks the chain with `derives()`.
- **ABSTRACT bases.** With the chain walk in place, `FB_SequenceBaseLd` itself was
  flagged for lacking `_retVal`. A base is scaffolding, not a chain.

Also: in a network list a call appears as a `BoxType` string (`"M_Step"`), never
the ST call syntax, so the token check matches names rather than `M_Step(`. Three
fixtures cover the chain walk, the abstract skip and an `<NWL>` body.

**Open risk, deliberately not resolved here.** Re-declaring an inherited method
with an extra input is not a signature-compatible override in IEC 61131-3. The
pattern is the user's and is followed consistently, but the first compile is the
authority; if it is rejected the fix is distinct names (`M_StepLd`, …) with the
same delegation bodies.

**Remaining rungs not generated.** The `<NWL>` graph is replicable from an
example, but N000 is unconditional — an `EQ` gate plus a straight box chain. Every
other step branches (`IF _pressRam.Done`, `IF M_TryIssue`, `IF/ELSIF`), and the
contact/branch vocabulary for that appears nowhere in this file. Generating them
would mean inventing that part of the graph with no compiler to check it, on a
file that has already been rebuilt twice. One conditional rung — N110 ram-up is
the smallest — supplies the missing vocabulary, after which the remaining rungs
are mechanical.

## 106. Sequence flow-chart contract (PLC half) (2026-08-03)

The HMI wants a per-module tab drawing the whole chain: every step, the active one
highlighted with its elapsed time, red when it outruns its guard, and click-through
from a step to the module it commands. Today only `CurrentStep` is published, so
the PLC half had to come first.

**The inventory is discovered, not authored.** `_M_SetStep` is the single funnel
every step of every chain already passes through, so `_M_RecordSequenceStep`
registers each step there the first time it is seen, matched by `StepNo` and
bounded by `MAX_SEQUENCE_STEPS` (32). A chain author writes **nothing** — the §1.1
O1 trimming rule applied to a new feature rather than retrofitted afterwards. A
step not yet reached is simply absent, which is honest: the chart shows what the
chain has actually done.

New/changed contract:

- `ST_SequenceStep` — StepNo, StepName, AwaitingLabel, **AwaitsPath**, TimeClass,
  ExpectedTime, Visited, LastDuration.
- `FB_UnitBase`: `SequenceSteps` + `SequenceStepCount`, `CurrentStepElapsed`,
  `CurrentStepTimedOut` (the same `_tStall` watchdog §6.9 stalls on).
- `FB_ModuleBase`: `SequenceViewEnabled` — every module can enable or suppress its
  own tab, so a type too simple to be worth drawing leaves it FALSE. `FB_UnitBase`
  defaults it TRUE in `OnInit`, and a concrete Unit may vary it per mode.

**`AwaitsPath` is the "direct wiring".** The drill-down target is the module the
step *declares* through `Awaits`, read once in `_M_SetStep` — no `IF`/`CASE` chose
it, so the link is unambiguous by construction. This gives the rule its teeth: a
step that wants to be click-through **shall** pass a constant module reference to
`Awaits` and command that module unconditionally in the same step.

Two consequences worth stating plainly:

- A step that passes `Awaits := 0` publishes an empty `AwaitsPath` and is therefore
  **not** click-through. Press AUTO `N200` is exactly this case — it dropped its
  await deliberately to own the ram's failure (§99), so it trades drill-down for
  disposition. That is a real trade the chart now makes visible.
- H1 caught this work in the act: the first version set `SequenceViewEnabled`
  before `SUPER^.OnInit()`. The gate was right and the line moved.

**Not done here: the HMI half.** The Flutter side needs the domain model, the
snapshot mapper rows, a `ModuleTabKind.sequence` tab rendering the chart, the
click-through into `AwaitsPath`, and the step-detail panel for a step with no
failure state. The contract above is what it will bind to.

Not verified here: no TwinCAT compiler in this environment.

## 107. Raising a step error the framework cannot see (2026-08-04)

§106 left a hole it named honestly: a step whose command sits behind an `IF`/`CASE`
cannot hand its child to `Awaits`, so nothing rolls the child's fault up and the step
waits until the stall guard with no link to what broke. `N200` chose that trade
deliberately, but it had to be a **choice**, not the only option.

Two calls on `FB_SequenceBase` close it, and the reaction is fixed rather than
per-step:

- `M_RaiseFromChild(Source : I_Module) : BOOL` — adopts the child's own first-out
  verbatim (`GetFaultSummary()`), with the child's path as the §3.13 drill-down link.
  Returns FALSE when the child is not faulted, so it is safe every scan.
- `M_RaiseCustom(Reason, DescriptionKey, Severity, Category, LinkPath) : BOOL` — a
  message the step defines itself, for a rule no module reports.

Both route through the new `I_SequenceHost.M_SequenceRaise(Diag, LinkPath)`, which
stamps `ErrorActive`/`ErrorSourcePath` on the **active** flow-chart row *before*
`_M_FaultDiag` adopts the diagnostic. Order matters: `_M_FaultDiag` sets `_step := 0`
on the Unit, and the row index has to be read while it still points at the raising
step.

**Stop is free; resume is the part that needed designing.** `_M_Dispatch` only runs
while `_exec = BUSY`, so the fault stops the chain by itself, frozen *on* the step —
its own `_step` is untouched (the Unit's `_step := 0` is a different variable). The
hazard is what happens after the operator clears it: the step would resume with
`M_TryIssue`'s one-shot already spent, `M_Delay`'s timer half-run and `M_RunSub`'s
latch set — i.e. still believing a handshake that failed. So `FB_UnitBase` now edge-
detects the *end* of ERROR (`_errClr : R_TRIG` on `_exec <> E_ExecState.ERROR`),
clears the row marks and calls `M_ResumeAfterError()` on every registered chain,
which calls `M_ClearTransition()`. The step re-issues and re-tests. Whether the chain
continues there or restarts from the top stays the project's call in `OnCommandStart`
— `FB_ProbeUnitRaise` exposes both through `RestartOnCommand`.

`Severity`/`Category` on `M_RaiseCustom` are a **proposal**, not the last word:
`_M_FaultDiag` runs `F_RationalizeDiagnostic`, so a reason in the §8.8 registry takes
the registry's priority and category and the inputs are ignored. They survive for a
project band code (10000+) — which is precisely where a message of a deliberately
different level belongs. The first draft of the doc comment claimed the caller always
won; reading `F_RationalizeDiagnostic` corrected it.

**The worked example is a test, not a demo edit.** `FB_ProbeRaiseChain` +
`FB_ProbeUnitRaise` + `FB_SequenceRaise_Tests` prove the three promises (stop, link,
re-evaluate). The probe unit registers its child and ticks it but deliberately does
**not** call `_M_RollupFault()` — that omission *is* the scenario. The press demo was
left alone: `N200` still owns the ram's failure, which the user confirmed needs no
raise, and inventing a use for it in a chain that runs on real hardware would have
been a behavioural change nobody asked for.

HMI half: `SequenceStep.errorActive`/`errorSourcePath`, and `linkPath` resolving
`errorSourcePath` **before** `awaitsPath` — the operator wants the module that
failed, not the one the step nominally commands. An errored row blinks red whether or
not it is still active (a timeout only ever marks the running step), and the step
detail lists the raiser.

No compiler here: structurally verified only — both lint profiles clean on 273 files,
every touched `.TcPOU` re-parsed as XML, 172 HMI tests and `flutter analyze` clean.
The TcUnit suite's first real run is the XAE download.

## 108. Messages that inform without stopping — §6.9(e) (2026-08-04)

§107 gave a step one reaction: stop. That is wrong for the two conditions the press
demo actually has, and both were asked for by name.

**N180 — two-hand released while the door closes.** Designed operator behaviour: the
door goes back up, the part slides out, the cycle returns to N100. Faulting there
would charge downtime for someone letting go of a button. But a cycle *was* abandoned
with the part still in the machine, so it belongs in the shift log.

**N200 — the ram did not reach.** The chain already owns this: confirm with the
operator, scrap the part, go home. It passes `Awaits := 0` precisely so the framework
does **not** adopt the fault (§99). The cost was that the failure existed only on the
ram module — the Unit said nothing. "Passed and displayed on the HMI, but it shouldn't
stop the sequence" is exactly the missing third option.

Three calls on `FB_SequenceBase`, none of which touch `_exec`:

- `M_RaiseWarning(Reason, DescriptionKey, Severity, Category)` — the step states the
  rule itself.
- `M_ReportFromChild(Source)` — the child's own first-out, published verbatim
  (`GetFaultSummary()`) but **not adopted**. The counterpart of `M_RaiseFromChild`.
- Both route through `I_SequenceHost.M_SequenceWarn(Diag)` → `FB_UnitBase`, which
  raises an **AUTO_RESET come+gone** ring entry (§8.3(c)) and stamps the active
  §3.13 row.

Three details that make it correct rather than merely present:

1. **AUTO_RESET is not cosmetic.** `_M_UpdateBlocking` only goes blocking on a
   `MANUAL_RESET` entry, so a message provably cannot gate the next `Start`. The test
   asserts `ResetClass` and `Blocking` rather than trusting the comment.
2. **Once per visit.** The step body calls it unguarded every scan; `_warnRaised` is
   step-scoped and `M_ClearTransition` re-arms it on commit. Without this the ring
   would fill with one entry per cycle of the task — the O1 rule again: a project
   shall never have to remember an edge latch for correctness. The test asserts
   `RingHead` moved by exactly one across three scans.
3. **`WarningSourcePath` is what makes N200 visible.** The row link is the *message's*
   subject, so a step that reports a child is click-through to that child even with
   `Awaits := 0` — the trade §106 made visible is now paid back. Precedence in the
   HMI is error → reported → declared `Awaits`, most specific first.

The mark is cleared when the step is **entered again**, not when the chain moves on:
an amber row means "this is what happened on the last pass", which is the useful
statement for a looping cycle.

New: `PL_PressReasons` (project band 12000-12999, `PRESS_TWO_HAND_RELEASED := 12001`).
A project code sits outside the shipped §8.8 registry, so `F_RationalizeDiagnostic`
leaves the step's chosen severity alone — which is what makes "a message of a
different level" actually possible rather than nominal.

Two sequencing defects in my own §107 tests surfaced while writing this and are
fixed: the first test asserted `SequenceStepCount = 3` when only two steps had been
reached (the inventory is honest about that — the assertion was not), and the
custom-message test ran on a chain that had already advanced past step 30, so it
would have exercised the completion step instead. It now uses its own Unit instance.

Structural verification only, as before: 274 files clean in both lint profiles, all
touched `.TcPOU`/`.TcGVL`/`.plcproj` re-parsed as XML, 175 HMI tests and
`flutter analyze` clean. The five-test TcUnit suite has never executed — the XAE
download is its first run.

## 109. Concurrent branches — §6.12 (2026-08-04)

A parallel branch was drawn into `FB_SFC_PressDemoAuto` (A250 on the main line,
A300/A310 on a second leg) with `_conRetVal : ARRAY[1..MAX_PARALLEL_BRANCHES]` added
to the base — a per-leg transition result, which is exactly the right first move: two
legs cannot share one `_retVal`. Finishing it turned up more that could not be shared.

**Every step-scoped latch had to become per-branch.** `_driveIssued`, `_delay`,
`_subRunning` and the §6.9(e) message latch are singular per chain. With two legs live
in the same POU, leg A's `M_TryIssue` consumed leg B's one-shot, so only one leg could
ever command a child — and `M_ClearTransition` cleared *all* of `_conRetVal`, so leg A
committing a step wiped leg B's result mid-motion. They are now
`ARRAY[0..MAX_PARALLEL_BRANCHES]`, indexed by a scan-scoped cursor. Index 0 is the
main line, which is every step of every chain that has no parallel branch — so
nothing existing changed.

**A latent bug fell out of it.** The re-arm of those latches lived in
`M_ClearTransition`, which ST reaches through `M_Advance` on commit. A chart language
never calls it — its engine owns the transition, so there is no commit point — and
nothing else re-armed anything. `M_TryIssue` therefore fired once per chart **RUN**
instead of once per step: the SFC rendition would have commanded its first cylinder
and then silently nothing. It never bit because `FB_SFC_PressDemoAuto` is compiled but
not instantiated. The re-arm now lives in `M_Step`, the one call every step of every
language makes, keyed by step number and branch.

**What stays singular is a decision, not an omission.** `CurrentStep`, the §6.9 stall
walk and the §8.11.4 profiler follow the **main line** only. A first-out has to name
one step; letting whichever leg ran last write them would make the walk report at
random. So a leg is timed and guarded on its own §3.13 row instead — `Active`,
`Elapsed`, `TimedOut` per row — which is also what the HMI needs to draw several live
steps at once. `_M_SetStep` keeps the signature every inline chain already calls; the
leg routing sits in the host bridge (`M_SequenceSetStep`), so no project call site
moved (§1.1 O1).

**The ST answer is not an array — it is a chain.** `M_RunPar(Chain, BaseStepNo,
Branch)` per leg plus `_retVal := M_ParJoin();` gives a leg its own instance, hence its
own step pointer, `_retVal` and latches by construction: the collisions above cannot
arise. It reads as §1.1 O4 applied to sequences — a work position is a *thing*, so make
it a type and instantiate it rather than duplicating its steps in a drawing — and it is
the only form that nests, is reusable, and works in ST. The leg list is the `M_RunPar`
calls themselves, so there is nothing to register and nothing to forget when a leg is
added (O1). It is documented as the preferred form; the native divergence stays
supported because a chart is often the clearest way to *show* two short legs.

**HMI.** Liveness moved from "the row whose StepNo matches CurrentStep" to the row's own
`Active` flag, with a documented fallback to the old rule when **no** row reports Active
— so the tab does not go blank against an older runtime. The rule is a named type
(`SequenceRowState.of`) rather than inline build logic, which is what made it testable
without standing up an AppState. Leg rows are indented and badged `∥n`, and a leg blinks
on its **own** guard.

The press demo's leg commands nothing on purpose: the press has one work position, and
inventing a second would change what the machine does. The steps are real (`M_Step`
with `Branch := 1`, records that reach the chart), so the pattern is live and visible —
the place a real second position would go is marked.

**Follow-up: the cursor is set by `M_Step`, not by a call before it.** The first cut
had a separate `M_Branch(Index := n)`. Folding it into `M_Step` as a defaulted input
removed a method from the base and a line from every leg step, and — the part that
matters more — made two mistakes unrepresentable: declaring a leg without recording a
step, and recording a step under the wrong leg because the declaration was forgotten.
The default is "this chain's own leg", which is the main line for a top-level chain and
the fork-assigned index for a chain running as a leg, so a main-line step and a
sub-chain leg both stay silent about branches. The cost is one [TC3] wrinkle: defaulted
method inputs are 4026+, so the declaration is pragma-guarded (rule C1) and a legacy
`FRAKTAL_TC3_4024` build must write `Branch := 0` at every `M_Step` call — the same
tax that profile already pays on `M_ResetBase` and `M_Advance`.

Structural verification only: 278 files clean in both lint profiles, every touched
archive re-parsed as XML, the SFC graph re-walked to confirm the branch is parallel
(legs open with a step, not a transition), 177 HMI tests and `flutter analyze` clean.
The two new TcUnit suites have never executed — the XAE download is their first run.

## 110. Derived state flags — §3.12 (2026-08-04)

Reading the Nexeed reference next to the press demo turned up a real modelling error
in ours. `OutCmd.Homed` was set by the HOME sequence and by CHANGEOVER, and cleared at
the start of AUTO. That is a **latch**, and a latch only a sequence can clear: jog an
axis off the reference position in MANUAL and the Unit goes on reporting `Homed` with
nothing running to contradict it. The reference gets this right by construction —
`StationOutImmStruct.TypeSetupOk` is an `OutImm`, recomputed, not announced.

The rule now written into §3.12: **ask what makes the value change.** A command
produced it and it stands until another command replaces it → `OutCmd`. It is simply
true right now → `OutImm`, derived every scan. `CycleCompleted` and
`ChangeoverCompleted` stay in `OutCmd` (a cycle ran; a changeover ran). `Homed` moved.

**`_M_State(Idx, Key, Ok) : BOOL`** on `FB_ModuleBase`, returning the value so the
assignment reads exactly as it did before. What it adds is the part nobody writes per
flag: the name, `Since` on the synchronized clock — "closed" is rarely the question,
"closed for how long" is — and a bounded generic table the HMI renders without knowing
the module type. Deliberately the same shape as `_M_Await(Idx, Label, Ok)`: one idiom
for "a named boolean the framework publishes", not two.

The part worth arguing about is **abandonment**. A flag is only honest if it is
published unconditionally every scan, and the mechanism must not be able to leave a
stale claim standing — that being the exact failure it exists to prevent. So a flag
not published in a scan is marked `Stale` and forced FALSE by a sweep at the top of
`Cyclic`, before that scan's `OnCyclic` re-publishes. The HMI renders `Stale` as
*unknown* rather than as a confident "off", because a forced FALSE is the absence of a
claim, not a claim.

Deriving `Homed` also exposed a duplicate: `OutImm.ReadyForLoad` was the same three-
cylinder expression written a second time. There is now one derivation, with
`ReadyForLoad` reading from it under the name the load gate uses (§1.1 O9).

**S1 was wrong about ladder, and the rebuilt ladder proved it.** Mid-work the ladder
came back driving `_step` directly from a MOVE box — the integer state machine
without `_retVal` or `M_Advance` — and the gate went red. S1 was demanding a
transition *mechanism* it had no business nominating: SFC progresses through `_retVal`
because its runtime reads it, ladder progresses by writing `_step`, and forcing a rung
through `M_Advance` to satisfy a linter is the tail wagging the dog. S1 now requires
what actually matters — the chart records its steps, and has *some* way to move
(`M_Advance`, `_retVal`, or `_step`). The fixture that encoded the old contract was
replaced with two that encode the new boundary, including a chart that records steps
but cannot progress at all, which is still rejected.

Removing `Homed` from `ST_PneumaticPressOutCmd` meant removing its assignment from the
ladder archive. My first attempt used a regex ending in `</o>`, which matched a nested
close and ate half the neighbouring operand — the file stayed plausible and stopped
being well-formed XML. Repaired by line range and re-parsed. The lesson is the one
already in the README about chart bodies: they are object graphs, so cut on structure,
never on a lazy regex.

Structural verification only: 280 files clean in both lint profiles, 42 linter
fixtures pass, every archive re-parsed as XML, `flutter analyze` clean and 178 HMI
tests passing. `FB_StateFlag_Tests` has never executed — the XAE download is its first
run, and it is also where the `OutCmd.Homed` removal proves itself, since two press
suites now assert `OutImm.Homed` instead.

## 111. Keeping M_Advance, and finally using its defaults (2026-08-04)

Once the ladder proved a chain can move by writing `_step` directly, the fair question
was whether `M_Advance` earns its place. It does, but not for the reason it looks like.

It is **not** what registers a step. `M_Step` is: `M_Step` → `M_SequenceSetStep` →
`_M_RecordSequenceStep` fills the §3.13 rows, and `FB_UnitBase` never reads `_retVal`
at all. So the HMI argument for keeping it is worth nothing.

What it earns is an **enforceable invariant**. `M_Advance` is the one place a step
declares its complete set of exits, and S1 uses exactly that: one `M_Advance` per
non-terminal `CASE _step` branch, terminal steps excused because they end with
`M_Complete()` or `Done := TRUE`. A step branch with no exit is a hung chain, and that
check finds it at commit time. Replace it with `_step := N` scattered through
conditionals and the property becomes "does some assignment to `_step` happen on every
path", which a regex gate cannot decide — it would need dataflow analysis. Trading an
enforced invariant for one saved line is a bad deal under §1.1 O9, and the graph being
readable from the last line of each branch is O2. So: **ST chains shall use
`M_Advance`; chart languages shall not be forced into it**, since neither SFC nor a
ladder rung has a commit point to hang it on.

The real simplification was already available and unused. `OnJump1..3` have had
pragma-guarded defaults since the compat policy was inverted — the policy document
even names `OnJump1 := -1, OnJump2 := -1, OnJump3 := -1` at 22 call sites as the thing
that inversion was *for*. Nobody then went back and deleted them. 32 call sites now
read `M_Advance(OnAdvance := 999);`, and the three real jumps in the demo stand out
instead of hiding among `-1`s.

That also settles a worry left open in §109. Using these defaults makes the demo
modern-profile-only, exactly like `M_Step(Branch := …)` does — but that was already
the intended direction the moment the policy was inverted, not a new cost introduced
by the parallel-branch work. A 4024 build writes the arguments out; that is the whole
content of the legacy profile.

Not changed: `M_Advance` still mirrors `ActiveStep := target` even though the next
scan's `M_Step` would set it anyway. Removing it would move `ActiveStep` a scan later
and shift assertions in two suites for no gain.

280 files clean in both profiles, 42 linter fixtures, archives well-formed, 178 HMI
tests. No compiler here — the XAE download remains the first real check.

## 112. Explicit split and rejoin: neither leg is the main line (2026-08-04)

The SFC parallel branch was re-cut so that **both** legs are numbered — leg 1 is
A200→A240→A250, leg 2 is A300→A310 — instead of leg 1 sitting on branch 0 and
borrowing `_retVal`. That is the better model and it should have been built this way:

- A simultaneous divergence has **N equal legs**. Numbering one of them 0 was an
  artefact of the `Branch` default, not of IEC. The §3.13 chart drew that leg
  unindented and the other indented, which reads as *subordinate* when they are peers.
- `_retVal` had come to mean two things: the single-threaded line outside the fork,
  and leg 1's result inside it. Now it means one thing — the line **before and after**
  the fork. Between them there are only `_conRetVal[n]`.

Two things fell out of it.

**The join was wrong.** It read
`_conRetVal[1] = ADVANCE AND _conRetVal[1] = ADVANCE` — leg 1 twice. It would have
committed the fork as soon as leg 1 finished, with leg 2 still running, which is the
one failure a join exists to prevent. Fixed to read leg 2.

**`M_RunSub` was hard-coding `Branch := 0`.** Spotted from the API surface: there was
no way to say which leg a composite step ran in. The right answer is not to add a
parameter — the framework already knows, because `M_Step` set `_branch` from the step
record. `M_RunSub` now passes `_branch`, so a sub-chain inherits the leg of the step
that runs it and publishes its rows there. Adding an argument would have re-created
exactly the defect that folding `M_Branch` into `M_Step` removed: a second place to
state the leg, free to drift out of step with the record. A240 is the live case — it
runs the load-position chain from leg 1, and those four steps now publish as leg 1.

Not covered by a test: the `M_RunSub` inheritance is a one-expression change, and
proving it in TcUnit would need a third probe type (an FB cannot contain itself, so a
leg cannot nest a leg of its own type). It is exercised by the press demo instead, and
is visible on the chart the moment the demo runs — the load-position rows appear
indented under leg 1 or they do not.

280 files clean in both profiles, archives well-formed, 178 HMI tests. As always the
XAE download is the first real check.

## 113. The flow chart belongs to the running mode (2026-08-04)

Tracing how `FB_PressDemoLoadPosition` appears on the §3.13 chart turned up a
boundary that was never drawn. Rows are **discovered** by visit (§6.5) — which is what
makes the chart free to author, and §106 was right about that — but discovery has no
end of its own. `SequenceStepCount` only ever grew, so after AUTO then HOME the
operator would be shown AUTO's rows and HOME's together, with only some of them live.

Worse, it was close to silent truncation. The three press mode chains hold 29 distinct
step numbers against `MAX_SEQUENCE_STEPS = 32`: three rows of headroom before
`_M_RecordSequenceStep` starts returning early and later steps stop appearing at all —
bounded, as designed, but invisible. Per mode the peak is 19.

`FB_UnitBase.OnModeChanged` now calls `_M_ResetSequenceRows()`. A mode is the right
boundary: within one mode a re-run keeps its rows, so `Visited` and `LastDuration`
stay meaningful across cycles, and a project writes nothing because the clear lands in
the base hook every override already calls `SUPER^` on first (§3.14.2). The clear is
bounded by the count actually in use rather than by `MAX_SEQUENCE_STEPS`, so a mode
change does not cost the whole 32-row table in one scan.

For the record, the answer to the question that started this: a sub-chain is
**integrated, not linked**. `M_RunSub` does not publish a row for the composite step —
in the demo N240 calls only `M_RunSub` — and the sub-chain is attached to the same
host, so its steps land in the same table at `BaseStepNo + n`: 240, 260, 280, 300,
appended in visit order exactly where the composite step runs. There is no second
chart and nothing to link. The branch is not looked up either: each row carries the
branch stamped by whichever chain instance published it, which is why `M_RunSub`
inheriting `_branch` (§112) was the whole fix.

280 files clean in both profiles, archives well-formed, 178 HMI tests, 42 linter
fixtures. The new `Sequence_rows_belong_to_the_active_mode` test has never executed —
the XAE download is its first run.

## 114. MAX_SEQUENCE_STEPS 32 -> 128, and why that forced a tiering decision (2026-08-04)

32 rows covered the demo and nothing else — a real station chain of a hundred-odd
steps is ordinary, and the overflow is **silent**: `_M_RecordSequenceStep` returns
early and the chart simply stops growing, with no diagnostic saying so.

Raising it is a two-sided cost, and it is worth knowing which side hurts:

| | 32 | 128 |
|---|---|---|
| PLC memory per Unit | 36 kB | 145 kB |
| Published OPC UA nodes per Unit | 544 | 2176 |

A row is 1156 bytes of which **98% is strings** — `StepName`, `AwaitingLabel`,
`AwaitsPath`, `ErrorSourcePath`, `WarningKey`, `WarningSourcePath`. If this ever needs
to go further, shortening those is the lever, not trimming fields.

The HMI widget was never the constraint: `ListView.builder` virtualizes, and the
mapper loops to the *published count*, not the array bound. **The wire was.**
`SequenceSteps` was un-tiered, i.e. cyclic, and 2176 nodes per Unit across a forest is
precisely what `opcua_field_tier.dart` already warns about for the rings ("at ~265
nodes each across a forest they dominate the fast read"). Quadrupling a cyclic payload
would have been shipping a scalability regression against §1.1 O4, which makes
published surface a first-class property. So `SequenceSteps` joined
`onDemandContainers`: read by targeted batch while the Sequence tab is open, never in
the cyclic snapshot.

That change had a trap in it. The tab's capability was
`sequenceViewEnabled && sequenceSteps.isNotEmpty` — and once the rows are on-demand
that deadlocks: no tab, so no read, so no rows, so no tab. It is now keyed on
`SequenceStepCount`, a leaf at the module root that stays live, along with
`SequenceViewEnabled` and the `CurrentStep*` pair. Two tests pin it: the capability
against a node with a count and no rows, and the tier classifier against both index
spellings plus the live root leaves.

The §113 mode reset matters more at this size, not less: it keeps a Unit's actual
usage near its longest single chain rather than the sum of every chain it has ever
run, and it bounds the clear loop by the count in use rather than by 128.

280 files clean in both profiles, 42 linter fixtures, `flutter analyze` clean, 179 HMI
tests. XAE download is still the first real check on the PLC side.

## 115. Splitting the flow-chart row by change frequency (2026-08-04)

The proposal was "publish the critical data by OPC UA and fetch the rest on demand by
mailbox". The instinct was right; two facts moved where the cut goes.

**Sorting the 1131 string bytes by how often they change** shows the obvious split is
the wrong one:

| | fields | bytes |
|---|---|---|
| static per row | `StepName`, `AwaitingLabel`, `AwaitsPath` | 498 |
| dynamic | `ErrorSourcePath`, `WarningKey`, `WarningSourcePath` | **633** |

"Static text on demand" would have left the larger half behind. But the dynamic
strings are **sparse** — one error at a time, and a message only until its step runs
again — so every row was reserving 633 bytes for a case that is almost always empty.
They belong in a side table, not on the row.

**And no new mailbox was needed.** Fraktal already has two on-demand paths: the
`onDemand` field tier (targeted batch read while a view is open) and §3.10.2
`M_AppendConfig`/`FB_ConfigPager`, whose stated job is serving static facets kept off
the cyclic tree. A third would have been O9 debt.

The result is three tables:

| part | mechanism | 128 rows |
|---|---|---|
| live scalars (`ST_SequenceStep`, 25 B) | on-demand array read | 3.1 kB |
| static text (`ST_SequenceStepText`, 323 B) | config manifest, `OPC.UA.DA := '0'` | 40.4 kB |
| notes (`ST_SequenceAnnotation`, 205 B × 16) | on-demand array read | 3.2 kB |

**47 kB per Unit, down from 145 kB**, and the cyclic-capable node count drops from
2176 to 1408.

Two details that made it work cleanly:

**The manifest publishes the text under the LIVE half's browse paths.**
`M_AppendConfig` emits `SequenceSteps/SequenceSteps[3]/StepName`, which
`_indexedAlternatives` already recognises, so `synthesizeManifestValues` lands it on
exactly the key the mapper was already reading. The HMI mapper needed **no change** for
the static half — one row structure, half of it live, half fetched once and cached.

**The row flag stays authoritative, not the note.** The note table is deliberately
small (16). If it fills, `_M_SequenceAnnotate` returns FALSE *after* the caller has
already set `ErrorActive`/`WarningActive`, so a full table costs the text and never the
mark. Deriving the mark from the note would have silently unmarked a real failure; there
is a test for exactly that.

Also folded in the free win: `AwaitsPath`, `ErrorSourcePath` and `WarningSourcePath`
were `STRING(255)` but are copied from `I_Module.Name`, backed by
`FB_ModuleBase._name : STRING(80)`. They are `STRING(80)` now — 175 bytes per field
that could never be used. That also makes the contract explicit: a drill-down link is a
*module path*, bounded by the module's own name.

282 files clean in both profiles, 42 linter fixtures, `flutter analyze` clean, 180 HMI
tests. The PLC half — the annotation table, the manifest export — has never executed;
the XAE download is its first run, and the first place the manifest path spelling gets
checked against a real TF6100 namespace.

## 116. Liveness per leg, history per row (2026-08-04)

The question was whether every step needs live data at all, or whether only the active
ones should be published and the HMI could assemble the rest. Sorting the eleven live
fields by whether a client could reconstruct them gave three groups, and the middle one
is the interesting one:

- **Four were never live at all.** `StepNo`, `Branch`, `TimeClass`, `ExpectedTime` are
  fixed from a step's first visit. Leaving them in the live array after §115 was an
  oversight; they joined the text in `ST_SequenceStepDef` (renamed from
  `ST_SequenceStepText`, since it is no longer only text).
- **Three can move, safely.** `Active`, `Elapsed`, `TimedOut` are only meaningful for a
  running step, and a leg runs exactly one at a time — so they became `ActiveSteps`, a
  cursor **indexed by branch**: ~10 entries however long the chain is. Small enough to
  be live tier, which is a UX gain as well as a saving: the chart is correct the instant
  its tab opens instead of after the first on-demand read.
- **Four must not move.** `Visited`, `LastDuration`, `ErrorActive`, `WarningActive` are
  per-row history. An HMI polls at a few Hz; the PLC steps at scan rate. A step shorter
  than one poll interval is never observed, so a client that accumulated these would
  silently skip exactly the fast steps, mistime visits, and lose a fault that raised and
  cleared between two reads. That is the difference between a chart showing what the
  chain **did** and one showing what somebody happened to catch — §1.1 O3 is diagnosable
  by construction, not by luck.

| | after §115 | now |
|---|---|---|
| PLC memory per Unit | 47 kB | 46 kB |
| leaves read while the tab is open | 1408 | **576** |
| leaves read cyclically | 0 | 30 (the cursor) |

The memory barely moved — that was never the problem. **Leaf count** was: reads here
are per-leaf sum-reads with batch handle resolution, and 1408 handles for one open tab
is real pressure on a finite pool. 576 is a 2.4x cut with nothing inferred client-side.

Two things fell out of moving the clock from the row to the leg. The per-scan sweep is
now ~10 iterations instead of up to 128, because it sweeps legs rather than rows. And
`LastDuration` is frozen by that sweep from the cursor's own elapsed, which is exactly
the value the HMI could not have measured.

A further ~2x is available by bit-packing the three row booleans into a flags byte
(~286 leaves). Not taken: the HMI would need to know bit positions, which breaks the
"binds to named fields, knows nothing about the module type" property §3.13 exists to
protect.

283 files clean in both profiles, 42 linter fixtures, `flutter analyze` clean, 181 HMI
tests. The PLC half has never executed; the XAE download is the first check, and the
first place the `ActiveSteps` index base (the cursor is `ARRAY[0..n]`, so the HMI probes
both zero- and one-based spellings through `_indexedPrefix`) gets confirmed against a
real TF6100 namespace.

## 117. Live channel state; the RS232 terminal joins the bus view (2026-08-04)

**Channel value promoted to live.** The whole `Topology` subtree was on-demand, which
also gated the one field an operator watches without opening the bus page: an
interlock that will not clear, a sensor that never comes on. `BoolValue` and
`AnalogValue` are now `liveLeaves`, checked BEFORE the container rules so a leaf can
outrank the on-demand subtree it sits in. One leaf per channel; `Address`, `Path`,
`Diagnostic`, `Forced`, `Quality` stay gated. Two existing suites asserted the old
contract and were updated rather than worked around — `opcua_repository_test` now uses
`Forced` as its on-demand exemplar, since the value it used to pick is live.

**The EL6001 was on the bus and invisible.** Checking the XTI export settled what is
physically there:

| slave | mapped before | now |
|---|---|---|
| `=000+S-K010 (EK1200)` coupler | node, no channels | unchanged — it has no process data |
| `=000+S-K010B1 (EL1809)` 16 DI | node + 15 channels | unchanged |
| `=000+S-K010C1 (EL2809)` 16 DO | node + 10 channels | unchanged |
| `=000+S-K010D1 (EL6001)` RS232 | **node, no channels** | node + 8 channels, process image mapped |
| `=000+S-K010E (EL9011)` end cap | node, no channels | unchanged — passive |

So the tree was not missing devices; the EL6001 was missing its *channels*, which is
the same thing from an operator's chair. Mapping it needed a Core addition: the
publisher could only express digital channels, while a serial terminal's process image
is bytes. `E_ChannelKind.ANALOG` already existed in `ST_IoChannel` — only the API was
absent — so `M_DefineAnalogChannel` / `M_SetAnalogValue` mirror the digital pair
exactly, same validation, differing only in `Kind` and the engineering unit.

The terminal belongs to no module (nothing speaks a protocol over it yet), so its
channels carry the Unit as `ModulePath`: the bus view still shows and forces them, and
cross-navigation lands somewhere honest rather than nowhere.

**Flagged, not guessed:** the `TcLinkTo` names are the EL6001's *default* 3-byte PDO
assignment (0x1A00/0x1600). The terminal also offers 5- and 22-byte variants, and the
XTI lists all of them as alternatives without making the active choice readable. If
XAE is set to another variant the link names differ and the build will say so — the
comment in `GVL_PressIO` says exactly this, in the same style as the existing warning
on the N54 button channels.

283 files clean in both profiles, archives well-formed, 182 HMI tests.

## 118. Misfiled types and speculative flags — and the rule that stops both (2026-08-04)

Two questions ("why is `ST_PneumaticPressOutCmd` inside a library?" and "what about
`ChangeoverCompleted`, only written, never read?") turned out to be one habit, so the
answer had to be a gate rather than a paragraph.

**The scan.** Two passes over the PLC tree: types a library declares that nothing in
that library uses, and struct fields written by the PLC that neither the PLC nor the
HMI reads. Both raw outputs needed judgment, and saying why is the useful part:

- *"Used only from outside" is not misfiling.* The first pass flagged
  `FB_CylinderSim`, `FB_TwoHandStartCM`, `FB_ClampStationUnit`, `FB_TcpVisionCM` and a
  dozen more — every one correct, because being used from outside is what a reusable
  type is *for*. The real signal is narrower: no object **owns** it, i.e. nothing in
  the Framework tree declares a member of that type.
- *`OutImm` fields with no named reader are not orphans.* The second pass flagged the
  whole of `ST_PneumaticPressOutImm`, but `OutImm` is by definition the published live
  facet: its consumer is the generic HMI tree, which renders what is published without
  naming fields in Dart. Deleting those would have removed the contract to satisfy a
  grep.

**The one real misfiling** was exactly the four `ST_PneumaticPress*` DUTs: in
`Fraktal_Modules`, owned by no library FB, referenced only by the press project — while
`ST_ClampStation*` sit correctly beside the `FB_ClampStationUnit` that declares them.
Moved to `01_PneumaticPress/DUTs/` in the project. Every consumer of the module library
stops carrying a press it does not have.

**Rule L1** now enforces it, and getting it right took three corrections that are worth
recording because each was a false positive with a different cause:

1. Ownership must include `REFERENCE TO` — that is how a CM owns its HAL struct
   (`ST_CylinderHal` and four siblings looked unowned).
2. It must include `ARRAY[..] OF` — that is how `ST_BusNode` owns `ST_IoChannel`
   (three correctly-placed Core types looked misfiled).
3. It must span the **whole Framework tree**, not one library — `ST_IoPointIdentity`
   lives in Core and is owned by Modules, which is correct layering, not a defect.

Three fixtures pin those boundaries so the rule cannot silently loosen back.

**On speculative flags.** `ChangeoverCompleted` is written by two chains and read by one
test assertion; nothing in the machine and nothing in the HMI consumes it. The standing
rule going into AGENTS.md: declare a flag when something needs it. A published field
with no consumer is not readiness, it is surface everyone pays for. (`CycleCompleted`
is the near miss that stays: two unit types write it, so it is a convention rather than
a one-off — but it has no reader either, and should get one or go.)

283 files clean in both profiles, 45 linter fixtures. The XAE gate remains red for
reasons predating this session (§119 note pending the error text).

## 119. The library compiles — and what a whole session of "unverified" was hiding (2026-08-05)

Every report in this session ended with "no PLC compiler in this environment; the XAE
download is the first real verification." That was an assumption I never checked, and
it was false: TwinCAT 3.1.4026 and `VisualStudio.DTE.18.0` are installed here and
`tools/Invoke-TwinCatBuild.ps1` runs. The cost of not checking was a session of work
built on a base that did not compile.

**What the compiler said, once §5.1 of the workflow doc made the Error List readable.**
The DTE2 qualification is the whole trick — a COM object from `VisualStudio.DTE.<n>` is
seen by PowerShell as base `EnvDTE.DTE`, whose `ToolWindows` probe returns nothing, which
is exactly the misleading empty result I hit three times and nearly concluded was a
tooling dead end. Through `DTE2`: **27 × `C0094: Interface of overridden method ...
doesn't match declaration`**, every one in `FB_SequenceBaseLd`.

That is precisely the risk flagged and left unresolved four times in this session:
*"FB_SequenceBaseLd re-declares inherited methods with an extra `Run` input, which is not
a signature-compatible override; if the compiler rejects them the fix is distinct names."*
It did reject them. Writing a risk down is not the same as retiring it.

**The fix, in three parts** — and parts two and three were only visible because each
compile pass revealed the next layer:

1. The facade methods are **not overrides**. A method that adds `Run : BOOL` for rung
   power flow is a different method that happens to delegate, so it takes its own name:
   `M_StepLd`, `M_AdvanceLd`, … 27 of them. `SUPER^.M_Step(...)` targets are untouched.
2. A method returns through **its own name**, so every body still assigning `M_Await :=`
   was now assigning to the inherited *method*, not the return variable — 34 ×
   `Cannot convert type 'BOOL' to type 'M_AWAIT'`. Retargeted, delegation calls excluded.
3. The ladder calls the facade by name, so `FB_LD_PressDemoAuto`'s `BoxType` operands
   follow (`M_StepLd`, `M_PartProcessedLd`, `M_CountGoodLd`), and rule S1 accepts either
   spelling with the reason recorded inline.

**Result: `CheckAllObjects = True`, 0 errors, 0 warnings — for both Fraktal_Core and
Fraktal_Modules.** Everything this session added to Core compiles: the raise/report API,
the message path, concurrent branches, the split flow-chart row with its cursor and
annotation tables, derived state flags, and the analog channel API. The `ST_PneumaticPress*`
removal is validated too — Modules compiles clean without them.

**Why nobody had seen it.** The gate asserted `BootProjectAutostart` is off and threw
*before* `CheckAllObjects` for `Fraktal_Core`. That assertion is a test-project rule — a
test app must not auto-start on a runtime — and a library is never downloaded, so it is
meaningless there. Applying it anyway meant **neither library was ever compiled by CI**,
and 27 errors sat in a library the gate reported on without ever checking. The gate now
skips the assertion for the two library solutions and includes them, in dependency order,
in its default list.

Still outstanding: `FraktalTests` and `PressTests` return FALSE because `Fraktal_Core`,
`Fraktal_Modules` and `TcUnit` are not in this machine's Library Repository. That is the
*Save as library and install* step the workflow doc describes and the automation
deliberately never performs, so the seven new TcUnit suites remain unexecuted — but they
are now the only thing between here and a real test run.

## 120. SFC step naming: N for steps, A for actions (2026-08-05)

The SFC chart's steps were renamed `A<n>` → **`N<n>`** (`A200` → `N200`, and the join
placeholders `_aA250_active` → `_aN250_active`); the action objects keep `A<n>_<What>`.

It is a small change that removes a real friction. `N` is already the step token
everywhere else in Fraktal — `M_Step(StepNo := 200)`, the `200:` label in the ST twin,
the `N200` row on the §3.13 chart, the `Step N200 stalled → …` first-out message. The
chart was the only surface calling it `A200`, so a reader tracing one step across the
chart, the code and the operator's screen had to translate at exactly the moment they
were already confused.

Keeping `A` on the *action* is the other half: in the archive a step and its
`MainAction` are separate objects bound by GUID, and `N200 → A200_RamDown` says which
is which without opening either. Same number, different prefix, no ambiguity.

Documented in the README's SFC build procedure and in AGENTS.md so a generated chart
follows it.

## 121. What it takes to write a ladder chain unaided (2026-08-05)

With N000/N100/N110/N999 drawn, the ladder vocabulary is complete and the procedure is
now written down in the README (§ "Writing a Ladder sequence rung by rung"). The two
rung shapes cover every step of every chain: pure logic, and command-a-child. A jump is
not a construct — it is a second `MOVE` under a different contact. A terminal step
completes and does not `MOVE`.

What made this hard to write earlier was not the drawing, it was three facts only the
compiler could settle, all now recorded:

- the facade methods are **not overrides** (`C0094`), so they carry `Ld` names;
- a method returns through **its own** name, so renaming one without retargeting the
  body's `<name> :=` silently rebinds it to the inherited method;
- a ladder box's `BoxType` must name the facade, not the base, or it has no `Run` pin.

**Why the remaining rungs are still not generated.** Two blockers, one of them mine:

1. `FB_LD_PressDemoAuto` reports two unresolved lazy-typed implicit variables
   (`ImpVar597_1`, `ImpVar616_1`) — editor-generated intermediates for rung results
   whose type cannot be inferred, i.e. a dangling or mistyped pin in an existing rung.
   Until the file compiles, a generated rung's errors cannot be told apart from the
   ones already there, and that is precisely the confusion that hides real defects.
2. The EL6001 `TcLinkTo` names were a guess and were wrong: XAE reports
   `TIIB[=000+S-K010D1 (EL6001)]^Inputs^Status` not found, so the terminal is on a
   different PDO assignment than the default 3-byte one. The links are **removed**
   rather than guessed a second time; the variables and their §10.5.1 topology channels
   stay, so the card is still published and visible, and the comment says exactly what
   to read off the Process Data tab to restore them. A wrong `TcLinkTo` fails the build
   loudly, which is the right failure mode and the reason not to leave a plausible one
   in place.

The demo now has a real oracle (Core and Modules are installed as libraries), so once
those two are cleared each generated rung can be `CheckAllObjects`-verified as it is
added, rather than twelve at once.

The implicit-variable diagnosis above is superseded by §122: the generated names do
identify the exact archive boxes, and the defect is nested method-return composition,
not an unlocatable editor variable.

## 122. LD implicit-variable audit: the generated name locates the graph defect (2026-08-05)

An archive-level audit of `FB_LD_PressDemoAuto` resolved the two names from §121
without opening the graphical editor. In this XAE archive the convention is
`ImpVar<BoxId>_<output ordinal>`:

- `ImpVar597_1` is output 1 (`BOOL`) of `M_AwaitLd` box ID `597`; that box is nested
  as an input of OR box `612`.
- `ImpVar616_1` is output 1 (`BOOL`) of `M_AwaitLd` box ID `616`; that box is nested
  into the `Run` input of outer `M_AwaitLd` box `614`.
- box `614` is then assigned to `_startReady` by assignment node `605`.

Therefore §121's “dangling or mistyped pin whose source cannot be inferred” was not
accurate. The names are generated by XAE, but the numeric stem maps directly to the
serialized `<v n="Id">…L</v>` node. Both outputs are connected and both descriptor
tables already say `BOOL`. What TwinCAT cannot type is the *nested method-return
temporary* created by the composed graph.

The graph is also behaviorally wrong compared with both authoritative renditions.
ST N100 and SFC action `A100_AwaitTwoHand` make three independent assignments:
`_partReady := M_Await(Idx := 1, …)`, `_airReady := M_Await(Idx := 2, …)`, and the
conditional `_startReady := M_Await(Idx := 3, …)`/`TRUE`; only afterwards do they
combine `_partReady AND _airReady AND _startReady`. The LD graph instead serializes
those calls inside one `_startReady` expression, uses an inner result as another
call's `Run`, and contains no assignment operand for `_partReady` or `_airReady`.
That can suppress later waits and their diagnostics when an earlier wait is false.

The correction rule is now explicit in the TwinCAT README and AGENTS.md: draw each
value-returning facade call as its own box with an explicitly typed result local;
combine only the locals in a later logic/transition branch. `Run` carries rung power
only. The graphical repair should still be performed in XAE because `<NWL>` is a
serialized editor graph, but no unknown XAE-generated variable must be guessed.

Validation caveat found during this audit: `PressDemo.slnx` could not be exercised by
the test-only hidden helper because its deployed PLC has `BootProjectAutostart=TRUE`,
which that helper intentionally rejects. `PressTests.slnx` is safe to check but does
not include `FB_LD_PressDemoAuto`; after the latest folder/type movement it also omits
the project-owned `ST_PneumaticPress*` DUTs and reason list, so its current check stops
with 136 cascading unknown-type errors. It is not an LD oracle until that manifest is
reconciled. The LD-specific evidence here is the reported two compiler names plus the
deterministic archive mapping above.

## 123. PressTests is green again — the DUT move had broken it (2026-08-05)

§122's validation caveat was a regression I introduced. Moving the four
`ST_PneumaticPress*` DUTs out of `Fraktal_Modules` (§118) fixed the layering, but
`PressTests.plcproj` compiles the demo **sources** directly and had been resolving
those types through the module library. With them gone from the library and not added
to its manifest, the check stopped with 136 cascading unknown-type errors — the
"oracle" was reporting my own manifest omission, not the ladder.

Fixed by listing the four DUTs plus `PL_PressReasons.TcGVL` (which `FB_PressDemoAuto`
now references) and the `DUTs` folder in `PressTests.plcproj`.

**Result: `CheckAllObjects = True`, 0 errors, 0 warnings.** That covers
`FB_PressDemoUnit`, all four ST chains, the release FB, the fieldbus GVL and both press
suites — so essentially every ST change this session is now compiler-verified: the
§6.9(d) raise, the §6.9(e) message and `M_ReportFromChild`, `Homed` moving to `OutImm`
via `_M_State`, the project reason band, the `M_Advance` default simplification, and
the DUT relocation itself.

Worth noting why lint did not catch it: rule P1 checks that authored sources under a
project root appear in that project's compile list. These DUTs live under the
`Fraktal_Press_Demo` root and are consumed by a *different* project, `PressTests`, and
no rule looks at cross-project source borrowing. That is a genuine gap — a second
project compiling another project's sources is exactly where a manifest drifts
silently — and is the obvious next lint rule.

## 124. M_MayIssue -> M_TryIssue (2026-08-05)

A question-shaped name on a call that consumes what it reports. `M_MayIssue` reads as a
predicate — ask twice, same answer — but when the gate opens it latches
`_driveIssued[_branch]`, so the second call in a step returns FALSE and the command
silently never issues. Command/Query Separation, and the kind of defect that survives
review because the call site reads correctly.

`Try*` is the established convention for attempt-and-report, and it matches the real
contract including the part that is easy to miss: a **closed** gate returns FALSE
*without* consuming, so retrying on the next scan is correct. It also restores the
imperative-verb convention every sibling follows (`M_Step`, `M_Await`, `M_Advance`,
`M_Delay`, `M_RunSub`, `M_Gate`) — `M_MayIssue` was the only interrogative, because it
was conceived as a predicate and implemented as a consuming operation.

`M_BeginCommand` was the runner-up and was rejected: `OnCommandStart` already exists on
the module base and means something else (the Unit's own command edge), and the
near-collision would have cost more than the clarity gained.

59 occurrences across the base, the `Ld` facade, the ST/SFC/LD renditions, the probes
and the specification. `Fraktal_Core` verifies green (`CheckAllObjects = True`).

**Consumers need the library re-installed.** `PressTests` compiles against the
*installed* `Fraktal_Core` (0.4.0.0), which still exports `M_MayIssue`, so it now
reports 30 errors until Core is rebuilt and re-installed via **Save as library and
install**. That is the documented dependency order, not a defect — but it is the first
time this session a Core API rename has been made, and it is worth recording that the
source-green/consumer-red window is expected and is closed by the install step.
## 125. The §3.13 flow chart never told the HMI it had changed (2026-08-07)

**Symptom.** The HMI's sequence view rendered every row as `N0` with an empty
drill-down, intermittently — sometimes correct, usually not.

**Cause.** A chart row is deliberately split in two: the LIVE half (`Visited`,
`LastDuration`, the error/message marks) publishes cyclically, and the STATIC
half (`StepNo`, `StepName`, `Branch`, `TimeClass`, `ExpectedTime`,
`AwaitingLabel`, `AwaitsPath`) is served once through the §3.10.2 manifest under
the same browse paths, so the mapper reads one row without knowing it arrived by
two routes. The HMI refetches that manifest only when `ConfigRev` changes.

`SequenceStepDef` rows, however, are discovered **by visit** — and neither
`_M_RecordSequenceStep` (append) nor `_M_ResetSequenceRows` (the mode-change
clear) bumped `ConfigRev`. Every other manifest contributor already did:
`RegisterAvailableModel`, `SetAccessLevel`, the recipe commit in `SetModel`. So
a chart that grew after the HMI's one-time fetch — which is every chart, since
the rows appear as the chain runs — rendered its new rows from defaults: step 0,
no text. `OnModeChanged` then made it permanent for that mode.

That the split is invisible to the mapper is the design working; that half of it
had no revision signal is the defect. **A published surface assembled from two
sources needs one revision that covers both.**

**Fix.** `ConfigRev := ConfigRev + 1` on append (only when a row is actually
added — a re-visit rewrites identical values) and on the mode-change clear
(guarded by `SequenceStepCount > 0`, so a mode change with nothing published
costs no refetch). The HMI's `_manifestFetchInFlight` guard coalesces the bumps
of a first pass into far fewer fetches than there are steps.

Core advances to `0.4.0.1`: a contract-neutral rebuild in the fourth component
(Part II §2.2). Nothing about the published types changed, but a fixed library
that still called itself `0.4.0.0` would be indistinguishable from the broken one
in the library repository. Pins in `Fraktal_Demo`, `PressTests` and
`Fraktal_Tests` move with it; Core must be rebuilt and re-installed, then Modules
resolved, before any application binds the fix.

## 126. A ladder rung agreed on every step and still dropped an effect (2026-08-07)

**Symptom.** Running the LD rendition of the press AUTO chain, releasing a
two-hand button before the slide finished retracting put the machine in a loop:
slide in, door down, abort, door up, slide out, repeat, indefinitely.

**Cause.** `FB_LD_PressDemoAuto` network 8 (step 190, the post-abort slide-out)
carried its `M_Step`, its `M_TryIssue`, the RETRACT command, the Reset of
`_partSlide.Execute` and `MOVE 100 -> _step` — everything its ST twin does
except `_startLatched := FALSE`. `_startLatched` is a `REFERENCE TO BOOL` shared
with the Unit, and N100's `M_Await(Ok := _startLatched)` is the only thing that
holds the cycle at the two-hand wait. Still latched, N100 fell straight through
and the chain ran the whole cycle again against a released button.

The ST and SFC renditions both write it in both places (steps 190 and 999); the
ladder wrote it only at 999.

**Why nothing caught it.** `check_consistency.py --checks parity` compared which
steps exist and where each one can go. Step 190 existed and went to 100 in both
renditions, so the chain was "at parity" while doing something materially
different. **Same steps and same transitions is not the same chain.**

**Fix.** The rung gains a Reset coil on `_startLatched`, generated with
`tools/ld_rung_gen.py` and gated by the same `EQ(_step,190) AND _partSlide.Done`
power that already resets `_partSlide.Execute` — tapping rail 197, which was
computed at the top of the rung, so it cannot be re-evaluated after the MOVE
below sets `_step := 100`.

The gate now compares **effects**, not just topology: for every step carried in
both languages, the shared state the ST branch assigns must be written by a coil
in the ladder rung. "Shared" is exactly the roots the ST twin declares
`REFERENCE TO` — a rendition's own scratch is excluded on purpose, because
`_partProcessed` in ST is `_processed` in ladder and naming scratch differently
is not a divergence. A PLAIN coil is exempt everywhere: it writes its rail's
value every scan, so it already drives the symbol FALSE in every other step and
the ST twin's explicit clears have no ladder counterpart to find. That exemption
is what keeps `_outCmd.CycleCompleted` from being reported. Run against the
pre-fix artifact the check reports exactly one error, naming step 190 and
`_startLatched`.
## 127. The fieldbus tree showed each card its neighbour's state (2026-08-07)

**Symptom.** On the press bench the EL6001 (`=000+S-K010D1`) read OFFLINE on the
HMI fieldbus tree while XAE showed the terminal present and the card was
operational.

**Cause — not the HMI, and not a stale boot configuration.** `FB_EcBusHealth`
mapped the master's slave list to topology nodes *by position*:
`node := _firstSlaveNode + i - 1`. That assumes the catalog and the master's
slave list are the same sequence. They are not.

The master enumerates only devices with an EtherCAT slave controller on the
process-data ring. The press bus is EK1200 coupler, EL1809, EL2809, EL6001,
EL9011 — five entries in the project tree and in the catalog, but the coupler
and the passive end cap have **no ESC**, so `FB_EcGetAllSlaveStates` returns
three. The `.xti` shows it plainly: those two boxes declare 0 PDOs, the other
three declare 16, 16 and 10.

Everything therefore shifted by one:

| master slot | really is | published onto |
|---|---|---|
| 1 | EL1809 | node 2 — the **coupler** |
| 2 | EL2809 | node 3 — the **EL1809** |
| 3 | EL6001 | node 4 — the **EL2809** |
| — | (nothing) | node 5 — EL6001 → OFFLINE |
| — | (nothing) | node 6 — EL9011 → OFFLINE |

So the EL6001's genuine OP state was being displayed on the EL2809's row. **A
wrong state on the right node is worse than no state: it is a plausible lie**,
and it is why the symptom looked like a single dead card rather than a
system-wide off-by-one.

**Fix.** The mapping is stated, not assumed. `FB_EcBusHealth` gains
`M_MapSlaveNode(SlaveIndex, NodeIndex)` — which topology node the master's
slave *i* actually is — and `M_MapPassiveNode(NodeIndex)` for catalogued
devices that carry the bus but are not enumerated. A passive node's state is
*inferred* (OPERATIONAL exactly when the read succeeded and at least one slave
answered), never invented: leaving it OFFLINE forever on a healthy bus is the
same class of lie in the other direction. `Setup`'s consecutive
`FirstSlaveNode`/`SlaveCount` form still fills the map and stays correct for a
bus where every catalogued node really is a slave.

`FB_PressIoDriver` now declares the truth: `SlaveCount := 3` starting at node 3,
three explicit slave mappings, and the coupler and end cap as passive.

**Not verified on hardware.** The press PLC was unavailable when this was
written. The diagnosis rests on the live probe capture taken while it *was*
reachable (`SlavesReported 3`, slots 4–5 returning `0x00` = no data) plus the
`.xti` PDO counts, and both agree. The runtime re-test is outstanding: with the
bus healthy, all six nodes should read OPERATIONAL and `CountMismatch` should be
FALSE.
## 128. The manifest threw away the type it knew (2026-08-08)

**Symptom.** Every row of the §3.13 sequence flow chart rendered as `N0` with an
empty drill-down. §125 fixed the *revision* half of this (the HMI never refetched
a chart that grew), but the rows stayed blank — so that fix was necessary and not
sufficient, and I reported it as complete too early.

**Cause.** A chart row is half live, half manifest. `FB_ConfigPager.M_Append`
stamps `ValueType := TEXT` on every entry, and `M_AppendNumber` — which knows
perfectly well it is writing a number — inherited it. The type was discarded at
the source, so the HMI had to guess from the leaf NAME against a hand-maintained
allowlist. `StepNo` was never in that list. The value crossed the wire as the
string `"100"`, the mapper's `_integer()` fell back to `0`, and the whole chart
became N0. `Branch`, `TimeClass` and `ExpectedTime` were silently wrong the same
way.

**A type the sender knows must never be re-derived by the receiver.**
`M_AppendNumber` now stamps `E_ConfigValueType.NUMBER` on the slot it just wrote,
using the `_storedSlot` mechanism `M_AppendCapability` already relies on. The HMI
consults the declared type first and keeps the name list only as a fallback for a
PLC built before this change — so an un-upgraded controller still renders, and a
new leaf can never silently stringify again.

Core advances to `0.4.0.2` (contract-neutral, Part II §2.2): no published type
changed, but a fixed library must be distinguishable from the broken one in the
repository.


## 129. Output forcing existed in the contract and nowhere in the code (2026-08-14)

**Symptom.** The HMI's fieldbus page had a complete force UI, `ST_IoChannel`
carried `Forced`/`Forceable`, `E_HmiRequestKind.FORCE_CHANNEL` was routed and
audited, and `FB_UnitBase.ForceChannel` proved access, mode and state. Then it
called `_M_RouteForceChannel`, whose base implementation is one line:
`_M_RouteForceChannel := FALSE;`. No Unit anywhere overrode it, and no project
ever called `M_SetForceable`, so `Forceable` was FALSE on every channel and the
whole path was unreachable. The feature was fully specified, fully plumbed, and
did nothing — the kind of gap a compile and a lint both pass over.

**What was missing was not the plumbing but the authority to turn it on.** Core
§10.5.1 says a force is gated by §7.6 and §7.7; it did not say the surface should
be *absent* from a production machine, only that it should be refused. Refusal is
not enough: a greyed control still tells an operator the machine can be forced,
and invites a call asking who can enable it.

**§7.5 now owns that.** Core §7.5 had three lines about a `COMM_FLAG`
commissioning constant, and no mechanism. It gains §7.5.1 (a gate is a build
constant, and the set of active gates is a published register) and §7.5.2 (while
any gate is active the station annunciates it, non-clearably). Forcing became the
framework's own first gate:

- `PL_FraktalEngineering.OUTPUT_FORCING`, selected by the `FRAKTAL_ENGINEERING`
  compiler define, gates the whole surface. A production build publishes
  `Forceable = FALSE` everywhere and the HMI draws nothing.
- `FB_EngineeringMode` is the register. It is write-once, and declaring a gate IS
  activating it: `M_Declare(..., Active := <the build constant>)` registers
  nothing when the constant is FALSE. `ST_EngineeringGate` therefore has no
  `Active` member, and a production station's register is genuinely empty rather
  than a list of things that are off.
- `FB_UnitBase.SetEngineeringMode` declares the framework's own force gate as a
  side effect, so a station cannot arm forcing without annunciating it, and a
  station that wires nothing simply cannot force (§1.1 O1, fail closed).

**The annunciation is deliberately the weakest alarm in the system.** LOW,
SYSTEM, `AUTO_RESET`. Every stronger choice is wrong for a specific reason:
`MANUAL_RESET` refuses `Start` (§8.3(b)), which would make commissioning gates
block the commissioning they exist to serve; a MED/HIGH severity would displace
real process alarms in the phase that produces the most of them; PROCESS or
SAFETY category would claim something about the machine that is not true. What
makes it non-clearable is not its strength but its shape: `OperatorReset` reaches
only `MANUAL_RESET` events, and the §8.9 record is `shelvable: false`, so neither
of the two operator actions that can silence an alarm applies to it.

**Two things had to move to make a force actually reach a terminal.** First, the
held set-point could not live in `ST_IoChannel.BoolValue`: the hardware driver
republishes that member every scan from the process image, so a set-point stored
there survives exactly one cycle, and clearing a force would freeze the last
forced value rather than restore the real one. `ForceBool`/`ForceAnalog` are
separate members for that reason. Second, the per-scan permit could not live in
the `FB_IoTopologyPublisher` instance: the press attaches *two* to the same table
(the catalog defines identity, the driver moves values), and two copies of that
flag would disagree about whether a force is live. `ST_FieldbusTopology.ForcesEnabled`
is in the published table, and `M_ApplyForces` derives its falling edge from the
flag itself, so every instance agrees and leaving idle MANUAL withdraws every
force on that scan — §10.5.1's "a force cannot survive into automatic operation",
enforced rather than assumed.

**The press bench's two existing commissioning gates are now annunciated.**
`USE_SIMULATION` and `CONTROL_CIRCUIT_MAPPING_CONFIRMED` have cost multiple
debugging sessions each (see §6.0 of AGENTS.md); they were documented in three
places and visible on the machine in none. They are declared into the register
from the same `VAR CONSTANT` values, so the machine now says so itself.

`_000K951_A1` and `_000K911_A1` are excluded from the forceable set even in a
commissioning image: they drive the hardwired N54 D2 Control On relay chain, and
energizing control power from a diagnostic screen is exactly the act this surface
must never offer (§10.5.1 rule 4).

Core advances to `0.5.0.0` — a MINOR bump (Part II §2.2). Everything here is
additive: new types (`FB_EngineeringMode`, `ST_EngineeringGate`,
`PL_FraktalEngineering`), new members (`ST_IoChannel.ForceBool`/`ForceAnalog`,
`ST_FieldbusTopology.ForcesEnabled`), new methods, and one appended `E_Reason`.
No existing member changed type or meaning and no `ST_*ParCfg` schema moved, so
there is no §3.8 migration due and every prior consumer compiles unchanged — but
an application still has to resolve the new library before it can see any of it,
which is what the first `CheckAllObjects` run after this change reported.
