from pathlib import Path
import importlib.util,json,shutil
ROOT=Path(r'C:\Projects\Fraktal');WORK=Path(__file__).resolve().parent
subset=WORK/'services_readback_final'
subset.mkdir(exist_ok=False)
for p in (WORK/'candidate_05').iterdir():
    if p.suffix in ('.scl','.udt'):shutil.copy2(p,subset/p.name)
spec=importlib.util.spec_from_file_location('verify',ROOT/'FraktalCore/PLC/Siemens/Tests/Generator/verify_exports.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
result=module.verify(subset,WORK/'runtime_export_05')
(WORK/'18_services_readback.json').write_text(json.dumps(result,indent=2)+'\n',encoding='ascii')
print({n:len(rows) for n,rows in result.items()})
