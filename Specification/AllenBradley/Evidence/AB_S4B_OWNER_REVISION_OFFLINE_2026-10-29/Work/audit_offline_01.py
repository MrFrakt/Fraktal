from pathlib import Path
import json,subprocess,sys,xml.etree.ElementTree as ET,re
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0,str(T))
import fraktal_ab_owner_read_bindings as owner
import fraktal_ab_genealogy_s4b_owner_demo as demo
a=demo.application()
def run(label,*args):
    subprocess.run([sys.executable,str(W/'run_logged.py'),label,*map(str,args)],cwd=R,check=True)
for target in ('EchoController','PhysicalController'):
    run('sdk_audit_'+target+'_01',sys.executable,T/'fraktal_ab_sdk_log_gate.py',W/('build_'+target+'_01.log'),
        '--require','Open project','--require','Build','--require','Save As')
    run('access_'+target+'_01',sys.executable,W/'audit_access.py',W/(target+'_owner_readback_01.L5X'),W/('access_'+target+'_01.json'))
root=ET.parse(W/'canonical_owner_01.L5X').getroot()
sources={r.get('Name'):'\n'.join(''.join(x.itertext()) for x in r.findall('./STContent/Line'))
         for r in root.findall('.//Routine')}
paths=owner.module_paths(a)
protected={p.replace('/','.')+'.Status.'+m for p in paths for m in owner.HEADER_MEMBERS}
mutable={p.replace('/','.')+'.Status.State' for p in paths}|{a.name+'.Status.ConfigRev'}
writes=[]
for routine,source in sources.items():
    for target in re.findall(r'\b([A-Za-z_][\w.\[\]]*)\s*:=',source):
        if target in protected:
            writes.append(dict(routine=routine,target=target))
    for instruction,args in re.findall(r'\b(CPS|COP|MOV)\(([^()]*)\)',source):
        fields=args.split(',')
        if len(fields)>1:
            dest=fields[1].strip()
            assert not any(p==dest or p.startswith(dest+'.') or dest.startswith(p+'.') for p in protected), (routine,instruction,dest)
assert {r['target'] for r in writes}==mutable and len(writes)==len(mutable)
source=sources['FRK_Press_ScanCanonical']; compact=lambda s:re.sub(r'\s+','',s)
for i,path in enumerate(paths):
    target=path.replace('/','.')+'.Status.State'
    expression=re.search(re.escape(target)+r'\s*:=\s*([^;]+);',source)[1]
    assert compact(source).count(compact('\n'.join(owner.write_header(a,i,'State',expression))))==1
target=a.name+'.Status.ConfigRev';expression=re.search(re.escape(target)+r'\s*:=\s*([^;]+);',source)[1]
assert compact(source).count(compact('\n'.join(owner.write_header(a,0,'ConfigRev',expression))))==1
close=compact('\n'.join(owner.close_headers(a)))
assert compact(source).count(close)==1
assert compact(source).index(close)>max(compact(source).index(compact(r['target']+':=')) for r in writes)
result=dict(passed=True,mutableWriters=writes,staticIdentityWriters=0,headerLeaves=29,
    allProtectedWritesGuarded=True,wholeRecordCopyBypasses=0,bodyClosesAfterAllWriters=True,
    nativeAcceptanceClaim=False)
with (W/'writer_coverage_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
