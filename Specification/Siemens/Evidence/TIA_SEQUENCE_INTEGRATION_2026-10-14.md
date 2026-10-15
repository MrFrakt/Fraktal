# Sequence restore and generic HMI integration, 2026-10-14

Generator 0.17 was qualified on TIA V20 / S7-PLCSIM Advanced V7, simulated
CPU1516 instance Fraktal. This continuation combines the selected LOAD_DB
consumers and Core 3.13 view. It does not declare the whole port complete.

The owning persistence quiesce path now withdraws all sequence cursors,
CurrentStep, elapsed and timeout publication. Running-state quiesce preserves
definitions, visited history and annotations. Cold startup clears the volatile
chart. Normal frames and quiesce use one generated publication map; projects
add no scheduling call. Core type layouts and enum ordinals are unchanged.

The live generic HMI qualification found and corrected two integration defects:

- Startup acquired the entire published tree before applying read tiers. The
  repository now obtains available path discovery and applies view gating before
  its first sample; the gateway uses the native discovery capability without
  requiring a full snapshot. Older clients keep their snapshot fallback.
- Siemens live rows use compact array paths while manifest entries use nested
  array paths. Manifest hydration now resolves metadata against discovered row
  containers. The shared parent index joins both forms without duplicating row
  state. Static-only arrays retain their original paths.

The production repository and generic chart render N42/N11, titles, live cursor,
75 ms elapsed / 50 ms guard, warning text/source path, and the PLC-owned 2 ms
fast-step history. History is absent before the consuming tab opens and present
after opening it. StationB remains isolated. The test uses synthetic view events
and commands no press plant. Its screenshot and row record are in the archive.

| Gate | Result |
|---|---|
| Combined LOAD_DB quiesce/restore/restart | 37/37 native checks |
| Sequence-view outcomes on that medium | 120/120 native checks |
| Live generic HMI chart | 1 opt-in test passed |
| HMI suite | 577 passed, 9 opt-in skips |
| HMI static analysis | No issues |
| Siemens tool suite | 184 passed |
| Cross-artifact suite | 35 passed |
| Siemens lint / repository consistency | 0 findings / 0 errors, 0 warnings |
| Selected Siemens .NET solution build | 0 errors, 0 warnings |
| Combined runtime native compile | 0 errors, 0 warnings |
| Separate wired press, both compile stages | 0 errors, 0 warnings |
| Native press readback | 19 AUTO + 4 HOME GRAPH steps; 161 LAD networks / 155 calls |
| Generated replay | 24 default / 168 press sources |

The 120 view checks include a variable number of manifest-page acknowledgements;
the earlier LOCAL_RETAIN fixture's 122 is a separate run. The previous 903
LOAD_DB consumer checks were not all rerun here. Failed attempts are preserved,
including a mistaken cold-history assertion, disk-full compiler/project-save
failures, the initial chart join failure and a startup snapshot timeout. The
successful native/UI run precedes only cast/comment/line-ending cleanup with
unchanged behavior; the final full HMI suite and analysis follow that cleanup.

The supplied Problems export contains 15,811 entries: 15,809 came from archived
HMI snapshots outside their package context. The active C# restore errors came
from the auto-selected root solution's separate Allen-Bradley probe and its
absent local Rockwell SDK feed. Workspace settings now select `Fraktal.TIA.sln`
and exclude historical evidence from Dart analysis/project discovery. Siemens
restore/build and current HMI analysis pass. Reload the editor window to discard
cached diagnostics. The Allen-Bradley probe still needs its installed SDK.

C: ran full during verification. Transparent compression recovered space without
changing source/evidence bytes. Automatic approval review rejected removal of
two failed compiler temporary directories; they were retained and compressed.
No existing engineering project or sealed archive was deleted.

Current runtime:
`%LOCALAPPDATA%/Fraktal/TiaStations/Sequence_Integration_Runtime_20261014/FrkS12/FrkS12.ap20`.
Current offline press: `Sequence_Integration_Press_Offline_20261014/FrkS12/FrkS12.ap20`
under the same station directory. The press remains offline: GRAPH/ST permissives
are wired, optional ST/LAD twins remain uninstantiated, MAIN remains three calls.

After the VM/session restart there was no registered owner; the persisted Fraktal
store remained. `Resume-TiaSimOwner.ps1` restored that store and exact isolated
identity. Keeper **PID5380** has no expiry. Historical PID12728 is now an unrelated
process; do not act on historical PIDs. No image/address/certificate was recreated.
The approved `candidate_structure_examples` driver was reused unchanged:
SHA256 `ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74`.
The separately built .NET validation binary was not used for engineering.

Final read verifies owner RUN, TCPIP,169.254.212.49/192.168.1.1, mappings zero.
Both roots are MANUAL/READY/logged out, with empty charts, no blocking alarm,
and no pending/failed config commit. Storage is LOAD_DB with Restoring=false;
stimuli and the owned test gateway are stopped. The simulator keeper remains.

Remaining work includes complete awaited diagnostic walks/stall reporting and
profiling, provider/line config facets, module/HAL expansion and deployment
acceptance. Physical press, abrupt/torn loss, endurance, changed-layout/full
download and CARD_FILE/external-media gates remain separate. No guarantees for
those follow from this simulator integration.

[Raw archive](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_SEQUENCE_INTEGRATION_2026-10-14/)
and [SHA256SUMS](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_SEQUENCE_INTEGRATION_2026-10-14/SHA256SUMS)
bind generated inputs, native exports/logs, source snapshots and HMI evidence.
Native engineering projects remain in their working locations; this archive
contains exported artifacts rather than another full project-cache copy.
