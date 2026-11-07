from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;NAME='AB_S6_COLLAPSE_C5B2_OFFLINE_2026-11-06';P=R/'Specification/AllenBradley/Evidence'/NAME
OLD=Path('C:/work/fraktal-ab-c5-control-20261106')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def read(p):return json.loads(Path(p).read_bytes())
required=['clients_07','native_replay_01','ab_suite_02','root_suite_02','ab_spec_01','ab_contracts_01','consistency_01','token_proof_02','genealogy_reuse_01','predicate_accounting_01','dart_version_01','dart_locked_01','host_compile_01','dart_tests_01','dart_analyze_01','ab_spec_02','ab_contracts_02','consistency_02']
for label in required:assert read(W/(label+'_exit.json'))['exitCode']==0,label
assert read(W/'prepare_press_02.json')['passed']
for name in ('schema_press_01','schema_genealogy_01','token_proof_02','genealogy_reuse_01'):assert read(W/(name+'.json'))['passed']
freeze=read(W/'tools_freeze_02.json');assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==freeze['head']
for row in freeze['files']:assert sha(R/row['path'])==row['sha256'],row['path']
for name,digest in read(W/'unrelated_before.json').items():assert sha(R/name)==digest,name
assert not subprocess.check_output(['git','status','--porcelain','--','FraktalCore/HMI'],cwd=R,text=True).strip(),'shipping HMI tree changed'
bindings=read(OLD/'gateway_bindings_01.json')
for name,digest in bindings['sources'].items():assert sha(R/name)==digest,name
assert sha(OLD/'fraktal_gateway.exe')==bindings['gatewaySha256']
counts={}
for label in ('ab_suite_02','root_suite_02','clients_07','native_replay_01'):
 raw=(W/(label+'.log')).read_bytes().decode('ascii','ignore');match=re.findall(r'Ran ([0-9]+) tests?',raw);assert match,label;counts[label]=int(match[-1])
assert counts['ab_suite_02']==2664 and counts['root_suite_02']==85,counts
assert '+44: All tests passed!' in (W/'dart_tests_01.log').read_text(encoding='utf-8')
capacity=read(W/'prepare_01/press_capacity.json');assert capacity['VerifiedFit'] and capacity['SourceUnchanged']
assert read(W/'host_cli_help_01.json')['passed']
assert sha(W/'fraktal_host_adapter.exe')==read(W/'host_cli_help_01.json')['executableSha256']
assert not P.exists();P.mkdir(parents=True)
# The frozen reference archives and binaries stay private, hash-bound below.
# Archive only controlled nonbinary investigation/preparation/test records.
for path in sorted(W.rglob('*')):
 if not path.is_file() or path.suffix.lower() not in ('.py','.json','.log') or 'reference' in path.relative_to(W).parts:continue
 if path.name in ('seal_03.log','seal_03_exit.json'):continue
 relative=path.relative_to(W);group='Preparation' if len(relative.parts)>1 else 'Investigation' if path.suffix=='.py' else 'Gates'
 target=P/group/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
artifacts=[]
for path in sorted(W.rglob('*')):
 if not path.is_file() or 'reference' in path.relative_to(W).parts:continue
 if path.suffix.lower() not in ('.l5x','.acd','.exe','.zip') and not path.name.lower().endswith('.acd.bak'):continue
 artifacts.append(dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size,archived=False))
with (P/'Preparation/artifact_bindings.json').open('x',encoding='utf-8') as f:json.dump(dict(schema='fraktal.ab.c5b2-prepared-artifacts',schemaVersion=1,artifacts=artifacts),f,indent=2)
summary=dict(schema='fraktal.ab.c5b2-offline-qualification',schemaVersion=1,passed=True,parentCommit=freeze['head'],sourceFiles=len(freeze['files']),counts=counts,requiredGates=required,press=read(W/'prepare_press_02.json'),pressCapacity=capacity,genealogyReuse=read(W/'genealogy_reuse_01.json'),schemaPress=read(W/'schema_press_01.json'),schemaGenealogy=read(W/'schema_genealogy_01.json'),tokenProof=read(W/'token_proof_02.json'),accounting=read(W/'predicate_accounting_01.json'),hmiSourceFilesUnchanged=bindings['sourceFiles'],hmiTests='Fresh Dart gateway tests/analyzer, locked dependencies and host compile; Flutter not rerun because shipping HMI/gateway/client files are unchanged',controllerAccess=False,downloads=0,nativeAcceptance='S6-Q after C7; sets/documents/HX integration and scan not performed',credentialsArchived=False)
with (P/'Gates/summary.json').open('x',encoding='utf-8') as f:json.dump(summary,f,indent=2)
manifest=[dict(path=path.relative_to(P).as_posix(),sha256=sha(path),bytes=path.stat().st_size) for path in sorted(P.rglob('*')) if path.is_file()]
with (P/'artifact_manifest.json').open('x',encoding='utf-8') as f:json.dump(dict(schema='fraktal.evidence.artifacts',schemaVersion=1,files=manifest),f,indent=2)
print(json.dumps(dict(passed=True,files=len(manifest),manifestSha256=sha(P/'artifact_manifest.json'),counts=counts),indent=1))
