from pathlib import Path
import csv,json,subprocess,time
D=Path(__file__).parent
ready=D/'cpu_probe_ready_01.json';stop=D/'cpu_probe_stop_01.json';output=D/'cpu_probe_01.csv'
with (D/'cpu_probe_01.log').open('x',encoding='utf-8') as log:
    process=subprocess.Popen(['powershell','-NoProfile','-NonInteractive','-File',str(D/'host_cpu_monitor.ps1'),
        '-OutFile',str(output),'-ReadyFile',str(ready),'-StopFile',str(stop)],stdout=log,stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        until=time.monotonic()+20
        while not ready.exists() and process.poll() is None and time.monotonic()<until:time.sleep(.1)
        assert ready.exists() and json.loads(ready.read_bytes())==dict(ready=True,readOnly=True),'CPU sampler readiness'
        time.sleep(2)
    finally:
        with stop.open('x') as f:json.dump(dict(stop=True),f)
        try:code=process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.terminate();process.wait(timeout=5);raise
assert code==0
rows=list(csv.DictReader(output.open(encoding='utf-8')))
assert any(r['kind']=='host' for r in rows)
assert any('emulatecontrollogix' in r['process'].lower() for r in rows),'actual Echo emulator process absent'
result=dict(passed=True,readOnly=True,controllerAccess=False,hostRows=sum(r['kind']=='host' for r in rows),
    emulatorRows=sum('emulatecontrollogix' in r['process'].lower() for r in rows),exitCode=code)
with (D/'cpu_sampler_check_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
