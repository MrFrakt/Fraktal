# TIA Portal automation â€” verified engineering knowledge (V20)

Built 2026-10-08 while starting the Fraktal/TIA port. Every fact below is
marked with how it is known: **[measured]** on this workstation/bench,
**[help]** from the indexed TIA V20 information system (`..\tia-v20-help`),
**[api]** from `PublicAPI\V20\Siemens.Engineering.xml`, **[sheet]** from a
Siemens data sheet in `..\manuals\downloaded`.

| File | Contents |
|---|---|
| `press-bench-network-and-topology.md` | Live saved FraktalBench/1214C, controller-initiated TCP streams, scoped P8 topology, strict generic HMI and power-loss recovery, guarded API7/network findings, wrong-target diagnosis, shared Disconnect and SHA256 certificate workflow |
| `line-press-and-public-admission.md` | Generator0.25 complete Line admission and press composition,37 Line/64 GRAPH checks, fresh-project617/162/71 read-back, target latching and P12 boundary |
| `runtime-models-and-atomic-catalog.md` | Generator0.24 model/set cloning, BUSY isolation, atomic catalog/config checkpoint and recovery,31 PLC assertions/110 live checks, native fresh/press/LOCAL_RETAIN proof and capture storage classes |
| `data-classes-and-policy-recovery.md` | Generator0.23 root class policies, manifest redaction, atomic set authorization, independent LOAD_DB recovery,16 PLC assertions/97 live checks and sequential resource discipline |
| `operations-health-graph-and-test-gate.md` | Generator0.22 operations/health/gates/capture, wired GRAPH jumps and pacing, host rings, native assertion gate, simulator disk lessons and remaining scope |
| `line-sets-and-bound-mirrors.md` | P1 root-scoped line sets/current export, source-bound synthetic mirror, offline LOAD_DB restore, 165+64 live checks; partial profile stays isolated |
| `typed-configuration.md` | Generator0.21 typed values/enum choices/array elements, token-bound current exports, selected LOAD_DB restore, native readback and remaining port scope |
| `shared-sequence-recovery.md` | Current generator0.20 retained-step recovery, native GRAPH scan/reset boundaries, abort/quiescence/HELD gates and remaining port scope |
| `shared-cycle-profiling.md` | Current generator0.19 timing/history/HMI gates, late-kernel completion order, consumed discovery, approved disk cleanup and remaining port scope |
| `shared-sequence-diagnostics.md` | Scoped first-out/stall/HELD services, command-release cleanup, native regression/readback and current restored owner |
| `sequence-restore-hmi-integration.md` | Combined LOAD_DB quiesce/boot and live generic chart, startup tiering/array-path joins, error diagnosis and restored simulator owner |
| `load-memory-transfer.md` | Native optimized/UNLINKED load-memory transfer, restart/privacy gates and next document-medium integration |
| `retained-event-delivery.md` | Dedicated receipt mailbox, SQLite commit/deduplication, banked timing checkpoint correction and native qualification |
| `manual-alarm-recovery.md` | Selected ACTIVE/WAIT_RESET recovery, observed duration, startup fencing, interrupted-close journal and native qualification |
| `program-groups-and-press-examples.md` | Owner-requested program/type groups, Main extraction, unwired ST/LD/GRAPH examples, native graph gates and evidence relocation |
| `capabilities.md` | **What this workstation can do**: every demonstrated end-to-end capability (engineering, download, test harvest, simulator, Web API, HMI, measurement) with tool, scope, limits and evidence; what is not possible here |
| `agent-workflow-lessons.md` | **How to work**: controller-act guards, station-project identity, driver whitelist discipline, secrets, evidence and claim rules, workstation limits, encodings and shell quirks |
| `verified-gotchas.md` | **Start here when something fails**: every Openness / SCL-source / security / download pitfall hit on the real bench, with cause and fix |
| `openness-v20.md` | Prerequisites, assembly loading, API map with verified signatures, download questions, gotchas |
| `s7-1200-vs-1500.md` | Language/feature scope by family (what exists on S7-1200 V4.7 vs S7-1500), OPC UA server limits |
| `bench-192.168.0.10.md` | The physical bench CPU: identity, ports, how it was identified |
| `graph-simaticml-and-plcsim.md` | Generating S7-GRAPH as SimaticML (template from a TIA export, verified action/transition forms, what is refused), GRAPH runtime semantics (same-call step switch, `INIT_SQ`, no multi-instance), headless S7-PLCSIM Advanced 5.0 (register, download, read tags) |
| `plc-communication-options.md` | Hostâ†”CPU protocols without a runtime licence (Web API vs OPC UA vs PUT/GET vs OUC vs PROFINET vs Modbus); Web API contract; enabling web server, users and certificate through Openness |
| `unit-controls-and-local-carrier.md` | Unit profile, real mailbox/access/release/reset, local part events and native restart controls |
| `nested-units-and-manual-routing.md` | Three-level mode/reset cascade, typed manual routes and live release reports; native120 controls |
| `shared-command-kernel.md` | Generated shared command lifecycle: latching, reset/abort/HELD/timeout/timing; simulator and native read-back proof; remaining Unit facets |
| `core-type-map-and-roundtrip.md` | Complete Core type census on simulated1500, strict field parsing, wide strings, SDK timestamp encodings, source round-trip and simulator Web API/time limits |
| `project-translation-roundtrip.md` | **Project translation / bulk-text round-trip** (2026-10-09, PL8051 zhâ†’en end-to-end): XML reimport of blocks/types/tag tables, `Export/ImportProjectTexts` semantics (source column = identification key, target column = where translations land; the **reference language** decides what users see), rename support matrix, WinCC Unified has no screen export and no `ICompilable`, mandatory `Save()` per session, verified pipeline and CJK verification |

