"""Read-only service/listener and idle/login/restore baseline state."""
from pathlib import Path
import datetime,json,os,subprocess,sys,time
R=Path(__file__).parent
ROOT=Path('C:/Users/SoftIndVM/Fraktal');sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
from pylogix import PLC
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_execute as px
import fraktal_ab_projection as projection
import fraktal_ab_station as station
ps='$s=Get-Service -Name "FactoryTalk Logix Echo Service"; $c=Get-NetTCPConnection -State Listen -LocalAddress 127.0.0.1 -LocalPort 44818; $p=Get-Process -Id $c.OwningProcess; [pscustomobject]@{Service=$s.Name;ServiceStatus=$s.Status.ToString();ListenerAddress=$c.LocalAddress;ListenerPort=$c.LocalPort;Process=$p.ProcessName;ProcessId=$p.Id}|ConvertTo-Json -Compress'
response=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',ps],check=True,text=True,capture_output=True)
host=json.loads(response.stdout);assert host['ServiceStatus']=='Running' and host['Process']=='EmulateControlLogix5580'
app=station.application()
with PLC('127.0.0.1') as native:
    native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,5
    comm=fixture.Guarded(native,0x601FC87B,app);comm.guard()
    unit=px.read_unit(comm);access=projection.read_access(comm);held=projection.read_document(comm)['liveConfig']
    assert unit is not None
    idle=not any(unit[n] for n in ('Running','Error','Aborted','RunRequest','AbortRequest','ResetRequest'))
    result=dict(readOnly=True,serial='601FC87B',host=host,mode=unit['Mode'],manual=unit['Mode']==app.manual_mode,
        idle=idle,currentLevel=access['CurrentLevel'],restoring=held.restoring,
        capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    assert idle and access['CurrentLevel']==0 and not held.restoring,result
with (R/'baseline_inspection_01.json').open('x') as f:json.dump(result,f,indent=2)
dumps=Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root')
rows=[dict(path=p.relative_to(dumps).as_posix(),bytes=p.stat().st_size) for p in sorted(dumps.rglob('*.dmp'))]
with (R/'dumps_before_session_01.json').open('x') as f:json.dump(dict(readOnly=True,dumpFiles=rows),f,indent=2)
assert not rows,'Controller dump present; inspect before controller changes'
print(json.dumps(result))
