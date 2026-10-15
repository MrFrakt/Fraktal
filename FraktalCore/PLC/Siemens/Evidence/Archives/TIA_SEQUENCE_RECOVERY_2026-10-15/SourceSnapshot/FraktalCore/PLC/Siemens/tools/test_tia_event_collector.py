"""Durable receipt ordering, identity conflicts and failure/reconnect boundaries."""
import copy,json,sqlite3,tempfile,unittest
from pathlib import Path
from tia_event_collector import EVENT_FIELDS,EventCollector,SqliteEventStore,entry_crc,validate_envelope
from fraktal_tia_event_delivery import build
from fraktal_tia_binding import Catalog
from fraktal_tia_declaration import validate,DeclarationError
from fraktal_tia_generate import build as generate
from tia_delivery_mailbox import ReceiptMailbox

def envelope(sequence=1):
    event={f['member']:('' if f['native_type'].startswith(('String','WString')) else ('0' if f['native_type']=='LDT' else (False if f['native_type']=='Bool' else 0))) for f in EVENT_FIELDS}
    event.update(ReasonCode=17000,Description='test.\u4e2d\u6587',SourcePath='StationA',State=1)
    stream='78f23c0b-7bce-4521-96d5-3f5ee7e3f4ce'
    return dict(schema_version=1,token=stream+'/StationA/1/'+str(sequence),stream_id=stream,scope='StationA',epoch=1,checksum=entry_crc(sequence,event),event=event)

class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'events.sqlite';self.store=SqliteEventStore(self.path)
    def tearDown(self):self.store.close();self.temp.cleanup()
    def test_durable_reopen_and_unique_identity(self):
        value=envelope();self.assertTrue(self.store.persist(value));self.store.close();self.store=SqliteEventStore(self.path)
        self.assertFalse(self.store.persist(value));self.assertEqual(self.store.conn.execute('SELECT count(*) FROM events').fetchone()[0],1)
        self.assertEqual(json.loads(self.store.conn.execute('SELECT payload FROM events').fetchone()[0]),value)
        self.assertEqual(self.store.conn.execute('PRAGMA synchronous').fetchone()[0],2)
    def test_identity_conflict_preserves_committed_record(self):
        value=envelope();self.store.persist(value);different=copy.deepcopy(value);different['event']['Description']='other';different['checksum']=entry_crc(1,different['event'])
        with self.assertRaisesRegex(ValueError,'Conflicting'):self.store.persist(different)
        self.assertEqual(json.loads(self.store.conn.execute('SELECT payload FROM events').fetchone()[0]),value)
    def test_damaged_existing_record_not_acknowledged(self):
        value=envelope();self.store.persist(value);self.store.conn.execute("UPDATE events SET sha256='damaged'")
        with self.assertRaisesRegex(ValueError,'damaged'):self.store.persist(value)
    def test_incomplete_or_changed_record_refused(self):
        value=envelope();value['event']['Description']='altered'
        with self.assertRaisesRegex(ValueError,'checksum'):self.store.persist(value)
        value=envelope();del value['event']['ShelfTimeSynchronized']
        with self.assertRaisesRegex(ValueError,'Incomplete'):self.store.persist(value)
        self.assertEqual(self.store.conn.execute('SELECT count(*) FROM events').fetchone()[0],0)
    def test_foreign_database_refused(self):
        p=Path(self.temp.name)/'foreign.sqlite';c=sqlite3.connect(p);c.execute('CREATE TABLE unrelated(x)');c.commit();c.close()
        with self.assertRaisesRegex(ValueError,'identity'):SqliteEventStore(p)
    def collector(self,receipt):
        collector=EventCollector(None,self.store,lambda:{})
        collector.head=lambda slot:envelope();collector.acknowledge=receipt
        return collector
    def test_database_failure_has_no_receipt(self):
        receipts=[];self.store.conn.execute('PRAGMA query_only=ON')
        with self.assertRaises(sqlite3.OperationalError):self.collector(lambda v:receipts.append(v)).deliver_once(1)
        self.assertEqual(receipts,[]);self.assertFalse(self.store.conn.in_transaction)
    def test_commit_precedes_receipt_and_retry_deduplicates(self):
        def lost(value):
            self.assertEqual(self.store.conn.execute('SELECT count(*) FROM events').fetchone()[0],1)
            raise TimeoutError('lost receipt')
        with self.assertRaises(TimeoutError):self.collector(lost).deliver_once(1)
        self.store.close();self.store=SqliteEventStore(self.path)
        self.assertEqual(self.collector(lambda v:True).deliver_once(1)['new'],False)
        self.assertEqual(self.store.conn.execute('SELECT count(*) FROM events').fetchone()[0],1)
    def test_denied_receipt_keeps_durable_event(self):
        result=self.collector(lambda v:False).deliver_once(1)
        self.assertFalse(result['accepted']);self.assertEqual(self.store.conn.execute('SELECT count(*) FROM events').fetchone()[0],1)
    def test_receipt_transport_has_no_operator_command_vocabulary(self):
        receipt=ReceiptMailbox(None,lambda:{},lambda r:None)
        with self.assertRaisesRegex(ValueError,'Only event delivery'):receipt.request(Catalog.read().enums['E_HmiRequestKind']['START'])
    def test_token_identity_and_crc_cover_each_field(self):
        base=envelope()
        for f in EVENT_FIELDS:
            value=copy.deepcopy(base);kind=f['native_type'];name=f['member']
            if kind.startswith(('String','WString')):value['event'][name]+='x'
            elif kind=='Bool':value['event'][name]=not value['event'][name]
            else:value['event'][name]=str(int(value['event'][name])+1) if kind=='LDT' else int(value['event'][name])+1
            with self.subTest(field=name),self.assertRaises(ValueError):validate_envelope(value)
        for name,value in [('epoch',2),('scope','StationB'),('stream_id','invalid')]:
            row=copy.deepcopy(base);row[name]=value
            with self.subTest(field=name),self.assertRaises(ValueError):validate_envelope(row)

