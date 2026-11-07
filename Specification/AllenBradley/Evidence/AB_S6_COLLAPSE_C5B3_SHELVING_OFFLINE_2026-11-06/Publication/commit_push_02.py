from pathlib import Path
import hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;NAME='AB_S6_COLLAPSE_C5B3_SHELVING_OFFLINE_2026-11-06';P=R/'Specification/AllenBradley/Evidence'/NAME
def git(*args):return subprocess.check_output(['git',*args],cwd=R,text=True).strip()
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
assert git('branch','--show-current')=='main'
freeze=read(W/'tools_freeze_01.json');assert git('rev-parse','HEAD')==freeze['head']
original=read(W/'commit_paths_01.json');assert set(git('diff','--cached','--name-only').splitlines())==set(original)
for row in read(P/'artifact_manifest.json')['files']:assert sha(P/row['path'])==row['sha256']
for row in freeze['files']:assert sha(R/row['path'])==row['sha256']
for row in read(W/'unrelated_before.json'):assert sha(R/row['path'])==row['sha256'],row['path']
runtime=read(P/'Gates/runtime_bindings_01.json')
for name,digest in runtime['sources'].items():assert sha(R/name)==digest,name
for name in ('gateway','hostAdapter'):assert sha(runtime[name]['path'])==runtime[name]['sha256']
assert git('config','core.hooksPath')=='.githooks'
raw=P/'Gates/focused_profile_02.log';path=raw.relative_to(R).as_posix()
entry=next(row for row in read(P/'artifact_manifest.json')['files'] if row['path']=='Gates/focused_profile_02.log')
assert sha(raw)==entry['sha256']
assert subprocess.check_output(['git','show',':'+path],cwd=R)==raw.read_bytes()
check=['git','-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check']
failed=subprocess.run(check,cwd=R,capture_output=True)
lines=failed.stdout.splitlines()
assert failed.returncode==2 and not failed.stderr and len(lines)==2,failed.stdout
assert lines[0]==(path+':5: trailing whitespace.').encode()
assert lines[1].startswith(b'+test_exercised_service_owners_are_identical_before_storage_lowering ') and lines[1].endswith(b' ... ')
passed=subprocess.run(check+['--','.',':(exclude)'+path],cwd=R,capture_output=True)
assert passed.returncode==0 and not passed.stdout and not passed.stderr
Q=P/'Publication';Q.mkdir(exist_ok=False)
for source,name in ((W/'commit_push_01.log','commit_attempt_01.log'),(W/'commit_push_01_exit.json','commit_attempt_01_exit.json'),(Path(__file__),'commit_push_02.py'),(W/'verify_pushed_02.py','verify_pushed_02.py')):
 with (Q/name).open('xb') as out:out.write(source.read_bytes())
record=dict(passed=True,scope='Git diff whitespace only; all source/runtime/test gates unchanged',excludedPath=path,excludedSha256=sha(raw),reason='Preserve the immutable failed unittest output byte-for-byte, including its trailing space after the subtest heading',fullCheckExitCode=failed.returncode,fullCheckOutput=failed.stdout.decode('ascii'),remainingFilesCheckExitCode=passed.returncode,commitHookEnabled=True)
with (Q/'whitespace_check_01.json').open('x',encoding='utf-8') as out:json.dump(record,out,indent=2)
manifest=[dict(path=p.relative_to(Q).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(Q.iterdir()) if p.is_file()]
with (Q/'artifact_manifest.json').open('x',encoding='utf-8') as out:json.dump(dict(schema='fraktal.evidence.artifacts',schemaVersion=1,files=manifest),out,indent=2)
paths=sorted(original+[p.relative_to(R).as_posix() for p in Q.iterdir() if p.is_file()])
with (W/'commit_paths_02.json').open('x',encoding='utf-8') as out:json.dump(paths,out,indent=2)
with (W/'commit_paths_02.nul').open('xb') as out:out.write(b'\0'.join(p.encode() for p in paths)+b'\0')
subprocess.run(['git','fetch','origin','main'],cwd=R,check=True)
assert git('rev-parse','origin/main')==freeze['head'],'origin/main advanced'
subprocess.run(['git','add','-f','--pathspec-from-file='+str(W/'commit_paths_02.nul'),'--pathspec-file-nul'],cwd=R,check=True)
assert set(git('diff','--cached','--name-only').splitlines())==set(paths)
subprocess.run(check+['--','.',':(exclude)'+path],cwd=R,check=True)
message='''S6 C5b3: qualify the dedicated shelving acceptance profile

Inherit the collapsed press and require unavailable controller metrics only
in an acceptance profile. The existing health/alarm owner supplies the
shelvable warning; the normal press keeps its platform exclusion and all
fixture eligibility/session guards remain. Add the separate S6-Q image phase.

Validation: 2,689 AB tests, 85 root tests, 52 focused service/profile checks;
both v38 builds/read-backs/access/defaults, exact schema and token proof.
Capacity 54%, +36 Blocks; 65 routines unchanged and nine added ST tokens.
No controller operations. Positive native shelving stays S6-Q after C7;
other HX migrations, Frame retirement and final S6 gates remain open.
'''
with (W/'commit_message_02.txt').open('x',encoding='utf-8',newline='\n') as out:out.write(message)
subprocess.run(['git','commit','-F',str(W/'commit_message_02.txt')],cwd=R,check=True)
commit=git('rev-parse','HEAD');assert git('rev-parse','HEAD^')==freeze['head']
subprocess.run(['git','push','origin','main'],cwd=R,check=True)
remote=git('ls-remote','--heads','origin','refs/heads/main').split()[0];assert remote==commit
for row in read(W/'unrelated_before.json'):assert sha(R/row['path'])==row['sha256']
result=dict(committed=True,pushed=True,branch='main',commit=commit,remote=remote,files=len(paths),unrelatedEditsPreserved=True,rawFailedLogPreserved=True,whitespaceExceptionEvidence=(Q/'artifact_manifest.json').relative_to(R).as_posix())
with (W/'commit_push_result_02.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(result,indent=1))
