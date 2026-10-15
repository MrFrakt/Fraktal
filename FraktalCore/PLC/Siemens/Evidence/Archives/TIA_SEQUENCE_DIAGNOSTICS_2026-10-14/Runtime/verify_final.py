import importlib.util,json,shutil,sys
from pathlib import Path
ROOT=Path(r'C:\Projects\Fraktal');WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Siemens/tools'))
import fraktal_tia_examples as EX
spec=importlib.util.spec_from_file_location('verify',ROOT/'FraktalCore/PLC/Siemens/Tests/Generator/verify_exports.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
result={}
for name,source in [('runtime','candidate_07'),('press','press_04')]:
    subset=WORK/(name+'_readback_verified');subset.mkdir(exist_ok=False)
    for p in (WORK/source).iterdir():
        if name=='press' and p.name.startswith(('23_00_FB_PressDemoLoadPosition','23_FB_PressDemoAuto','23_FB_PressDemoHome','28_')):continue
        if p.suffix in ('.scl','.udt'):shutil.copy2(p,subset/p.name)
    result[name]=module.verify(subset,WORK/(name+'_export_final'))
result['press_parity']=EX.verify(WORK/'press_04',WORK/'press_export_final')
(WORK/'32_native_readback_final.json').write_text(json.dumps(result,indent=2)+'\n',encoding='ascii')
print(json.dumps({name:{n:len(rows) for n,rows in r.items()} for name,r in result.items() if name!='press_parity'}))
print(json.dumps(result['press_parity']))
