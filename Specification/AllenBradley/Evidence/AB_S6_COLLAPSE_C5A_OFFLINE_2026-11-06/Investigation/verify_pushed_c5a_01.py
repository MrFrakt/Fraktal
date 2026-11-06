"""Read-only verification: tested bytes, evidence hashes, Git blobs and remote."""
from pathlib import Path
import hashlib,json,subprocess

R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
def git(*args):return subprocess.check_output(['git',*args],cwd=R)
head=git('rev-parse','HEAD').decode().strip()
assert git('ls-remote','--heads','origin','refs/heads/main').decode().split()[0]==head
assert git('branch','--show-current').decode().strip()=='main'
P=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5A_OFFLINE_2026-11-06'
payload=json.loads((P/'artifact_manifest.json').read_bytes())['files']
freeze=json.loads((W/'tools_freeze_05.json').read_bytes())['files']
for entry in payload:assert hashlib.sha256((P/entry['path']).read_bytes()).hexdigest().upper()==entry['sha256']
for entry in freeze:assert hashlib.sha256((R/entry['path']).read_bytes()).hexdigest().upper()==entry['sha256']
tree={}
for record in git('ls-tree','-r','-z','HEAD','--','FraktalCore/PLC/Allen-Bradley/tools',P.relative_to(R).as_posix()).split(b'\0'):
    if not record:continue
    header,path=record.split(b'\t',1);mode,kind,oid=header.split()
    assert kind==b'blob'
    tree[path.decode('utf-8')]=oid.decode()
checked=0
for path in [*(R/e['path'] for e in freeze),*(P/e['path'] for e in payload),P/'artifact_manifest.json']:
    raw=path.read_bytes()
    oid=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    assert tree[path.relative_to(R).as_posix()]==oid,path
    checked+=1
for path,digest in json.loads((W/'unrelated_bindings_01.json').read_bytes()).items():
    assert hashlib.sha256((R/path).read_bytes()).hexdigest().upper()==digest,path
result=dict(passed=True,commit=head,branch='main',remoteMatches=True,sourceFiles=len(freeze),evidenceFiles=len(payload),storedBlobsVerified=checked,unrelatedEditsPreserved=True)
with (W/'post_push_verification_01.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(result,indent=1))
