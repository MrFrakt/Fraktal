"""Read-only session settling; no login, logout or other tag write."""
import datetime,json,os,subprocess,sys,time
from pathlib import Path
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from pylogix import PLC
import fraktal_ab_projection as p
import fraktal_ab_press_execute as e
W=Path('C:/work/fraktal-ab-s3f-20261022/prepare_3816927132f14d4998876bc62e22f342')
subprocess.run([sys.executable,str(W/'scripts/guard_echo.py')],check=True)
with PLC('127.0.0.1') as c:
 c.ProcessorSlot,c.ConnectionSize,c.SocketTimeout=0,4000,5
 deadline=time.monotonic()+20
 while True:
  a=p.read_access(c)
  if a is None:raise ValueError('authority read failed')
  if not a['LoginBusy']:break
  if time.monotonic()>deadline:raise TimeoutError('bounded login remains busy')
  time.sleep(.1)
 u=e.read_unit(c)
 report=dict(readOnly=True,currentLevel=a['CurrentLevel'],loginBusy=a['LoginBusy'],loginFailed=a['LoginFailed'],
  unit={k:u[k] for k in ('Mode','Running','Error','Aborted')},capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 print(json.dumps(report))
 if a['CurrentLevel']!=0 or any(u[k] for k in ('Running','Error','Aborted')):raise ValueError('session is not idle/logged out')
