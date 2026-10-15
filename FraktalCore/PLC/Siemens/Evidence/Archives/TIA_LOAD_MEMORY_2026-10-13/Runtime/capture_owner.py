import sys,os,json,hashlib,subprocess
from pathlib import Path
r=Path('C:/Projects/Fraktal');sys.path.insert(0,str(r/'FraktalCore/PLC/Siemens/tools'))
from tia_target_guard import guard
from tia_webapi import WebApi,leaf_var
from fraktal_tia_binding import Catalog
owner=guard();assert owner['state']=='Run'
raw=subprocess.run(['powershell.exe','-NoProfile','-Command','Get-Process -Id 12728 | Select-Object Id,ProcessName,StartTime | ConvertTo-Json -Compress'],check=True,capture_output=True).stdout
keeper=json.loads(raw.decode('utf-8-sig'));assert keeper['Id']==12728
binary=r/'FraktalCore/PLC/Siemens/tools/TiaCli/bin/candidate_structure_examples/Fraktal.Tia.Cli.exe'
digest=hashlib.sha256(binary.read_bytes()).hexdigest();assert digest=='ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74'
api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
try:
 api.login('fraktal')
 paths=[root+'.'+field for root in ('StationA','StationB') for field in ('RunningPublished','Access.CurrentLevel','ModeActivePublished')]
 state={p:api.call('PlcProgram.Read',dict(var=leaf_var(p.split('.')))) for p in paths}
 for root in ('StationA','StationB'):
  assert state[root+'.RunningPublished'] is False and state[root+'.Access.CurrentLevel']==0
  assert state[root+'.ModeActivePublished']==Catalog.read().enums['E_Mode']['MANUAL']
 value=dict(owner=owner,keeper=keeper,driver_sha256=digest,fixture=state)
 with Path(sys.argv[1]).open('x',encoding='utf-8',newline='\n') as out:out.write(json.dumps(value,indent=2)+'\n')
 print(json.dumps(value))
finally:api.conn.close()
