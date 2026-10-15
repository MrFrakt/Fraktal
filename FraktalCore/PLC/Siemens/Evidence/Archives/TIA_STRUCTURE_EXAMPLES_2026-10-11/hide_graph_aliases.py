from pathlib import Path
import os,sys,json,shutil,hashlib
sys.path.insert(0,str(Path('FraktalCore/PLC/Siemens/tools').resolve()))
import fraktal_tia_examples as EX
w=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Structure_Examples_20261011'
EX.generate(w/'candidate_08')
target=Path('FraktalCore/PLC/Siemens/Examples/PressDemo/generated')
old=json.loads((target/'manifest.json').read_bytes())['generated']
for name,hashvalue in old.items():
    hits=list(target.rglob(name));assert len(hits)==1
    assert hashlib.sha256(hits[0].read_bytes()).hexdigest()==hashvalue
    shutil.copy2(w/'candidate_08'/name,hits[0])
shutil.copy2(w/'candidate_08/manifest.json',target/'manifest.json')
layout=json.loads((target/'layout.json').read_bytes())
for row in layout['files']:row['sha256']=hashlib.sha256((target/row['file']).read_bytes()).hexdigest()
(target/'layout.json').write_bytes((json.dumps(layout,indent=2)+'\n').encode('ascii'))
station=w/'grouped_station_07'
layout=json.loads((station/'layout.json').read_bytes())
lines=['open-project --path "'+str(Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Organized_Runtime_20261011/FrkS12/FrkS12.ap20')+'"']
for row in layout['files']:
    if Path(row['file']).name.startswith('27_'):
        p=station/row['file'];shutil.copy2(w/'candidate_08'/p.name,p)
        row['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append('import-xml --plc PLC_1 --file "'+str(p)+'" --group "'+row['group']+'"')
(station/'layout.json').write_bytes((json.dumps(layout,indent=2)+'\n').encode('ascii'))
lines+=['compile --plc PLC_1','list-groups --plc PLC_1','export --plc PLC_1 --out "'+str(w/'export_station_final')+'" --scl true','save']
(w/'27_aliases.plan').write_bytes(('\n'.join(lines)+'\n').encode('ascii'))
print(json.dumps(EX.verify(target)))
