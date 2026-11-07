from pathlib import Path
import ast,hashlib,json,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;P=Path('FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_part_execute.py')
old=subprocess.check_output(['git','show','HEAD:'+P.as_posix()],cwd=R).decode();new=(R/P).read_text(encoding='utf-8')
class Normalize(ast.NodeTransformer):
 def visit_Call(self,node):
  name=ast.unparse(node.func)
  if name=='part.read' or name=='views.part_identity':return ast.Name(id='part_identity_snapshot',ctx=ast.Load())
  return self.generic_visit(node)
def checks(text):
 tree=ast.parse(text);run=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Run');rows=[]
 for method in run.body:
  if not isinstance(method,ast.FunctionDef):continue
  for n in ast.walk(method):
   if isinstance(n,ast.Call) and ast.unparse(n.func)=='self.check':
    rows.append((method.name,'check',ast.dump(Normalize().visit(n.args[0]),include_attributes=False)))
   elif isinstance(n,ast.Call) and ast.unparse(n.func)=='self.wait':
    rows.append((method.name,'wait',ast.dump(Normalize().visit(n.args[0]),include_attributes=False)))
 return rows
a,b=checks(old),checks(new);assert a==b,(a,b)
result=dict(passed=True,parentCommit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),checks=sum(k=='check' for _,k,_ in a),waits=sum(k=='wait' for _,k,_ in a),scope='all self.check and self.wait predicates in Run; only equivalent decoded Part identity acquisition normalized',oldSha256=hashlib.sha256(old.encode()).hexdigest().upper(),newSha256=hashlib.sha256((R/P).read_bytes()).hexdigest().upper(),controllerAccess=False)
with (W/'predicate_proof_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
