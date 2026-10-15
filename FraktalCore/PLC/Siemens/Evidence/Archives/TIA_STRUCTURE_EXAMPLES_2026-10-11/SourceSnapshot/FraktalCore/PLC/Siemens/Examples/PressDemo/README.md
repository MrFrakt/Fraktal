# Siemens press examples

AUTO and HOME are supplied in SCL/ST, native LAD/LD and S7-GRAPH. The SCL and
LAD release examples evaluate the same six conditions and expose the first
blocking condition. These examples follow the TC3 press's device roles and
sequence/service separation. They cover the nominal process; TC3's scrap/recovery
branches, traceability, full sequence frontier and HMI chart integration remain
separate port work.

**The examples are unwired.** There are no example instance DBs, new root
registrations or calls from Main. Select a sequence and a release rendition,
attach them to your Unit, wire HAL and test the process as you did in TC3.
The offline compiler/export gate does not claim a runtime process test.

## Source ownership

| Source | Owns |
|---|---|
| [press.json](01_PneumaticPress/press.json) | Steps, exits, device roles and release conditions for every rendition |
| [Cylinder module](../../Framework/Modules/README.md) | Device semantics, HAL and typed Extend/Retract operations |
| [Core services](../../Framework/Core/README.md) | Lifecycle, command ownership, Execute release, waits, timers and step recording |
| [Example generator](../../tools/fraktal_tia_examples.py) | SCL emission and declared native LAD/GRAPH object graphs |
| `generated/` | Replayable, grouped imports derived from those authorities |

Generate a fresh package from the repository root:

```powershell
python FraktalCore/PLC/Siemens/tools/fraktal_tia_examples.py --out C:\Temp\FraktalPressExamples
```

Use [the layout tool](../../tools/fraktal_tia_program_layout.py) to derive matching
source and TIA groups. Its import plan builds the GRAPH types before their SCL
owner adapters. A generated plan rebuilds the target program: use an offline
project copy with a preserved export. `generated/import.plan` accepts
`--set project=<offline.ap20> --set export=<new-output-directory>` through the
driver. The standalone package includes its four-module Core fixture; when adding
examples to an existing station, retain that station's Core/registry and merge
only the new module/example types and sequence/permissive services. Regenerate
the complete station declaration when you actually add a root.

## Encapsulation and integration

A sequence receives actual typed `FB_CylinderCM` parameter instances and calls
`F_CylinderExtend` or `F_CylinderRetract`. It does not inspect or set the child's
handshake, HAL outputs or private storage. These semantic FCs are the Siemens
equivalent of the TC3 device methods. TIA has no `EXTENDS` or protected methods;
the generated frame and shared FCs provide the common behavior once.

The generated sequence body owns begin/end management, command release and
step-scoped issue storage. Only an owned command can satisfy its wait. Switching
steps gives the child a real Execute-low scan; native Ladder dispatch captures
the scan's state so a later rung cannot re-enter a new state immediately.
Concurrent HOME waits run independently before their AND join. A stopped,
restarted or faulted chain releases its commands and withdraws its owned outputs.
A subsequent manual command clears the stale sequence owner.

Choose one active rendition per mode. Supply a positive registered `OwnerIndex`,
the actual scan `Delta`, `Run` and reset policy; AUTO also receives its consumed
part/start/hold signals and settle times. HOME carries only its four management
inputs. Each sequence owns its context and visited/duration rows. Public inspection
state is read-only; intermediate rung results and bookkeeping are excluded from
external publication. TIA strips external flags on parameter-instance aliases
in native export; verify the browse surface after you instantiate and wire them.

Evaluate the selected release FB every scan. Map its `RamExtend.Permit` and
blocking diagnostic to the CM's live extension permit; wire retraction and the
other devices' permits according to your process. Permits apply to coils while
BUSY and after completion. Two-hand release pauses the dwell and withdraws the
ram output; it is an expected hold. The release FB calculates conditions only;
the owning Unit/module applies their policy. These ordinary PLC conditions are
not a safety function.

For GRAPH, create a separate chart instance DB and pass it to the matching
`FB_PressDemoAutoGraphOwner` or `FB_PressDemoHomeGraphOwner`. The adapter owns the
same management calls as ST/LAD; the GRAPH runtime owns transitions. Preserve
the owner's child-call order and connect sequence errors/completion to the Unit's
shared lifecycle at its dispatch hook. Main calls the root only; put this wiring
in the owning Unit, not in Main.

## Verification

Replay and native export comparison:

```powershell
python FraktalCore/PLC/Siemens/tools/fraktal_tia_examples.py --verify FraktalCore/PLC/Siemens/Examples/PressDemo/generated
python FraktalCore/PLC/Siemens/tools/fraktal_tia_ld.py generated.xml tia-export.xml
```

The reader checks native operands, typed pins, return connections, contacts,
coils, network order and wires. GRAPH is read back with `fraktal_tia_graph.py`.
Compile before wiring; after wiring, test repeated cycles, held/resumed motion,
parallel HOME, reset/stop, child faults and manual/sequence ownership handover.
