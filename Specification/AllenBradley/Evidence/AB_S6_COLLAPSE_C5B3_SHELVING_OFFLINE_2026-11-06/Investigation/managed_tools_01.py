from pathlib import Path
import datetime,hashlib,json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
folders=[R/'FraktalCore/PLC/Allen-Bradley/tools/Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86',Path('C:/work/fraktal-ab-s3j-20261024/s3j_01/prepare/bin/Debug/net8.0/win-x86')]
files=[]
for folder in folders:
 selected=[p for p in folder.rglob('*') if p.is_file() and (p.suffix.lower() in ('.exe','.dll') or p.name.endswith(('.deps.json','.runtimeconfig.json')))]
 assert any(p.suffix=='.dll' for p in selected)
 for p in sorted(selected):files.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest().upper(),bytes=p.stat().st_size))
with (W/'managed_tools_01.json').open('x',encoding='utf-8') as out:json.dump(dict(passed=True,recordedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),purpose='Bind the managed entry assemblies and local dependencies as well as their apphost executables',files=files,controllerAccess=False),out,indent=2)
print(json.dumps(dict(passed=True,toolFolders=len(folders),files=len(files))))
