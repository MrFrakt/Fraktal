import json, os, sys, time
from pathlib import Path
out=Path(__file__).parent
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_resource_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from pylogix import PLC
import fraktal_ab_task_window_probe as probe
import fraktal_ab_observer_fixture as shared
import fraktal_ab_part_execute as fixture
import fraktal_ab_resource_demo as resource
with PLC('127.0.0.1') as native:
    native.ProcessorSlot=0
    native.ConnectionSize=4000
    native.SocketTimeout=5
    comm=fixture.Guarded(native,0x601FC87B,resource.application())
    comm.guard()
    value=shared.sample(comm,probe.TAG,probe.decode)
    observation=probe.assess(value)
    time.sleep(.25)
    comm.guard()
    stable=shared.sample(comm,probe.TAG,probe.decode)==value
    assert stable and not observation['faultsObserved'] and not observation['overlapChanged']
result=dict(schema='fraktal.ab.task-window-observation',version=1,serial='601FC87B',
    completed=True,collectorControllerWrites=0,stableCompletedRecord=stable,
    values=value,observations=observation)
with (out/'observation_01.json').open('x',encoding='utf-8') as stream:
    json.dump(result,stream,indent=2)
print(json.dumps(observation))
