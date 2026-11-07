from pathlib import Path
import json,sys
R=Path('C:/Users/SoftIndVM/Fraktal');sys.path.insert(0,str(R/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_schema_identity as s
W=Path(__file__).parent;old=Path('C:/work/fraktal-ab-c5-control-20261106/prepare_03/press.L5X');new=W/'prepare_01/press.L5X'
a,b=s.surface(old),s.surface(new);diff=s.differences(a,b)
with (W/'surface_diff_01.json').open('x',encoding='utf-8') as f:json.dump([dict(path=p,change=c) for p,c in diff],f,indent=2)
for p,c in diff:print(c,p)
