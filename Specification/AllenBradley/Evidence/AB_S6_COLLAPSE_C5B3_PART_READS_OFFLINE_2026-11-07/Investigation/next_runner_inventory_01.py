from pathlib import Path
import ast,hashlib,json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools';rows=[]
for name in ('fraktal_ab_tower_execute.py','fraktal_ab_part_execute.py','fraktal_ab_press_canonical_execute.py','fraktal_ab_genealogy_execute.py','fraktal_ab_text_resource_execute.py','fraktal_ab_resource_execute.py'):
 p=T/name;tree=ast.parse(p.read_text(encoding='utf-8'));parents={child:node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
 for node in ast.walk(tree):
  if not isinstance(node,ast.Call):continue
  target=ast.unparse(node.func)
  if target not in ('projection.read_document','projection.read_access','part.read','part.project','part.uid','host.read','px.read_layout','tower.project','comm.Close','live.documents','live.FileMedium'):continue
  current=node;owner=None;conditions=[]
  while current in parents:
   current=parents[current]
   if isinstance(current,(ast.FunctionDef,ast.AsyncFunctionDef)) and owner is None:owner=current.name
   if isinstance(current,ast.If):conditions.append(ast.unparse(current.test))
  rows.append(dict(file=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest().upper(),line=node.lineno,function=owner,call=target,enclosingIfTests=conditions))
result=dict(passed=True,scope='Static next-slice inventory. Includes intentionally retained legacy branches; not all entries are reachable on a collapsed profile.',calls=rows,nextSlice=['Migrate shared tower bootstrap, access snapshots and cleanup onto canonical/O10 observations, retaining session/identity/manifest guards.', 'Compare configuration against an immutable isolated seed and the owned Dart adapter medium; use the existing canonical document verifier instead of a Python keeper.', 'Pre-open an independent guarded read-only observer before LAMP_TEST. Explicitly close command/gateway/host ownership, retain the complete 3.2-second no-controller-traffic interval and the original elapsed < 4 seconds rule.', 'After a successful intentional disconnect observation, create a fresh explicit fixture ownership phase. Do not restart a failed ProcessLease or clear its failure state.', 'Migrate standalone press seeding/launcher after the shared runner lifecycle is qualified.'],controllerAccess=False)
with (W/'next_runner_inventory_01.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(dict(passed=True,staticCallSites=len(rows),controllerAccess=False)))
