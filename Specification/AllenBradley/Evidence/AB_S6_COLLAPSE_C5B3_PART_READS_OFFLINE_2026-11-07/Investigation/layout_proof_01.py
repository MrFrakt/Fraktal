from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;sys.path.insert(0,str(R/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_schema_identity as si
old=Path('C:/work/fraktal-ab-c5-control-20261106/prepare_03/genealogy.L5X');new=W/'genealogy_01.L5X'
surfaces=[];fields=[]
for p in (old,new):
 root=ET.parse(p).getroot();tag=next(t for t in root.iter('Tag') if t.get('Name')=='FRK_Press_FixtureObservation')
 kind=tag.get('DataType');definition=next(t for t in root.iter('DataType') if t.get('Name')==kind)
 fields.append([ET.tostring(m) for m in definition.findall('./Members/Member')])
 surface=si.surface(p);surface['tags'].pop('FRK_Press_FixtureObservation');surface['types'].pop(kind);surfaces.append(surface)
assert len(fields[0])==1 and len(fields[1])==13 and fields[0]==fields[1][:1]
check=si.compare(*surfaces);assert check['passed'],check
assert check['derivedHashes']['before']==check['derivedHashes']['after']
result=dict(passed=True,oldFacts=1,newFacts=13,mailboxPrefixByteIdentical=True,otherPublicSurfaceIdentical=True,allThreeManifestHashesIdentical=True,comparison=check,controllerAccess=False)
with (W/'layout_proof_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='comparison'}))
