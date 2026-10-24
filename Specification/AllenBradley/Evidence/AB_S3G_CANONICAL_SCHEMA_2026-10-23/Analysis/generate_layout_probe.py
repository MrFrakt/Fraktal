"""Generate an offline type/layout probe; it is not an S3g runtime candidate."""
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import hashlib,json,sys,xml.etree.ElementTree as ET
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;TOOLS=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0,str(TOOLS))
import fraktal_ab_genealogy_s3f_demo as previous
import fraktal_ab_generate as gen
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_metrics as metrics
old=previous.application();new=replace(old,canonical_publication_stage=9)
assert metrics.validate(new)==[] and pub.validate(new), 'Full S3g generation must remain gated pending implementation'
baseline=P/'s3f_compatibility_01.L5X'
summary=gen.generate(old,Path('C:/work/echo38_5580_seed.L5X'),baseline)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert sha(baseline.read_bytes()).upper()=='B71E30ABBE8221AAA39A0DF8EEB934897FE0A4B0711047EFDC7D653A20AE7CF3'
tree=ET.parse(baseline);controller=tree.getroot().find('Controller')
types=controller.find('DataTypes');oldtypes={ET.fromstring(t).get('Name') for t in pub.data_types(old)}
for node in list(types):
 if node.get('Name') in oldtypes:types.remove(node)
for source in pub.data_types(new):types.append(ET.fromstring(source))
tags=controller.find('Tags');oldtags={ET.fromstring(t).get('Name') for t in pub.tags(old)}
for node in list(tags):
 if node.get('Name') in oldtags:tags.remove(node)
initial=pub.initial(new)
initial['Oee']=dict(RunMs=-1,DownMs=-2147483648,Availability=1/3)
initial['OeeTrend']=[dict(Oee=1/3),*({} for i in range(gen.OEE_SAMPLES-1))]
initial['Profiler']=dict(LastCycle=dict(CycleNo=-2147483648),StepStats=[dict(Count=-1),*({} for i in range(gen.PROFILE_STEPS-1))])
with patch.object(pub,'initial',return_value=initial):
 for source in pub.tags(new):tags.append(ET.fromstring(source))
# The serialized graph comes from the generator's declarations. The existing
# S3f executable bodies are deliberately unchanged; no dependent metric
# algorithm is implemented or accepted by this type-only probe.
destination=P/'metrics_layout_probe_01.L5X';assert not destination.exists()
tree.write(destination,encoding='utf-8',xml_declaration=True)
result=dict(passed=True,offlineOnly=True,controllerAccess=False,fullS3gCandidate=False,algorithmsImplemented=False,baselineGeneratedSourceUnchanged=True,sourceSha256=sha(destination.read_bytes()),typeDefinitions=len(pub.data_types(new)),canonicalFieldRows=len(pub.field_rows(new)),newTags=[ET.fromstring(t).get('Name') for t in metrics.tags(new,lambda name,kind,value,**kw:json.dumps(dict(name=name,kind=kind,value=value,**kw))) ] if False else [metrics.state_tag(new),metrics.labels_tag(new)],vectors=['native REAL 1/3 initializer','DINT -1/-2147483648 with existing BITSTRING32/UInt32 annotations'])
with (P/'layout_generation_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
