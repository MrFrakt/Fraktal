"""C5 read-site provenance. Parse only; no controller or runtime projection import."""
import ast,hashlib,json,sys
from pathlib import Path
T=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
R=T.parents[3]
old=json.loads((R/'Specification/AllenBradley/Evidence/AB_S6_HX_FACT_ACCOUNTING_OFFLINE_2026-11-03/Investigation/hx_fact_accounting_02.json').read_bytes())
MODULES=('PressRam','Door','PartSlide','PartPresentSensor','TwoHand','AirPressureMonitor')
KNOWN={'read_unit':'Unit','unit':'Unit','await_unit':'Unit','read_chart':'Chart','await_chart':'Chart',
 'read_config_audit':'ConfigAudit','profile_raw':'Profiler','read_persist':'Persist',
 'read_oee':'Oee','read_profiler':'Profiler','read_state_flags':'StateFlags','read_system_health':'Health',
 'read_alarm_log':'AlarmRing','log_raw':'AlarmRing','health_raw':'Health','flags_raw':'StateFlags'}
TAGS={'alarm_active_tag':'AlarmActive','alarm_ring_tag':'AlarmRing','profiler_tag':'Profiler','oee_tag':'Oee',
 'state_flags_tag':'StateFlags','health_probe_tag':'HealthProbe','system_health_tag':'Health',
 'release_report_tag':'ReleaseReport','config_persist_tag':'Persist','audit_tag':'ConfigAudit'}
# Tagged abstract values: ('surface', frozenset), ('literal', tuple),
# ('tuple', tuple of abstract values), ('dict', tuple of key/value pairs).
def surfaces(names):return ('surface',frozenset(names))
def literals(values):return ('literal',tuple(values))
EMPTY=('unknown',())

