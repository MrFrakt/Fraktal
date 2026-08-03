# Fraktal First Project and Deployment Guide for AI Agents

This document instructs an AI coding agent how to guide a programmer from an
empty TwinCAT solution to a deployed, HMI-commandable Fraktal station. It is a
workflow and evidence checklist, not a replacement for the normative standard.
Part I and the selected platform binding remain authoritative.

## 1. Agent operating rules

When the request concerns a first project, initial deployment, commissioning,
or OPC UA bring-up, the agent shall:

1. Read `AGENTS.md`, `Fraktal_Core_Part_I.md`, the applicable binding
   (`Fraktal_TC3_Part_II.md` for TwinCAT), `HMI_CONTRACT.md`, this guide, and
   `FraktalCore/PLC/TwinCAT/IMPLEMENTATION_NOTES.md` before changing code.
2. State the current phase and the evidence required to leave it. Do not mix a
   PLC compile failure, runtime deployment failure, OPC UA authorization issue,
   and HMI contract failure into one diagnosis.
3. Reuse the Core lifecycle, module libraries, providers, topology publisher,
   HMI mailbox, and generic HMI. Never create station-specific HMI screens or a
   parallel command protocol.
4. Build basic reusable mechanisms first, then compose project-specific
   behavior. Hardware addresses, electrical tags, recipes, safety mappings, and
   station composition belong to the application, not reusable module types.
5. Never infer functional-safety behavior from ordinary I/O or simulate a
   certified result in a physical deployment. Record missing safe devices,
   evaluated aliases, reset rules, and output authority as blockers.
6. Preserve user changes and record every spec/implementation reconciliation in
   `IMPLEMENTATION_NOTES.md`.
7. Report concrete evidence: compiler version, build output, target identity,
   ADS port, namespace URI, browse paths, mailbox write result, acknowledgement,
   and PLC diagnostic key. “Ping works” is never connection acceptance.

## 2. Inputs to collect before implementation

The agent shall identify or explicitly mark unknown:

- pinned TwinCAT XAE and XAR builds, controller model, operating system, PLC
  runtime name and ADS port;
- approved I/O list, terminal order, process-image addresses, electrical tags,
  safe versus ordinary signals, and fieldbus failure policy;
- the Unit forest, Unit/EM/CM decomposition, shared control domains, recipes,
  modes, commands, manual functions, and release conditions;
- safety concept: E-stops, guards, light curtains, two-hand control, safe valve
  or drive outputs, reset/bridging/muting behavior, and validated safe aliases;
- network addresses and conduits, TF6100 version, endpoint/security policy,
  HMI platforms, station languages, and which root Units each HMI owns;
- project target security level, user roles, credential/certificate owner, and
  whether the current activity is commissioning or production.

Unknown mechanical or naming details may be isolated behind configuration.
Unknown safety authority or ambiguous output polarity shall remain fail-closed.

## 3. Phase A — model and type design

1. Draw the forest. Each station is one root `FB_Unit`; peer stations remain
   peer roots. An EM never contains a Unit. A shared cage or power arrangement
   is a control domain associated with multiple roots, not a super-root.
2. Put each hardware-bound leaf in a CM with one semantic HAL channel. Put a
   bounded function assembled from CMs in an EM. Put continuous modes and cycle
   ownership in a Unit.
3. Search `Fraktal_Modules` before creating a type. Prefer configuration or a
   small extension over a project-specific duplicate.
4. For a new reusable CM, copy `PLC/TwinCAT/scaffold/FB_TemplateCM`, reserve and record
   its reason band, define its enum/HAL/config contract, and implement only the
   device `CASE` in `_M_Dispatch` plus required hooks.
5. Keep `SchemaVersion : UINT` first in every configuration/recipe record.
   Adding or reordering fields changes the schema and requires migration or a
   deliberate `RECIPE_INVALID` fault.
6. Use localization keys for every operator-facing string. Preserve electrical
   tags, addresses, identifiers, model codes, and browse paths verbatim.

**Exit evidence:** reviewed tree, reason-band allocation, explicit HAL boundary,
recipe schema, command list, and no duplicate lifecycle or station HMI code.

## 4. Phase B — application composition and I/O

Create an executable application project; do not place `MAIN` or a task inside
`Fraktal_Core` or `Fraktal_Modules`.

Recommended application ownership:

- `GVL_<Project>IO`: raw `%I/%Q/%M` mapped symbols only;
- `<Project>IoCatalog`: static tag/address/description/module-role engineering
  data;
