"""C5a: only the accounted O10 key copy/call changes emitted executable code."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
from fraktal_ab_st_format import tokens
W=Path(__file__).parent;OLD=Path('C:/work/fraktal-ab-s6-host-20261104/prepare');P=W/'prepare_02'
def routines(path):
 root=ET.parse(path).getroot();out={}
 for owner in [*root.iter('AddOnInstructionDefinition'),*root.iter('Program')]:
  for r in owner.findall('./Routines/Routine'):
   key=owner.get('Name')+'/'+r.get('Name')
   if r.get('Type')=='ST':out[key]=('ST',tokens('\n'.join(n.text or '' for n in r.iter('Line'))))
   else:out[key]=(r.get('Type'),ET.tostring(r,encoding='unicode'))
 return root,out
expected='FRK_Press_FixtureObservation.Mailbox_DiagnosticKey := FRK_Press_HmiResponse.DiagnosticKey;'
call='JSR(FRK_Press_CopyFixtureObservation,0);'
rows=[]
for name,before in [('genealogy','s6_collapse_17.L5X'),('press','press_collapse_17.L5X')]:
 old,ot=routines(OLD/before);new,nt=routines(P/(name+'.L5X'))
 copy=[k for k in nt if k.endswith('/FRK_Press_CopyFixtureObservation')];assert len(copy)==1
 key=copy[0]
 assert nt[key][0]=='ST'
 key_tokens=tokens(expected)
 body=nt[key][1]
 assert body[-len(key_tokens):]==key_tokens
 if name=='genealogy':
  assert key not in ot and body==key_tokens
  del nt[key]
  canonical=next(k for k in nt if k.endswith('/FRK_Press_ScanCanonical'))
  c=tokens(call);code=nt[canonical][1]
  hits=[i for i in range(len(code)-len(c)+1) if code[i:i+len(c)]==c];assert len(hits)==1
  i=hits[0];nt[canonical]=('ST',code[:i]+code[i+len(c):])
 else:nt[key]=('ST',body[:-len(key_tokens)])
 assert set(nt)==set(ot),(set(ot)-set(nt),set(nt)-set(ot))
 differences=[k for k in ot if ot[k]!=nt[k]];assert not differences,differences
 # Everything outside the two intended fixture changes has exactly the same
 # initialization and type/tag bytes. Record schema deltas independently below.
 import fraktal_ab_schema_identity as schema
 a,b=schema.surface(OLD/before),schema.surface(P/(name+'.L5X'))
 diffs=schema.differences(a,b)
 allowed={('FRK_Press_FixtureObservation','added' if name=='genealogy' else 'changed'),
          ('FRK_T_PressFixtureObservationV1','removed')}
 extra=[]
 for path,change in diffs:
  if name=='genealogy' and path=='FRK_Press_FixtureObservation' and change=='added':continue
  if path.startswith('FRK_Press_FixtureObservation.') and change in ('added','changed'):continue
  if path=='FRK_T_PressFixtureObservationV1' and change=='removed':continue
  if path.startswith('FRK_T_PressFixtureV2_') and change=='added':continue
  if name=='press' and (
    (path in ('FRK_T_PressCanonicalManifestV66',) and change=='removed') or
    (path in ('FRK_T_PressCanonicalManifestV67','FRK_T_CanonicalReadCoherenceV67') and change=='added') or
    (path in ('FRK_Press_CanonicalManifest.DataType','FRK_Press_CanonicalManifest.Data.SchemaMinor') and change=='changed') or
    (path in ('FRK_Press_CanonicalManifest.Data.ReadCoherenceBindings','FRK_Press_CanonicalManifest.Data.ReadCoherenceBindingsCount','FRK_Press_CanonicalManifest.Data.ReadCoherenceBindingsCapacity') and change=='added')):continue
  extra.append((path,change))
 assert not extra,extra
 rows.append(dict(profile=name,oldRoutines=len(ot),newRoutines=len(routines(P/(name+'.L5X'))[1]),unchangedAfterExactFixtureDelta=True,surfaceDifferences=[dict(path=p,change=c) for p,c in diffs],beforeSha256=hashlib.sha256((OLD/before).read_bytes()).hexdigest().upper(),afterSha256=hashlib.sha256((P/(name+'.L5X')).read_bytes()).hexdigest().upper()))
result=dict(passed=True,profiles=rows,controllerAccess=False)
with Path(sys.argv[1]).open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=1))
