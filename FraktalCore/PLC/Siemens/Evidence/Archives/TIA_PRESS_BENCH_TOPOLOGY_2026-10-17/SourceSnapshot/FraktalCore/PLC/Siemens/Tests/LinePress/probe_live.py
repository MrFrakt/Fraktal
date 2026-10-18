"""Real press line/calendar, atomic sets, persistence and wired GRAPH regression."""
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
    if output.resolve().parent!=WORK.resolve():raise ValueError('fixed private workspace required')
    facts=Catalog.read();before=original();checks=[]
    pin=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Press_Features_20261016.webapi.pin'
    api=box=None
    with output.open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):stream.write(json.dumps(row)+'\n');stream.flush()
        def check(label,value,expected=True):
            passed=type(value) is type(expected) and value==expected
            emit(dict(event='check',label=label,value=value,expected=expected,passed=passed));checks.append(passed)
            if not passed:raise AssertionError(label)
        def wait(predicate,label,seconds=240):
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                if predicate():return
                time.sleep(.1)
            raise TimeoutError(label)
        def read(path):return box.read('PressDemo.'+path)
        def request(kind,**fields):return box.request(kind,root='PressDemo',**fields)
        def connect():
            nonlocal api,box
            api=WebApi(TARGET.profile['address'],pin,not pin.exists());api.login('fraktal')
            box=Mailbox(api,TARGET.guard,emit)
            wait(lambda:not box.read('FRK_PersistStatus.Restoring') and read('Line.LineId')=='PRESS-DEMO-LINE','press restore and line startup')
        def durable():
            wait(lambda:not read('ConfigPersist.Pending') and not read('ConfigPersist.Failed'),'line read-back checkpoint')
        def edit(suffix,value):return request('WRITE_CONFIG',NameValue='line.shift.'+suffix,TextValue=str(value),IntValue=1)
        def configured_target():
            page=0
            while True:
                if not request('QUERY_CONFIG',IntValue=page):raise AssertionError('manifest rejected')
                base='PressDemo.HmiResponse.ConfigPage';count=box.read(base+'.EntryCount')
                for index in range(1,count+1):
                    entry=base+'.Entries[%d]'%index
                    if box.read(entry+'.WriteKey')=='line.shift.1.target':return int(box.read(entry+'.ValueText'))
                if page+1>=box.read(base+'.PageCount'):raise AssertionError('line target absent')
                page+=1
        try:
            connect();durable()
            check('owner line identity',read('Line.LineId'),'PRESS-DEMO-LINE')
            check('owner identity is press',read('Line.Owner'),'PressDemo')
            check('local owner is current',read('Line.Stale'),False)
            check('current shift starts disabled',read('CurrentShift'),0)
            check('model capacity coexists',read('ModelCapacity'),4)
            rows=[];page=0;kind=facts.enums['E_ConfigKind']['LINE_CFG']
            while True:
                if not request('QUERY_CONFIG',IntValue=page):raise AssertionError('manifest rejected')
                base='PressDemo.HmiResponse.ConfigPage';count=box.read(base+'.EntryCount')
                names=('Scope','Item','WriteKey','ConfigKind','Writable','ValueText')
                values=api.bulk([('PlcProgram.Read',dict(var=leaf_var((base+'.Entries[%d].%s'%(i,n)).split('.')))) for i in range(1,count+1) for n in names])
                if any(error for value,error in values):raise AssertionError('manifest entry read failed')
                for start in range(0,len(values),len(names)):
                    row=dict(zip(names,[v[0] for v in values[start:start+len(names)]]))
                    if row['ConfigKind']==kind and row['WriteKey']:rows.append(row)
                if page+1>=box.read(base+'.PageCount'):break
                page+=1
            check('complete V3 line capabilities',len(rows),1+4*facts.capacities['MAX_WEEKLY_SHIFTS'])
            check('line values use root scope',all(r['Scope']=='PressDemo' for r in rows))
            check('line namespace is canonical',all(r['WriteKey'].startswith('line.shift.') for r in rows))
            check('owner values are editable',all(r['Writable'] for r in rows))
            rev=read('Line.Revision')
            for suffix,value in [('utcOffsetMin',0),('1.durationMin',1440),('1.activeDays',127),('1.target',7),('1.startMin',0)]:
                check('calendar write '+suffix,edit(suffix,value))
            wait(lambda:read('CurrentShift')==1 and read('ShiftProductionTarget')==7,'shared shift calendar applied to press')
            check('line revision changes once accepted',read('Line.Revision')>rev)
            check('prepare disabled second row',edit('2.activeDays',127))
            # Enabling a second overlapping row must refuse the complete
            # candidate and preserve the active first shift.
            rejected_revision=read('Line.Revision')
            check('overlapping active calendar refused',edit('2.startMin',0),False)
            check('refusal preserves revision',read('Line.Revision'),rejected_revision)
            check('refusal preserves current shift',read('CurrentShift'),1)
            check('line set save',request('SAVE_CONFIG_SET',TextValue='line-profile',IntValue=kind))
            check('line set export header',request('EXPORT_CONFIG_SET',TextValue='line-profile'))
            header=json.loads(read('ConfigSetDocument'))
            check('export kind is LINE_CFG',header['kind'],kind)
            check('export has no model identity',header['model'],'')
            check('export scope is root',header['root'],'PressDemo')
            check('export is complete',header['records'],len(rows))
            check('change target after snapshot',edit('1.target',9))
            check('configured target changes for future intervals',configured_target(),9)
            check('open interval retains its latched target',read('ShiftProductionTarget'),7)
            check('atomic line set load',request('LOAD_CONFIG_SET',TextValue='line-profile'))
            check('line set restores configured target',configured_target(),7)
            check('line set preserves open interval target',read('ShiftProductionTarget'),7)
            check('model change uses ordinary path',request('SET_MODEL',TextValue='PLASTIC'))
            check('model changes keep shared line',read('ShiftProductionTarget'),7)
            durable();api.conn.close();emit(dict(event='restart',status=TARGET.action('restart')));connect()
            wait(lambda:read('CurrentShift')==1,'restored current shift')
            check('line target survives actual restart',read('ShiftProductionTarget'),7)
            check('active model survives actual restart',read('Model.ModelCode'),'PLASTIC')
            check('line restore has no data loss',read('ConfigPersist.RestoreLost'),False)
            check('original Fraktal unchanged',original(),before)
            emit(dict(event='complete',checks=len(checks),failures=sum(not c for c in checks)))
        finally:
            if api and api.conn:api.conn.close()


if __name__=='__main__':probe(Path(sys.argv[1]))
