# Nested Unit cascade and manual routing (2026-10-11)

Scope: isolated simulated1516 V3.0, Advanced7, TIA V20. Evidence:
C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_UNIT_ROUTING_2026-10-11.md.

- **[measured]** Generator0.4 derives typed routes from a forest with24 instances,
  two roots and two nested Unit levels.52 generated/54 test source files;
  104 blocks/40 interfaces canonical authored/native plus ordered reimport,
  software/hardware compile and re-export, all0 errors/warnings. Default production
  entrypoint102 blocks/40 interfaces compiles0/0 in a separate review project;
  it was not downloaded. Catalog/CatalogCount match the existing generic HMI names
  and derive from the same command ids/labels as timing.
- **[measured]** Extended native series120/120 twice, each including STOP/RUN and
  fresh manual commands. Earlier Unit series103/103 still passes current services.
  Manual access, target/direction/common reason rollup, query purity, command
  handshake/Execute drop, peer/unknown target rejection, nested owner mode/permit,
  trusted Start/Stop/reset cascade, unsupported mode safe Stop/event, deferred
  timeout/immediate exit, hidden scratch/conditions and nested mailbox refusal.
  This is native API proof, not GUI rendering or full Core conformance.
- **[measured]** VAR_INPUT Execute cannot be written inside its own FB without a
  warning, whether via INOUT or direct assignment. Generated PARENT calls perform
  terminal manual release against the child input without warnings. Automatic
  commands are untouched. Typed FB INOUT route parameters compile and round-trip.
- **[measured]** ST_HmiRequest.TargetPath maps to WString (Core STRING255). Keep
  that width/type during path comparison; compare against converted Status.Name.
  A67KB response in FC TEMP exceeds this CPU's16KB local-data limit. One private
  shared scratch response fixes it without reducing Core capacities/widths.
- **[measured]** Unit pure Release owns common HAL conditions once and refreshes
  before consuming requests or routing into a nested Unit. ManRelease is a set of
  unconditional conditions with unique bounded literal slots/command ids. Full
  reports retain common reasons before selected directional conditions and owner
  paths. Invalid/duplicate slots are rejected before source import.
- **[measured]** Preserve incoming cascade events when Core.ReleasePending cancels
  the old command: clearing that event in child preparation lost the second-level
  mode change. Reset events must likewise survive preparation until their callback.
  Parent reset cancels pending mode/start work and active nested reactions run once.
- **[measured]** Native nested HmiRequest writes return205 through the parent's
  read-only child boundary. Test-only independent calls use the same operation
  authority with TrustedFALSE; cascade uses TrustedTRUE only for access, preserving
  mode/state/release checks. Independent nested HMI actions need future root routing.
- **[measured]** AUTO rejection control proves graceful Stop at the cycle boundary.
  HOME exits immediately; a StopPending expectation there was wrong. Final controls
  measure both policies. Core names EVENT_CHILD_MODE_UNSUPPORTED but assigns no
  E_Reason ordinal yet; prototype history uses2008 plus std.event.childModeUnsupported.
  Full event registration/audit lifecycle remains open.
- **[measured]** Final115 tool tests/33 consistency tests pass; lint/replay/LF/ASCII/
  diff checks pass. Command kernel bytes equal prior238-assertion evidence; no new
  command-kernel runtime run is claimed. Root action queries cover implemented
  Stop/mode/reset/manual gates; unsupported actions stay withheld. Complete alarm/
  control-domain/frontier/configuration releases remain open.

Current saved image: LOCALAPPDATA/Fraktal/TiaStations/Routing_Runtime_20261011/FrkS12.
Routing_Verify_20261011 is the review/compiler project. Previous stations/secret/pin/
certificates preserved. Owned host4884 exited00:46:37UTC; zero registered instances,
prior NetworkMode2 restored. Driver hash unchanged; no new whitelist/physical change/
commit. Next: static manifest/native HMI forest/render/commands, complete Core
services, modules/press without power control and SCL/GRAPH parity. No150KB cap
on the S7-1500 reference. Held manual actions and durable UID/retention remain open.
