# CX2030 pneumatic-press I/O mapping

Sources:

- `TrainningStation_IOs_V2.xlsx`, worksheet `ios`, supplied 2026-07-13;
- `=000+S-A610-A1 (EtherCAT).xti`, supplied 2026-07-16 and preserved at
  `FraktalCore/PLC/TwinCAT/Tests and Examples/Fraktal_Press_Demo/00_System/Hardware/=000+S-A610-A1 (EtherCAT).xti`.

The XTI is authoritative for the installed EtherCAT terminal order, terminal names, PDO-entry names,
and channel numbers. The worksheet remains authoritative for the approved electrical descriptions and
module roles.
Target: `Fraktal_Press_Demo` on a CX2030 with locally attached EtherCAT terminals.

Status: application mapping implemented; electrical and safety commissioning items below remain
mandatory before physical operation.

## 1. Integration boundary

`GVL_PressIO` contains only process-image symbols (`AT %I*` / `AT %Q*`). The wildcard addresses are
intentional: every active symbol has a `TcLinkTo` attribute naming the exact XTI terminal, channel, and
PDO entry, so TwinCAT creates the PLC-to-I/O link without assuming byte offsets. `FB_PressIoDriver` is
the only POU that reads or writes those symbols and translates them into the reusable press HAL
structures. `MAIN` only selects the physical or simulation driver and establishes scan order.

Import the repository XTI under the XAE solution's **I/O > Devices** tree before compiling the PLC
project. Preserve these terminal names because the declarative links resolve by name:

1. `=000+S-K010 (EK1200)` -- EK1200-5000 EtherCAT Box coupler;
2. `=000+S-K010B1 (EL1809)` -- sixteen digital inputs;
3. `=000+S-K010C1 (EL2809)` -- sixteen digital outputs;
4. `=000+S-K010D1 (EL6001)` -- RS232 interface, present but not consumed by the press HAL;
5. `=000+S-K010E (EL9011)` -- end terminal.

After import/build, XAE shall show all 23 allocated `GVL_PressIO` variables linked. A missing terminal,
renamed box, or renamed PDO entry is a commissioning failure; do not replace the named links with guessed
absolute process-image addresses.

`UseSimulation` defaults to `TRUE`. In that state all mapped outputs are explicitly written FALSE.
Physical operation requires all of the following:

1. import the supplied XTI and verify all 23 declarative `GVL_PressIO` links;
2. supply the safety-status mirrors by **one** of:
   - **relay-safety machine (N54 D2 Control On circuit, no safety controller):**
     nothing to link — `FB_PressControlOnCircuit` reconstructs the six mirrors
     from the raw process image (E-stop mirror `_000K910A`, door `_101B201A`,
     two-hand `_101S101/102`, and the Control On feedback `_000K911_Y32`). Link
     `MAIN.RealBusOk` to the EtherCAT master DevState/WcState; it defaults FALSE
     (fail-closed) and is forced TRUE only on a validated isolated bench;
   - **safety-controller machine:** link the fail-closed `GVL_PressSafety` aliases
     to evaluated TwinSAFE (or validated external safety) results, and swap the
     driver back to reading `GVL_PressSafety` instead of the Control-On adapter;
3. verify the electrical behavior of the two Control-On coils and then set
   `ControlCircuitMappingConfirmed := TRUE`;
4. set `UseSimulation := FALSE` only after dry I/O and safety validation.

`GVL_PressFieldbus.Topology` publishes the same approved tags through the generic `ST_BusNode` /
`ST_IoChannel` contract. `FB_PressIoCatalog` owns the static engineering-data join and injects each
cylinder's four semantic I/O roles. `FB_PressIoDriver` alone accesses `GVL_PressIO`, maps the HAL, and
refreshes live values. Reusable `FB_IoTopologyPublisher` code performs bounds/duplicate validation,
health propagation and exact-tag diagnostic correlation. The driver currently uses the aggregate
`StandardIoHealthy`; production commissioning shall replace/augment that aggregate with actual
EtherCAT master/node diagnostics required by Core §10.5.1. It must not be mistaken for independent
proof that every configured terminal is present.

## 2. EL1809 inputs

| Channel | Electrical tag | Worksheet description | Application mapping |
|---:|---|---|---|
| 1 | `_101B301A` | Feeder retracted | `PartSlide.ExtendedFb` = logical **inside** |
| 2 | `_101B301B` | Feeder extended | `PartSlide.RetractedFb` = logical **outside** |
| 3 | `_101B201A` | Door closed | `Door.ExtendedFb` |
| 4 | `_101B201B` | Door opened | `Door.RetractedFb` |
| 5 | `_101B202A` | Press down | `PressRam.ExtendedFb` |
| 6 | `_101B202B` | Press up | `PressRam.RetractedFb` |
| 7 | `_101S101` | Right two-hand button | raw diagnostic/button state only |
| 8 | `_101S102` | Left two-hand button | raw diagnostic/button state only |
| 9 | `Reserve` | — | intentionally unmapped |
| 10 | `_000MB085A_2` | air below 0.3 bar | low-pressure/discrepancy input |
| 11 | `_000MB085A_4` | air above 4.5 bar | operating-pressure input |
| 12 | `_101B601` | part present | AUTO release condition and `OutImm.PartPresent` |
| 13 | `Reserve` | — | intentionally unmapped |
| 14 | `_000K911_Y32` | IsControlOn | pneumatic control-power feedback |
| 15 | `_000K910A` | E-stop panel not pressed | ordinary diagnostic mirror only |
| 16 | — | not listed | intentionally unmapped |

