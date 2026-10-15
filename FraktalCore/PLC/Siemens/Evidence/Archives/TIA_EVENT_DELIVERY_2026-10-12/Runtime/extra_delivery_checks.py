from pathlib import Path
import os,sys,json,time
import xml.etree.ElementTree as ET
sys.path.insert(0,'C:/Projects/Fraktal/FraktalCore/PLC/Siemens/tools')
from tia_webapi import WebApi,leaf_var
from tia_target_guard import guard
from tia_mailbox import Mailbox
from tia_event_collector import EventCollector,SqliteEventStore
out=Path(sys.argv[1]);checks=[];api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
store=SqliteEventStore(out.with_suffix('.sqlite'))
with out.open('x',encoding='ascii',newline='\n') as stream:
 def emit(r):stream.write(json.dumps(r,ensure_ascii=True)+'\n');stream.flush()
 def check(n,a,e=True):
  ok=type(a) is type(e) and a==e;checks.append((n,ok));emit(dict(event='check',name=n,actual=a,expected=e,passed=ok));assert ok,n
 try:
  api.login('fraktal');box=Mailbox(api,guard,emit);collector=EventCollector(api,store,guard,emit)
  check('authorized root remains admin',box.read('StationA.Access.CurrentLevel'),4)
  for i in range(24):
   r=collector.deliver_once(1)
   if r is None:break
   assert r['accepted']
  values={'GDB_DeliveryTest.Scope':'StationA','GDB_DeliveryTest.Text':'test.lost-reply','GDB_DeliveryTest.UnicodeMode':False,'GDB_DeliveryTest.Reason':17100}
  for fields in (values,{'GDB_DeliveryTest.Operation':1}):
   emit(dict(event='fixture-guard',targets=list(fields),status=guard()))
   replies=api.bulk([('PlcProgram.Write',dict(var=leaf_var(k.split('.')),value=v)) for k,v in fields.items()]);assert not any(e for v,e in replies)
  deadline=time.monotonic()+8
  while box.read('GDB_DeliveryTest.Operation') and time.monotonic()<deadline:time.sleep(.02)
  first=collector.head(1);check('real come queued',first['event']['State'],1)
  real_receipt=collector.acknowledge
  def lost(envelope):
   assert real_receipt(envelope)
   raise TimeoutError('test: receipt reply lost after PLC acceptance')
  collector.acknowledge=lost;failed=False
  try:collector.deliver_once(1)
  except TimeoutError:failed=True
  check('lost reply reported',failed)
  check('PLC had already consumed receipt',box.read('FRK_EventDeliveryView.Rows[1].Pending'),1)
  store.close();store=SqliteEventStore(out.with_suffix('.sqlite'));collector=EventCollector(api,store,guard,emit)
  second=collector.head(1);check('reconnect reads current head',second['event']['State'],0)
  check('old receipt cannot remove new head',collector.acknowledge(first),False)
  check('old durable row remains single',store.conn.execute('SELECT count(*) FROM events WHERE token=?',(first['token'],)).fetchone()[0],1)
  check('current head delivered',collector.deliver_once(1)['accepted'])
  check('reconnect drains without replay',box.read('FRK_EventDeliveryView.Rows[1].Pending'),0)
  check('exactly two phase records stored',store.conn.execute('SELECT count(*) FROM events').fetchone()[0],2)
 finally:
  store.close();api.conn.close()
  emit(dict(event='summary',checks=len(checks),failures=sum(not ok for n,ok in checks)))
  suite=ET.Element('testsuite',name='Fraktal.TIA.DeliveryLostReply',tests=str(len(checks)),failures=str(sum(not ok for n,ok in checks)))
  for name,ok in checks:
   row=ET.SubElement(suite,'testcase',name=name)
   if not ok:ET.SubElement(row,'failure',message=name)
  ET.ElementTree(suite).write(out.with_suffix('.xml'),encoding='utf-8',xml_declaration=True)
