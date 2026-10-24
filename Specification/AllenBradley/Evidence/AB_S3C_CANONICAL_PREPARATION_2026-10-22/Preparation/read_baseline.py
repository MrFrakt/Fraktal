import os,sys,json,datetime
from pathlib import Path
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from pylogix import PLC
import fraktal_ab_press_execute as execute
import fraktal_ab_projection as projection
import fraktal_ab_station as station
app=station.application()
with PLC('127.0.0.1') as comm:
 comm.ProcessorSlot,comm.ConnectionSize,comm.SocketTimeout=0,4000,5
 unit=execute.read_unit(comm);access=projection.read_access(comm)
 if unit is None or access is None:raise ValueError('read-only context acquisition failed')
 result=dict(readOnly=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),declaredManualOrdinal=app.manual_mode,unit={key:unit[key] for key in ('Mode','Running','Error','Aborted','RunRequest','AbortRequest','ResetRequest')},currentLevel=access['CurrentLevel'])
 with (Path(__file__).parent/'baseline_state_01.json').open('x') as stream:json.dump(result,stream,indent=2)
 print(json.dumps(result))
