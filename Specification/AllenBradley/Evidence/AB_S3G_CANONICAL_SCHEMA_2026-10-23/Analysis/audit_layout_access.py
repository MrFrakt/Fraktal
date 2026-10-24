"""Audit the S3g layout probe and its inherited provider request type."""
import json,sys,xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import replace
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_access_audit as access
import fraktal_ab_canonical_publication as canonical
import fraktal_ab_config_provider as provider
import fraktal_ab_config_provider_wire as wire
import fraktal_ab_genealogy_s3f_demo as demo
project,output=map(Path,sys.argv[1:])
if output.exists():raise SystemExit('new evidence required')
app=replace(demo.application(),canonical_publication_stage=9)
prior=json.loads(Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21/Runtime/candidate_access_01.json').read_text())['topLevel']
public=set(prior['Public'])|{b['SourceSymbol'] for b in canonical.publication_bindings(app)}|{s['ResponseSymbol'] for s in provider.services(app)}
report=access.audit(access.controller_tags(project),set(prior['Mailbox']),public,set(prior['Plant']))
types={n.get('Name'):n for n in ET.parse(project).getroot().findall('./Controller/DataTypes/DataType')}
findings=[];expected=[ET.fromstring(s).get('Name') for s in canonical.data_types(app)]
for name in expected:
    if name not in types:findings.append('missing canonical type '+name);continue
    level='Read/Write' if name==wire.INPUT else 'Read Only'
    for m in types[name].findall('Members/Member'):
        if m.get('ExternalAccess')!=level:findings.append(name+'.'+m.get('Name')+' access '+str(m.get('ExternalAccess')))
result=dict(passed=report['Conforms'] and not findings,topLevel=report,canonicalTypeCount=len(expected),canonicalMemberAccessFindings=findings)
with output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(passed=result['passed'],tags=report['TagsAudited'],canonicalTypes=len(expected),findings=findings)))
raise SystemExit(0 if result['passed'] else 1)
