# Fraktal/TIA derived states and alarm/event lifecycle - 2026-10-11

Generator0.7 compiles warning-free and passes96 native state/alarm checks,
23 nearest-Unit/ancestor-reset checks and122 authentication regressions on the
simulated S7-1500. The real generic HMI authenticates an operator, executes its
rendered manual button, displays the captured fault and clears it through reset.
This is a measured prototype slice, not complete Core alarm/audit conformance.

Raw logs, generated/native sources, JUnit, screenshots and source/knowledge
snapshots live in `../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_STATE_ALARMS_2026-10-11/`. Its `SHA256SUMS` binds archive
files and this report using repository-relative paths; it excludes itself.
This evidence is append-only. The final checksum audit stays outside the archive.

## Target and preserved engineering state

TIA Portal V20; Advanced7 with API5 compatibility DLL; simulated CPU1516-3 V3.0.
The reference uses full Core capacities, SCL and generated GRAPH, without a150KB
limit. This slice uses SCL services; it adds no chart rendition. The physical1214C
was untouched. Runtime project: `%LOCALAPPDATA%/Fraktal/TiaStations/Alarm_Runtime_20261011/FrkS12/FrkS12.ap20`.
`Alarm_Verify_20261011` holds native reimport and the compiler-only production image.
Both station copies were hash-checked before mutation; the Access projects remain.

The owner Fraktal instance uses TCPIP169.254.212.49 and the configured second
192.168.1.1 interface, with all three physical mappings zero. Existing project
certificates, pinned HTTPS and process-data-only Web permissions remain.
Application PINs and Web credentials come only from the DPAPI wrapper and are
cleared afterwards; no plaintext credential enters an argument/log/evidence file.

The approved `candidate_s11_enumeration/Fraktal.Tia.Cli.exe` remains unchanged:
SHA-256 `e455ee93e616c4788001b07830164da92b72e3817d6a90c90e03d98937026f33`.
No driver rebuild, new whitelist, physical download, stage, commit or push occurred.

## Implemented behavior

Unconditional authored FRK_State calls declare bounded unique literal slots and
keys in the derived cyclic region. The generator supplies context, sweep and
private touched flags; only consuming module types allocate StateFlags/count.
The12-slot capacity and120-character key width derive from Core. Value/key or
freshness changes update Since; a lost producer forces FALSE/Stale while retaining
its last change timestamp. Derived OutImm changes without a command.

Units publish16 active and64 closed Core ST_AlarmEvent records. Raise copies
first-out source/text/I/O, applies the authoritative rationalization and records
come UTC plus a private monotonic start. Gone computes saturating TIME duration.
AUTO_RESET closes at gone; MANUAL_RESET stays blocking in WAIT_RESET. Operator
reset closes ACTIVE and WAIT_RESET, stamps reset, and releases the Unit/issued
child commands. A live condition raises again rather than disappearing on reset.
Active overflow and closed-ring overwrite set Truncated. UTC-quality flags remain
FALSE; a CPU timestamp alone does not establish synchronization.

Generated fault capture follows FRK_End, stops at the nearest Unit, and reuses an
existing automatic first-out instead of duplicating adopted faults. Nested Unit
logs stay independent; ancestor admission sees their blocking through the registry.
HELD withdraws output and remains BUSY without an alarm. Access audits, Part events
and unsupported child modes now use AUTO_RESET occurrences. History remains the
separate diagnostic fault trace. Runtime project metadata/shelving remain absent.

An optional declaration event_sink binds a composition function with Ev:
ST_AlarmEvent input. Private SinkEnabled controls delivery. The native fixture
checks come and exact closed payload callbacks. With no binding, no callback
dependency is emitted. A durable historian adapter is not implemented or claimed.

## Measured gates

