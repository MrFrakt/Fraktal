# PROFINET node health and the approved driver (P8, 2026-11-10)

Owner decision 2A unblocked native PROFINET work: the Openness driver can now
build an IO system. This record covers the driver, the generated node health
and its first native gate.

## The driver

`tools/TiaCli/Program.cs` gains four commands, none changing an existing one:
`io-system` (the controller interface joins a subnet, the IO system is created
or kept), `add-module` (plug at a checked rack slot), `connect-io` (an IO device
joins the controller's subnet and IO system, optional address and device name)
and `system-constants` (hardware identifiers by name, read-only). The owner
approved build `tools/TiaCli/bin/candidate_profinet` (SHA-256
`6f9e1bf03a55d83a943811565498bb3e0c48e5270bfbe34704fe438dd68a45ec`) and
whitelisted it; the registry entry was read back before use. `tools/tia_driver.py`
is now the one pin both benches import. Openness whitelists one build per file
name, so the previous `candidate_structure_examples` (`ba24e6aa…`) no longer runs.

Measured on the first fixture build: subnet `PN/IE_1`, IO system 100 (hardware
ID 257), IM 155-6 PN ST V4.2 as `IM_1` (device 262), device name and address
set, hardware compile 0 errors. Two findings shaped the fixture: the ET 200SP
server module is plugged automatically at slot 1 and nothing may follow it, so
the head stays without I/O modules; `6ES7 131-6BF0x` DI modules were refused at
every tried version, while the central `6ES7 522-1BH01-0AB0/V1.0` DQ plugs at
slot 2 of the CPU rail.

## Node health

A topology node may bind to a PROFINET device by naming its IO-system and
device system constants. The generated publisher reads `DeviceStates`
(existing, disabled, problem) once per IO system, at most every 250 ms; the
device number comes from `LOG2GEO`. Link = exists and not disabled; state
`OFFLINE` without a link, `FAULT` when the device reports a problem, otherwise
`OPERATIONAL`; a failed read is `OFFLINE`. The bound node's inputs take their
quality from it. Stations without a binding generate nothing new. Part IV §10.5
records the rule and what remains open.

## Measured

| Run (`%LOCALAPPDATA%\Fraktal\TiaSpikes\…`) | Result |
|---|---|
| `P8_PnFixture_20261110_01`, `_02` (driver hardware trials) | as above; `_02` hardware compile 0 errors, 2 standard development warnings |
| `TiaGate_P8Pn_20261110_01` | all three suites compile 0/0; read-back refused `F_PnTestPublish`: the export writes `GEOADDR`'s instruction identity, which the generator did not. Fixed in the generator, test pinned |
| `TiaGate_P8Pn_20261110_02` (native gate, no bench) | PASS: 302 tool tests, lint/consistency/contracts clean, press replay 286. Operations 0/0, read-back 297/85/22; reusable modules 0/0, 305/93/18; **PROFINET 0/0, 262/71/17**, image hash `f80ba6c3846162aba202d592203c7c95b6552fd050ea3497250105e1fbc2c3b0` |

`P8_ForceSpike_20261110_01` (`Tests/ProfinetHealth/force_spike.py prepare`)
holds the same fixture with its web server, certificate and DPAPI-provisioned
user: compile 0/0, read-back 262/71/17, hardware compile 0 errors and the two
standard development warnings. It is ready for the owner's force-job session.

The fixture's `DeviceStates`, `LOG2GEO`, `D_ACT_DP` and `LED` calls compile on
the reference CPU 1516-3 PN/DP V3.0. The gate compiles the new suite on every
run and benches it after the other two when `--bench` is given.

## Not yet measured

The suite has not run on a test CPU: the PLCSIM manager is in Softbus mode
and every isolated bench needs TCP/IP. Its five runtime assertions (simulated
device operational, `D_ACT_DP` disable, offline on the next sample, re-enable,
operational again) and the force-job spike wait for that. `ModuleStates`,
`GET_DIAG` detail and OB82/OB83/OB86 wake-up are not used.
