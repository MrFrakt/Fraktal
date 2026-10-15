import json
from pathlib import Path
import shutil
import sys

ROOT=Path(r'C:\Projects\Fraktal')
WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Siemens/tools'))
import fraktal_tia_generate as GEN
import fraktal_tia_declaration as DECL
import fraktal_tia_examples as EX
from fraktal_tia_program_layout import organize

default=ROOT/'FraktalCore/PLC/Siemens/Tests/Generator/generated'
press=ROOT/'FraktalCore/PLC/Siemens/Examples/PressDemo/generated'
old=json.loads((default/'manifest.json').read_bytes())
GEN.generate(DECL.validate(old['declaration']),WORK/'ship_default',old['shared_runtime'])
EX.generate(WORK/'ship_press_raw')
organize(WORK/'ship_press_raw',WORK/'ship_press',Path('${project}'),Path('${export}'))
shutil.copy2(WORK/'ship_press_raw/manifest.json',WORK/'ship_press/manifest.json')
plan=WORK/'ship_press/import.plan'
plan.write_bytes(plan.read_bytes().replace(str(WORK/'ship_press').encode('ascii'),str(press).encode('ascii')))
for target,ready,name in [(default,WORK/'ship_default','default'),(press,WORK/'ship_press','press')]:
    assert target.resolve().is_relative_to(ROOT.resolve())
    shutil.copytree(target,WORK/('previous_generated_'+name))
    # Same generated inventory: preserve non-source metadata while replacing
    # authored outputs. No deletion or move of workspace/user files.
    shutil.copytree(ready,target,dirs_exist_ok=True)
print(json.dumps({'default':GEN.verify(default),'press':EX.verify(press)}))
