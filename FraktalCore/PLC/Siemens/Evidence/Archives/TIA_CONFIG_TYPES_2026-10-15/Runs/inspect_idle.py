import json,os,sys
from pathlib import Path
sys.path.insert(0,'C:/Projects/Fraktal/FraktalCore/PLC/Siemens/tools')
from tia_webapi import WebApi,leaf_var
api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
try:
    api.login('fraktal')
    paths=[r+'.'+n for r in ('StationA','StationA.Cell','StationA.Cell.Gate','StationA.Cell.Clamp','StationA.Satellite','StationA.Satellite.Inner','StationB') for n in ('Busy','Error','Done','Aborted','Held','ModeActivePublished','RunningPublished')]
    paths+=['StationA.HmiResponse.Diagnostic','StationA.ConfigPersist.Failed','StationA.Access.CurrentLevel']
    replies=api.bulk([('PlcProgram.Read',{'var':leaf_var(p.split('.'))}) for p in paths])
    value=dict(zip(paths,replies));Path(sys.argv[1]).write_text(json.dumps(value,indent=2),encoding='ascii');print(json.dumps(value))
finally:api.conn.close()
