from pathlib import Path
import json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
p=R/'Specification/AllenBradley/Evidence/AB_S6_HOST_SESSION_03_RUNTIME_2026-11-04/Session/capture_legacy.json'
d=json.loads(p.read_bytes())
result=dict(keys=list(d),inner={k:list(v)[:22] for k,v in d.items() if isinstance(v,dict)})
with (W/'legacy_inventory_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
