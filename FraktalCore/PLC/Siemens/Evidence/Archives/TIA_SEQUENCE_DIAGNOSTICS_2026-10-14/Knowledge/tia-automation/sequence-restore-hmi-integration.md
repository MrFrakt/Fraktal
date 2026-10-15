# Sequence restore and native generic HMI integration, 2026-10-14

[measured] Fraktal generator0.17 combines selected LOAD_DB consumers and the
Core3.13 sequence view on V20 / Advanced7 / CPU1516. Actual running quiesce
withdraws all cursors, CurrentStep, elapsed and timeout, while keeping row
definitions/history/notes. Cold startup clears the volatile chart. Normal and
quiescent publication use one mirror map; no application scheduling call.

[measured] The production generic HMI path found two integration defects.
Full-tree startup acquisition could exceed the gateway's five-second request
deadline. Path-capable discovery and repository tiering now precede the first
sample, preserving the snapshot fallback for older clients. Compact Siemens
array paths (SequenceSteps[1]) differed from nested manifest paths
(SequenceSteps/SequenceSteps[1]): history hydration made rows lose their step
numbers. Metadata now resolves against discovered row containers, sharing the
parent index with the mapper. Never infer an undiscovered compact array shape.

[measured] The opt-in native HMI test renders N42/N11, static titles, live cursor,
75ms elapsed/50ms guard, warning/source link, and PLC-owned 2ms fast history.
History is absent before opening the consuming tab and present afterward.
The fixture is synthetic, not a physical press. Medium/restore37 and view120
native checks pass; variable manifest-page acknowledgements explain why the
older separate LOCAL_RETAIN run reported122. Earlier903 medium regressions
were not all repeated. Full HMI577 pass/9 opt-in skips; analysis clean; tools184,
consistency35, shipped replay/lint clean. Runtime0/0; separate press both stages
0/0 and native GRAPH19AUTO/4HOME, LAD161networks/155calls, MAIN3. Generator default
replays24 sources and wired press168. Released Core layouts/ordinals unchanged.

[measured] Current projects, under %LOCALAPPDATA%/Fraktal/TiaStations:
Sequence_Integration_Runtime_20261014/FrkS12/FrkS12.ap20 (selected LOAD_DB17docs),
Sequence_Integration_Press_Offline_20261014/FrkS12/FrkS12.ap20 (offline wired press).
After the VM restart the registration was absent but persisted Fraktal storage
existed. Resume-TiaSimOwner.ps1 restored that store without image/certificate/
address recreation. Current keeper5380 has no expiry; historical12728 is now
an unrelated process. Verify process identity, never act on a historical PID.
Final Fraktal RUN/TCPIP/169.254.212.49+192.168.1.1/maps0; both roots
MANUAL/READY/loggedout/empty charts/no blocking alarm/pending/failed commit;
Restoring=false and test stimuli/gateway stopped. Preserve keeper5380.

[measured] The supplied Problems export had15,811 entries,15,809 from historical
HMI snapshot packages. Active C# restore errors came from the unrelated AB SDK
feed absent on this host. Workspace now selects Fraktal.TIA.sln and excludes
evidence snapshots from Dart analysis/discovery. Selected .NET restore/build0/0
and current HMI analysis pass; editor reload clears cached diagnostics. The AB
probe still requires its installed SDK. Disk-full verification attempts were
preserved; transparent compression recovered space, with no prior projects or
sealed evidence deleted.

Approved candidate_structure_examples executable/hash stayed unchanged:
ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74.
A separate binary validated the selected solution build and was not used for
Openness. Continue using the approved binary; do not trigger another whitelist
round for ordinary generator/SCL changes.

Remaining: complete awaited diagnostic walks/stall reporting/profiling,
provider/line config facets, module/HAL expansion and deployment acceptance.
Physical press, torn/abrupt loss/endurance, changed-layout/full-download and
CARD_FILE/external-media gates remain separate. User resumed implementation;
no new handover prompt requested.

[Dated report and evidence](C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_SEQUENCE_INTEGRATION_2026-10-14.md).
