import sys
sys.path.pop(0)
from pathlib import Path
import gzip,hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
exact={
 'FraktalCore/PLC/Allen-Bradley/README.md',
 'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
 'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S5_WRITE_REVISION_CORRECTION_2026-10-30.md',
 'Specification/Guides/AB_NEW_PROJECT_GUIDE.md','Specification/Guides/WEB_HMI_GATEWAY_DEPLOYMENT.md','Specification/OPCUA_TRANSPORT.md',
 *('FraktalCore/PLC/Allen-Bradley/tools/'+name for name in (
    'fraktal_ab_canonical_config.py','fraktal_ab_config_read_view.py',
    'fraktal_ab_s3f_equivalence.py','fraktal_ab_s4b_equivalence.py',
    'test_fraktal_ab_canonical_config.py','test_fraktal_ab_config_read_view.py'))}
raw=subprocess.check_output(['git','status','--porcelain','-z','--untracked-files=all'],cwd=R).decode('utf-8')
paths=[];outside=[]
for row in raw.split('\0'):
    if not row:continue
    assert row[:2] in (' M','??','M ','A '),row[:2]
    name=row[3:]
    if name in exact or name.startswith(('FraktalCore/HMI/','Specification/AllenBradley/Evidence/AB_S5_')):paths.append(name)
    else:outside.append(name)
pins=[u['pin'].encode() for u in json.loads(Path('C:/work/fraktal_echo38_access_fixture.json').read_bytes())['users']]
hashes={};sizes=[];decompressed=0
for name in paths:
    source=R/name
    assert source.is_file() and not source.is_symlink(),name
    assert source.suffix.lower() not in {'.exe','.dll','.pdb','.acd','.l5x','.bak','.pyc'},name
    assert not set(source.parts)&{'.dart_tool','__pycache__','browser_profile','build','obj'},name
    assert 'credential' not in source.name.lower(),name
    data=source.read_bytes();sizes.append((len(data),name))
    assert len(data)<100*1024*1024,('oversize',name)
    assert not any(pin in data for pin in pins),('credential bytes',name)
    if data.startswith(b'\x1f\x8b'):
        expanded=gzip.decompress(data);decompressed+=1
        assert not any(pin in expanded for pin in pins),('credential bytes in gzip',name)
    hashes[name]=hashlib.sha256(data).hexdigest().upper()
record=dict(passed=True,controllerAccess=False,sourceAndEvidenceFiles=len(paths),bytes=sum(s for s,n in sizes),
    largestFiles=[dict(bytes=s,path=n) for s,n in sorted(sizes,reverse=True)[:5]],
    gzipPayloadsInspected=decompressed,credentialValuesRecorded=False,outsideScopeLeftUnstaged=outside,sha256=hashes)
output='s5_commit_inventory_01.json' if len(sys.argv)==1 else sys.argv[1]
assert output in ('s5_commit_inventory_01.json','s5_commit_inventory_02.json')
with (W/output).open('x',encoding='utf-8') as f:json.dump(record,f,indent=2,sort_keys=True)
print(json.dumps({k:v for k,v in record.items() if k!='sha256'}))
