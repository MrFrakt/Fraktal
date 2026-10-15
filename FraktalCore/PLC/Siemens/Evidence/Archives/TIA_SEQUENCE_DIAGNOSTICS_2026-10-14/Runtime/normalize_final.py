import json,os,sys,time
from pathlib import Path
sys.path.insert(0,r'C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools')
from tia_webapi import WebApi,leaf_var
from tia_target_guard import guard
from tia_mailbox import Mailbox
from fraktal_tia_binding import Catalog
api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
with Path(sys.argv[1]).open('x',encoding='ascii') as f:
    def emit(r):f.write(json.dumps(r)+'\n');f.flush()
    def read(p):return api.call('PlcProgram.Read',{'var':leaf_var(p.split('.'))})
    def wait(pred):
        end=time.monotonic()+65
        while not pred():
            assert time.monotonic()<end,'normalization deadline';time.sleep(.04)
    try:
        api.login('fraktal');emit({'event':'owner','status':guard()})
        controls={'GDB_SequenceDiagnosticTest.Enabled':False,'GDB_SequenceViewTest.Enabled':False,
                  'GDB_SequenceViewTest.Annotate':False,'GDB_SequenceQuiesceTest.Enabled':False,
                  'GDB_PersistenceTest.Unavailable':False}
        emit({'event':'mutation-guard','status':guard(),'targets':list(controls)})
        results=api.bulk([('PlcProgram.Write',{'var':leaf_var(p.split('.')),'value':v}) for p,v in controls.items()])
        assert not any(e for _,e in results)
        mail=Mailbox(api,guard,emit);catalog=Catalog.read()
        for root in ('StationA','StationB'):
            assert mail.request('LOGIN',root=root,User='admin',Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
            wait(lambda:read(root+'.Access.CurrentLevel')==4 and not read(root+'.Access.LoginBusy'))
            for mode in ('AUTO','MANUAL'):
                ordinal=catalog.enums['E_Mode'][mode]
                assert mail.request('SET_MODE',root=root,IntValue=ordinal)
                wait(lambda:read(root+'.ModeActivePublished')==ordinal)
            assert mail.request('LOGOUT',root=root)
        wait(lambda:not read('FRK_PersistStatus.Restoring') and all(not read(r+'.ConfigPersist.Pending') for r in ('StationA','StationB')))
        for root in ('StationA','StationB'):
            row={n:read(root+'.'+n) for n in ('ModeActivePublished','Status.State','RunningPublished','Access.CurrentLevel',
                'AlarmLog.Blocking','ConfigPersist.Pending','ConfigPersist.Failed','SequenceStepCount','SequenceAnnotationCount','ActiveSteps[0].RowIdx','Pending.ReasonCode','Held')}
            assert row['ModeActivePublished']==catalog.enums['E_Mode']['MANUAL']
            assert row['Status.State']==catalog.enums['E_ExecState']['READY']
            assert all(row[n] in (False,0) for n in row if n not in ('ModeActivePublished','Status.State'))
            emit({'event':'final-root','root':root,'values':row})
        assert read('GDB_AccessPersistTest.UsersReady') and not read('GDB_AccessPersistTest.UsersLost')
        emit({'event':'final-storage','medium':read('FRK_PersistStatus.Medium'),'restoring':read('FRK_PersistStatus.Restoring'),'usersReady':True})
        emit({'event':'complete','status':guard(),'keeperPid':13476})
    finally:api.conn.close()
