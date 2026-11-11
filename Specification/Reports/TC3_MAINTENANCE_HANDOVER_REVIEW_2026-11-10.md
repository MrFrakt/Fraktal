# TC3 maintenance handover review, 2026-11-10

Scope: execute [the Siemens P8 handover](TC3_HANDOVER_PROMPT_2026-11-11.md)
on main `4af593db73a6bdd1ebfbf94eea7a9a27cabe9634`. This review changes no
Siemens or Allen-Bradley implementation. Native acceptance is recorded in
the accompanying dated TC3 evidence; the parity observations below are source
review, not physical I/O acceptance.

## Release decision

Core is **0.26.8.0**: reason 22 is additive and the generated catalog now has
97 entries. The existing generated files are verified, not edited by hand.

Modules is **0.18.0.0**, rather than the handover's conditional rebuild number
0.17.0.1. Commit `78115a2b0` already widened
`ST_RobotCapabilities.Commands` from DWORD to LWORD, changed real-robot safety
binding and withdrew pulsed cylinder outputs on timeout. The published layout
change requires a minor release under Part II §2.2. Third-party robot connectors
and typed clients need rebuilding; real connectors need the safety alias.
This handover also corrects two regressions exposed by native acceptance of
that follow-up, as described below. No retained recipe schema changes. All
five Core consumer pins and all four Modules application pins agree
with their library projects. Historical version statements remain historical.

The first native aggregate run caught an additional **test fixture defect** in
`78115a2b0`: `Power_on_is_refused_without_the_safety_alias` declared a robot CM
and connector as method locals. Windows recorded PLC exception `0xc00000fd`
(stack overflow), and the TcUnit summary was absent. The fixtures now live in
the owning test suite's instance storage. The row also runs `Cyclic` before
asserting `OutImm.SafetyPermit`, which is derived cyclic status. Neither the
task stack limit nor any production safety gate was changed.

After that fix, the aggregate ran to completion: 351 passed and two failed.
`Withdrawn_outputs_stay_off_while_a_pulsed_move_runs` found that the added
`_drive.M_Reset()` in `WithdrawOutputs` erased the pulse selection, so a restore
drove continuously. That reset is removed; the existing withdrawal latch still
keeps both outputs off, and the timeout resets remain.

`Power_on_is_refused_without_the_safety_alias` found a real-connector fixture
receiving the simulation default. The empty `I_SimulatedRobotConnector` marker
was not a discriminating capability on this compiler. It now declares the
read-only `Simulated` property, implemented TRUE by the simulation connector,
and Setup consumes that identity. The row directly checks that the real
connector lacks this capability and that the simulation connector has it.
Implementations of this optional simulation interface must supply the getter.

A further run reached 352 / 353: the remaining robot row also enables an
explicit simulation override as its second assertion scenario. The fixture
now switches that override off before Setup and after the scenario, and asserts
that withdrawing it removes permission. The original no-alias check and both
interface checks remain; the fixture uses the normal API for its cleanup.

## Reason 22: supported source found; implementation awaits the owner

Beckhoff explicitly documents two read-only runtime facts from TwinCAT
**3.1.4026.21**:

- `TwinCAT_SystemInfoVarList._AppInfo.ActivePlcForces`: a PLC-project variable
  is forced.
- `TwinCAT_SystemInfoVarList._AppInfo.ActiveIoForces`: a System Manager
  variable is forced.

