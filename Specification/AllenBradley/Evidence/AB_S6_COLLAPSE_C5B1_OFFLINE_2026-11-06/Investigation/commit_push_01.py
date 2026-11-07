from pathlib import Path
import hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;NAME='AB_S6_COLLAPSE_C5B1_OFFLINE_2026-11-06';P=R/'Specification/AllenBradley/Evidence'/NAME
def git(*args):return subprocess.check_output(['git',*args],cwd=R,text=True).strip()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def read(p):return json.loads(Path(p).read_bytes())
assert git('branch','--show-current')=='main'
freeze=read(W/'tools_freeze_01.json');assert git('rev-parse','HEAD')==freeze['head']
assert not git('diff','--cached','--name-only'),'unrelated staged work exists'
assert read(P/'Gates/summary.json')['passed']
for row in read(P/'artifact_manifest.json')['files']:assert sha(P/row['path'])==row['sha256']
for row in freeze['files']:assert sha(R/row['path'])==row['sha256']
for path,digest in read(W/'unrelated_before.json').items():assert sha(R/path)==digest,path
assert git('config','core.hooksPath')=='.githooks'
prefix='FraktalCore/PLC/Allen-Bradley/tools/'
sources=git('diff','--name-only','--',prefix).splitlines()+git('ls-files','--others','--exclude-standard','--',prefix).splitlines()
assert set(sources)<={e['path'] for e in freeze['files']}
docs=['Specification/AllenBradley/AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md','Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','Specification/AllenBradley/Evidence/'+NAME+'.md']
assert all((R/p).is_file() for p in docs)
paths=sorted(set(sources+docs+[p.relative_to(R).as_posix() for p in P.rglob('*') if p.is_file()]))
with (W/'commit_paths_01.json').open('x',encoding='utf-8') as f:json.dump(paths,f,indent=2)
with (W/'commit_paths_01.nul').open('xb') as f:f.write(b'\0'.join(p.encode() for p in paths)+b'\0')
subprocess.run(['git','fetch','origin','main'],cwd=R,check=True)
assert git('rev-parse','origin/main')==freeze['head'],'origin/main advanced; integration review required'
subprocess.run(['git','add','-f','--pathspec-from-file='+str(W/'commit_paths_01.nul'),'--pathspec-file-nul'],cwd=R,check=True)
assert set(git('diff','--cached','--name-only').splitlines())==set(paths)
subprocess.run(['git','-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check'],cwd=R,check=True)
message='''S6 C5b1: migrate capture and read-only configuration checks

Use typed Core requests, live PLC revisions and published refusal keys.
Read exact capture values/audits through O10; browse through the packaged
read-only configuration RPC and require START refusal before commit.
Enable the approved V6.8/V6.10 press publications; retain legacy endpoints.

Validation: 2,629 AB tests, 85 root tests and all three root gates; both
v38 builds/read-backs/access/defaults; schema and exact-token proofs.
Offline press Capacity 49%; genealogy bytes and prior qualification match.
No controller operations. Set/host workflows and native S6-Q remain open.
'''
with (W/'commit_message_01.txt').open('x',encoding='utf-8',newline='\n') as f:f.write(message)
subprocess.run(['git','commit','-F',str(W/'commit_message_01.txt')],cwd=R,check=True)
commit=git('rev-parse','HEAD');subprocess.run(['git','push','origin','main'],cwd=R,check=True)
remote=git('ls-remote','--heads','origin','refs/heads/main').split()[0];assert remote==commit
for path,digest in read(W/'unrelated_before.json').items():assert sha(R/path)==digest,path
result=dict(committed=True,pushed=True,branch='main',commit=commit,remote=remote,files=len(paths),unrelatedEditsPreserved=True)
with (W/'commit_push_result_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=1))
