from pathlib import Path
import hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z','--','FraktalCore/PLC/Allen-Bradley/tools'],cwd=R).decode().split('\0')
rows=[dict(path=p,sha256=hashlib.sha256((R/p).read_bytes()).hexdigest().upper()) for p in sorted(set(files)-{''})]
with (W/'tools_freeze_01.json').open('x',encoding='utf-8') as f:json.dump(dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),files=rows),f,indent=2)
print(json.dumps(dict(passed=True,files=len(rows))))
