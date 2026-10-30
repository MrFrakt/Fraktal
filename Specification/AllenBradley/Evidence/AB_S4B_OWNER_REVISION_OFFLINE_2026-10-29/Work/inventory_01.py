from pathlib import Path
import json,sys
R=Path('C:/Users/SoftIndVM/Fraktal');sys.path.insert(0,str(R/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_genealogy_s4b_owner_demo as demo
import fraktal_ab_owner_read_bindings as owner
app=demo.application();rows=owner.rows(app)
value=dict(ownerRows=rows,headerPaths=sum(len(json.loads(r['MembersJson'])) for r in rows),
 moduleCount=len(owner.module_paths(app)),configurationViews=sum(r['MembersJson']=='[]' for r in rows))
with (Path(__file__).parent/'inventory_01.json').open('x') as f:json.dump(value,f,indent=2)
print(json.dumps(value))
