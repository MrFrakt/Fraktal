from pathlib import Path
import hashlib,json,shutil
R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI';W=Path(__file__).parent
old=Path('C:/work/fraktal-ab-s4b-timing-20261027/offline_01/isolated_hmi_sources_02.json')
changed={H/p for p in ('packages/fraktal_opcua_client/lib/src/cip_read_plan.dart',
 'packages/fraktal_opcua_client/lib/src/cip_session_client.dart','test/opcua_freshness_test.dart')}
added={H/'test/cip_array_tiers_test.dart'}
rows=[];seen=set()
for row in json.loads(old.read_bytes())['files']:
    p=Path(row['source']);target=Path(row['copy']);digest=hashlib.sha256(p.read_bytes()).hexdigest()
    if digest!=row['sha256']:
        assert p in changed,p
        seen.add(p)
    shutil.copyfile(p,target)
    rows.append(dict(source=p.as_posix(),copy=target.as_posix(),sha256=digest,bytes=p.stat().st_size))
assert seen==changed
for p in added:
    target=Path('C:/work/fraktal-ab-s4b-20261025/hmi_verify_01')/p.relative_to(H)
    shutil.copyfile(p,target)
    rows.append(dict(source=p.as_posix(),copy=target.as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
with (W/'isolated_hmi_sources_01.json').open('x',encoding='utf-8') as f:json.dump(dict(passed=True,files=rows,changed=[p.as_posix() for p in sorted(changed)],added=[p.as_posix() for p in sorted(added)]),f,indent=2)
print(json.dumps(dict(files=len(rows),changed=len(changed),added=len(added))))
