import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path('FraktalCore/PLC/Allen-Bradley/tools').resolve()))
from pylogix import PLC
import fraktal_ab_generate as gen
import fraktal_ab_host_events as host
import fraktal_ab_live as live
import fraktal_ab_part as part
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_execute as px
import fraktal_ab_projection as projection
import fraktal_ab_tower_demo as tower
import fraktal_ab_tower_execute as acceptance

app=tower.application()
output=Path('C:/work/fraktal-ab-alarm-runtime-20261018/before_download_read.json')
assert not output.exists()
with PLC('127.0.0.1') as native:
    native.ProcessorSlot=0
    native.ConnectionSize=4000
    comm=fixture.Guarded(native,0x601FC87B,app)
    comm.guard()
    before=px.read_scalar(comm,'FRK_Press_ScanCount')
    doc=projection.read_document(comm)
    unit=px.read_unit(comm)
    held=doc['liveConfig']
    medium=live.FileMedium(live.live_directory(app,'601FC87B'))
    matches={k:live.content(medium.read(k))==live.content(v) for k,v in live.documents(app,held,0).items()}
    probe=px.read_layout(comm,gen.health_probe_tag(app),gen.health_probe_members())
    access=projection.read_access(comm)
    stimuli={t:px.read_scalar(comm,t) for t in gen.externally_writable(app)}
    v=dict(serial='601FC87B',manifestHash=doc['contentHash'],projectionPaths=len(doc['values']),
        scanBefore=before,scanAfter=px.read_scalar(comm,'FRK_Press_ScanCount'),
        unit={k:unit[k] for k in ('Mode','Running','Error','ErrorID','Aborted','GoodCount','ScrapCount','CycleCount')},
        tower=acceptance.snapshot(comm,app),accessLevel=access['CurrentLevel'],required=access['Required'],
        inputs=stimuli,orderFail=px.read_scalar(comm,'FRK_Press_OrderFail'),
        probe={k:probe[k] for k in ('MajorFaultBits','MinorFaultBits','TaskMaxScanUs','TimeIsSynchronized')},
        partPresent=bool(part.read(comm,app)['Present']),host=host.read(comm,app,[m.code for m in app.models])['metadata'],
        persist=projection.read_persist(comm),configurationReopen=matches)
    assert all(matches.values()) and not held.restoring
    assert unit['Running']==unit['Error']==unit['Aborted']==v['orderFail']==0
    assert access['CurrentLevel']==0 and not any(access['Required']) and not any(stimuli.values())
    assert not v['tower']['SignalTower/TestActive'] and v['scanAfter']>v['scanBefore']
    assert not probe['MajorFaultBits'] and not probe['MinorFaultBits']
    v['echo']=json.loads(subprocess.check_output(['C:/work/fraktal-echo-control-20261018/bin/Debug/net8.0-windows/EchoControl.exe','inspect'],text=True))
    assert not v['echo']['IsFaulted']
    v['backupSha256']=hashlib.sha256(output.with_name('echo_before_alarm.ACD').read_bytes()).hexdigest().upper()
    v['preparedAcdSha256']=hashlib.sha256(output.with_name('alarm_02.ACD').read_bytes()).hexdigest().upper()
output.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
print(json.dumps(v,indent=2))
