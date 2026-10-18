from pathlib import Path
import importlib.util,json,sys
repo=Path('C:/Projects/Fraktal');tia=repo/'FraktalCore/PLC/Siemens';sys.path.insert(0,str(tia/'tools'));w=Path(__file__).parent
spec=importlib.util.spec_from_file_location('owner',tia/'Tests/Line/verify_owner_exports.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
import fraktal_tia_io_bridge as bridge
out=w/'native05_controller_connect';result=v.verify(out/'sources',out/'native')
(out/'verified_private.json').write_text(json.dumps(result,indent=2)+'\n')
for name,text in bridge.build(False).items():
    if name=='30_PressDemoComposition.scl':continue
    assert (out/'sources'/name).read_bytes()==text.encode('ascii'),name
print({k:len(x) for k,x in result.items()})
