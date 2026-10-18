# Fraktal Safety and Control-Power Profile

Status: draft optional Core profile. It extends Core §9 without moving a safety function into the standard PLC or HMI.

## 1. Purpose and boundary

This profile standardizes how a Fraktal station requests, observes, diagnoses, and coordinates ordinary control power with a separately engineered functional-safety system. The risk assessment and certified safety application remain authoritative. ISO 13849-1:2023 or IEC 62061 determines the required PL/SIL; ISO 14119:2024 governs guard interlocking and defeat resistance; ISO 14118:2017 governs prevention of unexpected start-up; IEC 60204-1 governs machine electrical equipment. PLCopen Safety `SF_*` blocks are the preferred portable vocabulary on the safety side.

The standard PLC **shall never** claim that a safety function is achieved merely because a Boolean alias is TRUE. It may:

- send an untrusted functional request (`EnableRequest`, `UnlockRequest`, `StopRequest`) to the safety application;
- consume safety-evaluated status and feedback read-only;
- stop/abort ordinary sequences and withdraw ordinary output requests;
- explain the resulting state through the common diagnostic and release contracts.

The safety application alone grants safe enable, guard unlock, muting, bridging, reset, safe valve state, STO/SS1/SLS, and restart permission. HMI loss or standard-fieldbus loss shall never defeat those functions.

## 2. Control domains and two levels of energy control

The execution hierarchy and the safety/control-power arrangement are two independent graphs. A **control domain** is one cage/cell/energy arrangement with one stable `Id`, one safety aggregate, one control-power coordinator, and a bounded list of member root-Unit paths. It is infrastructure, not a fourth module tier and not a synthetic super-root Unit.

A root Unit shall reference zero or one control domain:

- no reference (`Present=FALSE`, `Id=''`) means the Unit has no safety/control-power arrangement and `Start` has no Control-On prerequisite from this profile;
- one domain may be referenced by one Unit (the common station-per-cage case) or by multiple peer root Units (several stations in one cage);
- domain membership shall use stable root browse paths and shall be validated at startup. A dangling, duplicate, or contradictory membership fails closed;
- sharing does not transfer mode, cycle, recipe, OEE, or access-session ownership between Units. The Unit forest remains unchanged.

The domain coordinator publishes `ST_ControlDomainStatus`. Each member Unit consumes the same status and republishes `Status.ControlDomainId` plus read-only safety/power facets for generic clients. This is a mirror, not duplicated ownership. A domain marked `Present` is ready for a Unit to start only when its `ReadyForStart` aggregate is true.

The terms are deliberately distinct:

- **Control On / Control Off** are control-domain orchestration requests. `ControlOn` means every power group marked `RequiredForControl` is proven ON and no group requires deliberate rearm. `ControlOff` withdraws every registered power request. It is not the main isolator and is not lockout/tagout. A shared-domain request shall identify every affected member Unit to the operator and shall be arbitrated by the coordinator, never independently latched by each Unit.
- **Power On / Power Off** are requests for one named power group: a valve-island zone, drive group, heater, process-energy group, or auxiliary group. A group may be safety-switched, ordinarily switched, or both; its published contract is identical.

`ControlOn` shall be a deliberate edge/action. Restoring a guard, safety permit, fieldbus, or power feedback shall not reissue it. A Unit assigned to a present domain shall refuse `Start` until `ReadyForStart=TRUE`. An unassigned Unit has no implicit power or safety requirement from this profile; its application interlocks still apply normally.

## 3. Published optional facets

Every module inherits two optional data facets. `Present=FALSE` means the capability is absent and the generic HMI hides it.

### 3.1 `ST_SafetyStatus`

The facet publishes the aggregate (`AllSafe`, `DemandActive`, `ResetRequired`, `FaultActive`, `MutingActive`, `BridgeActive`, `StopRequested`) and a bounded array of `ST_SafetyDeviceStatus`. Each device record contains a stable name/path, kind, state, safe-state feedback, fieldbus health, affected-power mask, and descriptive text.

`MutingActive` and `BridgeActive` are status only. They shall be conspicuous, logged, and never presented as ordinary `PermIntlk` bypasses. A keyed bridge is a safety-engineered operating mode, not permission for standard logic to force an input. Muting is automatic, safety-validated suppression using the applicable sensor sequence; override/recovery is a separate safety function.

