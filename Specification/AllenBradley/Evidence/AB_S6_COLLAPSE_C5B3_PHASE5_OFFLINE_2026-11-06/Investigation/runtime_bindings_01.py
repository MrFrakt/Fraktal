from pathlib import Path
import hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
E=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5B2_OFFLINE_2026-11-06'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def read(p):return json.loads(Path(p).read_bytes())
bindings=E/'Gates/runtime_bindings_01.json'
assert subprocess.check_output(['git','show','HEAD:'+bindings.relative_to(R).as_posix()],cwd=R)==bindings.read_bytes()
manifest=read(E/'artifact_manifest.json');held=next(r for r in manifest['files'] if r['path']=='Gates/runtime_bindings_01.json');assert held['sha256']==sha(bindings)
record=read(bindings)
for name,digest in record['sources'].items():assert sha(R/name)==digest,name
for name in ('gateway','hostAdapter'):assert sha(record[name]['path'])==record[name]['sha256']
assert not subprocess.check_output(['git','status','--porcelain','--','FraktalCore/HMI'],cwd=R,text=True).strip()
for label in ('dart_tests_01','dart_analyze_01','dart_locked_01','host_compile_01'):
 receipt=E/'Gates'/(label+'_exit.json');entry=next(r for r in manifest['files'] if r['path']==receipt.relative_to(E).as_posix());assert sha(receipt)==entry['sha256'];assert read(receipt)['exitCode']==0
assert '+44: All tests passed!' in (E/'Gates/dart_tests_01.log').read_text(encoding='utf-8')
result=dict(schema='fraktal.ab.c5b3-runtime-package-bindings',schemaVersion=1,passed=True,parentCommit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),inheritedEvidence=bindings.relative_to(R).as_posix(),inheritedEvidenceSha256=sha(bindings),sources=record['sources'],gateway=record['gateway'],hostAdapter=record['hostAdapter'],dartQualification='C5b2 hash-bound 44 tests/analyzer/locked dependencies/host compile reused; no shipping HMI/Dart source changes',controllerAccess=False,credentialsRead=False)
with (W/'runtime_bindings_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(passed=True,sources=len(record['sources']),executables=2,dartTestsReused=44)))
