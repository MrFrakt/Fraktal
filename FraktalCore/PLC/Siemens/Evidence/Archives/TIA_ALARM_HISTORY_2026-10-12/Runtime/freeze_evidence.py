"""Freeze completed history qualification without changing earlier archives."""
from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as E
REPO=Path('C:/Projects/Fraktal').resolve()
WORK=Path(__file__).resolve().parent
ARCHIVE=REPO/'FraktalCore/PLC/Siemens/Evidence/Archives/TIA_ALARM_HISTORY_2026-10-12'
assert not ARCHIVE.exists()
assert (WORK/'42_gate_summary.json').exists()
gates=json.loads((WORK/'42_gate_summary.json').read_bytes())
assert gates['native_assertions']==1165 and gates['tools']==155
assert gates['owner']['state']=='Run' and gates['keeper_pid']==12728
shutil.copytree(WORK,ARCHIVE/'Runtime',ignore=shutil.ignore_patterns('__pycache__'))
roots=[REPO/'FraktalCore/PLC/Siemens'/n for n in ('Framework','Examples/PressDemo','Tests/Generator','Tests/AlarmPersistence','Tests/AccessPersistence','Tests/ConfigSets','Tests/Config','Tests/Access','Tests/StateAlarm','Tests/Decision','tools')]
for root in roots:
    for p in sorted(root.rglob('*')):
        if not p.is_file() or any(n in ('__pycache__','bin','obj') for n in p.relative_to(root).parts):continue
        if p.suffix not in ('.py','.ps1','.dart','.md','.json','.scl','.udt','.db','.xml','.in','.plan','.cs','.csproj'):continue
        target=ARCHIVE/'SourceSnapshot'/p.relative_to(REPO);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
manifest=json.loads((WORK/'frames_final/manifest.json').read_bytes())
inputs=set(manifest['core_inputs']) | set(manifest['runtime']['authority_inputs'])
inputs |= {'AGENTS.md','tools/check_consistency.py','tools/test_check_consistency.py','Specification/Fraktal_TIA_Part_IV.md','Specification/Siemens/SIEMENS_PORT_PLAN.md','Specification/Siemens/README.md','Specification/Siemens/Evidence/TIA_ALARM_HISTORY_2026-10-12.md','FraktalCore/PLC/Siemens/README.md'}
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