Source: [Beckhoff, PlcAppSystemInfo](https://infosys.beckhoff.com/content/1033/tc3_plc_intro/714818699.html).
Its [System Manager forcing documentation](https://infosys.beckhoff.com/content/1033/tc3_system/20792640011.html?id=2429066840948240782)
also points to these runtime facts. `_AppInfo.Flags.1` is a control that
disables forcing, **not** an active-force indication; see
[PLC operation control](https://infosys.beckhoff.com/content/1033/tc3_plc_intro/14576659211.html).

Proposed smallest change for a separately approved follow-up:

1. Extend the platform probe's existing per-scan sample with explicit
   maintenance availability and demand. On supported builds, demand is the OR
   of the two documented flags. Handle older builds as unavailable; do not
   estimate force activity from output differences, tool login or operation
   control bits.
2. Let `FB_SystemHealthPublisher.Cyclic` own one additional alarm slot through
   its existing `_M_UpdateAlarm` path: reason 22,
   `std.system.controllerMaintenanceDemanded`, LOW / SYSTEM / AUTO_RESET,
   non-shelvable through the rationalization registry. Closing the condition
   closes the event. The generic HMI already renders the event and text.
3. Keep it on the existing probe/publisher call path, with no extra per-scan
   project call, force-writing method or new Start interlock. Verify old-build
   compatibility, both force sources, event deduplication and come/gone behavior
   before claiming support. Any shared-input change also needs the corresponding
   generated-input checks in the follow-up's agreed cross-binding scope.

The handover task 5 says to **"ask the owner before building it."** No detector
or new health condition was implemented here. The current TC3 health publisher
therefore still does not raise reason 22 automatically. Availability in the
vendor API is established. After both gates, a read-only ADS probe successfully
read both flags as FALSE on the designated runtime (3.1.4026.24). No active-force
experiment was performed by this release gate.

## Applied-output feedback parity

Observation at the base commit:

- `FB_IoTopologyPublisher.M_SetDigitalValue` (line 380) and
  `M_SetAnalogValue` (line 322) copy the supplied process-image value.
- `M_SetNodeState` (line 437) assigns every channel's `Quality := LinkOk`;
  `M_SetAllHealth` (line 409) does the same from one health verdict.
  Channel definition initially sets Quality TRUE (lines 305 and 365).
- The Press hardware driver writes outputs from the HAL through
  `M_EffectiveBool` (lines 175-182), then publishes those same output variables
  in `M_RefreshFieldbus` (lines 235-244). It does not sample a terminal's applied
  output or an independent feedback channel for these values.

Thus TC3's normal output value is the process-image **demand**, including the
application force when selected, and its Quality establishes node/link health.
It does not establish that the output was applied. An OP/link-healthy
node can still have a different applied state; neither current setter accepts
an applied-feedback health argument. This is a parity difference from the new
Siemens applied-feedback contract, which reports the remote output image after
the remote driver's gates; that too is not an electrical measurement of the
terminal or load. Core §10.5.1 currently names the common
HAL/process-image authority, so this review does not silently redefine that
shared contract or label node health as applied-output proof. A separate
owner-reviewed change should specify output-value meaning and per-channel
feedback quality before changing publisher or driver behavior.

## Force-storage publication parity

`ST_IoChannel.ForceBool` and `ForceAnalog` each have `OPC.UA.DA := 0`
(lines 47-50); `ST_FieldbusTopology.ForcesEnabled` also has that exclusion
(lines 16-17). They stay in PLC-owned shared storage so the catalog and hardware
driver attached to the same topology cannot disagree about a held force.
They are excluded from the TF6100 filtered publication; they are not private
IEC members, and the OPC UA exclusion does not itself remove ADS symbols.

The HMI's Dart sources contain no reads of these three names. The contract's
fieldbus bind table reads `Forced`, `Forceable`, values and Quality; the held
set-point is submitted through the existing validated force request. This is
consistent with Core §10.5.1's separate held set-point and the HMI contract.
The difference from Siemens is storage visibility, not an extra HMI control.
No publication, type layout, forcing predicate or client was changed by this
review.

## Acceptance and disposition

| Gate | Final result |
|---|---|
| PLC lint | modern + 4024: 469 files clean each |
| TwinCAT tool tests | 79 OK, one skipped |
| Strict consistency / tests | 0 errors / 0 warnings; 36 OK |
| Catalog generator | --check clean, 97 entries |
| Library install | Core 0.26.8.0, then final Modules 0.18.0.0 |
| Compiler | six solutions, CheckAllObjects TRUE, 0 errors / 0 warnings |
| Aggregate TcUnit | 353 / 353 in 54 suites, independently validated |
| Press TcUnit | 9 / 9 in 2 suites, independently validated |

The final compiler pass needed a fresh PressTests invocation after an XAE COM
startup failure (0x80080005); its retry compiled cleanly. The final test-project
check also retains the known benign IDE `Unknown TMC file version` row; its
compiler transcript has zero errors and warnings.

See [the evidence record](../Evidence/2026-11-10_TC3_MaintenanceHandover.md) and
[SHA-256 receipt](../Evidence/2026-11-10_TC3_MaintenanceHandover.json), including
every failed attempt and its final replacement. PressTests was independently
observed stopped over ADS after the gate. The detector proposal above and any
applied-output feedback change remain owner decisions. Release edits are left
uncommitted and unpushed, as the handover requests.
