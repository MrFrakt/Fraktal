from pathlib import Path
import difflib,json,subprocess,sys,xml.etree.ElementTree as ET
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools'
for target in ['EchoController','PhysicalController']:
    subprocess.run([sys.executable,str(W/'run_logged.py'),'sdk_audit_'+target+'_01',sys.executable,
        str(T/'fraktal_ab_sdk_log_gate.py'),str(W/('build_'+target+'_01.log')),
        '--require','Open project','--require','Build','--require','Save As'],check=True,cwd=R)
old=ET.parse('C:/work/fraktal-ab-s4b-owner-20261029/offline_01/canonical_owner_01.L5X').getroot()
new=ET.parse(W/'canonical_owner_01.L5X').getroot()
for section in ['DataTypes','Tags']:
    assert [ET.tostring(e) for e in old.findall('.//'+section)]==[ET.tostring(e) for e in new.findall('.//'+section)],section
def routines(root):
    return {e.get('Name'):'\n'.join(''.join(l.itertext()) for l in e.findall('./STContent/Line'))
        for e in root.findall('.//Routine')}
before,after=routines(old),routines(new);assert before.keys()==after.keys()
changes=[]
for name,text in after.items():
    if text==before[name]:continue
    diff=list(difflib.ndiff(before[name].splitlines(),text.splitlines()))
    removed=[l[2:] for l in diff if l.startswith('- ')]
    added=[l[2:] for l in diff if l.startswith('+ ')]
    assert removed and len(removed)==len(added)
    assert all('.WriteRevision :=' in l for l in removed+added),(name,removed,added)
    assert all('FRK_Press_CanonicalConfigWork.Revision' in l for l in added)
    changes.append(dict(routine=name,removed=removed,added=added))
assert sum(len(c['added']) for c in changes)==2,changes
value=dict(passed=True,identicalDataTypesAndInitialTags=True,changedAssignments=2,changes=changes,
    generatedOnly=True,controllerAccess=False)
with (W/'source_delta_01.json').open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
print(json.dumps(value))
