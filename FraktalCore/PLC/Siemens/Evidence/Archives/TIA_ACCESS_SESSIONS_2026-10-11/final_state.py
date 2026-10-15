from pathlib import Path
import os,sys,json
sys.path.insert(0,'C:/Projects/Fraktal/FraktalCore/PLC/Siemens/tools')
from tia_webapi import WebApi,leaf_var
api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
try:
 api.login('fraktal')
 rows={}
 for root in ('StationA','StationB'):
  rows[root]={f:api.call('PlcProgram.Read',{'var':leaf_var((root+'.'+f).split('.'))}) for f in ('Access.CurrentLevel','Access.CurrentUser','Access.LoginBusy','ModeActivePublished','RunningPublished','Status.State')}
  rows[root]['secretCleared']=api.call('PlcProgram.Read',{'var':leaf_var([root,'HmiRequest','Secret'])})==''
  assert rows[root]['Access.CurrentLevel']==0 and rows[root]['Access.CurrentUser']=='' and not rows[root]['Access.LoginBusy']
  assert not rows[root]['RunningPublished'] and rows[root]['Status.State']==0 and rows[root]['secretCleared']
 with Path(sys.argv[1]).open('x',encoding='ascii',newline='\n') as stream:json.dump(rows,stream,indent=2);stream.write('\n')
finally:
 api.conn.close()
