"""Compile the approved health mapper as an uncalled offline probe routine."""
from pathlib import Path
from dataclasses import replace
import hashlib,json,sys,xml.etree.ElementTree as ET
P=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_genealogy_s3f_demo as previous
import fraktal_ab_generate as gen
import fraktal_ab_canonical_metrics as metrics
app=replace(previous.application(),canonical_publication_stage=9)
source=P/'metrics_layout_probe_03.L5X';text=source.read_text(encoding='utf-8')
body=gen.st_program_routine('FRK_Press_CanonicalMetricsHealth',metrics.health(app))
program_at=text.index('<Programs>');routines_at=text.index('<Routines>',program_at)
at=text.index('</Routines>',routines_at);text=text[:at]+body+'\n'+text[at:]
tree=ET.fromstring(text);node=tree.find('./Controller/Programs/Program/Routines/Routine[@Name="FRK_Press_CanonicalMetricsHealth"]');assert node is not None
destination=P/'metrics_layout_probe_05.L5X'
with destination.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
print(json.dumps(dict(passed=True,controllerAccess=False,fullS3gCandidate=False,sourceSha256=hashlib.sha256(destination.read_bytes()).hexdigest(),healthRoutineUncalled=True)))
