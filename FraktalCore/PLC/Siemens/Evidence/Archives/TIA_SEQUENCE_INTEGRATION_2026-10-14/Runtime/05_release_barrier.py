import os,sys,time,json
from pathlib import Path
sys.path.insert(0,'FraktalCore/PLC/Siemens/tools')
from tia_webapi import WebApi,leaf_var
from tia_target_guard import guard
api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
try:
 api.login('fraktal');owner=guard()
 rows=api.bulk([('PlcProgram.Write',{'var':leaf_var(p.split('.')),'value':False}) for p in ('GDB_PersistenceTest.Unavailable','GDB_SequenceViewTest.Enabled')]);assert not any(e for v,e in rows)
 end=time.monotonic()+65
 while api.call('PlcProgram.Read',{'var':leaf_var(['FRK_PersistStatus','Restoring'])}):
  assert time.monotonic()<end;time.sleep(.1)
 Path(sys.argv[1]).write_bytes((json.dumps({'owner':owner,'barrier_released':True})+'\n').encode('ascii'))
finally:api.conn.close()
