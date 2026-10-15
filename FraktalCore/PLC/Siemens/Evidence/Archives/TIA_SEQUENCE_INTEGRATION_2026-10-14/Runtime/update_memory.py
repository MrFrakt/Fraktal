from pathlib import Path
import re
memory=Path(r'C:\Users\Siemens\.claude\projects\c--Projects-Fraktal\memory')
current='''
## Current continuation, 2026-10-14 (supersedes older owner/image pointers)

User resumed implementation and error checking; do not generate another handover.
Generator0.17 combines selected LOAD_DB and Core3.13 view. Actual quiesce withdraws
cursors/current work while preserving same-mode history; cold startup clears the
volatile chart. Native37+120 checks, native generic-HMI chart passed, HMI577/9
opt-in skips, tools184, consistency35, lint0, runtime/press both stages0/0,
GRAPH19AUTO/4HOME + LAD161networks/155calls, default24/press168 replay, MAIN3.
Startup path discovery/read gating and manifest compact/nested array joins were
fixed in shared HMI owners. No station UI glue or released Core layout changes.

Current runtime: %LOCALAPPDATA%/Fraktal/TiaStations/Sequence_Integration_Runtime_20261014/FrkS12/FrkS12.ap20
(selected LOAD_DB17docs). Separate offline press: Sequence_Integration_Press_Offline_20261014.
No physical press testing; earlier903 medium regressions not all repeated.
Persisted Fraktal was restored after the VM restart; current keeper5380 has no
expiry. Old12728 is unrelated: verify identity, do not stop it or keeper5380.
Fraktal RUN/CPU1516/TCPIP/169.254.212.49+192.168.1.1/maps0; roots MANUAL/READY/
loggedout/empty charts/no blocking alarm or pending/failed commit; Restoring=false.
Approved candidate_structure_examples/hash unchanged, use explicit --driver.

Workspace now selects Fraktal.TIA.sln and excludes archived HMI snapshots from
Dart analysis/discovery.15,809 of15,811 pasted Problems entries were archival;
active root-solution restore pulled absent AB SDK feed. Siemens solution0/0,
HMI analysis clean; reload editor for cached Problems. AB still needs its SDK.
Compression recovered disk space; no prior projects or sealed archives deleted.

Report/archive: C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_SEQUENCE_INTEGRATION_2026-10-14.md
KB sequence-restore-hmi-integration.md and SQLite search index updated (31 docs,
integrity ok, project/general tables unchanged). Next complete awaited diagnostic
walks/stall reporting/profiling, provider/line config, module/HAL and deployment.
Physical/torn/endurance/fullDL/card/external gates remain separate. Keep dirty
worktree; no commit/staging/push. Older sections below are dated history.

'''
p=memory/'MEMORY.md';old=p.read_text('utf-8');assert 'Current continuation, 2026-10-14' not in old
p.write_text(current.strip()+'\n\n'+old,encoding='utf-8')
p=memory/'project-siemens-port.md';old=p.read_text('utf-8');assert current.strip() not in old
old=re.sub(r'^description:.*$', 'description: "Fraktal/TIA current 2026-10-14: generator0.17 combined LOAD_DB/view, native generic HMI, restored keeper5380 and remaining port gates"',old,count=1,flags=re.M)
old=re.sub(r'^(  )?modified:.*$', '  modified: 2026-10-14T04:38:00Z',old,count=1,flags=re.M)
assert old.startswith('---\n');boundary=old.index('\n---\n',4)+len('\n---\n')
p.write_text(old[:boundary]+current+old[boundary:],encoding='utf-8')
print('Fraktal memory updated; historical records preserved')
