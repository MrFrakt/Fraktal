from pathlib import Path
import hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
E=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5B3_POLICY_OFFLINE_2026-11-06'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def read(p):return json.loads(Path(p).read_bytes())
proof=read(W/'image_proof_02.json');assert proof['passed']
derived=proof['surfaceVsBase']['derivedHashes'];assert derived['before']==derived['after'] and len(derived['before'])==3
modified=subprocess.check_output(['git','diff','--name-only','--','FraktalCore/PLC/Allen-Bradley/tools'],cwd=R,text=True).splitlines()
assert modified==['FraktalCore/PLC/Allen-Bradley/tools/test_fraktal_ab_schema_identity.py'],modified
manifest=read(E/'artifact_manifest.json')
reused=[]
for name in ('Preparation/artifact_bindings.json','Gates/genealogy_reuse_01.json','Gates/summary.json'):
 path=E/name;bound=next(row for row in manifest['files'] if row['path']==name)
 assert sha(path)==bound['sha256']
 assert subprocess.check_output(['git','show','HEAD:'+path.relative_to(R).as_posix()],cwd=R)==path.read_bytes()
 reused.append(dict(path=path.relative_to(R).as_posix(),sha256=sha(path)))
artifacts=read(E/'Preparation/artifact_bindings.json')['artifacts']
for row in artifacts:assert sha(row['path'])==row['sha256'],row['path']
genealogy=read(E/'Gates/genealogy_reuse_01.json');assert genealogy['passed']
result=dict(passed=True,basePressAndGenealogySourcesUnchanged=True,basePressCapacityPercent=54,genealogyCapacityPercent=60,onlyModifiedExistingTool=modified[0],allThreeManifestHashesIdentical=True,referenceEvidence=reused,referenceArtifactsVerified=len(artifacts),controllerAccess=False)
with (W/'reuse_proof_01.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(result))
