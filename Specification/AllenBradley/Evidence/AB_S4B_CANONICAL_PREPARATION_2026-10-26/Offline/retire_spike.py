from pathlib import Path
import hashlib,json
root=Path('C:/Users/SoftIndVM/Fraktal').resolve()
hmi=root/'FraktalCore/HMI'
sources=sorted((hmi/'lib/data/cip').glob('*.dart'))
sources+=sorted(p for p in (hmi/'tool').glob('*.dart') if '../lib/data/cip/' in p.read_text(encoding='utf-8'))
assert len(sources)==17,len(sources)
archive=root/'Specification/AllenBradley/Evidence/AB_S4B_OFFLINE_2026-10-26/retired_spike'
rows=[]
for source in sources:
    assert source.resolve().is_relative_to(hmi.resolve())
    destination=archive/source.relative_to(hmi)
    destination.parent.mkdir(parents=True,exist_ok=True)
    data=source.read_bytes()
    with destination.open('xb') as out:out.write(data)
    assert destination.read_bytes()==data
    rows.append(dict(path=source.relative_to(root).as_posix(),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
with (archive/'manifest.json').open('x',encoding='utf-8') as out:
    json.dump(dict(scope='Retired HMI station-aware CIP spike and its one-off probes; source history only, not runnable acceptance tools.',artifacts=rows),out,indent=2)
for source in sources:source.unlink()
print(json.dumps(dict(retired=len(sources),archive=str(archive))))
