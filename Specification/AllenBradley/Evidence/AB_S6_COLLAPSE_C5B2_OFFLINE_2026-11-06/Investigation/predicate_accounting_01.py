from pathlib import Path
import ast,hashlib,json,subprocess,sys
R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
W=Path(__file__).parent;path='FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_phase6_sets_execute.py'
before=subprocess.check_output(['git','show','ca786c6c9:'+path],cwd=R).decode();after=(R/path).read_text(encoding='utf-8')
class Reads(ast.NodeTransformer):
 def visit_Call(self,n):
  n=self.generic_visit(n)
  if isinstance(n.func,ast.Attribute) and n.func.attr=='numeric_key':return ast.Call(func=ast.Name(id='_published_key'),args=[n.args[1]],keywords=[])
  if isinstance(n.func,ast.Attribute) and n.func.attr=='read_records':n.func=ast.Name(id='read_records')
  if isinstance(n.func,ast.Attribute) and n.func.attr in ('FileStore','ReadOnlyStore'):n.func=ast.Name(id='_reopen_store')
  return n
 def visit_IfExp(self,n):
  n=self.generic_visit(n)
  if ast.dump(n.body,include_attributes=False)==ast.dump(n.orelse,include_attributes=False):return n.body
  return n
 def visit_Subscript(self,n):
  n=self.generic_visit(n)
  if isinstance(n.value,ast.Name) and n.value.id=='values' or isinstance(n.value,ast.Attribute) and ast.unparse(n.value)=='client.state.sets.values':
   return ast.Call(func=ast.Name(id='_value'),args=[n.slice],keywords=[])
  return n
def rows(source):
 fn=next(n for n in ast.parse(source).body if isinstance(n,ast.AsyncFunctionDef) and n.name=='exercise')
 out={}
 for n in ast.walk(fn):
  if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='row':
   label=ast.unparse(n.args[0]);original=ast.unparse(n.args[-1]);normalized=Reads().visit(ast.parse(original,mode='eval'))
   out[label]=dict(original=original,normalized=ast.dump(normalized,include_attributes=False))
 return out
a,b=rows(before),rows(after);assert set(a)==set(b)
errors=[name for name in a if a[name]['normalized']!=b[name]['normalized']];assert not errors,errors
result=dict(passed=True,parentCommit='ca786c6c9e549a9ff60287cba4c290afca9ac289',caseSites=len(a),predicates=[dict(case=name,before=a[name]['original'],after=b[name]['original']) for name in a],normalization='Only acquisition aliases, the portable read-only file reopen, and deployed numeric keys; no logical operator or value predicate removed',protocolSubjectAdaptation='sets_retain_the_gateway_write_gate now tests the packaged read-only deployment instead of Python _ConnState.authenticated; the refusal/unchanged-sequence predicate is unchanged',controllerAccess=False)
with (W/'predicate_accounting_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(passed=True,caseSites=len(a))))
