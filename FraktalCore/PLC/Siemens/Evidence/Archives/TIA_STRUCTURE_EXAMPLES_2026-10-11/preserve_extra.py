from pathlib import Path
import os,json,hashlib
w=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Structure_Examples_20261011'
p=w/'grouped_station_07/Tests/ConfigBench/Fixtures/05_GDB_RetainProbe.db'
p.write_bytes((w/'export_station_before/scl/GDB_RetainProbe.db').read_text('utf-8-sig').replace('\r\n','\n').encode('ascii'))
layout=w/'grouped_station_07/layout.json';data=json.loads(layout.read_bytes())
data['files'].append({'file':p.relative_to(layout.parent).as_posix(),'group':'Tests/ConfigBench/Fixtures','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'kind':'db'})
layout.write_bytes((json.dumps(data,indent=2)+'\n').encode('ascii'))
project=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Organized_Runtime_20261011/FrkS12/FrkS12.ap20'
lines=['open-project --path "'+str(project)+'"',
       'import-sources --plc PLC_1 --dir "'+str(p.parent)+'" --only '+p.name+' --group Tests/ConfigBench/Fixtures',
       'compile --plc PLC_1','list-groups --plc PLC_1',
       'export --plc PLC_1 --out "'+str(w/'export_station_08')+'" --scl true','save']
(w/'25_preserve_extra.plan').write_bytes(('\n'.join(lines)+'\n').encode('ascii'))
# The replay plan now also retains the previously saved test DB.
plan=w/'grouped_station_07/import.plan';lines=plan.read_text('ascii').splitlines()
index=next(i for i,s in enumerate(lines) if s.startswith('compile '))
lines.insert(index,'import-sources --plc PLC_1 --dir "'+str(p.parent)+'" --only '+p.name+' --group Tests/ConfigBench/Fixtures')
plan.write_bytes(('\n'.join(lines)+'\n').encode('ascii'))
print(json.dumps({'preserved_extra':'GDB_RetainProbe','wired':False}))
