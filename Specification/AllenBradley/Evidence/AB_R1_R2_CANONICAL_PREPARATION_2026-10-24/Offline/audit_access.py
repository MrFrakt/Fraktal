"""Audit canonical/legacy effective access with the read-only observation frame."""
import sys,json,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path('C:/Users/SoftIndVM/Fraktal');sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_access_audit as access
import fraktal_ab_canonical_observation as observation
import fraktal_ab_canonical_publication as pub
import fraktal_ab_config_provider as provider
import fraktal_ab_config_provider_wire as wire
import fraktal_ab_genealogy_s3i_demo as demo
import fraktal_ab_s3i_native_checks as native
project,output=map(Path,sys.argv[1:]);assert not output.exists();from dataclasses import replace;app=replace(demo.application(),canonical_table_driven=True,canonical_type_manifest=True)
prior=json.loads((ROOT/'Specification/AllenBradley/Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21/Runtime/candidate_access_01.json').read_text())['topLevel']
public=(set(prior['Public'])|{b['SourceSymbol'] for b in pub.publication_bindings(app)}|{s['ResponseSymbol'] for s in provider.services(app)}
        |set(observation.public_tags(app))|{native.tag(app)})
report=access.audit(access.controller_tags(project),set(prior['Mailbox']),public,set(prior['Plant']))
types={n.get('Name'):n for n in ET.parse(project).getroot().findall('./Controller/DataTypes/DataType')}
expected={ET.fromstring(s).get('Name') for s in pub.data_types(app)}
findings=[]
for name in expected:
    if name not in types:findings.append('missing '+name);continue
    level='Read/Write' if name==wire.INPUT else 'Read Only'
    for m in types[name].findall('Members/Member'):
        if m.get('ExternalAccess')!=level:findings.append(name+'.'+m.get('Name'))
frame=types.get(observation.type_name(app))
names=[m.get('Name') for m in frame.findall('Members/Member')] if frame is not None else []
if names!=[*observation.HEADER,*observation.sources(app)]:findings.append('observation frame members differ')
if 'Status' in names:findings.append('observation frame would be discovered as a root')
result=dict(passed=report['Conforms'] and not findings,topLevel=report,canonicalTypes=len(expected),
            observationTags=list(observation.public_tags(app)),memberAccessFindings=findings)
with output.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(passed=result['passed'],types=len(expected),findings=findings)))
raise SystemExit(0 if result['passed'] else 1)