Tools that implement this knowledge live in the Fraktal repository (one source):

| Tool | Path | Use |
|---|---|---|
| `Fraktal.Tia.Cli` | `C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools\TiaCli` | Openness V20 driver: plan files; project, hardware, security (UMAC, web server, certificate, master secret), reflection access to services/attributes, import/compile/export, guarded download, online state; JSON-lines log. Full command catalogue: `openness-v20.md` |
| `s7_probe.py` | `C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools\s7_probe.py` | read-only S7comm: `ident` (SZL 0x0011, works with PUT/GET off), `harvest` (non-optimized DB â†’ JUnit) |
| `tia_webapi.py` | same folder | Web API client: pinned HTTPS, login from env, browse/tree/snapshot/mailbox |
| `fraktal_tia_graph.py` | same folder | S7-GRAPH writer from a chain declaration + TIA template, canonical dump, SCL parity |
| `Invoke-PlcSimInstance.ps1` | same folder | S7-PLCSIM Advanced: host/status/run/stop an instance, read-only tag read |
| `plcsim_results.py` | same folder | validates magic, Done, rows/counters and exact case IDs in a Runtime API read log, then emits JUnit |
| `s7_bench_mode.py` | same folder | exact-IP/order/firmware guarded classic mode probe; 1214C V4.7.3 refuses control with 16#8104 |
| `Enable-TiaOpenness.ps1` | same folder | admin: add account to `Siemens TIA Openness`, optional exe whitelist |
| `TiaTranslate` | `C:\Projects\SiemensAgent\pl8051-translate\TiaTranslate` | Openness V20 driver for project-internal mass edits: probe/survey introspection, PLC XML + project-texts xlsx round-trip, identifier renames (`apply-jsonl`), script/reference patching (`apply-scripts`), language switch (`set-lang`), compile; JSON-lines log; `--save` per session. See `project-translation-roundtrip.md` |

## Fast answers

Current Fraktal port state: generator0.21, [typed configuration and current
exports](typed-configuration.md). That note identifies the current runtime/offline
press, restored keeper and measured gates. Continue implementation without a new
handover. The [0.20 recovery](shared-sequence-recovery.md) and
[0.17 integration](sequence-restore-hmi-integration.md) retain their dated scope.
**[measured]**

Latest P1 workbench continuation: [line sets and bound mirrors](line-sets-and-bound-mirrors.md).
Owner sets/current export and source-bound mirror persistence are measured;
shifts/classes/capture and complete press profile integration remain. **[measured]**

