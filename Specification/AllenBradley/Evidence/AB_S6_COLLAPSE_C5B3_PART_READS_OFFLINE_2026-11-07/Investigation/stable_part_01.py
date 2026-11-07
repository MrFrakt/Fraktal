from pathlib import Path
import hashlib,json,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
import fraktal_ab_fixture_reads as views
from test_fraktal_ab_part_canonical import CanonicalPart, APP, SESSION
CanonicalPart.setUpClass();case=CanonicalPart();case.setUp()
try:actual=views.part_values(object(),app=APP)
finally:case.doCleanups()
source=SESSION/'events_fixture.json';legacy=json.loads(source.read_bytes())
matches=[]
for index,row in enumerate(legacy['rows']):
 if row.get('passed') and row.get('part')==actual:matches.append(dict(index=index,language=row['language'],case=row['case']))
assert matches,dict(uid=actual['Part/Uid'],stamp=actual['Part/Result/Stamp'])
result=dict(passed=True,reference=source.relative_to(R).as_posix(),referenceSha256=hashlib.sha256(source.read_bytes()).hexdigest().upper(),matchingAcceptedRows=matches,partLeaves=len(actual),valueTypesEqual=True,scope='same accepted session and identical retained result including UID/stamp; not new native or same-scan proof',controllerAccess=False)
with (W/'stable_part_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
