import sys,json,os
from pathlib import Path
sys.path.insert(0,str(Path('FraktalCore/PLC/Siemens/tools').resolve()))
from tia_webapi import WebApi,leaf_var
api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
try:
 api.login('fraktal')
 paths=['StationA.HmiResponse.Diagnostic','StationA.Access.CurrentLevel','StationA.RunningPublished','StationA.ConfigPersist.RestoreLost','StationA.ConfigPersist.RestoreAcknowledged','StationA.ConfigPersist.LostPath','StationA.ModeActivePublished','StationA.Status.State','StationA.ErrorID','StationA.HmiResponse.Report.Count']
 rows=api.bulk([('PlcProgram.Read',dict(var=leaf_var(p.split('.')))) for p in paths])
 Path(sys.argv[1]).write_bytes((json.dumps(dict(zip(paths,rows)))+'\n').encode('ascii'))
finally:api.conn.close()
