from pathlib import Path
import hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
OLD=Path('C:/work/fraktal-ab-c5-control-20261106')
P=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5A_OFFLINE_2026-11-06'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def read(p):return json.loads(Path(p).read_bytes())
relative='Gates/gateway_bindings_01.json';archived=P/relative
manifest=read(P/'artifact_manifest.json')
row=next(e for e in manifest['files'] if e['path']==relative)
assert sha(archived)==row['sha256']
assert (OLD/'gateway_bindings_01.json').read_bytes()==archived.read_bytes()
committed=subprocess.check_output(['git','show','HEAD:'+archived.relative_to(R).as_posix()],cwd=R)
assert committed==archived.read_bytes()
held=read(archived)
for name,digest in held['sources'].items():assert sha(R/name)==digest,name
assert sha(OLD/'fraktal_gateway.exe')==held['gatewaySha256']
assert sha(W/'fraktal_host_adapter.exe')==read(W/'host_cli_help_01.json')['executableSha256']
result=dict(schema='fraktal.ab.c5b2-runtime-package-bindings',schemaVersion=1,passed=True,
 parentCommit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),
 inheritedEvidence=archived.relative_to(R).as_posix(),inheritedEvidenceSha256=sha(archived),
 inheritedManifestSha256=sha(P/'artifact_manifest.json'),sources=held['sources'],
 gateway=dict(path=str(OLD/'fraktal_gateway.exe'),sha256=sha(OLD/'fraktal_gateway.exe')),
 hostAdapter=dict(path=str(W/'fraktal_host_adapter.exe'),sha256=sha(W/'fraktal_host_adapter.exe')),
 controllerAccess=False,credentialsRead=False)
with (W/'runtime_bindings_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(passed=True,sources=len(held['sources']),archivedBindingMatchesCommittedBlob=True,controllerAccess=False)))
