"""Source-only starting inventory for the next migration; no acceptance claim."""
from pathlib import Path
import ast,hashlib,json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools'
rows=[]
for name in ('fraktal_ab_phase5_execute.py','fraktal_ab_part_execute.py','fraktal_ab_genealogy_execute.py'):
 source=(T/name).read_text(encoding='utf-8');tree=ast.parse(source);calls=[];predicates=[]
 for func in [n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]:
  for node in ast.walk(func):
   if not isinstance(node,ast.Call):continue
   called=ast.unparse(node.func)
   if called.startswith('projection.') or called=='px.read_layout':
    calls.append(dict(function=func.name,line=node.lineno,call=ast.unparse(node)))
   if called in ('px.row','row'):
    predicates.append(dict(function=func.name,line=node.lineno,arguments=[ast.unparse(arg) for arg in node.args]))
 rows.append(dict(path=(T/name).relative_to(R).as_posix(),sha256=hashlib.sha256((T/name).read_bytes()).hexdigest().upper(),legacyCalls=calls,rowSites=predicates))
result=dict(schema='fraktal.ab.next-hx-source-inventory',schemaVersion=1,analysisOnly=True,controllerAccess=False,acceptanceClaim=False,files=rows,healthPrecondition='Phase5 health_rows also requires a standing metrics-unavailable event; account explicitly during its migration, preserving the base exclusion and predicates.')
with (W/'next_hx_inventory_01.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps([dict(path=row['path'],legacyCalls=len(row['legacyCalls']),rowSites=len(row['rowSites'])) for row in rows]))
