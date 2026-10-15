import json,os,sys
from pathlib import Path
sys.path.insert(0,r'C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools')
from tia_webapi import WebApi,leaf_var
from tia_target_guard import guard
api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
api.login('fraktal')
paths=['FRK_PersistStatus.Restoring','FRK_PersistStatus.DocumentCount','FRK_PersistStatus.Medium',
 'GDB_PersistenceTest.Unavailable','GDB_SequenceQuiesceTest.Enabled','GDB_SequenceDiagnosticTest.Enabled',
 'GDB_AccessPersistTest.UsersReady','GDB_AccessPersistTest.UsersLost','GDB_PersistenceTest.NativeStatus','GDB_PersistenceTest.Generation[1]']
for root in ('StationA','StationB'):
    paths += [root+'.'+n for n in ('ConfigPersist.Pending','ConfigPersist.Failed','ConfigPersist.RestoreLost','ConfigPersist.RestoreAcknowledged','Status.State','Status.Diagnostic.ReasonCode','Status.Diagnostic.Description','AlarmLog.Blocking','ModeActivePublished','Access.CurrentLevel')]
result=api.bulk([('PlcProgram.Read',{'var':leaf_var(p.split('.'))}) for p in paths])
rows={'owner':guard(),'values':dict(zip(paths,[v if e is None else {'error':e} for v,e in result]))}
out=Path(sys.argv[1]);out.write_text(json.dumps(rows,indent=2)+'\n',encoding='ascii');print(json.dumps(rows))
api.conn.close()
