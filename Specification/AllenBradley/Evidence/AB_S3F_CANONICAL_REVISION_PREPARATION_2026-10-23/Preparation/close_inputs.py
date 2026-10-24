"""Bind capacity, source closure and unchanged predecessor generation/replays."""
from pathlib import Path
import ast,datetime,hashlib,json,subprocess,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
E=Path('C:/work/fraktal-ab-s3f-20261022/prepare_3816927132f14d4998876bc62e22f342')
R=Path('C:/work/fraktal-ab-s3f-20261022/runtime_fe75ae9724bb4b48ab66839171f73767');TOOLS=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cap=json.loads((W/'capacity_auto_01.json').read_text());prior=json.loads((W/'baseline_capacity.json').read_text())
assert cap['VerifiedFit'] and cap['CanonicalSha256']==(W/'canonical.sha256').read_text().strip()
for key in ('Sha256','UsedStandardBlocks','AvailableBlocks','TotalBlocks'):cap['Baseline'+key]=prior['CanonicalSha256' if key=='Sha256' else key]
cap['DeltaUsedStandardBlocks']=cap['UsedStandardBlocks']-prior['UsedStandardBlocks']
with (W/'capacity_review.json').open('x') as f:json.dump(cap,f,indent=2)
with (W/'canonical_prepared_compare.json').open('x') as f:f.write((W/'prepared_readback_01.log').read_text())
before=json.loads((R/'source_verification_01.json').read_text())['sha256']
paths={ROOT/n for n in before}|{TOOLS/(n+'.py') for n in ('fraktal_ab_s3f_revision_execute','test_fraktal_ab_s3f_revision_fixture')}
pending=list(paths);seen=set()
while pending:
 p=pending.pop()
 if p in seen:continue
 seen.add(p)
 if p.suffix!='.py':continue
 tree=ast.parse(p.read_text(encoding='utf-8-sig'))
 names={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
 names.update(a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names)
 for name in names:
  if not name:continue
  dependency=TOOLS/(name+'.py')
  if dependency.exists() and dependency not in paths:paths.add(dependency);pending.append(dependency)
bindings=dict(sourceCommit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),localPythonImportsClosed=True,
 sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)})
with (W/'source_bindings_01.json').open('x') as f:json.dump(bindings,f,indent=2)
text=(E/'compatibility.py').read_text().replace('genealogy_s3f_05.L5X','genealogy_s3f_revision_01.L5X')
with (W/'compatibility.py').open('x') as f:f.write(text)
print(json.dumps(dict(passed=True,sourceBindings=len(paths),capacityBlocks=cap['UsedStandardBlocks'],deltaBlocks=cap['DeltaUsedStandardBlocks'],preparedAcdSha256=cap['CanonicalSha256'],sourceSha256=sha(W/'genealogy_s3f_revision_01.L5X'))))
