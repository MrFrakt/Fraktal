"""Stop at the first failed dependency; delegate rollback to the sealed driver."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys
R=Path(__file__).parent;P=R.parent/'diagnostic_0b74f072e0d74c7c97531e07dec70898'
ROOT=Path('C:/Users/SoftIndVM/Fraktal');T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
PY=sys.executable;SDK=P/'session/bin/Debug/net8.0/win-x86/S3hSession.exe'
pins=json.loads((R/'initial_source_verification.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,pin in pins['sha256'].items():assert sha(ROOT/name)==pin,name
for name,pin in pins['diagnosticBindings'].items():assert sha(P/name)==pin,name
approval=json.loads((P/'authorization.json').read_text())
assert approval['CurrentOwnerApproved'] and approval['ReadTimingDiagnosticsAuthorized']
assert approval['ApprovalQuestion']=='call_b76d12f2f038411386f83c339fcd94e0:0'
assert sha(P/'s3h_canonical.ACD').upper()==pins['preparedAcdSha256']
stages=[];error=None
def run(label,*args):
 print(json.dumps(dict(stage=label,status='started')),flush=True)
 stages.append(label)
 # No later command can run after a refused guard or failed audit.
 subprocess.run([PY,str(R/'run_logged.py'),label,*map(str,args)],cwd=ROOT,check=True)
 print(json.dumps(dict(stage=label,status='finished')),flush=True)
try:
 run('guard_initial_02',PY,P/'scripts/guard_echo.py')
 run('manual_initial_02',PY,P/'ensure_manual.py','--output',R/'manual_initial_02.json')
 run('preflight_initial_02',PY,P/'scripts/preflight.py','--verify-only')
 run('backup_02',SDK,'backup')
 run('backup_log_audit_02',PY,T/'fraktal_ab_sdk_log_gate.py',R/'backup_02.log','--require','Save As')
 run('backup_access_02',PY,P/'audit_baseline_access.py',P/'echo_before_s3h.L5X','--output',R/'backup_access_02.json')
 run('session_01',PY,R/'candidate_then_restore.py')
except Exception as caught:error=f'{type(caught).__name__}: {caught}'
with (R/'resumption_execution_02.json').open('x') as f:
 json.dump(dict(passed=error is None,error=error,stagesStarted=stages,
  deploymentAttempted=(P/'deploy_attempt.json').exists(),capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat()),f,indent=2)
if error:print(error,file=sys.stderr)
raise SystemExit(0 if error is None else 1)
