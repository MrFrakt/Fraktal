"""Freeze completed selected-Unit alarm recovery qualification."""
from pathlib import Path
import json,hashlib,shutil
REPO=Path('C:/Projects/Fraktal').resolve();WORK=Path(__file__).resolve().parent
ARCHIVE=REPO/'FraktalCore/PLC/Siemens/Evidence/Archives/TIA_ALARM_RECOVERY_2026-10-12'
assert not ARCHIVE.exists()
gates=json.loads((WORK/'29_gate_summary.json').read_bytes())
assert gates['recovery']==341 and gates['owner']['state']=='Run' and gates['keeper_pid']==12728
assert gates['native_assertions']==1510
final=json.loads((WORK/'42_final_target.json').read_bytes())
assert final['owner']['state']=='Run' and final['keeper']['Id']==12728 and final['bench_normalized']
assert all(row['verified'] for row in json.loads((WORK/'40_previous_archives_verified.json').read_bytes()).values())
shutil.copytree(WORK,ARCHIVE/'Runtime',ignore=shutil.ignore_patterns('__pycache__'))
for name in ('Framework','Examples/PressDemo','Tests','tools','Spikes/S12_TypeMap'):
    root=REPO/'FraktalCore/PLC/Siemens'/name
    for p in sorted(root.rglob('*')):
        if not p.is_file() or any(n in ('bin','obj','__pycache__') for n in p.relative_to(root).parts):continue
        if p.suffix not in ('.py','.ps1','.md','.json','.scl','.udt','.db','.xml','.in','.plan','.dart','.cs','.csproj'):continue
        target=ARCHIVE/'SourceSnapshot'/p.relative_to(REPO);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
manifest=json.loads((WORK/'frames_04/manifest.json').read_bytes())
inputs=set(manifest['core_inputs'])|set(manifest['runtime']['authority_inputs'])
inputs|={'AGENTS.md','tools/check_consistency.py','tools/test_check_consistency.py','Specification/Fraktal_TIA_Part_IV.md','Specification/Siemens/SIEMENS_PORT_PLAN.md','Specification/Siemens/README.md','Specification/Siemens/Evidence/TIA_ALARM_RECOVERY_2026-10-12.md','FraktalCore/PLC/Siemens/README.md','FraktalCore/HMI/lib/localization/default_catalogs.dart'}
for name in sorted(inputs):
    target=ARCHIVE/'SourceSnapshot'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/name,target)
rows=[];total=0
for p in sorted(ARCHIVE.rglob('*')):
    if p.is_file():
        data=p.read_bytes();total+=len(data);rows.append(hashlib.sha256(data).hexdigest()+'  '+p.relative_to(REPO).as_posix())
(ARCHIVE/'SHA256SUMS').write_bytes(('\n'.join(rows)+'\n').encode('ascii'))
for row in rows:
    sha,name=row.split('  ',1);assert hashlib.sha256((REPO/name).read_bytes()).hexdigest()==sha
print(json.dumps({'archive':str(ARCHIVE),'files':len(rows),'bytes':total,'verified':True}))
