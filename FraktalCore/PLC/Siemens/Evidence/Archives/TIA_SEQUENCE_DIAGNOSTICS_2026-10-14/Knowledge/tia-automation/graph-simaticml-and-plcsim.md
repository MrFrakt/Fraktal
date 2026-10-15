# S7-GRAPH generation (SimaticML) and headless S7-PLCSIM Advanced — verified (2026-10-09)

Measured while proving the Fraktal/TIA S11 GRAPH leg. Station: CPU 1516-3 PN/DP
`6ES7 516-3AP03-0AB0` V3.0 simulated on S7-PLCSIM Advanced 5.0 (runtime 50.42.10.00),
TIA V20 / Openness V20. Evidence and every raw log:
`C:\Projects\Fraktal\Specification\Siemens\Evidence\TIA_S11_GRAPH_PLCSIM_2026-10-09.md`.
Tools (one source, in the Fraktal repo): `FraktalCore\PLC\Siemens\tools\fraktal_tia_graph.py`
(GRAPH writer/reader/parity), `Invoke-PlcSimInstance.ps1` (PLCSIM host/read).

## Getting a GRAPH template at all

| Question | Answer |
|---|---|
| Can Openness create a GRAPH block? | **No.** `PlcBlockComposition.CreateFB` supports only ProDiag ("Create block only supports the programming language 'ProDiag'"). **[measured]** |
| Then how do I generate GRAPH? | Draw one small chart in the editor once and export it (`Blocks.Export`). Use that export as the template for every generated chart, and re-import (`Blocks.Import`, `ImportOptions.Override`). Never write the schema from scratch. **[measured]** |
| Export encoding | UTF-8 with BOM, CRLF. GraphVersion `6.0`, namespace `.../NetworkSource/Graph/v5`. **[measured]** |

## SimaticML forms TIA V20 accepts in a GRAPH FB

| Element | Verified form |
|---|---|
| Action | `<Action [Event="S1"\|"S0"] Qualifier="N">` with one `<Token Text="…"/>` per lexeme (identifier, space, `:=`, literal, `&#xA;` newline as its own token) and a final newline token. `S1` = once on activation, `S0` = once on deactivation, no event = every active scan. **[measured]** |
| CALL in an action | `CALL "FC" ⏎ (P1 := v ⏎ P2 := v ⏎ )`, one parameter per line and **no commas**. With commas it is refused: "invalid characters". **[measured]** |
| What an action may contain | only `operand := operand` (or a bare Bool operand) and CALL. `IF … THEN … END_IF` → **"Tag IF not defined"**; `#a := #b AND NOT #c` → **"The operand is missing or has an incorrect data type"**. Put conditions in the **transition**, or pass them to an FC as an operand. **[measured]** |
| InOut access | InOut struct members and **InOut FB-instance** members (`#CylA.Execute`, `#Seq.Issued`) can be read and written in actions and transitions. **[measured]** |
| Transition | `<Transition IsMissing="false" Name="T1" Number="1" ProgrammingLanguage="FBD">` + `FlgNet`: `Access` operands, `<Part Name="A">` with `TemplateValue Name="Card" Type="Cardinality"` = n (n = 1 accepted), `<Part Name="TrCoil"/>`, wires `IdentCon → NameCon in<i>`, `out → TrCoil in`. **No power rail** needed in FBD. A Bool literal `TRUE` (`Scope="LiteralConstant"`) is a valid operand. LAD transitions need `Powerrail → pre` on a comparison box (`Eq` with `TemplateValue SrcType`). **[measured]** |
| Empty transition | refused at compile ("transition … missing / no conditions"). **[measured]** |
| Step | `<Step Number="n" Init="true\|false" Name="N100" MaximumStepTime="T#10S" WarningTime="T#7S">`. Each step carries **empty** `Supervisions`/`Interlocks` LAD networks (`Powerrail → SvCoil` / `IlCoil`), copied from the template. Actions end with an empty `<Action />`. **[measured]** |
| Connections | `StepRef → TransitionRef` and `TransitionRef → StepRef`; `LinkType` `Direct` to the next drawn step, `Jump` otherwise. `<Branches />` when none. **[measured]** |
| Interface | the GRAPH standard interface (`OFF_SQ`, `INIT_SQ`, `ACK_EF`, `SW_AUTO` …, static `RT_DATA : G7_RTDataPlus_V6`) comes from the template. Add `<Section Name="InOut">` members such as `<Member Name="Seq" Datatype="&quot;FRK_SeqCtx&quot;" Accessibility="Public" />`. **[measured]** |
| Round trip | import → compile → export of a generated chart gives the same steps, actions, edges and transition operands (canonical dump identical). **[measured]** |

## GRAPH runtime semantics (S7-1500 V3.0 on PLCSIM)

- **One call switches step and runs the new step's actions**: the transition fires,
  the old step's `S0` and the new step's `S1` + `N` actions run in the same FB call. A
  child reported `Done` earlier in the same scan (called before the chart) fires the
  transition on that scan. **[measured]**
