from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
from fraktal_ab_st_format import tokens
W=Path(__file__).parent;P=W/'prepare_01'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def routines(p):
 root=ET.parse(p).getroot();out={}
 for owner in [*root.iter('AddOnInstructionDefinition'),*root.iter('Program')]:
  for r in owner.findall('./Routines/Routine'):
   key=owner.get('Name')+'/'+r.get('Name')
   out[key]=(r.get('Type'),tokens('\n'.join(n.text or '' for n in r.iter() if n.tag in ('Line','Text'))) if r.get('Type')=='ST' else ET.tostring(r))
 return out
before,after=routines(P/'reference_press.L5X'),routines(P/'press.L5X');key='FRK_PressProgram/FRK_Press_CopyFixtureObservation'
assert set(before)==set(after)
expected=['FRK_Press_FixtureObservation.Cfg0_SchemaVersion := FRK_T_PressParCfgTag.SchemaVersion;',
          'FRK_Press_FixtureObservation.Cfg0_BaselineWorkMs := FRK_T_PressParCfgTag.BaselineWorkMs;',
          'FRK_Press_FixtureObservation.ConfigAudit_Head := FRK_Press_ConfigAudit.Head;']
for field in ('Sequence','Kind','Value','SourceKey','Revision'):
 expected += ['FOR FRK_Press_FixtureIndex := 0 TO 15 DO',f'FRK_Press_FixtureObservation.ConfigAudit_{field}[FRK_Press_FixtureIndex] := FRK_Press_ConfigAudit.{field}[FRK_Press_FixtureIndex];','END_FOR;']
expected += ['FRK_Press_FixtureObservation.Profiler_LastWork := FRK_Press_Profiler.LastWork;',
             'FRK_Press_FixtureObservation.AirPressureMonitor_OutImm_PressureOk := FRK_Press_InstAirPressureMonitor.OutImm_PressureOk;']
assert after[key]==('ST',before[key][1]+tokens('\n'.join(expected)))
unchanged=[k for k in before if k!=key];assert all(before[k]==after[k] for k in unchanged)
# The feature reference came from frozen C5a source, with only its two approved flags enabled.
# Every code producer is frozen except the explicit fixture surface catalogue.
reference=W/'reference/FraktalCore/PLC/Allen-Bradley/tools';producers=[]
for file in reference.glob('fraktal_ab_*.py'):
 if file.name in ('fraktal_ab_fixture_observation.py','fraktal_ab_press_s6_collapse_echo38.py','fraktal_ab_fixture_reads.py','fraktal_ab_harness_commands.py','fraktal_ab_phase5_execute.py','fraktal_ab_phase6_execute.py','fraktal_ab_press_execute.py','fraktal_ab_canonical_live.py'):continue
 assert sha(file)==sha(T/file.name),file.name
 producers.append(dict(path=file.name,sha256=sha(file)))
old=Path('C:/work/fraktal-ab-c5-control-20261106/prepare_03/genealogy.L5X');assert sha(old)==sha(P/'genealogy.L5X')
result=dict(passed=True,referenceCommit='df647e2f34b28e7c5f9962d4b93a2ea564755862',referenceSha256=sha(P/'reference_press.L5X'),pressSha256=sha(P/'press.L5X'),genealogySha256=sha(old),unchangedRoutines=len(unchanged),exactFixtureTokenAppend=list(tokens('\n'.join(expected))),frozenProducers=producers,controllerAccess=False)
with (W/'token_proof_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(passed=True,unchangedRoutines=len(unchanged),frozenProducers=len(producers))))
