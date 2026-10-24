"""Restore only the approved five live documents after empty-controller recovery; no regression stimuli."""
import argparse,json,os,sys,subprocess
from pathlib import Path
from datetime import datetime,timezone
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--execute-restore',action='store_true')
parser.add_argument('--expect-serial',required=True,choices=('601FC87B',))
parser.add_argument('--credential-file',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
if not args.execute_restore or args.output.exists():parser.error('explicit arm and new evidence output required')
work=Path('C:/work/fraktal-ab-s2-20261021/prepare_3701f795c13b4329891f4eca1346b3a5')
a=json.loads((work/'authorization.json').read_text())
if not a['CurrentOwnerApproved'] or a['Serial']!=args.expect_serial or 'genealogy rollback' not in a['Scope']:raise SystemExit('current genealogy rollback authorization required')
subprocess.run([sys.executable,str(work/'scripts/guard_echo.py')],check=True)
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from pylogix import PLC
import fraktal_ab_part_execute as fixture
import fraktal_ab_projection as projection
import fraktal_ab_station as station
import fraktal_ab_mailbox as mb
import fraktal_ab_live as live
app=station.application()
account=next(a for a in json.loads(args.credential_file.read_text())['users'] if a['level']==4)
if account['user'] not in {u.name for u in app.access_users}:raise SystemExit('fixture account not declared')
report=dict(schema='fraktal.ab.genealogy-documents-only-recovery',serial=args.expect_serial,capturedUtc=datetime.now(timezone.utc).isoformat(),rows=[],passed=False)
prior=json.loads((work/'preflight.json').read_text())
medium=live.FileMedium(live.live_directory(app,args.expect_serial))
if {k:medium.read(k) for k in prior['documents']}!=prior['documents']:raise SystemExit('saved document medium changed since preflight')
with PLC('127.0.0.1') as native:
    native.ProcessorSlot=0;native.ConnectionSize=4000;native.SocketTimeout=5
    comm=fixture.Guarded(native,int(args.expect_serial,16),app);comm.guard()
    run=fixture.Run(comm,app,account,report)
    u=run.unit();access=projection.read_access(comm)
    if u['Mode']!=0 or any(u[k] for k in ('Running','Error','RunRequest','AbortRequest','ResetRequest')) or access['CurrentLevel']!=0:raise SystemExit('recovery requires MANUAL/idle and logged out')
    try:
        run.login();run.restore_configuration()
        report['passed']=True
    except Exception as error:
        report['error']=str(error)
        raise
    finally:
        try:
            if projection.read_access(comm)['CurrentLevel']!=0:run.command(mb.LOGOUT)
            report['loggedOut']=projection.read_access(comm)['CurrentLevel']==0
            report['passed']=report['passed'] and report['loggedOut']
        finally:
            with args.output.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
print(json.dumps(dict(passed=report['passed'],regressionRows=len(report['rows']),configuration=report.get('configuration'))))
raise SystemExit(0 if report['passed'] else 1)
