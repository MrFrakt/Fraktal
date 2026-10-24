"""Read-only exact-candidate read-back access audit using its sealed preparation allow-list."""
import json,sys,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_access_audit as access
import fraktal_ab_canonical_publication as canonical
import fraktal_ab_genealogy_s3e_demo as demo
work=Path('C:/work/fraktal-ab-s2-20261021/prepare_3701f795c13b4329891f4eca1346b3a5')
project=Path(sys.argv[1]); output=Path(sys.argv[2])
if output.exists():raise SystemExit('new evidence required')
prior=json.loads(Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21/Runtime/candidate_access_01.json').read_text())['topLevel']
report=access.audit(access.controller_tags(project),set(prior['Mailbox']),set(prior['Public'])|{b['SourceSymbol'] for b in canonical.publication_bindings(demo.application())},set(prior['Plant']))
types={n.get('Name'):n for n in ET.parse(project).getroot().findall('./Controller/DataTypes/DataType')}
findings=[]
expected=[ET.fromstring(s).get('Name') for s in canonical.data_types(demo.application())]
for name in expected:
    if name not in types:findings.append('missing canonical type '+name);continue
    for m in types[name].findall('Members/Member'):
        if m.get('ExternalAccess')!='Read Only':findings.append(name+'.'+m.get('Name')+' access '+str(m.get('ExternalAccess')))
result=dict(passed=report['Conforms'] and not findings,topLevel=report,canonicalTypeCount=len(expected),canonicalMemberAccessFindings=findings)
with output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(passed=result['passed'],tags=report['TagsAudited'],canonicalTypes=len(expected),findings=findings)))
raise SystemExit(0 if result['passed'] else 1)
