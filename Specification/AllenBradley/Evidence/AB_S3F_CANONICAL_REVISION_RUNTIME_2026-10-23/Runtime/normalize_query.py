from pathlib import Path
import datetime,json,os,subprocess,sys
R=Path(__file__).parent;W=Path('C:/work/fraktal-ab-s3f-revision-20261023/prepare_c66f76a368304f6981b436dbf651e009')
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from pylogix import PLC
import fraktal_ab_part_execute as fixture
import fraktal_ab_projection as projection
import fraktal_ab_genealogy_demo as demo
import fraktal_ab_genealogy_s3f_demo as candidate
import fraktal_ab_s3f_fixture_execute as s3f
import fraktal_ab_canonical_reader as reader
import fraktal_ab_mailbox as mb
approval=json.loads((W/'authorization.json').read_text());assert approval['CurrentOwnerApproved'] and approval['ConfigurationVectorsAuthorized'] and approval['Serial']=='601FC87B'
subprocess.run([sys.executable,str(W/'scripts/guard_echo.py')],check=True)
with PLC('127.0.0.1') as native:
 native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,5
 app=demo.application();comm=fixture.Guarded(native,0x601FC87B,app);comm.guard()
 document,capture=reader.read_document(comm,expect_serial='601FC87B');assert capture['manifest']['contentHash']==s3f.expected_manifest(candidate.application())
 before=document['values']['Press/HmiResponse/ConfigPage/PageIndex'];access=projection.read_access(comm)
 assert access['CurrentLevel']==0 and not access['LoginBusy']
 account=next(u for u in json.loads(Path('C:/work/fraktal_echo38_access_fixture.json').read_text())['users'] if u['level']==4)
 run=fixture.Run(comm,app,account,dict(rows=[],serial='601FC87B'));unit=run.unit()
 assert unit['Mode']==1 and not any(unit[k] for k in ('Running','Error','Aborted','RunRequest','AbortRequest','ResetRequest'))
 run.login()
 try:run.command(mb.QUERY_CONFIG,IntValue=0,DurationMs=0)
 finally:run.command(mb.LOGOUT)
 document,capture=reader.read_document(comm,expect_serial='601FC87B');after=document['values']['Press/HmiResponse/ConfigPage/PageIndex'];assert after==0
 report=dict(passed=True,readOnly=False,commands=['LOGIN','QUERY_CONFIG(page=0,model=0)','LOGOUT'],beforePage=before,afterPage=after,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 with (R/'normalize_query_01.json').open('x') as f:json.dump(report,f,indent=2)
 print(json.dumps(report))
