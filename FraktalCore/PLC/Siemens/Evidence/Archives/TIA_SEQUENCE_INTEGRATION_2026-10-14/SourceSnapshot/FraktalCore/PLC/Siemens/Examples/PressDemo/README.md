# Siemens press demo

The current generator 0.15 package has 157 grouped sources and selects the
[shared LOAD_DB medium](../../Tests/Persistence/README.md) for station config,
four named-set slots, private users and root policy (seven documents). Its
warning-clean offline project is
`Persist_Medium_Press_Offline_20261013/FrkS12/FrkS12.ap20` under the local TIA
station directory. MAIN still has three calls. The dated profile notes below
describe earlier packages; [current evidence](../../../../../Specification/Siemens/Evidence/TIA_PERSIST_MEDIUM_2026-10-13.md)
supersedes their current-image references.

The demo wires `FB_GRAPH_PressDemoAuto` and `FB_GRAPH_PressDemoHome` to the
owning `FB_PressDemoUnit`, with `FB_PressDemoRelease` evaluating permissives in ST.
ST and native LD sequence twins, and the LD release twin, remain optional examples
with no instances. Main calls input read, the composition root and output write.
One hardware-driver FB owns all logical I/O access. Feedback is not synthesized;
field addresses and physical process qualification await the owner's bench.

AUTO follows the TC3 press's sixteen main steps and its native chart's nineteen
steps. It includes the two recovery choices, backwards jumps and parallel join:

| Step | Normal exit | Recovery exit |
|---|---|---|
| N180, close door | Fork to N200 and demonstration leg N300 | JUMP1 to N185, reopen door; N190 returns slide and jumps to N100 |
| N200, press stroke | N220 dwell, N230 record | JUMP1 to N210 deliberate scrap confirmation, then N215 NOK disposition |
| N240, return to load | Reusable ST sub-chain: ram, door, slide | Sub-chain errors retain the child's first-out |
| N250 and N310 | Both legs join before N999 | Each leg has its own return value and context |
| N999, cycle complete | Jump to N100 | A pending Stop completes the Unit at the cycle boundary |

The parallel demonstration leg adds no fabricated machine operation. The return
sub-chain records steps 240/260/280/300 in its own context. ST/LD carry the same
main recovery exits; the three extra native GRAPH steps express the visual fork
and join. Releasing two-hand control during dwell pauses time and withdraws force.
A completed door-close wins a simultaneous release, matching TC3 policy.

The TC3 chart's serialized N200 failure transition currently reads ADVANCE,
although its action produces JUMP1. This port uses the intended JUMP1 condition.
The TC3 source is preserved. With traceability disabled, both OK and scrap cycles
update their respective counters; a scrapped part is never counted as good.

## Ownership and encapsulation

[press.json](01_PneumaticPress/press.json) owns steps, exits, station config and
release conditions. [auto_services.scl.in](01_PneumaticPress/auto_services.scl.in)
owns press policy. [Cylinder](../../Framework/Modules/README.md) owns device
semantics and typed commands. [Core](../../Framework/Core/README.md) owns lifecycle,
leases, Execute release, waits, timers, decisions, messages and step visits.
[The generator](../../tools/fraktal_tia_examples.py) owns native object graphs and
adapter wiring; the application does not duplicate the common command lifecycle.

The Unit's unconditional sequence hook drives inactive, reset, aborted and
faulted chains as well as active chains. GRAPH owns transitions; its adapters
manage contexts and child-command leases. Separate chart instance DBs are wired
at the Unit. Their host status parameter is named HostStatus so it cannot appear
as another root with a direct Status facet. TIA strips external flags on structured
and FB parameter-instance aliases; complete deployed alias exclusion remains
unqualified. Private device storage and intermediate locals are excluded, and
inspection rows are readonly. Full Core 3.13 frontier/HMI chart integration remains
port work; these inspection rows do not claim that complete contract.

ST release runs every scan. The CM applies the same live permit while BUSY and
after completion, and uses it for manual release queries too. A handled press
failure keeps its first-out, closes an AUTO_RESET message, withdraws the failed
output and waits indefinitely for explicit scrap confirmation. Ordinary faults
retain their MANUAL_RESET capture. These process permits are not safety functions.
Homed is recomputed from the cylinders every scan, never latched by HOME.

## Generate, import and verify

