from pathlib import Path
import re
memory=Path(r'C:\Users\Siemens\.claude\projects\c--Projects-Fraktal\memory')
current='''
## Latest diagnostic continuation, 2026-10-14

User resumed implementation; no new handover. Generator0.18 shared first-out,
named LOW Pending, longest awaited guards, HELD and generic busy-command release
are qualified. Native71+37+122, tools189, consistency35, lint0, runtime/press0/0,
runtime432/98 and press401/95 native source/interface subsets; GRAPH19AUTO/4HOME,
LAD161networks/155calls, default24/press172 replay, MAIN3. No HMI/.NET product edit.

Current runtime is %LOCALAPPDATA%/Fraktal/TiaStations/Sequence_Diagnostics_Runtime_20261014/FrkS12/FrkS12.ap20
(LOAD_DB17docs). Separate wired offline press is Sequence_Diagnostics_Press_Offline_20261014.
During the pause Windows restarted (local18:31). Existing persisted Fraktal was
restored without image/certificate/address recreation; current keeper13476 has
no expiry. Old5380/12728 are historical: verify process identity, never act on
those IDs. RUN/CPU1516/TCPIP/169.254.212.49+192.168.1.1/maps0. Roots normalized
MANUAL/READY/loggedout, empty charts/Pending, no HELD/blocking alarm/pending or
failed commit; Restoring=false, users valid, stimuli disabled. Preserve keeper.

Cold restart rejected the private user document and login failed closed. Existing
trusted bench provisioning repaired it; login/durability and routine STOP/RUN
passed afterward. Abrupt VM-loss retention remains unqualified. No prior project
or sealed evidence deleted; compression recovered disk. Approved driver/hash
unchanged; use explicit candidate_structure_examples --driver, no rebuild/whitelist.

Report: C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_SEQUENCE_DIAGNOSTICS_2026-10-14.md
KB shared-sequence-diagnostics.md is current; older notes below are history.
Next profiling/full freeze-resume policy, provider/line config, module/HAL and
deployment. Physical/torn/endurance/fullDL/card/external gates stay separate.
Keep dirty worktree unstaged; no commit/push. Workspace editor-error fix from
0.17 remains: Siemens solution selected, archived Dart snapshots excluded.

'''
p=memory/'MEMORY.md';old=p.read_text('utf-8');assert 'Latest diagnostic continuation' not in old
p.write_text(current.strip()+'\n\n'+old,encoding='utf-8')
p=memory/'project-siemens-port.md';old=p.read_text('utf-8');assert 'Latest diagnostic continuation' not in old
old=re.sub(r'^description:.*$', 'description: "Fraktal/TIA current 2026-10-14: generator0.18 sequence diagnostics, restored keeper13476 and remaining port gates"',old,count=1,flags=re.M)
old=re.sub(r'^(  )?modified:.*$', '  modified: 2026-10-14T17:46:00Z',old,count=1,flags=re.M)
boundary=old.index('\n---\n',4)+len('\n---\n')
p.write_text(old[:boundary]+current+old[boundary:],encoding='utf-8')
print('Current memory updated; dated history preserved')
