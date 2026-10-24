from pathlib import Path
import json
R=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley'
v=json.loads((R/'restart_failure_01.json').read_text());assert v['restartApprovalConsumed'] and not v['diagnosticApprovalConsumed']
name='AB_S3H_CANONICAL_ECHO_RESTART_2026-10-23'
source='https://compatibility.rockwellautomation.com/GeneratedReleaseNote.aspx?v1=66077'
summary=f'''**Latest, 2026-10-23: authorized Echo restart failed during emulator startup.**
The one-shot approval `call_37bd66c3442340b08084fd7b2deb2ce5:0` was used:
IsEnabled false applied; re-enable was requested and the native emulator
exited with code 1. The service remains Running; controller 601FC87B remains
enabled/ClosedExternally, RemoteProgram/Remote, not faulted, with no CIP
listener. No PLC download, tag write, mode command, fault clear or clock
change ran. The original S3h diagnostic approval remains recorded and unused.

Fresh native crash metadata records 0xC0000005 in v38.011 libComms.dll at
offset 0x50C2A4, with exception parameters [0, 0]. The x86 frame chain stays
in libComms before runtime-library thread frames. Private vendor symbols are
unavailable; the underlying cause remains unconfirmed. Earlier service logs
also record an emulator shutdown timeout/forced close and the same startup
exit before this authorized attempt. Controller definitions/state files stay
in place. The full memory dump is not archived; only metadata/control-address
stack frames and selected logs are recorded.

Rockwell's Echo 4.00 release notes describe an initialization issue for which
a Windows-host reboot is recommended. That is a possible next recovery step;
ASLR is unconfirmed here. Read [restart result](Evidence/{name}.md).
S3h remains incomplete and V2 inactive; no further restart is authorized by
the consumed one-shot approval. No commit or push.

'''
for filename,anchor in (
 ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','## 2. State at hand-over (2026-10-20)\n\n'),
 ('AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','## Current continuation state (2026-10-20)\n\n')):
 p=AB/filename;t=p.read_text(encoding='utf-8');assert t.count(anchor)==1
 t=t.replace('**Latest, 2026-10-23: Echo service is running; the virtual controller is',
             '**Earlier restart preparation: the virtual controller was',1)
 p.write_text(t.replace(anchor,anchor+summary,1),encoding='utf-8')
p=AB/'AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md';t=p.read_text(encoding='utf-8')
t=t.replace('**Latest, 2026-10-23: Echo service is running; the virtual controller is',
            '**Earlier restart preparation: the virtual controller was',1)
p.write_text(t.replace('\n\n','\n\n'+summary,1),encoding='utf-8')
p=AB/'AB_FROZEN_CONTRACTS_V2.json';d=json.loads(p.read_text());assert not d['active']
d['approvedTraceabilityCorrection'].update(echoRestartPrepared=False,echoRestartAuthorized=False,
 echoRestartApprovalConsumed=True,echoRestartPassed=False,echoRestartEvidence='Evidence/'+name+'.md',
 diagnosticSessionApprovalConsumed=False,diagnosticNativeDownloadAttempted=False,
 diagnosticBlockedByEmulatorStartupCrash=True)
p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
report=f'''# Echo authorized restart and startup crash — 2026-10-23

**The authorized restart failed. S3h diagnostics have not run.** The owner
approved `call_37bd66c3442340b08084fd7b2deb2ce5:0`, “Approve guarded Echo
restart”, for exact virtual controller 601FC87B / 127.0.0.1 / slot 0 / v38.011.
The helper passed its fresh GUID/serial/firmware/slot/Remote/no-fault and
ClosedExternally/no-process/no-listener guards. It applied disable, then
requested enable once. The emulator exited with code 1 during enable, and
the SDK returned ServiceException. That one-shot approval is consumed.

| Outcome | Measured result |
|---|---|
| Power flag sequence | true → false → true; enable request reports emulator startup failure |
| Post-state | Enabled, ClosedExternally, RemoteProgram, Remote, not faulted |
| Service / port 44818 | Running / no listener |
| PLC downloads / tag writes / mode commands | 0 / 0 / 0 |
| Fault clears / clock changes | 0 / 0 |
| Original diagnostic session | Not started; approval b76d12f2… remains recorded and unused |
| Source pins | All 159 existing project and two diagnostic files unchanged |
| Controller definition / retained-state files | Preserved; no agent deletion or file modification |

The Windows Application events for EchoRestart.exe describe the SDK wrapper's
unhandled ServiceException (managed exception 0xE0434352). Separately, the
fresh native emulator dump records **0xC0000005 in libComms.dll**, v38.011
firmware package 979cf5b0-3243-581d-819c-2c9f87041c39, module offset
**0x50C2A4**, exception parameters [0, 0]. The x86 EBP-chain walk returns
libComms offsets 50C2A4, 53068B, 5306B4, 36BC94, 465761, 23DF2E and AB024,
followed by msvcrt/kernel32/ntdll thread frames. It is a frame-chain observation
without private symbols, not a full symbolized root-cause analysis. The DLL
has no named executable exports to refine those internal functions.

Service logs show that the earlier Windows shutdown timed out and forced the
emulator process closed. They also show startup exit code 1 when the service
first restarted, before this authorized attempt. The runtime pwrDown.dat is
43,164,904 bytes; its timestamps/hashes and related-state metadata are recorded.
These observations do not prove retained-state corruption. No raw state file
was reset, renamed or deleted, and no controller recreation was attempted.
The SDK's generic deletion suggestion was not acted on.

The 1,035,901,098-byte native dump remains in its original vendor folder.
It was not copied or archived. Only exception/module metadata and bounded
frame-chain control addresses were read and recorded; no global-memory or
stack-argument values are exported. No credential file is archived. The
metadata parser and frame-chain reader are included for review/reproduction.

Rockwell's [Echo 4.00 release notes]({source}) document an initialization
issue involving ASLR and recommend restarting the Windows host. A host reboot
is the next supported recovery step to consider; ASLR is unconfirmed in this
case. If it persists afterward, vendor diagnosis is needed before selecting
a state reset, controller recreation or firmware change. No such additional
operation is authorized by the completed one-shot restart approval.

The unchanged S3h C6 image, 79% Capacity and 2,149 AB / 74 root test evidence
remain bound. They do not establish current controller readiness. The native
baseline identity/session/documents cannot be verified while no controller is
listening, so the prepared diagnostic download stays blocked at its original
guards. Historical 39 successful comparisons and 31 baseline regressions remain
at their recorded scope; no new acceptance is claimed. V2 remains inactive.

Work folder: `{R.as_posix()}`. Payload:
[manifest]({name}/manifest.json). It retains all restart logs, metadata and
source hashes, and references the 36 prior immutable canonical records.
No commit or push.
'''
with (AB/'Evidence'/(name+'.md')).open('x',encoding='utf-8') as f:f.write(report)
with (R/'startup_references_01.json').open('x') as f:
 json.dump(dict(primarySource=source,title='FactoryTalk Logix Echo Single Node 4.00 release notes',
  relevantNote='ASLR may prevent initialization; vendor recommends restarting the Windows host',
  aslrConfirmedHere=False),f,indent=2)
print(json.dumps(dict(passed=True,restartPassed=False,restartApprovalConsumed=True,diagnosticApprovalConsumed=False)))
