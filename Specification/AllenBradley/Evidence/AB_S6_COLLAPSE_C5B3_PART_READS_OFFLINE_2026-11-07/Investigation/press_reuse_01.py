from pathlib import Path
import hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;E=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5B3_PHASE5_OFFLINE_2026-11-06'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
pins=json.loads((E/'Preparation/artifact_bindings.json').read_bytes())['artifacts'];rows=[]
for name in ('press','shelving'):
 source=W/(name+'_01.L5X');prior=Path('C:/work/fraktal-ab-c5b3-phase5-control-20261106/prepare_01')/(name+'.L5X')
 bound=next(row for row in pins if Path(row['path'])==prior)
 assert sha(prior)==bound['sha256'] and sha(source)==bound['sha256'],(name,sha(source),bound)
 acd=prior.with_suffix('.ACD');row=next(row for row in pins if Path(row['path'])==acd);assert sha(acd)==row['sha256']
 rows.append(dict(profile=name,sourceSha256=sha(source),acdSha256=sha(acd),qualifiedEvidence=E.relative_to(R).as_posix()))
with (W/'press_reuse_01.json').open('x',encoding='utf-8') as f:json.dump(dict(passed=True,profiles=rows,controllerAccess=False),f,indent=2)
print(json.dumps(dict(passed=True,unchangedProfiles=len(rows))))
