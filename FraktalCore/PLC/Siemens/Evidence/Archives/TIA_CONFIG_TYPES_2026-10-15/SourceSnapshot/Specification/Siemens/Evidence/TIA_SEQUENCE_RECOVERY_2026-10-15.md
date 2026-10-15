# Selected sequence recovery, 2026-10-15

Generator0.20 qualifies shared fault recovery on the preserved TIA V20 /
Advanced7 CPU1516 Fraktal simulator. A synthetic native GRAPH exercises the
mechanisms; the separate wired press is compiled offline. This does not claim
physical-process acceptance or a released, fully conforming runtime library.
The work directory began on October14 UTC; this report uses Europe/London.

## Owning behavior

The generated Unit frame captures lifecycle state before sequences and after
the command kernel resolves the scan. Private restart/resume epochs are
allocated only for consumed sequence-view owners. Existing begin helpers consume
them; MAIN stays three calls and applications add no recovery scheduling call.
Released Core layouts and enum ordinals remain unchanged.

A fault freezes the raising step and releases issued child command leases.
Leaving ERROR clears row errors and rearms command, delay and event state.
An accepted Start follows project policy: continue at the retained step or restart
the whole chain. The press explicitly restarts on each accepted Start. Recovery
reissues and retests the command after an Execute-low gap. Removing the condition
or resetting alone does not start motion. HELD keeps its existing automatic
permit recovery without a fault/reset/reissue.

Boot, mode change, both abort paths and restore quiescence invalidate retained
work. Native GRAPH evaluates transitions before new step actions: its shared
begin service preserves the preceding active result for that evaluation, and the
mandatory step record clears it before the current action decides. Fault,
restart and rearm discard the result. Ordinary fault freeze withholds the chart
call; forced-restart idle scans call it with OFF_SQ and let INIT_SQ fall before
the next Start. INIT_SQ pulses only while running. Inactive step/delay helpers
cannot publish a row or progress a timer.

## Validation

| Gate | Result |
|---|---|
| Native GRAPH recovery | 79 passed |
| Native profile regression | 106 passed, including 57 deterministic timing cases |
| Native diagnostic regression | 71 passed |
| Native view/helper/manifest regression | 122 passed |
| LOAD_DB restore/quiesce/restart regression | 37 passed |
| Final normalized fixture | 45 values checked; retained private-user login/logout passed |
| Engineering-tool suite | 197 passed |
| Cross-tree consistency suite | 35 passed; consistency0 errors/0 warnings |
| Selected changed HMI tests | 111 passed |
| Siemens lint | 0 findings; declaration-only pending categories remain stated by the gate |
| Final runtime, delta and download compiles | 0 errors, 0 warnings |
| Separate wired press full-import and final delta compiles | 0 errors, 0 warnings |
| Runtime source/interface witness | 466 blocks / 111 interfaces |
| Press source/interface witness | 424 blocks / 101 interfaces |
| Synthetic native GRAPH object | 3 steps / 3 edges match |
| Wired press native GRAPH parity | 19 AUTO / 4 HOME steps |
| Optional native Ladder parity | 161 networks / 155 calls |
| Shipped replay | 24 default / 184 grouped press sources |

The five native probes total415 passed checks. Final fixture checks are separate.
Native recovery covers retained-step continuation, explicit restart, no automatic
retry, command/delay/event rearm, row clearing, Execute-low release, peer-root
isolation, HELD, late kernel faults, both abort paths and live quiescence.

Source witnesses cover SCL, UDTs and the recovery observation DB. Initialized
storage DBs are excluded because native export moves their initializers into
BEGIN. Press optional ST twins and GRAPH owner adapters retain the earlier
explicit witness exclusions for omitted reference annotations/empty sections;
native chart/Ladder object parity is separate. No access change is normalized
away. Native checks verify private work and readonly step publication.

The profile regression starts after a guarded restart: the four-slot synthetic
stat pool had correctly reported truncation after unrelated GRAPH test steps
occupied it. Production capacities were not enlarged. The view regression now
retains its actual successful Pending sample: its test-only helper context is
read directly and its scan-local flag briefly clears before Await sets it.
Frame-owned public chart mirrors retain their existing publication boundary.

The selected HMI suite covers changed config, gateway, reset, manifest,
repository, mapper, Web API and widget behavior. Its111-test result is recorded
from the tool transcript; native HMI rendering remains the separate generator0.19
qualification. Broader historical persistence/plant suites were not repeated.

## Errors corrected

The initial test import compiled before its GRAPH owner and provisioning routine
were available. The fixture now compiles a complete bootstrap chart/Unit set,
then imports the owner and final frames. A malformed first download plan opened
the project only and was rejected by the clean-compile gate; it performed no
download. Correct plans use distinct lines and the lowercase download placeholder.

Live execution exposed transition-result clearing before GRAPH's evaluation.
The shared GRAPH begin boundary fixes it. A Ladder input had serialized an SCL
OR expression as a tag; all renditions now consume one computed SubReset operand.
Abort-in-ERROR exposed a retained native reset input, and recovery also needed
to clear the error latch when a whole restart was pending. Forced idle/reset
handling now passes both abort paths. An inactive initial GRAPH action could
publish a MANUAL row; running-only reset pulses and shared helper guards close it.

Abort is a protected PLC input, not an HMI ABORT ordinal. The fixture drives it
through committed PLC wiring without weakening production access. Quiescence
drops the session, so its restart test logs in again. Failed attempts and
read-only SDK diagnostics are preserved with their exact source variants.

## Current artifacts and remaining scope

Runtime: `%LOCALAPPDATA%/Fraktal/TiaStations/Sequence_Recovery_Runtime_20261014/FrkS12/FrkS12.ap20`.
Offline press: `Sequence_Recovery_Press_Offline_20261015/FrkS12/FrkS12.ap20` under
the same station directory. Final source/run variants are runtime09 and press05
under `%LOCALAPPDATA%/Fraktal/TiaSpikes/Sequence_Recovery_20261014`.

The approved candidate_structure_examples driver is unchanged, SHA256
`ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74`.
No rebuild or new whitelist was needed. Every native mutation used the isolated
target guard and complete-argument/final-sequence mailbox discipline. The
Fraktal simulator, keeper13476, addresses, physical mappings0, storage, pin and
DPAPI credentials remain preserved. Final roots are MANUAL/READY/logged out,
with no Held, blocking alarm, Pending diagnostic or pending/failed config;
charts and volatile profiles are empty and test stimuli are disabled.

Code, run logs, native exports, failed variants and knowledge notes are frozen
in [the archive](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_SEQUENCE_RECOVERY_2026-10-15/).
Its SHA256SUMS binds the payload bytes. Earlier archives remain immutable.
The local SiemensAgent SQLite knowledge index is updated with backup and
integrity/table-count checks; the private database backup stays local.

Next: configuration-provider and line-config integration, baseline/degradation
and gated statistics/OEE reset, module/HAL expansion and deployment acceptance.
Full branched-process, physical press and broader loss/conformance gates remain
separate. ST/LD examples remain uninstantiated; GRAPH/ST permissives stay wired.