class Scan:
 def __init__(self,path):
  self.path=path;self.source=path.read_text(encoding='utf-8');self.tree=ast.parse(self.source)
  self.facts={};self.unresolved=[];self.summaries={};self.globalenv={}
  for n in self.tree.body:
   if isinstance(n,ast.Assign):self.assign(n.targets[0],self.infer(n.value,self.globalenv),self.globalenv)
 def key(self,n,env):
  v=self.infer(n,env)
  return tuple(x for x in v[1] if isinstance(x,str)) if v[0]=='literal' else ()
 def infer(self,n,env):
  if isinstance(n,ast.Constant):return literals((n.value,))
  if isinstance(n,ast.Name):return env.get(n.id,EMPTY)
  if isinstance(n,(ast.Tuple,ast.List,ast.Set)):
   values=[self.infer(v,env) for v in n.elts]
   if all(v[0]=='literal' for v in values):return literals(tuple(x for v in values for x in v[1]))
   return ('tuple',tuple(values))
  if isinstance(n,ast.Dict):
   return ('dict',tuple((k.value,self.infer(v,env)) for k,v in zip(n.keys,n.values) if isinstance(k,ast.Constant)))
  if isinstance(n,ast.Subscript):
   base=self.infer(n.value,env);keys=self.key(n.slice,env)
   if base[0]=='dict' and len(keys)==1:return dict(base[1]).get(keys[0],EMPTY)
  if isinstance(n,ast.Call):
   name=n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id if isinstance(n.func,ast.Name) else ''
   if name in ('read_module','await_module'):
    names=self.key(n.args[1],env) if len(n.args)>1 else ()
    shape=surfaces(names or MODULES)
   elif name=='read_access':
    audit=any(k.arg=='audit' and isinstance(k.value,ast.Constant) and k.value.value for k in n.keywords)
    shape=surfaces(('AccessAudit' if audit else 'Access',))
   elif name=='read_data_access':
    policy=any(k.arg=='policy' and isinstance(k.value,ast.Constant) and k.value.value for k in n.keywords)
    shape=surfaces(('DataPolicy' if policy else 'DataLevels',))
   elif name in KNOWN:shape=surfaces((KNOWN[name],))
   elif name=='read_layout' and len(n.args)>1:
    tag=n.args[1]
    method=tag.func.attr if isinstance(tag,ast.Call) and isinstance(tag.func,ast.Attribute) else ''
    if method=='ctx_tag_for':
     names=self.key(tag.args[1],env);shape=surfaces(names or MODULES)
    elif method in TAGS:shape=surfaces((TAGS[method],))
    elif isinstance(tag,ast.Name) and tag.id in ('ACTIVE','RING'):shape=surfaces(('AlarmActive' if tag.id=='ACTIVE' else 'AlarmRing',))
    else:shape=EMPTY
   elif name=='get' and isinstance(n.func,ast.Attribute):
    base=self.infer(n.func.value,env);keys=self.key(n.args[0],env) if n.args else ()
    shape=dict(base[1]).get(keys[0],EMPTY) if base[0]=='dict' and len(keys)==1 else EMPTY
   else:shape=self.summaries.get(name,EMPTY)
   if name.startswith('await_'):return ('tuple',(shape,EMPTY))
   return shape
  if isinstance(n,ast.BoolOp):
   values=[self.infer(v,env) for v in n.values]
   return next((v for v in values if v[0]=='surface'),EMPTY)
  if isinstance(n,ast.IfExp):return self.infer(n.body,env)
  return EMPTY
 def assign(self,target,value,env):
  if isinstance(target,ast.Name):env[target.id]=value
  elif isinstance(target,(ast.Tuple,ast.List)):
   values=value[1] if value[0]=='tuple' else [EMPTY]*len(target.elts)
   for t,v in zip(target.elts,values):self.assign(t,v,env)
 def record(self,base,keys,node):
  if base[0]!='surface':return
  if not keys:self.unresolved.append(dict(line=node.lineno,expression=ast.get_source_segment(self.source,node)))
  for surface in base[1]:
   for key in keys:
    self.facts.setdefault((surface,key),set()).add(node.lineno)
 def expr(self,n,env):
  if n is None:return
  if isinstance(n,ast.Subscript):self.record(self.infer(n.value,env),self.key(n.slice,env),n)
  if isinstance(n,ast.Call):
   if isinstance(n.func,ast.Attribute) and n.func.attr=='get' and n.args:
    self.record(self.infer(n.func.value,env),self.key(n.args[0],env),n)
   name=n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id if isinstance(n.func,ast.Name) else ''
   shape=self.infer(n,env)
   if shape[0]=='tuple' and name.startswith('await_'):shape=shape[1][0]
   for arg in [*n.args,*(k.value for k in n.keywords)]:
    if isinstance(arg,ast.Lambda):
     nested=dict(env)
     if shape[0]=='surface' and arg.args.args:nested[arg.args.args[0].arg]=shape
     self.expr(arg.body,nested)
  for child in ast.iter_child_nodes(n):
   if not isinstance(child,ast.Lambda):self.expr(child,env)
 def statements(self,body,env):
  returns=[]
  for n in body:
   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):continue
   if isinstance(n,ast.Assign):
    self.expr(n.value,env)
    for target in n.targets:self.assign(target,self.infer(n.value,env),env)
   elif isinstance(n,ast.AnnAssign):
    self.expr(n.value,env)
    if n.value:self.assign(n.target,self.infer(n.value,env),env)
   elif isinstance(n,(ast.For,ast.AsyncFor)):
    nested=dict(env);iteration=self.infer(n.iter,env)
    if isinstance(n.iter,ast.Attribute) and n.iter.attr=='modules':iteration=literals(MODULES)
    self.assign(n.target,iteration,nested)
    self.statements(n.body,nested);self.statements(n.orelse,nested)
   elif isinstance(n,(ast.If,ast.While)):
    self.expr(n.test,env);self.statements(n.body,dict(env));self.statements(n.orelse,dict(env))
   elif isinstance(n,(ast.With,ast.AsyncWith,ast.Try)):
    self.statements(n.body,env)
    for attr in ('orelse','finalbody'):self.statements(getattr(n,attr,[]),env)
    for handler in getattr(n,'handlers',[]):self.statements(handler.body,dict(env))
   elif isinstance(n,ast.Return):
    self.expr(n.value,env);returns.append(self.infer(n.value,env))
   else:self.expr(n,env)
  return next((v for v in returns if v[0]!='unknown'),EMPTY)
 def run(self):
  for unused in range(3):
   for f in (n for n in ast.walk(self.tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))):
    value=self.statements(f.body,dict(self.globalenv))
    if value[0]!='unknown':self.summaries[f.name]=value
  return dict(module=self.path.stem,sha256=hashlib.sha256(self.path.read_bytes()).hexdigest().upper(),
              facts=[dict(surface=s,member=m,lines=sorted(lines)) for (s,m),lines in sorted(self.facts.items())],
              unresolved=[dict(line=line,expression=expr) for line,expr in sorted({(v['line'],v['expression']) for v in self.unresolved})])

rows=[Scan(T/(h['module']+'.py')).run() for h in old['harnesses']]
result=dict(schema='fraktal.ab.c5-readsite-provenance',schemaVersion=1,precision='conservative module parameters; unresolved uses require review',harnesses=rows)
with Path(sys.argv[1]).open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
for row in rows:print(row['module'],len(row['facts']),'facts',len(row['unresolved']),'unresolved')
