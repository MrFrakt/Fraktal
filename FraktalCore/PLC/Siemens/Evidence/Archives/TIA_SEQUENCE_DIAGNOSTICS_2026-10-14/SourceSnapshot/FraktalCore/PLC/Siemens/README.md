# Fraktal/TIA — Siemens TIA Portal binding (working tree)

**Status: Phase0 runtime evidence; Phase2 tooling started.** The binding is
[`Specification/Fraktal_TIA_Part_IV.md`](../../../Specification/Fraktal_TIA_Part_IV.md);
the plan is [`Specification/Siemens/SIEMENS_PORT_PLAN.md`](../../../Specification/Siemens/SIEMENS_PORT_PLAN.md).
There is **no released runtime library yet**. The tree contains the engineering
driver, bench tooling, spike fixtures, declaration/frame generator and a shared
[command-kernel prototype](Framework/Core/README.md).
Do not describe it as a conforming implementation.

Current continuation: generator 0.18 adds scoped first-out walks, named stalls,
HELD propagation and shared command-release cleanup to the selected LOAD_DB/view
profile. The synthetic runtime is
`%LOCALAPPDATA%\Fraktal\TiaStations\Sequence_Diagnostics_Runtime_20261014\FrkS12\FrkS12.ap20`;
the separate wired press is `Sequence_Diagnostics_Press_Offline_20261014` under
the same station directory. Earlier image names below describe dated gates.
See [the diagnostic report](../../../Specification/Siemens/Evidence/TIA_SEQUENCE_DIAGNOSTICS_2026-10-14.md)
and [the earlier integration/error report](../../../Specification/Siemens/Evidence/TIA_SEQUENCE_INTEGRATION_2026-10-14.md).

VS Code selects [Fraktal.TIA.sln](Fraktal.TIA.sln) for this Siemens workspace.
Historical evidence snapshots are excluded from Dart analysis/project discovery.
The separate Allen-Bradley offline probe still requires the installed Rockwell
SDK; selecting the Siemens solution avoids restoring that unrelated project.
Reload the editor window after changing these workspace settings.

The implementation now has `Framework/Core`, `Framework/Modules`,
[wired GRAPH/ST press demo and optional ST/LD examples](Examples/PressDemo/README.md), `Tests`, `Spikes`,
`tools` and [immutable evidence payloads](Evidence/README.md). The
[Siemens specification working set](../../../Specification/Siemens/README.md)
contains documents only. The relocation verifier preserves historical hashes.

The press demo now wires GRAPH AUTO/HOME and ST permissives in the owning Unit.
Main remains three calls. AUTO includes TC3 recovery choices, backwards jumps and
the native parallel join; ST/LD twins remain uninstantiated examples. The isolated
wired project is `%LOCALAPPDATA%\Fraktal\TiaStations\Config_Sets_Press_Offline_20261012\FrkS12\FrkS12.ap20`.
The Fraktal simulator runs the separate config-set/decision bench.
Generator0.9 adds bounded root decisions; its native checks and config/state/access
regressions are recorded in
[the current evidence](../../../Specification/Siemens/Evidence/TIA_GRAPH_RECOVERY_DECISIONS_2026-10-12.md).
Physical press qualification and full sequence frontier conformance remain open.

S12/S4 on simulated1516 V3.0 now compile the complete Core-derived type layout
and pass269-source canonical reimport. After the owner installed Advanced7,
native symbolic Web API reads work on the preserved image. The reference
timestamp mapping is now LDT: the candidate passes1081/1081 native witnesses,
1146/1146 SDK type witnesses and43/43 SDK scalar checks, retaining all88 types,
610 fields, Core capacities and full-width strings. The real HMI transport/date
parser passes36 checks across99 Good leaves. Full Unit rendering and commands
remain the Phase3 gate. See [fixture workflow](Spikes/S12_TypeMap/README.md) and
[upgrade evidence](../../../Specification/Siemens/Evidence/TIA_S12_WEBAPI_ADVANCED7_2026-10-10.md).

