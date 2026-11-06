"""Bind C4 parameter/local defaults and per-instance data to the compiled read-back.
Usage: source.L5X readback.L5X output.json. No controller access.
"""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
source,readback,output=map(Path,sys.argv[1:])
roots=[ET.parse(p).getroot() for p in (source,readback)]
aois=[{n.get('Name'):n for n in r.iter('AddOnInstructionDefinition') if 'R8C4' in n.get('Name','')
       and n.get('Name','').startswith('FRK_M_')} for r in roots]
assert aois[0] and set(aois[0])==set(aois[1])
findings=[];definitions=[];instances=[]
def defaults(node):
    v=node.find('./DefaultData[@Format="Decorated"]/DataValue')
    return int(v.get('Value')) if v is not None else 0
for name in aois[0]:
    counts={}
    for kind,path in (('parameter','./Parameters/Parameter'),('local','./LocalTags/LocalTag')):
        rows=[{n.get('Name'):dict(dataType=n.get('DataType'),usage=n.get('Usage'),value=defaults(n))
               for n in a[name].findall(path)} for a in aois]
        if rows[0]!=rows[1]:findings.append(dict(aoi=name,kind=kind,expected=rows[0],actual=rows[1]))
        counts[kind]=len(rows[0])
    definitions.append(dict(aoi=name,**counts))
for tag in roots[0].find('./Controller/Tags'):
    if tag.get('DataType') not in aois[0]:continue
    actual=roots[1].find('./Controller/Tags/Tag[@Name="'+tag.get('Name')+'"]')
    assert actual is not None
    values=[{n.get('Name'):int(n.get('Value')) for n in t.findall('./Data[@Format="Decorated"]/Structure/DataValueMember')}
            for t in (tag,actual)]
    if values[0]!=values[1]:findings.append(dict(instance=tag.get('Name'),expected=values[0],actual=values[1]))
    instances.append(dict(tag=tag.get('Name'),values=values[0]))
result=dict(passed=not findings,findings=findings,definitions=definitions,instances=instances,controllerAccess=False,
            inputs=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest().upper()) for p in (source,readback)])
with output.open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(dict(passed=result['passed'],definitions=definitions,instances=len(instances),findings=len(findings))))
raise SystemExit(0 if result['passed'] else 1)
