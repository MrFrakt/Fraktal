from pathlib import Path
import gzip
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
W=Path(__file__).parent
TOOLS=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0,str(TOOLS))
import fraktal_ab_readback as readback

def sha(data):return hashlib.sha256(data).hexdigest()
source=W/'genealogy_s3b_03.L5X'
exported=W/'native_echo_03.L5X'
native=ET.parse(exported).getroot()
controller=native.find('Controller')
tag=controller.find("Tags/Tag[@Name='FRK_Press_CanonicalManifest']")
assert tag.find("Data[@Format='Decorated']") is None
types={node.get('Name'):node for node in controller.findall('DataTypes/DataType')}
needed=set()
def collect(kind):
    if kind in needed or kind not in types:return
    needed.add(kind)
    for member in types[kind].findall('Members/Member'):collect(member.get('DataType'))
collect(tag.get('DataType'))
subset=ET.Element('RSLogix5000Content')
c=ET.SubElement(subset,'Controller',Name=controller.get('Name'))
data_types=ET.SubElement(c,'DataTypes')
for name in sorted(needed):data_types.append(types[name])
ET.SubElement(c,'Tags').append(tag)
prefix=controller.get('Name')+'/FRK_Press_CanonicalManifest/'
expected={key:({'bytes':value.hex()} if isinstance(value,bytes) else {'value':value})
          for key,value in readback.initials(ET.parse(source).getroot()).items() if key.startswith(prefix)}
capture=dict(schema='fraktal.ab.l5k-manifest-capture',readOnly=True,sourceSha256=sha(source.read_bytes()),
    nativeExportSha256=sha(exported.read_bytes()),tag='FRK_Press_CanonicalManifest',
    xml=ET.tostring(subset,encoding='unicode'),expected=expected,expectedAuthoredValues=len(expected))
work_capture=W/'l5k_manifest_capture_03.json'
with work_capture.open('x',encoding='utf-8') as output:json.dump(capture,output,indent=2)

fixtures=TOOLS/'fixtures/canonical'
manifest_path=fixtures/'manifest.json'
manifest=json.loads(manifest_path.read_text())
for name,origin,scope in (
    ('batch_transport_01.json.gz',gzip.decompress((W/'batch_transport_01.json.gz').read_bytes()),'Guarded read-only legacy Echo: eight complete UDTs in two MSP replies; transport diagnostic, no same-scan claim'),
    ('s3b_l5k_manifest_03.json.gz',work_capture.read_bytes(),'Native v38 Echo manifest L5K plus source-authored expected values; extracted without editing values')):
    assert not any(row['file']==name for row in manifest['captures'])
    data=gzip.compress(origin,mtime=0)
    with (fixtures/name).open('xb') as output:output.write(data)
    manifest['captures'].append(dict(file=name,sha256=sha(data),source=str(W/('batch_transport_01.json.gz' if name.startswith('batch_') else work_capture.name)),
        sourceSha256=sha(origin),sourceBytes=len(origin),compressedBytes=len(data),scope=scope))
assert sum(row['compressedBytes'] for row in manifest['captures'])<=manifest['compressedBudgetBytes']
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(captures=len(manifest['captures']),compressedBytes=sum(row['compressedBytes'] for row in manifest['captures']),l5kAuthoredValues=len(expected))))
