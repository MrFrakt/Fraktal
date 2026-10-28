from pathlib import Path
import difflib
import json
import xml.etree.ElementTree as ET

W=Path(__file__).parent
old=ET.parse('C:/work/fraktal-ab-s4b-20261025/offline_01/canonical_read_view_01.L5X').getroot()
new=ET.parse(W/'canonical_cold_01.L5X').getroot()
for path in ('./Controller/DataTypes','./Controller/Tags'):
    assert ET.tostring(old.find(path))==ET.tostring(new.find(path)),path
oldlines=[line.text for line in old.findall('.//STContent/Line')]
newlines=[line.text for line in new.findall('.//STContent/Line')]
changed=list(difflib.unified_diff(oldlines,newlines,fromfile='qualified',tofile='cold-deferred',lineterm=''))
assert changed and all('S:FS' in line or 'LastCatalogCount' in line or line.startswith(('---','+++','@@',' ')) for line in changed),changed
result=dict(passed=True,tagAndTypeLayoutsIdentical=True,manifestAndInitializersIdentical=True,
    oldStLines=len(oldlines),newStLines=len(newlines),diff=changed)
with (W/'cold_layout_comparison_01.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result))