```powershell
python FraktalCore/PLC/Siemens/tools/fraktal_tia_examples.py --out C:\Temp\FraktalPressDemo
python FraktalCore/PLC/Siemens/tools/fraktal_tia_examples.py --verify FraktalCore/PLC/Siemens/Examples/PressDemo/generated
```

[The layout tool](../../tools/fraktal_tia_program_layout.py) derives matching source
and TIA groups. The generated import plan accepts `${project}` and `${export}`
through driver --set arguments, and compiles chart types before their adapters
and Unit. It rebuilds a complete demo application: use an offline project copy
with a preserved export. It replaces that copy's program, including its Core and
registry; it is not a merge into an already registered production forest.

The offline wired project is
`%LOCALAPPDATA%\Fraktal\TiaStations\Alarm_Recovery_Press_Offline_20261012\FrkS12\FrkS12.ap20`.
The owner Fraktal simulator runs the separate access/config-set/decision qualification bench.
The press application has not been downloaded or physically tested.

[The dated evidence](../../../../../Specification/Siemens/Evidence/TIA_GRAPH_RECOVERY_DECISIONS_2026-10-12.md)
records native compilation, GRAPH/LD export parity and simulator service checks.
Physical acceptance still needs repeated cycles, cancellation, held/resumed
motion, manual/sequence handover, failures, reset and Stop at the cycle boundary.


The declaration also enables four named station config slots through the shared
Core handlers. The demo declares no model catalog or line config provider, so
those set kinds are refused. Set operations use the generic HMI configuration
controls; Main still contains three calls. This package has 110 generated sources
and the same 19-step AUTO and four-step HOME GRAPH charts. See
[set evidence](../../../../../Specification/Siemens/Evidence/TIA_CONFIG_SETS_2026-10-12.md).

Generator 0.11 also carries private local user and root-policy retention. The
shipped demo policy remains fully open; deliberate commissioning uses the trusted
hashed provider seam and the gated policy mailbox. Sessions remain volatile. See
[access retention evidence](../../../../../Specification/Siemens/Evidence/TIA_ACCESS_PERSISTENCE_2026-10-12.md).

Generator 0.12 opts PressDemo into the shared closed-event LOCAL_RETAIN history
profile. Its generated Unit frame restores history and the Core close path stores
new records; Main stays at three calls. Active alarms/control latches remain
volatile. See [history qualification](../../Tests/AlarmPersistence/README.md).

Generator0.13 also opts PressDemo into manual-reset alarm recovery. Shared Core
services restore latches and reconcile fresh faults before Start, with running-time
checkpoints and an interrupted-close journal. The Unit schedules this through its
existing frame; Main remains three calls. Commands and outputs remain volatile.
See [recovery scope](../../Tests/AlarmRecovery/README.md).


The current optional event-delivery profile selects PressDemo with 32 retained
slots and a deployment UUID. Framework capture and receipt handling add no Main
call. The generated application now has 120 sources. Its current offline project
is Event_Delivery_Press_Offline_20261012/FrkS12/FrkS12.ap20. The collector's SQLite
path is a deployment choice; no process bench or physical download is claimed.
See [delivery profile](../../Tests/EventDelivery/README.md).

Generator 0.16 publishes the Core sequence view with 23 rows, two parallel legs and four annotations. Load-position locals 240/260/280/300 project to 600/620/640/660 through `press.json`'s single offset; the GRAPH numbers/transitions stay intact. The final 168-source package compiles 0/0 at both stages, and native 19 AUTO/4 HOME plus LAD161 networks/155 calls match. MAIN remains three calls. View helpers are synthetically qualified; physical press behavior and native HMI chart rendering remain unqualified. See [dated evidence](../../../../../Specification/Siemens/Evidence/TIA_SEQUENCE_VIEW_2026-10-13.md).

Current generated package is 0.17. The selected LOAD_DB restore path now
withdraws the sequence cursor/current view through the shared owning service.
The current offline project is Sequence_Integration_Press_Offline_20261014;
both compile stages remain 0/0 and native GRAPH/LAD parity is unchanged. The
separate synthetic medium bench now qualifies generic-HMI chart rendering.
Physical press behavior remains unqualified. See [integration evidence](../../../../../Specification/Siemens/Evidence/TIA_SEQUENCE_INTEGRATION_2026-10-14.md).
