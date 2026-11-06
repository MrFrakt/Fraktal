"""Seal C5a only after every final gate passes. No controller or Git mutation."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
P=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5A_OFFLINE_2026-11-06'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def read(p):return json.loads(Path(p).read_bytes())
required=['ab_suite_05','storage_followup_01','gateway_close_03','coherence_focused_02','preparation_04','qualification_04','gateway_locked_dependencies_01','gateway_compile_01','gateway_help_01','gateway_tests_01','gateway_analyze_01','dart_version_01','root_suite_02','ab_spec_02','ab_contracts_02','consistency_02']
for label in required:assert read(W/(label+'_exit.json'))['exitCode']==0,label
assert read(W/'prepare_c5a_04.json')['passed'] and read(W/'qualification_04.json')['passed']
source=read(W/'tools_freeze_05.json')
assert all(sha(R/entry['path'])==entry['sha256'] for entry in source['files'])
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==source['head']
for name,digest in read(W/'unrelated_bindings_01.json').items():assert sha(R/name)==digest,name
bindings=read(W/'gateway_bindings_01.json')
for name,digest in bindings['sources'].items():assert sha(R/name)==digest,name
assert sha(W/'fraktal_gateway.exe')==bindings['gatewaySha256']
counts={}
for label in ('ab_suite_05','root_suite_02','storage_followup_01','gateway_close_03','coherence_focused_02'):
 raw=(W/(label+'.log')).read_bytes().decode('ascii','ignore')
 matches=re.findall(r'Ran (\d+) tests?',raw);assert matches,label
 counts[label]=int(matches[-1])
assert counts['ab_suite_05']==2612 and counts['root_suite_02']==85,counts
assert not P.exists();P.mkdir(parents=True)
# Only controlled nonbinary run outputs enter the payload. Credentials are
# never read by this workflow. ACD/L5X/EXE artifacts are bound by hash below.
files=[]
for path in sorted(W.rglob('*')):
 if not path.is_file() or path.suffix.lower() not in ('.py','.json','.log'):continue
 relative=path.relative_to(W)
 if path.parent==W:
  group='Investigation' if path.suffix=='.py' or path.name.startswith(('fact_','account_')) else 'Gates'
 else:group='Preparation'
 target=P/group/relative;target.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(path,target);files.append(target)
artifacts=[]
for path in sorted(W.rglob('*')):
 if path.is_file() and (path.suffix.lower() in ('.l5x','.acd','.exe') or path.name.lower().endswith('.acd.bak')):
  artifacts.append(dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size,archived=False))
with (P/'Preparation/artifact_bindings.json').open('x',encoding='utf-8') as f:json.dump(dict(schema='fraktal.ab.c5a-prepared-artifacts',schemaVersion=1,artifacts=artifacts,controllerAccess=False,downloads=0),f,indent=2)
summary=dict(schema='fraktal.ab.c5a-offline-qualification',schemaVersion=1,passed=True,parentCommit=source['head'],sources=len(source['files']),counts=counts,requiredGates=required,productionGatewayAndClientFilesUnchanged=bindings['sourceFiles'],gatewayTests=44,preparation=read(W/'prepare_c5a_04.json'),qualification=read(W/'qualification_04.json'),capacity=dict(genealogy=read(W/'prepare_03/genealogy_capacity.json'),press=read(W/'prepare_04/press_capacity.json')),controllerAccess=False,downloads=0,nativeAcceptance='S6-Q after C7; not performed',flutterFullSuite='Not run: no HMI source change; gateway/client bytes pinned and fresh Dart gateway checks pass',credentialsArchived=False)
with (P/'Gates/summary.json').open('x',encoding='utf-8') as f:json.dump(summary,f,indent=2)
manifest=[dict(path=str(path.relative_to(P)).replace('\\','/'),sha256=sha(path),bytes=path.stat().st_size) for path in sorted(P.rglob('*')) if path.is_file()]
with (P/'artifact_manifest.json').open('x',encoding='utf-8') as f:json.dump(dict(schema='fraktal.evidence.artifacts',schemaVersion=1,files=manifest),f,indent=2)
print(json.dumps(dict(passed=True,files=len(manifest),manifestSha256=sha(P/'artifact_manifest.json'),counts=counts),indent=1))
