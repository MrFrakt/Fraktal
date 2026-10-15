import json,os,sys,time
from pathlib import Path
sys.path.insert(0,r'C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools')
from tia_webapi import WebApi,leaf_var
from tia_target_guard import guard
from tia_mailbox import Mailbox
api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
with Path(sys.argv[1]).open('x',encoding='ascii') as f:
    def emit(r):f.write(json.dumps(r)+'\n');f.flush()
    def read(p):return api.call('PlcProgram.Read',{'var':leaf_var(p.split('.'))})
    def wait(pred,label):
        end=time.monotonic()+65
        while not pred():
            assert time.monotonic()<end,label;time.sleep(.03)
    try:
        api.login('fraktal');emit({'event':'owner','status':guard()})
        assert read('GDB_AccessPersistTest.UsersLost') and not read('GDB_AccessPersistTest.UsersReady')
        emit({'event':'mutation-guard','status':guard(),'target':'GDB_AccessPersistTest.Operation','operation':7})
        api.call('PlcProgram.Write',{'var':leaf_var(['GDB_AccessPersistTest','Operation']),'value':7})
        wait(lambda:read('GDB_AccessPersistTest.Operation')==0 and read('GDB_AccessPersistTest.UsersReady'),'trusted test provisioning')
        mail=Mailbox(api,guard,emit)
        for root in ('StationA','StationB'):
            assert mail.request('LOGIN',root=root,User='admin',Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
            wait(lambda:read(root+'.Access.CurrentLevel')==4 and not read(root+'.Access.LoginBusy'),'restored test login')
            if read(root+'.ConfigPersist.RestoreLost') and not read(root+'.ConfigPersist.RestoreAcknowledged'):
                assert mail.request('ACK_CONFIG_RESTORE',root=root)
            assert mail.request('LOGOUT',root=root)
        wait(lambda:all(not read(r+'.ConfigPersist.Pending') and not read(r+'.ConfigPersist.Failed') for r in ('StationA','StationB')),'verified repair durability')
        emit({'event':'complete','usersReady':read('GDB_AccessPersistTest.UsersReady'),'usersLost':read('GDB_AccessPersistTest.UsersLost'),'owner':guard()})
    finally:api.conn.close()
