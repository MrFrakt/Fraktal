import importlib.util,json,shutil
from pathlib import Path
ROOT=Path(r'C:\Projects\Fraktal');w=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('verify',ROOT/'FraktalCore/PLC/Siemens/Tests/Generator/verify_exports.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
subset=w/'runtime_readback_qualified';subset.mkdir(exist_ok=False)
for p in (w/'candidate_08').iterdir():
    if p.suffix in ('.scl','.udt') or p.name=='08_GDB_SequenceQuiesceTest.db':shutil.copy2(p,subset/p.name)
result=m.verify(subset,w/'runtime_export_qualified')
(w/'41_runtime_readback_qualified.json').write_text(json.dumps(result,indent=2)+'\n',encoding='ascii')
print({n:len(v) for n,v in result.items()})
