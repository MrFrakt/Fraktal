from pathlib import Path
import hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;P=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5B3_SHELVING_OFFLINE_2026-11-06';Q=P/'Publication'
def git(*args):return subprocess.check_output(['git',*args],cwd=R)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
head=git('rev-parse','HEAD').decode().strip();assert git('ls-remote','--heads','origin','refs/heads/main').decode().split()[0]==head
assert git('branch','--show-current').decode().strip()=='main'
freeze=json.loads((W/'tools_freeze_01.json').read_bytes())['files'];payload=[]
for folder,name in ((P,'artifact_manifest.json'),(Q,'artifact_manifest.json'),(Q,'artifact_manifest_02.json')):
 for row in json.loads((folder/name).read_bytes())['files']:
  path=folder/row['path'];assert sha(path)==row['sha256'];payload.append(path)
 payload.append(folder/name)
for row in freeze:assert sha(R/row['path'])==row['sha256']
paths=[*(R/row['path'] for row in freeze),*payload,*(R/path for path in json.loads((W/'commit_paths_03.json').read_bytes()) if path.endswith('.md'))]
tree={}
for row in git('ls-tree','-r','-z','HEAD','--','FraktalCore/PLC/Allen-Bradley/tools','Specification/AllenBradley').split(b'\0'):
 if not row:continue
 header,path=row.split(b'\t',1);mode,kind,oid=header.split();assert kind==b'blob';tree[path.decode()]=oid.decode()
for path in paths:
 raw=path.read_bytes();oid=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();assert tree[path.relative_to(R).as_posix()]==oid,path
for row in json.loads((W/'unrelated_before.json').read_bytes()):assert sha(R/row['path'])==row['sha256']
result=dict(passed=True,commit=head,branch='main',remoteMatches=True,sourceFiles=len(freeze),evidenceFiles=len(payload),storedBlobsVerified=len(paths),unrelatedEditsPreserved=True)
with (W/'post_push_verification_03.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(result,indent=1))