Earlier Advanced5 symbolic denial and its isolation controls remain frozen
history. The upgrade changed the manager, compatibility DLL and virtual adapter;
the comparison establishes recovery on this host without isolating one cause.
The prior one-hour host-time comparison failed; simulator-time consistency
passed separately. Hardware drift and synchronized UTC quality remain unproven.

Phase2 has started with the [reference declaration model](Tests/Declaration/README.md):
reusable types and root instances derive a registration inventory, validated
against Core widths and tiers. The [frame/registry generator](Tests/Generator/README.md)
now emits typed contracts, HAL bundles/calls, identity setup and compact registry
services. The two-root fixture passes103 runtime checks and native public/private
read checks;36 blocks/19 interfaces round-trip canonically. Its begin/end FCs are
test probes. The separate [Lifecycle fixture](Tests/Lifecycle/README.md) now uses
the actual shared command kernel and passes238 assertions in55 cases, including
STOP/RUN replay, plus100 native public reads and7 private refusals.47 blocks and
18 interfaces round-trip canonically. `--shared-runtime` includes the kernel;
every type then declares its command catalog and ParCfg timeout. Full Unit
facets, alarms/state/recipe services and Phase3 HMI remain open.
The subsequent [Unit control bench](Tests/Unit/README.md) now passes103 native
checks for modes, mailbox, release/reset and local Part services, including
STOP/RUN.79 blocks/34 interfaces compare canonically. The current saved image
belongs to TiaStations/Unit_Runtime_20261011/FrkS12/FrkS12.ap20 at that scope.
The subsequent [nested Unit/manual bench](Tests/UnitRouting/README.md) passes
120 native checks across24 instances, including three Unit levels, reset and
STOP/RUN.104 blocks/40 interfaces round-trip warning-free. Generator0.4 owns
typed manual routes, catalogs and pure release predicates. The current saved
image is TiaStations/Routing_Runtime_20261011/FrkS12/FrkS12.ap20.
The [static manifest/native HMI bench](Tests/Manifest/README.md) now passes241
native manifest checks and120 routing checks with generator0.5. The real HMI
hydrates492 entries for24 modules, renders the manual controls and commands the
simulated CPU from the rendered button. Mailbox payloads stay off cyclic reads.
117 blocks/41 interfaces round-trip warning-free; production114/41 compiles0/0.
The current saved image is TiaStations/Manifest_Runtime_20261011/FrkS12/FrkS12.ap20.
This GUI gate uses an explicit test-only display policy at NONE; authentication,
full alarm/release/retention services and sequence/GRAPH integration remain open.

The [access/session bench](Tests/Access/README.md) now passes122 native checks
and120 routing regressions with generator0.6. Salted local hashes, asynchronous
login/session enforcement and gated policy edits compile0/0. The HMI authenticates
an operator and commands the rendered button under its normal OPERATOR display
policy.129 blocks/42 interfaces round-trip; production125/42 compiles0/0.
User/policy persistence and full MESSAGE/alarm audit remain open. Current image:
TiaStations/Access_Runtime_20261011/FrkS12/FrkS12.ap20, owner instance Fraktal.
See [evidence](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_ACCESS_SESSIONS_2026-10-11.md).

The [state/alarm bench](Tests/StateAlarm/README.md) adds generator0.7 derived
states, nearest-Unit fault capture, AUTO_RESET/MANUAL_RESET active/closed events,
recursive blocking/reset and an optional event callback. Native96/96 plus23/23
nested ownership checks and122/122 authentication regressions pass. The real HMI
renders the fault and clears it through the reset button.148 blocks/45 interfaces
round-trip0/0; production142/45 compiles0/0. Current owner Fraktal image:
TiaStations/Alarm_Runtime_20261011/FrkS12/FrkS12.ap20. Shelving, durable sinks,
retention, full diagnostics/releases and sequence/GRAPH integration remain open.
See [evidence](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_STATE_ALARMS_2026-10-11.md).

