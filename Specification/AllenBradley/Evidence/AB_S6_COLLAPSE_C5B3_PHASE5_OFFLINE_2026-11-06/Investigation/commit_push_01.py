from pathlib import Path
import hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;NAME='AB_S6_COLLAPSE_C5B3_PHASE5_OFFLINE_2026-11-06';P=R/'Specification/AllenBradley/Evidence'/NAME
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
sources=[prefix+name for name in (
 'fixtures/schema_identity/fraktal_ab_press_s6_collapse_echo38.declared.json',
 'fraktal_ab_fixture_observation.py',
 'fraktal_ab_fixture_reads.py',
 'fraktal_ab_phase5_execute.py',
 'fraktal_ab_press_s6_collapse_echo38.py',
 'test_fraktal_ab_fixture_observation.py',
 'test_fraktal_ab_fixture_reads.py',
 'test_fraktal_ab_phase5_canonical.py',
)]
actual=git('diff','--name-only','--',prefix).splitlines()+git('ls-files','--others','--exclude-standard','--',prefix).splitlines()
assert set(actual)==set(sources),actual
docs=[
 'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md',
 'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
 'Specification/AllenBradley/Evidence/'+NAME+'.md',
]
paths=sorted(set(sources+docs+[p.relative_to(R).as_posix() for p in P.rglob('*') if p.is_file()]))
with (W/'commit_paths_01.json').open('x',encoding='utf-8') as out:json.dump(paths,out,indent=2)
with (W/'commit_paths_01.nul').open('xb') as out:out.write(b'\0'.join(p.encode() for p in paths)+b'\0')
subprocess.run(['git','fetch','origin','main'],cwd=R,check=True)
assert git('rev-parse','origin/main')==freeze['head'],'origin/main advanced; integration review required'
subprocess.run(['git','add','-f','--pathspec-from-file='+str(W/'commit_paths_01.nul'),'--pathspec-file-nul'],cwd=R,check=True)
assert set(git('diff','--cached','--name-only').splitlines())==set(paths)
subprocess.run(['git','-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check'],cwd=R,check=True)
message='''S6 C5b3: migrate Phase 5 metrics and report reads to canonical/O10

Move fraktal_ab_phase5_execute onto canonical CIP rows and O10 private
observations (141 facts, +39 in FRK_T_PressFixtureV2_2A276D94) with zero
direct legacy projection or layout calls and all 21 row predicates and 16
wait predicates preserved. Read cylinder TimCount/TimLast from canonical
Timing/Rows[1..2] aliases and resolve refusal keys from the deployed PLC
command table. Account for the Phase 5 health_rows reason-21 precondition
on the shelving profile while preserving the normal press metrics exclusion.

Validation: 2,696 AB tests, 85 root tests, 62 focused checks and 27 native
capture replay/storage checks across all 86 accepted press captures; both
v38 press profiles build/read back on both targets, pass access/default/SDK
and token/schema proofs, and fit at 54% Capacity (1,726,208 and 1,726,244
Blocks, +13,004). No controller operations ran.
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