class GenerationTests(unittest.TestCase):
    def fixture(self):
        import importlib.util
        p=Path(__file__).resolve().parents[1]/'Tests/Config/make_fixture.py'
        spec=importlib.util.spec_from_file_location('config_fixture',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        value=module.declaration();value['alarm_history']={'scopes':['StationA','StationA.Satellite','StationB']}
        return value
    def test_opt_in_allocates_only_consumed_scopes(self):
        value=self.fixture();sources,_=generate(validate(value),True)
        self.assertFalse(any('Delivery' in n for n in sources));self.assertNotIn('DeliverySlot',sources['02_FRK_AlarmLog.udt'])
        value['alarm_delivery']={'scopes':['StationA.Satellite'],'capacity':3,'stream_id':envelope()['stream_id']}
        sources,manifest=generate(validate(value),True)
        self.assertIn('Array[1..1]',sources['05_FRK_EventDeliveryStore.db']);self.assertIn('Array[1..3]',sources['02_FRK_DeliveryImage.udt'])
        self.assertIn('VAR RETAIN',sources['05_FRK_EventDeliveryStore.db']);self.assertNotIn('VAR RETAIN',sources['05_FRK_EventDeliveryRuntime.db'])
        self.assertIn('ExternalWritable',sources['05_FRK_EventDeliveryView.db'])
        self.assertIn('Array[1..1]',sources['05_FRK_EventDeliveryReceipt.db'])
        self.assertNotIn('HmiRequest',sources['05_FRK_EventDeliveryReceipt.db'])
        self.assertIn('"FRK_DeliveryMailbox"',sources['13_UnitServices.scl'])
        self.assertIn('DISCARD_LOST_EVENT_DELIVERY',Path(__file__).resolve().parents[1].joinpath('Framework/Core/event_delivery.json').read_text())
        block=next(s for n,s in sources.items() if n.startswith('20_') and '"FRK_DeliveryBoot"' in s)
        self.assertLess(block.index('"FRK_DeliveryBoot"'),block.index('"FRK_UnitMailbox"'))
    def test_invalid_scope_uuid_capacity_and_project_mutation_refused(self):
        for scopes,capacity,stream in [(['StationA.Cell'],3,envelope()['stream_id']),(['StationA','StationA'],3,envelope()['stream_id']),(['StationA'],0,envelope()['stream_id']),(['StationA'],65,envelope()['stream_id']),(['StationA'],3,'other')]:
            value=self.fixture();value['alarm_delivery']=dict(scopes=scopes,capacity=capacity,stream_id=stream)
            with self.subTest(scopes=scopes,capacity=capacity,stream=stream),self.assertRaises(DeclarationError):validate(value)
        value=self.fixture();value['types'][0]['logic']['cyclic']+='\n"FRK_DeliveryCapture"();'
        with self.assertRaises(DeclarationError):generate(validate(value),True)

if __name__=='__main__':unittest.main()