The [config transaction bench](Tests/Config/README.md) adds generator0.8 editable
station config/model config, a local-retain provider and atomic model changes.
Native120 config checks,122 authentication and96 state/alarm regressions pass;
190 authored blocks/52 interfaces round-trip0/0, production183/52 compiles0/0.
The HMI/spec names now consistently read Station config, Line config and Model
config. Current Fraktal image: Config_Runtime_20261011/FrkS12/FrkS12.ap20.
Named sets, line config replication, other media and remaining Core services are
open. See [evidence](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_CONFIG_TRANSACTIONS_2026-10-11.md).

What *is* proven (2026-10-08, [evidence](../../../Specification/Siemens/Evidence/TIA_S2_S15_FIRST_BENCH_RUN_2026-10-08.md)):
the S2 fixture builds headless through Openness, compiles 0 errors / 0 warnings
(software and hardware), downloads to the physical CPU 1214C, and its 17 self-test
assertions pass on three consecutive download-and-restart runs.

And since 2026-10-08 evening ([evidence](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_S1W_WEBAPI_2026-10-08.md)):
the ASCII sources pass 17/17 on three more runs, and the CPU's licence-free **Web
API** is on — HTTPS with a pinned project certificate, one UMAC user `fraktal` with
read/write-process-data rights only. `tia_webapi.py` browses the spike Unit (126
leaves, private state absent), reads it, is refused every write except the mailbox,
and commits mailbox requests acknowledged in ≈ 140 ms. Throughput on the 1214C is
≈ 57 ms per request + 15 ms per leaf.

S11 continued on 2026-10-09
([evidence](../../../Specification/Siemens/Evidence/TIA_S11_SEMANTICS_2026-10-09.md)):
GRAPH supervision/acknowledgement/skip probes, OB100 and local invalid-index
handling compile 0/0; 28/28 on PLCSIM after download and direct STOP→RUN;
19/19 on the physical 1214C after download/start. Native bench STOP→RUN and two
code-only downloads in RUN also passed 19/19
([evidence](../../../Specification/Siemens/Evidence/TIA_S11_NATIVE_2026-10-09.md));
the second delta preserved DB, OB100 and mailbox state. The temporary
diagnostics mode right is removed; gateway access and 19/19 verified
([cleanup evidence](../../../Specification/Siemens/Evidence/TIA_S11_ENUMERATION_2026-10-09.md)).

Active GRAPH recovery continued on the simulated 1516 on 2026-10-10
([evidence](../../../Specification/Siemens/Evidence/TIA_S11_GRAPH_RECOVERY_2026-10-10.md)):
16 checks passed, with 28/28 in fifteen completed baseline harvests. Reset while
BUSY, STOP→RUN and reset after completion withdraw outputs and require a fresh
Arm in the test owner. An FC delta preserves observed BUSY/step/DB state.
A GRAPH body delta requests native sequence turn-off and DB reinitialization
despite unchanged exported interfaces; uninterrupted GRAPH updates remain
unpassed. The cylinder applies its interlock to outputs outside the idle guard.

S9 read/session probes also passed on the 1214C: two clients, pinned reconnect,
idle-token invalidation with re-login and retained-token reads through STOP→RUN.
**One Web API batch spans multiple PLC scans** (ten counter-read batches);
snapshots stay eventually consistent
([evidence](../../../Specification/Siemens/Evidence/TIA_S9_READ_SESSIONS_2026-10-09.md)).

S3 2026-10-10 measured the Unit idle guard and Core-derived optimized storage
([evidence](../../../Specification/Siemens/Evidence/TIA_S3_BUDGET_2026-10-10.md)).
The guard saves about 0.202 ms/idle Unit; both five-Unit/ten-CM variants passed
19/19. All compact tables together use 96.89/150 KB including the spike code.
Eight compact write definitions alone add 5.49 KB: share immutable metadata
instead of repeating dense maximum-sized tables per module. Candidate widths
and capacities live in [`Spikes/S3_Budget`](Spikes/S3_Budget/README.md); complete
runtime/press fit and the released family profile remain open.

