from pathlib import Path
import shutil
root=Path('C:/Projects/Fraktal/FraktalCore/PLC/Siemens')
for source,target in [(root/'Framework/Modules'/n,root/'Framework/Modules/ControlModules/Cylinder'/n)
                      for n in ('cylinder.json','cylinder_logic.scl.in','cylinder_api.scl.in')]+[
                     (root/'Examples/PressDemo/press.json',root/'Examples/PressDemo/01_PneumaticPress/press.json')]:
    assert source.resolve().is_relative_to(root) and target.resolve().is_relative_to(root)
    assert source.is_file() and not target.exists()
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.move(str(source),str(target))
print('Aligned authored module and process sources with the TIA groups')
