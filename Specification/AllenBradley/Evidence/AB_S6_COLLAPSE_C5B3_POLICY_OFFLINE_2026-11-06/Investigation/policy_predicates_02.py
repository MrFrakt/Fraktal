from pathlib import Path
import ast,copy,hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;PREFIX='FraktalCore/PLC/Allen-Bradley/tools/'
class Normalize(ast.NodeTransformer):
 def visit_Call(self,n):
  n=self.generic_visit(n)
  f=ast.unparse(n.func)
  if f in ('projection.read_access','users.read_access','read_access'):
   n.func=ast.Name(id='native_access',ctx=ast.Load());return n
  if f=='mf.numeric_key':return ast.Call(func=ast.Name(id='published_key',ctx=ast.Load()),args=[n.args[1]],keywords=[])
  if f=='views.numeric_key':return ast.Call(func=ast.Name(id='published_key',ctx=ast.Load()),args=[n.args[1]],keywords=[])
  if f in ('mb.config_ordinal','views.config_capability'):return ast.Call(func=ast.Name(id='published_capability',ctx=ast.Load()),args=[n.args[1]],keywords=[])
  if isinstance(n.func,ast.Attribute) and n.func.attr=='get':
   subject=n.func.value
   if ast.unparse(subject)=='client.state.sets.values' or isinstance(subject,ast.Call) and ast.unparse(subject.func)=='client.values':
    n.func.value=ast.Name(id='state',ctx=ast.Load())
  return n
 def visit_Subscript(self,n):
  n=self.generic_visit(n)
  if isinstance(n.value,ast.Name) and n.value.id=='public' and 'Shelved' in ast.unparse(n.slice):return ast.Name(id='published_shelved',ctx=ast.Load())
  return n

def cases(raw):
 result={}
 for n in ast.walk(ast.parse(raw)):
  if not isinstance(n,ast.Call):continue
  name=ast.unparse(n.func)
  if name not in ('check','px.row'):continue
  if len(n.args)<3:continue
  label=ast.dump(n.args[0],include_attributes=False)
  normalized=ast.dump(Normalize().visit(copy.deepcopy(n.args[-1])),include_attributes=False)
  assert label not in result,label
  result[label]=dict(label=ast.unparse(n.args[0]),predicate=normalized,source=ast.unparse(n.args[-1]))
 return result
modules=[]
for file in ('fraktal_ab_phase6_access_execute.py','fraktal_ab_phase6_data_execute.py','fraktal_ab_phase6_shelving_execute.py'):
 path=PREFIX+file;before=subprocess.check_output(['git','show','f68314e3b:'+path],cwd=R).decode();after=(R/path).read_text(encoding='utf-8')
 a,b=cases(before),cases(after);assert set(a)==set(b),file
 differences=[dict(case=a[k]['label'],before=a[k]['source'],after=b[k]['source']) for k in a if a[k]['predicate']!=b[k]['predicate']]
 assert not differences,(file,differences)
 modules.append(dict(path=path,cases=len(a),predicates=[dict(case=a[k]['label'],before=a[k]['source'],after=b[k]['source']) for k in a]))
result=dict(passed=True,parentCommit='f68314e3b2d46d4497be5e204818ae5df5bd26f0',modules=modules,normalization='Only deployed key/capability lookup and independently read public text/annunciation; every logical operator, value comparison, no-change predicate and time bound retained',protocolSubject='The old direct Frame probe becomes the approved typed gateway path with independent native ACK; no legacy writer or reinitialization remains in the collapsed branch',controllerAccess=False)
with (W/'policy_predicates_02.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(passed=True,caseSites=sum(x['cases'] for x in modules))))
