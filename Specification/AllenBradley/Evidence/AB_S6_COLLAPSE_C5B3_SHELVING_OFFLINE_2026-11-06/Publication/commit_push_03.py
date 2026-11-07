from pathlib import Path
import base64,hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;P=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5B3_SHELVING_OFFLINE_2026-11-06';Q=P/'Publication'
def git(*args):return subprocess.check_output(['git',*args],cwd=R,text=True).strip()
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def write(name,value):
 with (Q/name).open('x',encoding='utf-8') as out:json.dump(value,out,indent=2)
freeze=read(W/'tools_freeze_01.json');assert git('branch','--show-current')=='main' and git('rev-parse','HEAD')==freeze['head']
original=read(W/'commit_paths_02.json');assert set(git('diff','--cached','--name-only').splitlines())==set(original)
for folder in (P,Q):
 for row in read(folder/'artifact_manifest.json')['files']:assert sha(folder/row['path'])==row['sha256']
for row in freeze['files']:assert sha(R/row['path'])==row['sha256']
for row in read(W/'unrelated_before.json'):assert sha(R/row['path'])==row['sha256']
runtime=read(P/'Gates/runtime_bindings_01.json')
for name,digest in runtime['sources'].items():assert sha(R/name)==digest
for name in ('gateway','hostAdapter'):assert sha(runtime[name]['path'])==runtime[name]['sha256']
assert git('config','core.hooksPath')=='.githooks'
excluded={
 (P/'Gates/focused_profile_02.log').relative_to(R).as_posix():5,
 (Q/'commit_attempt_01.log').relative_to(R).as_posix():4,
}
for path in excluded:assert subprocess.check_output(['git','show',':'+path],cwd=R)==(R/path).read_bytes()
check=['git','-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check']
failed=subprocess.run(check,cwd=R,capture_output=True);lines=failed.stdout.splitlines()
assert failed.returncode==2 and not failed.stderr and len(lines)==4,failed.stdout
found=set()
for i in range(0,len(lines),2):
 matched=[path for path,line in excluded.items() if lines[i]==f'{path}:{line}: trailing whitespace.'.encode()]
 assert len(matched)==1 and lines[i+1].endswith(b' ... '),lines[i:i+2]
 found.add(matched[0])
assert found==set(excluded)
narrow=check+['--','.',*(':(exclude)'+path for path in excluded)]
subprocess.run(narrow,cwd=R,check=True)
raw=(W/'commit_push_02.log').read_bytes()
write('commit_attempt_02.json',dict(logSha256=hashlib.sha256(raw).hexdigest().upper(),logBase64=base64.b64encode(raw).decode(),receipt=read(W/'commit_push_02_exit.json'),encoding='base64 of original bytes; preserves the quoted trailing space without adding another text-log exception'))
write('whitespace_check_02.json',dict(passed=True,scope='Git diff whitespace only',excluded=[dict(path=path,line=line,sha256=sha(R/path)) for path,line in excluded.items()],reason='The unchanged failed unittest heading and the unchanged diagnostic quoting it retain their original trailing space. Every other staged file passes. Source/test/runtime gates and the commit hook remain enabled.',fullCheckExitCode=failed.returncode,fullCheckOutput=failed.stdout.decode('ascii'),remainingFilesCheckExitCode=0))
for source,name in ((Path(__file__),'commit_push_03.py'),(W/'verify_pushed_03.py','verify_pushed_03.py')):
 with (Q/name).open('xb') as out:out.write(source.read_bytes())
names=('commit_attempt_02.json','whitespace_check_02.json','commit_push_03.py','verify_pushed_03.py')
write('artifact_manifest_02.json',dict(schema='fraktal.evidence.artifacts',schemaVersion=1,files=[dict(path=name,sha256=sha(Q/name),bytes=(Q/name).stat().st_size) for name in names]))
paths=sorted(original+[(Q/name).relative_to(R).as_posix() for name in (*names,'artifact_manifest_02.json')])
with (W/'commit_paths_03.json').open('x',encoding='utf-8') as out:json.dump(paths,out,indent=2)
with (W/'commit_paths_03.nul').open('xb') as out:out.write(b'\0'.join(path.encode() for path in paths)+b'\0')
subprocess.run(['git','fetch','origin','main'],cwd=R,check=True);assert git('rev-parse','origin/main')==freeze['head']
subprocess.run(['git','add','-f','--pathspec-from-file='+str(W/'commit_paths_03.nul'),'--pathspec-file-nul'],cwd=R,check=True)
assert set(git('diff','--cached','--name-only').splitlines())==set(paths)
subprocess.run(narrow,cwd=R,check=True)
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
with (W/'commit_message_03.txt').open('x',encoding='utf-8',newline='\n') as out:out.write(message)
subprocess.run(['git','commit','-F',str(W/'commit_message_03.txt')],cwd=R,check=True)
commit=git('rev-parse','HEAD');assert git('rev-parse','HEAD^')==freeze['head']
subprocess.run(['git','push','origin','main'],cwd=R,check=True)
remote=git('ls-remote','--heads','origin','refs/heads/main').split()[0];assert remote==commit
for row in read(W/'unrelated_before.json'):assert sha(R/row['path'])==row['sha256']
result=dict(committed=True,pushed=True,branch='main',commit=commit,remote=remote,files=len(paths),unrelatedEditsPreserved=True,rawFailedLogsPreserved=True,whitespaceExceptions=2)
with (W/'commit_push_result_03.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(result,indent=1))
