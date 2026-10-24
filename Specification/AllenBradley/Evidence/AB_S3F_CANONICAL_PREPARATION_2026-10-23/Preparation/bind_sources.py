"""Bind selected sources and derive their local Python import closure."""
from pathlib import Path
import ast,datetime,hashlib,json,subprocess
ROOT=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
TOOLS=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
old=json.loads(Path('C:/work/fraktal-ab-s3e-20261022/prepare_768bb43d842d4b008ab1dfb322741aea/source_bindings_01.json').read_text())
paths={ROOT/p for p in old['sha256']}
extra=('fraktal_ab_canonical_config','fraktal_ab_config_provider','fraktal_ab_config_provider_client','fraktal_ab_config_provider_wire',
 'fraktal_ab_genealogy_s3f_demo','fraktal_ab_s3f_equivalence','fraktal_ab_s3f_fixture_execute',
 'test_fraktal_ab_canonical_config','test_fraktal_ab_config_provider_client','test_fraktal_ab_s3f_fixture',
 'fraktal_ab_readback','fraktal_ab_set_broker','fraktal_ab_gateway','fraktal_ab_sets','fraktal_ab_mailbox')
paths.update(TOOLS/(n+'.py') for n in extra)
paths.add(ROOT/'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/Params/PL_Fraktal.TcGVL')
pending=list(paths);visited=set()
while pending:
 p=pending.pop()
 if p in visited:continue
 visited.add(p)
 if p.suffix!='.py':continue
 tree=ast.parse(p.read_text(encoding='utf-8-sig'))
 names={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
 names.update(a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names)
 for name in names:
  if not name:continue
  dependency=TOOLS/(name+'.py')
  if dependency.exists() and dependency not in paths:paths.add(dependency);pending.append(dependency)
report=dict(sourceCommit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),localPythonImportsClosed=True,
 sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)})
with (W/'source_bindings_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(dict(passed=True,sourceBindings=len(paths),localPythonImportsClosed=True)))
