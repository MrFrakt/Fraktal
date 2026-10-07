# Core and Press TC3 feature audit — 2026-10-06

This is a source audit with primary vendor documentation, not a production
conformance certificate. Scope: current working tree based on public commit
`c66e91ce353c578b439e258f588777ab9f071cc8`, including the current clock change.
Core Part I, TC3 Part II and the safety profile remain normative. Old dated
reports are historical; current source decides whether a gap remains.

## Status after the 2026-10-06 implementation (Core 0.25.0.0 / Modules 0.11.0.3)

| Finding below | Status now | Remaining |
|---|---|---|
| Protected local-user persistence | **Implemented.** Retained as one image document on a confidential persistence medium - by default a file medium in the Boot directory, on the Press bench the station's data folder - with loss/failure through §3.8b (IMPLEMENTATION_NOTES §160, §163); the hidden-persistence warnings are gone from both full builds. Restart, re-activation, corruption, deletion, failed write and recovery accepted on the isolated runtime. | Uncontrolled power loss and the Press target itself are untested. |
| Station, line and model configuration and parameter sets as files (owner request) | **Implemented** behind the project-chosen `I_PersistMedium` (file or retentive pool; §163): readable JSON-lines documents, restored at start through the staged set path, rewritten after every accepted write; Press uses `C:\ProgramData\Fraktal\PressDemo\`. | A database medium waits for a named server and TF6420 licence; the Press target, its write filter and uncontrolled power loss are untested. |
| Controller and IPC telemetry | **Implemented** through Tc3_IPCDiag (§161), enabled in the Press real profile; unavailable on a host without the Device Manager (verified on the test host). | Positive values, limits and loss/recovery need the Beckhoff IPC target. |
| Fieldbus counters and DC quality | **Implemented**: always-on master device state, frame and CRC windows, DC bit; `M_BusOk` now uses the live master state (§161). | Real counters need the EtherCAT target. |
| Windows clock (addressed earlier) | PLC file reader accepted live with the native observer; error reporting, accepted-only measurements and PLC/OS clock disagreement (TwinCAT time 475 s behind Windows on the usermode runtime) corrected (§162). | Observer deployment, upstream sync and the TwinCAT-versus-Windows clock comparison on the target. |
| TCP transport, EL6001 linking, PartFeed axis, external adapters | **Out of scope by owner decision (2026-10-06)**: no such device or endpoint is used now. | Unchanged; revisit when one is deployed. |

The table below is the audit as written before that work.

## Findings and next acceptance

| Priority | Finding and exact scope | Source and required next evidence |
|---|---|---|
| P1 | **Protected local-user persistence is defective.** Same-run access control exists, but the compiler warns that hidden `_users` and `_n` will not persist. | `Framework/Fraktal_Core/Connectivity/FB_LocalAccessProvider.TcPOU`, implementation notes §154. Provide protected retention without publishing credential material, then test power cycle, download, recovery and permissions. Removing `hide` merely to silence warnings is insufficient. |
| P1 | **Real controller and IPC telemetry is unwired in Press.** Task measurement works; CPU/memory availability is tied to simulation, and IPC availability is false. | Press `00_System/MAIN.TcPOU`, Core §8.12 / TC3 §8.12. Add supported target-specific metrics providers; demonstrate valid values, unsupported-target behavior and unavailable/recovery events. Clock synchronization alone cannot clear these messages. |
| P1 when TCP devices are deployed | **Native TCP byte transport is a skeleton.** Open/Close/Send fail, Poll returns zero and the channel stays closed. Device protocol/parser CMs and simulated channels already exist. | `Connectivity/FB_TcpChannelTc3.TcPOU`, TC3 §3.15. Implement bounded asynchronous socket operations, framing, reconnect, timeout and errors against the pinned runtime; verify TF6310 prerequisite/license and real disconnect tests. |
| P2 | **Press aggregate fieldbus health lacks full counter/DC wiring.** Actual master/node state exists, but `LostFrameCount` and `SlaveErrorCount` are supplied as zero and real `DcAvailable` is false in the health probe. | Press `MAIN` and `Hardware/FB_PressIoDriver.TcPOU`, Core §10.5 / §8.12. Feed verified master counters/DC status into the aggregate health publisher without duplicating the existing topology algorithms. |
| P2 when serial is used | **EL6001 PDO linking is unfinished.** Raw serial symbols and topology are present; guessed entry names were deliberately removed after native build failures. No demo module currently speaks this serial protocol. | `Hardware/GVL_PressIO.TcGVL`. Read the actual terminal PDO assignment, link exact names and test real bytes/health before claiming usable serial I/O. |
| P2 when the feed axis is used | **PartFeed remains outside the deployed child/config walk.** Axis CM logic exists; the composition root intentionally omits `ConfigurePartFeedAxis` and registration until physical NC commissioning. | Press `MAIN` comments and Unit configuration. Verify the current System Manager NC channel, actual linkage and motion commissioning, then bind/register the axis and verify config restore and jog permissions. Presence of an NC wrapper alone does not establish commissioned motion. |
| Optional extension | **Rich EtherCAT discovery remains a skeleton.** This is not the default fieldbus path. `FB_EcBusHealth`, the project I/O catalog and `FB_IoTopologyPublisher` already implement the default profile. | `Connectivity/FB_EcFieldbusScanner.TcPOU`, TC3 §10.6. Implement only if vendor-specific discovery beyond the catalog is required; verify ADS/CoE indices and bounded on-demand work. |
| Deployment-dependent | **External carrier/historian/MES adapters need project choices.** Local BY_POSITION carrier, traceability events, bounded history and interfaces already exist. | `FB_LocalPartCarrier`, `I_PartCarrier`, `I_EventSink`, Core §3.16 / §11.6. Select real endpoints and prove acknowledgement/failure behavior. Their absence from this bench is not missing generic lifecycle logic. |

Beckhoff explicitly documents that
[hidden variables are not stored as persistent](https://infosys.beckhoff.com/content/1033/tc3_plc_intro/2529654667.html),
matching the native warning. Its
[TF6310 documentation](https://download.beckhoff.com/download/document/automation/twincat3/TF6310_TC3_TCP_IP_EN.pdf)
defines the native TCP/IP service and prerequisites; it is not evidence that the
Fraktal skeleton already performs network I/O. These findings are source-level
inferences supported by the cited vendor behavior.

## Clock gap addressed in this change

The former real Press profile injected `TimeAvailable=FALSE` and
`TimeSynchronized=FALSE`. Core had quality/alarm propagation but lacked this
target adapter. Core 0.23.1.0 adds the target-local Windows Time observer and
validated expiring reader. Press enables it and derives its real task period,
removing the unrelated fixed-period jitter defect. See the
[implementation guide](../Guides/TC3_WINDOWS_CLOCK.md) and dated evidence.

Beckhoff's [OS time reader](https://infosys.beckhoff.com/content/1033/tcplclib_tc2_system/3622991755.html)
reads system time; it does not prove clock discipline. The selected Windows
service exposes structured quality through Microsoft's
[MS-W32T status query](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-w32t/7e80a465-f5f4-4c3c-87ef-12f76e45f8d1).
The current host returns Local CMOS Clock, so upstream synchronization remains a
commissioning gap even with a working observer. PTP/DC alternatives remain
separate target integrations; existing Core §2.7 requirements were not relaxed.

## Recommended order

1. Commission Windows Time and deploy its observer to each Windows PLC target.
2. Correct protected credential retention and add actual controller/IPC telemetry.
3. Complete aggregate fieldbus counter/DC inputs.
4. Implement TCP, serial and feed-axis hardware paths only where the project uses them.
5. Run real power-loss, hardware fault/recovery and safety acceptance separately
   from simulation/TcUnit. Preserve the control-domain and release guards.

No safety acceptance, TF6100 commissioning or physical I/O verification is
inferred from a clean compiler result. Existing reset/hold behavior, recipes,
model configuration and all three sequence renditions are implemented and are
not listed as absent merely because older reports predate them.
