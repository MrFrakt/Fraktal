"""Preserve LF in the three working documents, leaving CRLF PLC tools alone."""
from pathlib import Path
import hashlib,json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
updates=json.loads((W/'documentation_updates_01.json').read_bytes())
for name,row in updates.items():
    p=R/name;b=p.read_bytes()
    before=(W/('before_'+p.name)).read_bytes()
    assert b'\r\n' not in before
    p.write_bytes(b.replace(b'\r\n',b'\n'))
    row['afterSha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    row['newlineCorrection']='Preserve existing LF; no content change'
with (W/'documentation_updates_02.json').open('x') as f:json.dump(updates,f,indent=2)
print(json.dumps({'correctedWorkingDocuments':len(updates),'abCodeChanged':False}))
