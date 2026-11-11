# Native force-status acceptance on an isolated TwinCAT runtime

This checks the installed Core probe through the Unit's normal system-health
path. It exercises native XAE/System Manager forces, separately from Fraktal's
application output-forcing service. Use only an explicitly authorized isolated
runtime, with the test PLC's boot autostart disabled and no physical I/O devices.
Follow [the XAE workflow](TWINCAT_XAE_WORKFLOW.md) for target and compile gates.

`PRG_PlatformAcceptance` in the aggregate test application provides:

- `ForceWitness`: an unmapped Boolean assigned FALSE each scan, with no control
  consumer. Native PLC forcing can hold it TRUE without actuating anything.
- `MaintenanceProbe` and `MaintenanceUnit`: continuous sampling and the existing
  `SetSystemHealth`/Unit publisher path. Synthetic health inputs belong only to
  this acceptance fixture. The fixture preserves the other suites' time quality.

1. Compile and activate the aggregate test application on the chosen isolated
   target, run the exact-inventory TcUnit gate, and validate its raw summary.
   Confirm the loaded PLC ProjectName and ADS port. Check XAE's actual
   `GetTargetNetId()`; the toolbar's `<Local>` label alone is insufficient.
2. Open that same disposable checkout in XAE, log into the test application and
   start it. With no forces, both `_AppInfo.ActivePlcForces` and `ActiveIoForces`
   must be FALSE, `MaintenanceProbe.Health.MaintenanceAvailable` TRUE,
   `MaintenanceDemanded` FALSE, and no reason-22 event active.
3. In the online declaration of `PRG_PlatformAcceptance`, prepare
   `ForceWitness := TRUE` and execute **Force Values**. Read the native flags,
   witness, probe sample, `MaintenanceUnit.SystemHealth.Healthy` and
   `MaintenanceUnit.AlarmLog` over ADS. Expect PLC force TRUE, I/O force FALSE,
   witness/demand TRUE, Healthy TRUE and exactly one active reason 22:
   LOW/SYSTEM/AUTO_RESET, key `std.system.controllerMaintenanceDemanded`,
   source `ForceAcceptance.SystemHealth`. After several scans, a second snapshot
   must show the same single event and no new history entry.
4. Execute **Unforce Values**. The witness's ordinary FALSE assignment resumes;
   both flags and demand become FALSE. The event closes automatically and its
   reason, source and nonzero duration appear in the closed-event ring.
5. To check System Manager forcing without hardware, add a temporary **task with
   image** to the disposable XAE configuration, with one unlinked BOOL input
   `ForceIoWitness`. The measured fixture is `ForceAcceptanceTask`. Do not add a
   device or link this variable to a PLC command or I/O. Beckhoff documents
   [task/image creation](https://infosys.beckhoff.com/content/1033/tc3_automationinterface/242740107.html):
   `TIRT.CreateChild(name, 0, null, null)` creates the task; its `Inputs` node's
   `CreateChild(name, -1, null, 'BOOL')` appends the input. Compile and activate
   that configuration through the same isolated-runtime gate, then start its PLC.
6. In the task's Inputs list, select **Online Force...** for `ForceIoWitness` and
   set 1. Expect I/O force TRUE, PLC force FALSE, demand TRUE and the same single
   LOW reason-22 event. Capture a second held snapshot to prove deduplication.
7. Select **Release Force**. Verify both native flags clear, demand clears and
   the event closes with its duration. An unlinked image input may retain 1
   after release; use **Online Write '0'** to restore its original value.
8. Remove only the temporary task, compile/activate the original test
   configuration again, and stop the test application. Verify both force flags
   clear, no reason-22 event active, boot autostart off, one original PLC task
   and no I/O devices. Preserve raw ADS snapshots, configuration snapshots,
   runtime/TMC/source identities and exact-inventory JUnit validation.

The native fields require TwinCAT 3.1.4026.21+ declarations; older declarations
are explicitly unavailable in the probe. See Beckhoff's
[PlcAppSystemInfo](https://infosys.beckhoff.com/content/1033/tc3_plc_intro/714818699.html),
[PLC forcing](https://infosys.beckhoff.com/content/1033/tc3_plc_intro/2527602315.html)
and [System Manager forcing](https://infosys.beckhoff.com/content/1033/tc3_system/20792640011.html).
Do not force the status flags themselves: that would test an injected sample,
not the controller's native force detection.

Measured acceptance:
[2026-11-11 live-force record](../Evidence/2026-11-11_TC3_LiveForceAcceptance.md).
