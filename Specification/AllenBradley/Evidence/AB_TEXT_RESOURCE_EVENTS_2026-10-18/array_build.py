from dataclasses import replace
import json, subprocess, sys
from pathlib import Path
root=Path('C:/Users/SoftIndVM/Fraktal')
tools=root/'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0,str(tools))
import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_readback as readback
import fraktal_ab_sdk_log_gate as gate
import fraktal_ab_text_resource_demo as text
out=Path(__file__).parent
app=text.application()
# Compiler-only array operand. TimLast is a real declared DINT array, not a
# resource source for a deployment. This image is never downloaded.
app=replace(app,chains=tuple(replace(chain,steps=tuple(replace(step,
    resource_value=decl.ResourceText(source='PressRam.TimLast')) if step.number==230 else step
    for step in chain.steps)) if chain.name=='AUTO' else chain for chain in app.chains))
source=out/'text_array_01.L5X'
result=gen.generate(app,Path('C:/work/echo38_5580_seed.L5X'),source)
(out/'array_generation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
probe=tools/'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
rows=[]
for label,target in [('array_echo','EchoController'),('array_physical','PhysicalController')]:
    export=out/(label+'_readback.L5X')
    run=subprocess.run([str(probe),'--build-readback',str(source),str(export),target],capture_output=True,timeout=240)
    (out/(label+'_build.log')).write_bytes(run.stdout+run.stderr)
    assert run.returncode==0,(label,run.returncode)
    comparison=readback.compare(source,export)
    audit=gate.audit_log((run.stdout+run.stderr).decode('utf-8',errors='replace'),('Build','Save As'),require_clean_import=True)
    assert comparison['Equivalent'] and audit['Clean'],(label,comparison,audit)
    (out/(label+'_compare.json')).write_text(json.dumps(comparison,indent=2)+'\n',encoding='utf-8')
    rows.append(dict(target=target,comparison=comparison,audit=audit))
(out/'array_compiled.json').write_text(json.dumps(dict(passed=True,rows=rows),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(arrayBuildsPassed=True,targets=len(rows))))
