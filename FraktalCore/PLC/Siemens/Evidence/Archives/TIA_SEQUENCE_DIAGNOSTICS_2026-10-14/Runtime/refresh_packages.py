import json,shutil,sys
from pathlib import Path
ROOT=Path(r'C:\Projects\Fraktal');WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Siemens/tools'))
import fraktal_tia_generate as GEN
import fraktal_tia_declaration as DECL
import fraktal_tia_examples as EX
from fraktal_tia_program_layout import organize
default=ROOT/'FraktalCore/PLC/Siemens/Tests/Generator/generated'
press=ROOT/'FraktalCore/PLC/Siemens/Examples/PressDemo/generated'
old=json.loads((default/'manifest.json').read_bytes())
GEN.generate(DECL.validate(old['declaration']),WORK/'ship_default_final',old['shared_runtime'])
EX.generate(WORK/'ship_press_raw_final')
organize(WORK/'ship_press_raw_final',WORK/'ship_press_final',Path('${project}'),Path('${export}'))
shutil.copy2(WORK/'ship_press_raw_final/manifest.json',WORK/'ship_press_final/manifest.json')
plan=WORK/'ship_press_final/import.plan'
plan.write_bytes(plan.read_bytes().replace(str(WORK/'ship_press_final').encode('ascii'),str(press).encode('ascii')))
for target,ready,name in [(default,WORK/'ship_default_final','default_intermediate'),(press,WORK/'ship_press_final','press_intermediate')]:
    assert target.resolve().is_relative_to(ROOT.resolve())
    shutil.copytree(target,WORK/('previous_generated_'+name))
    shutil.copytree(ready,target,dirs_exist_ok=True)
result={'default':GEN.verify(default),'press':EX.verify(press)}
(WORK/'31_shipped_replay_final.json').write_text(json.dumps(result,indent=2)+'\n',encoding='ascii')
print(json.dumps(result))
