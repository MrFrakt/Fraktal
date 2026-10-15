"""Native retained policy/user qualification, with exact virtual-target guards."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]/'tools'), str(HERE.parent/'ConfigSets')]
from tia_webapi import WebApi, leaf_var
from native_mailbox import Mailbox
from fraktal_tia_binding import Catalog
spec = importlib.util.spec_from_file_location('guard', HERE.parent/'Unit/probe_web.py')
UNIT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(UNIT)


def probe(out):
    checks = []
    complete = False
    pin = Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin'
    api = WebApi('169.254.212.49', pin, False)
    with out.open('x', encoding='ascii', newline='\n') as stream:
        def emit(row):
            stream.write(json.dumps(row)+'\n')
            stream.flush()

        def guard():
            # Retry identity reads only. A target mismatch or any write failure is final.
            for attempt in range(3):
                try:
                    return UNIT.guard()
                except RuntimeError as error:
                    if str(error) != 'simulator identity unavailable' or attempt == 2:
                        raise
                    emit(dict(event='identity-read-retry',attempt=attempt+1,message=str(error)))
                    time.sleep(.2 * (attempt+1))

        def check(name, actual, expected):
            ok = type(actual) is type(expected) and actual == expected
            checks.append((name, ok))
            emit(dict(event='check', label=name, actual=actual, expected=expected, passed=ok))
            assert ok, name

        def until(predicate, name):
            deadline = time.monotonic()+8
            while time.monotonic() < deadline:
                if predicate():
                    return
                time.sleep(.02)
            raise AssertionError(name)

        def writes(fields):
            emit(dict(event='fixture-mutation-guard', targets=list(fields), status=guard()))
            rows = api.bulk([('PlcProgram.Write', {'var':leaf_var(path.split('.')), 'value':value}) for path,value in fields.items()])
            assert not any(error for value,error in rows)

        def stimulus(operation, value=0, root='StationA', gate=2):
            writes({'GDB_AccessPersistTest.Value':value, 'GDB_AccessPersistTest.Root':root, 'GDB_AccessPersistTest.Gate':gate})
            writes({'GDB_AccessPersistTest.Operation':operation})
            until(lambda:box.read('GDB_AccessPersistTest.Operation') == 0, 'fixture consumption')
            return box.read('GDB_AccessPersistTest.Applied')

        def login(user='admin', level=4, root='StationA', failed=False):
            check('login consumed '+root+' '+user, box.request('LOGIN',root,User=user,Secret=os.environ['FRAKTAL_TIA_'+user.upper()+'_PIN']), True)
            until(lambda:not box.read(root+'.Access.LoginBusy'), 'login result')
            check('login failure '+root+' '+user, box.read(root+'.Access.LoginFailed'), failed)
            check('login level '+root+' '+user, box.read(root+'.Access.CurrentLevel'), level)
            check('transported secret cleared '+root, box.read(root+'.HmiRequest.Secret'), '')

        def cycle(power=False):
            nonlocal api, box
            before_startup = box.read('GDB_AccessPersistTest.StartupCount')
            if power:
                api.conn.close()
                commands = [str(HERE.parent/'Config/cycle_simulator.ps1')]
            else:
                commands = [str(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1')]*2
            for index, script in enumerate(commands):
                emit(dict(event='restart-guard',power=power,status=guard()))
                command = ['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',script]
                if not power:
                    command += ['-Action', ('halt','run')[index]]
                result = subprocess.run(command,capture_output=True)
                emit(dict(event='restart-result',power=power,exit_code=result.returncode,output=result.stdout.decode('utf-8-sig').strip()))
                assert result.returncode == 0
            if power:
                api = WebApi('169.254.212.49',pin,False)
                api.login('fraktal')
                box = Mailbox(api, guard, emit)
            until(lambda:box.read('GDB_AccessPersistTest.StartupCount') > before_startup, 'completed startup scan')
            for root in ('StationA','StationB'):
                check('restart session level '+root,box.read(root+'.Access.CurrentLevel'),0)
                check('restart session identity '+root,box.read(root+'.Access.CurrentUser'),'')
                check('restart pending attempt '+root,box.read(root+'.Access.LoginBusy'),False)

        def policy_defaults(root):
            levels = {2:1,4:1,5:1,8:4,11:3}
            for gate in Catalog.read().enums['E_GatedAction'].values():
                assert box.request('SET_ACCESS_LEVEL',root,IntValue=gate,TextValue=str(levels.get(gate,0)))
            assert box.request('SET_SESSION_TIMEOUT',root,DurationMs=0)

        try:
            api.login('fraktal')
            box = Mailbox(api, guard, emit)
            # Normalize only the authorized test bench, including a prior interrupted run.
            if not box.read('GDB_AccessPersistTest.UsersReady'):
                check('preflight explicit engineering repair',stimulus(7),True)
            for root in ('StationA','StationB'):
                login(root=root)
                if box.read(root+'.ConfigPersist.LostPath') == root+'.AccessPolicy':
                    check('preflight acknowledge prior policy test '+root,box.request('ACK_CONFIG_RESTORE',root),True)
                policy_defaults(root)
                assert box.request('LOGOUT',root)
            provision_count = box.read('GDB_AccessPersistTest.ProvisionCount')
            check('store deliberately provisioned',provision_count >= 1,True)
            check('native Core CRC-32 check vector',box.read('GDB_AccessPersistTest.CrcWitness'),0xCBF43926)
            check('initial private user store validated',box.read('GDB_AccessPersistTest.UsersReady'),True)
            for root in ('StationA','StationB'):
                check('initial logged out '+root,box.read(root+'.Access.CurrentLevel'),0)
                check('unauthenticated policy change refused '+root,box.request('SET_ACCESS_LEVEL',root,IntValue=2,TextValue='3'),False)
                login(root=root)
            before = box.read('GDB_AccessPersistTest.UserGeneration')
            check('invalid user role refused',stimulus(1,5),False)
            check('refused registration leaves store generation',box.read('GDB_AccessPersistTest.UserGeneration'),before)
            check('negative user role refused',stimulus(1,-1),False)
            check('disabled account accepted as NONE',stimulus(1,0),True)
            until(lambda:all(box.read(root+'.Access.CurrentLevel') == 0 for root in ('StationA','StationB')), 'sessions revoked by disabled account')
            login(user='operator',level=0,failed=True)
            check('disabled account is valid stored data',box.read('GDB_AccessPersistTest.UsersReady'),True)
            check('trusted operator role update',stimulus(1,2),True)
            until(lambda:all(box.read(root+'.Access.CurrentLevel') == 0 for root in ('StationA','StationB')), 'old sessions revoked')
            check('registration invalidates every root session',all(box.read(root+'.Access.CurrentLevel') == 0 for root in ('StationA','StationB')),True)
            for root, required, timeout in (('StationA',3,60000),('StationB',2,45000)):
                login(root=root)
                check('edit distinct manual policy '+root,box.request('SET_ACCESS_LEVEL',root,IntValue=2,TextValue=str(required)),True)
                check('edit idle timeout '+root,box.request('SET_SESSION_TIMEOUT',root,DurationMs=timeout),True)
                check('invalid idle timeout refused '+root,box.request('SET_SESSION_TIMEOUT',root,DurationMs=604800001),False)
                check('refused idle timeout unchanged '+root,box.read(root+'.Access.Policy.SessionTimeout'),timeout)
            for power in (False,True):
                cycle(power)
                check('restart did not reseed credentials',box.read('GDB_AccessPersistTest.ProvisionCount'),provision_count)
                check('user table ready after restart',box.read('GDB_AccessPersistTest.UsersReady'),True)
                for root,required,timeout in (('StationA',3,60000),('StationB',2,45000)):
                    check('retained manual policy '+root,box.read(root+'.Access.Policy.Required[2]'),required)
                    check('retained idle timeout '+root,box.read(root+'.Access.Policy.SessionTimeout'),timeout)
                    login(user='operator',level=2,root=root)
                    check('policy editing still ADMIN '+root,box.request('SET_ACCESS_LEVEL',root,IntValue=2,TextValue='0'),False)
            writes({'GDB_AccessPersistTest.Value':1, 'GDB_AccessPersistTest.RotateOnLogin':True})
            login(user='operator',level=0,failed=True)
            check('pending old credential attempt revoked',box.read('GDB_AccessPersistTest.RotateOnLogin'),False)
            login(user='operator',level=1)
            # The symbol service must not reveal private images or enable bypass.
            for path in ('FRK_LocalUsers.SchemaVersion','FRK_LocalUsers.Checksum','FRK_LocalUsers.Rows[1].PinHash[0]',
                         'FRK_AccessPolicies.Rows[1].Scope','FRK_AccessPolicies.Rows[1].Policy.Required[2]',
                         'FRK_AccessStorage.UsersReady','FRK_AccessStorage.UsersCommissioned','StationA.Access.PolicySlot','StationA.Access.CandidateGeneration',
                         'GDB_AccessPersistTest.Record.PinHash[0]'):
                row = api.bulk([('PlcProgram.Read',{'var':leaf_var(path.split('.'))})])[0]
                check('private image read refused '+path,row[1]['code'],200)
            for path,value in (('StationA.Access.Policy.Required[2]',0),('StationA.Access.Policy.SessionTimeout',0)):
                emit(dict(event='mutation-guard',targets=[path],status=guard()))
                row = api.bulk([('PlcProgram.Write',{'var':leaf_var(path.split('.')),'value':value})])[0]
                check('policy mirror write refused '+path,row[1]['code'],205)
            for root in ('StationA','StationB'):
                assert box.request('LOGOUT',root)
            # Every corruption rejects the entire provider; no usable record leaks through.
            for operation,value,label in ((2,9,'schema'),(3,999,'count'),(4,9,'role'),(5,0,'duplicate name'),(6,0,'hash checksum'),(8,0,'cleared header')):
                provisions = box.read('GDB_AccessPersistTest.ProvisionCount')
                check('corrupt user '+label,stimulus(operation,value),True)
                cycle()
                check('damaged provider not ready '+label,box.read('GDB_AccessPersistTest.UsersReady'),False)
                check('user loss visible '+label,box.read('GDB_AccessPersistTest.UsersLost'),True)
                check('damaged user store was not reseeded '+label,box.read('GDB_AccessPersistTest.ProvisionCount'),provisions)
                login(level=0,failed=True)
                check('user loss emits precise alarm '+label,any(box.read('StationA.AlarmLog.Active[%d].Description'%i) == 'std.error.accessRestoreLost' for i in range(1,Catalog.read().capacities['MAX_ALARM_ACTIVE']+1)),True)
                check('user loss reaches generic persist status '+label,box.read('StationA.ConfigPersist.LostPath'),'StationA.Access')
                rows = api.bulk([('PlcProgram.Read',{'var':leaf_var(['StationA','ConfigPersist','LostPath'])}) for _ in range(24)])
                check('user loss publication stays stable '+label,all(error is None and value == 'StationA.Access' for value,error in rows),True)
                check('explicit engineering repair '+label,stimulus(7),True)
                until(lambda:box.read('GDB_AccessPersistTest.UsersReady'), 'repaired provider')
                login()
                assert box.request('LOGOUT')
            # Damage one root policy: other root remains exact, default never opens.
            for operation,value,label in ((10,9,'schema'),(11,9,'level'),(12,0,'checksum'),(13,0,'cleared header')):
                check('corrupt root policy '+label,stimulus(operation,value),True)
                cycle()
                check('other root policy survives '+label,box.read('StationB.Access.Policy.Required[2]'),2)
                check('policy loss reaches generic persist status '+label,box.read('StationA.ConfigPersist.LostPath'),'StationA.AccessPolicy')
                rows = api.bulk([('PlcProgram.Read',{'var':leaf_var(['StationA','ConfigPersist','LostPath'])}) for _ in range(24)])
                check('policy loss publication stays stable '+label,all(error is None and value == 'StationA.AccessPolicy' for value,error in rows),True)
                check('bad policy restricts every gate '+label,all(box.read('StationA.Access.Policy.Required[%d]'%gate) == 4 for gate in range(12)),True)
                login(user='operator',level=1)
                check('low-level restore acknowledgement refused '+label,box.request('ACK_CONFIG_RESTORE'),False)
                login()
                check('lost policy blocks Start '+label,box.request('START'),False)
                check('commission ENGINEER for acknowledgement '+label,stimulus(1,3),True)
                login(user='operator',level=3)
                check('explicit ENGINEER restore acknowledgement '+label,box.request('ACK_CONFIG_RESTORE'),True)
                check('acknowledgement preserves restrictive policy '+label,box.read('StationA.Access.Policy.Required[2]'),4)
                check('ENGINEER cannot reopen ADMIN policy '+label,box.request('SET_ACCESS_LEVEL',IntValue=2,TextValue='3'),False)
                login()
                check('policy editable by ADMIN after acknowledgement '+label,box.request('SET_ACCESS_LEVEL',IntValue=2,TextValue='3'),True)
                policy_defaults('StationA')
                check('restore OPERATOR role '+label,stimulus(1,1),True)
                assert box.request('LOGOUT')
            # Restore the qualification bench's intended policy, never user secrets.
            for root in ('StationA','StationB'):
                login(root=root)
                policy_defaults(root)
                assert box.request('LOGOUT',root)
            cycle()
            for root in ('StationA','StationB'):
                check('final retained bench manual policy '+root,box.read(root+'.Access.Policy.Required[2]'),1)
                check('final retained bench timeout '+root,box.read(root+'.Access.Policy.SessionTimeout'),0)
                login(root=root)
                check('select AUTO for release check '+root,box.request('SET_MODE',root,IntValue=Catalog.read().enums['E_Mode']['AUTO']),True)
                until(lambda:box.read(root+'.ModeActivePublished') == Catalog.read().enums['E_Mode']['AUTO'], 'AUTO mode')
                check('final authenticated Start release query '+root,box.request('RELEASE_START',root),True)
                check('restore no longer blocks Start '+root,box.read(root+'.HmiResponse.Report.Released'),True)
                assert box.request('SET_MODE',root,IntValue=Catalog.read().enums['E_Mode']['MANUAL'])
                assert box.request('LOGOUT',root)
            complete = True
            emit(dict(event='complete',checks=len(checks),status=guard()))
        finally:
            api.conn.close()
            suite = ET.Element('testsuite',name='Fraktal.TIA.AccessPersistence',tests=str(len(checks)),
                failures=str(sum(not ok for _,ok in checks)),errors='0' if complete else '1')
            for name,ok in checks:
                case = ET.SubElement(suite,'testcase',name=name)
                if not ok:
                    ET.SubElement(case,'failure',message=name)
            if not complete:
                ET.SubElement(ET.SubElement(suite,'testcase',name='completed'),'error',message='Probe stopped before completion')
            ET.ElementTree(suite).write(out.with_suffix('.xml'),encoding='utf-8',xml_declaration=True)


if __name__ == '__main__':
    probe(Path(sys.argv[1]))
