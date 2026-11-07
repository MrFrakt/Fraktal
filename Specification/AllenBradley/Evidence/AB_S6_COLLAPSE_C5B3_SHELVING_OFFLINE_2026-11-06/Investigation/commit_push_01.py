from pathlib import Path
import hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;NAME='AB_S6_COLLAPSE_C5B3_SHELVING_OFFLINE_2026-11-06';P=R/'Specification/AllenBradley/Evidence'/NAME
def git(*args):return subprocess.check_output(['git',*args],cwd=R,text=True).strip()
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
assert git('branch','--show-current')=='main'
freeze=read(W/'tools_freeze_01.json');assert git('rev-parse','HEAD')==freeze['head']
assert not git('diff','--cached','--name-only'),'unrelated staged work exists'
assert read(P/'Gates/summary.json')['passed']
for row in read(P/'artifact_manifest.json')['files']:assert sha(P/row['path'])==row['sha256']
for row in freeze['files']:assert sha(R/row['path'])==row['sha256']
for row in read(W/'unrelated_before.json'):assert sha(R/row['path'])==row['sha256'],row['path']
runtime=read(P/'Gates/runtime_bindings_01.json')
for name,digest in runtime['sources'].items():assert sha(R/name)==digest,name
for name in ('gateway','hostAdapter'):assert sha(runtime[name]['path'])==runtime[name]['sha256']
assert git('config','core.hooksPath')=='.githooks'
prefix='FraktalCore/PLC/Allen-Bradley/tools/'
sources=[prefix+name for name in ('fraktal_ab_press_s6_shelving_echo38.py','test_fraktal_ab_s6_shelving_profile.py','test_fraktal_ab_schema_identity.py')]
actual=git('diff','--name-only','--',prefix).splitlines()+git('ls-files','--others','--exclude-standard','--',prefix).splitlines()
assert set(actual)==set(sources),actual
docs=['Specification/AllenBradley/AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md','Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','Specification/AllenBradley/Evidence/'+NAME+'.md']
paths=sorted(set(sources+docs+[p.relative_to(R).as_posix() for p in P.rglob('*') if p.is_file()]))
with (W/'commit_paths_01.json').open('x',encoding='utf-8') as out:json.dump(paths,out,indent=2)
with (W/'commit_paths_01.nul').open('xb') as out:out.write(b'\0'.join(p.encode() for p in paths)+b'\0')
subprocess.run(['git','fetch','origin','main'],cwd=R,check=True)
assert git('rev-parse','origin/main')==freeze['head'],'origin/main advanced; integration review required'
subprocess.run(['git','add','-f','--pathspec-from-file='+str(W/'commit_paths_01.nul'),'--pathspec-file-nul'],cwd=R,check=True)
assert set(git('diff','--cached','--name-only').splitlines())==set(paths)
subprocess.run(['git','-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check'],cwd=R,check=True)
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
with (W/'commit_message_01.txt').open('x',encoding='utf-8',newline='\n') as out:out.write(message)
subprocess.run(['git','commit','-F',str(W/'commit_message_01.txt')],cwd=R,check=True)
commit=git('rev-parse','HEAD');assert git('rev-parse','HEAD^')==freeze['head']
subprocess.run(['git','push','origin','main'],cwd=R,check=True)
remote=git('ls-remote','--heads','origin','refs/heads/main').split()[0];assert remote==commit
for row in read(W/'unrelated_before.json'):assert sha(R/row['path'])==row['sha256'],row['path']
result=dict(committed=True,pushed=True,branch='main',commit=commit,remote=remote,files=len(paths),unrelatedEditsPreserved=True)
with (W/'commit_push_result_01.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(result,indent=1))
