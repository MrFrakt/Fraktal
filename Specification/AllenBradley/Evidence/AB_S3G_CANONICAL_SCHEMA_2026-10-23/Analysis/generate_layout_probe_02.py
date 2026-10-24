"""Generate only new declaration sections, preserving the native code graph."""
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import hashlib,json,sys,xml.etree.ElementTree as ET
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_genealogy_s3f_demo as previous
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_metrics as metrics
import fraktal_ab_generate as gen
old=previous.application();new=replace(old,canonical_publication_stage=9)
baseline=P/'s3f_compatibility_01.L5X';text=baseline.read_text(encoding='utf-8')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert sha(baseline.read_bytes()).upper()=='B71E30ABBE8221AAA39A0DF8EEB934897FE0A4B0711047EFDC7D653A20AE7CF3'
for fragment in [*pub.data_types(old),*pub.tags(old)]:
 assert text.count(fragment)==1,fragment[:100]
 text=text.replace(fragment,'',1)
initial=pub.initial(new)
initial['Oee']=dict(RunMs=-1,DownMs=-2147483648,Availability=1/3)
initial['OeeTrend']=[dict(Oee=1/3),*({} for i in range(gen.OEE_SAMPLES-1))]
initial['Profiler']=dict(LastCycle=dict(CycleNo=-2147483648),StepStats=[dict(Count=-1),*({} for i in range(gen.PROFILE_STEPS-1))])
with patch.object(pub,'initial',return_value=initial):tagtext='\n'.join(pub.tags(new))
for closing,fragment in (('</DataTypes>','\n'.join(pub.data_types(new))),('</Tags>',tagtext)):
 assert text.count(closing)==1,closing
 text=text.replace(closing,fragment+'\n'+closing,1)
source_root=ET.fromstring(text);baseline_root=ET.parse(baseline).getroot()
assert ET.tostring(source_root.find('./Controller/Programs'))==ET.tostring(baseline_root.find('./Controller/Programs'))
destination=P/'metrics_layout_probe_02.L5X'
with destination.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
result=dict(passed=True,offlineOnly=True,controllerAccess=False,fullS3gCandidate=False,algorithmsImplemented=False,sourceSha256=sha(destination.read_bytes()),nativeProgramGraphUnchanged=True,nativeCdataPreserved=True,baselineGeneratedSourceUnchanged=True,canonicalFieldRows=len(pub.field_rows(new)),typeDefinitions=len(pub.data_types(new)))
with (P/'layout_generation_02.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
