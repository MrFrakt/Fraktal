import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
OUT=Path(__file__).parent
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
from pylogix import PLC
import fraktal_ab_genealogy_demo as fixture
import fraktal_ab_host_events as host
import fraktal_ab_live as live
import fraktal_ab_part_execute as acceptance
import fraktal_ab_projection as projection
import fraktal_ab_tower_execute as tower

app=fixture.application()
prior=json.loads((OUT/'preflight.json').read_text())
gateway=json.loads((OUT/'gateway_restart.json').read_text())
checks={}
def check(name,value):
    checks[name]=bool(value)
    assert value,name
with PLC('127.0.0.1') as native:
    native.ProcessorSlot=0
    native.ConnectionSize=4000
    native.SocketTimeout=5
    comm=acceptance.Guarded(native,0x601FC87B,app)
    comm.guard()
    unit=acceptance.px.read_unit(comm)
    check('manual_idle',unit['Mode']==0 and not any(unit[key] for key in ('Running','Error','Aborted','RunRequest','AbortRequest','ResetRequest')))
    access=projection.read_access(comm)
    check('logged_out_and_original_policy',access['CurrentLevel']==0 and access['Required']==prior['originalPolicy'])
    check('no_active_lamp_test',not tower.snapshot(comm,app)['SignalTower/TestActive'])
    held=projection.read_document(comm)['liveConfig']
    check('not_restoring',not held.restoring)
    medium=live.FileMedium(live.live_directory(app,'601FC87B'))
    documents=live.documents(app,held,0)
    def values(doc):return [{key:value for key,value in row.items() if key!='rev'} for row in doc[1:]]
    for key,document in documents.items():
        check('medium_and_initial_values_'+key,values(medium.read(key))==values(document)==values(prior['documents'][key]))
    batch=host.read(comm,app,tuple(model.code for model in app.models))
    check('history_unchanged',batch['metadata']['NewestSequence']==gateway['rows'][0]['history']['Press/HostEvents/NewestSequence'])
run=subprocess.run(['C:/work/fraktal-echo-control-20261018/bin/Debug/net8.0-windows/EchoControl.exe','inspect'],capture_output=True,timeout=30)
check('echo_inspection_succeeded',run.returncode==0)
status=json.loads(run.stdout)
check('exact_echo_run_fault_free',status['ControllerGuid']=='91dec7d6-8ac3-45c9-ab2e-0d039c7006fd' and status['SerialNumber']==0x601FC87B and status['ControllerName']=='FraktalPhase0' and status['ControllerMode']==1 and status['IsFaulted'] is False)
with (OUT/'post_gateway_checks.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(passed=True,checks=checks,echo=status),stream,indent=2)
print(json.dumps(dict(passed=True,checks=len(checks))))