### 3.2 `ST_ControlPowerStatus`

The facet publishes Unit-level request/effective state and bounded `ST_PowerGroupStatus` records. Each group reports kind, state, request, feedback, safety permit, fieldbus health, fieldbus-loss reaction, rearm requirement, and diagnostic.

The affected-power mask is metadata shared with the HMI and validation tooling. It does **not** execute the safety reaction. The certified safety project owns the real sensor-to-output mapping.

## 4. Basic reusable modules

Implementations should start with small capabilities and compose specifics:

1. **Safety-device CM** — a read-only mirror for an E-stop, guard, light curtain, scanner, mat, enabling switch, safety valve, drive safety state, or generic safety sensor. It owns no safety output.
2. **Power-group CM** — owns one functional enable request and its feedback, safety-permit alias, fieldbus health, timeout, loss reaction, and deliberate-rearm latch.
3. **Safety-access CM/EM** — extends the safety-device pattern with a physical open-request input and an untrusted unlock request. It may publish `StopRequested`; the owning Unit performs a graceful stop, and unlock is requested only after the configured safe-state feedback is present. The safety application still decides whether unlocking is safe.
4. **Control-domain coordinator** — a cell-scope infrastructure provider, independent of Unit ownership. It implements Control On/Off, aggregates required-group feedback, publishes member Unit paths, and withdraws all requests on a configured control-off reaction. It may serve one or many peer root Units.

Purchased/vendor-specific valve terminals, guard-lock devices, drives, and scanners extend these basics by mapping vendor status into the same records. Sequences remain unchanged.

## 4a. The manual-enable fact (teaching with the guards open)

Teaching needs motion with the guards open, and the only thing that may permit it is the certified
safety system: a three-position enabling device, a deliberate mode selection, guard muting done by
the safety program, and a **safety-rated** reduced speed (the robot's safe-speed function, or drive
SLS). None of that is standard-PLC work, and none of it is defined here.

What the standard defines is how application code **observes** it, so a release (§7.6) can be written
against a fact that has a provenance instead of a boolean a station assembled from ordinary inputs:

```iecst
TYPE ST_ManualEnableStatus :    // derived, never authored
STRUCT
    Present    : BOOL;          // at least one enabling device is mirrored
    Held       : BOOL;          // one is permitting NOW — safety-evaluated
    DeviceName : STRING(80);    // which one, for the §7.6.0 release report
END_STRUCT
END_TYPE

FUNCTION F_ManualEnable : ST_ManualEnableStatus
VAR_INPUT  Safety : ST_SafetyStatus;  END_VAR
```

- **Derived from the device rows that already exist.** An enabling switch is an ordinary safety-device
  CM (`E_SafetyDeviceKind.ENABLE_SWITCH`, §4.1). The aggregate is computed from those rows, so the
  fact keeps one authoritative source and no station walks the array by hand.
- **Permitting is the positive state.** A held enabling device publishes `Ready` / not `DemandActive`,
  exactly as an E-stop that is not pressed does. Released **and** panic-squeezed both demand the safe
  state — which is the entire reason the device has three positions rather than two.
- **Fail-closed.** No mirrored enabling device means never enabled, so a cell that never wired one
  cannot jog with its guards open by omission. A safety fault, or an unhealthy safety fieldbus,
  withdraws the permission however the switch itself reads.
- **Status, never authority.** The module still applies its own interlocks; this is an *additional*
  requirement on manual motion, never a way around them. §9 remains read-only, and the PLC never
  infers "safe" from this record.

Grepping for `F_ManualEnable` lists every place in a codebase where motion is authorised by an
enabling device. That auditability is why the derivation lives here rather than in each station.

## 5. Optional behavior as data

The following are configuration policies, not bespoke branches:

