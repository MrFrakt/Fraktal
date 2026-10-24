"""Account for exactly one added initialization statement and ST line."""
from pathlib import Path
import copy,json,sys,xml.etree.ElementTree as ET
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_l5x_inventory as inventory
import fraktal_ab_readback as readback
W=Path(__file__).parent
old=Path('C:/work/fraktal-ab-s3f-20261022/prepare_3816927132f14d4998876bc62e22f342/genealogy_s3f_05.L5X')
new=W/'genealogy_s3f_revision_01.L5X';delta=readback.compare(old,new)
assert delta['SFC']['Equivalent'] and not delta['InitialValueDifferences'] and not delta['AlarmDifferences']
assert delta['ExecutableDifferences']==['FRK_PressProgram/FRK_Press_ScanCanonical']
a,b=inventory.inventory(old),inventory.inventory(new)
routine=b['Programs']['FRK_PressProgram']['routines']['FRK_Press_ScanCanonical']
prior=a['Programs']['FRK_PressProgram']['routines']['FRK_Press_ScanCanonical']
assert routine['lines']==prior['lines']+1
routine['lines']-=1
assert a==b,'unexpected non-code structural change'
ca,cb=readback.executable(ET.parse(old).getroot()),readback.executable(ET.parse(new).getroot())
key=('FRK_PressProgram','FRK_Press_ScanCanonical')
insert=readback.normalized('FRK_Press_CanonicalConfigWork.Initialized := 0;')
assert cb[key].count(insert)==ca[key].count(insert)+1
assert cb[key].replace(insert,'',1)==ca[key]
with (W/'source_delta_01.json').open('x') as f:json.dump(dict(passed=True,expectedDelta=True,changedBody='/'.join(key),
 addedStatement=insert,addedStLines=1,allOtherStructureInitialsAndCodeIdentical=True,comparison=delta),f,indent=2)
print(json.dumps(dict(passed=True,addedStLines=1,layoutAndInitialsUnchanged=True)))
