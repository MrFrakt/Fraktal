# Press demo operated over the direct S7 Web API link, 2026-10-15

The Fraktal/TIA press demo was downloaded to the simulated S7-1500 for the first
time and operated end to end by the native HMI repository over a new direct
`s7web://` link, with no gateway. Target: PLCSIM Advanced 7 instance `Fraktal`
(CPU1516, TCPIP 169.254.212.49 + 192.168.1.1, physical adapter mappings 0),
TIA Portal V20 through the approved `candidate_structure_examples` driver
(SHA256 `ba24e6aa…ff1d330652fc74`, unchanged, no rebuild or whitelist). The
owner authorized replacing the config-types bench image on that instance for
this run. This is simulation evidence, not physical process acceptance.

## What changed

**Direct HMI link.** `s7web://<cpu>?pin=<SHA-256>[&roots=…][&batch=…]` reaches a
TIA station from the native HMI as `ads://` reaches TwinCAT. It reuses the
gateway's `WebApiSessionClient` behind the same generation-guarded reconnecting
client. The CPU certificate is pinned by fingerprint (mandatory, no CA or
accept-any path; a mismatch fails the handshake naming the presented
fingerprint). The CPU web user comes from `FRAKTAL_TIA_WEB_USER`/`_PASSWORD`, never
the endpoint. The CPU refuses every write except the `HmiRequest` mailbox. Web
builds refuse the scheme and use the gateway. Specified in OPCUA_TRANSPORT
"Direct native HMI (no gateway)".

**Press parity with TC3, power control and PartFeed excluded (D3, owner).**
- Three passive CM types port the TC3 sensors with their TC3 type keys:
  `FB_TwoHandStartCM`, `FB_DigitalInputCM` (PartPresentSensor) and
  `FB_AirPressureMonitorCM` (qualified switch conflict, `AIR_SWITCH_CONFLICT`
  10601 bound from the TC3 module reason list). The shared runtime now admits a
  command-less type at the CM tier only; its frame rejects every request as
  UNSUPPORTED_COMMAND.
- CHANGEOVER mode chain (ST, wired) with the TC3 step graph 0/800/810/870/880/999,
  operator decision with "repeat position" JUMP1 back to 810, and the shared
  load-position sub-chain under its own lease identity.
- Model catalog ALUMINUM/PLASTIC/STEEL with the TC3 recipe seeds through a new
  Core `model_config.seeds` declaration. PressSettleTime, TransferSettleTime and
  the Unit's mode-switch Timeout are model data; RequireTwoHandStart stays station
  data (TC3 v3 rationale). A type that registers no ParCfg field keeps fixed type
  defaults (TC3: a module with no recipe); a partial registration is still refused.
- Simulated plant (travel-time cylinders, part swap, air/quality) selected by a
  generated `USE_SIMULATION` build constant from `integration.simulate_feedback`.
  Physical outputs are held FALSE while simulating. Stimuli are readable but not
  Web-API writable (lint T-EXT keeps the write surface at the mailbox).
- Derived `TwoHandStartReady` drives the start lamp output on the physical path.
- The Cylinder type key is now `std.moduleType.cylinder`, as on TC3.
- The Unit publishes its active model as `Model` (the Core/HMI contract name), not
  `ModelId`; before this the HMI showed no model for any TIA station.

## Defects found by running the press

The press had only ever been compiled offline. Running it exposed:

| Defect | Effect | Fix |
|---|---|---|
| ST `CASE` ELSE raised 10001 while idle | the load-position sub-chain (no step 0) faulted the Unit on every idle scan; a reset re-raised it | the undefined-step fault is raised only while the chain runs |
| Unit ParCfg `Timeout := T#0ms` | every mode change timed out on its first scan; Start would be refused | 10 s default, now editable model data |
| Diagnostic sync emitted `#ParCfg.` for a type without a timeout | compile errors in passive CMs | zero timeout for passive types |
| Active model published as `ModelId` | HMI never displayed or tracked the model | renamed to the contract `Model` |

## Gates

| Gate | Result |
|---|---|
| Offline compile press01…press06 | press01 6 errors (passive timeout), press02–06 0 errors / 0 warnings at both stages |
| Native readback press06 | 216 sources replay; GRAPH AUTO 19 / HOME 4 steps; LAD 198 networks / 192 calls incl. CHANGEOVER twin |
| Siemens tools | 205 tests OK (new: passive CM frame, model seeds, fixed-default type) |
| `tia_lint` | 0 findings |
| `check_consistency` | 0 errors, 0 warnings |
| HMI | analyze clean; 587 passed, 12 opt-in live skips (new `s7web_direct_test`: SHA-256 vectors, endpoint grammar, loopback TLS pin accept/refuse) |
| TwinCAT `plc_lint` | 426 files clean |

## Live runs (final download of press06, then `press_final`)

Through `createExternalRepository(s7web://…)` — the production repository the HMI
uses — with the on-demand chart/ring reads a Sequence tab requests:

| Phase | Result |
|---|---|
| Discovery | 1 root, 7 modules (3 cylinders + 3 sensor CMs), connect ≈ 0.8 s |
| MANUAL | ram EXTEND refused with the guard door open (release); door EXTEND accepted and closed |
| HOME | steps 0/900/910/999 visited; ram and door retracted |
| CHANGEOVER | SET_MODEL ALUMINUM → STEEL committed atomically; 0/800/810 (+600–660)/870/880/999 visited; answer 2 audited `decisionOperatorResolved option=+2` and re-asked; answer 1 completed; `OutCmd.ChangeoverCompleted` TRUE |
| AUTO | 3 good parts, 0 NOK in 11.8 s; dwell step 220 = 1199 ms (STEEL seed 1200 ms); parallel legs 1/2 and the sub-chain all visited |
| Stop/restore | stop at the cycle boundary; model back to ALUMINUM; two-hand requirement back to TRUE; MANUAL/READY |

Earlier failed live attempts (runs 1–11) are kept: they show each defect above
and two test-harness corrections (config hydration wait; HOME/repeat proven from
PLC-recorded visits and audit records rather than poll-rate transients).

## Remaining scope

Not ported, with no consumer yet in this binding: engineering-gate register and
its HMI strip, I/O topology/identity publisher (`IoTag`), OEE/shift/line, signal
tower, health providers, the TwoHand `Safety` facet. PartFeed axis waits for S14.
Two-hand start does not yet start AUTO from READY as on TC3 (Start comes from the
HMI). Simulator stimuli can only be changed through engineering tools.
Decision audit text keeps TIA's signed `option=+n`. Physical process,
endurance and deployment acceptance remain open.

Payloads: [archive](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_PRESS_COMPLETE_2026-10-15/SHA256SUMS)
(build/download logs, live JSON/flutter logs, read-only diagnostic reads, native
GRAPH/LAD XML and key SCL exports, readback parity). Projects:
`%LOCALAPPDATA%\Fraktal\TiaStations\Press_Complete_20261015` (copy of
Config_Types_Press_Offline_20261015, which is unchanged); work under
`TiaSpikes\Press_Complete_20261015`. The config-types bench project remains on
disk for re-download.