- `<Project>IoDriver`: the only POU that reads/writes the raw I/O GVL and maps
  it to semantic HALs;
- `FB_IoTopologyPublisher`: reusable bounds, duplicate, health, and diagnostic
  join behavior;
- simulation driver/plant: virtual commissioning only;
- control-domain coordinator and final output authority: project
  infrastructure, separate from the three module tiers;
- `MAIN`: setup, root declarations, real/simulation selection, and explicit
  scan order—not individual channel assignments.

Every deployed root declaration shall carry the binding’s explicit publication
marker. For TwinCAT TMC-Filtered publication:

```iecst
PROGRAM MAIN
VAR
    {attribute 'OPC.UA.DA' := '1'}
    Station1 : FB_StationUnit;
END_VAR
```

The instance name, `Setup`/`FB_init` name, schematic name, and OPC UA browse
name shall agree.

Do not add the enable marker to an FB type definition. A separately published
GVL value uses the same immediate-variable form:

```iecst
{attribute 'qualified_only'}
VAR_GLOBAL
    {attribute 'OPC.UA.DA' := '1'}
    Topology : ST_FieldbusTopology;
END_VAR
```

Before building, run `powershell -File "FraktalCore/PLC/TwinCAT/Tests/tools/Test-OpcUaPublication.ps1"`.
It rejects definition-level enable markers, misplaced GVL markers, and
persistent pointer/interface/reference fields without an immediate `DA=0`.

**Exit evidence:** application/library separation, one source for each I/O tag,
validated topology mapping, explicit root markers, and documented scan order.

## 5. Phase C — simulation and automated acceptance

1. Supply a simulation HAL/plant for each reusable type.
2. Run the inherited base suite and each type’s T2/T3/T5 rows. Composites and
   Units also prove their tier rows, rollup, mode support, recipe transaction,
   stop, and no-self-resume behavior.
3. Exercise HOME, AUTO, CHANGEOVER, MANUAL releases, each recipe, every first-out
   timeout, fieldbus loss, control-domain loss, and recovery without automatic
   restart.
4. Confirm the final output authority withdraws outputs after logic evaluation;
   ordinary application code never grants a certified safe output.

**Exit evidence:** clean test report, virtual-commissioning scenario record,
and all safety-dependent physical tests still marked separately for SAT.

## 6. Phase D — TwinCAT build and target deployment

1. Pin and record XAE/XAR. A `.plcproj` is added to a TwinCAT XAE solution with
   **PLC → Add Existing Item**; it is not opened as a solution.
2. Build and install `Fraktal_Core` as a library, then build and install
   `Fraktal_Modules`. Build the application and both applicable test gates
   afterwards: `Tests/Fraktal_Tests.plcproj` for Core/Modules and
   `Examples/PressDemo/PressTests.plcproj` for the internal Press feature-testing
   bench. This bench is framework integration evidence, not a real project or
   machine-acceptance target.
   Use a separate application solution, or unload/remove the Core and Modules
   source-library projects before adding applications that consume the installed
   libraries; otherwise XAE can see identical object GUIDs in source and installed
   copies. Native SFC POUs need no SFC/`IecSfc` library reference (the compiler
   provides SFC support). After changing a `.plcproj` library reference,
   close and reopen XAE before evaluating the next build.
   Run either test gate only on an isolated test runtime/ADS port with Autostart
   Boot Project disabled; neither is ever the machine boot application. Never
   load `PressTests` beside the deployed Press project because it links the same
   source objects. Before accepting the result, verify both the runner and count:
   Core/Modules is `PRG_TcUnitRunner` with 84 tests/26 suites; Press is
   `PRG_PressTestRunner` with 8 tests/2 suites. A Core identity after attempting
   Press means the wrong solution was downloaded or stale Core boot data restarted
   on the target. Disabling source autostart does not delete previously created
   target boot data.
3. Resolve the project to the intended target, add/scan the EtherCAT hardware,
   compare it to the approved I/O list, link process-image symbols, and verify
   terminal identity/order before enabling physical output authority.
4. Enable creation and download of the PLC symbol file/TMC. Activate the
   configuration, download the application, create boot data when required,
   start the correct PLC runtime, and verify the task is cycling.
5. Confirm the deployed runtime name and ADS port. TF6100 will import the
   matching `Port_<ADS port>.tmc` only after its server reload/restart.

