"""Guarded native tests of Core-compatible hashes, root sessions and policy gates."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/'tools'))
from fraktal_tia_binding import Catalog
from tia_webapi import WebApi, leaf_var
spec = importlib.util.spec_from_file_location('unit_probe', HERE.parent/'Unit/probe_web.py')
UNIT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(UNIT)


def probe(out):
    kinds = Catalog.read().enums['E_HmiRequestKind']
    pins = {user:os.environ[env] for user,env in
            (('operator','FRAKTAL_TIA_OPERATOR_PIN'),('admin','FRAKTAL_TIA_ADMIN_PIN'))}
    checks = []
    completed = False
    api = WebApi('169.254.212.49', Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin', False)
    with out.open('x', encoding='ascii', newline='\n') as stream:
        def emit(row):
            stream.write(json.dumps(row, ensure_ascii=True)+'\n')
            stream.flush()

        def check(label, actual, expected):
            ok = type(actual) is type(expected) and actual == expected
            checks.append((label,ok))
            emit({'event':'check','label':label,'actual':actual,'expected':expected,'passed':ok})
            if not ok:
                raise AssertionError(label)

        def read(path):
            return api.call('PlcProgram.Read', {'var':leaf_var(path.split('.'))})

        def writes(values):
            emit({'event':'mutation-guard','status':UNIT.guard(),'targets':list(values)})
            rows = api.bulk([('PlcProgram.Write',{'var':leaf_var(p.split('.')),'value':v}) for p,v in values.items()])
            if any(error for value,error in rows):
                raise AssertionError('native write refused')

        def until(predicate, label, seconds=10):
            deadline = time.monotonic()+seconds
            while time.monotonic() < deadline:
                if predicate():
                    return
                time.sleep(.02)
            raise AssertionError(label)

        def request(kind, root='StationA', **fields):
            seq = (read(root+'.HmiRequest.Sequence')+1) & 0xffffffff or 1
            values = {'Kind':kinds[kind],'IntValue':0,'DurationMs':0,'TextValue':'','User':'','Secret':'','TargetPath':''}
            values.update(fields)
            writes({root+'.HmiRequest.'+n:v for n,v in values.items()})
            writes({root+'.HmiRequest.Sequence':seq})
            until(lambda: read(root+'.HmiResponse.AckSequence')==seq, 'mailbox acknowledgement')
            return seq, read(root+'.HmiResponse.Accepted')

        def login(user, secret, root='StationA'):
            start = time.monotonic()
            seq, accepted = request('LOGIN', root, User=user, Secret=secret)
            check(root+' login consumed', accepted, True)
            until(lambda: read(root+'.Access.LoginResultSequence')==seq and not read(root+'.Access.LoginBusy'), 'correlated login result')
            result = {key:read(root+'.Access.'+key) for key in ('CurrentLevel','CurrentUser','LoginFailed','SessionGeneration')}
            emit({'event':'login-result','root':root,'sequence':seq,'durationMs':round((time.monotonic()-start)*1000),'result':result})
            check('transport secret cleared',read(root+'.HmiRequest.Secret') == '',True)
            check('sampled secret cleared',read('GDB_UnitTest.SnapshotSecretCleared'),True)
            return result

        def policy(gate, level, expected=True):
            _, accepted = request('SET_ACCESS_LEVEL', IntValue=gate, TextValue=str(level))
            check('policy gate %d level %s'%(gate,level), accepted, expected)

        try:
            api.login('fraktal')
            emit({'event':'connection','pin':api.fingerprint,'version':api.call('Api.Version'),'permissions':api.call('Api.GetPermissions')})
            out.with_suffix('.certificate.der').write_bytes(api.conn.sock.getpeercert(binary_form=True))
            for index, data in enumerate((b'',b'abc',bytes(range(32)),bytes(range(48)))):
                rows = api.bulk([('PlcProgram.Read',{'var':leaf_var(['GDB_AccessTest','Hash%d[%d]'%(index,i)])}) for i in range(32)])
                if any(error for value,error in rows):
                    raise AssertionError('hash witness unavailable')
                check('native SHA-256 vector %d'%index,bytes(value for value,error in rows).hex(),hashlib.sha256(data).hexdigest())
            check('startup NONE',read('StationA.Access.CurrentLevel'),0)
            check('peer startup NONE',read('StationB.Access.CurrentLevel'),0)
            _, accepted = request('MANUAL_COMMAND', TargetPath='StationA.Cell.Gate', IntValue=6)
            check('unauthenticated manual denied',accepted,False)
            _, accepted = request('SET_MODE', IntValue=1)
            check('unauthenticated mode denied',accepted,False)
            result = login('unknown',pins['operator'])
            check('unknown user rejected',result['LoginFailed'],True)
            check('unknown user no level',result['CurrentLevel'],0)
            result = login('operator','wrong')
            check('wrong PIN rejected',result['LoginFailed'],True)
            revision = read('StationA.ConfigRev')
            result = login('operator',pins['operator'])
            check('operator accepted',result['LoginFailed'],False)
            check('operator level',result['CurrentLevel'],1)
            check('operator identity',result['CurrentUser'],'operator')
            check('authentication changes manifest revision',read('StationA.ConfigRev')!=revision,True)
            generation = result['SessionGeneration']
            check('peer login isolation',read('StationB.Access.CurrentLevel'),0)
            result = login('operator','wrong')
            check('failed attempt flagged',result['LoginFailed'],True)
            check('failed attempt preserves valid session',result['CurrentLevel'],1)
            check('failed attempt preserves generation',result['SessionGeneration'],generation)
            before = read('GDB_RoutingTest.ManStarts')
            _, accepted = request('MANUAL_COMMAND', TargetPath='StationA.Cell.Gate', IntValue=6)
            check('authenticated manual accepted',accepted,True)
            until(lambda:read('GDB_RoutingTest.ManStarts')==before+1,'manual start counter')
            check('authenticated command issued once',read('GDB_RoutingTest.ManStarts'),before+1)
            policy(2,3,False)
            result = login('admin',pins['admin'])
            check('admin level',result['CurrentLevel'],4)
            for gate,level in ((-1,1),(12,1),(2,5),(2,'01')):
                policy(gate,level,False)
            policy(2,3)
            check('policy stored',read('StationA.Access.Policy.Required[2]'),3)
            result = login('operator',pins['operator'])
            _, accepted = request('MANUAL_COMMAND', TargetPath='StationA.Cell.Gate', IntValue=6)
            check('raised manual threshold enforced',accepted,False)
            login('admin',pins['admin'])
            policy(2,1)
            policy(8,0)
            login('operator',pins['operator'])
            policy(8,4,False)
            check('self-lockout leaves policy unchanged',read('StationA.Access.Policy.Required[8]'),0)
            login('admin',pins['admin'])
            policy(8,4)
            for duration,expected in ((604800001,False),(4294967295,False),(604800000,True),(0,True)):
                _, accepted = request('SET_SESSION_TIMEOUT',DurationMs=duration)
                check('timeout bound %d'%duration,accepted,expected)
            for root in ('StationA','StationB'):
                login('admin',pins['admin'],root)
            _, accepted = request('SET_SESSION_TIMEOUT',DurationMs=2000)
            check('idle timeout accepted',accepted,True)
            # A successful authenticated mutation starts the idle clock. Queries
            # and transport reads must allow that session to expire.
            deadline = time.monotonic()+6
            while read('StationA.Access.CurrentLevel') and time.monotonic()<deadline:
                request('RELEASE_MANUAL',TargetPath='StationA.Cell.Gate',IntValue=6)
            check('release polling does not retain session',read('StationA.Access.CurrentLevel'),0)
            check('idle root does not log out peer',read('StationB.Access.CurrentLevel'),4)
            login('admin',pins['admin'])
            request('SET_SESSION_TIMEOUT',DurationMs=4000)
            login('operator',pins['operator'])
            started = time.monotonic()
            while time.monotonic()-started < 5:
                _, accepted = request('MANUAL_COMMAND',TargetPath='StationA.Cell.Gate',IntValue=6)
                check('activity manual accepted',accepted,True)
                time.sleep(.3)
            check('accepted mutations refresh idle clock',read('StationA.Access.CurrentLevel'),1)
            head = read('StationA.HistoryHead')
            description = read('StationA.History[%d].Description'%head)
            check('audit includes action', 'kind=' in description,True)
            check('audit includes user', 'operator' in description,True)
            check('audit excludes PINs',all(pin not in description for pin in pins.values()),True)
            generation = read('StationA.Access.SessionGeneration')
            request('LOGOUT')
            check('logout NONE',read('StationA.Access.CurrentLevel'),0)
            check('logout clears identity',read('StationA.Access.CurrentUser'),'')
            check('logout advances generation',read('StationA.Access.SessionGeneration')!=generation,True)
            check('logout records previous user','operator' in read('StationA.History[%d].Description'%read('StationA.HistoryHead')),True)
            seq,_ = request('LOGIN',User='operator',Secret=pins['operator'])
            request('LOGOUT')
            time.sleep(1)
            check('logout prevents late grant',read('StationA.Access.CurrentLevel'),0)
            writes({'GDB_AccessTest.CancelOnLogin':True})
            seq,_ = request('LOGIN',User='operator',Secret=pins['operator'])
            check('deterministic cancellation interrupted busy provider',read('GDB_AccessTest.InterruptedBusy'),True)
            check('cancel clears pending worker',read('StationA.Access.LoginBusy'),False)
            time.sleep(1)
            check('cancelled valid credentials grant no session',read('StationA.Access.CurrentLevel'),0)
            writes({'GDB_AccessTest.SupersedeOnLogin':True})
            seq,_ = request('LOGIN',User='operator',Secret=pins['operator'])
            latest = read('GDB_AccessTest.SupersededSequence')
            until(lambda:read('StationA.Access.LoginResultSequence')==latest and not read('StationA.Access.LoginBusy'),'superseding result')
            check('superseding result has new correlation',latest!=seq,True)
            check('superseded valid credentials grant no session',read('StationA.Access.CurrentLevel'),0)
            check('latest invalid credentials explicitly fail',read('StationA.Access.LoginFailed'),True)
            writes({'GDB_AccessTest.ProviderOff':True})
            result = login('operator',pins['operator'])
            check('missing provider fails closed',result['LoginFailed'],True)
            check('missing provider grants no level',result['CurrentLevel'],0)
            writes({'GDB_AccessTest.ProviderOff':False})
            for path in ('FRK_LocalUsers.Count','FRK_LocalUsers.Rows[1].PinHash[0]','FRK_LocalUsers.Rows[1].Salt[0]',
                         'StationA.Access.ProviderEnabled','StationA.Access.CandidateUser','StationA.Access.Digest[0]'):
                rows = api.bulk([('PlcProgram.Read',{'var':leaf_var(path.split('.'))})])
                check('private read refused '+path,rows[0][1]['code'],200)
            for path,value in (('StationA.Access.CurrentLevel',4),('StationA.Access.Policy.Required[2]',0)):
                emit({'event':'mutation-guard','status':UNIT.guard(),'targets':[path]})
                rows = api.bulk([('PlcProgram.Write',{'var':leaf_var(path.split('.')),'value':value})])
                check('authority write refused '+path,rows[0][1]['code'],205)
            login('admin',pins['admin'])
            for action in ('halt','run'):
                emit({'event':'mode-guard','status':UNIT.guard(),'action':action})
                result = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1'),'-Action',action],capture_output=True)
                if result.returncode:
                    raise AssertionError('native mode action failed')
                emit({'event':'mode-result','action':action,'output':result.stdout.decode('utf-8-sig').strip()})
            check('restart session cleared',read('StationA.Access.CurrentLevel'),0)
            check('restart pending cleared',read('StationA.Access.LoginBusy'),False)
            check('restart identity cleared',read('StationA.Access.CurrentUser'),'')
            login('operator',pins['operator'])
            request('LOGOUT')
            completed = True
        finally:
            api.conn.close()
            if not completed:
                checks.append(('probe completed',False))
            emit({'event':'summary','checks':len(checks),'failures':sum(not ok for label,ok in checks),'completed':completed})
            suite = ET.Element('testsuite',name='Fraktal.TIA.Access',tests=str(len(checks)),failures=str(sum(not ok for label,ok in checks)))
            for label,ok in checks:
                case = ET.SubElement(suite,'testcase',name=label)
                if not ok:
                    ET.SubElement(case,'failure',message=label)
            ET.ElementTree(suite).write(out.with_suffix('.junit.xml'),encoding='utf-8',xml_declaration=True)


if __name__ == '__main__':
    probe(Path(sys.argv[1]))
