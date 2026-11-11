# What can see a CPU force job? (P8 spike, 2026-11-11)

Owner decision 3B. TIA force tables have no runtime API, so Core §10.5.1's
"annunciate the controller's own forces" needed a measurement before a design.
The owner started and stopped one force job in TIA Portal while
`Tests/ProfinetHealth/force_spike.py` recorded, every two seconds, what the
program and a host can see.

## Set-up

The PROFINET fixture (`P8_ForceSpike_20261110_01`, compile 0/0, read-back
262/71/17) on the reserved isolated CPU 1516-3 PN/DP V3.0 at 169.254.212.58,
web server on, a DPAPI-provisioned web user with `ReadTagStatus`,
`ModifyTagStatus` and `DoDiagnosis`. Forced: `%Q0.0:P` of the central DQ 16×24VDC
module. The saved `Fraktal` instance stayed RUN and preserved throughout.

## Result (session 5)

| Seen by | Before | Force active | After |
|---|---|---|---|
| Program, `LED(LADDR := "Local~Common", LED := 3)` (MAINT) | 1, off | **2, on** (24 consecutive readings, ~46 s) | 1, off |
| Program, STOP/RUN and ERROR LEDs | 2 / 1 | unchanged | unchanged |
| Host, `Plc.ReadOperatingMode` | run | run | run |
| Host, `DiagnosticBuffer.Browse` | — | `incoming` "CPU maintenance demanded: Force job active", event `textlist_id 2, text_id 16469`, CPU time 01:27:21.8 | the same event `outgoing`, 01:28:06.8 |

The CPU's `Api.Browse` lists 69 Web API methods on this firmware; none reads or
lists force jobs. The diagnostic buffer also carried the suite's own
`D_ACT_DP` events (13263, I/O device user deactivation) and every web login
(17430), so program and access events reach it as well.

## What this means

- **The program can tell that maintenance is demanded, not that it is a force
  job.** The CPU raises a force job as *maintenance demanded*; the MAINT LED,
  which the `LED` instruction reads, lights for any maintenance demand.
- **A host can tell exactly.** Event 16469 incoming/outgoing in the diagnostic
  buffer names the force job; reading it needs the `DoDiagnosis` web right.
- No method reads which addresses are forced.

Annunciation itself is not implemented; Part IV §10.5 records these facts in
place of the earlier "no runtime API" note.

## Attempts

Sessions 1–4 are kept as evidence. 1: the web user lacked `DoDiagnosis`
(operating mode and diagnostic buffer refused); the rights were re-applied
offline. 2: the 30-minute bench lifetime expired with no force job. 3: going
online, TIA assigned 172.31.254.241/24 to the PLCSIM virtual adapter (to reach
the CPU's second interface), which dropped every 169.254 connection and ended
the observer; the observer now records transport loss and reconnects. 4: the
bench refused to start on that adapter. The owner removed the address
(adapter back to 169.254.105.123/16); `Fraktal`, unregistered meanwhile, was
restored from its persisted storage. Go online through **PN/IE_1** and decline
TIA's offer to assign an address to the PG/PC interface.
