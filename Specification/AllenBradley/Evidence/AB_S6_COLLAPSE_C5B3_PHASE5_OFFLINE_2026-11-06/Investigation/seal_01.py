from pathlib import Path
import hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;NAME='AB_S6_COLLAPSE_C5B3_PHASE5_OFFLINE_2026-11-06';P=R/'Specification/AllenBradley/Evidence'/NAME
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def read(p):return json.loads(Path(p).read_bytes())
required=['ab_suite_01','root_tests_02','phase5_focused_tests_01','phase5_replay_tests_01','phase5_fact_accounting_01','phase5_predicates_01','layout_proof_03','token_proof_03','genealogy_reuse_02','runtime_bindings_01','declaration_import_01','next_hx_inventory_01','input_bindings_01','managed_tools_01','preparation_01','ab_spec_01','ab_contracts_01','finish_docs_01','consistency_01']
for label in required:assert read(W/(label+'_exit.json'))['exitCode']==0,label
for name in ('phase5_fact_accounting_01','phase5_predicates_01','layout_proof_01','token_proof_01','genealogy_reuse_01','runtime_bindings_01','declaration_import_01','preparation_01','finish_docs_01'):
 assert read(W/(name+'.json'))['passed'],name
freeze=read(W/'tools_freeze_01.json');assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==freeze['head']
for row in freeze['files']:assert sha(R/row['path'])==row['sha256'],row['path']
for row in read(W/'unrelated_before.json'):assert sha(R/row['path'])==row['sha256'],row['path']
for name,row in read(W/'input_bindings_01.json')['inputs'].items():assert sha(row['path'])==row['sha256'],name
for row in read(W/'managed_tools_01.json')['files']:assert sha(row['path'])==row['sha256'],row['path']
runtime=read(W/'runtime_bindings_01.json')
for name,digest in runtime['sources'].items():assert sha(R/name)==digest,name
for name in ('gateway','hostAdapter'):assert sha(runtime[name]['path'])==runtime[name]['sha256']
assert not subprocess.check_output(['git','status','--porcelain','--','FraktalCore/HMI'],cwd=R,text=True).strip()
assert not P.exists();P.mkdir(parents=True)
for path in sorted(W.rglob('*')):
 if not path.is_file() or path.suffix.lower() not in ('.py','.json','.log'):continue
 if path.name in ('seal_01.log','seal_01_exit.json'):continue
 rel=path.relative_to(W);group='Preparation' if len(rel.parts)>1 else 'Investigation' if path.suffix=='.py' else 'Gates'
 dest=P/group/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open('xb') as out:out.write(path.read_bytes())
artifacts=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size,archived=False) for p in sorted(W.rglob('*')) if p.is_file() and p.suffix.lower() in ('.l5x','.acd','.exe','.zip')]
with (P/'Preparation/artifact_bindings.json').open('x',encoding='utf-8') as out:json.dump(dict(schema='fraktal.ab.c5b3-phase5-prepared-artifacts',schemaVersion=1,artifacts=artifacts),out,indent=2)
summary=dict(
 schema='fraktal.ab.c5b3-phase5-offline-qualification',
 schemaVersion=1,
 passed=True,
 parentCommit=freeze['head'],
 sourceFiles=len(freeze['files']),
 requiredGates=required,
 counts=read(W/'finish_docs_01.json')['counts'],
 factAccounting=dict(prior=102,added=39,total=141,udt='FRK_T_PressFixtureV2_2A276D94'),
 predicateProof=dict(rows=21,waits=29,directLegacyCallsBefore=16,unconditionalLegacyCallsAfter=0),
 preparation=read(W/'preparation_01.json'),
 pressCapacity=read(W/'prepare_01/press_capacity.json'),
 shelvingCapacity=read(W/'prepare_01/shelving_capacity.json'),
 layoutProof=read(W/'layout_proof_01.json'),
 tokenProof=read(W/'token_proof_01.json'),
 genealogyReuse=read(W/'genealogy_reuse_01.json'),
 runtimeBindings=runtime,
 declarationImport=read(W/'declaration_import_01.json'),
 controllerAccess=False,
 downloads=0,
 credentialsArchived=False,
 nativeAcceptance='S6-Q after C7; offline harness, replay and image qualification only',
 remaining='C5b3 Part/genealogy/inherited runners and canonical press launcher; C5c/V6.12; C6/C7; native S6-Q; final census/deletion/gates/spec activation; hardware-only S7 deferred/excluded by O2',
)
with (P/'Gates/summary.json').open('x',encoding='utf-8') as out:json.dump(summary,out,indent=2)
manifest=[dict(path=p.relative_to(P).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(P.rglob('*')) if p.is_file()]
with (P/'artifact_manifest.json').open('x',encoding='utf-8') as out:json.dump(dict(schema='fraktal.evidence.artifacts',schemaVersion=1,files=manifest),out,indent=2)
print(json.dumps(dict(passed=True,files=len(manifest),manifestSha256=sha(P/'artifact_manifest.json'),counts=summary['counts'])))
