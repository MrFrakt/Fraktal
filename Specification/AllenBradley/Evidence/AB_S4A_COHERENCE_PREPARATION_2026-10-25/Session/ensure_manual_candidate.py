"""Fixed MANUAL normalization only after current exact-image session authorization.

This corrects the inherited session scripts' wrong literal MANUAL ordinal.
The controller owns SET_MODE validation. No policy or simulation write exists.
"""
from pathlib import Path
import argparse,datetime,json,os,subprocess,sys
W=Path(__file__).parent
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_s4_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from pylogix import PLC
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_execute as px
import fraktal_ab_projection as projection
import fraktal_ab_manifest as manifest
import fraktal_ab_manifest_read as reader
import fraktal_ab_mailbox as mb
import fraktal_ab_station as station
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args()
if args.output.exists():parser.error('new evidence required')
approval=json.loads((W/'authorization.json').read_text())
if (approval.get('CurrentOwnerApproved') is not True or approval.get('Serial')!='601FC87B'
 or approval.get('CanonicalSha256')!=(W/'canonical.sha256').read_text().strip()
 or approval.get('ManualNormalizationAuthorized') is not True or approval.get('RestoreGenealogyAuthorized') is not True):
 raise SystemExit('current exact-artifact and MANUAL mailbox authorization required')
subprocess.run([sys.executable,str(W/'scripts/guard_echo.py')],check=True)
app=station.application()
if app.manual_mode!=px.MODE_MANUAL:raise ValueError('fixture/declaration MANUAL mismatch')
report=dict(readOnly=False,serial='601FC87B',declaredManualOrdinal=app.manual_mode,
 controllerWrites=0,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
try:
 with PLC('127.0.0.1') as native:
  native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,5
  comm=fixture.Guarded(native,0x601FC87B,app);comm.guard()
  raw,status,unused=reader._read_raw(comm,manifest.header_tag(app))
  if raw is None:raise ValueError('legacy header unavailable')
  header=reader.decode_header(raw)
  if header['ContentHash']!=manifest.content_hash(app) or header['ConfigRevision']!=manifest.config_revision(app):
   raise ValueError('exact S4a migration image required')
  unit=px.read_unit(comm);access=projection.read_access(comm)
  if unit is None or any(unit[k] for k in ('Running','Error','Aborted','RunRequest','AbortRequest','ResetRequest')):
   raise ValueError('only an already idle, unlatched Unit may be normalized')
  if access['CurrentLevel']!=0:raise ValueError('active operator session; logout guard retained')
  report['restoringBeforeRollback']=bool(projection.read_document(comm)['liveConfig'].restoring)
  report['beforeMode']=unit['Mode']
  if unit['Mode']!=app.manual_mode:
   account=next(a for a in json.loads(Path('C:/work/fraktal_echo38_access_fixture.json').read_text())['users'] if a['level']==4)
   if account['user'] not in {u.name for u in app.access_users}:raise ValueError('wrong fixture account')
   run=fixture.Run(comm,app,account,dict(rows=[],serial='601FC87B'))
   run.login()
   try:
    run.command(mb.SET_MODE,IntValue=app.manual_mode)
    run.wait(lambda:run.unit()['Mode']==app.manual_mode,'MANUAL normalization')
    report['controllerWrites']='existing LOGIN, SET_MODE(1), LOGOUT mailbox frames only'
   finally:run.command(mb.LOGOUT)
  after=px.read_unit(comm);access=projection.read_access(comm)
  report.update(afterMode=after['Mode'],currentLevel=access['CurrentLevel'],passed=after['Mode']==app.manual_mode and access['CurrentLevel']==0 and not any(after[k] for k in ('Running','Error','Aborted','RunRequest','AbortRequest','ResetRequest')))
except Exception as error:report.update(passed=False,error=f'{type(error).__name__}: {error}')
with args.output.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report))
raise SystemExit(0 if report['passed'] else 1)
