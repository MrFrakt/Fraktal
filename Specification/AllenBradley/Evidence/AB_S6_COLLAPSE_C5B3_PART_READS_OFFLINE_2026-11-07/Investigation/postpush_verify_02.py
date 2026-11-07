from pathlib import Path
import hashlib,io,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;NAME='AB_S6_COLLAPSE_C5B3_PART_READS_OFFLINE_2026-11-07';P=R/'Specification/AllenBradley/Evidence'/NAME
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def read(p):return json.loads(Path(p).read_bytes())
def git(*args):return subprocess.check_output(['git',*args],cwd=R,text=True).strip()
publication=read(W/'publish_result_01.json');commit=publication['commit'];assert publication['pushed']
assert git('branch','--show-current')=='main' and git('rev-parse','HEAD')==commit
assert git('ls-remote','--heads','origin','refs/heads/main').split()[0]==commit
freeze=read(W/'tools_freeze_03.json');pins={r['path']:r['sha256'] for r in freeze['files']}
for manifest,root in ((P/'artifact_manifest.json',P),(P/'Publication/artifact_manifest.json',P/'Publication')):
 for row in read(manifest)['files']:pins[(root/row['path']).relative_to(R).as_posix()]=row['sha256']
 pins[manifest.relative_to(R).as_posix()]=sha(manifest)
for row in read(W/'unrelated_before.json'):assert sha(R/row['path'])==row['sha256'],row['path']
for path,digest in pins.items():assert sha(R/path)==digest,path
items=sorted(pins.items())
for base in range(0,len(items),32):
 batch=items[base:base+32];queries=''.join(commit+':'+path+'\n' for path,_ in batch).encode();stream=io.BytesIO(subprocess.check_output(['git','cat-file','--batch'],input=queries,cwd=R))
 for path,digest in batch:
  header=stream.readline().split();assert len(header)==3 and header[1]==b'blob',(path,header)
  content=stream.read(int(header[2]));assert stream.read(1)==b'\n'
  assert hashlib.sha256(content).hexdigest().upper()==digest,path
 assert not stream.read()
assert not git('diff','--cached','--name-only')
status=git('status','--porcelain');expected={row['path'] for row in read(W/'unrelated_before.json')}
# strip() may remove the first line's leading space, so compare only path suffixes.
assert len(status.splitlines())==len(expected) and all(any(line.endswith(path) for path in expected) for line in status.splitlines()),status
result=dict(passed=True,commit=commit,remote=commit,sourceFiles=len(freeze['files']),verifiedWorkingTreeAndGitBlobs=len(pins),onlyUnrelatedEditsRemain=True,controllerAccess=False)
with (W/'postpush_verify_01.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(result))
