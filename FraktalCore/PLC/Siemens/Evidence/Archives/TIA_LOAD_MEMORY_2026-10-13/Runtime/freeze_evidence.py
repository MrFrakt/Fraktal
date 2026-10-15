from pathlib import Path
import os,shutil,hashlib,json
r=Path('C:/Projects/Fraktal').resolve();w=Path(__file__).resolve().parent
archive=r/'FraktalCore/PLC/Siemens/Evidence/Archives/TIA_LOAD_MEMORY_2026-10-13'
g=json.loads((w/'19_gate_summary.json').read_bytes());assert g['native_assertions']==926 and not archive.exists()
owner=json.loads((w/'20_final_owner.json').read_bytes());assert owner['owner']['state']=='Run' and owner['keeper']['Id']==12728
shutil.copytree(w,archive/'Runtime',ignore=shutil.ignore_patterns('__pycache__'))
for name in ('Framework','tools','Spikes/S16_Persistence','Spikes/S12_TypeMap','Tests/Config','Tests/Access','Tests/AccessPersistence','Tests/AlarmRecovery','Tests/StateAlarm'):
 root=r/'FraktalCore/PLC/Siemens'/name
 for p in sorted(root.rglob('*')):
  if not p.is_file() or any(n in ('bin','obj','__pycache__') for n in p.relative_to(root).parts):continue
  if p.suffix not in ('.py','.ps1','.md','.json','.in','.scl','.db','.udt','.xml','.cs','.csproj'):continue
  target=archive/'SourceSnapshot'/p.relative_to(r);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
old=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Event_Delivery_20261012'
manifest=json.loads((old/'frames_07/manifest.json').read_bytes())
inputs=set(manifest['core_inputs'])|set(manifest['runtime']['authority_inputs'])
inputs|={'AGENTS.md','tools/check_consistency.py','tools/test_check_consistency.py','Specification/Fraktal_TIA_Part_IV.md','Specification/Siemens/SIEMENS_PORT_PLAN.md','Specification/Siemens/README.md','Specification/Siemens/Evidence/TIA_LOAD_MEMORY_2026-10-13.md','FraktalCore/PLC/Siemens/README.md'}
for name in sorted(inputs):
 p=r/name;target=archive/'SourceSnapshot'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
for name in ('probe_config.py','probe_state_alarm.py','frames_07/manifest.json'):
 p=old/name;target=archive/'BaselineInputs'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
rows=[];total=0
for p in sorted(archive.rglob('*')):
 if not p.is_file():continue
 data=p.read_bytes();total+=len(data);rows.append(hashlib.sha256(data).hexdigest()+'  '+p.relative_to(r).as_posix())
(archive/'SHA256SUMS').write_bytes(('\n'.join(rows)+'\n').encode('ascii'))
for row in rows:
 digest,name=row.split('  ',1);assert hashlib.sha256((r/name).read_bytes()).hexdigest()==digest,name
print(json.dumps(dict(archive=str(archive),files=len(rows),bytes=total,verified=True)))