The gateway reaches it with `--plc-endpoint s7web://192.168.0.10 --plc-certificate
<pem>` (`WebApiSessionClient`, OPCUA_TRANSPORT "Siemens S7 Web API transport"), and
the **unchanged Web HMI** served by that gateway discovered, rendered and commanded
(Start/Stop) the spike Unit on 2026-10-08 (S7 PASS, spike scope; evidence §10).

Decisions that shape this tree: TIA Portal V20 only; sequences in **S7-GRAPH
(SFC) + SCL (ST)**, with **unwired LD examples** and ST/LD release examples added
by the owner on 2026-10-11; the press bench is ported
**without power control**; self-description through the CPU's licence-free **Web
API** (JSON-RPC over HTTPS) into the Fraktal gateway, the embedded OPC UA server only
as an optional licensed projection (Part IV §1). S7-1500 is the reference family;
the S7-1200 is a constrained family.

**Current implementation target:** the simulated S7-1500 (`Fraktal`, CPU1516-3
V3.0, PLCSIM Advanced 7.0), with full Core/modules/press scope, SCL and generated
GRAPH. The physical 1214C's 150 KB budget and compact S3 candidates apply to its
secondary compatibility profile. They do not gate or reduce the S7-1500 work.

```
tools/
  TiaCli/                Fraktal.Tia.Cli — TIA Portal Openness V20 driver (C#, net48)
  s7_probe.py            read-only: identify a CPU (SZL), dump an SZL, harvest test results
  tia_webapi.py          Web API probe (S1W): pinned HTTPS, login, browse, snapshot, mailbox
  tia_lint.py            source gate (Part IV §5.3 T-rules) + test_tia_lint.py; pre-commit
  fraktal_tia_graph.py   S7-GRAPH writer (from a chain declaration + TIA's exported template),
                         reader (canonical dump) and SCL rendition parity + its tests
  Invoke-PlcSimInstance.ps1  S7-PLCSIM Advanced instance: host/status/run/stop, read-only tag read
  plcsim_results.py      validate a Runtime API read log against exact case IDs → JUnit
  s7_bench_mode.py       guarded classic mode probe for the named bench (refused by V4.7.3)
  Enable-TiaOpenness.ps1 admin setup: Openness group, and whitelisting of a driver build
Spikes/
  S2_Shape/              module FB frame, FRK_Begin/FRK_End/FRK_Hold, CM ×2, Unit, mailbox,
                         SCL AUTO chain with parameter instances, self-test harness,
                         TCP result server; station/build/download/webapi plans for the bench
  S11_Graph/             generated AUTO chain; Semantics/ (supervision/skip), Errors/ (local/OB121)
  S11_Scl/               physical 1214C startup and local-error observations, 19 rows total
  S9_WebRecovery/        concurrent/idle sessions, reconnect, batch coherence, retained-client STOP/RUN
```

## Bench

| Item | Value | Source |
|---|---|---|
| CPU | 1214C DC/DC/DC `6ES7 214-1AG40-0XB0`, FW **V4.7.3** | `s7_probe.py ident` (SZL 0x0011) |
| Address | 192.168.0.10; TIA PG/PC interface `Intel(R) 82574L Gigabit Network Connection` #2 (adapter `Ethernet1`, 192.168.0.123/24) | `interfaces --scan` |
| Station project | `%LOCALAPPDATA%\Fraktal\TiaStations\FrkSpikeS2\FrkSpikeS2.ap20` — holds the certificate the CPU trusts | see below |
| Running image | S2 + S11_Scl test image (ASCII sources), 19/19; result table TCP 2000, Web API HTTPS 443 | S11 evidence |
| Security (bench only) | access control via access level, anonymous = full access (no password), lowered protection accepted on download; web user `fraktal` (password DPAPI-protected in `TiaStations\FrkSpikeS2.webapi.secret`) | Part IV §14 |
| Use | nothing connected; may be downloaded/stopped/reset for Fraktal work (owner, 2026-10-08) | |

