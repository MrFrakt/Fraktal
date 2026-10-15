"""Record qualified findings in the owner-authorized KB and project memory."""
from pathlib import Path
import json
work=Path(__file__).resolve().parent;g=json.loads((work/"29_gate_summary.json").read_bytes())
kb=Path("C:/Projects/SiemensAgent/siemens-kb/tia-automation")
text=f"""# Selected Unit manual alarm recovery - measured 2026-10-12

**[measured]** Generator 0.13 opts deployed Units into private LOCAL_RETAIN
ACTIVE/WAIT_RESET recovery through alarm_recovery.scopes, a subset of
alarm_history.scopes. The qualification selects StationA and StationA.Satellite;
StationB retains closed history with volatile active events. Only selected Units
allocate recovery images. The press selects PressDemo. Stored images/commissioning
markers are Retain; runtime readiness is NonRetain; native exports prove external
exclusion. Private reads/writes return 200 and published authority writes 205.

**[measured]** The composition prepares a conservative readiness fence before any
root runs. Frames restore before management and recursively block parent Start
while a selected descendant is unready. No application scheduling call is added.
Manual alarm latches survive; commands, step/control state, outputs and sessions
restart inactive. Captured gone faults enter WAIT_RESET without self-closing; a
fresh live explicit owner claims its restored occurrence once without duplicate
come. Explicit occurrences without a fresh owner witness remain ACTIVE. One
ordinary gated reset closes the latch and releases commands. A live cause is
re-raised by its owner; reset never erases the condition.

**[measured]** Whole-image validation covers schema, canonical scope, generation,
header/event checksums, event shape, elapsed checkpoints and authorized-close
journal. Cleared commissioned headers cannot become virgin storage. Invalid
active state rejects whole into one retained HIGH/SYSTEM/MANUAL_RESET loss event,
while preserving closed history and peers. The single prototype reason authority
is Framework/Core/alarm_recovery.json: code 11001, std.error.alarmRestoreLost.
This does not add a released Core enum member.

**[measured]** Duration sums observed controller-running intervals across restart,
excluding the unobserved outage. WAIT_RESET freezes Duration. Elapsed values use
short slot/event-bound checksums; event text is not hashed and lifecycle generation
is not incremented every timer scan. Saved monotonic epochs and unsynchronized
wall-clock subtraction are not used. This profile does not measure outage-inclusive
wall duration.

**[measured]** An authorized-close journal is committed before history append.
At startup, the exact closed record is appended if needed or recognized by
expected cursor/generation/checksum before removing the active latch. Forced
interruptions immediately before and after history commit yield one closed record
and no replayed sink callbacks. These two measured points do not qualify external
durable sink acknowledgement or arbitrary physical torn writes/power loss.

**[measured]** Native fixture lessons: startup injection must run in a routine
that actually receives Startup; its selection must be retained across restart.
Always guard slot bounds before array indexing: a test-only zero-index expression
stopped the CPU. STOP completion requires the fixture FinishCycle pulse. Await
the complete-forest retained StartupCount after RUN; the API mode response alone
does not prove restore finished. Do not hide retained test policy by reseeding:
normalize the access timeout/session between suites. An interrupted config test
changed the retained preset while an admin session was left by the set suite;
restore that test baseline through authenticated WRITE_CONFIG and logout.

**[measured]** {g['recovery']} new recovery checks and {g['native_assertions']} native assertions across
all successful suites; tools {g['tools']}, consistency {g['consistency']}, HMI {g['hmi']} with {g['hmi_skips']} opt-in skips.
Runtime and wired press compile with zero errors/warnings. The press replays
110 sources, GRAPH AUTO 19/HOME 4 and four optional LAD examples 161 networks/
155 calls. MAIN remains three calls. The press is compiled offline; physical
press acceptance and changed-layout/full-download retention are separate gates.

Current projects: Alarm_Recovery_Runtime_20261012/FrkS12/FrkS12.ap20 and
Alarm_Recovery_Press_Offline_20261012/FrkS12/FrkS12.ap20 under local TiaStations.
Owner Fraktal/CPU1516/TCPIP/RUN, 169.254.212.49 + 192.168.1.1, physical mappings 0.
Keeper PID 12728 remains in Access_Persistence_20261012, without expiry/unregister
cleanup. Preserve it. The whitelisted candidate_structure_examples driver is
unchanged, SHA256 ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74;
pass --driver explicitly. DPAPI credentials remain private.

Evidence: C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_ALARM_RECOVERY_2026-10-12.md.
The separate immutable archive preserves interrupted attempts, successful logs,
source snapshots and SHA256SUMS. Previous dated records remain unchanged.
Next work: durable event delivery/acknowledgement and selected persistence media,
then remaining sequence frontier, config/provider and module scope.
"""
p=kb/"manual-alarm-recovery.md";assert not p.exists();p.write_text(text,encoding="utf-8",newline="\n")
p=kb/"INDEX.md";s=p.read_text(encoding="utf-8")
anchor="| `program-groups-and-press-examples.md` |";assert s.count(anchor)==1
row="| `manual-alarm-recovery.md` | Selected ACTIVE/WAIT_RESET recovery, observed duration, startup fencing, interrupted-close journal and native qualification |\n"
s=s.replace(anchor,row+anchor);p.write_text(s,encoding="utf-8",newline="\n")
memory=Path("C:/Users/Siemens/.claude/projects/c--Projects-Fraktal/memory")
p=memory/"MEMORY.md";s=p.read_text(encoding="utf-8")
latest=f"""- Latest Siemens state (2026-10-12): generator 0.13 selected manual-reset alarm
  recovery; {g['recovery']} new checks/{g['native_assertions']} native assertions, tools {g['tools']}/consistency {g['consistency']},
  HMI {g['hmi']} with {g['hmi_skips']} opt-in skips, native runtime/press compile 0/0. Current image
  Alarm_Recovery_Runtime_20261012; offline press Alarm_Recovery_Press_Offline_20261012,
  110 sources, wired GRAPH AUTO 19/HOME 4 + ST permissives, MAIN three calls.
  ACTIVE/WAIT_RESET manual latches retained only for selected Units; commands,
  outputs, step/control state and sessions remain volatile. Duration excludes
  unobserved outage. Prototype reason 11001 declared in alarm_recovery.json.
  Owner Fraktal RUN, keeper PID 12728 stays in previous Access_Persistence work dir;
  preserve owner/keeper. Approved candidate_structure_examples unchanged.
  Latest report/archive TIA_ALARM_RECOVERY_2026-10-12; next durable sink/media.

"""
p.write_text(latest+s,encoding="utf-8",newline="\n")
p=memory/"project-siemens-port.md";s=p.read_text(encoding="utf-8")
s+=f"""

## 2026-10-12 continuation: generator 0.13 manual alarm recovery

Supersedes current-image/next-slice notes above, preserving dated evidence.
Optional alarm_recovery.scopes must be distinct history-selected Unit identities.
Private versioned active images/commissioning markers are LOCAL_RETAIN; runtime
readiness is volatile. Selected fixture Units StationA/StationA.Satellite, peer
StationB active volatile, press PressDemo selected. Composition fences descendants
before roots; frame restores before mailbox. No project correctness call added.
Only manual ACTIVE/WAIT_RESET latches survive: commands, outputs, steps/control
state and sessions reset. Fresh faults reconcile gone to WAIT_RESET; an explicit
live owner reclaims once without duplicate come. One ordinary gated reset closes
the latch and releases child commands; live conditions re-raise.

Duration sums observed running intervals, excludes outage and freezes WAIT_RESET.
Short event/slot-bound timing CRC avoids event text hashing/generation per scan.
Close journal qualifies interrupted before/after-history commit exactly once,
without callback replay. Bad active image rejects whole into retained HIGH/SYSTEM
MANUAL_RESET loss reason 11001, declared once in alarm_recovery.json, independent
of released Core enum. Closed history layout unchanged and peer isolated.
Not arbitrary physical torn writes, durable external sink acknowledgement,
changed-layout/full-download or physical press acceptance.

{g['recovery']} new checks/{g['native_assertions']} successful native assertions; tools {g['tools']}/consistency {g['consistency']},
HMI {g['hmi']}/{g['hmi_skips']} opt-in skips; runtime and offline wired press native 0/0.
110-source press replay/native GRAPH 19/4 and LAD 161 networks/155 calls unchanged,
MAIN three calls. Current projects Alarm_Recovery_Runtime_20261012 and
Alarm_Recovery_Press_Offline_20261012 under local TiaStations/FrkS12.

Raw failed fixture attempts preserved: Startup hook in wrong provisioning routine,
unchecked slot 0 stopped CPU, nonretained damage selector disappeared, Stop needed
FinishCycle. Final bounds/injection/retained selector corrected and native-qualified.
Regression setup must explicitly normalize retained timeout/session. A set suite
left admin logged in; a failed config run then wrote preset 90. Restore baseline
through normal authenticated mailbox, logout and rerun; never relax access gates.

Fraktal owner CPU1516/TCPIP/169.254.212.49+192.168.1.1/maps 0 remains RUN;
keeper PID 12728 remains prior Access_Persistence work dir. Do not stop/unregister
or create its stop file. Same candidate_structure_examples driver ba24e6aa...;
exact --driver, no rebuild/new whitelist. Report and separate immutable archive
TIA_ALARM_RECOVERY_2026-10-12 with byte hashes; previous archives unchanged.
KB manual-alarm-recovery.md records measured findings. Next durable event sink/
selected media, then remaining sequence frontier/config/provider/module scope.
"""
p.write_text(s,encoding="utf-8",newline="\n")
print("Updated authorized Siemens KB/index and project memory.")
