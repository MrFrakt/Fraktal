from pathlib import Path
import datetime,hashlib,json
R=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal')
E=ROOT/'Specification/AllenBradley/Evidence/AB_S3H_CANONICAL_ECHO_RESTART_PREPARATION_2026-10-23'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((E/'manifest.json').read_text())
assert sha(E/'manifest.json')=='722328b7950bf61efcdae72e060cc033306eaa81f39d874fb180871297d9f547'
assert sha(E.parent/m['report'])==m['reportSha256']
assert sha(R/'EchoRestart/Program.cs')==m['helperSourceSha256']
assert sha(R/'EchoRestart/bin/Debug/net10.0-windows/EchoRestart.exe')==m['helperSha256']
assert not (R/'restart_attempt.json').exists()
approval=json.loads((R/'restart_authorization.template.json').read_text())
approval.update(CurrentOwnerApproved=True,RestartClosedExternallyAuthorized=True,
 ApprovalQuestion='call_37bd66c3442340b08084fd7b2deb2ce5:0',ApprovalAnswer='Approve guarded Echo restart',
 ApprovedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),PreparationManifestSha256=sha(E/'manifest.json'),
 HelperSourceSha256=m['helperSourceSha256'],HelperSha256=m['helperSha256'],
 HelperDllSha256=sha(R/'EchoRestart/bin/Debug/net10.0-windows/EchoRestart.dll'))
with (R/'restart_authorization.json').open('x') as f:json.dump(approval,f,indent=2)
print(json.dumps(dict(passed=True,approvalQuestion=approval['ApprovalQuestion'],controllerChanges=0)))
