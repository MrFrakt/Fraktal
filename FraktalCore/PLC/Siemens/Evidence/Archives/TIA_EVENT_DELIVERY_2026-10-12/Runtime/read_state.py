import sys,json,os
from pathlib import Path
sys.path.insert(0,'C:/Projects/Fraktal/FraktalCore/PLC/Siemens/tools')
from tia_webapi import WebApi,leaf_var
api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
try:
 api.login('fraktal');paths=['StationA.AlarmLog.NActive','StationA.AlarmLog.Active[1].ReasonCode','StationA.AlarmLog.Active[1].Description','StationA.AlarmLog.Active[1].ResetClass','FRK_EventDeliveryView.Rows[1].RestoreLost','FRK_EventDeliveryView.Rows[1].AnchorValid','GDB_AlarmRecoveryTest.Damage','GDB_DeliveryTest.Damage']
 data={p:api.call('PlcProgram.Read',{'var':leaf_var(p.split('.'))}) for p in paths};Path(sys.argv[1]).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(data))
finally:api.conn.close()
