from pathlib import Path
import hashlib,json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;P=R/'Specification/AllenBradley/Evidence/AB_S6_HOST_SESSION_03_RUNTIME_2026-11-04'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
manifest=json.loads((P/'artifact_manifest.json').read_bytes());rows=[]
for name in ('capture_canonical.json.gz','capture_legacy.json','events_fixture.json'):
 rel='Session/'+name;p=P/rel;digest=sha(p);assert digest==manifest['files'][rel]
 rows.append(dict(path=p.relative_to(R).as_posix(),sha256=digest,bytes=p.stat().st_size))
with (W/'reference_bindings_01.json').open('x',encoding='utf-8') as out:json.dump(dict(passed=True,evidenceManifest=P.relative_to(R).as_posix()+'/artifact_manifest.json',evidenceManifestSha256=sha(P/'artifact_manifest.json'),files=rows,controllerAccess=False),out,indent=2)
print(json.dumps(dict(passed=True,immutableReferenceFiles=len(rows))))