**Exit evidence:** warning-clean application build, target/runtime identity,
EtherCAT OP/mapping validation, running task, boot-project decision, and the
deployed TMC corresponding to the active application.

### 6.9 Commissioning gates — check these BEFORE debugging "nothing moves"

On first power-up of real hardware, two `VAR CONSTANT` gates in the application's `MAIN` deliberately
hold physical outputs off. They are **not** bugs, and chasing control logic past them wastes days:

| Gate (`VAR CONSTANT` in `MAIN`) | When wrong | Symptom |
| --- | --- | --- |
| `CONTROL_CIRCUIT_MAPPING_CONFIRMED` | `FALSE` | The I/O driver forces the control-circuit coils (`SwitchControlOn` / `EnableControlOn`) FALSE every cycle. The relay chain never closes, the valve-enable relays never energize, and **no output moves at all** — even though the actuator coils are written unconditionally. |
| `USE_SIMULATION` | `TRUE` | `MAIN` calls `M_ClearOutputs()` every cycle: outputs stay dark while the simulation driver animates the plant, so the HMI shows motion the machine never performs. |

**The decisive test:** force the output in TwinCAT XAE. If forcing works but the PLC never drives it, it
is one of these gates — the terminal, wiring and process image are already proven good.

They are constant so they **cannot be flipped online**; changing one is a source edit plus a download.
`MAIN` publishes inert read-only mirrors (`UseSimulation`, `ControlCircuitMappingConfirmed`) purely so
the state stays visible over ADS. Read them live with:

```bash
cd FraktalCore/HMI/gateway && dart run tool/probe_sim_flag.dart <amsNetId> [port]
```

`CONTROL_CIRCUIT_MAPPING_CONFIRMED` is a **safety interlock**: it holds the control coils off until the
control-circuit electrical semantics are verified on the real cabinet. **An agent must never set it —**
report it and stop; that verification belongs to the commissioning engineer.

Once the gate is open, the remaining "outputs still dead" causes are ordinary permits, in this order:
control-power `SafetyPermit` / `FieldbusHealthy` (a withheld-power fault latches `RearmRequired`, so an
operator reset is needed after fixing the cause), then sensor **polarity** — an E-stop or pressure input
read with the wrong sense makes a healthy machine report unsafe and silently withholds control power.

## 7. Phase E — TF6100 and OPC UA commissioning

TF6100 is installed and configured on the computer that owns the PLC runtime
(the CX/IPC in a remote-runtime deployment). The Flutter HMI is an OPC UA
client; it does not need another TF6100 server.

### 7.0 One-time server initialization (Trust-On-First-Use) — TF6100 ≥ 5.x

TF6100 setup ≥ 4.4.0 (the 5.x server shipped with TwinCAT 4026) requires a
one-time **TOFU** initialization before it publishes **any** Data Access
namespace. This is the single most-missed step and it mimics every other
failure:

- **Symptom:** the HMI connects, activates a session, but reports *"no Fraktal
  root Unit discovered / 0 value nodes"*; an `Objects` browse shows only
  `Server` and `Initialization`; `NamespaceArray` lists
  `…/TF6100/Server/Initialization` and **not** the PLC URI. This is **not** a
  symbol/TMC/ADS-port/license fault — the server is simply **uninitialized** and
  the `Initialization` namespace is literally its pre-init state.
- **Initialize via the OPC UA Configurator over a *secured* endpoint.** Configure
  the server connection with `SecurityPolicyUri = Basic256Sha256`,
  `SecurityMode = SignAndEncrypt`, `IdentityTokenType = UserName`, and an admin
  identity, then Connect and complete the TrustOnFirstUse. A username/password
  token can only be carried on an **encrypted** channel — a `None`/`SignAndEncrypt`
  mismatch or a `None` endpoint yields `BadIdentityTokenRejected` /
  `No matching UserTokenPolicy`, so the admin login **must** use the secured
  endpoint even when a later commissioning exception uses `None`.
- **On a TwinCAT usermode/standalone runtime (UM-RT):** the server runs with
  restricted rights and **cannot create the OS user** during TOFU —
  `Tofu_AddStatus: Access has been denied while trying to add the user to the
  operating system` (`NetUserAdd`). Pre-create the account in Windows first
  (elevated: `net user <user> <password> /add`), then initialize; the server
  registers the *existing* user as administrator in `TcUaSecurityConfig.xml`.
  On the full XAR runtime the server has the rights and this workaround is
  unnecessary.
