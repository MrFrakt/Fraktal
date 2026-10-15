# Unit controls and local carrier (2026-10-11)

Scope: simulated1516 V3.0, Advanced7, TIA V20, isolated FrkS12. Evidence:
C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_UNIT_CONTROLS_2026-10-11.md.

- **[measured]** Generator0.3 Unit-only profile declares supported Core modes,
  initial mode and run command.45 generated sources; the test package adds one
  stimulus DB and replaces OB1.79 blocks/34 interfaces compare canonically and
  ordered reimport compiles0 errors/0 warnings. Production entrypoint alone
  compares78 blocks/34 interfaces and compiles0/0; it is compiler-only.
- **[measured]** Native pinned Web API controls pass103 checks: live access and
  permits, unsupported modes/requests, same/zero sequence rejection, secret
  clearing, run beyond its bounded-command timeout, cycle-boundary stop,
  graceful/immediate/deferred/bounded mode exit, recursive child command release,
  live-fault/permit preservation on reset, carrier failures, part results/events,
  STOP/RUN and post-restart operation. Private paths return200; non-mailbox module
  writes return205. This is native API command proof, not GUI rendering.
- **[measured]** A VAR_INPUT HmiRequest passed to a modifying FC gives two access
  warnings. A writable static preserves the native path and compiles warning-free.
  Copy a complete nonzero commit before consuming; clear transport/private copy
  secrets, refresh cyclic releases, run the common operation authority and ack
  after processing. Every test mutation/mode act checks the exact virtual target.
- **[measured]** Unit run has no whole-run timeout; child commands/steps own
  bounded work. Pending mode exit has a ParCfg timeout. Core AUTO default is
  CONFIRM/GRACEFUL, unlike the currently implemented TwinCAT IMMEDIATE default.
  CONFIRM is the HMI prompt obligation; do not invent an additional BoolValue
  gate that the unchanged generic client does not supply.
- **[measured]** FRK_ReleaseCommand propagates through generated composite calls
  and wakes quiet CMs. Reset releases stranded Execute and gates Start until
  descendants are READY. A live cyclic condition re-faults after reset; a false
  permit remains false. A Unit command fault remains visible until reset/stop.
- **[measured]** BY_POSITION provider is explicitly injected; the peer stays off.
  Result writes precede the processed event; write/read/identity/invalid NOK
  failures use Core reasons and abort the present part. Counters change once;
  four canonical events use the bounded History. UID durability across restart,
  other providers, genealogy transport and measurement helpers remain open.
- **[measured]** This fixture's non-retained Restarts count returns1 at STOP/RUN.
  A counter-increment expectation failed; BootStamp proves a new Initial_Call,
  and ack is compared with the current post-restart request sequence. Do not
  assume old data/commit survived. Production retention classes remain separate.
- **[measured]** Native export spells AccessPolicy's T#0S as T#0ms. The scalar
  binding now emits that exact zero-TIME spelling; no source-ignore was added.
  All other source/interface/type/access attributes compare strictly.

Default PLC access policy is open/NONE. No authentication provider is implemented:
LOGIN fails and clears secrets; LOGOUT returns to NONE. Full session/audit/alarms,
nested Unit mode cascade, manual routing, complete release-action/config queries,
recipes/retention, sequence/GRAPH and native HMI rendering remain subsequent work.
Press scope still excludes power control;150KB applies only to the secondary1200.

Current Unit project: LOCALAPPDATA/Fraktal/TiaStations/Unit_Runtime_20261011/FrkS12.
Earlier projects, DPAPI secret, pin and certificates remain preserved. The driver
is the unchanged approved enumeration build; no new whitelist. Physical mappings0.

- **[measured]** The current common command kernel still passes 238/238 assertions
  in 55 cases. Its regenerated regression package compares 48 blocks/18 interfaces,
  compiles 0/0 and passes again after the harness CASE ELSE correction. The Unit
  image was restored and its 103-check native series repeated successfully.
  Final Siemens tool/consistency suites pass 112/33; declaration replay and lint
  pass. Owned host15268 exited, 0 instances registered, prior NetworkMode2 restored
  at 2026-10-10T23:44:09UTC. A new registration needs logged engineering trust.
