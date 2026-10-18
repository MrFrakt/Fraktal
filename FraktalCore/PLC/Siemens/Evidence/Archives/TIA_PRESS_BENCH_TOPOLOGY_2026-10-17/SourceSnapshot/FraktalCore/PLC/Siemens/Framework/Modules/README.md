# Siemens reusable modules

[cylinder.json](ControlModules/Cylinder/cylinder.json) owns the cylinder's contract, storage and command
catalog. [cylinder_logic.scl.in](ControlModules/Cylinder/cylinder_logic.scl.in) adds device reactions to
the generated common frame. [cylinder_api.scl.in](ControlModules/Cylinder/cylinder_api.scl.in) exposes
typed `F_CylinderExtend` / `F_CylinderRetract` operations to every sequence language.
The command identifiers are bound from the catalog, never repeated in a chain.

The frame owns lifecycle, command timing, terminal reset and derived states.
The CM owns feedback interpretation, direction and HAL coils. Both live permits
and a sequence's withdrawal apply to outputs after completion as well as BUSY.
Private Device storage is externally excluded. Parameter-instance alias flags
are stripped by TIA; verify the native browse surface when instantiating chains.
Sequences use the semantic API; raw Execute/Done handling stays in shared code.

Generate the module and the wired GRAPH/ST demo through
[the press example generator](../../tools/fraktal_tia_examples.py). Native groups
place the FB, contract types and API under
`Framework/Modules/ControlModules/Cylinder`; no module instance is created there.

F_CylinderExtendHandled lets an owning step branch on failure: it preserves the
first-out, withdraws the failed direction and releases the terminal handshake.
Ordinary Extend/Retract retain normal fault adoption. Leases include a branch
identity; a step change cancels a still-BUSY command before another command can
borrow its result. Manual release predicates consume the CM's live permits and
its extension/retraction diagnostics.

## Passive sensor modules

Three control modules port the TC3 press sensors with their TC3 type keys, so a
faceplate authored against `std.moduleType.*` renders on either binding:

| Type | Folder | Publishes |
|---|---|---|
| `FB_TwoHandStartCM` (`std.moduleType.twoHand`) | [TwoHand](ControlModules/TwoHand/two_hand.json) | `SafeActive` from the certified two-hand result, `Armed` after both buttons were released, and a one-scan `StartPulse` on the armed rising edge |
| `FB_DigitalInputCM` (`std.moduleType.digitalInput`) | [DigitalInput](ControlModules/DigitalInput/digital_input.json) | `Value` and its `Quality` |
| `FB_AirPressureMonitorCM` (`std.moduleType.airPressure`) | [AirPressure](ControlModules/AirPressure/air_pressure.json) | `PressureOk` from the two thresholds; both switches active for `ParCfg.ConflictTime` faults with `AIR_SWITCH_CONFLICT` (bound from the TC3 module reason list) |

None declares a command. The shared runtime admits a command-less type only at
the CM tier, and its generated frame rejects every request as
`UNSUPPORTED_COMMAND` instead of leaving it BUSY; Units and EMs still require
their commands and a ParCfg timeout. A passive module's fault is a latch the
owning Unit's operator reset releases; a persisting condition re-faults.

Differences from TC3, each because the Siemens binding has no consumer yet:
no `IoTag` identity fields (the I/O topology publisher is not ported), no
`Safety` summary facet, `ConflictTime` in `ParCfg` rather than an editable
`StationCfg`, and no `OutCmd.StartAccepted` (it duplicated `StartPulse`).