- **Initialization disables the Anonymous identity token.** Re-add/enable it in
  **Security → Users/Groups** only when an explicit `secure-anonymous`,
  `commissioning-anonymous`, or physically isolated Anonymous exception is
  required; activate the revised configuration afterward.

**Exit evidence for 7.0:** `TcUaSecurityConfig.xml` exists with the admin user
and a secured Configurator session connects. If an Anonymous exception was
selected, an anonymous browse of `Objects` also returns the Data Access device
(not just `Server`/`Initialization`).

1. Install/license TF6100 on the PLC target and configure a Data Access device
   for the intended runtime/ADS port. TF6100 5.x needs a valid license (a 7-day
   trial generated in XAE is enough); an unlicensed server logs
   `No license, running in DEMO mode` and will not publish. If the server cannot
   resolve the `[BootDir]` placeholder in `AutoCfgSymFile` (seen on UM-RT:
   `TcReg_GetBootDir failed`), set that field to the **absolute** boot symbol
   path, e.g. `…\Runtimes\<runtime>\3.1\Boot\Plc\Port_<ADS port>.tmc`.
2. Use TMC-Filtered publication and reload TF6100 after downloading a changed
   PLC/TMC. Mark implementation-only pointer/interface/reference storage with
   `{attribute 'OPC.UA.DA' := '0'}`; it is never part of the HMI contract. The
   generated TMC shall carry `DA=1` on every deployed root and standalone
   topology variable, and shall not expose `_unit`, `_hal`, `_children`,
   provider, carrier, or recipe aliases.
3. Configure the endpoint and certificate trust. Record the gateway profile:
   `production` (default, trusted certificate + SignAndEncrypt + dedicated
   user), `secure-anonymous` (encrypted transitional commissioning),
   `commissioning-anonymous` (None/Anonymous with bounded auto-expiry), or
   `isolated-anonymous` (documented physically isolated exception). A failed
   secure profile shall never downgrade automatically.
4. Only for an explicit Anonymous profile, edit the existing Anonymous user and
   assign it to the built-in **Users** group. In the Users group, grant the
   exact PLC namespace Browse, ReadAttribute, and ReadValue. Grant node Write
   only to each root Unit’s `HmiRequest` subtree. Write the configuration to the
   remote target and restart TF6100. Remove these temporary rights after
   commissioning on a network-connected target.
5. Do not grant only the Unit leaf while hiding its ancestors. `Objects`, the
   Data Access device, `PLC1`, and `MAIN` must remain browsable for discovery.

The namespace URI is read from `Server/NamespaceArray`; do not hard-code an
assumed namespace index. A typical TwinCAT runtime reports
`urn:BeckhoffAutomation:Ua:PLC1`.

**Exit evidence:** secure endpoint decision, active user/group mapping,
namespace/node rights, server restart, and an authorized browse showing
`PLC1/MAIN/<Root>/Status` plus the root `HmiRequest`/`HmiResponse` mailboxes.

## 8. Phase F — HMI first-run configuration

1. Install the gateway and its matched Web HMI build by following
   `WEB_HMI_GATEWAY_DEPLOYMENT.md`: use `FraktalSetup.exe` (select **Gateway +
   Web HMI** in the wizard) for a Windows tray/kiosk deployment or the supplied
   systemd unit for Linux. The gateway
   serves the compiled Web HMI and `/fraktal` from one loopback listener, so a
   separate static web server is not required. Record the installed package
   hash, gateway profile, Web origin, OPC UA application identity, and assigned
   `--write-root` paths.
2. Prove the layers independently: `/livez` reports a running process,
   `/readyz` reports a recent good PLC operation, `/` loads the compiled Web
   HMI, and `/fraktal` completes the WebSocket handshake and Fraktal discovery.
   For a local browser, open `http://127.0.0.1:8080/`. A release Web HMI derives
   the same-origin `ws://.../fraktal` or `wss://.../fraktal` endpoint
   automatically. For remote Windows-hosted browsers, select the installer's
   **secure remote Web HMI** option, set the exact HTTPS origin, and trust the
   exported `FraktalGatewayRootCA.crt` on every authorized client. This deploys
   the bundled authenticated same-host HTTPS/WSS proxy while the gateway remains
   loopback-only. Linux/site-SSO deployments provide the equivalent proxy;
   never expose the gateway directly on a LAN interface.
