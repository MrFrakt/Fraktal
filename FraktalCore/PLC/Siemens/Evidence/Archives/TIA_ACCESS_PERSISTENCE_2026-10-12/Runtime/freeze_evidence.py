"""Freeze the completed native work and authoritative sources without rewriting raw bytes."""
import hashlib
import json
from pathlib import Path
import shutil
REPO=Path('C:/Projects/Fraktal').resolve()
WORK=Path(__file__).resolve().parent
ARCHIVE=REPO/'FraktalCore/PLC/Siemens/Evidence/Archives/TIA_ACCESS_PERSISTENCE_2026-10-12'
assert not ARCHIVE.exists()
assert (WORK/'32_gateway.stop').exists(), 'Stop the test gateway before freezing its log'
shutil.copytree(WORK,ARCHIVE/'Runtime',ignore=shutil.ignore_patterns('__pycache__'))
roots=[REPO/'FraktalCore/PLC/Siemens'/name for name in ('Framework','Examples/PressDemo','Tests/Generator','Tests/AccessPersistence','Tests/ConfigSets','Tests/Config','Tests/Decision','Tests/Access','Tests/StateAlarm','tools')]
for root in roots:
    for path in sorted(root.rglob('*')):
        if not path.is_file() or any(part in ('__pycache__','bin','obj') for part in path.relative_to(root).parts):continue
        if path.suffix not in ('.py','.ps1','.dart','.md','.json','.scl','.udt','.db','.xml','.in','.plan','.cs','.csproj'):continue
        target=ARCHIVE/'SourceSnapshot'/path.relative_to(REPO);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
for name in ('FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/Connectivity/FB_LocalAccessProvider.TcPOU','FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/Platform/F_Crc32.TcPOU','FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/Platform/F_Sha256.TcPOU','FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/Params/PL_Fraktal.TcGVL','FraktalCore/HMI/lib/data/opcua_repository.dart','FraktalCore/HMI/test/opcua_repository_test.dart','FraktalCore/HMI/test/live_tia_manifest_test.dart','FraktalCore/HMI/test/config_sets_test.dart','tools/check_consistency.py','tools/test_check_consistency.py','Specification/OPCUA_TRANSPORT.md','Specification/Fraktal_TIA_Part_IV.md','Specification/Siemens/SIEMENS_PORT_PLAN.md','FraktalCore/PLC/Siemens/README.md','AGENTS.md'):
    target=ARCHIVE/'SourceSnapshot'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/name,target)
rows=[];total=0
for path in sorted(ARCHIVE.rglob('*')):
    if path.is_file():
        data=path.read_bytes();total+=len(data);rows.append(hashlib.sha256(data).hexdigest()+'  '+path.relative_to(REPO).as_posix())
(ARCHIVE/'SHA256SUMS').write_bytes(('\n'.join(rows)+'\n').encode('ascii'))
for row in rows:
    sha,name=row.split('  ',1);assert hashlib.sha256((REPO/name).read_bytes()).hexdigest()==sha
print(json.dumps({'archive':str(ARCHIVE),'files':len(rows),'bytes':total,'verified':True}))
