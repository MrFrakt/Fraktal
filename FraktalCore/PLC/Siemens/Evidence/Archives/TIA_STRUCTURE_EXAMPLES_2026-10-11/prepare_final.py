from pathlib import Path
import sys, os, json, shutil
sys.path.insert(0,str(Path('FraktalCore/PLC/Siemens/tools').resolve()))
import fraktal_tia_examples as EX
import fraktal_tia_program_layout as L
w=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Structure_Examples_20261011'
EX.generate(w/'candidate_06')
shutil.copytree(w/'merged_05',w/'merged_06')
for p in (w/'candidate_06').iterdir():
    if p.name.startswith('06_') and p.suffix=='.udt':shutil.copy2(p,w/'merged_06'/p.name)
project=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Organized_Runtime_20261011/FrkS12/FrkS12.ap20'
L.organize(w/'merged_06',w/'grouped_station_06',project,w/'export_station_06')
target=Path('FraktalCore/PLC/Siemens/Examples/PressDemo/generated')
L.organize(w/'candidate_06',target,Path('${project}'),Path('${export}'))
shutil.copy2(w/'candidate_06/manifest.json',target/'manifest.json')
print(json.dumps({'sources':len(EX.build()[0]),'project':str(project)}))