| Gate | Result | Archive records |
|---|---|---|
| Routing-only alarm candidate |120/120 |02-04 |
| Final state/alarm image |compile/download0 errors0 warnings |08,10 |
| Native state/event lifecycle |96/96, restart included |11_native_v4 |
| Nested ownership/ancestor reset |23/23 |29_nested |
| Current authentication regression |122/122 |16_auth_regression |
| Native canonical source/access layout |148 blocks/45 interfaces equal |09 |
| Native export/reimport/export |148 sources equal; compile0/0 |14,17 |
| Production compiler-only image |142 blocks/45 interfaces equal; compile0/0 |15,20 |
| Authenticated live HMI |pass:24 modules/492 entries, Instant counter delta1, state/fault/reset |21,22, hmi-forest.json, hmi-alarm.png, hmi-manual.png |
| HMI suite |570 pass,1 skip, exit0 |28_hmi_tests |
| HMI source analysis |no issues |35_hmi_analysis |
| Generator/tool suite |128 tests pass |24_tools |
| Source lint/consistency |0 findings;33 consistency tests pass |25-27, final checks |
| Post-reboot nested alarm regression |23/23 on restored image |38_postboot_nested |

The routing120 pass belongs to the earlier routing-only candidate, before final
fault-capture ordering and state/sink fixture additions. It is not represented as
a rerun on the final authentication-locked image. The final96/23/122 gates test
that image. Production generation omits test DBs/callback and disables the provider;
it was compiled/exported separately and was not downloaded over the measured image.

The HMI uses its normal OPERATOR display policy. Fault text resolves through the
Core reason-code localization map. The screenshot shows Test fault, the canonical
source, WAIT_RESET, blocking/reset controls and unsynchronized-time indication.
The HMI reset helper now recursively recognizes nested blocking even after the
child fault clears; a regression verifies the root remains resettable.
Read-only background queries can be cancelled during gateway disposal; the live
test finishes without widget exceptions and the gateway closes.

## Preserved corrections and VM reboot

All source candidates compile0/0. A new generator test caught capture before
FRK_End; candidate V4 moves it after End and passes.19_hmi_live preserves the first
HMI failure: its assertion expected raw test.first, while the mapper deliberately
uses the Core TEST_FAULT localization. The corrected assertion uses that authority;
22 passes. Source analysis info findings are preserved in30/31 and resolved in35.
The checked-in structural example regeneration changes only0.6->0.7 headers and
its manifest, with byte equality asserted after the version substitution.
The final whitespace check45 found CRLF in the changed HMI reset source;46 records
its LF conversion and47 passes. Raw vendor exports/logs retain their original bytes.

After the morning tests, the VM rebooted at16:09:46UTC. The final preflight found
zero registered instances and HTTPS unavailable. The existing Fraktal persistence
directory still held the CPU1516 hardware identity and memory card.33 restores it
without a download, but the registering API process exits and its registration
disappears;34 preserves the ensuing HTTPS timeout.36 restores the same saved image
with a hidden API keeper.38 then passes all23 nested fault/reset/login assertions
on that restored image. No explicit unregister or deletion was used.

The keeper is required while no control panel owns the registration. Its PID and
stop-file path are recorded in36; it has no expiry and remains running. Do not
stop it as routine test cleanup. No Openness compiler or Web gateway is left.
The final read-only witness checks Fraktal RUN, both roots and exercised nested
Units READY/MANUAL, sessions NONE, no pending login, secrets cleared and no active
or blocking alarm. State count/value are recomputed on restart. This is deliberate
nonretained prototype behavior, not an alarm-retention guarantee.

## Availability and remaining work

All3360 bindings of the previous Access archive and all134 available older files
are verified unchanged. This checkout still lacks twelve newer older reports and
all18 pre-Access checksum manifests. Absent records are not reconstructed or
claimed reverified; the availability gap remains the one recorded by Access.

Shelving, runtime project metadata, alarm/user/policy persistence, durable sink
adapters, configuration/recipe transactions, complete awaited-diagnostic selection,
frontier/control-domain/action release services and concurrent mailbox writers
remain open. Full SCL/generated GRAPH sequence integration, modules and the press
without power follow. No physical S7-1500 or S7-1200 state/alarm result is claimed.
