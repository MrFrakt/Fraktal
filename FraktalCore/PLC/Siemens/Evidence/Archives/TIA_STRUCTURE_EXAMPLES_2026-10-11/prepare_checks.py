from pathlib import Path
import sys,os,json,hashlib,shutil
sys.path.insert(0,str(Path('FraktalCore/PLC/Siemens/tools').resolve()))
import fraktal_tia_examples as EX
import fraktal_tia_program_layout as L
w=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Structure_Examples_20261011'
EX.generate(w/'candidate_07')
shutil.copytree(w/'merged_06',w/'merged_07')
for p in (w/'candidate_07').iterdir():
    if p.name in ('20_000_FB_CylinderCM.scl','23_FB_PressDemoAuto.scl','23_FB_PressDemoHome.scl'):
        shutil.copy2(p,w/'merged_07'/p.name)
project=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Organized_Runtime_20261011/FrkS12/FrkS12.ap20'
L.organize(w/'merged_07',w/'grouped_station_07',project,w/'export_station_07')
# Update the reversible generated output in place, checking its old ownership
# inventory before replacing only files derived from this generator.
target=Path('FraktalCore/PLC/Siemens/Examples/PressDemo/generated')
old=json.loads((target/'manifest.json').read_bytes())['generated']
for name,hashvalue in old.items():
    hits=list(target.rglob(name));assert len(hits)==1
    assert hashlib.sha256(hits[0].read_bytes()).hexdigest()==hashvalue
    shutil.copy2(w/'candidate_07'/name,hits[0])
shutil.copy2(w/'candidate_07/manifest.json',target/'manifest.json')
layout=json.loads((target/'layout.json').read_bytes())
for row in layout['files']:row['sha256']=hashlib.sha256((target/row['file']).read_bytes()).hexdigest()
(target/'layout.json').write_bytes((json.dumps(layout,indent=2)+'\n').encode('ascii'))
print(json.dumps(EX.verify(target)))
