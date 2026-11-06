"""Owner-authorized C5a commit/push, after sealed qualification and doc review."""
from pathlib import Path
import hashlib,json,subprocess,sys

R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
NAME='AB_S6_COLLAPSE_C5A_OFFLINE_2026-11-06'
P=R/'Specification/AllenBradley/Evidence'/NAME
def run(*args):return subprocess.check_output(list(args),cwd=R,text=True).strip()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
assert run('git','branch','--show-current')=='main'
freeze=json.loads((W/'tools_freeze_05.json').read_bytes())
assert run('git','rev-parse','HEAD')==freeze['head']
assert not run('git','diff','--cached','--name-only'),'unrelated staged work exists'
assert json.loads((P/'Gates/summary.json').read_bytes())['passed']
for entry in json.loads((P/'artifact_manifest.json').read_bytes())['files']:
    assert sha(P/entry['path'])==entry['sha256'],entry['path']
for entry in freeze['files']:assert sha(R/entry['path'])==entry['sha256'],entry['path']
for path,digest in json.loads((W/'unrelated_bindings_01.json').read_bytes()).items():assert sha(R/path)==digest,path
report=R/'Specification/AllenBradley/Evidence'/(NAME+'.md')
assert report.is_file()
prefix='FraktalCore/PLC/Allen-Bradley/tools/'
sources=run('git','diff','--name-only','--',prefix).splitlines()
sources+=run('git','ls-files','--others','--exclude-standard','--',prefix).splitlines()
assert all(path in {entry['path'] for entry in freeze['files']} for path in sources)
docs=['Specification/AllenBradley/AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md',
      'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',report.relative_to(R).as_posix()]
paths=sorted(set(sources+docs+[path.relative_to(R).as_posix() for path in P.rglob('*') if path.is_file()]))
with (W/'commit_paths_01.json').open('x',encoding='utf-8') as out:json.dump(paths,out,indent=2)
with (W/'commit_paths_01.nul').open('xb') as out:out.write(b'\0'.join(path.encode('utf-8') for path in paths)+b'\0')
subprocess.run(['git','fetch','origin','main'],cwd=R,check=True)
assert run('git','rev-parse','origin/main')==freeze['head'],'origin/main advanced; inspect before integrating'
# Force applies only to this explicit allowlist, so ignored evidence logs are
# retained while binaries and the owner's unrelated files remain excluded.
subprocess.run(['git','add','-f','--pathspec-from-file='+str(W/'commit_paths_01.nul'),'--pathspec-file-nul'],cwd=R,check=True)
assert set(run('git','diff','--cached','--name-only').splitlines())==set(paths)
subprocess.run(['git','-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check'],cwd=R,check=True)
message='''S6 C5a: route press harness commands through the pinned gateway

Use O11 writeBatch with independent CIP acknowledgement and numeric-key
observation. Add selected O10 V2 reads and the press V6.7 scan bindings.
Preserve legacy profiles/endpoints until the remaining HX clients migrate.

Validation: 2,612 AB and 85 root tests; both v38 targets, read-back/access/
default/schema/token proofs; 44 Dart gateway tests and package checks.
Offline Capacity: genealogy 60%, press 46%. No controller operations.
C5b/C5c and integrated native S6-Q remain open.
'''
with (W/'commit_message_01.txt').open('x',encoding='utf-8',newline='\n') as out:out.write(message)
subprocess.run(['git','commit','-F',str(W/'commit_message_01.txt')],cwd=R,check=True)
commit=run('git','rev-parse','HEAD')
subprocess.run(['git','push','origin','main'],cwd=R,check=True)
remote=run('git','ls-remote','--heads','origin','refs/heads/main').split()[0]
assert remote==commit
for path,digest in json.loads((W/'unrelated_bindings_01.json').read_bytes()).items():assert sha(R/path)==digest,path
result=dict(committed=True,pushed=True,branch='main',commit=commit,remote=remote,files=len(paths),unrelatedEditsPreserved=True)
with (W/'commit_push_result_01.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(result,indent=1))
