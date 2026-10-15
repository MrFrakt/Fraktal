import importlib.util,os,json,sys
from pathlib import Path
p=Path('C:/Projects/Fraktal/FraktalCore/PLC/Siemens/Tests/Config/probe_web.py')
s=importlib.util.spec_from_file_location('native_config',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
a=m.WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
a.login('fraktal')
with Path(sys.argv[1]).open('x',encoding='ascii') as f:
 for p in ['StationA.ParCfg.Preset','StationA.ConfigRev','StationA.HmiRequest.TextValue','StationA.HmiRequest.NameValue','StationA.HmiResponse.Accepted']:
  f.write(json.dumps({'path':p,'value':a.call('PlcProgram.Read',{'var':m.leaf_var(p.split('.'))})})+'\n')
a.conn.close()