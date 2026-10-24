from pathlib import Path
import datetime,hashlib,json
R=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley'
v=json.loads((R/'preflight_service_stop_01.json').read_text())
assert v['controllerChanges']==0 and not v['authorizationConsumed'] and not v['deploymentAttempted']
name='AB_S3H_CANONICAL_DIAGNOSTIC_SERVICE_PREFLIGHT_2026-10-23'
summary=f'''**Latest, 2026-10-23: diagnostic approval is recorded; Echo service is stopped.**
The owner approved `call_b76d12f2f038411386f83c339fcd94e0:0`, “Approve this
guarded S3h diagnostic session”. The resumed service/identity guards refuse:
FactoryTalk Logix Echo Service is Stopped, there is no 44818 listener, and
this process is not an elevated Administrator. No upload, download, mode
change or tag write ran. The prepared C6 ACD and diagnostic source pins still
match; no deployment sentinel or backup artifact exists. Current approval
remains recorded and unused; it is not being requested again.

The initial command orchestration continued after the first failed guard.
The backup helper independently refused before upload; all four failed logs
are retained. The replacement runner checks each return code and stops before
starting the next dependent phase. Owner action is the handover's documented
elevated `Start-Service "FactoryTalk Logix Echo Service"`. Once service is
back, fresh exact-identity/fault/keyswitch/HMI-session/document guards run again.
Fault clears remain excluded. Read
[service preflight](Evidence/{name}.md). S3h/V2 acceptance is unchanged.

'''
for filename,anchor in (
 ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','## 2. State at hand-over (2026-10-20)\n\n'),
 ('AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','## Current continuation state (2026-10-20)\n\n')):
 p=AB/filename;t=p.read_text(encoding='utf-8');assert t.count(anchor)==1
 t=t.replace('**Latest, 2026-10-23: active-workload S3h diagnostic session prepared;',
             '**Earlier active-workload S3h diagnostic preparation;',1)
 p.write_text(t.replace(anchor,anchor+summary,1),encoding='utf-8')
p=AB/'AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md';t=p.read_text(encoding='utf-8')
t=t.replace('**Latest, 2026-10-23: active-workload S3h diagnostic session prepared;',
            '**Earlier active-workload S3h diagnostic preparation;',1)
p.write_text(t.replace('\n\n','\n\n'+summary,1),encoding='utf-8')
p=AB/'AB_FROZEN_CONTRACTS_V2.json';d=json.loads(p.read_text());assert not d['active']
d['approvedTraceabilityCorrection'].update(diagnosticSessionApprovalRecorded=True,
 diagnosticSessionApprovalQuestion=v['authorizationQuestion'],diagnosticNativeDownloadAttempted=False,
 diagnosticBlockedByServiceStopped=True,diagnosticSessionApprovalConsumed=False,
 diagnosticPreflightEvidence='Evidence/'+name+'.md')
p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
report=f'''# S3h diagnostic service preflight — 2026-10-23

The owner approved the prepared diagnostic session (`{v['authorizationQuestion']}`),
then requested resume after an interruption. No prior SDK/Python diagnostic
process was running and the one-shot workspace had no authorization, backup
or deployment artifacts. Approval is now bound to the sealed preparation;
all 159 project and two diagnostic source hashes match.

The fresh preflight stops because FactoryTalk Logix Echo Service is **Stopped**
and port 44818 has no listener. The current process is not an elevated
Administrator. The [handover](../AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md)
documents this boot-time issue and requires the owner to start the service in
an Administrator PowerShell:

```powershell
Start-Service "FactoryTalk Logix Echo Service"
```

| Check | Exact outcome |
|---|---|
| Prepared image | C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC unchanged |
| Initial service guard | Refused, exit 1 |
| MANUAL helper | Its internal service guard refused before writes, exit 1 |
| Document preflight | Exact local Echo identity unavailable, exit 1 |
| Backup helper | Its internal guard refused before upload, exit 3762504530 |
| Backup/restore/deployment artifacts | No new ACD, backup.sha256 or deploy_attempt.json |
| Controller-changing operations | None |
| Authorization | Recorded, not consumed; no second download approval requested |

The command orchestration should have stopped at the first nonzero guard.
The SDK helper failed closed independently. The replacement guarded runner
uses check=True for each subprocess and cannot start a later dependency after
a failed guard/audit. Failed logs and both orchestration versions remain in
the payload. Fresh identity/service/listener/fault/Remote/session/document
checks remain mandatory after restart. A fault clear is not authorized.

This report records the stopped-service observation at
`{v['capturedUtc']}`. It does not claim a current controller mode or final
readiness while Echo is offline. S3h remains incomplete and V2 inactive.
No commit or push. Work folder: `{R.as_posix()}`.
'''
with (AB/'Evidence'/(name+'.md')).open('x',encoding='utf-8') as f:f.write(report)
print(json.dumps(dict(passed=True,controllerChanges=0,authorizationConsumed=False,serviceStartPending=True)))
