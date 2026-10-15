# What this workstation can do with Siemens controllers — capability map (2026-10-09)

What an agent here has **demonstrated**, end to end and without the TIA user
interface, while building the Fraktal/TIA port. Every row names the tool, where it
was proven, its limits, and the evidence. Use it to plan work. It tells you what is
already solved, and where a request needs a human, a licence or new hardware.
Marks: **[measured]** done on this workstation, **[pending]** started but not proven.

Current configuration continuation,2026-10-15: generator0.21 supports typed
values/enum choices/array elements and token-bound current station/model exports
without a saved slot. Exact numeric witness33 and transaction138 pass; runtime
381/84 and separate offline press437/102 canonical witnesses and warning-clean
compiles pass. Saved-set241, live HMI and final privacy/idle48 also pass.
See [typed configuration](typed-configuration.md) and its report
for final HMI/regression scope, numeric conversion/REAL RPC limits, owner
recovery and remaining port features.

Evidence lives in `C:\Projects\Fraktal\Specification\Siemens\Evidence\`, abbreviated
below: S2 = `TIA_S2_S15_FIRST_BENCH_RUN_2026-10-08.md`, S1W = `TIA_S1W_WEBAPI_2026-10-08.md`,
S3 = `TIA_S3_SCAN_AND_MEMORY_2026-10-08.md`, G = `TIA_S11_GRAPH_PLCSIM_2026-10-09.md`,
SEM = `TIA_S11_SEMANTICS_2026-10-09.md`. Tools are in
`C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools\` (one source; this KB only points
at them).

## Targets available

| Target | Identity | Use |
|---|---|---|
| Physical bench | CPU 1214C DC/DC/DC `6ES7 214-1AG40-0XB0` FW V4.7.3 @ 192.168.0.10, nothing wired | S7-1200 evidence; owner-authorized for free use. `s7_probe.py ident` runs before every controller-changing act (`bench-192.168.0.10.md`) |
| Simulated S7-1500 | CPU 1516-3 PN/DP `6ES7 516-3AP03-0AB0` V3.0 on S7-PLCSIM Advanced 5.0, instance `FrkS11`, 192.168.252.1, Softbus only | GRAPH, OB121, S7-1500-only features |
| Physical S7-1500 | none | no S7-1500 hardware claim is possible yet |

## Engineering (TIA Portal V20 through Openness, `Fraktal.Tia.Cli`)

| Capability | How | Proven | Limits / prerequisites |
|---|---|---|---|
| Create a station project headless: CPU by order number + firmware, IP, master secret, access control or access levels, UMAC users/roles, web server and its certificate | plan files (`station_*.plan`, `webapi_1214c.plan`) | 1214C, 1516 V3.0 **[measured]** S2, S1W, G | **One editor step on S7-1200:** the web server *certificate type* (no Openness getter/setter). Keep each station project for good: it holds the CPU's trusted certificate |
| Import SCL/UDT/DB external sources and SimaticML blocks; compile software and hardware **separately**; export XML/SCL | `import-sources`, `import-xml`, `compile [--hw]`, `export [--scl]` | 0/0 on both families **[measured]** | sources ASCII only; `GenerateBlocksFromSource` error text is empty, so bisect; `compile --hw` is not the software gate (SEM) |
| Generate S7-GRAPH charts from a declaration, read any chart back, prove parity with the SCL rendition | `fraktal_tia_graph.py generate/dump/parity` + TIA's exported reference chart | compile 0/0, TIA re-export identical, ran on PLCSIM **[measured]** G, SEM | Openness cannot *create* a GRAPH block, so one drawn chart is the template. Actions take no `IF`/expressions. A GRAPH FB cannot be a multi-instance (`graph-simaticml-and-plcsim.md`) |
| Discover settings Openness hides: unlisted attributes, service properties, internal enum names | `hw-attributes --probe`, `service-get/set/call`, `block-attribute`, `project-get/set`; reflection over `Portal V20\Bin\Siemens.Simatic.Hwcn.*.dll` | **[measured]** S1W | a name missing from `GetAttributeInfos()` may still work, so probe it by name |
| Guarded download (HW + SW): exact target address, every question logged, security questions answered only by explicit flags | `download --confirm-target … [--user-management keep\|update\|reset] [--accept-lower-protection] [--plc-password-env]` | 1214C ×many, PLCSIM ×many **[measured]** | the default `TurnOffSequence` stays on for GRAPH DBs; trust on first use (`--trust-plc`) only as a logged recovery, never in a plan |
| Download changes in RUN without reinitialization | `download --changes-only` (SoftwareOnlyChanges) | **[pending]** built in candidate `bin\candidate_s11`, awaiting the owner's whitelist | — |
| Go online / read the online state over TLS | `online-state` | **[measured]** | a recreated project is refused, so use the station project |

## Runtime: testing, results, data

| Capability | How | Proven | Limits |
|---|---|---|---|
| Identify any S7 CPU read-only (article, firmware), even with PUT/GET off | `s7_probe.py ident` (SZL 0x0011) | **[measured]** | SZL 0x001C refused on 1214C V4.7 |
| Run a self-test image and harvest machine-readable rows without licences | test image serves a non-optimized result record over passive OUC TCP 2000; `s7_probe.py harvest --tcp 2000 --junit` | 17/17 ×3, 19/19 on 1214C **[measured]** S2, SEM | test images only, never a production download |
| Same on the simulator | `Invoke-PlcSimInstance.ps1 -Action read` + `plcsim_results.py read.log --cases 1-28 --junit` | 19/19, 28/28 **[measured]** G, SEM | `String` leaves are not readable through the API |
| Simulator lifecycle, headless | `Invoke-PlcSimInstance.ps1 host / status / run / halt / off / stop` (mode/power actions need `-ConfirmTarget` = a Softbus ControllerIP) | **[measured]** G, SEM | a NEW registration means a new certificate and one logged trust step; the host ends after `-MaxMinutes`; ~4 GB RAM, so power the instance off during builds |
| Warm restart (STOP→RUN) on the simulator, with OB100 first-scan observation | `-Action halt` then `run` | 28/28 after restart **[measured]** SEM | — |
| Warm restart on the physical 1214C | classic S7comm STOP is refused with 16#8104 (`s7_bench_mode.py`); the native web start page has STOP/RUN forms for a user with `WebChangeOperatingMode` | **[pending]** (another session's evidence folder `TIA_S11_NATIVE_2026-10-09`, no record yet) | grant the mode right only temporarily, then restore and verify |
| Read/write symbolic tags licence-free | CPU Web API: `tia_webapi.py probe/browse/tree/snapshot/mailbox` (pinned HTTPS, env-var password) | **[measured]** S1W | 1214C: ~57 ms/request + ~15 ms/leaf, one request at a time, 2.75 s TLS handshake |
| Live HMI on a Siemens CPU | Fraktal gateway `s7web://` transport (`WebApiSessionClient`) + unchanged Web HMI | rendered and commanded the spike Unit **[measured]** S1W §9–§10 | read-only unless a write root is configured |
| Measure CPU memory and per-module cost | system web page `Diagnostics > Memory` (form login, then **log out**); cycle via the program's own clock read over the Web API | **[measured]** S3 | the only memory source on 1214C; Openness, SZL and the Web API have none |
| Instruction-error behaviour | `GET_ERR_ID` local handling; OB121 on 1500 | **[measured]** SEM | S7-1200 has no OB121 |

