from pathlib import Path
import hashlib,json,re,sys,xml.etree.ElementTree as ET
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
import fraktal_ab_fixture_observation as fixture
import fraktal_ab_generate as gen
import fraktal_ab_press_s6_collapse_echo38 as press_profile
import fraktal_ab_press_s6_shelving_echo38 as shelving_profile
import fraktal_ab_schema_identity as si
import fraktal_ab_st_model as st
from fraktal_ab_st_format import tokens
from test_fraktal_ab_schema_identity import DECLARATIONS
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
E_POLICY=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5B3_POLICY_OFFLINE_2026-11-06'
E_SHELVING=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5B3_SHELVING_OFFLINE_2026-11-06'
old_press=Path('C:/work/fraktal-ab-c5b3-control-20261106/prepare_01/press.L5X')
old_shelving=Path('C:/work/fraktal-ab-c5b3-shelving-control-20261106/prepare_01/shelving.L5X')
new_press=W/'press_01.L5X'
new_shelving=W/'shelving_01.L5X'
policy_pins=json.loads((E_POLICY/'Preparation/artifact_bindings.json').read_bytes())['artifacts']
assert any(Path(r['path'])==old_press and r['sha256']==sha(old_press) for r in policy_pins)
shelving_pins=json.loads((E_SHELVING/'Preparation/artifact_bindings.json').read_bytes())['artifacts']
assert any(Path(r['path'])==old_shelving and r['sha256']==sha(old_shelving) for r in shelving_pins)

def bodies(root,names=None):
 names=names or {};result={}
 for kind,nodes in (('program',root.iter('Program')),('aoi',root.iter('AddOnInstructionDefinition'))):
  for node in nodes:
   for routine in node.iter('Routine'):
    key=f"{kind}:{names.get(node.get('Name'),node.get('Name'))}/{routine.get('Name')}"
    text='\n'.join(n.text or '' for n in routine.iter() if n.tag in ('Line','Text'))
    for new,old in names.items():
     text=re.sub(r'\b'+re.escape(new)+r'\b',old,text)
    result[key]=[(t.kind,t.text) for t in st.tokenize(text) if t.kind!='eof']
 return result

def compare_against_prior(before_path,after_path,app):
 surfaces=[si.surface(p) for p in (before_path,after_path)]
 rootname=next(t[:-len('_MfHeader')] for t in surfaces[0]['tags'] if t.endswith('_MfHeader'))
 tables=[]
 for surface in surfaces:
  tags=surface['tags'];h=tags[rootname+'_MfHeader']['Data']
  keys={r['PortableKey']['DATA'].strip().strip("'"):int(r['NumericKey'])
        for r in tags[rootname+'_MfLocalization']['Data'] if int(r['PortableKey']['LEN'])}
  tables.append((keys,int(h['LocalizationCount']),int(h['ConfigRevision'])))
 (a_keys,ac,ar),(b_keys,bc,br)=tables
 mapping={a_keys[k]:b_keys[k] for k in a_keys if k in b_keys and a_keys[k]!=b_keys[k]}
 for x,y in ((ac,bc),(ac+1,bc+1),(ar,br)):
  if x!=y:mapping[x]=y
 roots=[ET.parse(p).getroot() for p in (before_path,after_path)]
 oldnames={n.get('Name') for n in roots[0].iter('AddOnInstructionDefinition')}
 names={}
 for node in roots[1].iter('AddOnInstructionDefinition'):
  name=node.get('Name')
  if name in oldnames:continue
  base=re.sub(r'R8C4[0-9A-F]{8}(Rev)?$',r'R8C4\1',name)
  candidates=[old for old in oldnames if re.sub(r'R8C4[0-9A-F]{8}(Rev)?$',r'R8C4\1',old)==base]
  if not candidates and name.startswith('FRK_U_'):
   prefix=re.sub(r'_C4[0-9A-F]{8}$','',name)
   candidates=[old for old in oldnames if old.startswith(prefix)]
  assert len(candidates)==1,(name,candidates)
  names[name]=candidates[0]
 code=[bodies(roots[0]),bodies(roots[1],names)]
 assert set(code[0])==set(code[1])
 type_name=next(t.get('DataType') for t in roots[0].iter('Tag') if t.get('Name')==fixture.tag(app))
 prior={m.get('Name') for t in roots[0].iter('DataType') if t.get('Name')==type_name for m in t.findall('./Members/Member')}
 copy_key='program:FRK_PressProgram/FRK_Press_CopyFixtureObservation'
 copy_body=list(code[1][copy_key]);deltas=[]
 expected={x['surface']+'.'+x['member']:x for x in json.loads((W/'phase5_fact_accounting_01.json').read_bytes())['facts']}
 for surface,m,name,source in fixture.facts(app):
  if name in prior:continue
  held=expected.pop(surface+'.'+m.name);assert source==held['source'] and m.dimension==held['dimension']
  if m.dimension:
   stmt=f'FOR FRK_Press_FixtureIndex := 0 TO {m.dimension-1} DO FRK_Press_FixtureObservation.{name}[FRK_Press_FixtureIndex] := {source}.{m.name}[FRK_Press_FixtureIndex]; END_FOR;'
  else:stmt=f'FRK_Press_FixtureObservation.{name} := {source}.{m.name};'
  wanted=[(t.kind,t.text) for t in st.tokenize(stmt) if t.kind!='eof']
  hits=[i for i in range(len(copy_body)-len(wanted)+1) if copy_body[i:i+len(wanted)]==wanted];assert len(hits)==1,(surface,m.name)
  at=hits[0];del copy_body[at:at+len(wanted)]
  deltas.append(dict(surface=surface,member=m.name,dimension=m.dimension,source=source,tokenCount=len(wanted)))
 assert not expected and len(deltas)==39
 code[1][copy_key]=copy_body
 def pool(root):
  tag=next(t for t in root.find('./Controller/Tags') if t.get('Name')==rootname+'_CanonicalText')
  return [int(n.get('Value')) for n in tag.iter('Element')]
 pools=[pool(r) for r in roots]
 diffs=[];renumbered=offsets=0
 for key in sorted(code[0]):
  a_toks,b_toks=code[0][key],code[1][key]
  if len(a_toks)!=len(b_toks):
   diffs.append(dict(routine=key,reason='token count',counts=[len(a_toks),len(b_toks)]));continue
  for i,(x,y) in enumerate(zip(a_toks,b_toks)):
   if x==y:continue
   if x[0]==y[0]=='number':
    old_n,new_n=int(x[1]),int(y[1])
    if mapping.get(old_n)==new_n:renumbered+=1;continue
    context=[v for _,v in a_toks[max(0,i-4):i]]
    if len(context)==4 and context[0].endswith('_CanonicalTextWork') and context[1:]==['.','Offset',':=']:
     following=a_toks[i+1:i+7]
     if len(following)==6 and [v for _,v in following[2:5]]==['.','Length',':='] and following[5][0]=='number':
      length=int(following[5][1])
      if 0<length and pools[0][old_n:old_n+length]==pools[1][new_n:new_n+length] and len(pools[0][old_n:old_n+length])==length:
       offsets+=1;continue
   diffs.append(dict(routine=key,index=i,before=x,after=y,context=a_toks[max(0,i-6):i]))
 assert not diffs,diffs[:5]
 return dict(
  passed=True,
  beforePath=str(before_path),
  beforeSha256=sha(before_path),
  afterPath=str(after_path),
  afterSha256=sha(after_path),
  routines=len(code[0]),
  renamedAoIs=names,
  renumberedLiterals=renumbered,
  movedPoolOffsets=offsets,
  addedFactCopies=len(deltas),
  addedFactTokens=sum(d['tokenCount'] for d in deltas),
  tokenCounts=dict(
   before=sum(len(v) for v in bodies(roots[0]).values()),
   after=sum(len(v) for v in bodies(roots[1]).values()),
  ),
 )

