import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'FraktalCore/PLC/Siemens/tools'))
from tia_webapi import WebApi,leaf_var
from tia_target_guard import guard
api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
try:
 api.login('fraktal')
 result={'owner':guard(),'roots':{}}
 for root in ('StationA','StationB'):
  fields=('ModeActivePublished','RunningPublished','Status.State','Access.CurrentLevel','SequenceStepCount','SequenceAnnotationCount','ConfigPersist.Pending','ConfigPersist.Failed','AlarmLog.Blocking')
  row={n:api.call('PlcProgram.Read',{'var':leaf_var((root+'.'+n).split('.'))}) for n in fields}
  row['secret_cleared']=api.call('PlcProgram.Read',{'var':leaf_var([root,'HmiRequest','Secret'])})==''
  assert row['ModeActivePublished']==2 and not row['RunningPublished'] and row['Status.State']==0 and row['Access.CurrentLevel']==0
  assert not row['ConfigPersist.Pending'] and not row['ConfigPersist.Failed'] and not row['AlarmLog.Blocking'] and row['secret_cleared']
  assert row['SequenceStepCount']==row['SequenceAnnotationCount']==0
  result['roots'][root]=row
 Path(sys.argv[1]).write_bytes((json.dumps(result,indent=2)+'\n').encode('ascii'))
 print(json.dumps(result))
finally: api.conn.close()