The bench is S7-1200: **no S7-GRAPH, no `REF_TO`, no named value types, 150 KB
work memory.** GRAPH renditions are proved on S7-PLCSIM V20 (S7-1500) until an
S7-1500 exists.

## Engineering workstation prerequisites

1. TIA Portal V20 (STEP 7 Professional) with Openness V20 — installed.
2. **Account in the `Siemens TIA Openness` group**, then a new logon.
3. **Every driver build whitelisted** in the Openness firewall — it gates headless
   instances too, by the exe's hash; a rebuild fails with
   `EngineeringSecurityException: The operation has timed out` until approved.
   Both: `tools/Enable-TiaOpenness.ps1 -WhitelistExe <built exe>` in an elevated shell.
4. .NET SDK (any recent) to build the driver (net48 via the reference-assemblies
   package; no Developer Pack).
5. Python 3 for `s7_probe.py` and `tia_webapi.py` (standard library only).

## Build the driver

```powershell
dotnet build FraktalCore/PLC/Siemens/tools/TiaCli/TiaCli.csproj -c Release --output FraktalCore/PLC/Siemens/tools/TiaCli/bin/candidate
# Never overwrite an approved build. Whitelist the exact candidate (prerequisite 3).
# Current approved driver: bin/candidate_s11_enumeration; hash in plan §11. Preserve its bytes.
```

## Run the S2 spike

```powershell
$st = "$env:LOCALAPPDATA\Fraktal\TiaStations"; $src = "<repo>\FraktalCore\PLC\Siemens\Spikes\S2_Shape"
$pc = 'pc=Intel(R) 82574L Gigabit Network Connection'
# 0. ONCE per target: station project (hardware, bench security posture, certificate)
Fraktal.Tia.Cli plan $src\station_1214c.plan --set work=$st
# 1. every build: delete program, import sources, compile 0/0, export (no controller access)
Fraktal.Tia.Cli plan $src\build_1214c.plan --set work=$st --set src=$src
# 2. CONTROLLER-CHANGING: download to 192.168.0.10 (needs current authorization)
Fraktal.Tia.Cli plan $src\download_1214c.plan --set work=$st --set $pc --set pcnum=2 --set um=keep --set protection=
#    (um and protection have no default: an unset one stops the plan before TIA starts)
# 3. ~40 s later: harvest the self-test rows from the test image's result server
python FraktalCore/PLC/Siemens/tools/s7_probe.py harvest --tcp 2000 --junit s2.xml
```

## Web API (S1W, licence-free self-description)

```powershell
# ONCE: web server on (HTTPS only), its certificate, the gateway's web user.
# The password is read from the environment only - never a plan, an argument or a log.
$env:FRAKTAL_TIA_WEB_PASSWORD = '<from the site secret store>'
Fraktal.Tia.Cli plan $src\webapi_1214c.plan --set work=$st
# then download_1214c.plan (CONTROLLER-CHANGING) carries it to the CPU
python FraktalCore/PLC/Siemens/tools/tia_webapi.py --trust-first probe   # pins the certificate once
python FraktalCore/PLC/Siemens/tools/tia_webapi.py tree --root SpikeUnit
python FraktalCore/PLC/Siemens/tools/tia_webapi.py snapshot --root SpikeUnit --repeat 10
python FraktalCore/PLC/Siemens/tools/tia_webapi.py mailbox --root SpikeUnit --kind 3 --int 1
```

**One manual step on S7-1200 V4.7:** Openness V20 cannot set the web server's
*certificate type* (neither getter nor setter). Set it once in the TIA editor —
PLC_1 > Properties > Web server > Security, "certificate loaded via the software" —
and save; the station project keeps it. Until then the hardware compile fails and
download refuses. The first download into the new posture needs `--set um=reset`
and `--set protection=--accept-lower-protection`; later ones `um=keep` and an empty
`protection=`.

