"""Audit effective access of the option A image; typed command endpoints are mailboxes."""
import sys,json,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path('C:/Users/SoftIndVM/Fraktal');sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_access_audit as access
import fraktal_ab_canonical_commands as commands
import fraktal_ab_canonical_fieldbus as fieldbus
import fraktal_ab_canonical_mailbox as mailbox
import fraktal_ab_canonical_observation as observation
import fraktal_ab_canonical_publication as pub
import fraktal_ab_command_binding as binding
import fraktal_ab_config_provider as provider
import fraktal_ab_config_provider_wire as wire
import fraktal_ab_generate as gen
import fraktal_ab_press_canonical_echo38 as demo
project,output=map(Path,sys.argv[1:]);assert not output.exists();app=demo.application()
prior=json.loads((ROOT/'Specification/AllenBradley/Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21/Runtime/candidate_access_01.json').read_text())['topLevel']
# The client writes the typed payload and then its commit; both are command ingress.
writable={commands.payload_tag(app),commands.commit_tag(app)}
# The genealogy baseline lists owners the press does not declare; drop exactly those.
undeclared={name for name,absent in ((f'FRK_{app.name}_HostEvents',not app.host_event_capacity),
    (f'FRK_{app.name}_Part',app.part_carrier is None),(f'FRK_{app.name}_SignalTower',app.signal_tower is None)) if absent}
public=((set(prior['Public'])-undeclared)|{b['SourceSymbol'] for b in pub.publication_bindings(app)}|{s['ResponseSymbol'] for s in provider.services(app)}
        |{mailbox.input_tag(app),commands.reply_tag(app)}|set(observation.public_tags(app))|set(gen.force_tags(app))
        |{p['SourceSymbol'] for p in fieldbus.products(app)})
report=access.audit(access.controller_tags(project),set(prior['Mailbox'])|writable,public,set(prior['Plant'])|{m.sample_tag for m in app.io_modules if m.sample_tag})
types={n.get('Name'):n for n in ET.parse(project).getroot().findall('./Controller/DataTypes/DataType')}
expected={ET.fromstring(s).get('Name') for s in pub.data_types(app)}
command_types={commands.PAYLOAD,commands.ARGS,*(commands.string_type(w) for w in {*binding.WIDTHS.values(),255})}
findings=[]
for name in expected:
    if name not in types:findings.append('missing '+name);continue
    level='Read/Write' if name in {wire.INPUT,fieldbus.SAMPLE}|command_types else 'Read Only'
    for m in types[name].findall('Members/Member'):
        if m.get('ExternalAccess')!=level:findings.append(name+'.'+m.get('Name')+' '+str(m.get('ExternalAccess')))
frame=types.get(observation.type_name(app))
names=[m.get('Name') for m in frame.findall('Members/Member')] if frame is not None else []
if names!=[*observation.HEADER,*observation.sources(app)]:findings.append('observation frame members differ')
if 'Status' in names:findings.append('observation frame would be discovered as a root')
sampled=set(observation.sources(app))|set(observation.legacy_sources(app))
for tag in (commands.payload_tag(app),commands.sample_tag(app),commands.work_tag(app)):
    if tag in sampled:findings.append('observation samples command storage '+tag)
result=dict(passed=report['Conforms'] and not findings,topLevel=report,canonicalTypes=len(expected),
            commandIngress=sorted(writable),observationTags=list(observation.public_tags(app)),memberAccessFindings=findings)
with output.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(passed=result['passed'],types=len(expected),findings=findings[:20])))
raise SystemExit(0 if result['passed'] else 1)
