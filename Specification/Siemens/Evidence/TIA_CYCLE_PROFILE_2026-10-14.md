# Selected cycle profiling, 2026-10-14

Generator0.19 qualifies shared cycle timing on the preserved TIA V20 / Advanced7
CPU1516 simulator Fraktal. The selected LOAD_DB/view/diagnostic runtime and the
wired press use separate engineering projects. The press is compiled offline;
this is no physical-process or released-library conformance claim.

## Owning behavior

Existing step records feed the main-line profiler. Existing cycle-end markers
request completion; the generated frame completes it after the command kernel's
final decision. A finish followed by a kernel timeout in the same scan is not
counted. First-scan zero-duration cycles are recorded, and a zero rolling minimum
survives later positive cycles. MAIN retains its three calls.

The shared services publish readonly last-cycle waterfalls, per-step statistics,
class totals, work/wait split, rolling minimum and a Core-sized 60-cycle ring.
Step/stat storage follows the consumed sequence capacity, capped at Core's
MAX_PROFILE_STEPS. Released Core layouts, enum ordinals and compact registry are
unchanged. Command and step rows share the aggregation function. Repeated records
of one visit do not reopen timing; terminal holding does not duplicate cycles.

Durations use the wrapping monotonic clock. LDT start stamps retain nanoseconds;
synchronization quality remains false. Positive TIME overflow clamps and signals
truncation; bounded row/stat overflow is visible, and counters saturate. Parallel
legs retain their chart rows and do not complete or classify the main line.
Starved/Blocked derive from the active AUTO main-line time class.

Mode exit, fault, abort and restore quiescence withdraw incomplete collection.
Completed profiles survive ordinary mode changes/quiescence. This profile is
volatile: startup clears the waterfall, statistics and history.

## Validation

| Gate | Result |
|---|---|
| Native profile cases and Unit integration | 106 passed, including 57 deterministic timing cases |
| Native diagnostic regression | 71 passed |
| LOAD_DB restore/quiesce/restart regression | 37 passed |
| Shared view/helper/manifest regression | 120 passed |
| Final normalized fixture | 36 values checked; retained private-user login and logout passed |
| Native generic HMI | Native durations/classes/guards/statistics/history match; waterfall and trend render |
| Targeted Web API/repository/mapper tests | 52 passed |
| Engineering-tool suite | 194 passed |
| Cross-tree consistency suite | 35 passed |
| Siemens lint | 0 findings; declaration-only pending categories remain stated by the gate |
| Final runtime compile/download compile | 0 errors, 0 warnings |
| Final wired-press import/compile, both stages | 0 errors, 0 warnings |
| Runtime native source/interface witness | 457 blocks / 110 interfaces |
| Press native source/interface witness | 417 blocks / 100 interfaces |
| Native GRAPH parity | 19 AUTO steps, 4 HOME steps |
| Native optional Ladder parity | 161 networks, 155 calls |
| Shipped generator replay | 24 default sources, 181 grouped press sources |

The four primary native probes total334 passed checks. Final fixture checks are
listed separately. The earlier full HMI and persistence-consumer suites were not
repeated; the new targeted/live gates and the selected restore/diagnostic/view
regressions define this continuation's scope.

Canonical source comparison covers SCL, UDTs and the profile observation DB.
Other initialized DB sources are excluded because TIA moves their declaration
initializers into BEGIN. Optional ST twins and GRAPH owner adapters follow the
explicit earlier witness exclusions for omitted reference annotations/empty
sections; native GRAPH/LAD graph parity is checked separately. No access change
is normalized away. Native privacy/readonly checks cover the new profile work
and mirrors.

## Errors found and corrected

The first thin compiler package omitted its structural registry dependency.
The complete 25-source package compiles cleanly. An early frame ordering could
count a cycle before a later kernel timeout; completion now follows FRK_End and
the native late-timeout case proves the failed cycle is rejected.

The first native HMI discovery expanded every history slot in every selected
Unit and hit the 20,000-node limit. Web API discovery now derives occupied slots
from Profiler.LastCycle.CycleNo and the actual array extent. Growth and reset
re-emit paths; new leaves remain excluded until a consuming read plan applies.
Ring wrap at full capacity does not require another discovery. The final native
HMI discovers18794 leaves without truncation and target-reads history/statistics
through the existing view demand. No station-specific HMI code was added.

Failed harness attempts are preserved. The four-row fixture rejected a fifth
distinct row; the corrected probe reuses declared rows. Graceful mode exit needs
the existing fixture completion input. MANUAL does not accept Unit Start, so the
non-AUTO running check uses HOME. Reset is requested only when its release query
allows it. Screenshot I/O runs in Flutter's real async zone. One diagnostic
attempt stopped when simulator identity lookup failed before the next mutation;
fresh guarded regression subsequently passed. In-flight manifest queries can
log a closed-session message during HMI harness teardown; the live test passes.

## Disk cleanup

Checksum-matched archived temporary duplicates removed earlier account for
64,128 files / 1,111,828,363 logical bytes. The separately approved 33 saved
engineering copies dated October11–13 contained4,765,766,798 logical bytes.
Automatic approval review rejected their deletion with "blocked by policy".
The owner ran the prepared containment/process/reparse-checked script.

The completion audit records33 removed directories, physical free-space recovery
of3,159,453,696 bytes, and4,504,428,544 bytes free immediately afterward. Verification
finds none of those approved paths remaining. Current runtime/press projects,
baseline, credentials, simulator storage and sealed evidence are preserved.
Cleanup scope and audits are copied into this continuation's archive.

## Preserved continuation

Current runtime:
`%LOCALAPPDATA%/Fraktal/TiaStations/Cycle_Profile_Runtime_20261014/FrkS12/FrkS12.ap20`.
Separate wired press:
`%LOCALAPPDATA%/Fraktal/TiaStations/Cycle_Profile_Press_Offline_20261014/FrkS12/FrkS12.ap20`.
The persistent keeper13476 owns Fraktal; verify identity before any action.
RUN, CPU1516, TCPIP169.254.212.49 plus192.168.1.1, physical mappings0 are preserved.
The approved candidate_structure_examples driver is unchanged; its SHA256 is
ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74.

Final roots are MANUAL/READY/logged out, with empty chart/profile history after
the tested restart, no HELD/Pending/blocking alarm/pending or failed config commit,
and all stimuli disabled. LOAD_DB restores17 documents; retained login works.
No commit, staging, push or new handover prompt was produced.

[Sealed payload](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_CYCLE_PROFILE_2026-10-14/)
contains completed logs, source/native witnesses, failures, the HMI capture,
cleanup audits and source/knowledge snapshots. Earlier sealed evidence is untouched.

Complete sequence freeze/resume policy, baseline/degradation watching, gated
statistics/OEE reset, provider and line config, module/HAL expansion and deployment
acceptance remain open. Physical process testing and abrupt VM-loss/torn/endurance/
full-download/card/external persistence guarantees remain separate gates.
