import json,os,sys,time
from pathlib import Path
ROOT=Path(r'C:\Projects\Fraktal');sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Siemens/tools'))
from tia_webapi import WebApi,leaf_var
from tia_target_guard import guard
from tia_mailbox import Mailbox
from fraktal_tia_binding import Catalog
out=Path(sys.argv[1]);api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
with out.open('x',encoding='ascii') as stream:
    def emit(r):stream.write(json.dumps(r)+'\n');stream.flush()
    def read(p):return api.call('PlcProgram.Read',{'var':leaf_var(p.split('.'))})
    def wait(pred):
        end=time.monotonic()+65
        while not pred():
            assert time.monotonic()<end,'normalization deadline';time.sleep(.05)
    try:
        api.login('fraktal');emit({'event':'owner','status':guard()})
        values={'GDB_SequenceViewTest.Enabled':False,'GDB_SequenceViewTest.Annotate':False,
                'GDB_SequenceQuiesceTest.Enabled':False,'GDB_PersistenceTest.Unavailable':False}
        emit({'event':'mutation-guard','status':guard(),'targets':list(values)})
        result=api.bulk([('PlcProgram.Write',{'var':leaf_var(p.split('.')),'value':v}) for p,v in values.items()])
        assert not any(e for _,e in result)
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
            row={k:read(root+'.'+k) for k in ('ModeActivePublished','Status.State','RunningPublished','Access.CurrentLevel',
                'AlarmLog.Blocking','ConfigPersist.Pending','ConfigPersist.Failed','SequenceStepCount','SequenceAnnotationCount','ActiveSteps[0].RowIdx')}
            assert row['ModeActivePublished']==catalog.enums['E_Mode']['MANUAL']
            assert row['Status.State']==catalog.enums['E_ExecState']['READY']
            assert all(row[k] in (False,0) for k in row if k not in ('ModeActivePublished','Status.State'))
            emit({'event':'final-root','root':root,'values':row})
        emit({'event':'final-storage','medium':read('FRK_PersistStatus.Medium'),'restoring':read('FRK_PersistStatus.Restoring')})
        emit({'event':'complete','status':guard(),'keeperPid':5380})
    finally:api.conn.close()