- Consequence: dropping a command on exit (`S0`) and raising it on entry in the same
  call means the commanded FB never sees the drop. Raise on the **second** active scan
  (`S1 latch := FALSE`, `N Execute := latch`, `N latch := TRUE`). **[measured]**
- **`INIT_SQ = TRUE`** for one call: the active step's `S0` actions run (the commands are
  dropped), the chart returns to the initial step, and that step's actions run in
  the same call. The first call with `INIT_SQ` starts the chart at its initial step. **[measured]**
- **A GRAPH FB cannot be a multi-instance**: "The data type '"FB_…"' is not supported as
  a multiple instance". This holds with or without GRAPH alarm handling
  (`WithAlarmHandling`). It **can** be a parameter instance:
  `VAR_IN_OUT Chart : "FB_…"; … #Chart(INIT_SQ := …, …)`, given a single-instance DB
  (`DATA_BLOCK "X" "FB_…"`). **[measured]**
- Download asks `TurnOffSequence` ("Turn off the sequence (FB …, DB …) before
  loading?"), with default `True`. **[measured]**
- Continuation evidence: `TIA_S11_SEMANTICS_2026-10-09.md` in the same Fraktal
  evidence directory. On PLCSIM 1516 V3.0, an empty-network step ran **499–500 ms**
  with T_MAX 100 ms / T_WARN 50 ms and no ERR_FLT. Time attributes alone are inert;
  step-time monitoring needs a supervision condition. **[measured]**
- A generated FBD supervision (`Probe.Fault` → AND → SvCoil) compiles 0/0 and
  round-trips with identical topology. With AcknowledgeErrorsRequired TRUE, clearing
  the condition and making the transition valid leaves the step blocked until a
  one-call ACK_EF pulse; FALSE advances without the pulse. **[measured]**
- SkipSteps TRUE recorded N000,N300 when N100,N200 had TRUE exits; FALSE recorded
  all four. Fraktal therefore keeps V/C networks empty and skip disabled: Core
  owns pending/fault diagnostics, and every visited step must be recorded.
  **[measured]** Policy is in Fraktal Part IV §3.5, not a Siemens requirement.
- Direct API Stop→Run, no download, rebuilt the NON_RETAIN probe observations,
  changed the OB100 timestamp and passed 28/28 again. Manual/semi-automatic GRAPH
  interface modes, retentive classes and GRAPH download-in-RUN remain unmeasured.
  Physical 1214C SCL-only code deltas in RUN were subsequently measured in
  `TIA_S11_NATIVE_2026-10-09.md`; this does not prove the GRAPH path. **[measured]**
  **[measured]**

## S7-PLCSIM Advanced 5.0, headless

| Question | Answer |
|---|---|
| API | `C:\Program Files (x86)\Common Files\Siemens\PLCSIMADV\API\5.0\Siemens.Simatic.Simulation.Runtime.Api.x64.dll`, `SimulationRuntimeManager.RegisterInstance(name)` → `IInstance.PowerOn(ms)` / `Run` / `PowerOff` / `UnregisterInstance`. **[measured]** |
| Instance lifetime | Registered from one process and the same API used from another: the instance stays registered. The Runtime Manager and Instance processes keep the virtual CPU. Fraktal's `-Action host` owns it and stops on a stop file. **[measured]** |
| `PowerOn` → `InstanceNotRunning (-14)` | It happens on the first call after the Runtime Manager cold-starts, and succeeds seconds later. Retry with a bound. **[measured]** |
| Download from TIA/Openness | PG/PC interface `PLCSIM`, target address = the project's CPU IP. The project needs **`IsSimulationDuringBlockCompilationEnabled = true`** (project property, settable through Openness), else "cannot be simulated". **[measured]** |
| TLS on a new instance | A newly registered instance presents a new certificate, so the first download fails with "certificate not matching" → "Connect to module failed". Trust it once (`TlsVerificationConfiguration` = `Trusted`). Later downloads from the same project need nothing. **[measured]** |
| S7-1500 V3.0 access level | A new V3.0 CPU defaults to protection NoAccess; set `PlcAccessLevelProvider.PlcProtectionAccessLevel = FullAccess` for a simulator. **[measured]** |
| Reading tags | `UpdateTagList(ETagListDetails.DB, false, "\"DB1\",\"DB2\"")`: **every DB name in double quotes**, comma-separated; bare names → `WrongArgument (-8)`. Then `TagInfos` + `Read(name)` → `SDataValue` (`.Type`, value in the property of that name). `String` leaves → `NotSupported (-19)`. **[measured]** |
| Two `ETagListDetails` types in the DLL | Resolve the one with its namespace: `Siemens.Simatic.Simulation.Runtime.ETagListDetails`. **[measured]** |
| Cycle | about 1.0 ms mean on this workstation, max 2–4 ms, with the S2 test image plus a GRAPH chain. **[measured]** |
| A second program-cycle OB from an SCL source | `ORGANIZATION_BLOCK "Name"` + `TITLE` with no number creates a **program-cycle** OB, auto-numbered 123. Program-cycle OBs run in number order after OB1. **[measured]** |

## Active recovery and GRAPH load boundary (2026-10-10)

Scope: PLCSIM Advanced5.0, CPU1516-3 V3.0, FrkS11 Softbus. Evidence:
`C:\Projects\Fraktal\Specification\Siemens\Evidence\TIA_S11_GRAPH_RECOVERY_2026-10-10.md`.
Sixteen recovery checks passed, one GRAPH preservation gate remains unpassed;
fifteen completed baseline harvests each passed28/28. **[measured]**

- An FC marker delta loaded with SoftwareOnlyChanges during a BUSY cylinder
  command: marker2101→2102, observed step/handshake/trace preserved, Calls advanced,
  no stop/start/turn-off/reinitialization question. Endpoint reads do not prove
  per-scan coil continuity. **[measured]**
- A GRAPH action-label delta with fully unchanged exported DB interfaces still
  requested TurnOffSequence and DataBlockReinitialization and loaded the chart DB.
  Generic driver chose StopPlcAndReinitialize; the BUSY endpoint and two-second
  state monitor cannot establish native preservation. Quiesce the affected owner,
  withdraw outputs and require its reset/fresh Start policy for such loads.
  Production workflow enforcement remains open. **[measured]**
- NON_RETAIN owner Calls/ResetCount reset on STOP→RUN; StartupCalls becomes1 again,
  not2. Observe the actual native state change and startup timestamp, not a supposed
  accumulating nonretentive startup count. The active test owner stayed idle with
  requests/coils off until new Arm, before and after the output-permit fix.
  **[measured]**
- A READY cylinder kept its last valve coil after completion; Abort only invoked
  the spike hook while BUSY/ERROR. Applying the existing interlock to coil outputs
  outside the quiescent guard corrected reset after completion without owner coil
  writes or an interface change. Full Unit runtime integration is still open.
  **[measured]**
- Runtime API WriteBool/WriteInt32/WriteUInt32 work through the simulation helper.
  Validate exact ControllerIP+Softbus and native primitive type first; wrong physical
  IP and UInt32 write to Bool were refused before writes. **[api, measured]**
- PowerShell identifiers are case-insensitive: a new typed `[string] $Tag` parameter
  also typed foreach `$tag`, coercing native STagInfo objects to strings. Reads
  silently emitted nothing. Use a distinct `$leafTag`; reject an empty harvest.
  Read primitive array elements, not unsupported array containers. **[measured]**
- Passing a nested quoted plan replacement through PowerShell5.1 stripped the
  `"1 X1"` target quotes. Python subprocess argument lists preserved them. A relative
  forward-slash executable path failed CreateProcess; use an absolute Windows Path.
  Both failures occurred before any download. **[measured]**

## S11 follow-up: startup, instruction errors and workstation memory

- **Use an absolute source header to select the event class:**
  `ORGANIZATION_BLOCK OB100` produced Number 100 / SecondaryType Startup on 1200
  and 1500; `ORGANIZATION_BLOCK OB121` produced ProgrammingError on 1500. Merely
  renumbering a named program-cycle OB to 100 is refused (1,123–32767 permitted).
  The exports in the S11 follow-up record prove the classes. **[measured]**
- Invalid variable array index 99 into Array[0..1], with GET_ERR_ID in the
  offending FC: 16#2522, substitute zero, following statement runs; on 1500 OB121
  is bypassed. Same local code on the physical 1214C V4.7.3 (19/19 total).
  Without local handling on PLCSIM, OB121 ran once: Fault_ID 16#22, Reaction 1,
  then the FC continued with zero. **[measured]** S7-1200 has no OB121 fallback.
  **[help]** Presence of GET_ERROR/GET_ERR_ID activates local handling: consume
  the result or the error is silently swallowed. **[help, measured]**
- `Invoke-PlcSimInstance.ps1`: `halt` = Stop without unregistering; `run` = Run;
  `off` = PowerOff, registration/image kept; `stop` = PowerOff+Unregister.
  Mode/power-off actions require ConfirmTarget matching a ControllerIP and
  CommunicationInterface Softbus. **[api, measured]** A new registration means a
  new certificate; the existing FrkS11 host expired/unregistered after 120 minutes
  in this run. **[measured]**
- Workstation has ~4 GB RAM + 12 GB page file. TIA + the virtual CPU + the help
  service exhausted Windows commit and killed an import/GoOnline. Power off the
  owned virtual CPU during offline builds; stop only confirmed orphan helpers
  belonging to failed owned TIA sessions. A successful download followed by a
  TIA crash is a failed *plan*, even when independent runtime harvest is green.
  **[measured]**
