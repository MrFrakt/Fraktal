from pathlib import Path
import datetime,hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def save(name,value):
 with (W/name).open('x',encoding='utf-8') as out:json.dump(value,out,indent=2)
parent=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
assert parent=='8f87f0ab5f4e1c9fb007a23e1b0f51847d2ae3a0'
save('entry_01.json',dict(parentCommit=parent,startUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='C5b3 acceptance-only shelving health requirement, offline',controllerAccess=False))
owner=['.vscode/settings.json','FraktalCore/PLC/Siemens/Tests/Manifest/README.md','analysis_options.yaml']
save('unrelated_before.json',[dict(path=p,sha256=sha(R/p)) for p in owner])
files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z','--','FraktalCore/PLC/Allen-Bradley/tools'],cwd=R).decode().split('\0')
save('tools_freeze_01.json',dict(head=parent,files=[dict(path=p,sha256=sha(R/p)) for p in sorted(set(files)-{''})]))
print(json.dumps(dict(passed=True,parent=parent,files=len(set(files)-{''}))))
