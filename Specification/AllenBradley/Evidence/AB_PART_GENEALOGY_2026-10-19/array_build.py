from dataclasses import replace
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path('C:/Users/SoftIndVM/Fraktal'); OUT=Path(__file__).parent
TOOLS=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'; sys.path.insert(0,str(TOOLS))
import fraktal_ab_genealogy_demo as fixture
import fraktal_ab_resources as resources
import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_readback as rb
import fraktal_ab_sdk_log_gate as gate
app=resources.without_text(fixture.application())
app=replace(app,chains=tuple(replace(chain,steps=tuple(replace(step,part_parents=(decl.AsciiSource(source='PressRam.TimLast'),)) if step.part_parents else step for step in chain.steps)) for chain in app.chains))
assert not decl.validate(app),decl.validate(app)
source=OUT/'genealogy_array_01.L5X'
result=gen.generate(app,Path('C:/work/echo38_5580_seed.L5X'),source)
(OUT/'array_generation.json').write_text(json.dumps(result,indent=2))
probe=TOOLS/'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
rows=[]
for label,target in [('echo','EchoController'),('physical','PhysicalController')]:
 output=OUT/f'array_{label}_readback.L5X'
 run=subprocess.run([str(probe),'--build-readback',str(source),str(output),target],capture_output=True,timeout=240)
 log=run.stdout+run.stderr;(OUT/f'array_{label}_build.log').write_bytes(log)
 assert run.returncode==0,(label,run.returncode)
 audit=gate.audit_log(log.decode(errors='replace'),('Build','Save As'),require_clean_import=True)
 assert audit['Clean'],audit
 compare=rb.compare(source,output);assert compare['Equivalent'],compare
 (OUT/f'array_{label}_compare.json').write_text(json.dumps(compare,indent=2))
 rows.append(dict(target=target,audit=audit))
(OUT/'array_compiled.json').write_text(json.dumps(dict(passed=True,rows=rows),indent=2))
print(json.dumps(dict(passed=True,compilerCases=len(rows))))
