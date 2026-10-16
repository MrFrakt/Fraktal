"""Native retained FIFO, typed receipts and real SQLite crash/retry qualification."""
import importlib.util,json,os,sqlite3,subprocess,sys,time
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'tools'))
from tia_webapi import WebApi,leaf_var
from tia_mailbox import Mailbox
from tia_target_guard import guard
from fraktal_tia_binding import Catalog
from tia_event_collector import EventCollector,SqliteEventStore,POLICY_DATA

def probe(out):
    checks=[];complete=False
    pin=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin'
    api=WebApi('169.254.212.49',pin,False);store=SqliteEventStore(out.with_suffix('.sqlite'))
    with out.open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):stream.write(json.dumps(row,ensure_ascii=True)+'\n');stream.flush()
        def check(name,actual,expected=True):
            ok=type(actual) is type(expected) and actual==expected;checks.append((name,ok));emit(dict(event='check',name=name,actual=actual,expected=expected,passed=ok))
            if not ok:raise AssertionError(name)
        def until(test,name):
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                if test():return
                time.sleep(.02)
            raise AssertionError(name)
        def write(values):
            emit(dict(event='fixture-guard',status=guard(),targets=list(values)))
            rows=api.bulk([('PlcProgram.Write',dict(var=leaf_var(n.split('.')),value=v)) for n,v in values.items()])
            assert not any(error for value,error in rows)
        def login(root='StationA',user='admin'):
            check('login consumed '+root+' '+user,box.request('LOGIN',root,User=user,Secret=os.environ['FRAKTAL_TIA_'+user.upper()+'_PIN']))
            until(lambda:not box.read(root+'.Access.LoginBusy'),'login completion')
            check('login level '+root+' '+user,box.read(root+'.Access.CurrentLevel'),4 if user=='admin' else 1)
        def stimulate(scope='StationA',operation=1,text='test.delivery',unicode=False):
            write({'GDB_DeliveryTest.Scope':scope,'GDB_DeliveryTest.Text':text,'GDB_DeliveryTest.Reason':17000,'GDB_DeliveryTest.UnicodeMode':unicode})
            write({'GDB_DeliveryTest.Operation':operation});until(lambda:box.read('GDB_DeliveryTest.Operation')==0,'stimulus consumed')
        def pending(slot):return box.read('FRK_EventDeliveryView.Rows['+str(slot)+'].Pending')
        def drain(slot):
            for i in range(24):
                result=collector.deliver_once(slot)
                if result is None:return
                assert result['accepted'],'Authorized drain refused'
            raise AssertionError('delivery receipt recursion')
        def restart(power=False):
            nonlocal api,box,collector
            before=box.read('GDB_AccessPersistTest.StartupCount')
            if power:api.conn.close()
            scripts=[(HERE.parent/'Config/cycle_simulator.ps1',None)] if power else [(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1',a) for a in ('halt','run')]
            for script,action in scripts:
                emit(dict(event='restart-guard',status=guard(),power=power,action=action))
                cmd=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script)]
                if action:cmd+=['-Action',action]
                result=subprocess.run(cmd,capture_output=True);emit(dict(event='restart-result',exit_code=result.returncode,output=result.stdout.decode('utf-8-sig')));assert result.returncode==0
            if power:api=WebApi('169.254.212.49',pin,False);api.login('fraktal')
            box=Mailbox(api,guard,emit);collector=EventCollector(api,store,guard,emit)
            until(lambda:box.read('GDB_AccessPersistTest.StartupCount')>before,'complete forest startup')
            check('restart session inactive',box.read('StationA.Access.CurrentLevel'),0)
            check('restart output inactive',box.read('StationA.Cell.Gate.OutImm.Output'),False)
        def repair(scope,epoch):
            return collector.receipts.request(POLICY_DATA['request_kinds']['DISCARD_LOST_EVENT_DELIVERY'],scope.split('.')[0],TargetPath=scope,NameValue=str(epoch),TextValue=stream_id,BoolValue=True)
        try:
            api.login('fraktal');box=Mailbox(api,guard,emit);collector=EventCollector(api,store,guard,emit)
            check('selected consumers only',box.read('FRK_EventDeliveryView.Count'),3)
            owners={box.read('FRK_EventDeliveryView.Rows['+str(i)+'].Scope'):i for i in range(1,4)}
            check('canonical selected owners',sorted(owners),['StationA','StationA.Satellite','StationB'])
            stream_id=box.read('FRK_EventDeliveryView.Rows[1].StreamId')
            for i in range(1,4):check('fresh image valid '+str(i),box.read('FRK_EventDeliveryView.Rows['+str(i)+'].RestoreLost'),False)
            login();login('StationB')
            for root in ('StationA','StationB'):
                if box.read(root+'.AlarmLog.Blocking'):
                    assert box.request('OPERATOR_RESET',root)
                    until(lambda:not box.read(root+'.AlarmLog.Blocking'),'initial manual latch reset')
                assert box.request('SET_SESSION_TIMEOUT',root,DurationMs=0)
            for i in range(1,4):drain(i)
            stimulate(unicode=True);check('come plus close queued',pending(1),2)
            first=collector.head(1);check('come phase',first['event']['State'],1);check('full Unicode record',first['event']['Description'],'test.\u4e2d\u6587')
            # Commit succeeds, then the collector dies before sending any receipt.
            check('first durable SQLite insert',store.persist(first));store.close();store=SqliteEventStore(out.with_suffix('.sqlite'));collector=EventCollector(api,store,guard,emit)
            check('crash leaves same head',collector.head(1),first)
            operator_sequence=box.read('StationA.HmiRequest.Sequence')
            operator_ack=box.read('StationA.HmiResponse.AckSequence')
            write({'StationA.HmiRequest.Kind':Catalog.read().enums['E_HmiRequestKind']['START']})
            result=collector.deliver_once(1);check('restarted collector deduplicates',result['new'],False);check('durable receipt accepted',result['accepted'])
            check('receipt leaves operator commit unchanged',box.read('StationA.HmiRequest.Sequence'),operator_sequence)
            check('receipt leaves operator acknowledgement unchanged',box.read('StationA.HmiResponse.AckSequence'),operator_ack)
            check('uncommitted START cannot mix with receipt',box.read('StationA.RunningPublished'),False)
            write({'StationA.HmiRequest.Kind':Catalog.read().enums['E_HmiRequestKind']['NONE']})
            second=collector.head(1);check('close phase',second['event']['State'],0);check('separate phase identity',second['token']!=first['token'])
            check('stale receipt refused',collector.acknowledge(first),False);check('stale receipt preserves close',collector.head(1),second)
            altered=dict(second);altered['checksum']^=1
            check('wrong checksum receipt refused',collector.acknowledge(altered),False)
            check('peer cannot receipt foreign scope',collector.receipts.request(POLICY_DATA['request_kinds']['ACK_EVENT_DELIVERY'],'StationB',TargetPath='StationA',NameValue=second['token'],DurationMs=second['checksum']),False)
            check('prefix alias refused',collector.receipts.request(POLICY_DATA['request_kinds']['ACK_EVENT_DELIVERY'],TargetPath='StationAOther',NameValue=second['token'],DurationMs=second['checksum']),False)
            check('unknown descendant refused',collector.receipts.request(POLICY_DATA['request_kinds']['ACK_EVENT_DELIVERY'],TargetPath='StationA.Unknown',NameValue=second['token'],DurationMs=second['checksum']),False)
            check('receipt leaves alarm state closed',box.read('StationA.AlarmLog.NActive'),0)
            check('FIFO drains close',collector.deliver_once(1)['accepted']);check('no receipt feedback loop',pending(1),0)
            stimulate();old=collector.head(1)
            # A real database write refusal must not remove the PLC record.
            store.conn.execute('PRAGMA query_only=ON');refused=False
            try:collector.deliver_once(1)
            except sqlite3.OperationalError:refused=True
            check('database refusal surfaced',refused);check('database refusal retains PLC head',collector.head(1),old)
            store.conn.execute('PRAGMA query_only=OFF')
            assert box.request('LOGOUT');denied=collector.deliver_once(1)
            check('anonymous cannot receipt',denied['accepted'],False);check('anonymous receipt keeps same head',collector.head(1),old)
            login(user='operator');check('operator cannot receipt',collector.deliver_once(1)['accepted'],False)
            login();data_gate=Catalog.read().enums['E_GatedAction']['DATA_WRITE'];old_level=box.read('StationA.Access.Policy.Required['+str(data_gate)+']')
            check('data gate lowered for negative control',box.request('SET_ACCESS_LEVEL',IntValue=data_gate,TextValue='0'))
            # Re-login as operator after policy lowering: fixed delivery minimum wins.
            login(user='operator');check('delivery minimum survives lowered data gate',collector.deliver_once(1)['accepted'],False);login()
            assert box.request('SET_ACCESS_LEVEL',IntValue=data_gate,TextValue=str(old_level))
            for i in range(1,4):drain(i)
            for scope in owners:stimulate(scope,text='test.retained.'+scope)
            originals={scope:collector.head(slot) for scope,slot in owners.items()}
            restart()
            for scope,slot in owners.items():check('STOP/RUN preserves exact FIFO head '+scope,collector.head(slot),originals[scope])
            restart(True)
            for scope,slot in owners.items():check('power preserves exact FIFO head '+scope,collector.head(slot),originals[scope])
            login();login('StationB')
            for i in range(1,4):drain(i)
            for point in (40,41):
                stimulate(operation=2,text='test.interrupted-close.'+str(point));before=collector.head(1)
                event_slot=box.read('GDB_DeliveryTest.EventSlot')
                write({'GDB_AlarmRecoveryTest.Scope':'StationA','GDB_AlarmRecoveryTest.EventSlot':event_slot})
                write({'GDB_AlarmRecoveryTest.Operation':point});until(lambda:box.read('GDB_AlarmRecoveryTest.Operation')==0,'close interruption consumed')
                check('close queued before history point '+str(point),pending(1),2)
                restart();check('close interruption keeps exact come '+str(point),collector.head(1),before)
                check('close interruption remains two records '+str(point),pending(1),2)
                login();assert collector.deliver_once(1)['accepted']
                check('interrupted close delivered once '+str(point),collector.head(1)['event']['State'],0)
                drain(1);check('interrupted close queue drained '+str(point),pending(1),0)
            # Full queue preserves its oldest record; loss is explicitly counted.
            dropped_before=box.read('FRK_EventDeliveryView.Rows[1].Dropped')
            for i in range(5):stimulate(text='test.capacity.'+str(i))
            check('bounded pending capacity',pending(1),8)
            check('overflow visible',box.read('FRK_EventDeliveryView.Rows[1].Overflow'))
            check('discarded delivery count',box.read('FRK_EventDeliveryView.Rows[1].Dropped')-dropped_before,2)
            head=collector.head(1);drain(1);check('drain never removes overflow marker',box.read('FRK_EventDeliveryView.Rows[1].Overflow'))
            stimulate('StationB',text='test.peer-preserved');peer=collector.head(3)
            for damage in (1,2,3,4,5,6,8):
                drain(1);stimulate(text='test.damage.'+str(damage));before=collector.head(1);epoch=before['epoch']
                write({'GDB_DeliveryTest.Scope':'StationA','GDB_DeliveryTest.Damage':damage});restart()
                check('corruption injected '+str(damage),box.read('GDB_DeliveryTest.Applied'))
                check('corrupt image rejected whole '+str(damage),box.read('FRK_EventDeliveryView.Rows[1].RestoreLost'))
                check('no corrupt head published '+str(damage),box.read('FRK_EventDeliveryView.Rows[1].Token'),'')
                check('restore loss annunciated '+str(damage),any(box.read('StationA.AlarmLog.Active['+str(i)+'].ReasonCode')==POLICY_DATA['restore_loss']['code'] for i in range(1,17)))
                check('corruption preserves peer '+str(damage),collector.head(3),peer)
                check('anonymous cannot discard lost image '+str(damage),repair('StationA',epoch),False)
                login();check('explicit engineering discard accepted '+str(damage),repair('StationA',epoch))
                check('new identity epoch '+str(damage),box.read('FRK_EventDeliveryView.Rows[1].Epoch'),epoch+1)
                check('loss marker remains after discard '+str(damage),box.read('FRK_EventDeliveryView.Rows[1].Overflow'))
                check('image usable after explicit discard '+str(damage),box.read('FRK_EventDeliveryView.Rows[1].RestoreLost'),False)
                check('pre-discard receipt cannot remove new epoch '+str(damage),collector.acknowledge(before),False)
            # An invalid identity anchor cannot be discarded into reused IDs.
            drain(1);stimulate();write({'GDB_DeliveryTest.Scope':'StationA','GDB_DeliveryTest.Damage':7});restart();login()
            check('bad anchor visible',box.read('FRK_EventDeliveryView.Rows[1].AnchorValid'),False)
            check('bad anchor discard refused',repair('StationA',1),False)
            write({'GDB_DeliveryTest.Damage':10});restart();login()
            check('test-only checksum correction restores anchor',box.read('FRK_EventDeliveryView.Rows[1].AnchorValid'))
            drain(1);login('StationB');drain(3)
            for path in ('FRK_EventDeliveryStore.Images[1].Count','FRK_EventDeliveryStore.Anchors[1].Epoch','FRK_EventDeliveryRuntime.Valid[1]','StationA.AlarmLog.DeliverySlot'):
                response=api.bulk([('PlcProgram.Read',dict(var=leaf_var(path.split('.'))))])[0]
                check('private queue read refused '+path,response[1]['code'],200)
            for path,value in [('FRK_EventDeliveryView.Rows[1].Pending',0),('FRK_EventDeliveryView.Rows[1].Token','forged'),('FRK_EventDeliveryView.Rows[1].Ev.State',0)]:
                emit(dict(event='mutation-guard',status=guard(),targets=[path]));response=api.bulk([('PlcProgram.Write',dict(var=leaf_var(path.split('.')),value=value))])[0]
                check('published queue write refused '+path,response[1]['code'],205)
            emit(dict(event='mutation-guard',status=guard(),targets=['FRK_EventDeliveryReceipt.Response[1].Accepted']))
            response=api.bulk([('PlcProgram.Write',dict(var=leaf_var(['FRK_EventDeliveryReceipt','Response[1]','Accepted']),value=True))])[0]
            check('receipt response is read only',response[1]['code'],205)
            check('SQLite persisted unique event identities',store.conn.execute('SELECT count(*)=count(DISTINCT token) FROM events').fetchone()[0],1)
            complete=True
        finally:
            store.close();api.conn.close()
            if not complete:checks.append(('probe completed',False))
            emit(dict(event='summary',checks=len(checks),failures=sum(not ok for n,ok in checks),completed=complete))
            suite=ET.Element('testsuite',name='Fraktal.TIA.EventDelivery',tests=str(len(checks)),failures=str(sum(not ok for n,ok in checks)))
            for name,ok in checks:
                case=ET.SubElement(suite,'testcase',name=name)
                if not ok:ET.SubElement(case,'failure',message=name)
            ET.ElementTree(suite).write(out.with_suffix('.junit.xml'),encoding='utf-8',xml_declaration=True)

if __name__=='__main__':probe(Path(sys.argv[1]))