## Not possible here (yet) — say so instead of trying

- Rebuild the Openness driver **and** use it unattended: every rebuild must be whitelisted
  by the owner in an elevated shell (`agent-workflow-lessons.md`).
- Set PUT/GET on S7-1200 through Openness; set the S7-1200 web certificate type through Openness.
- Enable the embedded OPC UA server for production use: it needs a runtime licence. The Fraktal
  default transport is the Web API.
- Any S7-1500 *hardware* claim (timing, memory, OPC UA budgets): no S7-1500 is on the bench.
- Classic S7comm STOP/RUN on the 1214C V4.7.3 (16#8104).

## Previous Fraktal continuation, 2026-10-13

Shared sequence tables/frontier/annotations now pass122 native synthetic checks, runtime/press compile0/0 and canonical GRAPH/LAD readback. The existing Fraktal owner/keeper remains running during builds; do not apply older temporary-host/power-off advice to it. Earlier LOAD_DB consumer gates remain preserved; the currently loaded view fixture uses LOCAL_RETAIN config. Native HMI/combined boot, diagnostic/provider/module/deployment closure remain open. See [current scope](shared-sequence-view.md) and its handover link.

## Current Fraktal continuation, 2026-10-14

[Shared cycle profiling](shared-cycle-profiling.md) records generator0.19 and
the current LOAD_DB runtime, offline press, approved cleanup and keeper13476. Preserve
that owner during builds. Historical keeper5380 is gone after the VM restart;
never apply temporary-host/power-off instructions to the persistent owner.
The new note states completed gates and the remaining port/physical-loss scope.

## Current Fraktal continuation, 2026-10-15

[Shared sequence recovery](shared-sequence-recovery.md) records generator0.20,
the current LOAD_DB runtime and offline press. Retained-step continuation and
explicit restart, command/delay/event rearm, both abort paths, late kernel faults,
HELD and quiescence are measured on a synthetic GRAPH. Native GRAPH scan/reset
boundaries are shared; applications add no scheduling call. Preserve the keeper,
simulator, credentials and sealed evidence. Provider/line config, module/HAL,
baseline/reset/OEE and deployment/physical acceptance remain open.