| Feature | Declarative realization |
|---|---|
| Door opening disables only part of a valve island | Door safety record names affected power-group bits; the safety project switches those safe output zones; unaffected groups remain available. |
| Light curtain interrupts selected pneumatic/drive zones | Same affected-group mapping; `MutingActive` is safety-generated and visible. |
| Control Off on fieldbus error | Group policy `CONTROL_OFF`; field terminal safe-state/watchdog is configured independently as the primary reaction. |
| Stop Unit when physical open-door button is pressed | Access device publishes `StopRequested`; owning Unit requests graceful stop without requiring an HMI session. |
| Key bridge | Safety input/mode only; publish `BridgeActive`, operator identity/procedure where available, expiry/return requirement, and affected zone. No HMI command. |
| Safety reset | Physical/local deliberate action evaluated by safety logic. Standard HMI may explain `ResetRequired` but shall not generate the safety reset unless the certified design explicitly includes a compliant reset device/channel. |
| Partial machine operation | Independent safety/power zones plus Unit/EM ownership. A Unit may run only if all groups required by its active mode/recipe are proven. |

Every `CASE` over a reaction policy shall have a defined fail-safe `ELSE`. Unknown enum values map to `CONTROL_OFF`, never to “keep running.”

## 6. Door/access sequence

1. Physical access-request button rises.
2. Access module latches `StopRequested` and the owning Unit performs its configured graceful stop.
3. Ordinary output requests for affected groups are withdrawn.
4. Safety logic proves the hazardous state is safe, then grants/unlocks the guard.
5. Door state, lock state, bridge/muting state, and affected groups remain visible.
6. After closing/locking, safety reset/restart permission is deliberate.
7. Operator issues a new domain Control On and then Start on the required member Unit(s). Neither action is replayed automatically.

If the guard opens without the request sequence, the safety system reacts immediately; the standard PLC records a safety demand, faults/aborts affected commands, and never treats the prior graceful-stop path as a safety function.

## 7. Fieldbus and degraded communication

The reaction is layered:

- safety communication loss drives the safety system to its validated safe state;
- field output devices use configured watchdog/safe-state behavior;
- the standard PLC withdraws functional requests and raises `SYSTEM`/`SAFETY` diagnostics;
- the HMI locks interaction on link loss and never queues Control On, Power On, bridge, reset, or unlock actions.

`ALARM_ONLY` is permitted only when the risk assessment shows the affected communication cannot control hazardous energy. Unknown health shall be treated as unhealthy.

## 8. Plug-and-produce conformance

Plug-and-produce does not mean dynamically rewriting a validated safety program. A conforming device/module package supplies a machine-readable descriptor containing:

- stable device and power-group IDs/browse paths;
- stable control-domain ID and explicit member root-Unit paths (zero-domain Units are explicit too);
- device kind and required safe function;
- affected power-group mapping;
- normal and safe-state feedback semantics;
- expected fieldbus identity and safe-parameter checksum/identity;
- required PL/SIL from the machine risk assessment (deployment-owned);
- supported diagnostics and test proof.

At integration, tooling compares the installed identities and mapping against the validated manifest and fails closed on mismatch. Any safety mapping change triggers the safety management-of-change and revalidation process. This preserves fast composition without pretending certification is hot-pluggable.

## 9. HMI rules

The generic HMI renders the two facets automatically:

- Safety card: aggregate state and one row per device; bridge/muting/reset-required are prominent and safety alarms cannot be shelved.
- Control-power card: Control On/Off plus group state, feedback, safety permit, bus health, and rearm reason.
- Shared-domain card: domain name/ID and every affected root Unit; one command changes the domain once, not once per mirrored Unit.
- Power On/Off is shown per group only where the deployment exposes it and is release-gated.
- Physical safety reset, bridge, muting, and guard unlock are read-only unless a separately validated design explicitly exposes a compliant request.

Control/power writes use the same act-or-explain release reporting and audit trail as other gated actions.

## 10. Minimum tests

- no automatic re-energization after safety or fieldbus recovery;
- Control On requires all required groups and deliberate rearm;
- fieldbus-loss policy drives the configured reaction, with unknown policy failing to Control Off;
- physical access request produces a Unit stop request before unlock request;
- unrequested guard opening produces immediate demand/fault status;
- bridge and muting are visible, logged, never writable through normal HMI/force paths;
- affected-zone mapping leaves unrelated power groups unchanged in simulation;
- safety alias unavailable/invalid fails closed;
- HMI hides absent facets and disables Start when required control power is not on.
