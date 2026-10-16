"""Native class policy, typed access, atomic sets and actual LOAD_DB restart."""
import json
import os
from pathlib import Path
import sys
import time
from target import TARGET,WORK,original
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from fraktal_tia_binding import Catalog
from tia_mailbox import Mailbox
from tia_webapi import WebApi,leaf_var


def probe(output):
    if output.resolve().parent!=WORK.resolve():raise ValueError('fixed isolated workspace required')
    facts=Catalog.read();before=original();TARGET.guard();checks=[]
    pin=WORK.parents[1]/'TiaStations/Operations_20261016.webapi.pin'
    api=box=None
    with output.open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):stream.write(json.dumps(row)+'\n');stream.flush()
        def check(label,value,expected=True):
            passed=type(value) is type(expected) and value==expected
            emit(dict(event='check',label=label,value=value,expected=expected,passed=passed));checks.append(passed)
            if not passed:raise AssertionError(label)
        def wait(predicate,label,seconds=120):
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                if predicate():return
                time.sleep(.1)
            raise TimeoutError(label)
        def connect():
            nonlocal api,box
            api=WebApi(TARGET.profile['address'],pin,not pin.exists());api.login('fraktal')
            box=Mailbox(api,TARGET.guard,emit)
            wait(lambda:not box.read('FRK_PersistStatus.Restoring'),'restore barrier')
            # Restoring begins FALSE before the first OB scan. The deployed
            # class counts witness that the root actually crossed the barrier.
            wait(lambda:box.read('StationA.Access.ClassCount')==2 and box.read('StationB.Access.ClassCount')==1,'root startup after restore',240)
        def login(user='admin',root='StationA',level=None):
            check('login '+root+' '+user,box.request('LOGIN',root,User=user,Secret=os.environ['FRAKTAL_TIA_'+user.upper()+'_PIN']))
            wait(lambda:not box.read(root+'.Access.LoginBusy'),'login result')
            check('authenticated '+root+' '+user,box.read(root+'.Access.CurrentLevel'),level if level is not None else (4 if user=='admin' else 1))
        def policy(action,level,root='StationA'):
            return box.request('SET_ACCESS_LEVEL',root,IntValue=facts.enums['E_GatedAction'][action],TextValue=str(level))
        def classes(identity,level,write=True,root='StationA'):
            return box.request('SET_CLASS_LEVEL',root,NameValue=identity,IntValue=level,BoolValue=write)
        def control(path,value):
            TARGET.guard();api.call('PlcProgram.Write',dict(var=leaf_var(path.split('.')),value=value))
        def ready():
            wait(lambda:all(not box.read(r+'.ConfigPersist.Pending') for r in ('StationA','StationB')),'read-back durability',240)
        def manifest(root='StationA',model=0):
            found={};page=0
            names=('Scope','WriteKey','WriteRevision','ClassId','ReadLevel','WriteLevel','Readable','ValueText')
            while True:
                if not box.request('QUERY_CONFIG',root,IntValue=page,DurationMs=model):raise RuntimeError('manifest refused')
                base=root+'.HmiResponse.ConfigPage';count=box.read(base+'.EntryCount')
                values=api.bulk([('PlcProgram.Read',dict(var=leaf_var((base+'.Entries[%d].%s'%(i,n)).split('.')))) for i in range(1,count+1) for n in names])
                if any(error for value,error in values):raise RuntimeError('manifest entry read refused')
                for i in range(0,len(values),len(names)):
                    row=dict(zip(names,[v[0] for v in values[i:i+len(names)]]))
                    if row['Scope']==root and row['WriteKey']:found[row['WriteKey']]=row
                if page+1>=box.read(base+'.PageCount'):break
                page+=1
            return found
        def edit(key,value,root='StationA'):
            return box.request('WRITE_CONFIG',root,NameValue=key,IntValue=revisions[key],TextValue=value)
        def set_request(kind,name,config_kind=1):
            return box.request(kind,TextValue=name,IntValue=config_kind)
        def cycle():
            api.conn.close();emit(dict(event='power-cycle',status=TARGET.action('restart')));connect()
        def role(level):
            for key,value in [('Root','StationA'),('Value',level),('Operation',1)]:control('GDB_AccessPersistTest.'+key,value)
            wait(lambda:box.read('GDB_AccessPersistTest.Operation')==0,'trusted fixture provider edit')
            check('trusted provider role update',box.read('GDB_AccessPersistTest.Applied'))
        try:
            connect();login();login(root='StationB');ready()
            wait(lambda:box.read('GDB_ClassPolicyTest.Done'),'native class assertions')
            check('native class assertions',box.read('GDB_ClassPolicyTest.Checks'),16)
            check('native class failures',box.read('GDB_ClassPolicyTest.Failures'),0)
            check('rootA declares two classes',box.read('StationA.Access.ClassCount'),2)
            check('rootB has independent policy',box.read('StationB.Access.Classes[1].WriteLevel'),2)
            prior={a:box.read('StationA.Access.Policy.Required[%d]'%facts.enums['E_GatedAction'][a]) for a in ('DATA_READ','DATA_WRITE','CONFIG_SET','ACCESS_POLICY')}
            old=manifest();revisions={k:r['WriteRevision'] for k,r in old.items()}
            label=box.read('StationA.StationCfg.SiteLabel');line_gain=old['line.gain']['ValueText']
            check('allow operator CONFIG_SET explicitly',policy('CONFIG_SET',1))
            check('set DATA_READ admin',policy('DATA_READ',4));check('set DATA_WRITE admin',policy('DATA_WRITE',4))
            check('gate class edits at engineer',policy('ACCESS_POLICY',3))
            rev=box.read('StationA.ConfigRev');check('class read policy edit',classes('public',0,False))
            check('class change invalidates manifest',box.read('StationA.ConfigRev')!=rev)
            generation=box.read('GDB_ClassPolicyTest.ClassGeneration')
            check('same class level is accepted',classes('public',0,False))
            check('same class level does not dirty storage',box.read('GDB_ClassPolicyTest.ClassGeneration'),generation)
            check('unknown class cannot be edited',classes('missing',0),False)
            check('out-of-range class level refused',classes('public',5),False)
            denied=api.bulk([('PlcProgram.Write',dict(var=leaf_var(['StationA','Access','Classes[1]','WriteLevel']),value=0))])
            check('class table is externally read only',all(error is not None for value,error in denied))
            check('logout for anonymous presentation',box.request('LOGOUT'))
            rows=manifest()
            check('custom public class readable below DATA_READ',rows['siteLabel']['Readable'])
            check('public field carries identity',rows['siteLabel']['ClassId'],'public')
            check('public effective read level',rows['siteLabel']['ReadLevel'],0)
            check('public effective write level',rows['siteLabel']['WriteLevel'],1)
            check('builtin field keeps DATA_READ',rows['timeout']['ReadLevel'],4)
            check('unreadable builtin value blanked',rows['timeout']['ValueText'],'')
            check('commissioning value hidden',rows['preset']['Readable'],False)
            check('commissioning value blanked',rows['preset']['ValueText'],'')
            check('undeclared class fails admin',rows['grade']['WriteLevel'],4)
            check('value minimum raises public class',rows['gain']['WriteLevel'],3)
            login('operator')
            check('operator cannot change class policy',classes('public',0),False)
            check('public edit below blanket DATA_WRITE',edit('siteLabel','class-live'))
            check('public value applied',box.read('StationA.StationCfg.SiteLabel'),'class-live')
            gain=box.read('StationA.StationCfg.Gain')
            check('raised value minimum refuses operator',edit('gain','2.75'),False)
            check('refusal leaves value unchanged',box.read('StationA.StationCfg.Gain'),gain)
            check('refusal names exact key',box.read('StationA.ConfigPersist.LastRejectKey'),'gain')
            check('refusal reports access',box.read('StationA.HmiResponse.Diagnostic'),'std.error.accessDenied')
            check('capture uses same public class',box.request('CAPTURE_CONFIG',NameValue='capturedCycles',IntValue=revisions['capturedCycles']))
            check('shared line permits public owner edit',edit('line.gain','2.5'))
            login('operator','StationB')
            check('peer class refuses same user on shared line',edit('line.gain','3.0','StationB'),False)
            check('line refusal names value',box.read('StationB.ConfigPersist.LastRejectKey'),'line.gain')
            check('save reveals nothing and needs CONFIG_SET only',set_request('SAVE_CONFIG_SET','class-hidden'))
            check('export rechecks every read level',box.request('EXPORT_CONFIG_SET',TextValue='class-hidden',IntValue=0),False)
            check('export names first unreadable record',bool(box.read('StationA.ConfigPersist.LastRejectKey')))
            check('change public value after saved snapshot',edit('siteLabel','class-after'))
            check('load rechecks all write levels before commit',set_request('LOAD_CONFIG_SET','class-hidden'),False)
            check('rejected load changes no earlier staged value',box.read('StationA.StationCfg.SiteLabel'),'class-after')
            login();check('admin loads complete station set',set_request('LOAD_CONFIG_SET','class-hidden'))
            check('accepted load applies saved value',box.read('StationA.StationCfg.SiteLabel'),'class-live')
            check('model set saved',set_request('SAVE_CONFIG_SET','class-model',0))
            check('write threshold permits engineer',policy('DATA_WRITE',0));role(3);login('operator',level=3)
            check('load requires write access without hidden read access',set_request('LOAD_CONFIG_SET','class-model',0))
            check('export still requires read access',box.request('EXPORT_CONFIG_SET',TextValue='class-model',IntValue=0),False)
            check('class self-lockout refused',classes('public',4),False)
            login();role(1);login()
            check('restore blanket write before restart',policy('DATA_WRITE',4))
            check('commission public write to technician',classes('public',2))
            ready();control('GDB_ClassPolicyTest.PoisonPulse',True)
            wait(lambda:box.read('GDB_ClassPolicyTest.Poisoned'),'retained cache deliberately poisoned')
            cycle();check('restart clears operator session',box.read('StationA.Access.CurrentLevel'),0)
            check('LOAD_DB overrides poisoned retained class cache',box.read('StationA.Access.Classes[1].WriteLevel'),2)
            check('existing action policy survives new class domain',box.read('StationA.Access.Policy.Required[1]'),4)
            check('redeclaration keeps commissioned class',box.read('StationA.Access.Classes[1].WriteLevel'),2)
            login();ready();control('GDB_ClassPolicyTest.DamagePulse',True)
            wait(lambda:box.read('GDB_ClassPolicyTest.Damaged'),'both class anchors damaged')
            cycle();check('class loss is published',box.read('StationA.ConfigPersist.RestoreLost'))
            check('class loss restricts effective policy',box.read('StationA.Access.Classes[1].WriteLevel'),4)
            check('peer class remains commissioned',box.read('StationB.Access.Classes[1].WriteLevel'),2)
            login();check('class loss refuses edits until acknowledged',edit('siteLabel','must-not-apply'),False)
            check('acknowledge restrictive class fallback',box.request('ACK_CONFIG_RESTORE'))
            ready();check('restore acknowledgment published',box.read('StationA.ConfigPersist.RestoreAcknowledged'))
            check('commission recovered public write',classes('public',1))
            check('commission recovered public read',classes('public',0,False))
            check('commission recovered private write',classes('commissioning',3))
            check('commission recovered private read',classes('commissioning',3,False))
            check('normalize fixture label',edit('siteLabel',label))
            check('normalize shared line gain',edit('line.gain',line_gain))
            for name in ('class-hidden','class-model'):check('remove test set '+name,box.request('DELETE_CONFIG_SET',TextValue=name))
            for action,level in prior.items():check('restore action policy '+action,policy(action,level))
            ready();box.request('LOGOUT');box.request('LOGOUT','StationB')
            check('original Fraktal unchanged',original(),before)
            emit(dict(event='complete',checks=len(checks),failures=sum(not v for v in checks)))
        finally:
            if api and api.conn:api.conn.close()


if __name__=='__main__':probe(Path(sys.argv[1]))
