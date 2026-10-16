"""Guarded native controls for a two-root, three-level Unit forest."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'tools'))
from tia_webapi import WebApi,leaf_var
from fraktal_tia_binding import Catalog
spec=importlib.util.spec_from_file_location('unit_probe',HERE.parent/'Unit/probe_web.py')
UNIT=importlib.util.module_from_spec(spec);spec.loader.exec_module(UNIT)


def probe(out):
    catalog=Catalog.read();modes=catalog.enums['E_Mode'];kinds=catalog.enums['E_HmiRequestKind'];gates=catalog.enums['E_GatedAction']
    pin=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin'
    checks=[]
    completed=False
    with out.open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):stream.write(json.dumps(row,ensure_ascii=True)+'\n');stream.flush()
        def check(label,actual,expected):
            ok=type(actual) is type(expected) and actual==expected
            checks.append((label,ok));emit({'event':'check','label':label,'actual':actual,'expected':expected,'passed':ok})
            if not ok:raise AssertionError(label)
        api=WebApi('169.254.212.49',pin,False)
        def read(path):return api.call('PlcProgram.Read',{'var':leaf_var(path.split('.'))})
        def wait(path,value):
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                actual=read(path)
                if actual==value:return
                time.sleep(.02)
            check('wait '+path,actual,value)
        def write(values):
            emit({'event':'mutation-guard','status':UNIT.guard(),'targets':list(values)})
            replies=api.bulk([('PlcProgram.Write',{'var':leaf_var(k.split('.')),'value':v}) for k,v in values.items()])
            if any(error for value,error in replies):raise AssertionError('mutation refused: '+str(replies))
        def request(kind,iv=0,target='',root='StationA'):
            seq=(int(read(root+'.HmiRequest.Sequence'))+1)&0xffffffff
            if seq==0:seq=1
            write({root+'.HmiRequest.Kind':kinds[kind],root+'.HmiRequest.IntValue':iv,root+'.HmiRequest.TargetPath':target,root+'.HmiRequest.DurationMs':0})
            write({root+'.HmiRequest.Sequence':seq});wait(root+'.HmiResponse.AckSequence',seq)
            accepted=read(root+'.HmiResponse.Accepted')
            emit({'event':'ack','root':root,'kind':kind,'sequence':seq,'accepted':accepted,'released':read(root+'.HmiResponse.Report.Released')})
            return accepted
        def set_test(**values):write({'GDB_RoutingTest.'+k:v for k,v in values.items()})
        def mode(value,root='StationA'):
            check('set mode '+root+' '+value,request('SET_MODE',modes[value],root=root),True)
            wait(root+'.ModeActivePublished',modes[value])
        def local(kind,value=0):
            set_test(LocalKind=kinds[kind],LocalValue=value,LocalPulse=True)
            wait('GDB_RoutingTest.LocalPulse',False)
            return read('GDB_RoutingTest.LocalAccepted')
        def local_mode(value):
            check('local nested mode '+value,local('SET_MODE',modes[value]),True)
            wait('StationA.Satellite.ModeActivePublished',modes[value])
        def report():
            count=read('StationA.HmiResponse.Report.Count')
            return [{'path':read('StationA.HmiResponse.Report.Reasons[%d].SourcePath'%i),'description':read('StationA.HmiResponse.Report.Reasons[%d].Description'%i),'kind':read('StationA.HmiResponse.Report.Reasons[%d].Kind'%i)} for i in range(1,count+1)]
        def release(value,target):
            check('manual query consumed',request('RELEASE_MANUAL',value,target),True)
            return read('StationA.HmiResponse.Report.Released')
        def finish():
            write({'GDB_UnitTest.FinishCycle':True});set_test(NestedFinish=True,InnerFinish=True)
            for root in roots:wait(root+'.Status.State',0)
            write({'GDB_UnitTest.FinishCycle':False});set_test(NestedFinish=False,InnerFinish=False)
        roots=['StationA','StationA.Satellite','StationA.Satellite.Inner']
        target='StationA.Cell.Gate';nested='StationA.Satellite.Inner.Cell.Gate'
        def catalog_read():
            # Activation-static catalogs now arrive through the Core manifest.
            catalog_values={};page=0
            wanted={'CatalogCount','Catalog/Catalog[6]/Value','Catalog/Catalog[6]/Label','Catalog/Catalog[6]/Style'}
            while not wanted.issubset(catalog_values):
                if not request('QUERY_CONFIG',page):raise AssertionError('catalog page refused')
                base='StationA.HmiResponse.ConfigPage'
                count=read(base+'.EntryCount')
                rows=api.bulk([('PlcProgram.Read',{'var':leaf_var((base+'.Entries[%d].%s'%(i,f)).split('.'))}) for i in range(1,count+1) for f in ('Scope','Item','ValueText')])
                if any(error for value,error in rows):raise AssertionError('catalog row unreadable')
                values=[value for value,error in rows]
                for index in range(0,len(values),3):
                    scope,item,value=values[index:index+3]
                    if scope==target:catalog_values[item]=value
                page+=1
                if page>=read(base+'.PageCount') and not wanted.issubset(catalog_values):raise AssertionError('catalog missing')
            return catalog_values
        try:
            api.login('fraktal');emit({'event':'connection','pin':api.fingerprint,'version':api.call('Api.Version'),'permissions':api.call('Api.GetPermissions')})
            for root in roots:check('initial MANUAL '+root,read(root+'.ModeActivePublished'),modes['MANUAL'])
            catalog_values=catalog_read()
            check('catalog count',int(catalog_values['CatalogCount']),7)
            check('catalog value',int(catalog_values['Catalog/Catalog[6]/Value']),6)
            check('catalog label',catalog_values['Catalog/Catalog[6]/Label'],'Instant')
            check('catalog oneshot',int(catalog_values['Catalog/Catalog[6]/Style']),catalog.enums['E_CommandStyle']['ONESHOT'])
            set_test(ManualAccessLock=True)
            check('manual access query blocks',release(6,target),False)
            check('manual access reason present',catalog.enums['E_ReleaseKind']['ACCESS'] in [r['kind'] for r in report()],True)
            check('manual access action matches',request('MANUAL_COMMAND',6,target),False)
            set_test(ManualAccessLock=False)
            before=read('GDB_RoutingTest.ManStarts');history=read('StationA.AlarmLog.RingHead')
            check('instant manual released',release(6,target),True)
            check('query does not command',read('GDB_RoutingTest.ManStarts'),before)
            check('query does not audit',read('StationA.AlarmLog.RingHead'),history)
            check('instant manual accepted',request('MANUAL_COMMAND',6,target),True)
            wait('GDB_RoutingTest.ManStarts',before+1);wait(target+'.Status.State',0)
            check('manual execute drops automatically',read('GDB_RoutingTest.ManExecute'),False)
            head=read('StationA.AlarmLog.RingHead')
            check('manual acceptance audited',read('StationA.AlarmLog.Ring[%d].Description'%head).startswith('std.audit.manualCommandAccepted'),True)
            check('audit target canonical',read('StationA.AlarmLog.Ring[%d].SourcePath'%head),target)
            check('peer target rejected',request('MANUAL_COMMAND',6,'StationB.Cell.Gate'),False)
            check('peer did not execute',read('StationB.Cell.Gate.OutImm.StartCount'),0)
            check('unknown target rejected',request('MANUAL_COMMAND',6,'StationA.Missing'),False)
            check('unknown command rejected',request('MANUAL_COMMAND',999,target),False)
            set_test(PermitOne=False,PermitTwo=False)
            check('both directional conditions block',release(2,target),False)
            check('both reasons present',read('StationA.HmiResponse.Report.Count'),2)
            check('both canonical owning paths',[r['path'] for r in report()],[target,target])
            check('both descriptions',[r['description'] for r in report()],['test.manual.first','test.manual.second'])
            check('other direction unaffected',release(6,target),True)
            write({'GDB_UnitTest.Permit':False})
            check('common plus directional block',release(2,target),False)
            check('common before directional',[r['path'] for r in report()],['StationA.Cell.Clamp',target,target])
            before=read('GDB_RoutingTest.ManStarts')
            check('blocked command rejected',request('MANUAL_COMMAND',2,target),False)
            check('blocked command has no handshake',read('GDB_RoutingTest.ManStarts'),before)
            write({'GDB_UnitTest.Permit':True});set_test(PermitOne=True)
            check('remaining condition still blocks',release(2,target),False)
            check('remaining reason live',[r['description'] for r in report()],['test.manual.second'])
            set_test(PermitTwo=True)
            check('all conditions cleared',release(2,target),True)
            check('manual wait accepted',request('MANUAL_COMMAND',2,target),True);wait(target+'.Status.State',1)
            check('busy target rejected',release(6,target),False)
            mode('AUTO');wait(target+'.Status.State',0)
            check('leaving manual drops execute',read('GDB_RoutingTest.ManExecute'),False)
            check('auto manual rejected',request('MANUAL_COMMAND',6,target),False)
            mode('MANUAL');local_mode('AUTO')
            check('nested owner must be manual',release(6,nested),False)
            check('nested owner reason exists','StationA.Satellite' in [r['path'] for r in report()],True)
            local_mode('MANUAL')
            check('nested manual accepted',request('MANUAL_COMMAND',6,nested),True)
            wait(nested+'.OutImm.StartCount',1);wait(nested+'.Status.State',0)
            set_test(RootManualPermit=False)
            check('nested common condition blocks',release(6,nested),False)
            check('nested condition canonical','StationA.Satellite.Cell.Clamp' in [r['path'] for r in report()],True)
            set_test(RootManualPermit=True,NestedAccessLock=True)
            mode('AUTO')
            for root in roots:wait(root+'.ModeActivePublished',modes['AUTO'])
            check('parent start accepted',request('START'),True)
            for root in roots:wait(root+'.RunningPublished',True);check('cascade running '+root,read(root+'.RunningPublished'),True)
            check('peer stays idle',read('StationB.RunningPublished'),False)
            check('local independent start access checked',local('START'),False)
            check('trusted cascade did not widen local access',read('GDB_RoutingTest.LocalFirstKind'),catalog.enums['E_ReleaseKind']['ACCESS'])
            history=read('StationA.AlarmLog.RingHead')
            check('stop query consumed',request('RELEASE_ACTION',gates['START_STOP']),True)
            check('stop query matches gate',read('StationA.HmiResponse.Report.Released'),True)
            check('stop query does not stop',read('StationA.StopPendingPublished'),False)
            check('action query does not audit',read('StationA.AlarmLog.RingHead'),history)
            check('parent stop accepted',request('STOP'),True)
            for root in roots:wait(root+'.StopPendingPublished',True)
            finish();set_test(NestedAccessLock=False)
            mode('AUTO');check('auto start before unsupported child mode',request('START'),True)
            for root in roots:wait(root+'.RunningPublished',True)
            check('unsupported child mode request accepted by parent',request('SET_MODE',modes['CHANGEOVER']),True)
            wait('StationA.Satellite.StopPendingPublished',True)
            check('unsupported child mode not forced',read('StationA.Satellite.ModeActivePublished'),modes['AUTO'])
            finish();wait('StationA.ModeActivePublished',modes['CHANGEOVER'])
            events=[(read('StationA.AlarmLog.Ring[%d].Description'%i),read('StationA.AlarmLog.Ring[%d].SourcePath'%i)) for i in range(1,catalog.capacities['MAX_ALARM_RING']+1)]
            check('unsupported child event published',('std.event.childModeUnsupported','StationA.Satellite') in events,True)
            check('parent remains fault-free',read('StationA.Status.FaultActive'),False)
            check('negative mode rejected',request('SET_MODE',-1),False)
            check('blocked mode start accepted',request('START'),True);wait('StationA.RunningPublished',True)
            check('mode action query consumed',request('RELEASE_ACTION',gates['MODE_CHANGE']),True)
            check('blocked mode query rejects',read('StationA.HmiResponse.Report.Released'),False)
            check('blocked mode action rejects',request('SET_MODE',modes['HOME']),False)
            check('unsupported action query consumed',request('RELEASE_ACTION',999),True)
            check('unsupported action closed',read('StationA.HmiResponse.Report.Released'),False)
            check('stop blocked mode accepted',request('STOP'),True);finish();mode('MANUAL')
            check('idle reset query consumed',request('RELEASE_ACTION',gates['ALARM_RESET']),True)
            check('idle reset report withheld',read('StationA.HmiResponse.Report.Released'),False)
            check('idle reset action matches query',request('OPERATOR_RESET'),False)
            mode('AUTO');check('start before nested reset',request('START'),True)
            for root in roots:wait(root+'.RunningPublished',True)
            resets={root:read(root+'.OutImm.Resets') for root in roots}
            check('one parent reset accepted',request('OPERATOR_RESET'),True)
            for root in roots:
                wait(root+'.Status.State',0)
                check('nested reset reaction '+root,read(root+'.OutImm.Resets'),resets[root]+1)
            time.sleep(.1)
            for root in roots:check('reset did not queue restart '+root,read(root+'.RunningPublished'),False)
            mode('HOME');check('start before deferred exit with nested run',request('START'),True)
            for root in roots:wait(root+'.RunningPublished',True)
            write({'GDB_UnitTest.ExitHold':True})
            check('deferred exit request',request('SET_MODE',modes['CHANGEOVER']),True)
            wait('StationA.ErrorID',catalog.enums['E_Reason']['TIMEOUT'])
            check('deferred exit keeps current mode',read('StationA.ModeActivePublished'),modes['HOME'])
            for root in roots[1:]:wait(root+'.Status.State',0);check('exit timeout releases nested run '+root,read(root+'.RunningPublished'),False)
            write({'GDB_UnitTest.ExitHold':False})
            check('reset after deferred exit timeout',request('OPERATOR_RESET'),True)
            for root in roots:wait(root+'.Status.State',0)
            check('start before immediate exit',request('START'),True)
            for root in roots:wait(root+'.RunningPublished',True)
            check('immediate unsupported child exit',request('SET_MODE',modes['CHANGEOVER']),True)
            wait('StationA.ModeActivePublished',modes['CHANGEOVER'])
            check('immediate exit releases nested run',read('StationA.Satellite.RunningPublished'),False)
            mode('AUTO');check('start before warm restart',request('START'),True)
            for root in roots:wait(root+'.RunningPublished',True)
            boot=read('GDB_UnitTest.BootStamp')
            for action in ('halt','run'):
                emit({'event':'mode-guard','action':action,'status':UNIT.guard()})
                result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1'),'-Action',action],capture_output=True)
                emit({'event':'mode-result','action':action,'exit':result.returncode,'output':result.stdout.decode('utf-8-sig')})
                if result.returncode:raise RuntimeError('mode act failed')
            for root in roots:
                wait(root+'.Status.State',0)
                check('warm restart MANUAL '+root,read(root+'.ModeActivePublished'),modes['MANUAL'])
                check('warm restart no replay '+root,read(root+'.RunningPublished'),False)
            check('warm restart observed',read('GDB_UnitTest.BootStamp')!=boot,True)
            check('catalog survives restart',int(catalog_read()['CatalogCount']),7)
            check('fresh manual request after restart',request('MANUAL_COMMAND',6,target),True)
            wait(target+'.OutImm.StartCount',1);wait(target+'.Status.State',0)
            for path in ['FRK_UnitScratch.Response.Accepted',target+'.ManConditions[1].Ok']:
                value,error=api.bulk([('PlcProgram.Read',{'var':leaf_var(path.split('.'))})])[0]
                check('private '+path,error.get('code') if error else None,200)
            emit({'event':'mutation-guard','status':UNIT.guard(),'target':'StationA.Satellite.HmiRequest.Kind'})
            value,error=api.bulk([('PlcProgram.Write',{'var':leaf_var(['StationA','Satellite','HmiRequest','Kind']),'value':3})])[0]
            check('nested mailbox remains read-only',error.get('code') if error else None,205)
            completed=True
            emit({'event':'summary','checks':len(checks),'failed':0,'passed':True})
        finally:
            if not completed and all(ok for label,ok in checks):checks.append(('probe completed',False))
            if api.token:api.call('Api.Logout')
            api.conn.close()
            suite=ET.Element('testsuite',name='Fraktal.TIA.Unit.Routing.Native',tests=str(len(checks)),failures=str(sum(not ok for label,ok in checks)))
            for label,ok in checks:
                case=ET.SubElement(suite,'testcase',name=label)
                if not ok:ET.SubElement(case,'failure',message=label)
            ET.ElementTree(suite).write(out.with_suffix('.junit.xml'),encoding='utf-8',xml_declaration=True)


if __name__=='__main__':probe(Path(sys.argv[1]))
