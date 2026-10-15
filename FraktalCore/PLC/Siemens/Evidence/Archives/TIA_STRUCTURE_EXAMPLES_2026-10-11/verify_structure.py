from pathlib import Path
import sys,os,json,importlib.util,re,hashlib,xml.etree.ElementTree as ET
root=Path('C:/Projects/Fraktal')
sys.path.insert(0,str(root/'FraktalCore/PLC/Siemens/tools'))
import fraktal_tia_examples as EX
spec=importlib.util.spec_from_file_location('roundtrip',root/'FraktalCore/PLC/Siemens/Spikes/S12_TypeMap/verify_roundtrip.py')
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)
w=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Structure_Examples_20261011'
def read(p):
    data=p.read_bytes();return data.decode('utf-16' if data.startswith(b'\xff\xfe') else 'utf-8-sig').replace('\r\n','\n')
events=[json.loads(line) for file in ('16_checked_compile.jsonl','25_preserve_extra.jsonl','27_aliases.jsonl','28_final_sources.jsonl') for line in read(w/file).splitlines() if line.startswith('{')]
assert events[-1]['event']=='plan-complete'
compiles=[e for e in events if e['event']=='compile']
assert len(compiles)==5 and all(e['errors']==0 and e['warnings']==0 for e in compiles)
native=w/'export_station_verified'
results=EX.verify(root/'FraktalCore/PLC/Siemens/Examples/PressDemo/generated',native)
parameter_aliases=0;hidden_value_parameters=0
for name in ('FB_SFC_PressDemoAuto','FB_SFC_PressDemoHome'):
    chart=ET.parse(native/'xml'/(name+'.xml'))
    ns={'i':'http://www.siemens.com/automation/Openness/SW/Interface/v5'}
    section=chart.find('.//Interface/i:Sections/i:Section[@Name="InOut"]',ns)
    for member in section:
        if member.get('Datatype').startswith('"'):
            assert member.find('i:AttributeList',ns) is None,'Re-audit changed native structured parameter-instance flags'
            parameter_aliases+=1
        else:
            flags={a.get('Name'):a.text for a in member.find('i:AttributeList',ns)}
            assert all(flags.get(k)=='false' for k in ('ExternalAccessible','ExternalVisible','ExternalWritable')),(name,member.get('Name'))
            hidden_value_parameters+=1
results['parameter_aliases_with_unproven_runtime_exclusion']=parameter_aliases
results['native_hidden_graph_value_parameters']=hidden_value_parameters
ns={'i':'http://www.siemens.com/automation/Openness/SW/Interface/v5'}
storage_checks=[]
for name,section,member,visible in [('FB_CylinderCM','Static','Device',False),
                                 ('FB_LD_PressDemoAuto','Static','Ready1',False),
                                 ('FB_LD_PressDemoAuto','Static','Seq',True)]:
    xml=ET.parse(native/'xml'/(name+'.xml'))
    members=xml.find('.//Interface/i:Sections/i:Section[@Name="'+section+'"]',ns)
    node=next(m for m in members if m.get('Name')==member)
    flags={a.get('Name'):a.text for a in node.find('i:AttributeList',ns)}
    assert flags['ExternalWritable']=='false' and flags['ExternalAccessible']==str(visible).lower() and flags['ExternalVisible']==str(visible).lower()
    storage_checks.append({'block':name,'member':member,'visible':visible,'writable':False})
results['native_storage_flags']=storage_checks
before=w/'export_station_before/scl'
after=native/'scl'
unchanged=[];changed=[]
for p in before.iterdir():
    if p.suffix not in ('.scl','.udt','.db'):continue
    target=after/p.name;assert target.exists(),p.name
    if R.canonical(read(p))==R.canonical(read(target)):unchanged.append(p.name)
    else:changed.append(p.name)
assert changed==['Main.scl'],changed
main=read(after/'Main.scl')
body=main.split('BEGIN',1)[1].split('END_ORGANIZATION_BLOCK')[0]
calls=re.findall(r'"(\w+)"\(',body)
assert calls==['F_ConfigBenchPrepare','GDB_FraktalMain','F_ConfigBenchObserve'],calls
baseline_main=read(w.parent/'Config_Transactions_20261011/package_v6/40_Main.scl')
baseline_body=baseline_main.split('\nBEGIN\n')[1].split('END_ORGANIZATION_BLOCK')[0]
functions=[]
for name in ('F_ConfigBenchPrepare','F_ConfigBenchObserve'):
    source=read(after/(name+'.scl'))
    functions.append(re.sub(r'#Startup\b','#Initial_Call',source.split('\nBEGIN\n')[1].split('END_FUNCTION')[0]))
reconstructed=functions[0]+'    "GDB_FraktalMain"(Startup := #Initial_Call);\n'+functions[1]
expected_tokens=R.canonical(baseline_body);actual_tokens=R.canonical(reconstructed)
if expected_tokens!=actual_tokens:
    at=next(i for i in range(min(len(expected_tokens),len(actual_tokens))) if expected_tokens[i]!=actual_tokens[i])
    raise AssertionError(('Main reconstruction',at,expected_tokens[max(0,at-5):at+10],actual_tokens[max(0,at-5):at+10]))
last_events=[json.loads(line) for line in read(w/'28_final_sources.jsonl').splitlines() if line.startswith('{')]
groups=[e for e in last_events if e['event']=='group-member']
assert groups and all(e.get('path') for e in groups)
results.update({'compile_results':[{'errors':e['errors'],'warnings':e['warnings']} for e in compiles],
                'unchanged_baseline_sources':len(unchanged),'changed_baseline_sources':changed,
                'main_calls':calls,'main_body_reconstructed':True,
                'group_members':len(groups),'groups':sorted(set(e['path'] for e in groups)),
                'native_xml_files':len(list((native/'xml').glob('*.xml'))),
                'native_source_files':len(list(after.iterdir())),
                'driver_sha256':hashlib.sha256((root/'FraktalCore/PLC/Siemens/tools/TiaCli/bin/candidate_structure_examples/Fraktal.Tia.Cli.exe').read_bytes()).hexdigest()})
(w/'20_structure_verified.json').write_bytes((json.dumps(results,indent=2)+'\n').encode('ascii'))
print(json.dumps(results,indent=2))
