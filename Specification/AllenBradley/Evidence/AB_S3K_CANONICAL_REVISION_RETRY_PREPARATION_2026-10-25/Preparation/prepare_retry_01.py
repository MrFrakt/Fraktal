"""Prepare an unapproved exact-image retry; never connect to a controller."""
from pathlib import Path
import hashlib,json
W=Path(__file__).parent;R=W.parent/'retry_revision_01';OLD=W.parent/'download_01'
S3J=Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
ROOT=Path('C:/Users/SoftIndVM/Fraktal');T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
capacity=json.loads((W/'capacity_auto_02.json').read_bytes());assert capacity['VerifiedFit']
pin=sha(W/'command_a_02.ACD');assert pin==capacity['CanonicalSha256']
assert not R.exists() or not any(R.iterdir());R.mkdir(exist_ok=True);(R/'scripts').mkdir();(R/'session').mkdir()
def write(p,b):
 with p.open('xb') as f:f.write(b)
for src,dest in [('command_a_02.ACD','s3k_command_a.ACD'),('s3k_command_a_02.L5X','s3k_command_a.L5X'),('run_logged.py','run_logged.py'),('audit_access.py','audit_access.py')]:
 write(R/dest,(W/src).read_bytes())
write(R/'canonical.sha256',(pin+'\n').encode())
write(R/'capacity_review.json',(W/'capacity_auto_02.json').read_bytes())
write(R/'canonical_prepared_compare.json',(W/'prepared_compare_02.log').read_bytes())
write(R/'scripts/guard_echo.py',(S3J/'scripts/guard_echo.py').read_bytes())
preflight=(S3J/'scripts/preflight.py').read_text().replace(str(S3J),str(R))
write(R/'scripts/preflight.py',preflight.encode())
cs=(OLD/'session/Program.cs').read_text()
cs=cs.replace(str(OLD),str(R)).replace(str(S3J/'scripts'),str(R/'scripts'))
old='if (fromBaseline) await Python(scripts+"/preflight.py","--verify-only");'
assert cs.count(old)==1
cs=cs.replace(old,old+'\n    else await Python(root+"/pre_restore_guard.py");')
write(R/'session/Program.cs',cs.encode());write(R/'session/S3kSession.csproj',(OLD/'session/S3kSession.csproj').read_bytes())
for name,source in [('ensure_manual_baseline.py','ensure_manual_baseline.py'),('ensure_manual_candidate.py','ensure_manual_rollback_03.py'),('pre_restore_guard.py','pre_restore_rollback_guard.py')]:
 s=(OLD/source).read_text().replace("restore_authorization.json","authorization.json")
 s=s.replace(str(S3J/'scripts/guard_echo.py'),str(R/'scripts/guard_echo.py'))
 write(R/name,s.encode())
authorization=dict(CurrentOwnerApproved=False,OwnerInstruction=None,Serial='601FC87B',CanonicalSha256=pin,
 SourceSha256=sha(R/'s3k_command_a.L5X'),DownloadAuthorized=False,BackupUploadAuthorized=False,
 MailboxOrTagWritesAuthorized=False,ManualNormalizationAuthorized=False,RestoreGenealogyAuthorized=False,
 BaselineRegressionWritesAuthorized=False,FaultClearAuthorized=False,ClockSetAuthorized=False,
 OwnerCapacityConfirmed={k:capacity[k] for k in ('UsedStandardBlocks','AvailableBlocks','TotalBlocks','DisplayedUsagePercent')},
 Scope='Fresh backup; guarded MANUAL normalization; Program/download/Run of the exact corrected S3k image; five-document restore, inherited 41 checks and prepared typed/collision vectors; read-only equivalence/acquisition/timing; pinned-copy genealogy rollback, five-document restore and 31 baseline checks; MANUAL cleanup/final checks/preflight. No fault clear, clock change, power or vendor-state operation.')
write(R/'authorization.template.json',(json.dumps(authorization,indent=2)+'\n').encode())
write(R/'genealogy.sha256',b'D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084\n')
record=dict(passed=True,controllerOperations=0,approved=False,session=str(R),canonicalSha256=pin,sourceSha256=sha(R/'s3k_command_a.L5X'))
write(W/'retry_prepared_01.json',(json.dumps(record,indent=2)+'\n').encode());print(json.dumps(record))