The pin lives in `%LOCALAPPDATA%\Fraktal\TiaStations\<host>.webapi.pin`; a changed
certificate fails closed until someone deliberately re-pins it. `mailbox` writes the
arguments, then `Sequence` alone, and waits for `AckSequence`; it never replays.

Every driver run prints one JSON object per line — keep the log with the
evidence record. `download` refuses unless `--confirm-target` equals the CPU
address configured in the project, and answers security-relevant questions only
when an explicit flag says so.

**If the bench refuses to connect** ("Connect to module failed" / "Changing to
online mode failed"): the CPU holds a certificate from a project you are not using.
Use the station project. Recovering a CPU that holds a foreign certificate is a
deliberate, logged trust decision: add `--trust-plc PLC_1` to one `download`.

## Rules that already apply

- Sources are **ASCII** text (`.udt`, `.scl`, `.db`, GRAPH SimaticML) imported
  through Openness in **file-name order** — the numbered prefix is the dependency
  order. One `TYPE` per `.udt`, nothing before the keyword. TIA reads BOM-less files
  as ANSI. (The S2 sources are ASCII since 2026-10-08; the image running on the
  bench was built before that conversion, until the next build replaces it.)
- The TIA **program** is a build output; the TIA **project** is per-station
  engineering state (certificate) kept under `%LOCALAPPDATA%\Fraktal\TiaStations`.
  Never commit `*.ap20`.
- Contract members sit **directly on the module instance** (the HMI finds a module
  by its `Status` child). `Status` and the root `HmiRequest` are published statics;
  outputs are written, never read, by their own block. Private state carries
  `ExternalAccessible/ExternalVisible/ExternalWritable := 'False'`; only `HmiRequest`
  is `ExternalWritable` for operator commands. The optional sink adapter exposes
  its metadata-only `FRK_EventDeliveryReceipt.Request` separately; status/replies
  and all implementation storage remain protected.
- Every module FB calls `FRK_Begin` first and `FRK_End` last, inside a generated
  quiescent guard (Part IV §3.14): an initialised, READY module with Execute/Abort low
  and nothing pending skips the lifecycle (≈ 0.20 → 0.053 ms per idle CM on the
  1214C, measured); identity setup and derived `OutImm` run outside the guard, every
  scan. The S2 Unit uses two fences driven by one predicate after its mailbox;
  children, chain-result clear and mirrors stay outside (about 0.202 ms saved
  per idle Unit, S3 2026-10-10). Every child is called exactly once per scan by
  its owner. Full mode-hook quiescence remains a generator/runtime gate.
- Identity comes from `#w := GetInstancePath(SIZE := 0);` at setup, never from a
  typed string. A member named `Name` is declared quoted (`"Name"`).
- An open interlock during a command is **HELD** (busy, outputs off, reason at LOW,
  self-resume), as in the TC3 reference — never a fault.


Generator 0.10 adds [named station/model config sets](Tests/ConfigSets/README.md),
with PLC-owned save/list/load/delete and JSON-lines export/import through the
existing generic HMI. Typed owner handlers validate the entire set before a
recursive commit; catalogs and transfer work are allocated per deployed root.
The press demo opts into four station config slots and remains compiled offline.
The current owner image is Config_Sets_Runtime_20261012/FrkS12/FrkS12.ap20. See
[the current set evidence](../../../Specification/Siemens/Evidence/TIA_CONFIG_SETS_2026-10-12.md).
File/database media, line config and user/policy/alarm retention remain subsequent
work. This continuation does not release a conforming runtime library.

Generator 0.11 adds [user and access-policy retention](Tests/AccessPersistence/README.md)
with whole-image validation and volatile sessions. The current owner image is
Access_Persistence_Runtime_20261012/FrkS12/FrkS12.ap20; the wired press remains offline
in Access_Persistence_Press_Offline_20261012/FrkS12/FrkS12.ap20. See
[the current retention evidence](../../../Specification/Siemens/Evidence/TIA_ACCESS_PERSISTENCE_2026-10-12.md).
Alarm retention, other persistence media and broader provider forms remain open.

Generator 0.12 adds optional [closed-event history retention](Tests/AlarmPersistence/README.md)
for explicitly selected Unit scopes. Shared Core services own validation, restore
and append. The current owner image is Alarm_Persistence_Runtime_20261012/FrkS12/FrkS12.ap20;
the separate wired press is Alarm_Persistence_Press_Offline_20261012, compiled offline.
See [history evidence](../../../Specification/Siemens/Evidence/TIA_ALARM_HISTORY_2026-10-12.md).
Active-alarm restart policy, external durable sinks and other persistence media
remain later gates.

Generator 0.13 adds optional [manual-reset alarm recovery](Tests/AlarmRecovery/README.md)
for a subset of history-selected Units. Shared services preserve ACTIVE/WAIT_RESET
latches, reconcile fresh faults, fence descendant startup and complete interrupted
closes. Commands, outputs and sessions stay volatile. Current projects are
Alarm_Recovery_Runtime_20261012 and Alarm_Recovery_Press_Offline_20261012; the press
remains compiled offline. See [recovery evidence](../../../Specification/Siemens/Evidence/TIA_ALARM_RECOVERY_2026-10-12.md).


Generator 0.14 adds optional [retained event delivery](Tests/EventDelivery/README.md)
for selected Units, with framework-owned FIFO capture and a SQLite collector that
commits before sending a gated metadata receipt. Current simulator project is
Event_Delivery_Runtime_20261012; the wired press compiles offline in
Event_Delivery_Press_Offline_20261012. Independent service authentication, other
persistence media and physical loss commissioning remain open. See
[delivery evidence](../../../Specification/Siemens/Evidence/TIA_EVENT_DELIVERY_2026-10-12.md).

The [S16 persistence spike](Spikes/S16_Persistence/README.md) qualifies asynchronous
load-memory reads/writes, independent RAM/load values, optimized UNLINKED banks,
restart and private access boundaries. Current diagnostic runtime is
Load_Memory_Only_Runtime_20261013; its framework matches the event-delivery image.
Config, named sets, users and policy continue using LOCAL_RETAIN while the shared
keyed document adapter is integrated. The separately compiled press is unchanged.
See [S16 evidence](../../../Specification/Siemens/Evidence/TIA_LOAD_MEMORY_2026-10-13.md).


Generator 0.15 adds the selected [shared LOAD_DB document medium](Tests/Persistence/README.md). Station config, all offered model config, named sets, private users and root policy restore through the generated composition barrier. Confirmed load-memory documents replace cached values; native read-back precedes durability. Current runtime is Persist_Medium_Runtime_20261013 and the separate offline GRAPH/ST press is Persist_Medium_Press_Offline_20261013. MAIN remains three calls in the press, and optional ST/LAD examples remain unwired. See [the consumer evidence](../../../Specification/Siemens/Evidence/TIA_PERSIST_MEDIUM_2026-10-13.md). The original S16 diagnostic projects above are preserved.

Generator 0.16 adds the optional [shared sequence view](Tests/SequenceView/README.md): Core definitions served by the manifest, per-leg cursors, PLC-owned history and sparse annotations. The owning frame controls scan/mode boundaries; projects add no scheduling call. Current runtime is Sequence_View_Runtime_20261013 (synthetic events, LOCAL_RETAIN config); the separate Sequence_View_Press_Offline_20261013 compiles the view with LOAD_DB. Native 122 checks and press readback pass; native HMI table rendering and combined boot qualification remain work. See [evidence](../../../Specification/Siemens/Evidence/TIA_SEQUENCE_VIEW_2026-10-13.md).
