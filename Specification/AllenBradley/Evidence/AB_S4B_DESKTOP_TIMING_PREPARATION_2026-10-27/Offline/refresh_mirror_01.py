from pathlib import Path
import hashlib,json,shutil
R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI';W=Path(__file__).parent
Q=Path('C:/work/fraktal-ab-s4b-partdiag-20261027/offline_01')
mirror=json.loads((Q/'isolated_hmi_sources_01.json').read_bytes())
changed={H/p for p in ('packages/fraktal_opcua_client/lib/src/cip_session_client.dart','lib/data/opcua_repository.dart','test/opcua_freshness_test.dart')}
seen=set()
for row in mirror['files']:
    p=Path(row['source']);target=Path(row['copy']);digest=hashlib.sha256(p.read_bytes()).hexdigest()
    if digest!=row['sha256']:
        assert p in changed,p
        seen.add(p)
    shutil.copyfile(p,target)
    row.update(sha256=digest,bytes=p.stat().st_size)
assert seen==changed and len(mirror['files'])==318
mirror.update(changed=[p.as_posix() for p in sorted(changed)],added=[])
with (W/'isolated_hmi_sources_01.json').open('x',encoding='utf-8') as f:json.dump(mirror,f,indent=2)
print(json.dumps(dict(passed=True,files=318,changed=len(changed),added=0)))