3. For production native Windows/Linux/Android clients, use the configured
   `wss://<gateway>/fraktal` endpoint. The same gateway protocol is implemented
   by native and browser clients. A direct Windows
   `opc.tcp://<PLC host>:4840` endpoint is an explicitly logged Anonymous/None
   path for commissioning, troubleshooting, or a physically isolated PLC only.
4. Select available languages. The detected locale is enabled by default;
   standard and project catalogs remain separate and are importable/exportable
   by an authorized administrator.
5. After discovery, select the root Units this HMI may display and command.
   Persist this scope only after the repository reaches `LIVE`; an
   authenticated administrator may edit it later.
6. Validate a read and an acknowledged write: inspect live mode, request a
   supported mode, observe `HmiResponse.AckSequence`, `Accepted`, and
   `Diagnostic`, and confirm `ModeActivePublished` changes.
7. Test link loss. The operator shell shall disappear immediately, no command
   is queued across reconnect, and connection editing appears only after 30 s.

**Exit evidence:** installed gateway + Web HMI package/hash, liveness, PLC
readiness, static page and WebSocket results, selected-language and Unit-scope
record, `LIVE` connection, successful mailbox round trip, mode/status update,
and fail-closed link-loss behavior.

## 9. Layered OPC UA troubleshooting

Diagnose in this order and stop at the first failed layer:

| Layer | Evidence | Failure meaning / action |
|---|---|---|
| IP | Correct route and target identity; ping if allowed | Ping proves only IP reachability. Correct cabling, route, VLAN, firewall, or wrong target. |
| TCP | Port 4840 accepts a socket | Install/start TF6100 or correct endpoint/firewall. |
| Channel | SecureChannel opens | Resolve policy/certificate/ApplicationURI mismatch. |
| Session | Session reaches Activated | Resolve IdentityToken, username/password, or trust rejection. |
| Namespace | `NamespaceArray` contains the PLC Data Access URI | If absent, the Data Access device/TMC was not loaded for that runtime. |
| Browse | `Objects` exposes the Data Access device/PLC tree | PLC URI present but only `Server` visible means the identity lacks active group/namespace browse rights. Write configuration to the remote target and restart TF6100. |
| Fraktal root | `<Root>/Status` is browsable | Check explicit root DA marker, TMC download/reload, structured publication, and correct deployed application. |
| Mailbox paths | `HmiRequest` leaves are writable and `HmiResponse` readable | Correct TF6100 node rights and verify the breadth-limited client did not report a truncated contract. |
| Commit | Writing arguments then `Sequence` changes `AckSequence` | Verify the root Unit is called cyclically, request enum ordinals match, and the active PLC application contains the mailbox handler. |
| Acceptance | `Accepted=TRUE`; otherwise read `Diagnostic` | This is a PLC release/mode/access rejection, not a transport failure. Diagnose the published key/report. |
| Live state | Published mode/status changes | Verify requested mode is supported and the HMI is watching the owning root Unit. |

Before those runtime layers, a TwinCAT compile that reports every reusable type
(`FB_CylinderCM`, `FB_TwoHandStartCM`, `ST_CylinderHal`, and similar) as
unknown has not resolved `Fraktal_Modules`. Do not repair the resulting hundreds
of member/call/type-conversion messages individually. Build and install the exact
pinned Core library first, resolve that version in Modules, build and install the
exact pinned Modules library, reload the application placeholders, and rebuild.
Messages claiming that a named type cannot convert to the identically named type
are also typical stale/duplicate library-resolution fallout.

If a native chart reports unknown `SFCStepType`, the fault is that POU's SFC
`ObjectProperties`/`XmlArchive` implementation block, not a missing library —
native SFC needs no `IecSfc` reference. The compiler synthesises one implicit
`SFCStepType` record per graphical step, so the resulting `.x`, `._x`, `.t`,
`._t`, transition-BOOL, and assignment errors are one cascade from the malformed
chart; regenerate the chart (do not repair each action or add a placeholder).

A project Unit such as `FB_PressDemoUnit` is different: it shall resolve from the owning application
branch, not from `Fraktal_Modules`. If only the project Unit, its SFCs, or its Release component is
unknown, verify the application's local `<Compile Include>` entries before changing library references.

Additional interpretations:

- A server hostname returned by `FindServers` is not itself a failure when the
  redirected connection reaches `SessionState: Activated`.
