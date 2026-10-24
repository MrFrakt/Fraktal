from pathlib import Path
import datetime,hashlib,json
R=Path(__file__).parent;P=R.parent/'diagnostic_0b74f072e0d74c7c97531e07dec70898'
t=(R/'candidate_then_restore.py').read_text()
with (R/'candidate_then_restore_before_guard_stop.py').open('x') as f:f.write(t)
for old,new in {
 "R/'backup_01_exit.json'":"R/'backup_02_exit.json'",
 "R/'backup_log_audit_01.log'":"R/'backup_log_audit_02.log'",
 "R/'backup_access_01.json'":"R/'backup_access_02.json'",
}.items():
 assert t.count(old)==1,(old,t.count(old));t=t.replace(old,new,1)
(R/'candidate_then_restore.py').write_text(t)
for name in ('echo_before_s3h.ACD','echo_before_s3h.L5X','backup.sha256','deploy_attempt.json'):
 assert not (P/name).exists(),name
exits={label:json.loads((R/(label+'_exit.json')).read_text())['exitCode']
 for label in ('guard_initial_01','manual_initial_01','preflight_initial_01','backup_01')}
assert all(exits.values())
report=dict(capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 serviceStatus='Stopped',listener44818=False,elevatedAdministrator=False,controllerChanges=0,
 backupHelperInvoked=True,backupUploadStarted=False,backupCreated=False,deploymentAttempted=False,
 preparationAcdSha256=hashlib.sha256((P/'s3h_canonical.ACD').read_bytes()).hexdigest().upper(),
 authorizationQuestion='call_b76d12f2f038411386f83c339fcd94e0:0',authorizationConsumed=False,
 failedRunsRetained=exits,
 orchestrationCorrection='Resume runner checks every subprocess return code before starting the next phase',
 ownerAction='Start-Service "FactoryTalk Logix Echo Service" in elevated PowerShell')
with (R/'preflight_service_stop_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report))