- *Can a block find out its own instance name?* Yes: `#w := GetInstancePath(SIZE := 0);` returns `"IDB".Inst.Sub` on S7-1200 and S7-1500 (the help's `OUT =>` form is rejected); expensive â€” call once, not cyclically; not directly in an OB. **[measured]**
- *Why can't I connect/download any more after rebuilding my project?* The CPU accepts secure PG/PC communication only with the certificate from the project you downloaded; a recreated project has a new one. Keep the project; to recover, answer `TlsVerificationConfiguration` with `Trusted` on `ConnectionConfiguration.OnlineLegitimation`. **[measured]** â€” see `verified-gotchas.md`.
- *How do I read/write optimized DB tags from a PC without buying the OPC UA licence?* The CPU's Web API (JSON-RPC over HTTPS, S7-1500 and S7-1200 â‰¥ V4.5): web-server user with ReadTag/ModifyTag, `Api.Login`, `PlcProgram.Read/Write/Browse`, tags need "Accessible from HMI/OPC UA/Web API". **[manual]** â€” see `plc-communication-options.md`.
- *How do I bulk-translate or mass-edit project texts (incl. WinCC Unified screens/alarms)?* PLC objects: XML export â†’ patch â†’ `ImportOptions.Override`. All free texts (Unified included): `ExportProjectTexts`/`ImportProjectTexts` xlsx. Semantics that bite: the source column is an identification key (translations land only in the target column), rows fail by internal ID if the object was recreated, and users see the **reference language** â€” switch `LanguageSettings.ReferenceLanguage` after importing. Verify by re-export + scanning, not by return codes. **[measured]** â€” see `project-translation-roundtrip.md`.
- *Why did my Openness changes vanish after the run?* The session closed without `Project.Save()` â€” Openness close discards modifications silently. Every mutating session must end with a save (also: `ImportProjectTexts` returns rc 0 with state *Warning* on row misses â€” verify by re-export). **[measured]**

- *What resolved FrkS12 symbolic Web API denial?* After the owner installed Advanced7, the saved full image accepts Read/Browse with unchanged pin and process-data-only mask24. Manager, API5 compatibility DLL and adapter changed together; one root cause is not isolated. The1500 LDT reference candidate passes native/HMI type mapping and source round-trip; full Unit rendering/commands remain owed. See `core-type-map-and-roundtrip.md`, Advanced7 continuation. **[measured]**

- [Static manifest and native HMI](static-manifest-and-native-hmi.md) - windowed pager, canonical indices, private catalogs, read gates and real-network widget proof. **[measured]**

- [Local access and owner instance](local-access-and-owner-instance.md) - salted hash/session gates, real HMI login, adoption without unregistering, runner trust propagation and evidence availability. **[measured]**

- [Derived states and alarm lifecycle](derived-state-and-alarm-lifecycle.md) - state freshness, nearest-Unit events, nested blocking/reset, optional callback, native/HMI gates and saved-image recovery after reboot. **[measured]**

- [Station and model config](station-and-model-config.md) - consistent category names, typed capabilities, independent restore, atomic local-model change and retentive simulator evidence. **[measured]**

- [GRAPH branches and root decisions](graph-branches-and-root-decisions.md) - native branch ports/order, jump attachment, exact whitelisted driver selection and root-bounded decision service. **[measured]**

- [Private access retention](private-access-retention.md) - native member remanence, whole-image validation, volatile grants, stable loss publication and completed-startup synchronization. **[measured]**

- [Shared LOAD_DB document consumers](shared-load-db-documents.md): generator0.15,903native assertions, private banked documents, retry/quiescence/repair and warning-clean runtime/press. **[measured2026-10-13]**

- [Candidate contracts](candidate-contracts.md) - immutable V1 subset, pre-commit/CI checks, native-interface comparison and explicit remaining R3 scope. **[measured 2026-10-15]**

- [Physical press I/O bridge](press-io-bridge.md) ? confirmed 1214C companion, cyclic TCP, native tests and gated commissioning. **[measured 2026-10-15]**

- [Typed line engine](typed-line-engine.md) - P1 owner/mirror kernel, 51 native assertions; production composition and LOAD_DB integration remain. **[measured 2026-10-15]**

- [Shared line owner and LOAD_DB](shared-line-owner-load-db.md) - isolated two-root owner wiring, 54 live checks, durable restart and generic HMI editor; incomplete profile stays workbench-only. **[measured 2026-10-16]**
