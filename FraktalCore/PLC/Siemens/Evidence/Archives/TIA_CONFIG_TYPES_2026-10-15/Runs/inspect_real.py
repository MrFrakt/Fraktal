import json,os,sys
from pathlib import Path
sys.path.insert(0,'C:/Projects/Fraktal/FraktalCore/PLC/Siemens/tools')
from tia_webapi import WebApi
from tia_mailbox import Mailbox
from tia_target_guard import guard
api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
try:
 api.login('fraktal');box=Mailbox(api,guard,lambda row:None)
 result=dict(raw=box.read('StationA.StationCfg.Gain'))
 page=0
 while True:
  assert box.request('QUERY_CONFIG',IntValue=page)
  base='StationA.HmiResponse.ConfigPage'
  for i in range(1,box.read(base+'.EntryCount')+1):
   e=base+'.Entries[%d]'%i
   if box.read(e+'.Scope')=='StationA' and box.read(e+'.WriteKey')=='gain':
    result['text']=box.read(e+'.ValueText');result['page']=page
  if 'text' in result:break
  page+=1;assert page<box.read(base+'.PageCount')
 Path(sys.argv[1]).write_bytes((json.dumps(result,indent=2)+'\n').encode('ascii'));print(json.dumps(result))
finally:api.conn.close()
