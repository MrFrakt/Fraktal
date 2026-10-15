# Derived states and alarm/event lifecycle bench

Generator0.7 uses the same 24-module, two-root, nested-Unit declaration and private
hashed application provider as Tests/Access. This fixture adds a derived AtHome
state, test-only alarm stimuli and an optional callback that records event payloads.
The production compiler image omits that callback, its test DBs and the provider.

Module `cyclic` logic declares states unconditionally:

```scl
#OutImm.AtHome := "FRK_State"(Idx := 1, Key := 'project.state.atHome',
                            Ok := #Hal.Cell.Clamp.Sample = 0);
```

The generator supplies context arguments and the sweep; a project adds no reset
or per-scan assembly call. Literal indices and keys are bounded and unique per
module type. Only consuming types allocate the Core-sized 12 state slots. A lost
producer becomes stale and FALSE; a value/key/freshness change updates Since.

Units publish the Core-sized 16 active/64 closed ST_AlarmEvent log. AUTO_RESET
closes at gone; MANUAL_RESET remains blocking in WAIT_RESET until operator reset.
Reset can close ACTIVE and WAIT_RESET, withdraws issued commands, and does not
erase a live condition. Fault capture follows FRK_End, preserves first-out/I/O
identity, stops at the nearest Unit and reuses an already captured first-out.
An ancestor checks nested blocking through its registry. HELD produces no fault
alarm. Ring overwrite and active overflow report Truncated.

Optional declaration `"event_sink": "F_ProjectEventSink"` adds a composition
dependency with `Ev : ST_AlarmEvent` input. The callback receives come and exact
closed records. Private SinkEnabled is configured by the composition root. No
binding emits no external dependency; a durable historian adapter is still owed.
Access audits, Part events and unsupported child modes use AUTO_RESET occurrences;
the separate History is diagnostic fault history.

Measured on owner-created Fraktal, simulated CPU1516 V3.0/Advanced7:
96 native state/alarm assertions, 23 nearest-Unit/ancestor-reset assertions,
122 authentication regressions and an authenticated rendered HMI fault/reset pass.
The routing-only candidate passes120 checks. Native export/reimport148 blocks/45
interfaces and production142/45 compile0 errors/0 warnings. The HMI suite passes
570 tests with one skip; the tool suite passes128.

Use `Tests/Access/with_credentials.ps1 -Action prepare|probe -ScriptFile <script>`
with make_fixture.py, probe_web.py or probe_nested_web.py. The wrapper loads only
DPAPI credentials and clears them afterwards. Writes require the exact isolated
Fraktal CPU1516 TCPIP target,169.254.212.49, with zero physical mappings. Never
replay a mutation after uncertain delivery. Do not rebuild the approved driver.

Current saved runtime: TiaStations/Alarm_Runtime_20261011/FrkS12/FrkS12.ap20.
Alarm_Verify_20261011 holds native reimport and the production compiler-only image.
The owner Fraktal instance remains registered and RUN. Physical1214C was untouched.
After the owner's VM reboot, the same saved Fraktal persistence restored without
a download. A hidden API keeper remains alive because the registering client owns
the registration while no control panel is attached; do not stop it as routine
cleanup. Post-reboot nested fault/reset checks pass23/23 again.

Shelving, runtime project metadata, alarm/user/policy retention, synchronized UTC
quality, complete awaited-diagnostic selection and full sequence/GRAPH integration
remain open. Restart deliberately clears this nonretained prototype log/session.
See [dated evidence](../../../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_STATE_ALARMS_2026-10-11.md).
