import json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'FraktalCore/PLC/Siemens/tools'))
from tia_webapi import WebApi,leaf_var
api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
api.login('fraktal')
fields=['StationA.Status.State','StationA.Busy','StationA.Error','StationA.Done','StationA.Execute','StationA.ModeActivePublished','StationA.AlarmLog.Blocking','StationA.HmiResponse.Diagnostic','StationA.HmiResponse.Report.Count','StationA.HmiResponse.Report.Released','StationA.HmiResponse.Report.Items[1].Description','StationA.HmiResponse.Report.Items[1].ReasonCode','StationA.Access.CurrentLevel','GDB_UnitTest.FinishCycle','GDB_UnitTest.Permit','StationA.ConfigPersist.Pending','FRK_PersistStatus.Restoring']
rows=api.bulk([('PlcProgram.Read',{'var':leaf_var(p.split('.'))}) for p in fields])
with Path(sys.argv[1]).open('x',encoding='ascii') as f:
 for path,(value,error) in zip(fields,rows):
  row=dict(path=path,value=value,error=error);f.write(json.dumps(row)+'\n');print(json.dumps(row))
api.conn.close()
