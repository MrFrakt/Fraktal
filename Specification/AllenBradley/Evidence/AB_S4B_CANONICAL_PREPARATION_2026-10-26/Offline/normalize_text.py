from pathlib import Path
import json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal')
paths=subprocess.check_output(['git','diff','--name-only','--diff-filter=ACM','--','FraktalCore/HMI'],cwd=R,text=True).splitlines()
paths=[p for p in paths if p.endswith('.dart') and p!='FraktalCore/HMI/lib/ui/facet_cards.dart']
paths.append('Specification/AllenBradley/AB_FROZEN_CONTRACTS_V2.json')
rows=[]
for name in paths:
    path=R/name;raw=path.read_bytes();held=subprocess.check_output(['git','show','HEAD:'+name],cwd=R)
    normalized=raw.replace(b'\r\n',b'\n')
    if raw!=normalized:path.write_bytes(normalized)
    rows.append(dict(path=name,headCrLf=held.count(b'\r\n'),headLf=held.count(b'\n'),changed=raw!=normalized))
print(json.dumps(dict(passed=True,files=rows)))