Air is accepted only when the high threshold is active and the low threshold is inactive. Both false
means pressure is in the indeterminate/insufficient band; both true is treated as invalid. The feeder
mapping intentionally reverses the generic cylinder position names: the physical cylinder's retracted
state places the slide inside the machine.

## 3. EL2809 outputs

| Channel | Electrical tag | Worksheet description | Application mapping |
|---:|---|---|---|
| 1 | `_101K301A` | Feeder backward | slide inside request |
| 2 | `_101K301B` | Feeder forward | slide outside request |
| 3 | `_101K201A` | Close door | door close request |
| 4 | `_101K201B` | Open door | door open request |
| 5 | `_101K202A` | Press downward | ram-down ordinary request |
| 6 | `_101K202B` | Press upward | ram-up ordinary request |
| 7 | `_101P101` | Right-hand lamp | two-hand armed and station ready |
| 8 | `_101P102` | Left-hand lamp | two-hand armed and station ready |
| 9 | `Reserve` | worksheet row says `EL2810`; XTI says EL2809 Reserve | intentionally unmapped; XTI resolves the installed terminal as EL2809 |
| 10 | `_000K951_A1` | SwitchControlOn | functional Control-On request, confirmation-gated |
| 11 | `_000K911_A1` | EnableControlOn | functional Control-On request, confirmation-gated |
| 12–16 | — | not listed | intentionally unmapped |

Neither the spreadsheet nor the XTI defines whether `_000K951_A1` is maintained, pulsed, or sequenced
relative to `_000K911_A1`, and no physical Control On/Off input buttons are allocated. The implementation therefore
keeps both coil outputs off until `ControlCircuitMappingConfirmed` is deliberately set. Confirm the
electrical diagram/relay datasheets before choosing maintained or pulse timing. HMI Control On/Off is
already available through the access-gated Unit request contract.

The EL6001 serial PDOs are intentionally not declared in `GVL_PressIO`: no press module, protocol, or
serial device requirement was supplied. The terminal is still published as a fieldbus node. Add a
project-owned serial driver and an explicit HAL contract if a later device is assigned; do not expose
raw serial buffers as an accidental generic-HMI contract.

## 4. Safety gap identified from the worksheet

The EL1809 is documented by Beckhoff as a 16-channel 24 V DC digital input terminal, and the EL2809 as
a 16-channel 24 V DC digital output terminal. Their listed raw E-stop and two-hand channels are useful
for status and discrepancy diagnostics, but the worksheet contains no certified safety input, safety
output, guard channel, safe-valve feedback, or evaluated two-hand result. By contrast Beckhoff's EL1904
and EL2904 product titles explicitly identify them as TwinSAFE terminals:

- [Beckhoff EL1809](https://www.beckhoff.com/en-us/products/i-o/ethercat-terminals/el1xxx-digital-input/el1809.html)
- [Beckhoff EL2809](https://www.beckhoff.com/en-us/products/i-o/ethercat-terminals/el2xxx-digital-output/el2809.html)
- [Beckhoff EL1904 TwinSAFE input](https://www.beckhoff.com/en-us/products/i-o/ethercat-terminals/el1xxx-digital-input/el1904.html)
- [Beckhoff EL2904 TwinSAFE output](https://www.beckhoff.com/en-us/products/i-o/ethercat-terminals/el2xxx-digital-output/el2904.html)

This does not prescribe those exact terminals: a validated external safety relay/controller may be
appropriate. It does mean the current ordinary-I/O list alone is insufficient evidence for a safe
E-stop, two-hand control, guard function, or pneumatic energy removal. The machine risk assessment and
safety design must supply and validate:

- dual-channel E-stop evaluation, reset, EDM and restart prevention;
- certified two-hand simultaneity, anti-tie-down and release behavior;
- guard monitoring if the door is a protective guard rather than a process shutter;
- safe pneumatic dump/enable output plus feedback and required diagnostic coverage;
- safe-communication health and the standard EtherCAT terminal health status.

`GVL_PressSafety` provides fail-closed integration aliases for those evaluated results. The ordinary
PLC uses them for functional withdrawal, release reporting, and HMI status; the independent safety
system remains final output authority.

## 5. Dry-I/O commissioning checklist

- Import the preserved XTI and confirm its physical order, revisions, supply groups, commons and output current budget.
- Build the PLC project and prove that all 23 `TcLinkTo` mappings resolve with no unlinked allocated symbol.
- Confirm all English/Spanish tag descriptions against the electrical schematic.
- Verify every position sensor individually, then prove dual-sensor contradictions block motion.
- Confirm slide Ch1 really means inside and Ch2 outside before enabling either solenoid.
- Verify valve polarity and that opposing solenoids cannot be energized together.
- Verify low/high air switches through depressurization and repressurization.
- Verify part-present behavior and failure state.
- Prove mapped outputs remain off in simulation and during PLC/fieldbus loss.
- Validate E-stop, two-hand, guard and pneumatic safe-state functions independently of `MAIN`.
- Archive the final I/O link map, safety checksum, validation report and electrical revision.

## 6. Technician diagnostic path

The reusable cylinder type accepts application I/O identity through `ConfigureIoIdentity`. A position
timeout keeps `SourcePath` as the logical module but adds the awaited sensor's exact `IoTag` and
`IoAddress`. For example, a ram-down timeout publishes `PneumaticPress.PressRam`, `_101B202A`, and
`=000+S-K010B1 Ch5`; the HMI alarm/detail view shows those fields and the fieldbus view highlights that same
input row. A simultaneous-position-sensor fault identifies and highlights both corresponding inputs.
The electrical tag remains untranslated; only its description and diagnostic sentence use the
standard/project language catalogs.