- “Security policy not available” lines for rejected alternatives are not the
  failure when a permitted endpoint is subsequently selected and activated.
- `Unsupported datatype ... UXINT` means TF6100 skipped a pointer-like TMC leaf.
  If the path belongs to the application (for example a local recipe provider),
  exclude that internal field from DA publication and reload the TMC. The
  Beckhoff-owned `TwinCAT_SystemInfoVarList._AppInfo.TComSrvPtr` leaf is not a
  Fraktal node and may be skipped; it does not explain a PLC compile failure or
  an otherwise missing Unit tree.
- A first authorized browse may be larger than the unauthorized browse. The
  native repository caches breadth-first discovery once per session and batch
  reads values afterwards. It prunes unused fieldbus `Nodes[]` and `Channels[]`
  from their published counts. A `truncated=true` snapshot is a
  publication-scope or client-limit defect: the HMI rejects it, the gateway
  keeps `/readyz` degraded, and the operator shell stays unavailable. Do not
  hide it by increasing limits indefinitely.
- If the module tree is live but a control appears unresponsive, inspect
  `opcua-request-start`, write/commit failure, acknowledgement, timeout, and
  `HmiResponse.Diagnostic` logs. Do not return to ping/TMC troubleshooting after
  the tree is already live.
- TF6100 configuration and security files belong to the remote server host.
  Their absence on the HMI/development PC is expected.
- If one station appears more than once, compare each candidate's local browse
  name to the final segment of its qualified `Status.Name`. The canonical
  deployed root is the shallow direct
  `PLC1/MAIN/<Root>` instance. Paths through `UnitRef`, recipe catalogs, I/O
  drivers, or coordinators are reference aliases, not additional stations. Fix
  publication ownership where practical and confirm the HMI reports the aliases
  as discarded rather than passing duplicate identities to its selectors.

## 10. Production release gate

Before FAT/SAT completion, the agent shall require evidence that:

- Anonymous write and `SecurityPolicy=None` are disabled on every
  network-connected production path; any permanent `isolated-anonymous`
  exception identifies its owner and proves the PLC/HMI cell is physically
  isolated and unrouted;
- the HMI uses the secured `wss` gateway path on supported production
  platforms, with a provisioned OPC UA gateway identity and authenticated TLS
  reverse-proxy boundary;
- the gateway and Web HMI are a matched, signed release; the installed hash,
  `/livez`, `/readyz`, static `/`, WebSocket/discovery, and fail-closed
  reconnect evidence are recorded separately;
- namespace browse/read and mailbox write permissions follow least privilege;
- PLC access policy, safety aliases, control-domain membership, fieldbus loss
  response, recipes, localization, documentation access, backups, boot project,
  and recovery procedure have been reviewed;
- the final running versions of PLC, libraries, HMI, TF6100, safety project,
  I/O list, TMC, and configuration exports are recorded under change control.

An AI agent shall not call an anonymously writable commissioning setup
production-ready. The isolated legacy exception is a documented deployment
constraint, not an equivalent security posture.

## 11. Appendix — initial bring-up quick paths

Condensed, ordered checklists for the two most common starting points. Follow the
normative phases above for anything not covered here.

### 11.1 Local development PC (PLC runtime + TF6100 + HMI on one Windows PC)

Fastest loop for HMI/PLC development against the shipped press demo.

1. **Windows Developer Mode ON** — required so `flutter run -d windows` can create
   plugin symlinks (`start ms-settings:developers`). Without it the build fails
   with *"Building with plugins requires symlink support."*
2. **PLC:** add the application `.plcproj` to a TwinCAT XAE solution (§6), build,
   enable **TMC File** in the PLC project *Settings* tab, **Activate Configuration**
   with Autostart Boot Project, and confirm the runtime is in **Run**. Note the
   ADS port — the first PLC runtime is **851**, the Nth is **850 + N** (the shipped
   press demo lands on **854** when it is the 4th project in the solution). The
   TMC-File step is what generates `…\Boot\Plc\Port_<ADS port>.tmc`; without it
   TF6100 has no symbol file to publish.
3. **License:** in XAE `SYSTEM → License`, generate the **TF6100 7-Day Trial**
   (plus base TC1200/TC1100/TC1000 trials if the system is fresh) and restart.
   Unlicensed → `No license, running in DEMO mode` and no published data.
4. **Install TF6100** (close VS/XAE first; elevated):
   `& 'C:\ProgramData\Beckhoff\TcPkg\TcPkg.exe' install TF6100.OpcUaServer.XAR -y`.
   The package refuses while VS/XAE is running (exit 1051).
