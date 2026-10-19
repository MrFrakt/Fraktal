import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
TOOLS=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
OUT=Path(__file__).parent
sys.path.insert(0,str(TOOLS))
import fraktal_ab_generate as gen
import fraktal_ab_resource_demo as resource
import fraktal_ab_tower_demo as tower
import fraktal_ab_readback as readback
import fraktal_ab_sdk_log_gate as gate
source=OUT/'windows_01.L5X'
seed=Path('C:/work/echo38_5580_seed.L5X')
result=json.loads((OUT/'generation_01.json').read_text())
gen.generate(tower.application(),seed,OUT/'tower_baseline.L5X')
probe=TOOLS/'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
rows=[]
for label,target in [('echo','EchoController'),('physical','PhysicalController')]:
    output=OUT/(label+'_readback.L5X')
    run=subprocess.run([str(probe),'--build-readback',str(source),str(output),target],capture_output=True,timeout=240)
    (OUT/(label+'_build.log')).write_bytes(run.stdout+run.stderr)
    if run.returncode:
        raise RuntimeError(f'{label} native build failed: {run.returncode}')
    compared=readback.compare(source,output)
    with (OUT/(label+'_compare.json')).open('x',encoding='utf-8') as stream:
        json.dump(compared,stream,indent=2)
    if not compared['Equivalent']:
        raise RuntimeError(f'{label} actual readback differs')
    rows.append(dict(target=target,passed=True,comparison=compared))
with (OUT/'compiled.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest().upper(),rows=rows),stream,indent=2)
print(json.dumps(dict(passed=True,targets=len(rows),sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest().upper())))
