from pathlib import Path
import hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
prior=json.loads((W/'tools_freeze_02.json').read_bytes())
changed=[row['path'] for row in prior['files'] if sha(R/row['path'])!=row['sha256']]
assert changed==['FraktalCore/PLC/Allen-Bradley/tools/test_fraktal_ab_s3i_lifetime.py'],changed
files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z','--','FraktalCore/PLC/Allen-Bradley/tools'],cwd=R).decode().split('\0')
rows=[dict(path=p,sha256=sha(R/p)) for p in sorted(set(files)-{''})]
assert {row['path'] for row in rows}=={row['path'] for row in prior['files']}
with (W/'tools_freeze_03.json').open('x',encoding='utf-8') as out:json.dump(dict(head=prior['head'],files=rows,changedSinceSecondFreeze=changed,priorFreezeSha256=sha(W/'tools_freeze_02.json'),reusedGateScope='Production, generator, replay/Part test, runtime package and root gate sources are identical; only the legacy lifetime test model now accepts the documented audit=False state-read argument and still rejects audit-table reads. Full AB suite and lifetime tests rerun; other 62 focused checks retain identical sources.'),out,indent=2)
print(json.dumps(dict(passed=True,files=len(rows),changed=changed)))
