from pathlib import Path
import hashlib,json,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
sys.path.insert(0,str(R/'FraktalCore/PLC/Allen-Bradley/tools'))
import test_fraktal_ab_fixture_reads as replay
import fraktal_ab_fixture_observation as observed
new={'AccessState','AccessAudit','AlarmActive','AlarmRing','ReleaseStart'}
facts=observed.facts(replay.APP);rows=[];problems=[]
for surface,member,name,source in facts:
 if surface not in new:continue
 rows.append(dict(surface=surface,member=member.name,dimension=member.dimension,source=source,nativeType='DINT',purpose='Exact source field asserted by Phase 6 access/data/shelving; public text is independently read from Core'))
for label,pair in replay.pairs():
 for surface,member,name,source in facts:
  if surface not in new:continue
  held=replay.legacy_surface(pair,surface)
  if held is None or member.name not in held:problems.append(dict(capture=label,surface=surface,member=member.name,problem='missing native bytes'));continue
  value=held[member.name]
  if member.dimension and (not isinstance(value,list) or len(value)!=member.dimension):problems.append(dict(capture=label,surface=surface,member=member.name,expected=member.dimension,actual=len(value) if isinstance(value,list) else type(value).__name__))
result=dict(passed=not problems,facts=rows,captures=86,problems=problems,controllerAccess=False)
with (W/'policy_fact_accounting_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(passed=not problems,newFacts=len(rows),captures=86,problems=problems[:5])))
raise SystemExit(0 if not problems else 1)
