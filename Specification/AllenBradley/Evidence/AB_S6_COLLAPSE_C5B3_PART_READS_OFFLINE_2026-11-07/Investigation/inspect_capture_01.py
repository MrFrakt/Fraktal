from pathlib import Path
import gzip,json,hashlib
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
root=R/'Specification/AllenBradley/Evidence/AB_S6_HOST_SESSION_03_RUNTIME_2026-11-04/Session'
rows=[]
for path in root.rglob('*'):
 if not path.is_file() or path.name not in ('capture_canonical.json.gz','host_events_comparison.json','host_compare.json'):continue
 raw=path.read_bytes();data=json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)
 rows.append(dict(path=path.relative_to(R).as_posix(),sha256=hashlib.sha256(raw).hexdigest().upper(),keys=list(data),inner={k:list(v)[:14] for k,v in data.items() if isinstance(v,dict)}))
with (W/'capture_inventory_01.json').open('x',encoding='utf-8') as out:json.dump(rows,out,indent=2)
print(json.dumps(rows,indent=1))