press_vs_prior=compare_against_prior(old_press,new_press,press_profile.application())
shelving_vs_prior=compare_against_prior(old_shelving,new_shelving,shelving_profile.application())

def raw_routines(path):
 root=ET.parse(path).getroot();out={}
 for owner in [*root.iter('AddOnInstructionDefinition'),*root.iter('Program')]:
  for routine in owner.findall('./Routines/Routine'):
   key=owner.get('Name')+'/'+routine.get('Name')
   out[key]=(routine.get('Type'),list(tokens('\n'.join(n.text or '' for n in routine.iter() if n.tag in ('Line','Text')))) if routine.get('Type')=='ST' else ET.tostring(routine))
 return out

pa,pb=raw_routines(new_press),raw_routines(new_shelving);assert set(pa)==set(pb)
changed=[k for k in pa if pa[k]!=pb[k]]
assert changed==['FRK_PressProgram/FRK_Press_ScanHealth'],changed
scan_key=changed[0];before_scan=list(pa[scan_key][1]);after_scan=list(pb[scan_key][1])
idx=gen.HEALTH_EVENTS.index('CONTROLLER_METRICS_UNAVAILABLE')
expected_health=list(tokens(f'{gen.system_health_tag(shelving_profile.application())}.Bad[{idx}] := 1;'))
at=[i for i in range(len(after_scan)-len(expected_health)+1) if after_scan[i:i+len(expected_health)]==expected_health]
assert len(at)==1;del after_scan[at[0]:at[0]+len(expected_health)];assert after_scan==before_scan

surf_press=si.surface(new_press);surf_shelving=si.surface(new_shelving)
same_surface=si.compare(surf_press,surf_shelving);assert same_surface['passed'],same_surface
assert same_surface['derivedHashes']['before']==same_surface['derivedHashes']['after']
baseline=si.read(T/'fixtures/schema_identity/fraktal_ab_press_canonical_echo38.json.gz')
decl_name=DECLARATIONS.get('fraktal_ab_press_s6_collapse_echo38','fraktal_ab_press_s6_collapse_echo38')
declarations=[si.Declared(**row) for row in json.loads((T/'fixtures/schema_identity'/f'{decl_name}.declared.json').read_bytes())]
schema_press=si.compare(baseline,surf_press,declarations);assert schema_press['passed'],schema_press
schema_shelving=si.compare(baseline,surf_shelving,declarations);assert schema_shelving['passed'],schema_shelving

result=dict(
 passed=True,
 parentCommit='7b793c516bc48bb50ae5b2337e99b8ab63e001bd',
 pressVsPrior=press_vs_prior,
 shelvingVsPrior=shelving_vs_prior,
 shelvingVsPress=dict(
  changedRoutines=changed,
  unchangedRoutines=len(pa)-1,
  onlyAddedTokens=expected_health,
  surfaceComparison=same_surface,
 ),
 schemaVsPrecollapse=dict(
  pressPassed=schema_press['passed'],
  shelvingPassed=schema_shelving['passed'],
  coveredChanges=len(schema_press['covered']),
  derivedHashes=same_surface['derivedHashes']['after'],
 ),
 controllerAccess=False,
)
with (W/'token_proof_01.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(dict(
 passed=True,
 pressTokenCounts=press_vs_prior['tokenCounts'],
 shelvingTokenCounts=shelving_vs_prior['tokenCounts'],
 unchangedBetweenProfiles=len(pa)-1,
)))
