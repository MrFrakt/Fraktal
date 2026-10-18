"""Wired GRAPH pacing and operator jumps over the real root mailbox."""
import json
import os
from pathlib import Path
import sys
import time
from target import TARGET,WORK,original
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from fraktal_tia_binding import Catalog
from tia_mailbox import Mailbox
from tia_webapi import WebApi,WebApiError


def probe(output):
    if output.resolve().parent!=WORK.resolve():raise ValueError('fixed isolated workspace required')
    facts=Catalog.read();before=original();TARGET.guard();checks=[]
    pin=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Press_Features_20261016.webapi.pin'
    api=WebApi(TARGET.profile['address'],pin,not pin.exists())
    with output.open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):stream.write(json.dumps(row)+'\n');stream.flush()
        def check(label,value,expected=True):
            passed=type(value) is type(expected) and value==expected
            emit(dict(event='check',label=label,value=value,expected=expected,passed=passed));checks.append(passed)
            if not passed:raise AssertionError(label)
        def wait(predicate,label,seconds=45):
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                if predicate():return
                time.sleep(.05)
            emit(dict(event='timeout',label=label,state=read('Status.State'),step=read('CurrentStep.StepNo'),diagnostic=read('Status.Diagnostic.Description')))
            raise TimeoutError(label)
        def read(path):return box.read('PressDemo.'+path)
        def request(kind,**fields):return box.request(kind,root='PressDemo',**fields)
        def mode(name):
            check('select '+name,request('SET_MODE',IntValue=facts.enums['E_Mode'][name]))
            wait(lambda:read('ModeActivePublished')==facts.enums['E_Mode'][name],'mode '+name)
        def style(name):check('select '+name,request('SET_RUN_STYLE',IntValue=facts.enums['E_RunStyle'][name]))
        def idle():wait(lambda:read('Status.State')==facts.enums['E_ExecState']['READY'],'root READY')
        def advance_until(step):
            for index in range(24):
                if read('CurrentStep.StepNo')==step:return
                check('single step request '+str(index),request('STEP_REQUEST'))
                time.sleep(.1)
            raise AssertionError('single step did not reach '+str(step))
        try:
            api.login('fraktal');box=Mailbox(api,TARGET.guard,emit)
            wait(lambda:not box.read('FRK_PersistStatus.Restoring'),'LOAD_DB restore');idle()
            active=[read('AlarmLog.Active[%d].ReasonCode'%i) for i in range(1,facts.capacities['MAX_ALARM_ACTIVE']+1) if read('AlarmLog.Active[%d].State'%i)!=facts.enums['E_AlarmState']['CLOSED']]
            check('simulation gate visible',facts.enums['E_Reason']['COMMISSIONING_GATE_ACTIVE'] in active)
            register={};page=0
            while True:
                check('query static engineering register page '+str(page),request('QUERY_CONFIG',IntValue=page))
                count=read('HmiResponse.ConfigPage.EntryCount');pages=read('HmiResponse.ConfigPage.PageCount')
                if not 1<=pages<=1024:raise ValueError('unbounded manifest')
                for index in range(1,count+1):
                    item=read('HmiResponse.ConfigPage.Entries[%d].Item'%index)
                    if item.startswith('Engineering/'):
                        check('engineering metadata has no write capability '+item,read('HmiResponse.ConfigPage.Entries[%d].Writable'%index),False)
                        register[item]=read('HmiResponse.ConfigPage.Entries[%d].ValueText'%index)
                page+=1
                if page>=pages:break
            check('only active build gates registered',register['Engineering/Count'],'1')
            check('register names exact source constant',register['Engineering/Gates/1/Name'],'USE_SIMULATION')
            check('register describes simulation',register['Engineering/Gates/1/DescriptionKey'],'std.engineering.simulation')
            check('host ring advertises its bound',read('HostEvents.Capacity'),facts.capacities['MAX_HOST_EVENTS'])
            for alias in ('Home.Seq.OwnerIndex','Home.PressRam.Status.Name','Auto.Load.Seq.OwnerIndex','Core.RegIndex'):
                try:read(alias)
                except WebApiError as error:check('private storage inaccessible: '+alias,error.code,200)
                else:check('private storage inaccessible: '+alias,False)
            mode('HOME');style('SINGLE_STEP')
            check('start single-step HOME',request('START'));wait(lambda:read('RunningPublished'),'HOME running')
            wait(lambda:read('CurrentStep.StepNo')==0,'initial HOME step')
            time.sleep(.25);check('HOME waits at first boundary',read('CurrentStep.StepNo'),0)
            for next_step in (900,910):
                check('advance HOME to '+str(next_step),request('STEP_REQUEST'))
                wait(lambda:read('CurrentStep.StepNo')==next_step,'HOME '+str(next_step))
                time.sleep(.2);check('one token cannot pass '+str(next_step),read('CurrentStep.StepNo'),next_step)
            check('finish HOME',request('STEP_REQUEST'));wait(lambda:not read('RunningPublished'),'HOME completed');idle()
            check('HOME load position derived',read('OutImm.Homed'))
            style('HOLD_TO_RUN');check('start hold HOME',request('START'));wait(lambda:read('RunningPublished'),'held HOME running')
            time.sleep(.25);check('released hold blocks initial boundary',read('CurrentStep.StepNo'),0)
            check('hold grants HOME progression',request('SET_HOLD_RUN',BoolValue=True))
            wait(lambda:not read('RunningPublished'),'held HOME completed');idle()
            check('hold release always accepted',request('SET_HOLD_RUN',BoolValue=False))
            mode('CHANGEOVER');style('SINGLE_STEP')
            check('start guided CHANGEOVER',request('START'));wait(lambda:read('RunningPublished'),'CHANGEOVER running')
            advance_until(880)
            wait(lambda:read('Decision.Prompt')=='project.decision.pressChangeoverConfirm','changeover decision')
            check('decision offers repeat jump',read('Decision.Options[2]'),'project.decision.repeatChangeoverPosition')
            check('choose repeat while single-step paused',request('DECISION_ANSWER',IntValue=2))
            time.sleep(.25);check('answer waits for step permission',read('CurrentStep.StepNo'),880)
            check('release retained JUMP1',request('STEP_REQUEST'))
            wait(lambda:read('CurrentStep.StepNo')==810,'GRAPH JUMP1 880 to 810')
            check('jump returns to shared load sub-chain',read('CurrentStep.StepNo'),810)
            advance_until(880)
            wait(lambda:read('Decision.Prompt')=='project.decision.pressChangeoverConfirm','repeat asks again')
            style('HOLD_TO_RUN')
            check('confirm while hold released',request('DECISION_ANSWER',IntValue=1))
            time.sleep(.25);check('confirmed result retained behind hold',read('CurrentStep.StepNo'),880)
            check('held confirmation completes changeover',request('SET_HOLD_RUN',BoolValue=True))
            wait(lambda:read('OutCmd.ChangeoverCompleted'),'changeover result');idle()
            check('drop held run after completion',request('SET_HOLD_RUN',BoolValue=False))
            head=read('HostEvents.RingHead')
            check('CHANGEOVER_DONE produced by lifecycle',read('HostEvents.Ring[%d].Kind'%head),facts.enums['E_HostEventKind']['CHANGEOVER_DONE'])
            check('host uses canonical producing station',read('HostEvents.Ring[%d].StationPath'%head),'PressDemo')
            check('host clock qualification remains explicit',read('HostEvents.Ring[%d].TimeSynchronized'%head),False)
            mode('MANUAL');check('MANUAL does not advertise step pacing',read('SupportedRunStylesPublished[1]'),False)
            check('unsupported mode pacing refused',request('SET_RUN_STYLE',IntValue=facts.enums['E_RunStyle']['SINGLE_STEP']),False)
            check('original keeper unchanged',original(),before)
            emit(dict(result='PASS',checks=len(checks),failures=sum(not p for p in checks)))
        except BaseException:
            emit(dict(result='FAIL',checks=len(checks),failures=sum(not p for p in checks),original_before=before,original_after=original()));raise
        finally:
            if api.conn:api.conn.close()


if __name__=='__main__':probe(Path(sys.argv[1]))
