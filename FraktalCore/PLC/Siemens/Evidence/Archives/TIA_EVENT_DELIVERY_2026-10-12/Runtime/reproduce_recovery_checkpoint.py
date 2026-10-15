import sys,os,json,time,subprocess
from pathlib import Path
sys.path.insert(0,'C:/Projects/Fraktal/FraktalCore/PLC/Siemens/tools')
from tia_webapi import WebApi,leaf_var
from tia_target_guard import guard
api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
with Path(sys.argv[1]).open('x',encoding='ascii',newline='\n') as stream:
 def emit(row):stream.write(json.dumps(row)+'\n');stream.flush()
 def read(p):return api.call('PlcProgram.Read',{'var':leaf_var(p.split('.'))})
 def write(fields):
  emit(dict(event='mutation-guard',status=guard(),targets=list(fields)))
  replies=api.bulk([('PlcProgram.Write',{'var':leaf_var(p.split('.')),'value':v}) for p,v in fields.items()]);assert not any(e for v,e in replies)
 try:
  api.login('fraktal')
  write({'GDB_AlarmRecoveryTest.Scope':'StationA','GDB_AlarmRecoveryTest.Operation':3})
  deadline=time.monotonic()+8
  while read('GDB_AlarmRecoveryTest.Operation') and time.monotonic()<deadline:time.sleep(.02)
  write({'GDB_StateAlarmTest.Diag.ReasonCode':15080,'GDB_StateAlarmTest.Diag.Description':'test.checkpoint.full','GDB_StateAlarmTest.Diag.SourcePath':'StationA.Cell.Gate','GDB_StateAlarmTest.Diag.Severity':2,'GDB_StateAlarmTest.Diag.Category':0,'GDB_StateAlarmTest.ResetClass':1,'GDB_StateAlarmTest.FillCount':16,'GDB_StateAlarmTest.FillPulse':True})
  deadline=time.monotonic()+8
  while read('GDB_StateAlarmTest.FillPulse') and time.monotonic()<deadline:time.sleep(.02)
  emit(dict(event='filled',count=read('StationA.AlarmLog.NActive')))
  for i in range(12):
   before=read('GDB_AccessPersistTest.StartupCount')
   for mode in ('halt','run'):
    emit(dict(event='mode-guard',status=guard(),mode=mode))
    r=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File','C:/Projects/Fraktal/FraktalCore/PLC/Siemens/Spikes/S12_TypeMap/simulator.ps1','-Action',mode],capture_output=True);assert r.returncode==0
   deadline=time.monotonic()+8
   while read('GDB_AccessPersistTest.StartupCount')<=before and time.monotonic()<deadline:time.sleep(.02)
   row=dict(event='recovery-checkpoint',cycle=i,count=read('StationA.AlarmLog.NActive'),check=read('GDB_DeliveryTest.RecoveryCheck'),index=read('GDB_DeliveryTest.RecoveryIndex'))
   emit(row);print(json.dumps(row))
   if row['count']!=16:break
 finally:api.conn.close()
