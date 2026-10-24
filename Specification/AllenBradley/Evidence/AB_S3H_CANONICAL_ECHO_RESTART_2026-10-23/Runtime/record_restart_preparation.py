from pathlib import Path
import datetime,hashlib,json
R=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
state=json.loads((R/'echo_full_inspect_restart_02.log').read_text())
assert state['SerialNumber']==0x601FC87B and state['ErrorCode']=='ClosedExternally'
assert state['Mode']=='RemoteProgram' and state['KeySwitch']=='Remote' and not state['IsFaulted']
assert json.loads((R/'echo_restart_selftest_02.log').read_text())==dict(Passed=True,AuthorizationCases=6,ControllerChanges=0)
pins=json.loads((R/'initial_source_verification.json').read_text())
for n,pin in pins['sha256'].items():assert sha(ROOT/n)==pin,n
assert not (R/'restart_authorization.json').exists() and not (R/'restart_attempt.json').exists()
name='AB_S3H_CANONICAL_ECHO_RESTART_PREPARATION_2026-10-23'
summary=f'''**Latest, 2026-10-23: Echo service is running; the virtual controller is
ClosedExternally.** Read-only SDK metadata identifies the exact 601FC87B /
127.0.0.1 / slot 0 / v38.011 controller, enabled, RemoteProgram, Remote,
not faulted. The emulator process and 44818 listener are absent. SDK loaded-
project/path strings are empty; that does not prove the persisted PLC image
is empty while the emulator is unavailable. No new controller change ran.

A separate one-shot disable/re-enable helper is prepared and compile-clean.
Six offline authorization cases pass. It verifies exact identity/GUID/firmware/
slot/Remote/not-faulted and the reviewed ClosedExternally/RemoteProgram state
immediately before use, and refuses if an emulator/listener appears. It changes
only IsEnabled false then true, through the public SDK. It does not download,
change keyswitch/mode, clear a fault or set a clock. This added restart needs
current explicit approval under AGENTS.md §3a; its approval template is false.
The original diagnostic approval remains recorded and unused. After restart,
normal identity/session/document guards run; an unverified baseline stops
before any diagnostic download. Read
[restart preparation](Evidence/{name}.md). S3h is incomplete; V2 stays inactive.

'''
for filename,anchor in (
 ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','## 2. State at hand-over (2026-10-20)\n\n'),
 ('AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','## Current continuation state (2026-10-20)\n\n')):
 p=AB/filename;t=p.read_text(encoding='utf-8');assert t.count(anchor)==1
 t=t.replace('**Latest, 2026-10-23: diagnostic approval is recorded; Echo service is stopped.**',
             '**Earlier diagnostic preflight: Echo service was stopped.**',1)
 p.write_text(t.replace(anchor,anchor+summary,1),encoding='utf-8')
p=AB/'AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md';t=p.read_text(encoding='utf-8')
t=t.replace('**Latest, 2026-10-23: diagnostic approval is recorded; Echo service is stopped.**',
            '**Earlier diagnostic preflight: Echo service was stopped.**',1)
p.write_text(t.replace('\n\n','\n\n'+summary,1),encoding='utf-8')
p=AB/'AB_FROZEN_CONTRACTS_V2.json';d=json.loads(p.read_text());assert not d['active']
d['approvedTraceabilityCorrection'].update(diagnosticBlockedByServiceStopped=False,
 diagnosticBlockedByClosedExternally=True,echoRestartPrepared=True,echoRestartAuthorized=False,
 echoRestartPreparationEvidence='Evidence/'+name+'.md')
p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
report=f'''# Echo ClosedExternally restart preparation — 2026-10-23

The owner reports Logix Echo running. The service is Running, but read-only
SDK metadata reports controller 601FC87B as ClosedExternally. No emulator
process or port 44818 listener exists. Diagnostic approval remains recorded
and unused. No new controller-changing operation has run.

| Read-only target observation | Value |
|---|---|
| Controller GUID | {state['ControllerGuid']} |
| Serial / address / slot | 601FC87B / 127.0.0.1 / 0 |
| Firmware | ControlLogix 5580 Emulator, 38.011 |
| Enabled / SDK error | true / ClosedExternally |
| Mode / keyswitch / fault | RemoteProgram / Remote / false |
| Emulator / CIP listener | Absent / absent |
| Loaded project / project path | Empty SDK strings; persisted-image content remains unknown until emulation is available |

The older inspection summary serialized the SDK mode as 2. Reflection of the
installed public SDK enum confirms 2 means RemoteProgram. A new read-only
metadata utility exposes enabled/error/project fields; it invokes ReadController
only. Its first build correctly stopped on Windows platform annotation CA1416;
targeting net10.0-windows fixes that build, with zero warnings/errors. The host
has the net10 reference pack, and this utility references the already installed
Echo SDK assemblies rather than downloading packages.

Prepared restart: a one-shot public SDK UpdateController with only IsEnabled
changed from true to false, then false to true. Before use it verifies exact
serial, GUID, address, slot, firmware 38.011, Remote keyswitch, no fault,
ClosedExternally/RemoteProgram/enabled state, and no emulator/listener. It
refuses if the target has recovered or changed. Each state-changing request
is preceded by a fresh SDK target check. If disable reports an error after
taking effect, the approved enable is completed only after exact-target checks;
there is no repeated disable or retry of an already requested enable. A one-shot
attempt file prevents an unreviewed repeat.

| Preparation gate | Result |
|---|---|
| Restart helper build | Pass, zero warnings/errors |
| Offline authorization tests | Six pass: current approval, restart permission, exact serial and fault/clock exclusions |
| Controller update requests executed | None |
| Restart approval / attempt file | Absent; false template only |
| Existing diagnostic image/sources | Unchanged; original diagnostic approval is separate and unused |

This restart is an additional controller power-state operation. It requires
current explicit authorization under AGENTS.md §3a; the diagnostic download
approval is not being reused for it. The restart performs no project download,
keyswitch/mode command, network edit, fault clear or clock set.

After a successful restart, read-only CIP identity/fault/keyswitch, MANUAL/idle,
HMI logout and five-document/policy checks must pass before resuming the
already approved diagnostic session. If the loaded baseline cannot be verified,
the workflow stops before any download. Empty SDK project strings alone never
authorize overwriting a controller. S3h remains incomplete; V2 stays inactive.
No commit or push.

Work folder: `{R.as_posix()}`. Helper source:
`EchoRestart/Program.cs`. Payload:
[manifest]({name}/manifest.json). Credentials and native ACD binaries are not
archived. Earlier stopped-service evidence remains sealed unchanged.
'''
with (AB/'Evidence'/(name+'.md')).open('x',encoding='utf-8') as f:f.write(report)
result=dict(passed=True,currentRestartApprovalPending=True,controllerChanges=0,
 helperSha256=sha(R/'EchoRestart/bin/Debug/net10.0-windows/EchoRestart.exe'),
 helperSourceSha256=sha(R/'EchoRestart/Program.cs'),target=state,
 originalDiagnosticApprovalConsumed=False,sourceBindingsUnchanged=159)
with (R/'restart_preparation_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
