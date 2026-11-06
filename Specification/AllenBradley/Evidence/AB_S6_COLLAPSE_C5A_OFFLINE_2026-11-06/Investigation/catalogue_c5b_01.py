"""C5b preparation: literal source sites, not an inferred runtime-completeness claim.
Never imports a harness, reads a credential, or contacts a controller.
"""
import ast,hashlib,json,sys
from pathlib import Path
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools'
old=json.loads((R/'Specification/AllenBradley/Evidence/AB_S6_HX_FACT_ACCOUNTING_OFFLINE_2026-11-03/Investigation/hx_fact_accounting_02.json').read_bytes())
freeze={r['path']:r['sha256'] for r in json.loads((W/'tools_freeze_05.json').read_bytes())['files']}
rows=[]
for h in old['harnesses']:
 p=T/(h['module']+'.py');raw=p.read_bytes();digest=hashlib.sha256(raw).hexdigest().upper()
 assert digest==freeze[p.relative_to(R).as_posix()]
 tree=ast.parse(raw.decode('utf-8'));imports={}
 for n in ast.walk(tree):
  if isinstance(n,ast.Import):
   for a in n.names:imports[a.asname or a.name]=a.name
  elif isinstance(n,ast.ImportFrom):
   for a in n.names:imports[a.asname or a.name]=(n.module or '')+'.'+a.name
 def name(n):
  if isinstance(n,ast.Name):return imports.get(n.id,n.id)
  if isinstance(n,ast.Attribute):return name(n.value)+'.'+n.attr
  return '<dynamic>'
 sites=[];cases=[]
 for n in ast.walk(tree):
  if not isinstance(n,ast.Call):continue
  f=name(n.func);method=f.rsplit('.',1)[-1]
  category=None
  if f.startswith('fraktal_ab_projection.'):category='legacy-projection'
  elif f.startswith('fraktal_ab_gateway.'):category='legacy-gateway'
  elif f.startswith(('fraktal_ab_live.','fraktal_ab_set_broker.')):category='legacy-host-interception'
  elif f.startswith('fraktal_ab_press_execute.') and method in ('command','manual','seed_sequence','await_response'):
   category='shared-command-facade; arguments and remaining reads still need review'
  elif method in ('command_writes','write_config_set','restore_command'):category='legacy-command/stage candidate'
  elif method in ('Write','Read','read_layout','read_flat','read_scalar'):category='native-read-or-stimulus; scope must be reviewed'
  if category:
   sites.append(dict(line=n.lineno,call=f,category=category,keywords=[k.arg for k in n.keywords],
                     commandKind=ast.unparse(n.args[1]) if f=='fraktal_ab_press_execute.command' and len(n.args)>1 else None))
  if method in ('row','check') and len(n.args)>=4:
   case=n.args[0]
   cases.append(dict(line=n.lineno,name=case.value if isinstance(case,ast.Constant) and isinstance(case.value,str) else None,
      nameExpression=ast.unparse(case) if not isinstance(case,ast.Constant) else None,
      predicateAstSha256=hashlib.sha256(ast.dump(n.args[-1],include_attributes=False).encode()).hexdigest().upper()))
 rows.append(dict(module=h['module'],sourceSha256=digest,sites=sorted(sites,key=lambda r:r['line']),caseCandidates=sorted(cases,key=lambda r:r['line']),
   subjectDisposition='retire with RT; no station read to port' if h['module'] in ('fraktal_ab_s9_read_execute','fraktal_ab_s9_mutations') else 'migrate/review inheritance'))
result=dict(schema='fraktal.ab.c5b-source-site-catalogue',schemaVersion=1,method='Literal AST calls and row/check predicate hashes; no inferred surface or runtime coverage claim. Dynamic helpers and inherited reads need manual review.',harnesses=rows,controllerAccess=False,credentialsRead=False)
with Path(sys.argv[1]).open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(harnesses=len(rows),sourceSites=sum(len(h['sites']) for h in rows),caseCandidates=sum(len(h['caseCandidates']) for h in rows),controllerAccess=False)))