5. **Point Data Access at the running PLC** (Configurator → Data Access → Add
   Device Type → the PLC's ADS port). On the usermode runtime, if the server logs
   `TcReg_GetBootDir failed`/unresolved `[BootDir]`, set the device's symbol-file
   path to the **absolute** `…\Runtimes\<runtime>\3.1\Boot\Plc\Port_<ADS port>.tmc`.
6. **Initialize + optionally re-enable Anonymous** (§7.0): pre-create the OS admin user
   (`net user <user> <pw> /add`), connect the Configurator over the **secured**
   endpoint (Basic256Sha256 / SignAndEncrypt / UserName) and complete
   TrustOnFirstUse. For the local development exception, add an **Anonymous**
   user (assign to **Users**), grant PLC namespace Browse/Read (+ `HmiRequest`
   Write), and **Activate**.
7. **Install the gateway + Web HMI:** build `FraktalSetup.exe` as shown in
   `WEB_HMI_GATEWAY_DEPLOYMENT.md`, install it for the kiosk/development user
   (select **Gateway + Web HMI** in the wizard), and set
   `commissioning-anonymous`, `--commissioning-ttl-minutes 120`, and
   `--write-root PLC1/MAIN/PneumaticPress` in `gateway.args`. Restart from the
   tray, require **Ready**, then open `http://127.0.0.1:8080/`; the packaged Web
   HMI derives `ws://127.0.0.1:8080/fraktal` automatically. A source
   `run_gateway.ps1` + `flutter run -d chrome` pair remains a development-only
   alternative. Direct
   `opc.tcp://127.0.0.1:4840` remains available for transport troubleshooting
   but logs its Anonymous/None posture.

Usermode/standalone-runtime specifics:
- The standalone server's config files under
  `C:\ProgramData\Beckhoff\TF6100-OPC-UA\…` are **restored to install defaults on
  reboot**. Make persistent changes through the **Configurator**, not by editing
  those XML files.
- A plain `TcSysSrv` service restart can bring TwinCAT back up in **Config** mode;
  switch it to **Run** (XAE, the systray, or an ADS `WriteControl(AdsState.Reset)`
  to port 10000) so the PLC runtimes and Data Access are actually live.

### 11.2 Brand-new Beckhoff PLC (CX / IPC, remote runtime)

Same phases, with the runtime and TF6100 **on the controller**, engineered from a
development PC.

1. Establish an **ADS route** from the engineering PC to the controller
   (broadcast search or manual AMS NetId) and confirm the target identity — never
   commission by IP/ping alone (§9).
2. Run Phases D–E **for the controller target:** build + install the libraries,
   resolve to the controller, scan and validate the EtherCAT I/O against the
   approved list, link the process image, enable **TMC File**, activate + create
   the boot project, and confirm the task cycles and the ADS port.
3. Install/license **TF6100 on the controller** (the CX runs the server; the HMI
   PC does not need its own TF6100). Apply the real or trial license on the
   controller.
4. **Initialize (§7.0) on the controller.** On the full XAR runtime, TOFU creates
   the OS user directly; on a usermode/standalone image, pre-create the OS user on
   the controller first. Configure Data Access for the controller's ADS port.
5. Configure endpoint/security. Commissioning Anonymous → **Users** with
   least-privilege namespace rights only while an explicit exception profile is
   active (§7 step 4). **Production: trusted gateway certificate,
   SignAndEncrypt, dedicated user; disable Anonymous/None on network-connected
   targets** (§10).
6. Build the matched gateway + Web HMI package and deploy it with the Windows
   tray installer or Linux systemd unit in
   `WEB_HMI_GATEWAY_DEPLOYMENT.md`. Prove `/livez`, `/readyz`, static `/`, the
   `/fraktal` WebSocket, non-empty discovery, and an acknowledged mailbox
   request separately. Open `http://127.0.0.1:8080/` for a same-host browser;
   release Web builds select the same-origin gateway automatically. Native and
   Web remote HMIs use an authenticated TLS reverse proxy and `wss://`. On
   Windows the installer can deploy/supervise that proxy, write the exact
   `--allow-origin`, and add a local-subnet firewall rule; the exported proxy CA
   root still has to be trusted on each client. The gateway itself remains
   loopback-only (browsers cannot open raw OPC UA
   TCP).
