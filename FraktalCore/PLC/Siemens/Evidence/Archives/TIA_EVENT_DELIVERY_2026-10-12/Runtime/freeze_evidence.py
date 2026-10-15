from pathlib import Path
import os,json,hashlib,shutil
REPO=Path('C:/Projects/Fraktal').resolve();WORK=Path(__file__).resolve().parent
ARCHIVE=REPO/'FraktalCore/PLC/Siemens/Evidence/Archives/TIA_EVENT_DELIVERY_2026-10-12'
g=json.loads((WORK/'60_gate_summary.json').read_bytes());assert g['native_assertions']==1728 and g['receipt_protocol']=='dedicated_metadata_mailbox' and g['active_image_schema']==2
assert g['owner']['state']=='Run' and not ARCHIVE.exists()
final=json.loads((WORK/'61_final_owner.json').read_bytes());assert final['owner']['state']=='Run' and final['keeper']['Id']==12728
shutil.copytree(WORK,ARCHIVE/'Runtime',ignore=shutil.ignore_patterns('__pycache__'))
for name in ('Framework','Examples/PressDemo','Tests','tools','Spikes/S12_TypeMap'):
 root=REPO/'FraktalCore/PLC/Siemens'/name
 for p in sorted(root.rglob('*')):
  if not p.is_file() or any(n in ('bin','obj','__pycache__') for n in p.relative_to(root).parts):continue
  if p.suffix not in ('.py','.ps1','.md','.json','.scl','.udt','.db','.xml','.in','.plan','.dart','.cs','.csproj'):continue
  target=ARCHIVE/'SourceSnapshot'/p.relative_to(REPO);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
manifest=json.loads((WORK/'frames_07/manifest.json').read_bytes())
inputs=set(manifest['core_inputs'])|set(manifest['runtime']['authority_inputs'])
inputs|={'AGENTS.md','tools/check_consistency.py','tools/test_check_consistency.py','Specification/Fraktal_TIA_Part_IV.md','Specification/Siemens/SIEMENS_PORT_PLAN.md','Specification/Siemens/README.md','Specification/Siemens/Evidence/TIA_EVENT_DELIVERY_2026-10-12.md','FraktalCore/PLC/Siemens/README.md','FraktalCore/HMI/lib/localization/default_catalogs.dart'}
for name in sorted(inputs):
 target=ARCHIVE/'SourceSnapshot'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/name,target)
rows=[];total=0
for p in sorted(ARCHIVE.rglob('*')):
 if p.is_file():
  data=p.read_bytes();total+=len(data);rows.append(hashlib.sha256(data).hexdigest()+'  '+p.relative_to(REPO).as_posix())
(ARCHIVE/'SHA256SUMS').write_bytes(('\n'.join(rows)+'\n').encode('ascii'))
for row in rows:
 expected,name=row.split('  ',1);assert hashlib.sha256((REPO/name).read_bytes()).hexdigest()==expected,name
print(json.dumps(dict(archive=str(ARCHIVE),files=len(rows),bytes=total,verified=True)))
