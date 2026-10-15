import os,sys,json
from pathlib import Path
sys.path.insert(0,'C:/Projects/Fraktal/FraktalCore/PLC/Siemens/tools')
from tia_webapi import WebApi,leaf_var
api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
api.login('fraktal')
try:
 paths=['StationA.Access.Policy.Required[2]','StationA.ConfigPersist.LostPath','StationA.Access.PolicySlot','StationA.AlarmLog.Active[1].Description','StationA.ModeActivePublished','StationA.Status.State','StationA.HmiResponse.Report.Count','StationA.HmiResponse.Report.Reasons[1].Description','StationA.HmiResponse.Report.Reasons[2].Description','StationA.ConfigPersist.RestoreLost','StationA.ConfigPersist.RestoreAcknowledged','StationA.AlarmLog.NActive']
 rows=api.bulk([('PlcProgram.Read',{'var':leaf_var(p.split('.'))}) for p in paths])
 result=dict(zip(paths,rows))
 Path(sys.argv[1]).write_text(json.dumps(result,indent=2),encoding='ascii');print(json.dumps(result))
finally:api.conn.close()
