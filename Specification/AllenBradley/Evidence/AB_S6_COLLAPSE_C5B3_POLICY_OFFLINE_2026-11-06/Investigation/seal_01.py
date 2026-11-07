from pathlib import Path
import hashlib,json,re,shutil,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;NAME='AB_S6_COLLAPSE_C5B3_POLICY_OFFLINE_2026-11-06';P=R/'Specification/AllenBradley/Evidence'/NAME

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def read(p):return json.loads(Path(p).read_bytes())
required=['focused_05','annotations_replay_01','native_replay_01','ab_suite_01','root_suite_01','predicates_02','schema_02','token_proof_01','layout_proof_01','fact_accounting_01','genealogy_reuse_01','runtime_pins_01','ab_spec_01','ab_contracts_01','consistency_01']
for label in required:assert read(W/(label+'_exit.json'))['exitCode']==0,label
for name in ('prepare_press_01','schema_press_02','schema_genealogy_01','token_proof_01','layout_proof_01','policy_fact_accounting_01','policy_predicates_02','genealogy_reuse_01','runtime_bindings_01'):assert read(W/(name+'.json'))['passed'],name
freeze=read(W/'tools_freeze_01.json');assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==freeze['head']
for row in freeze['files']:assert sha(R/row['path'])==row['sha256'],row['path']
for name,digest in read(W/'unrelated_before.json').items():assert sha(R/name)==digest,name
runtime=read(W/'runtime_bindings_01.json')
for name,digest in runtime['sources'].items():assert sha(R/name)==digest,name
for name in ('gateway','hostAdapter'):assert sha(runtime[name]['path'])==runtime[name]['sha256']
assert not subprocess.check_output(['git','status','--porcelain','--','FraktalCore/HMI'],cwd=R,text=True).strip()
counts={}
for label in ('ab_suite_01','root_suite_01','focused_05','native_replay_01','annotations_replay_01'):
 rows=re.findall(r'Ran ([0-9]+) tests?',(W/(label+'.log')).read_bytes().decode('ascii','ignore'));assert rows,label;counts[label]=int(rows[-1])
assert counts==dict(ab_suite_01=2681,root_suite_01=85,focused_05=63,native_replay_01=25,annotations_replay_01=1),counts
capacity=read(W/'prepare_01/press_capacity.json');assert capacity['VerifiedFit'] and capacity['SourceUnchanged']
assert not P.exists();P.mkdir(parents=True)
for path in sorted(W.rglob('*')):
 if not path.is_file() or path.suffix.lower() not in ('.py','.json','.log'):continue
 if path.name in ('seal_01.log','seal_01_exit.json','command_keys_before_01.py'):continue
 rel=path.relative_to(W);group='Preparation' if len(rel.parts)>1 else 'Investigation' if path.suffix=='.py' else 'Gates'
 dest=P/group/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
artifacts=[]
for path in sorted(W.rglob('*')):
 if not path.is_file():continue
 if path.suffix.lower() not in ('.l5x','.acd','.exe','.zip') and path.name!='command_keys_before_01.py':continue
 artifacts.append(dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size,archived=False))
with (P/'Preparation/artifact_bindings.json').open('x',encoding='utf-8') as f:json.dump(dict(schema='fraktal.ab.c5b3-prepared-artifacts',schemaVersion=1,artifacts=artifacts),f,indent=2)
summary=dict(schema='fraktal.ab.c5b3-policy-offline-qualification',schemaVersion=1,passed=True,parentCommit=freeze['head'],sourceFiles=len(freeze['files']),counts=counts,requiredGates=required,press=read(W/'prepare_press_01.json'),pressCapacity=capacity,genealogyReuse=read(W/'genealogy_reuse_01.json'),schemaPress=read(W/'schema_press_02.json'),schemaGenealogy=read(W/'schema_genealogy_01.json'),tokenProof=read(W/'token_proof_01.json'),layoutProof=read(W/'layout_proof_01.json'),predicateProof=read(W/'policy_predicates_02.json'),factAccounting=read(W/'policy_fact_accounting_01.json'),runtimeBindings=runtime,controllerAccess=False,downloads=0,nativeAcceptance='S6-Q after C7; other HX consumers/launchers remain open',credentialsArchived=False)
with (P/'Gates/summary.json').open('x',encoding='utf-8') as f:json.dump(summary,f,indent=2)
manifest=[dict(path=p.relative_to(P).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(P.rglob('*')) if p.is_file()]
with (P/'artifact_manifest.json').open('x',encoding='utf-8') as f:json.dump(dict(schema='fraktal.evidence.artifacts',schemaVersion=1,files=manifest),f,indent=2)
print(json.dumps(dict(passed=True,files=len(manifest),manifestSha256=sha(P/'artifact_manifest.json'),counts=counts),indent=1))
