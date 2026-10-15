# Shared sequence diagnostics, 2026-10-14

Generator 0.18 qualifies scoped first-out, named stalls and HELD services on
TIA V20 / S7-PLCSIM Advanced V7, simulated CPU1516 instance Fraktal. The separate
wired press compiles offline. This closes a diagnostic slice of the port;
complete binding conformance and physical press acceptance remain open.

Private snapshots are allocated for deployed modules beneath selected sequence
Units. Names, slots and ownership derive from the declaration. Owning frames
capture canonical diagnostics after cyclic work and invalidate them during
quiescence. The compact registry and released Core types/ordinals are unchanged.
Sequence commands pass target identity instead of copied state/diagnostic inputs.
Shared walks reject foreign roots, preserve the whole first-out and distinguish
EM fault adoption from Unit awaited-fault adoption. Handled failures remain
warnings under their sequence's recovery policy.

The frame derives the longest awaited timeout unless the step supplies a guard.
At expiry the main line publishes LOW Pending with the child reason or a named
first-false condition. Stalls create no fault or blocking alarm. HELD preserves
the child reason, disarms generic stall publication and clears when its permit
returns. Unhandled faults mark their row before guard expiry; parallel faults
use their own row. Generic command leases now withdraw Execute and pulse Abort
when releasing a busy command, preserving the Execute-low reset gap.

The press still wires GRAPH AUTO/HOME and ST permissives. Optional ST/LAD twins
remain uninstantiated. Fraktal groups, config names and three-call MAIN remain.
No application scheduling call was added.

| Gate | Result |
|---|---|
| Native first-out/stall/HELD/handled-failure checks | 71 passed |
| Combined LOAD_DB quiesce/restore/restart | 37 passed |
| Sequence-view regression | 122 passed |
| Siemens tools | 189 passed |
| Cross-artifact suite | 35 passed |
| Siemens lint / consistency | 0 findings / 0 errors, 0 warnings |
| Final runtime and offline press compile | 0 errors, 0 warnings |
| Runtime native source/interface readback | 432 blocks / 98 interfaces |
| Press Core/module/frame readback | 401 blocks / 95 interfaces |
| Native chart/rung parity | 19 AUTO + 4 HOME GRAPH steps; LAD161 networks / 155 calls |
| Shipped generated replay | 24 default / 172 press sources |

The view count includes variable manifest-page acknowledgements; the earlier
0.17 run reported 120 on its separate package. Source comparison includes SCL,
UDTs and the observation DB. Other initialized DB sources are excluded because
TIA relocates declaration initializers to BEGIN. Optional ST chart twins and
GRAPH adapters are excluded from the press canonical-source subset: native SCL
export omits their FB-reference access annotations and empty sections. Their
compilation and native GRAPH/LAD graph parity are checked separately. The new
Core services, device APIs and owning frames are included. No verifier rule
discards an access change. Native block export lookup now uses block kind,
including DBs authored inside SCL files. Only the exact native DTL vendor prefix
is normalized; access flags and other library versions remain significant.

Failed attempts are preserved. Native tests exposed missing busy-command abort
cleanup and a press warning from borrowing readonly config into an extracted
cyclic helper. Snapshot capture now sits at the generated frame boundary and
reads Core.Held directly. Fixture corrections start before withdrawing a Start
permit, accept immediate invalid-target faults, capture quiesce in the same
native call, and enable structural records after all fields are written.
A Unicode description write was refused by the Web API; the successful
first-out transport case uses 214 ASCII characters and does not qualify that
Unicode write boundary. The observed stop/restart recovery uses the existing
operator-reset/release paths; complete sequence freeze/resume policy and
profiling remain open.

During the pause Windows restarted (local boot 18:31). Historical keeper5380
was absent. Resume-TiaSimOwner restored the existing Fraktal store, addresses
and pinned certificate; new keeper **PID13476** has no expiry. User storage was
rejected on this cold restart, causing UsersReady=false/UsersLost=true and
login to fail closed. The bench's existing trusted provisioning operation
repaired its test-user document; login and verified durability recovered.
Routine STOP/RUN then passes the combined restore checks. This observation
does not establish abrupt VM-loss retention. No image, address or certificate
was recreated. Do not act on historical PIDs.

The approved candidate_structure_examples driver is unchanged:
SHA256 `ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74`.
No rebuild or new whitelist was required. Disk compression recovered room
without deleting prior projects or sealed evidence. The earlier editor Problems
diagnosis/workspace fix remains in the
[0.17 report](TIA_SEQUENCE_INTEGRATION_2026-10-14.md); HMI/.NET product code was
unchanged here, so their full suites were not repeated.

Current runtime:
`%LOCALAPPDATA%/Fraktal/TiaStations/Sequence_Diagnostics_Runtime_20261014/FrkS12/FrkS12.ap20`.
Offline press: `Sequence_Diagnostics_Press_Offline_20261014/FrkS12/FrkS12.ap20`
under the same station directory. Final normalization verifies both roots
MANUAL/READY/logged out, empty charts/Pending, no HELD/blocking alarm or
pending/failed config commit, LOAD_DB Restoring=false and valid test users.
Test stimuli are disabled; keeper13476 remains RUN on isolated TCPIP mappings0.

Next work is profiling and complete sequence freeze/resume policy, provider and
line config, module/HAL expansion and deployment acceptance. Physical press,
abrupt/torn loss, endurance, changed-layout/full-download and CARD_FILE/external
media gates remain separate.

[Raw archive](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_SEQUENCE_DIAGNOSTICS_2026-10-14/)
and [SHA256SUMS](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_SEQUENCE_DIAGNOSTICS_2026-10-14/SHA256SUMS)
bind sources, generated packages, native exports, successful/failed logs and
knowledge records. Engineering projects remain at their working locations.
